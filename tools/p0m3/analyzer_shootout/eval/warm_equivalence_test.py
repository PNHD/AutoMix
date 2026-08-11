"""
PM REVIEW #2 R8 -- same-fixture cold-vs-warm equivalence test.

Answers exactly one question per candidate: if a model/estimator is
reused (warm) across a DIFFERENT fixture first, then run again on THE
SAME fixture, is its output identical to a freshly-constructed
estimator run on that fixture alone (cold)?

This is deliberately narrower than the aggregate "run 8 different
fixtures with one warm estimator" experiment (that lives in
eval/run_runtime_profile.py and only measures wall-clock time, never
correctness) -- it isolates state-carryover on ONE fixed input, so any
difference found is unambiguously caused by prior-call state, not by
which audio file was processed.

Writes results/warm_cold_equivalence.json. Never feeds canonical
all_raw.json/metrics.json.

Usage (run separately per candidate venv):
    python warm_equivalence_test.py --candidate beatnet
    python warm_equivalence_test.py --candidate cuedetr
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from eval import metrics as M  # noqa: E402


def load_manifest():
    with open(os.path.join(ROOT, "fixtures", "manifest.json")) as fh:
        return json.load(fh)


def _beatnet_case(target_fixture_id: str, warm_up_fixture_id: str) -> dict:
    from candidates.run_beatnet import construct_estimator, run_with_estimator

    manifest = load_manifest()
    by_id = {e["fixture_id"]: e for e in manifest["fixtures"]}
    target_path = os.path.normpath(os.path.join(ROOT, "fixtures", by_id[target_fixture_id]["wav_relpath"]))
    warm_path = os.path.normpath(os.path.join(ROOT, "fixtures", by_id[warm_up_fixture_id]["wav_relpath"]))

    # COLD: brand-new estimator, used exactly once, on the target fixture.
    cold_estimator = construct_estimator(model=1, mode="offline", inference_model="DBN", device="cpu")
    cold_result = run_with_estimator(cold_estimator, target_fixture_id, target_path,
                                      estimator_lifecycle="EQUIVALENCE_TEST_COLD")

    # WARM: a fresh estimator is first "used" on a DIFFERENT fixture, then
    # reused (same Python object) on the SAME target fixture.
    warm_estimator = construct_estimator(model=1, mode="offline", inference_model="DBN", device="cpu")
    _ = run_with_estimator(warm_estimator, warm_up_fixture_id, warm_path,
                            estimator_lifecycle="EQUIVALENCE_TEST_WARMUP")
    warm_result = run_with_estimator(warm_estimator, target_fixture_id, target_path,
                                      estimator_lifecycle="EQUIVALENCE_TEST_WARM_REUSED")

    return _compare_beatnet(cold_result.to_dict(), warm_result.to_dict(), by_id[target_fixture_id]["ground_truth"])


def _compare_beatnet(cold: dict, warm: dict, gt: dict) -> dict:
    fields_equal = {}
    for field_name in ("beat_timestamps_ms", "beat_position_in_bar", "downbeat_timestamps_ms", "meter_numerator"):
        fields_equal[field_name] = cold.get(field_name) == warm.get(field_name)

    beat_period_ms = 60000.0 / gt["bpm"] if gt.get("bpm") else None
    cold_metrics = {}
    warm_metrics = {}
    if beat_period_ms and cold.get("beat_timestamps_ms") and warm.get("beat_timestamps_ms"):
        cold_metrics["beat_fraction"] = M.beat_alignment_fraction(cold["beat_timestamps_ms"], gt["beat_timestamps_ms"], beat_period_ms)
        warm_metrics["beat_fraction"] = M.beat_alignment_fraction(warm["beat_timestamps_ms"], gt["beat_timestamps_ms"], beat_period_ms)
    gt_downbeat_idx = gt.get("downbeat_indices") or []
    if cold.get("beat_position_in_bar") and cold.get("beat_timestamps_ms"):
        n_bar = gt["meter"]["numerator"] if gt.get("meter") else 4
        cold_metrics["exact_bar_phase"] = M.exact_bar_phase_correctness(
            cold["beat_position_in_bar"], gt["beat_timestamps_ms"], cold["beat_timestamps_ms"], n_bar, gt_downbeat_idx)
        warm_metrics["exact_bar_phase"] = M.exact_bar_phase_correctness(
            warm["beat_position_in_bar"], gt["beat_timestamps_ms"], warm["beat_timestamps_ms"], n_bar, gt_downbeat_idx)

    derived_metrics_equal = (cold_metrics == warm_metrics)
    overall_equivalent = all(fields_equal.values()) and derived_metrics_equal

    return {
        "candidate": "beatnet",
        "fields_equal": fields_equal,
        "derived_metrics_equal": derived_metrics_equal,
        "cold_derived_metrics": cold_metrics,
        "warm_derived_metrics": warm_metrics,
        "cold_raw": {k: cold.get(k) for k in ("beat_timestamps_ms", "beat_position_in_bar", "downbeat_timestamps_ms", "meter_numerator")},
        "warm_raw": {k: warm.get(k) for k in ("beat_timestamps_ms", "beat_position_in_bar", "downbeat_timestamps_ms", "meter_numerator")},
        "verdict": "EQUIVALENT" if overall_equivalent else "NOT_EQUIVALENT",
    }


def _cuedetr_case(target_fixture_id: str, warm_up_fixture_id: str) -> dict:
    from candidates.run_cuedetr import construct_model, run_with_model

    manifest = load_manifest()
    by_id = {e["fixture_id"]: e for e in manifest["fixtures"]}
    target_path = os.path.normpath(os.path.join(ROOT, "local_audio", "mp3", f"{target_fixture_id}.mp3"))
    warm_path = os.path.normpath(os.path.join(ROOT, "local_audio", "mp3", f"{warm_up_fixture_id}.mp3"))

    processor_c, model_c, device_c = construct_model()
    cold_result = run_with_model(processor_c, model_c, device_c, target_fixture_id, target_path,
                                  estimator_lifecycle="EQUIVALENCE_TEST_COLD")

    processor_w, model_w, device_w = construct_model()
    _ = run_with_model(processor_w, model_w, device_w, warm_up_fixture_id, warm_path,
                        estimator_lifecycle="EQUIVALENCE_TEST_WARMUP")
    warm_result = run_with_model(processor_w, model_w, device_w, target_fixture_id, target_path,
                                  estimator_lifecycle="EQUIVALENCE_TEST_WARM_REUSED")

    cold = cold_result.to_dict()
    warm = warm_result.to_dict()
    fields_equal = {}
    for field_name in ("raw_cue_points_ms", "raw_cue_score", "cue_points_ms", "cue_score"):
        fields_equal[field_name] = cold.get(field_name) == warm.get(field_name)
    overall_equivalent = all(fields_equal.values())
    return {
        "candidate": "cue_detr",
        "fields_equal": fields_equal,
        "cold_raw": {k: cold.get(k) for k in ("raw_cue_points_ms", "raw_cue_score")},
        "warm_raw": {k: warm.get(k) for k in ("raw_cue_points_ms", "raw_cue_score")},
        "verdict": "EQUIVALENT" if overall_equivalent else "NOT_EQUIVALENT",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, choices=["beatnet", "cuedetr"])
    ap.add_argument("--target-fixture", default="FIX-A-constant-120bpm-4-4")
    ap.add_argument("--warmup-fixture", default="FIX-D-4-4-reference")
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "warm_cold_equivalence.json"))
    args = ap.parse_args()

    if args.candidate == "beatnet":
        case = _beatnet_case(args.target_fixture, args.warmup_fixture)
    else:
        case = _cuedetr_case(args.target_fixture, args.warmup_fixture)

    case["target_fixture"] = args.target_fixture
    case["warmup_fixture"] = args.warmup_fixture
    case["methodology"] = (
        "COLD = brand-new model/estimator constructed and run exactly once, on target_fixture only. "
        "WARM = a brand-new model/estimator is first run once on warmup_fixture (a DIFFERENT file), "
        "then the SAME object is reused to run target_fixture again. Any difference between cold and "
        "warm output on the IDENTICAL target_fixture input is caused by prior-call state carried by the "
        "reused object, not by input variation."
    )

    # Merge with any existing file so both candidates' results accumulate
    # (each candidate runs in its own venv/process, same pattern as
    # eval/run_shootout.py's raw-directory merge).
    existing = []
    if os.path.exists(args.out):
        with open(args.out) as fh:
            try:
                existing = json.load(fh)
            except json.JSONDecodeError:
                existing = []
    if not isinstance(existing, list):
        existing = []
    existing = [c for c in existing if c.get("candidate") != case["candidate"]]
    existing.append(case)

    with open(args.out, "w") as fh:
        json.dump(existing, fh, indent=2)

    print(f"[{case['candidate']}] verdict={case['verdict']}")
    print(json.dumps(case, indent=2)[:2000])


if __name__ == "__main__":
    main()
