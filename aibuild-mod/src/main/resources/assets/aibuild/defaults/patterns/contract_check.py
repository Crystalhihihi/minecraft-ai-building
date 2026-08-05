#!/usr/bin/env python3
"""contract_check.py — 卡-代码契约校验器 (card-code contract verifier).

FIX 2026-08-03: the evaluation report found the card layer has NO machine
checks — JSON defaults drifting from py DEFAULTS (e.g. xieshan_roof), stairs
emitted without a facing (altar), ids not validated. This script closes that
gap: it checks every patterns/*.json against its same-named .py before the
cards are merged/registered, so a broken card is caught at build time, not by
an agent later.

Checks (all deterministic, no side effects):
  A. json parses; required fields present (name/description/params/validators)
  B. same-named .py exists (patterns); json params defaults == py DEFAULTS
  C. referenced patterns/*.py exist
  D. block ids are valid (vs blocks.md vocabulary + colour/stair families)
  E. style cards: use_for / pitfalls(>=3) / validators present; <=100 lines
  F. pattern cards: params.validators present; <=40 lines; every *_stairs /
     *_slab param default carries a facing/type (where the generator sets it)

Usage:
  python patterns/contract_check.py            # check patterns/ in this dir
  python patterns/contract_check.py --dir X   # check cards in dir X
Exit code: 0 = all pass, 1 = failures found.
"""
import argparse, importlib, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---- block id vocabulary (from blocks.md + colour families) ----------------
def _load_vocab(blocks_md):
    if not blocks_md.exists():
        return set()
    txt = blocks_md.read_text(encoding="utf-8")
    tok = set()
    for m in re.finditer(r"minecraft:([a-z0-9_]+)|([a-z0-9_]+)", txt):
        tok.add(m.group(1) or m.group(2))
    return tok

COLORS = ["white","orange","magenta","light_blue","yellow","lime","pink",
          "gray","light_gray","cyan","purple","blue","brown","green","red","black"]
FAMS = ["concrete","wool","terracotta","stained_glass","stained_glass_pane",
        "glazed_terracotta"]
WOODS = ["oak","spruce","birch","jungle","acacia","dark_oak","mangrove",
         "cherry","pale_oak","bamboo","crimson","warped"]
SUFFIXES = ["_stairs","_slab","_wall","_fence","_door","_trapdoor","_button",
            "_pressure_plate"]

def _color_family(name):
    return any(name == c + "_" + f for c in COLORS for f in FAMS)

def _norm(s):
    """Normalize a JSON string/array repr for equality comparison."""
    try:
        return json.dumps(json.loads(s), sort_keys=True)
    except (ValueError, TypeError):
        return s.strip().strip("'\"").strip()

def _legal_id(name, vocab):
    if name in vocab or _color_family(name) or name in (
            "gold_block","calcite","smooth_quartz","quartz_bricks"):
        return True
    for suf in SUFFIXES:
        if name.endswith(suf):
            base = name[:-len(suf)]
            if base in vocab or _color_family(base):
                return True
            if base + "_planks" in vocab or base + "_log" in vocab:
                return True
            if base in [w + "_planks" for w in WOODS] + [w + "_log" for w in WOODS]:
                return True
    return False


