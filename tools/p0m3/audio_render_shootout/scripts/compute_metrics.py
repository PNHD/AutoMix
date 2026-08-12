"""
Aggregates Issue #7's required "OBJECTIVE / DIAGNOSTIC METRICS" across all
16 rendered (scenario x method) cells into results/machine_metrics.json.

DIAGNOSTIC ONLY -- per AGENTS.md rule 2 / Issue #7's STAGE-A VERDICT RULE,
nothing here computes or implies a subjective PASS/seamless verdict.

PM STAGE A REVIEW R3 repair: outgoing and incoming use INDEPENDENTLY
IDENTIFIABLE marker signatures (dsp/markers.py) and are reported as THREE
separate numbers -- `outgoing_anchor_absolute_error_ms`,
`incoming_anchor_absolute_error_ms`, `relative_alignment_error_ms` -- each
with its own detection quality/confidence. `relative_alignment_error_ms` is
computed ONLY when BOTH sides are confidently detected; otherwise it is
reported as `None`/`"UNKNOWN"`, never a fabricated `0.0` (the exact prior
defect: two detect_marker() calls using the SAME template could lock onto
the same peak and mechanically difference to 0.0 even when both individual
detections were ~200+ms off).

Follow-up finding during this repair: equal-power crossfade gain is
EXACTLY 0 at the very first sample of the incoming side's fade-in
(`sin(0) == 0`), which is precisely where the incoming alignment anchor
sits by definition -- so an incoming marker is always silenced at that
instant in the FINAL gain-mixed render, regardless of whether the renderer
positioned it correctly. This is a real, expected property of equal-power
crossfades, not a placement bug, but it makes the final mixed render an
unreliable place to empirically verify incoming-side alignment. Marker
detection is therefore run against `results/premix_diag/*_premix.wav`
(`dsp.render_common.save_premix_diagnostic` -- the exact PRE-GAIN
`outgoing_overlap`/`incoming_overlap` buffers each renderer computed,
after stretch/alignment-shift but before `dsp.mixing.mix_overlap`
multiplies by the crossfade curve). Both markers are authored at sample 0
of their respective overlap buffer, so `expected_sample = 0` for both,
and the RELATIVE error between them is directly meaningful (both premix
buffers start at the identical output-timeline instant by construction of
`dsp.mixing.assemble_transition_render`). Signal-safety/loudness/
discontinuity diagnostics still run against the FINAL mixed render, since
those legitimately describe the actual deliverable.

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
from dsp.markers import marker_spec_for_role  # noqa: E402

SCENARIOS = ["R3-A", "R3-B", "R3-C", "R3-D"]
METHODS = ["M0", "M1", "M2", "M3"]

RENDERED_DIR = ROOT / "results" / "rendered"
META_DIR = ROOT / "results" / "render_meta"
PREMIX_DIR = ROOT / "results" / "premix_diag"
OUT_PATH = ROOT / "results" / "machine_metrics.json"


def marker_ground_truth(transition_id: str):
    scenario_ctx = load_scenario_context(transition_id, variant="diagnostic")
    segs = compute_segments(scenario_ctx)  # default 15s/15s -- matches every method's pre-roll length
    sr = segs["sr"]
    out_gt = scenario_ctx["outgoing_ground_truth"]
    in_gt = scenario_ctx["incoming_ground_truth"]

    # R3 repair item 4: ground-truth sample positions must be converted
    # into the ACTUAL render sample-rate domain. This project's fixtures
    # are authored directly at the canonical render rate (44100Hz
    # throughout, post R1 repair), so the "conversion" is an identity
    # assertion here -- made explicit rather than silently assumed.
    assert out_gt["sr"] == sr, f"{transition_id}: outgoing ground-truth sr {out_gt['sr']} != render sr {sr}"
    assert in_gt["sr"] == sr, f"{transition_id}: incoming ground-truth sr {in_gt['sr']} != render sr {sr}"

    return {
        "sr": sr,
        "out_marker_spec": out_gt["marker_spec"] or marker_spec_for_role("outgoing"),
        "in_marker_spec": in_gt["marker_spec"] or marker_spec_for_role("incoming"),
    }


def compute_cell_metrics(transition_id: str, method: str, gt: dict) -> dict:
    wav_path = RENDERED_DIR / f"{transition_id}_{method}.wav"
    meta_path = META_DIR / f"{transition_id}_{method}.json"
    audio, sr = read_wav_float(wav_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert sr == gt["sr"], f"{transition_id}_{method}: rendered sr {sr} != ground-truth sr {gt['sr']}"

    # Both markers are authored at sample 0 of their respective PRE-GAIN
    # overlap buffer (dsp.render_common.save_premix_diagnostic) -- see the
    # module docstring for why detection runs here, not on the final
    # gain-mixed render.
    out_premix_path = PREMIX_DIR / f"{transition_id}_{method}_outgoing_premix.wav"
    in_premix_path = PREMIX_DIR / f"{transition_id}_{method}_incoming_premix.wav"
    out_premix, out_premix_sr = read_wav_float(out_premix_path)
    in_premix, in_premix_sr = read_wav_float(in_premix_path)
    assert out_premix_sr == sr and in_premix_sr == sr, f"{transition_id}_{method}: premix diagnostic sr mismatch"

    out_marker = sm.detect_marker(out_premix, sr, 0, gt["out_marker_spec"], search_window_ms=150.0)
    in_marker = sm.detect_marker(in_premix, sr, 0, gt["in_marker_spec"], search_window_ms=150.0)

    outgoing_anchor_absolute_error_ms = out_marker["error_ms"]  # None if not confidently detected
    incoming_anchor_absolute_error_ms = in_marker["error_ms"]

    relative_alignment_error_ms = None
    relative_alignment_quality = "UNKNOWN_INSUFFICIENT_CONFIDENT_DETECTIONS"
    if out_marker["confident"] and in_marker["confident"]:
        relative_alignment_error_ms = (in_marker["detected_sample"] - out_marker["detected_sample"]) / sr * 1000.0
        relative_alignment_quality = "COMPUTED_FROM_TWO_CONFIDENT_DISTINCT_MARKER_DETECTIONS"

    applied_ratio = meta.get("applied_tempo_ratio", 1.0) or 1.0
    planner_ratio = meta.get("planner_required_tempo_ratio")
    stretch_ratio_error = (
        abs(planner_ratio - applied_ratio) if planner_ratio is not None else None
    )

    # Handoff/discontinuity/loudness diagnostics below legitimately still
    # use the FINAL mixed render (they describe the actual deliverable,
    # not the pre-gain marker-detection concern above) -- pre_roll_len is
    # recomputed here directly from the onset ms already recorded in this
    # cell's own metadata, consistent with dsp.render_common.PRE_ROLL_S.
    onset_smp = ms_to_samples(meta["onset_ms"], sr)
    pre_roll_len = onset_smp - max(0, onset_smp - ms_to_samples(15.0 * 1000, sr))
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
            "canonical_sample_rate": meta.get("canonical_sample_rate"),
            "channels": meta.get("channels"),
        },
        "timing": {
            "outgoing_anchor_absolute_error_ms": outgoing_anchor_absolute_error_ms,
            "incoming_anchor_absolute_error_ms": incoming_anchor_absolute_error_ms,
            "relative_alignment_error_ms": relative_alignment_error_ms,
            "relative_alignment_quality": relative_alignment_quality,
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
        "signalsmith_job_sidecar": meta.get("signalsmith_job_sidecar"),
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
            t = cell["timing"]
            print(f"{tid} {method}: out_abs_err_ms={t['outgoing_anchor_absolute_error_ms']} "
                  f"in_abs_err_ms={t['incoming_anchor_absolute_error_ms']} "
                  f"rel_err_ms={t['relative_alignment_error_ms']} ({t['relative_alignment_quality']}) "
                  f"out_quality={cell['timing']['outgoing_marker_detection']['quality']} "
                  f"in_quality={cell['timing']['incoming_marker_detection']['quality']} "
                  f"stretch_ratio_err={t['stretch_ratio_error']} "
                  f"peak_dbfs={cell['signal_safety']['peak_dbfs']:.2f} "
                  f"clip={cell['signal_safety']['clipped_sample_count']}")

    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {len(results)} cells to {OUT_PATH}")


if __name__ == "__main__":
    main()
