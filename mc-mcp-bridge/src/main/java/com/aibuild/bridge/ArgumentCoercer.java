package com.aibuild.bridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.BooleanNode;
import com.fasterxml.jackson.databind.node.DoubleNode;
import com.fasterxml.jackson.databind.node.IntNode;
import com.fasterxml.jackson.databind.node.LongNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Consumer;

/**
 * Postel-style lenient coercion of tool arguments before dispatch. Small models
 * often emit integers as "64", arrays as stringified JSON "[0,0]", booleans as
 * "true" - the mod backend rejects those and the model gives up. Each argument
 * is checked against the tool's inputSchema (from {@link Tools}); a string in an
 * integer/number/boolean/array/object slot is parsed when possible, recursively
 * for nested structures (e.g. string elements inside a set_blocks entry).
 *
 * Only strings (and integral doubles in integer slots) are coerced; values of
 * other wrong types pass through untouched so backend validation keeps its say.
 * A string that cannot be parsed raises {@link CoercionException}, which the
 * dispatcher surfaces as an isError result naming the offending parameter.
 * Every applied coercion is logged.
 */
final class ArgumentCoercer {

    /** A string argument that could not be parsed into its schema type. */
    static final class CoercionException extends Exception {
        CoercionException(String message) {
            super(message);
        }
    }

    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, JsonNode> schemasByTool = new HashMap<>();
    private final Consumer<String> logger;

    ArgumentCoercer(Consumer<String> logger) {
        this.logger = logger;
        for (JsonNode tool : Tools.definitions(mapper)) {
            schemasByTool.put(tool.path("name").asText(), tool.path("inputSchema"));
        }
    }

    /** Returns a copy of args with coercible values fixed up; unknown fields pass through. */
    JsonNode coerce(String toolName, JsonNode args) throws CoercionException {
        JsonNode schema = schemasByTool.get(toolName);
        if (schema == null || !args.isObject()) {
            return args;
        }
        ObjectNode coerced = args.deepCopy();
        JsonNode properties = schema.path("properties");
        for (String field : fieldNames(coerced)) {
            JsonNode propSchema = properties.get(field);
            if (propSchema != null) {
                coerced.set(field, coerceValue(propSchema, coerced.get(field), field));
            }
        }
        return coerced;
    }

    private JsonNode coerceValue(JsonNode schema, JsonNode value, String path) throws CoercionException {
        return switch (schema.path("type").asText("")) {
            case "integer" -> coerceInteger(value, path);
            case "number" -> coerceNumber(value, path);
            case "boolean" -> coerceBoolean(value, path);
            case "array" -> coerceArray(schema, value, path);
            case "object" -> coerceObject(schema, value, path);
            default -> value;
        };
    }

    private JsonNode coerceInteger(JsonNode value, String path) throws CoercionException {
        if (value.isIntegralNumber()) {
            return value;
        }
        if (value.isFloatingPointNumber() && value.canConvertToLong()
                && value.doubleValue() == Math.rint(value.doubleValue())) {
            logger.accept("coerced " + path + ": number -> integer");
            return integerNode(value.longValue());
        }
        if (value.isTextual()) {
            Long parsed = parseLong(value.asText().strip());
            if (parsed != null) {
                logger.accept("coerced " + path + ": string -> integer");
                return integerNode(parsed);
            }
            throw failure(path, "integer", value);
        }
        return value;
    }

    private JsonNode coerceNumber(JsonNode value, String path) throws CoercionException {
        if (value.isNumber()) {
            return value;
        }
        if (value.isTextual()) {
            try {
                double d = Double.parseDouble(value.asText().strip());
                if (Double.isFinite(d)) {
                    logger.accept("coerced " + path + ": string -> number");
                    return DoubleNode.valueOf(d);
                }
            } catch (NumberFormatException ignored) {
                // fall through to failure
            }
            throw failure(path, "number", value);
        }
        return value;
    }

    private JsonNode coerceBoolean(JsonNode value, String path) throws CoercionException {
        if (value.isBoolean()) {
            return value;
        }
        if (value.isTextual()) {
            String s = value.asText().strip().toLowerCase(Locale.ROOT);
            if (s.equals("true") || s.equals("false")) {
                logger.accept("coerced " + path + ": string -> boolean");
                return BooleanNode.valueOf(s.equals("true"));
            }
            throw failure(path, "boolean", value);
        }
        return value;
    }

    private JsonNode coerceArray(JsonNode schema, JsonNode value, String path) throws CoercionException {
        JsonNode node = value;
        if (value.isTextual()) {
            node = parseJsonContainer(value, path, "array");
            logger.accept("coerced " + path + ": string -> array");
        }
        if (node.isArray()) {
            JsonNode items = schema.get("items");
            if (items != null) {
                ArrayNode array = (ArrayNode) node;
                for (int i = 0; i < array.size(); i++) {
                    array.set(i, coerceValue(items, array.get(i), path + "[" + i + "]"));
                }
            }
        }
        return node;
    }

    private JsonNode coerceObject(JsonNode schema, JsonNode value, String path) throws CoercionException {
        JsonNode node = value;
        if (value.isTextual()) {
            node = parseJsonContainer(value, path, "object");
            logger.accept("coerced " + path + ": string -> object");
        }
        if (node.isObject()) {
            JsonNode properties = schema.get("properties");
            if (properties != null) {
                ObjectNode object = (ObjectNode) node;
                for (String field : fieldNames(object)) {
                    JsonNode propSchema = properties.get(field);
                    if (propSchema != null) {
                        object.set(field, coerceValue(propSchema, object.get(field), path + "." + field));
                    }
                }
            }
        }
        return node;
    }

    /** Parse a string as JSON and require the expected container kind. */
    private JsonNode parseJsonContainer(JsonNode value, String path, String kind) throws CoercionException {
        try {
            JsonNode parsed = mapper.readTree(value.asText().strip());
            if (parsed != null && (kind.equals("array") ? parsed.isArray() : parsed.isObject())) {
                return parsed;
            }
        } catch (Exception ignored) {
            // fall through to failure
        }
        throw failure(path, kind, value);
    }

    private static Long parseLong(String s) {
        try {
            return Long.parseLong(s);
        } catch (NumberFormatException ignored) {
            // fall through to the decimal form ("64.0")
        }
        try {
            double d = Double.parseDouble(s);
            if (Double.isFinite(d) && d == Math.rint(d)
                    && d >= Long.MIN_VALUE && d <= Long.MAX_VALUE) {
                return (long) d;
            }
        } catch (NumberFormatException ignored) {
            // not a number at all
        }
        return null;
    }

    /** IntNode when possible: consumers like BlocksFilePlacer check isInt(). */
    private static JsonNode integerNode(long v) {
        return v >= Integer.MIN_VALUE && v <= Integer.MAX_VALUE
                ? IntNode.valueOf((int) v) : LongNode.valueOf(v);
    }

    private static List<String> fieldNames(ObjectNode node) {
        List<String> names = new ArrayList<>();
        node.fieldNames().forEachRemaining(names::add);
        return names;
    }

    private static CoercionException failure(String path, String expected, JsonNode value) {
        String text = value.asText();
        if (text.length() > 80) {
            text = text.substring(0, 80) + "...";
        }
        String article = expected.equals("integer") || expected.equals("array") || expected.equals("object")
                ? "an" : "a";
        return new CoercionException("\"" + path + "\" must be " + article + " " + expected
                + ", but the string \"" + text + "\" could not be parsed as one.");
    }
}
