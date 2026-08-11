"""
P0-M3-R1 disposable benchmark harness -- CLI orchestrator.

Runs the negative baselines (always) and whichever candidate runners are
importable in the current environment, against every fixture in
fixtures/manifest.json, scores each against SYNTHETIC_EXACT ground truth,
and writes:
  - results/raw/<candidate>__<fixture>.json  (one AnalyzerResult each)
  - results/metrics.json                      (all computed metrics)
  - results/SUMMARY.md                        (human-readable table)

Usage:
    python run_shootout.py --candidates baselines,beatnet
    python run_shootout.py --candidates baselines   # baselines only, no ML deps needed
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from baselines import scalar_bpm_grid, fixed_n_beat_proxy, energy_onset_heuristic  # noqa: E402
from eval import metrics as M  # noqa: E402


def load_manifest():
    with open(os.path.join(ROOT, "fixtures", "manifest.json")) as fh:
        return json.load(fh)


def beat_period_ms_of(gt: dict) -> float | None:
    bpm = gt.get("bpm")
    if bpm:
        return 60000.0 / bpm
    return None


def score_against_gt(fixture_id: str, gt: dict, result_dict: dict) -> dict:
    out = {"fixture_id": fixture_id, "candidate_id": result_dict["candidate_id"]}
    gt_beats = gt.get("beat_timestamps_ms")
    beat_period_ms = beat_period_ms_of(gt)
    pred_beats = result_dict.get("beat_timestamps_ms")

    if gt_beats and pred_beats:
        out["beat_event_errors"] = M.beat_alignment_errors_ms(pred_beats, gt_beats)
        if beat_period_ms:
            out["beat_fraction"] = M.beat_alignment_fraction(pred_beats, gt_beats, beat_period_ms)

    gt_downbeat_idx = gt.get("downbeat_indices")
    gt_downbeats_ms = [gt_beats[i] for i in gt_downbeat_idx] if (gt_beats and gt_downbeat_idx) else None
    pred_downbeats = result_dict.get("downbeat_timestamps_ms")
    if gt_downbeats_ms and pred_downbeats and beat_period_ms:
        n_bar = gt["meter"]["numerator"] if gt.get("meter") else 4
        bar_period_ms = beat_period_ms * n_bar
        out["downbeat_bar_phase"] = M.downbeat_bar_phase_error(pred_downbeats, gt_downbeats_ms, bar_period_ms)

    pred_positions = result_dict.get("beat_position_in_bar")
    if gt_downbeat_idx and pred_beats and pred_positions:
        n_bar = gt["meter"]["numerator"] if gt.get("meter") else 4
        out["exact_bar_phase"] = M.exact_bar_phase_correctness(pred_positions, gt_beats, pred_beats, n_bar,
                                                                 gt_downbeat_idx)
        pred_meter = max(pred_positions) if pred_positions else None
        out["meter_correct"] = (pred_meter == n_bar) if pred_meter is not None else None
        out["meter_predicted"] = pred_meter
        out["meter_gt"] = n_bar

    gt_phrase = gt.get("phrase_boundaries_ms")
    pred_phrase = result_dict.get("phrase_boundaries_ms")
    if gt_phrase and pred_phrase:
        out["phrase_boundary_distance"] = M.phrase_section_boundary_distance_ms(pred_phrase, gt_phrase)

    gt_sections = gt.get("section_boundaries")
    pred_sections = result_dict.get("section_boundaries")
    if gt_sections and pred_sections:
        gt_starts = [s["t_start_ms"] for s in gt_sections]
        pred_starts = [s["t_start_ms"] for s in pred_sections]
        out["section_boundary_distance"] = M.phrase_section_boundary_distance_ms(pred_starts, gt_starts)

    gt_bpm = gt.get("bpm")
    pred_bpm = result_dict.get("bpm")
    if gt_bpm is not None:
        out["bpm_error"] = M.bpm_error(pred_bpm, gt_bpm)

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="baselines",
                     help="comma-separated: baselines,beatnet,allinone,cuedetr")
    ap.add_argument("--fixtures", default=None, help="comma-separated fixture_id filter, default = all")
    args = ap.parse_args()
    wanted = set(args.candidates.split(","))
    fixture_filter = set(args.fixtures.split(",")) if args.fixtures else None

    manifest = load_manifest()
    raw_dir = os.path.join(HERE, "..", "results", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    all_raw = []
    all_scores = []

    beatnet_mod = None
    if "beatnet" in wanted:
        try:
            beatnet_mod = importlib.import_module("candidates.run_beatnet")
        except Exception as exc:
            print(f"[WARN] beatnet candidate not importable in this environment: {exc}")

    cuedetr_mod = None
    if "cuedetr" in wanted:
        try:
            cuedetr_mod = importlib.import_module("candidates.run_cuedetr")
        except Exception as exc:
            print(f"[WARN] cuedetr candidate not importable in this environment: {exc}")

    for entry in manifest["fixtures"]:
        fid = entry["fixture_id"]
        if fixture_filter and fid not in fixture_filter:
            continue
        gt = entry["ground_truth"]
        wav_path = os.path.normpath(os.path.join(ROOT, "fixtures", entry["wav_relpath"]))

        runs = []
        if "baselines" in wanted:
            runs.append(scalar_bpm_grid.run(fid, gt).to_dict())
            r_fixed = fixed_n_beat_proxy.run(fid, gt, n_beats_per_phrase=32).to_dict()
            runs.append(r_fixed)
            runs.append(energy_onset_heuristic.run(fid, wav_path).to_dict())
        if beatnet_mod is not None:
            print(f"[beatnet] {fid} ...")
            runs.append(beatnet_mod.run(fid, wav_path).to_dict())
        if cuedetr_mod is not None:
            mp3_path = os.path.join(ROOT, "local_audio", "mp3", f"{fid}.mp3")
            print(f"[cuedetr] {fid} ...")
            runs.append(cuedetr_mod.run(fid, mp3_path).to_dict())

        for r in runs:
            out_path = os.path.join(raw_dir, f"{r['candidate_id']}__{fid}.json")
            with open(out_path, "w") as fh:
                json.dump(r, fh, indent=2)

    # Different candidates run in different, mutually-incompatible venvs
    # (see requirements/*.txt), so a single process invocation never sees
    # every candidate. Re-derive the merged view from every raw/*.json file
    # on disk each time, so metrics.json/all_raw.json/SUMMARY.md always
    # reflect the full accumulated result set, not just this invocation's.
    results_dir = os.path.join(HERE, "..", "results")
    gt_by_fixture = {e["fixture_id"]: e["ground_truth"] for e in manifest["fixtures"]}
    all_raw = []
    all_scores = []
    for fname in sorted(os.listdir(raw_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(raw_dir, fname)) as fh:
            r = json.load(fh)
        all_raw.append(r)
        if r["run_state"] == "OK" and r["fixture_id"] in gt_by_fixture:
            all_scores.append(score_against_gt(r["fixture_id"], gt_by_fixture[r["fixture_id"]], r))

    with open(os.path.join(results_dir, "metrics.json"), "w") as fh:
        json.dump(all_scores, fh, indent=2)
    with open(os.path.join(results_dir, "all_raw.json"), "w") as fh:
        json.dump(all_raw, fh, indent=2)

    write_summary_md(manifest, all_raw, all_scores, results_dir)
    print(f"wrote {len(all_raw)} raw results (accumulated), {len(all_scores)} scored entries to {results_dir}")


def write_summary_md(manifest, all_raw, all_scores, results_dir):
    lines = ["# P0-M3-R1 analyzer shootout -- machine-generated summary", ""]
    lines.append(f"Fixtures: {len(manifest['fixtures'])}. Raw runs: {len(all_raw)}. Scored: {len(all_scores)}.")
    lines.append("")
    lines.append("| candidate | fixture | run_state | wall_time_s | error |")
    lines.append("|---|---|---|---|---|")
    for r in all_raw:
        err = (r.get("error") or "").replace("|", "/")[:80]
        lines.append(f"| {r['candidate_id']} | {r['fixture_id']} | {r['run_state']} | "
                      f"{r.get('wall_time_sec')} | {err} |")
    lines.append("")
    lines.append("## Scored metrics")
    lines.append("")
    lines.append("| candidate | fixture | beat_fraction_ok_rate | median_beat_frac_err | "
                  "downbeat_within_10pct_bar | exact_bar_phase_acc | meter_correct | bpm_abs_err_pct |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in all_scores:
        bf = s.get("beat_fraction", {})
        db = s.get("downbeat_bar_phase", {})
        ebp = s.get("exact_bar_phase", {})
        bpme = s.get("bpm_error", {})
        lines.append(
            f"| {s['candidate_id']} | {s['fixture_id']} | "
            f"{bf.get('cond_beat_ok_rate')} | {bf.get('median_beat_fraction_error')} | "
            f"{db.get('within_10pct_bar_rate')} | {ebp.get('exact_bar_phase_accuracy')} | "
            f"{s.get('meter_correct')} | {bpme.get('abs_error_pct')} |"
        )
    with open(os.path.join(results_dir, "SUMMARY.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
