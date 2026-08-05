#!/usr/bin/env python3
"""lottery.py — anti-AI-bias style-axis lottery (反 AI 偏好抽签器).

A style card's "lottery" field declares weighted option axes (roof_type,
dormers, chimney, ...) plus interaction rules. This script draws one concrete
combination per build so the AI doesn't default to its favorite every time.
Deterministic iron rule: same card + same seed => byte-identical output.

Card schema (defaults/styles/<style>.json):
  "lottery": {
    "axes": {
      "<axis>": {"options": [
        {"id": "gable_steep", "weight": 80, "source": "gc:..."},
        {"id": "hip", "weight": 19, "requires": {"plot": "corner"}}
      ]}
    },
    "rules": [
      {"if": {"roof_type": "hip"}, "forbid": ["dormers_gable"]},
      {"if": {"roof_type": "hip"}, "then": {"chimney": "rear_slope"}}
    ]
  }

Pipeline:
  1. per-axis weighted draw (random.Random(seed)); options whose "requires"
     conditions are not all satisfied by --params are filtered out first.
  2. rules fixpoint: "if" (matched against current axes only) -> "forbid"
     bans those option ids on whichever axis declares them and that axis is
     redrawn; "then" with an AXIS key force-writes that axis (value must be
     an existing option id on it; overrides requires by designer intent).
     Repeat until a round changes nothing; still flipping after 10 redraw
     rounds = dead-loop rules -> die.
  3. "then" with a NON-axis key (e.g. {"weathering_preset": "plaster_timber"},
     {"pilaster": false}) is not an axis at all: it writes extra build params
     into build_order.params, collected from the rules matching the FINAL
     axes (rule order, last write wins).
  4. emit {"build_order": {style, seed, axes, params, texture_seed}};
     texture_seed is derived from seed (own Random stream, independent of
     draw count).

Usage:
  python lottery.py --params '{"style":"medieval_house","seed":12345,"plot":"corner"}' --out build_order.json
seed optional: if omitted, the current timestamp is used and printed to
stderr so the run can be reproduced. Every successful draw appends
{ts,style,seed,axes} to lottery_log.jsonl next to --out (calibration data).
"""
import argparse, json, os, random, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
STYLES_DIR = os.path.normpath(os.path.join(HERE, "..", "styles"))
MAX_RULE_ROUNDS = 10

def die(msg, legal=None):
    print(json.dumps({"error": msg, "legal": legal}, ensure_ascii=False), file=sys.stderr)
    sys.exit(2)

def known_styles():
    try:
        return sorted(f[:-5] for f in os.listdir(STYLES_DIR) if f.endswith(".json"))
    except OSError:
        return []

def whitelisted_styles():
    ok = []
    for s in known_styles():
        try:
            with open(os.path.join(STYLES_DIR, s + ".json"), encoding="utf-8") as f:
                if "lottery" in json.load(f):
                    ok.append(s)
        except (OSError, json.JSONDecodeError):
            pass
    return ok

def load_style(style):
    path = os.path.join(STYLES_DIR, style + ".json")
    if not os.path.isfile(path):
        die("unknown style '%s' (no %s)" % (style, path), known_styles())
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        die("cannot read style card '%s': %s" % (style, e), known_styles())

def _match(cond, values):
    # cond {key: wanted | [wanted...]} matches iff every key's actual value
    # equals (or is among) the wanted one(s); a missing actual value never
    # matches. Empty cond matches unconditionally.
    for k, want in cond.items():
        got = values.get(k)
        if isinstance(want, list):
            if got not in want:
                return False
        elif got != want:
            return False
    return True

def available_options(axis, spec, params):
    opts = spec.get("options") if isinstance(spec, dict) else None
    if not isinstance(opts, list) or not opts:
        die("lottery axis '%s' has no options" % axis)
    for o in opts:
        if not isinstance(o, dict) or not o.get("id"):
            die("lottery axis '%s' has an option without an 'id'" % axis)
        w = o.get("weight", 1)
        if isinstance(w, bool) or not isinstance(w, (int, float)) or w < 0:
            die("lottery axis '%s' option '%s' has bad weight %r" % (axis, o.get("id"), o.get("weight")))
    ok = [o for o in opts if _match(o.get("requires", {}), params)]
    if not ok:
        die("lottery axis '%s': no option survives requires-filtering under params %s"
            % (axis, json.dumps(params, ensure_ascii=False, sort_keys=True)),
            [o["id"] for o in opts])
    return ok

def _draw(options, rng):
    ids = [o["id"] for o in options]
    weights = [o.get("weight", 1) for o in options]
    if sum(weights) <= 0:
        die("lottery options %s have zero total weight" % ids, ids)
    return rng.choices(ids, weights=weights, k=1)[0]

