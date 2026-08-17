"""
P0-M4-R2 PF2/PF3 verifier.

Checks the two sanitized evidence files `render_adapter.py` produces
(PLAN_ONLY and RENDER_AUDIO passes) for internal consistency, privacy
safety, and the specific PF2/PF3 claims this task must prove:

  PF2 -- every one of the frozen 50 pairs loads and renders through the
  EXISTING generic paths with zero failures and zero forbidden-class hits.
  PF3 -- every SIMPLE_CROSSFADE candidate's boundary is sourced from cached
  Stage-B evidence (never a fresh analyzer run), and every pair lacking
  sufficient cached evidence fails closed to NO_SPECIAL_TRANSITION.

Usage:
    python tools/p0m4/narrow_validation/verify_pf2_pf3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN_PATH = HERE / "boundary_evidence_plan_only_sanitized.json"
RENDER_PATH = HERE / "boundary_evidence_render_sanitized.json"

CACHED_EVIDENCE_METHODS_HINT = ("STAGE_B", "NOVELTY_PEAK", "INSTRUMENTAL_TAIL", "OUTRO", "UNKNOWN")

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def scan_for_path_like_leaks(obj, path_keys_seen=None) -> list[str]:
    hits = []

    def walk(v, key_hint=""):
        if isinstance(v, dict):
            for k, vv in v.items():
                walk(vv, k)
        elif isinstance(v, list):
            for vv in v:
                walk(vv, key_hint)
        elif isinstance(v, str):
            if "/" in v or "\\" in v or ":" in v.replace("t_start_ms", ""):
                if key_hint not in ("evidence_type",):
                    hits.append(f"{key_hint}={v!r}")
    walk(obj)
    return hits


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    check("PLAN_ONLY evidence file exists", PLAN_PATH.exists(), str(PLAN_PATH))
    check("RENDER_AUDIO evidence file exists", RENDER_PATH.exists(), str(RENDER_PATH))
    if not (PLAN_PATH.exists() and RENDER_PATH.exists()):
        for name, ok, detail in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return 1

    plan = load(PLAN_PATH)
    render = load(RENDER_PATH)

    check("PLAN_ONLY mode label correct", plan.get("mode") == "PLAN_ONLY")
    check("RENDER_AUDIO mode label correct", render.get("mode") == "RENDER_AUDIO")

    for label, d in (("PLAN_ONLY", plan), ("RENDER_AUDIO", render)):
        check(f"{label}: attempted == 50", d.get("pair_attempted_count") == 50, str(d.get("pair_attempted_count")))
        check(f"{label}: success == 50 (zero failures)", d.get("pair_success_count") == 50, str(d.get("pair_success_count")))
        check(f"{label}: failure == 0", d.get("pair_failure_count") == 0, str(d.get("pair_failure_count")))
        check(f"{label}: zero forbidden-class hits (PF2/NG4 zero-tolerance)", d.get("forbidden_class_hit_count") == 0, str(d.get("forbidden_class_hit_count")))

    plan_classes = {(p["out_id"], p["in_id"]): p["rendered_class"] for p in plan["pairs"]}
    render_classes = {(p["out_id"], p["in_id"]): p.get("rendered_class") for p in render["pairs"]}
    mismatches = [k for k in plan_classes if plan_classes[k] != render_classes.get(k)]
    check(
        "PLAN_ONLY and RENDER_AUDIO agree on rendered_class for every pair",
        len(mismatches) == 0,
        f"{len(mismatches)} mismatches: {mismatches[:5]}",
    )

    simple_crossfade_pairs = [p for p in render["pairs"] if p.get("rendered_class") == "SIMPLE_CROSSFADE"]
    check("at least one SIMPLE_CROSSFADE candidate exists (PF2 exercises the nonzero-overlap path too)", len(simple_crossfade_pairs) > 0, str(len(simple_crossfade_pairs)))

    for p in simple_crossfade_pairs:
        pid = f"{p['out_id']}->{p['in_id']}"
        check(f"{pid}: boundary_source is cached Stage-B evidence, not a fresh analyzer", p.get("boundary_source") == "CACHED_STAGE_B_EXIT_CANDIDATE", str(p.get("boundary_source")))
        check(f"{pid}: exit_structure_confidence is MEDIUM/HIGH (matches accepted eligibility guard)", p.get("exit_structure_confidence") in ("MEDIUM", "HIGH"), str(p.get("exit_structure_confidence")))
        check(f"{pid}: safety diagnostics present with zero NaN/Inf", p.get("safety", {}).get("nan_inf_sample_count") == 0, str(p.get("safety")))
        check(f"{pid}: safety diagnostics present with zero uncontrolled clipping", p.get("safety", {}).get("clipped_sample_count") == 0, str(p.get("safety")))
        check(f"{pid}: outgoing_content_preservation_target present and numeric", isinstance(p.get("outgoing_content_preservation_target"), (int, float)), str(p.get("outgoing_content_preservation_target")))

    no_special = [p for p in render["pairs"] if p.get("rendered_class") == "NO_SPECIAL_TRANSITION"]
    for p in no_special:
        pid = f"{p['out_id']}->{p['in_id']}"
        check(
            f"{pid}: NO_SPECIAL_TRANSITION fail-closed reason recorded (insufficient cached evidence or fallback)",
            p.get("boundary_source") == "FAIL_CLOSED_NO_SUFFICIENT_CACHED_EVIDENCE",
            str(p.get("boundary_source")),
        )

    # Privacy: neither evidence file may contain a path-like string anywhere.
    for label, d in (("PLAN_ONLY", plan), ("RENDER_AUDIO", render)):
        hits = scan_for_path_like_leaks(d)
        check(f"{label}: no path-like strings anywhere in evidence JSON", len(hits) == 0, "; ".join(hits[:10]))

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
