"""
Aggregates Issue #7's required "OBJECTIVE / DIAGNOSTIC METRICS" across all
16 rendered (scenario x method) cells into results/machine_metrics.json.

DIAGNOSTIC ONLY -- per AGENTS.md rule 2 / Issue #7's STAGE-A VERDICT RULE,
nothing here computes or implies a subjective PASS/seamless verdict.

Usage:
    python scripts/compute_metrics.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float  # noqa: E402
from dsp.render_common import load_scenario_context, compute_segments, ms_to_samples  # noqa: E402
from dsp import safety_metrics as sm  # noqa: E402

SCENARIOS = ["R3-A", "R3-B", "R3-C", "R3-D"]
METHODS = ["M0", "M1", "M2", "M3"]

RENDERED_DIR = ROOT / "results" / "rendered"
META_DIR = ROOT / "results" / "render_meta"
OUT_PATH = ROOT / "results" / "machine_metrics.json"


def marker_ground_truth(transition_id: str):
    scenario_ctx = load_scenario_context(transition_id)
    segs = compute_segments(scenario_ctx)  # default 15s/15s -- matches every method's pre-roll length
    sr = segs["sr"]
    out_gt = scenario_ctx["outgoing_ground_truth"]
    in_gt = scenario_ctx["incoming_ground_truth"]
    return {
        "sr": sr,
        "pre_roll_len_smp": segs["onset_smp"] - max(0, segs["onset_smp"] - ms_to_samples(15.0 * 1000, sr)),
        "onset_smp": segs["onset_smp"],
        "entry_smp": segs["entry_smp"],
        "out_marker_sample": out_gt["marker_sample_positions"][0],
        "in_marker_sample": in_gt["marker_sample_positions"][0],
        "marker_freq_hz": out_gt["marker_freq_hz"],
        "marker_duration_s": out_gt["marker_duration_s"],
    }


def compute_cell_metrics(transition_id: str, method: str, gt: dict) -> dict:
    wav_path = RENDERED_DIR / f"{transition_id}_{method}.wav"
    meta_path = META_DIR / f"{transition_id}_{method}.json"
    audio, sr = read_wav_float(wav_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    pre_roll_len = gt["pre_roll_len_smp"]
    applied_ratio = meta.get("applied_tempo_ratio", 1.0) or 1.0
    align_offset_smp = ms_to_samples(meta.get("applied_alignment_offset_ms", 0.0) or 0.0, sr)

    out_expected_smp = pre_roll_len + (gt["out_marker_sample"] - gt["onset_smp"])
    in_expected_smp = pre_roll_len + align_offset_smp + round((gt["in_marker_sample"] - gt["entry_smp"]) / applied_ratio)

    out_marker = sm.detect_marker(audio, sr, out_expected_smp, gt["marker_freq_hz"], gt["marker_duration_s"])
    in_marker = sm.detect_marker(audio, sr, in_expected_smp, gt["marker_freq_hz"], gt["marker_duration_s"])

    beat_alignment_error_ms = None
    if out_marker["detected"] and in_marker["detected"]:
        beat_alignment_error_ms = (in_marker["detected_sample"] - out_marker["detected_sample"]) / sr * 1000.0

    planner_ratio = meta.get("planner_required_tempo_ratio")
    stretch_ratio_error = (
        abs(planner_ratio - applied_ratio) if planner_ratio is not None else None
    )

    handoff_start_smp = pre_roll_len
    handoff_end_smp = pre_roll_len + int(meta.get("overlap_len_samples", 0))

    disc_whole_clip = sm.discontinuity_proxy(audio, sr)
    disc_at_edges = sm.discontinuity_proxy_at_edges(audio, sr, [handoff_start_smp, handoff_end_smp], window_ms=20.0, jump_threshold_sigma=15.0)

    return {
        "transition_id": transition_id,
        "method": method,
        "contract": {
            "rendered_transition_class": meta.get("rendered_transition_class"),
            "planner_allowed_transition_class_set": meta.get("planner_allowed_transition_class_set"),
            "onset_ms": meta.get("onset_ms"),
            "content_end_ms": meta.get("content_end_ms"),
            "entry_ms": meta.get("entry_ms"),
            "applied_tempo_ratio": applied_ratio,
            "planner_required_tempo_ratio": planner_ratio,
            "applied_pitch_shift_semitones": meta.get("applied_pitch_shift_semitones"),
            "applied_alignment_offset_ms": meta.get("applied_alignment_offset_ms"),
        },
        "timing": {
            "beat_alignment_error_ms": beat_alignment_error_ms,
            "downbeat_alignment_error_ms": beat_alignment_error_ms,  # same combined anchor -- see synth.py note
            "outgoing_marker_detection": out_marker,
            "incoming_marker_detection": in_marker,
            "output_duration_s": meta.get("output_duration_s"),
            "overlap_duration_ms": meta.get("overlap_duration_ms"),
            "stretch_ratio_error": stretch_ratio_error,
        },
        "signal_safety": {
            "nan_inf_sample_count": sm.nan_inf_count(audio),
            "peak_dbfs": sm.peak_dbfs(audio),
            "clipped_sample_count": sm.clipped_sample_count(audio),
            "discontinuity_proxy_whole_clip_note": "whole-clip proxy legitimately fires on ordinary drum/percussion transients -- not a splice indicator by itself; see discontinuity_proxy_at_transition_edges for the seam-scoped check",
            "discontinuity_proxy_whole_clip": disc_whole_clip,
            "discontinuity_proxy_at_transition_edges": disc_at_edges,
        },
        "loudness": {
            "overall_rms_dbfs": sm.rms_dbfs(audio),
            "loudness_jump_at_overlap_start_db": sm.loudness_jump_at_handoff_db(audio, sr, handoff_start_smp),
            "loudness_jump_at_overlap_end_db": sm.loudness_jump_at_handoff_db(audio, sr, handoff_end_smp),
        },
        "performance": {
            "render_wall_time_s": meta.get("render_wall_time_s") or meta.get("render_wall_time_s_python_side"),
            "real_time_factor": meta.get("real_time_factor"),
            "note": meta.get("render_wall_time_s_note"),
        },
    }


def main():
    results = []
    for tid in SCENARIOS:
        gt = marker_ground_truth(tid)
        for method in METHODS:
            wav_path = RENDERED_DIR / f"{tid}_{method}.wav"
            if not wav_path.exists():
                print(f"SKIP {tid} {method}: no rendered wav")
                continue
            cell = compute_cell_metrics(tid, method, gt)
            results.append(cell)
            print(f"{tid} {method}: beat_align_err_ms={cell['timing']['beat_alignment_error_ms']} "
                  f"stretch_ratio_err={cell['timing']['stretch_ratio_error']} "
                  f"peak_dbfs={cell['signal_safety']['peak_dbfs']:.2f} "
                  f"clip={cell['signal_safety']['clipped_sample_count']} "
                  f"disc_edges={cell['signal_safety']['discontinuity_proxy_at_transition_edges']['total_discontinuity_count']}")

    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {len(results)} cells to {OUT_PATH}")


if __name__ == "__main__":
    main()
