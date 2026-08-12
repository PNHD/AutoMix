"""
Shared render context/segmentation logic used by every method (M0-M3).

This is the ONE place that reads the R2 PlannerDecision and cuts audio
segments from it -- every method downstream receives the SAME
outgoing/incoming boundary, onset window, entry window, and (when
applicable) tempo/pitch/alignment contract (Issue #7 "the exact same
outgoing/incoming planner boundary must be used by all methods").
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "fixtures"))

from dsp.wav_io import read_wav_float  # noqa: E402
from scenario_fixtures import SCENARIOS_BY_ID  # noqa: E402

PLANNER_DECISIONS_DIR = ROOT / "fixtures" / "planner_decisions"
GROUND_TRUTH_DIR = ROOT / "fixtures" / "ground_truth"
AUDIO_DIR = ROOT / "audio_local"

PRE_ROLL_S = 15.0
POST_ROLL_S = 15.0

REQUIRED_FULL_DJ_ALIGNMENT_FIELDS = (
    "outgoing_beat_alignment_target_ms",
    "incoming_beat_alignment_target_ms",
    "outgoing_downbeat_alignment_target_ms",
    "incoming_downbeat_alignment_target_ms",
    "beat_alignment_action",
    "bar_alignment_action",
)


class PlannerContractError(Exception):
    """Raised when a renderer would have to guess/fabricate a planner field. Fail-closed, never silently substituted."""


def require_full_dj_alignment_fields(decision: dict) -> None:
    """
    Issue #7 "For FULL_DJ: require outgoing beat target, incoming beat
    target, outgoing downbeat target, incoming downbeat target,
    beat_alignment_action, bar_alignment_action. Fail closed if missing."
    `beat_phase_relation == NOT_MEASURED` does NOT satisfy this by itself --
    only the presence of the actual target/action fields does.
    """
    missing = [f for f in REQUIRED_FULL_DJ_ALIGNMENT_FIELDS if decision.get(f) in (None, "NOT_APPLICABLE")]
    if missing:
        raise PlannerContractError(
            f"FULL_DJ_BLEND requires {REQUIRED_FULL_DJ_ALIGNMENT_FIELDS}; missing/NOT_APPLICABLE: {missing}. "
            "Failing closed -- refusing to render FULL_DJ_BLEND rather than guessing an alignment target."
        )
    if decision.get("required_tempo_ratio") is None:
        raise PlannerContractError("FULL_DJ_BLEND selected but required_tempo_ratio is None -- failing closed.")


def ms_to_samples(ms: float, sr: int) -> int:
    return int(round(ms / 1000.0 * sr))


VALID_VARIANTS = ("diagnostic", "clean")


def load_scenario_context(transition_id: str, variant: str = "diagnostic") -> dict:
    """
    PM STAGE A REVIEW R4 repair: `variant="diagnostic"` loads the
    marker-embedded source audio (used for the full DSP pipeline + machine
    alignment metrics + PM forensic review). `variant="clean"` loads
    marker-FREE source audio (used ONLY for owner-listening renders) --
    diagnostic ticks must never reach owner-listening audio.
    """
    if variant not in VALID_VARIANTS:
        raise ValueError(f"variant must be one of {VALID_VARIANTS}, got {variant!r}")
    scenario = SCENARIOS_BY_ID[transition_id]
    decision = json.loads((PLANNER_DECISIONS_DIR / f"{transition_id}.json").read_text(encoding="utf-8"))
    audio_source_id = scenario.get("reuses_audio_from", transition_id)
    suffix = "" if variant == "diagnostic" else "_clean"

    out_wav, sr_out = read_wav_float(AUDIO_DIR / f"{audio_source_id}_outgoing{suffix}.wav")
    in_wav, sr_in = read_wav_float(AUDIO_DIR / f"{audio_source_id}_incoming{suffix}.wav")
    assert sr_out == sr_in, "outgoing/incoming sample rates must match for this harness's fixtures"

    out_gt = None
    in_gt = None
    if variant == "diagnostic":
        out_gt = json.loads((GROUND_TRUTH_DIR / f"{audio_source_id}_outgoing.ground_truth.json").read_text(encoding="utf-8"))
        in_gt = json.loads((GROUND_TRUTH_DIR / f"{audio_source_id}_incoming.ground_truth.json").read_text(encoding="utf-8"))

    return {
        "transition_id": transition_id,
        "scenario": scenario,
        "decision": decision,
        "audio_source_id": audio_source_id,
        "variant": variant,
        "sr": sr_out,
        "outgoing_audio": out_wav,
        "incoming_audio": in_wav,
        "outgoing_ground_truth": out_gt,
        "incoming_ground_truth": in_gt,
    }


def compute_segments(ctx: dict, pre_roll_s: float = PRE_ROLL_S, post_roll_s: float = POST_ROLL_S) -> dict:
    """
    Cuts [outgoing_pre | outgoing_overlap] and [incoming_overlap_raw_input |
    incoming_post_raw_input] directly from the planner decision's own
    fields -- onset/content-end/entry timestamps are read verbatim from the
    PlannerDecision, never re-derived or guessed.
    """
    decision = ctx["decision"]
    sr = ctx["sr"]
    out_audio = ctx["outgoing_audio"]
    in_audio = ctx["incoming_audio"]

    onset_ms = decision["transition_onset_window_ms"]["t_start_ms"]
    content_end_ms = decision["current_track_effective_content_end_ms"]
    entry_ms = decision["next_track_entry_window_ms"]["t_start_ms"]

    onset_smp = ms_to_samples(onset_ms, sr)
    content_end_smp = min(ms_to_samples(content_end_ms, sr), out_audio.shape[0])
    overlap_len_smp = max(0, content_end_smp - onset_smp)

    pre_start_smp = max(0, onset_smp - ms_to_samples(pre_roll_s * 1000, sr))
    outgoing_pre = out_audio[pre_start_smp:onset_smp]
    outgoing_overlap = out_audio[onset_smp:content_end_smp]

    entry_smp = ms_to_samples(entry_ms, sr)
    post_roll_len_smp = ms_to_samples(post_roll_s * 1000, sr)
    incoming_needed_raw_smp = min(in_audio.shape[0] - entry_smp, overlap_len_smp + post_roll_len_smp)
    incoming_raw_segment = in_audio[entry_smp:entry_smp + incoming_needed_raw_smp]

    return {
        "sr": sr,
        "onset_ms": onset_ms,
        "content_end_ms": content_end_ms,
        "entry_ms": entry_ms,
        "onset_smp": onset_smp,
        "content_end_smp": content_end_smp,
        "entry_smp": entry_smp,
        "overlap_len_smp": overlap_len_smp,
        "outgoing_pre": outgoing_pre,
        "outgoing_overlap": outgoing_overlap,
        "incoming_raw_segment": incoming_raw_segment,
    }


def compute_alignment_offset_ms(decision: dict, segs: dict, applied_tempo_ratio: float) -> float:
    """
    General (not hardcoded-zero) computation of how far the incoming
    stretched clip must be shifted so that
    outgoing_beat_alignment_target_ms and incoming_beat_alignment_target_ms
    coincide at the same output-timeline instant, per
    `beat_alignment_action = ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET`.
    Positive return value means the incoming clip should start LATER
    (silence-padded) relative to the overlap window start; negative means
    EARLIER (trimmed).
    """
    out_target_ms = decision.get("outgoing_beat_alignment_target_ms")
    in_target_ms = decision.get("incoming_beat_alignment_target_ms")
    if out_target_ms is None or in_target_ms is None:
        return 0.0
    out_target_rel_ms = out_target_ms - segs["onset_ms"]
    in_target_rel_raw_ms = in_target_ms - segs["entry_ms"]
    ratio = applied_tempo_ratio if applied_tempo_ratio else 1.0
    in_target_rel_stretched_ms = in_target_rel_raw_ms / ratio
    return out_target_rel_ms - in_target_rel_stretched_ms


def apply_time_offset(x: np.ndarray, offset_ms: float, sr: int) -> np.ndarray:
    """Shifts a (n, ch) buffer later (positive offset_ms, zero-padded) or earlier (negative, trimmed)."""
    offset_smp = ms_to_samples(offset_ms, sr)
    if offset_smp == 0:
        return x
    if offset_smp > 0:
        pad = np.zeros((offset_smp, x.shape[1]), dtype=x.dtype)
        return np.concatenate([pad, x], axis=0)
    return x[-offset_smp:]


PREMIX_DIAG_DIR = Path(__file__).resolve().parent.parent / "results" / "premix_diag"


def save_premix_diagnostic(transition_id: str, method: str, outgoing_overlap: np.ndarray, incoming_overlap: np.ndarray, sr: int) -> None:
    """
    PM STAGE A REVIEW R3 follow-up finding: equal-power gain is exactly 0
    at the very start of the incoming side's crossfade-in by mathematical
    construction (`sin(0) == 0`) -- a diagnostic marker embedded at the
    incoming track's own alignment-anchor sample is therefore ALWAYS
    silenced at that exact instant in the fully gain-mixed final render,
    regardless of whether the renderer positioned it correctly. That is a
    real, expected property of equal-power crossfades, not a placement
    bug -- but it makes the FINAL MIXED render an unreliable place to
    empirically verify incoming-side alignment. This saves the PRE-GAIN
    `outgoing_overlap`/`incoming_overlap` buffers (exactly as each
    renderer computed them, post-stretch/post-alignment-shift, before
    `dsp.mixing.mix_overlap` multiplies by the crossfade gain curve) so
    `scripts/compute_metrics.py` can measure marker positions on content
    that was never gain-nulled. Diagnostic-only, local, not committed.
    """
    from dsp.wav_io import write_wav_float32
    PREMIX_DIAG_DIR.mkdir(parents=True, exist_ok=True)
    # Only the first ~600ms of each is needed (markers are <=12ms long and
    # placed at sample 0 of each overlap buffer) -- kept small deliberately.
    snippet_len = min(outgoing_overlap.shape[0], incoming_overlap.shape[0], int(round(0.6 * sr)))
    write_wav_float32(PREMIX_DIAG_DIR / f"{transition_id}_{method}_outgoing_premix.wav", outgoing_overlap[:snippet_len], sr)
    write_wav_float32(PREMIX_DIAG_DIR / f"{transition_id}_{method}_incoming_premix.wav", incoming_overlap[:snippet_len], sr)


def fit_exact_length(x: np.ndarray, n: int) -> np.ndarray:
    """Pads with zeros or trims a (m, ch) buffer to exactly n frames."""
    if x.shape[0] == n:
        return x
    if x.shape[0] > n:
        return x[:n]
    pad = np.zeros((n - x.shape[0], x.shape[1]), dtype=x.dtype)
    return np.concatenate([x, pad], axis=0)
