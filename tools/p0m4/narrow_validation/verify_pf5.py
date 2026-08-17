"""
P0-M4-R2 PF5 verifier (part 2) -- checks the NG2 comparator executability
evidence file produced by `ng2_comparator_proof.py` against the real
30-pair NG2 subset.

Usage:
    python tools/p0m4/narrow_validation/verify_pf5.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE_PATH = HERE / "ng2_comparator_evidence_sanitized.json"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def main() -> int:
    check("PF5 evidence file exists", EVIDENCE_PATH.exists(), str(EVIDENCE_PATH))
    if not EVIDENCE_PATH.exists():
        for name, ok, detail in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return 1

    d = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    check("ng2_total == 30", d.get("ng2_total") == 30, str(d.get("ng2_total")))
    check("ng2_success == 30 (zero backfill needed)", d.get("ng2_success") == 30, str(d.get("ng2_success")))
    check("ng2_excluded_unrenderable == 0", d.get("ng2_excluded_unrenderable") == 0, str(d.get("ng2_excluded_unrenderable")))
    check("ng2_holdout_success == 9", d.get("ng2_holdout_success") == 9, str(d.get("ng2_holdout_success")))
    check("ng2_dev_success == 21", d.get("ng2_dev_success") == 21, str(d.get("ng2_dev_success")))

    pairs = d.get("pairs", [])
    check("exactly 30 pair records", len(pairs) == 30, str(len(pairs)))
    for p in pairs:
        pid = f"{p.get('out_id')}->{p.get('in_id')}"
        check(f"{pid}: status SUCCESS", p.get("status") == "SUCCESS", str(p.get("status")))
        check(f"{pid}: crossfade_duration_ms within [20000,45000]", 20000 <= p.get("crossfade_duration_ms", -1) <= 45000, str(p.get("crossfade_duration_ms")))
        check(f"{pid}: entry_ms == 0", p.get("entry_ms") == 0.0, str(p.get("entry_ms")))
        check(f"{pid}: zero NaN/Inf", p.get("safety", {}).get("nan_inf_sample_count") == 0, str(p.get("safety")))
        check(f"{pid}: zero uncontrolled clipping", p.get("safety", {}).get("clipped_sample_count") == 0, str(p.get("safety")))

    # Privacy: no path-like strings anywhere.
    raw = json.dumps(d)
    leak_hits = [tok for tok in ("\\\\", "C:/", "C:\\\\") if tok in raw]
    check("no path-like strings in PF5 evidence JSON", len(leak_hits) == 0, str(leak_hits))

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