def run_lottery(lottery, params, rng):
    axes_def = lottery.get("axes")
    if not isinstance(axes_def, dict) or not axes_def:
        die("lottery field has no non-empty 'axes' object")
    rules = lottery.get("rules", [])
    if not isinstance(rules, list):
        die("lottery 'rules' must be a list")
    avail = {ax: available_options(ax, spec, params) for ax, spec in axes_def.items()}
    # option id -> axes declaring it (forbid targets option ids, not axes)
    id_axes = {}
    for ax in axes_def:
        for o in axes_def[ax].get("options", []):
            id_axes.setdefault(o.get("id"), []).append(ax)
    # initial draw: axes in card order — deterministic rng stream
    chosen = {ax: _draw(avail[ax], rng) for ax in axes_def}

    converged = False
    for rnd in range(1, MAX_RULE_ROUNDS + 2):  # 10 redraw rounds + 1 check
        forbid = {ax: set() for ax in axes_def}
        forces = []
        for rule in rules:
            if not isinstance(rule, dict):
                die("lottery rule is not an object: %r" % (rule,))
            if not _match(rule.get("if", {}), chosen):
                continue
            fb = rule.get("forbid", [])
            if isinstance(fb, str):
                fb = [fb]
            for fid in fb:
                targets = id_axes.get(fid)
                if not targets:
                    die("lottery rule forbids unknown option id '%s'" % fid,
                        sorted(x for x in id_axes if x))
                for ax in targets:
                    forbid[ax].add(fid)
            then = rule.get("then", {})
            if not isinstance(then, dict):
                die("lottery rule 'then' must be an object {axis|param: value}")
            for ax, val in then.items():
                if ax in axes_def:
                    forces.append((ax, val))
                # non-axis keys are output params, applied after convergence
        changed = False
        for ax, val in forces:
            if ax not in axes_def:
                die("lottery rule 'then' targets unknown axis '%s'" % ax, list(axes_def))
            legal = [o["id"] for o in axes_def[ax].get("options", [])]
            if val not in legal:
                die("lottery rule 'then' forces unknown option '%s' on axis '%s'" % (val, ax), legal)
            if chosen[ax] != val:
                chosen[ax] = val
                changed = True
        for ax in axes_def:  # card order — deterministic redraw stream
            if chosen[ax] in forbid[ax]:
                pool = [o for o in avail[ax] if o["id"] not in forbid[ax]]
                if not pool:
                    die("lottery rules forbid every available option of axis '%s' (round %d)"
                        % (ax, rnd), [o["id"] for o in avail[ax]])
                chosen[ax] = _draw(pool, rng)
                changed = True
        if not changed:
            converged = True
            break
    if not converged:
        die("lottery rules did not converge after %d redraw rounds (dead-loop rules in style card)"
            % MAX_RULE_ROUNDS)
    # extra build params from rules matching the FINAL axes (rule order, last wins)
    extra = {}
    for rule in rules:
        if _match(rule.get("if", {}), chosen):
            for k, v in rule.get("then", {}).items():
                if k not in axes_def:
                    extra[k] = v
    return chosen, extra

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}",
                    help="JSON object: style (required), seed (optional int), plus requires-context keys e.g. plot")
    ap.add_argument("--out", default="", help="output file (default: stdout)")
    a = ap.parse_args()
    try:
        params = json.loads(a.params) if a.params.strip() else {}
    except json.JSONDecodeError as e:
        die("invalid --params JSON: %s" % e)
    if not isinstance(params, dict):
        die("--params must be a JSON object")
    style = params.get("style")
    if not style or not isinstance(style, str):
        die("missing required param 'style'", known_styles())
    card = load_style(style)
    lottery = card.get("lottery")
    if not isinstance(lottery, dict):
        die("style card '%s' has no 'lottery' field — 该卡未白名单化 (not whitelisted for lottery)" % style,
            whitelisted_styles())
    if params.get("seed") is None:
        seed = int(time.time())
        print("no seed given; using timestamp seed %d "
              "(re-run with '\"seed\":%d' in --params to reproduce)" % (seed, seed), file=sys.stderr)
    else:
        try:
            seed = int(params["seed"])
        except (TypeError, ValueError):
            die("param 'seed' must be an integer, got %r" % (params["seed"],))
    rng = random.Random(seed)
    axes, extra = run_lottery(lottery, params, rng)
    texture_seed = random.Random("texture:%d" % seed).getrandbits(32)
    order = {"build_order": {"style": style, "seed": seed, "axes": axes,
                             "params": extra, "texture_seed": texture_seed}}
    out = json.dumps(order, ensure_ascii=False)
    log_dir = os.path.dirname(os.path.abspath(a.out)) if a.out else os.getcwd()
    try:
        with open(os.path.join(log_dir, "lottery_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "style": style, "seed": seed, "axes": axes},
                               ensure_ascii=False) + "\n")
    except OSError as e:
        print("warning: could not append lottery_log.jsonl: %s" % e, file=sys.stderr)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote build_order (%d axes) to %s" % (len(axes), a.out), file=sys.stderr)
    else:
        print(out)

if __name__ == "__main__":
    main()
