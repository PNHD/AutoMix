"""
AC7 self-test: "renderer fails closed on missing FULL_DJ alignment fields."

None of this pass's actual scenario fixtures (A/B/C) exercise the missing-
field path (their R2 boundaries genuinely carry full alignment evidence on
both sides, correctly), so this script proves the guard is REAL by
mutating a copy of a real, accepted PlannerDecision (R3-B's) to null out
each required field one at a time and asserting
dsp.render_common.require_full_dj_alignment_fields raises
PlannerContractError every time -- and does NOT raise on the untouched
original.

Usage:
    python scripts/selftest_fail_closed.py
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.render_common import require_full_dj_alignment_fields, REQUIRED_FULL_DJ_ALIGNMENT_FIELDS, PlannerContractError  # noqa: E402

DECISION_PATH = ROOT / "fixtures" / "planner_decisions" / "R3-B.json"


def main():
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    assert "FULL_DJ_BLEND" in decision["allowed_transition_class_set"], "R3-B must actually allow FULL_DJ_BLEND for this test to be meaningful"

    failures = []

    try:
        require_full_dj_alignment_fields(decision)
        print("OK: unmutated R3-B decision passes (has full alignment evidence)")
    except PlannerContractError as e:
        failures.append(f"unmutated decision unexpectedly raised: {e}")

    for field in REQUIRED_FULL_DJ_ALIGNMENT_FIELDS:
        mutated = copy.deepcopy(decision)
        mutated[field] = None if field.endswith("_ms") else "NOT_APPLICABLE"
        try:
            require_full_dj_alignment_fields(mutated)
            failures.append(f"missing '{field}' did NOT raise PlannerContractError -- fail-closed guard is broken")
        except PlannerContractError:
            print(f"OK: missing '{field}' correctly raises PlannerContractError (fail-closed)")

    mutated = copy.deepcopy(decision)
    mutated["required_tempo_ratio"] = None
    try:
        require_full_dj_alignment_fields(mutated)
        failures.append("missing 'required_tempo_ratio' did NOT raise -- fail-closed guard is broken")
    except PlannerContractError:
        print("OK: missing 'required_tempo_ratio' correctly raises PlannerContractError (fail-closed)")

    print(f"\n{'ALL SELF-TESTS PASS' if not failures else f'{len(failures)} SELF-TEST(S) FAILED'}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