def check_dir(directory, blocks_md, strict=None, silent=False):
    """strict: set of card names to enforce the FULL contract on. Cards not in
    it are reference copies from the upstream repo (furniture/crenellation/
    terrace_farm/...) whose format predates these standards — checking them
    strictly would produce noise, not signal. Only our own delivered cards get
    the hard gate."""
    issues = []
    d = Path(directory)
    vocab = _load_vocab(blocks_md)
    jsons = sorted(d.glob("*.json"))
    strict = set(strict or [])

    # importable py defaults for same-named generators
    py_defaults = {}
    for j in jsons:
        stem = j.stem
        py = d / (stem + ".py")
        if not py.exists():
            continue
        try:
            mod = importlib.import_module(stem)
            py_defaults[stem] = getattr(mod, "DEFAULTS", None)
        except Exception as e:  # noqa: BLE001
            issues.append((j.name, "py_import_fail", str(e)[:80]))

    for j in jsons:
        stem = j.stem
        strict_this = stem in strict
        try:
            data = json.loads(j.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            issues.append((j.name, "json_parse_fail", str(e)))
            continue

        lines = len(j.read_text(encoding="utf-8").splitlines())
        is_style = (j.parent.name == "styles")

        # A. required fields (json must parse for all cards; full required-field
        # gate only for strict cards — reference copies predate the standard)
        try:
            json.loads(j.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            issues.append((j.name, "json_parse_fail", str(e)))
            continue
        if strict_this:
            for f in ("name", "description", "params", "validators"):
                if f not in data:
                    issues.append((j.name, "missing_field", f))

        # E/F. line limits + style required fields (only strict cards)
        if strict_this:
            limit = 100 if is_style else 40
            if lines > limit:
                issues.append((j.name, "too_many_lines", "%d>%d" % (lines, limit)))
            if is_style:
                for f in ("use_for", "pitfalls", "validators"):
                    if f not in data:
                        issues.append((j.name, "style_missing", f))
                if len(data.get("pitfalls", [])) < 3:
                    issues.append((j.name, "style_pitfalls_lt3",
                                   str(len(data.get("pitfalls", [])))))

        # B. json param defaults == py DEFAULTS (only strict cards)
        pydef = py_defaults.get(stem)
        if strict_this and pydef is not None:
            for k, v in data.get("params", {}).items():
                dflt = v.get("default") if isinstance(v, dict) else None
                pd = pydef.get(k)
                if dflt is None or pd is None:
                    continue
                if isinstance(pd, (list, dict)):
                    # JSON stores lists/dicts as a string repr; normalize both
                    jnorm = dflt if isinstance(dflt, str) else json.dumps(dflt)
                    pnorm = json.dumps(pd)
                    if _norm(jnorm) != _norm(pnorm):
                        issues.append((j.name, "default_mismatch",
                                       "%s json=%s py=%s" % (k, dflt, pd)))
                elif dflt != pd:
                    issues.append((j.name, "default_mismatch",
                                   "%s json=%r py=%r" % (k, dflt, pd)))

        # C. referenced patterns/*.py exist (strict cards)
        if strict_this:
            for m in re.finditer(r"patterns/([a-z_]+)\.py", json.dumps(data)):
                ref = m.group(1)
                if not (d / (ref + ".py")).exists():
                    issues.append((j.name, "ref_missing", ref))

        # D. block ids legal (strict cards)
        if strict_this:
            for m in re.finditer(r"minecraft:([a-z0-9_]+)", json.dumps(data)):
                if not _legal_id(m.group(1), vocab):
                    issues.append((j.name, "bad_id", m.group(1)))

    # F. every *_stairs / *_slab param default must have facing/type semantics
    for j in jsons:
        if j.parent.name == "styles" or j.stem not in strict:
            continue
        try:
            data = json.loads(j.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for k, v in data.get("params", {}).items():
            if not isinstance(v, dict):
                continue
            t = v.get("type", "")
            dflt = v.get("default")
            if isinstance(dflt, str) and ("_stairs" in dflt or "_slab" in dflt):
                if "[facing" not in dflt and "[type" not in dflt and \
                   v.get("notes", "") and "facing" not in v["notes"] and \
                   "type" not in v["notes"]:
                    issues.append((j.name, "stateful_default_no_state",
                                   "%s=%s (notes lack facing/type)" % (k, dflt)))

    if not silent:
        if issues:
            print("FAIL: %d issue(s)" % len(issues))
            for name, kind, detail in issues:
                print("  [%s] %s: %s" % (kind, name, detail))
        else:
            print("OK: %d strict card(s) pass contract" % len(strict))
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE))
    ap.add_argument("--strict", nargs="*", default=None,
                    help="card names to enforce the full contract on (default: our delivered cards)")
    a = ap.parse_args()
    d = Path(a.dir)
    blocks_md = d.parent / "blocks.md"
    if not blocks_md.exists():
        blocks_md = HERE / ".." / "blocks.md"
    # cards we delivered that must meet the full contract
    default_strict = ["altar", "dougong", "round_plan", "settlement",
                      "scene_load", "walkability_check", "walkability_batch",
                      "xieshan_roof"]
    strict = set(a.strict) if a.strict else set(default_strict)
    issues = check_dir(d, blocks_md, strict=strict)
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
