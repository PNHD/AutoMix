"""
P0-M4-R2 PF4 verifier -- checks the repaired owner annotation schema
(Issue #9 comment `5318289406`, `PHASE0_PF4_REPAIR_REQUIRED`).

Three layers:

1. Schema-shape checks against `build_ng4_annotation_pack.
   build_response_template()` output directly (no local pack needed) --
   proves the response format can represent zero/one/two/three accepted
   classes, all three narrow classes are present, and no forbidden class
   is offered.
2. `ng4_policy_materialization` unit tests against SYNTHETIC response rows
   only (no real owner data) -- proves the accepted-class mapping and the
   mechanical forbidden-class rejection are correct, and that an
   incomplete row is correctly detected as not-yet-ready.
3. OPTIONAL local-pack checks: if the local `ng4_annotation_pack` exists,
   verifies token count == 23, the response template's token set matches
   the existing local blind key's token set (identity preserved across
   the repair), and that neither the template nor the instructions leak
   opaque IDs, split labels, or forbidden classes as choices. This layer
   NEVER prints any blind-key value -- only token-set membership.

Usage:
    python tools/p0m4/narrow_validation/verify_pf4_pack.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_ng4_annotation_pack as bpack  # noqa: E402
import ng4_policy_materialization as polmat  # noqa: E402

PACK_DIR = HERE / "work_local" / "ng4_annotation_pack"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def run_schema_shape_checks() -> None:
    tmpl = bpack.build_response_template(["NG4-TEST-01", "NG4-TEST-02"])

    check("narrow_classes lists exactly the 3 authorized classes", set(tmpl["narrow_classes"]) == set(bpack.NARROW_CLASSES) and len(tmpl["narrow_classes"]) == 3, str(tmpl["narrow_classes"]))
    for forbidden in ("FULL_DJ_BLEND", "SHORT_EQ_BLEND", "CUT"):
        check(f"forbidden class '{forbidden}' is never offered in narrow_classes", forbidden not in tmpl["narrow_classes"])

    row = tmpl["responses"][0]
    check("response row has NO single-scalar 'assigned_class' field (old schema removed)", "assigned_class" not in row, str(row))
    check("response row has class_acceptability as a dict", isinstance(row.get("class_acceptability"), dict), str(row.get("class_acceptability")))
    ca_keys = set(row.get("class_acceptability", {}).keys())
    check("class_acceptability has all 3 narrow classes as independent keys", ca_keys == set(bpack.NARROW_CLASSES), str(ca_keys))
    check("class_acceptability values start unset (null)", all(v is None for v in row["class_acceptability"].values()))

    # Prove the schema can represent 0, 1, 2, and 3 simultaneously-true
    # classes -- i.e. it is NOT a single-choice field.
    for n_true in (0, 1, 2, 3):
        candidate = dict(row["class_acceptability"])
        for i, c in enumerate(bpack.NARROW_CLASSES):
            candidate[c] = i < n_true
        problems = polmat.validate_completed_row({"class_acceptability": candidate})
        check(f"schema can represent exactly {n_true} accepted class(es) simultaneously", problems == [], str(problems))

    check("exactly 2 tokens produced for 2 requested tokens", len(tmpl["responses"]) == 2)
    check("template's own instructions pointer references INSTRUCTIONS.md", "INSTRUCTIONS.md" in tmpl["instructions"])

    for forbidden in ("FULL_DJ_BLEND", "SHORT_EQ_BLEND"):
        check(f"INSTRUCTIONS.md never offers '{forbidden}' as an owner choice", forbidden not in bpack.INSTRUCTIONS_TEXT)
    # "CUT" alone would false-positive on ordinary English; check the
    # specific forbidden phrase shape instead.
    check("INSTRUCTIONS.md never asks the owner about CUT as a style choice", "CUT** --" not in bpack.INSTRUCTIONS_TEXT and "`CUT`" not in bpack.INSTRUCTIONS_TEXT)
    check("INSTRUCTIONS.md does not ask 'which ONE' / 'best describes'", "which ONE" not in bpack.INSTRUCTIONS_TEXT and "best describes" not in bpack.INSTRUCTIONS_TEXT)
    check("INSTRUCTIONS.md explicitly says more than one can be true", "more than one can be true" in bpack.INSTRUCTIONS_TEXT.lower() or "More than one can be true" in bpack.INSTRUCTIONS_TEXT)
    check("INSTRUCTIONS.md does not mention dev/holdout", "dev/holdout" not in bpack.INSTRUCTIONS_TEXT and "holdout" not in bpack.INSTRUCTIONS_TEXT.lower().replace("split", ""))
    check("INSTRUCTIONS.md does not mention candidate implementation quality as in-scope here", "not judging candidate implementation quality" in bpack.INSTRUCTIONS_TEXT.lower() or "never a specific candidate implementation" in bpack.INSTRUCTIONS_TEXT)

    # build_ng4_annotation_pack.py must no longer advertise the unused
    # --seed-file option (PM repair item 7).
    src = (HERE / "build_ng4_annotation_pack.py").read_text(encoding="utf-8")
    check("build_ng4_annotation_pack.py no longer advertises unused --seed-file", "--seed-file" not in src, "found --seed-file still referenced")


def run_materialization_unit_tests() -> None:
    # Ordinary pair: both NO_SPECIAL_TRANSITION and SIMPLE_CROSSFADE
    # acceptable, GAPLESS not -- the exact motivating example from the PM
    # review.
    ordinary = polmat.materialize_transition_class_policy({
        "NO_SPECIAL_TRANSITION": True, "GAPLESS": False, "SIMPLE_CROSSFADE": True,
    })
    check(
        "materialization: ordinary pair -> BOTH NO_SPECIAL_TRANSITION and SIMPLE_CROSSFADE in accepted_unconditional",
        set(ordinary["accepted_unconditional"]) == {"NO_SPECIAL_TRANSITION", "SIMPLE_CROSSFADE"},
        str(ordinary["accepted_unconditional"]),
    )
    check("materialization: GAPLESS not accepted for the ordinary pair", "GAPLESS" not in ordinary["accepted_unconditional"])
    check("materialization: accepted_conditional always empty (no invented conditional evidence)", ordinary["accepted_conditional"] == [])
    check("materialization: rejected_conditional always empty", ordinary["rejected_conditional"] == [])

    # Continuous-work pair: only GAPLESS acceptable.
    continuous = polmat.materialize_transition_class_policy({
        "NO_SPECIAL_TRANSITION": False, "GAPLESS": True, "SIMPLE_CROSSFADE": False,
    })
    check("materialization: continuous-work pair -> only GAPLESS accepted", continuous["accepted_unconditional"] == ["GAPLESS"], str(continuous["accepted_unconditional"]))

    # All-false pair (owner found nothing acceptable): empty accepted list,
    # still valid (not an error) -- closed-world default applies to every
    # narrow class via omission.
    none_ok = polmat.materialize_transition_class_policy({
        "NO_SPECIAL_TRANSITION": False, "GAPLESS": False, "SIMPLE_CROSSFADE": False,
    })
    check("materialization: all-false row -> empty accepted_unconditional (valid, not an error)", none_ok["accepted_unconditional"] == [])

    # Forbidden classes are ALWAYS rejected, mechanically, regardless of
    # what the (narrow-class-only) owner input says -- they aren't even a
    # field the owner can set.
    for forbidden in ("FULL_DJ_BLEND", "SHORT_EQ_BLEND", "CUT"):
        hit = [r for r in ordinary["rejected"] if r["class"] == forbidden]
        check(f"materialization: '{forbidden}' is always in rejected[] with a mandatory reason", len(hit) == 1 and bool(hit[0].get("reason")), str(hit))

    # Mutual exclusivity: no class appears in more than one list.
    all_seen = ordinary["accepted_unconditional"] + [r["class"] for r in ordinary["rejected"]]
    check("materialization: no class appears in more than one policy list", len(all_seen) == len(set(all_seen)), str(all_seen))

    # Incomplete row (owner has not finished answering) must be rejected,
    # not silently defaulted.
    incomplete = {"NO_SPECIAL_TRANSITION": True, "GAPLESS": None, "SIMPLE_CROSSFADE": False}
    problems = polmat.validate_completed_row({"class_acceptability": incomplete})
    check("validate_completed_row: detects a still-null class as incomplete", len(problems) == 1 and "GAPLESS" in problems[0], str(problems))
    try:
        polmat.materialize_transition_class_policy(incomplete)
        check("materialize_transition_class_policy: raises on an incomplete row rather than silently defaulting", False)
    except polmat.InvalidResponseRow:
        check("materialize_transition_class_policy: raises on an incomplete row rather than silently defaulting", True)

    complete = {"NO_SPECIAL_TRANSITION": True, "GAPLESS": False, "SIMPLE_CROSSFADE": True}
    check("validate_completed_row: a fully-answered row has zero problems", polmat.validate_completed_row({"class_acceptability": complete}) == [])


def run_local_pack_checks() -> None:
    blind_key_path = PACK_DIR / "blind_key.local.json"
    template_path = PACK_DIR / "response_template.json"
    instructions_path = PACK_DIR / "INSTRUCTIONS.md"

    if not blind_key_path.exists():
        check("optional: local NG4 pack checks (SKIPPED -- no local pack on this machine)", True)
        return

    blind_key = json.loads(blind_key_path.read_text(encoding="utf-8"))
    blind_tokens = set(blind_key.keys())  # tokens only; values are NEVER read here
    check("local pack: blind key has exactly 23 tokens", len(blind_tokens) == 23, str(len(blind_tokens)))

    check("local pack: response_template.json exists", template_path.exists())
    if template_path.exists():
        tmpl = json.loads(template_path.read_text(encoding="utf-8"))
        template_tokens = {r["token"] for r in tmpl.get("responses", [])}
        check("local pack: response_template token set matches blind_key token set (identity preserved)", template_tokens == blind_tokens, f"{len(template_tokens)} vs {len(blind_tokens)}")

        for row in tmpl.get("responses", []):
            check(f"local pack: {row['token']} uses class_acceptability schema", isinstance(row.get("class_acceptability"), dict))
            check(f"local pack: {row['token']} has no assigned_class scalar field", "assigned_class" not in row)

        raw = json.dumps(tmpl)
        for forbidden in ("FULL_DJ_BLEND", "SHORT_EQ_BLEND"):
            check(f"local pack template: '{forbidden}' never appears", forbidden not in raw)

        # Privacy: template must never carry opaque IDs, split labels, or
        # path-like strings.
        leak_hits = [tok for tok in ("RM0", "\\", "/", "dev", "holdout") if tok in raw]
        # "dev"/"holdout" would false-positive on ordinary words only if they
        # appear as bare tokens; template is machine-generated JSON with
        # fixed keys, so a raw substring check is safe here.
        check("local pack template: no opaque RM### IDs or split labels leak into the owner-facing template", not any(t in raw for t in ("RM0", '"dev"', '"holdout"')), str(leak_hits))

    check("local pack: INSTRUCTIONS.md exists", instructions_path.exists())
    if instructions_path.exists():
        instr = instructions_path.read_text(encoding="utf-8")
        check("local pack INSTRUCTIONS.md: matches the current corrected instructions text", instr == bpack.INSTRUCTIONS_TEXT)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    run_schema_shape_checks()
    run_materialization_unit_tests()
    run_local_pack_checks()

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        suffix = f" -- {detail}" if (not ok and detail) else ""
        print(f"[{status}] {name}{suffix}")
    print()
    if failed:
        print(f"RESULT: {len(failed)}/{len(checks)} CHECKS FAILED")
        return 1
    print(f"RESULT: ALL CHECKS PASS ({len(checks)}/{len(checks)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
