"""
M1 -- planner-correct equal-power SIMPLE_CROSSFADE reference (Issue #7
"M1 -- clean simple reference... equal-power SIMPLE_CROSSFADE; no tempo
correction unless the class requires it; serves as the 'do less'
reference").

SIMPLE_CROSSFADE never requires tempo correction or beat alignment by
AGENTS.md's own terminology gate ("Crossfade: volume overlap only"), so M1
intentionally never applies either, even on scenarios where FULL_DJ_BLEND
was ALSO allowed by the planner (B/C) -- it renders the same class
regardless, by design, so it is a stable "do less" comparator against M2/M3.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402
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
        sr, use_equal_power=True, use_bass_handoff=False,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)

    decision = ctx["decision"]
    metadata = {
        "method": "M1",
        "method_role": "planner_correct_equal_power_simple_crossfade_reference",
        "transition_id": transition_id,
        "rendered_transition_class": "SIMPLE_CROSSFADE",
        "planner_allowed_transition_class_set": decision["allowed_transition_class_set"],
        "gain_law": "equal_power",
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
