"""
M0 -- intentionally weak negative baseline (Issue #7 "M0 -- intentionally
weak negative baseline... no hidden quality improvements").

Uses the SAME planner boundary (onset/entry timestamps) as every other
method, but deliberately:
  - never applies the planner's required_tempo_ratio, even when the
    scenario requires one (audible tempo/pitch mismatch on B/C);
  - uses a linear (non-equal-power) crossfade, which produces a real,
    well-known perceived volume dip near the midpoint;
  - never applies beat/downbeat alignment or bass/EQ handoff.
This is a real, reproducible negative reference, not a strawman -- it is
exactly "do nothing clever" applied to the correct boundary.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsp.mixing import assemble_transition_render, apply_headroom_and_safety, linear_crossfade_gains  # noqa: E402
from dsp.render_common import load_scenario_context, compute_segments, fit_exact_length  # noqa: E402


def render(transition_id: str) -> tuple:
    ctx = load_scenario_context(transition_id)
    segs = compute_segments(ctx)
    sr = segs["sr"]

    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
    incoming_post = segs["incoming_raw_segment"][overlap_len:]

    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=False, use_bass_handoff=False,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)

    decision = ctx["decision"]
    metadata = {
        "method": "M0",
        "method_role": "intentionally_weak_negative_baseline",
        "transition_id": transition_id,
        "rendered_transition_class": "SIMPLE_CROSSFADE_LINEAR_UNCORRECTED",
        "planner_allowed_transition_class_set": decision["allowed_transition_class_set"],
        "gain_law": "linear",
        "bass_eq_handoff_applied": False,
        "applied_tempo_ratio": 1.0,
        "planner_required_tempo_ratio": decision.get("required_tempo_ratio"),
        "tempo_correction_deliberately_skipped": decision.get("required_tempo_ratio") not in (None, 1.0),
        "applied_pitch_shift_semitones": 0,
        "applied_alignment_offset_ms": 0.0,
        "beat_alignment_applied": False,
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "entry_ms": segs["entry_ms"],
        "overlap_len_samples": overlap_len,
        "overlap_duration_ms": overlap_len / sr * 1000.0,
        "output_duration_s": safe_audio.shape[0] / sr,
        "safety": safety_diag,
    }
    return safe_audio, sr, metadata
