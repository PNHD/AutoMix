"""
PM OWNER LISTENING DIRECTION UPDATE, Task 2 "TEMPO-RAMP RESULTS":
renders a MATCH_AND_RETURN_TO_NATIVE comparator (smooth ramp back to
native tempo after handoff) against a MATCH_INCOMING_DURING_OVERLAP
comparator (stable matched tempo through the whole listening excerpt --
identical to the existing M2 diagnostic render) for scenario R3-B (the
only scenario whose tempo mode resolves to MATCH_AND_RETURN_TO_NATIVE
with a non-trivial ratio worth demonstrating; R3-C's HALF_DOUBLE residual
is much smaller and R3-A needs no correction at all -- see
dsp/tempo_modes.py).

Reuses the ALREADY-FETCHED Signalsmith stretch output sitting in
serve_tmp/ from the prior diagnostic M2 render (no new browser round-trip
needed) -- both comparators consume the exact same matched-tempo stretched
buffer, differing ONLY in whether the post-handoff tail is ramped.

Usage:
    python scripts/render_tempo_ramp_experiment.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402
from dsp.render_common import (  # noqa: E402
    load_scenario_context, compute_segments, fit_exact_length, ms_to_samples,
    compute_alignment_offset_ms, apply_time_offset,
)
from dsp.render_m2_signalsmith import POST_ROLL_STRETCH_S  # noqa: E402
from dsp.tempo_ramp import apply_return_to_native_ramp  # noqa: E402
from dsp.tempo_modes import select_tempo_mode  # noqa: E402
from dsp import safety_metrics as sm  # noqa: E402

SERVE_TMP = ROOT / "serve_tmp"
OUT_DIR = ROOT / "results" / "tempo_ramp_experiment"
TRANSITION_ID = "R3-B"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = load_scenario_context(TRANSITION_ID, variant="diagnostic")
    decision = ctx["decision"]
    mode, evidence = select_tempo_mode(decision, prefer_return_to_native=True)
    print(f"{TRANSITION_ID} tempo mode: {mode}")
    print(json.dumps(evidence, indent=2))
    assert mode == "MATCH_AND_RETURN_TO_NATIVE", f"expected MATCH_AND_RETURN_TO_NATIVE for {TRANSITION_ID}, got {mode}"

    segs = compute_segments(ctx, post_roll_s=POST_ROLL_STRETCH_S)
    sr = segs["sr"]
    ratio = decision["required_tempo_ratio"]

    stretched, sr_out = read_wav_float(SERVE_TMP / f"{TRANSITION_ID}_diagnostic_m2_output.wav")
    assert sr_out == sr

    align_offset_ms = compute_alignment_offset_ms(decision, segs, ratio)
    stretched_aligned = apply_time_offset(stretched, align_offset_ms, sr)

    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(stretched_aligned[:overlap_len], overlap_len)
    incoming_post_matched = stretched_aligned[overlap_len:overlap_len + ms_to_samples(POST_ROLL_STRETCH_S * 1000, sr)]

    # Incoming's own native bpm -> 2 bars at NATIVE tempo is the "musically
    # sensible settling region" (PM: "align ramp boundaries to musically
    # sensible beat/bar/phrase regions").
    incoming_bpm = ctx["scenario"]["audio_plan"]["incoming"]["bpm"]
    bar_dur_s = 4.0 * (60.0 / incoming_bpm)
    ramp_duration_s = 2.0 * bar_dur_s
    print(f"incoming native bpm={incoming_bpm}, bar_dur_s={bar_dur_s:.3f}, ramp_duration_s={ramp_duration_s:.3f} (2 bars)")

    # --- Comparator 1: MATCH_INCOMING_DURING_OVERLAP (no ramp, stable matched tempo) ---
    rendered_no_ramp = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post_matched,
        sr, use_equal_power=True, use_bass_handoff=True,
    )
    safe_no_ramp, safety_no_ramp = apply_headroom_and_safety(rendered_no_ramp)
    write_wav_float32(OUT_DIR / f"{TRANSITION_ID}_no_ramp.wav", safe_no_ramp, sr)

    # --- Comparator 2: MATCH_AND_RETURN_TO_NATIVE (ramped post-handoff tail) ---
    ramped_post, rate_curve = apply_return_to_native_ramp(incoming_post_matched, sr, ratio, ramp_duration_s)
    rendered_ramp = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, ramped_post,
        sr, use_equal_power=True, use_bass_handoff=True,
    )
    safe_ramp, safety_ramp = apply_headroom_and_safety(rendered_ramp)
    write_wav_float32(OUT_DIR / f"{TRANSITION_ID}_with_ramp.wav", safe_ramp, sr)

    # Splice point where the ramp begins (end of overlap, in render-buffer coordinates).
    pre_roll_len = segs["onset_smp"] - max(0, segs["onset_smp"] - ms_to_samples(15000, sr))
    ramp_start_render_smp = pre_roll_len + overlap_len

    disc_no_ramp = sm.discontinuity_proxy_at_edges(safe_no_ramp, sr, [ramp_start_render_smp], window_ms=20.0, jump_threshold_sigma=15.0)
    disc_ramp = sm.discontinuity_proxy_at_edges(safe_ramp, sr, [ramp_start_render_smp], window_ms=20.0, jump_threshold_sigma=15.0)
    # Also scan the ramp region itself for any internal discontinuity the
    # warp/interpolation might have introduced (not just the splice edge).
    ramp_region_end_smp = min(safe_ramp.shape[0], ramp_start_render_smp + int(round((ramp_duration_s + 1.0) * sr)))
    disc_within_ramp = sm.discontinuity_proxy(safe_ramp[ramp_start_render_smp:ramp_region_end_smp], sr)

    result = {
        "transition_id": TRANSITION_ID,
        "tempo_mode": mode,
        "tempo_mode_evidence": evidence,
        "required_tempo_ratio": ratio,
        "incoming_native_bpm": incoming_bpm,
        "ramp_duration_s": ramp_duration_s,
        "ramp_bars": 2,
        "rate_curve": rate_curve,
        "no_ramp": {
            "output_duration_s": safe_no_ramp.shape[0] / sr,
            "nan_inf_sample_count": sm.nan_inf_count(safe_no_ramp),
            "clipped_sample_count": sm.clipped_sample_count(safe_no_ramp),
            "peak_dbfs": sm.peak_dbfs(safe_no_ramp),
            "discontinuity_at_handoff_boundary": disc_no_ramp,
        },
        "with_ramp": {
            "output_duration_s": safe_ramp.shape[0] / sr,
            "nan_inf_sample_count": sm.nan_inf_count(safe_ramp),
            "clipped_sample_count": sm.clipped_sample_count(safe_ramp),
            "peak_dbfs": sm.peak_dbfs(safe_ramp),
            "discontinuity_at_handoff_boundary": disc_ramp,
            "discontinuity_within_ramp_region": disc_within_ramp,
        },
    }
    (OUT_DIR / f"{TRANSITION_ID}_tempo_ramp_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rate_curve"}, indent=2))
    print(f"\nrate_curve has {len(rate_curve)} points (every ~100ms); first few:")
    for pt in rate_curve[:5]:
        print(" ", pt)
    print("...")
    for pt in rate_curve[-5:]:
        print(" ", pt)


if __name__ == "__main__":
    main()
