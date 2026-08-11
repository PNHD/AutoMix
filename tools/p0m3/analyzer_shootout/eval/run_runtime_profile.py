"""
PM REVIEW #2 R8 -- separate, non-canonical warm-reuse PERFORMANCE profiling.

Deliberately constructs one model/estimator per candidate and reuses it
across all 8 fixtures, purely to measure the cold-vs-warm wall-clock
difference. This is timing/memory evidence ONLY. It never feeds
correctness fields (beat_timestamps_ms, cue_points_ms, etc.) into
canonical results/all_raw.json or results/metrics.json -- those are
produced exclusively by eval/run_shootout.py calling each candidate's
fresh-per-call run() (see candidates/run_beatnet.py, run_cuedetr.py
module docstrings). Whether this warm-reuse path is even SAFE to use for
correctness is a separate, already-answered question -- see
eval/warm_equivalence_test.py and results/warm_cold_equivalence.json.

Writes results/runtime_profile.json.

Usage (run separately per candidate venv):
    python run_runtime_profile.py --candidate beatnet
    python run_runtime_profile.py --candidate cuedetr
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def load_manifest():
    with open(os.path.join(ROOT, "fixtures", "manifest.json")) as fh:
        return json.load(fh)


def _profile_beatnet(fixture_ids: list[str]) -> list[dict]:
    from candidates.run_beatnet import construct_estimator, run_with_estimator

    manifest = load_manifest()
    by_id = {e["fixture_id"]: e for e in manifest["fixtures"]}

    rows = []
    t_load_start = time.perf_counter()
    estimator = construct_estimator(model=1, mode="offline", inference_model="DBN", device="cpu")
    model_load_wall = time.perf_counter() - t_load_start

    for i, fid in enumerate(fixture_ids):
        path = os.path.normpath(os.path.join(ROOT, "fixtures", by_id[fid]["wav_relpath"]))
        lifecycle = "COLD_MODEL_LOAD_INFERENCE" if i == 0 else "WARM_INFERENCE"
        load_sec = round(model_load_wall, 4) if i == 0 else 0.0
        result = run_with_estimator(estimator, fid, path, estimator_lifecycle=lifecycle,
                                     model_load_wall_sec=load_sec)
        d = result.to_dict()
        rows.append({
            "candidate": "beatnet", "fixture_id": fid, "estimator_lifecycle": lifecycle,
            "model_load_wall_sec": d.get("model_load_wall_sec"),
            "inference_wall_sec": d.get("inference_wall_sec"),
            "total_call_wall_sec": d.get("total_call_wall_sec"),
            "process_peak_rss_mb": d.get("process_peak_rss_mb"),
            "python_tracemalloc_peak_mb": d.get("python_tracemalloc_peak_mb"),
            "memory_measurement_method": d.get("memory_measurement_method"),
            "run_state": d.get("run_state"),
        })
    return rows


def _profile_cuedetr(fixture_ids: list[str]) -> list[dict]:
    from candidates.run_cuedetr import construct_model, run_with_model

    rows = []
    t_load_start = time.perf_counter()
    processor, model, device = construct_model()
    model_load_wall = time.perf_counter() - t_load_start

    for i, fid in enumerate(fixture_ids):
        path = os.path.normpath(os.path.join(ROOT, "local_audio", "mp3", f"{fid}.mp3"))
        lifecycle = "COLD_MODEL_LOAD_INFERENCE" if i == 0 else "WARM_INFERENCE"
        load_sec = round(model_load_wall, 4) if i == 0 else 0.0
        result = run_with_model(processor, model, device, fid, path, estimator_lifecycle=lifecycle,
                                 model_load_wall_sec=load_sec)
        d = result.to_dict()
        rows.append({
            "candidate": "cue_detr", "fixture_id": fid, "estimator_lifecycle": lifecycle,
            "model_load_wall_sec": d.get("model_load_wall_sec"),
            "inference_wall_sec": d.get("inference_wall_sec"),
            "total_call_wall_sec": d.get("total_call_wall_sec"),
            "process_peak_rss_mb": d.get("process_peak_rss_mb"),
            "python_tracemalloc_peak_mb": d.get("python_tracemalloc_peak_mb"),
            "memory_measurement_method": d.get("memory_measurement_method"),
            "run_state": d.get("run_state"),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, choices=["beatnet", "cuedetr"])
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "runtime_profile.json"))
    args = ap.parse_args()

    manifest = load_manifest()
    fixture_ids = [e["fixture_id"] for e in manifest["fixtures"]]

    if args.candidate == "beatnet":
        rows = _profile_beatnet(fixture_ids)
        candidate_key = "beatnet"
    else:
        rows = _profile_cuedetr(fixture_ids)
        candidate_key = "cue_detr"

    existing = {"_scope_note": "PERFORMANCE PROFILING ONLY -- NOT canonical correctness data. "
                                "Produced by deliberately reusing one model/estimator across fixtures. "
                                "See eval/run_runtime_profile.py and eval/warm_equivalence_test.py.",
                "rows": []}
    if os.path.exists(args.out):
        with open(args.out) as fh:
            try:
                existing = json.load(fh)
            except json.JSONDecodeError:
                pass
    existing.setdefault("rows", [])
    existing["rows"] = [r for r in existing["rows"] if r.get("candidate") != candidate_key] + rows

    with open(args.out, "w") as fh:
        json.dump(existing, fh, indent=2)

    print(f"wrote {len(rows)} profiling rows for {candidate_key} to {args.out}")


if __name__ == "__main__":
    main()
