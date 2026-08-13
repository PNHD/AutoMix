"""Deterministic mutation/self-tests for Issue #7 bounded recovery logic."""
from __future__ import annotations

import copy
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pair_gate_audit as audit  # noqa: E402
import recover_analyzer_evidence as recovery  # noqa: E402

checks = 0
failures: list[str] = []


def check(condition: bool, label: str) -> None:
    global checks
    checks += 1
    print(("PASS" if condition else "FAIL") + f" {checks}: {label}")
    if not condition:
        failures.append(label)


def fake_rows(prefix: str) -> list[dict]:
    return [
        {"outgoing_opaque_id": f"RM{i:03d}", "incoming_opaque_id": f"RM{i + 1:03d}", "failed_gates": ["genre"]}
        for i in range(1, 11)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out")
    args = parser.parse_args()
    trace = {
        "v1_near_misses_top10_ranked_by_fewest_failed_gates": fake_rows("V1"),
        "v2_near_misses_top10_ranked_by_fewest_failed_gates": list(reversed(fake_rows("V2"))),
    }
    subset = recovery.derive_subset(trace)
    check(subset["v1_pair_count"] == 10 and subset["v2_pair_count"] == 10, "exact 10+10 pair derivation")
    check(subset["unique_track_count"] == 11, "union is deduplicated")
    mutated = copy.deepcopy(trace)
    mutated["v2_near_misses_top10_ranked_by_fewest_failed_gates"].pop()
    try:
        recovery.derive_subset(mutated)
        rejected = False
    except ValueError:
        rejected = True
    check(rejected, "9-row near-miss mutation fails closed")

    statuses = {gate: audit.PASS for gate in audit.GATE_ORDER}
    statuses["analysis_confidence"] = audit.UNKNOWN_EVIDENCE
    diagnostic = audit.confidence_ledger_diagnostic(statuses)
    check(diagnostic["eligible"], "diagnostic omits only duplicate aggregate confidence")
    check("analysis_confidence" not in diagnostic["gate_order"], "aggregate gate absent from diagnostic order")
    statuses["genre"] = audit.UNKNOWN_EVIDENCE
    diagnostic = audit.confidence_ledger_diagnostic(statuses)
    check(not diagnostic["eligible"] and diagnostic["failed_gates"] == ["genre"], "underlying UNKNOWN genre still fails diagnostic")

    rows = [{"honest_render_candidate_under_existing_r2": False, "unknown_evidence_remaining": ["genre"], "measured_incompatibilities_remaining": []}]
    check(recovery.result_enum(rows) == "ANALYZER_EVIDENCE_STILL_INSUFFICIENT", "unknown-only result enum")
    rows[0]["measured_incompatibilities_remaining"] = ["texture"]
    check(recovery.result_enum(rows) == "ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY", "combined blocker result enum")
    rows[0]["unknown_evidence_remaining"] = []
    check(recovery.result_enum(rows) == "MEASURED_INCOMPATIBILITY_DOMINATES", "measured-only result enum")
    rows[0]["honest_render_candidate_under_existing_r2"] = True
    check(recovery.result_enum(rows) == "REAL_RENDER_CANDIDATE_RECOVERED", "strict recovered candidate result enum")

    track = {
        "duration_ms": 180000.0,
        "sample_rate_analysis_hz": 22050,
        "tempo": {"period_frames": 43.0},
        "beat": {"phase_frame": 0},
        "downbeat": {"phase_of_4": 0},
    }
    oracle = {"downbeat": {"source": "X", "downbeats_ms": [5000 + i * 2000 for i in range(12)], "downbeat_count": 12, "median_downbeat_activation": 0.9, "downbeat_interval_cv": 0.01}}
    classified = recovery.classify_downbeat(track, oracle)
    check(classified["status"] in {"RESOLVED_CONFLICT", "STILL_UNKNOWN"}, "disagreeing oracle is never RESOLVED_HIGH")

    result = {"result": "PASS" if not failures else "FAIL", "assertions": checks, "failures": failures}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"SELFTEST_RESULT={result['result']} ASSERTIONS={checks} FAILURES={len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
