"""
P0-M3-R2 (Apple-like redesign) -- planner output contract.

The smallest provider-independent handoff the P0-M3-R3 DSP-execution pass
needs. This module defines only the SHAPE of that handoff; it never
implements Signalsmith Stretch / Rubber Band / any DSP execution (AC16).

Field set follows Issue #6 "PLANNER OUTPUT CONTRACT FOR P0-M3-R3" exactly.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

from .compatibility import evaluate_pair_compatibility, downgrade_transition_class_set

# P0 placeholder tempo/pitch envelope offered only when FULL_DJ_BLEND is
# actually in the allowed class set. Matches P0-M2's tempo_ratio_max_deviation
# ceiling (docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md). Not an
# Apple-documented number.
PERMITTED_TEMPO_RATIO_MAX_DEVIATION = 0.12
PERMITTED_MAX_PITCH_SHIFT_SEMITONES = 3


@dataclass
class PlannerDecision:
    fixture_id: str
    listener_intent: str
    policy_name: str

    # AC10: PLAY_THROUGH / NO_SPECIAL_TRANSITION are first-class results,
    # not error states. decision_type is one of:
    #   "TRANSITION" | "PLAY_THROUGH" | "NO_SPECIAL_TRANSITION"
    decision_type: str

    # --- Song-preservation / timing (spec section B) ---
    current_track_effective_content_end_ms: Optional[int] = None
    transition_onset_window_ms: Optional[dict] = None      # {"t_start_ms":..,"t_end_ms":..}
    outgoing_last_audible_target_ms: Optional[int] = None
    outgoing_content_preservation_target: Optional[float] = None
    next_track_entry_window_ms: Optional[dict] = None      # provider-independent placeholder; no next-track audio referenced

    # --- Transition class / pair compatibility (spec sections D/E) ---
    allowed_transition_class_set: list = field(default_factory=list)
    pair_compatibility_components: Optional[dict] = None    # None when no pair was supplied (compatibility unproven)
    beat_alignment_target: Optional[int] = None
    downbeat_alignment_target: Optional[int] = None
    permitted_tempo_ratio: Optional[float] = None
    permitted_pitch_shift: Optional[int] = None
    energy_continuity_target: Optional[str] = None
    vocal_collision_constraints: Optional[str] = None
    bass_collision_constraints: Optional[str] = None

    analysis_confidence: str = "NONE"
    reason_codes: list = field(default_factory=list)

    # AC11: queue ordering never grants permission to exit the current
    # track early. Always true; asserted by verify.py against the fact that
    # no eligibility computation in this package ever reads a "next track
    # quality"/queue field for TIMING purposes.
    queue_order_independent_of_exit_timing: bool = True

    # Full per-candidate evaluation trace, including eligible_rank for
    # every RANKED_POLICY run (AC12 + multi-candidate ranking evidence).
    candidate_rank_trace: list = field(default_factory=list)

    # Retained for backward-compatible field name; identical to
    # candidate_rank_trace.
    candidate_trace: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _compatibility_payload(pair: Optional[dict]):
    if pair is None:
        return None, None
    result = evaluate_pair_compatibility(pair)
    return result, result.to_dict()


def build_transition_decision(fixture_id, intent, policy_name, chosen_eligibility, candidate, candidate_trace, pair=None):
    compat_result, compat_payload = _compatibility_payload(pair)
    allowed_class_set = downgrade_transition_class_set(chosen_eligibility.preferred_transition_class_set, compat_result)

    permitted_tempo_ratio = None
    permitted_pitch_shift = None
    if "FULL_DJ_BLEND" in allowed_class_set:
        permitted_tempo_ratio = PERMITTED_TEMPO_RATIO_MAX_DEVIATION
        permitted_pitch_shift = PERMITTED_MAX_PITCH_SHIFT_SEMITONES

    onset = chosen_eligibility.transition_onset_ms
    remaining_headroom = max(0, chosen_eligibility.effective_content_end_ms - onset)
    onset_window = {"t_start_ms": onset, "t_end_ms": min(chosen_eligibility.effective_content_end_ms, onset + remaining_headroom)}

    vocal_constraint = "NO_HIGH_RISK_OVERLAP_PERMITTED"
    bass_constraint = "NO_HIGH_RISK_OVERLAP_PERMITTED"
    energy_target = "MAINTAIN_OR_INCREASE_MOMENTUM_WHERE_PAIR_COMPATIBLE"
    if compat_result is not None:
        vocal_constraint = f"PAIR_VOCAL_COLLISION_RISK={compat_result.vocal_collision_risk}"
        bass_constraint = f"PAIR_BASS_PERCUSSION_COLLISION_RISK={compat_result.bass_percussion_collision_risk}"
        energy_target = f"PAIR_ENERGY_CONTINUITY={compat_result.energy_continuity}"

    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type="TRANSITION",
        current_track_effective_content_end_ms=chosen_eligibility.effective_content_end_ms,
        transition_onset_window_ms=onset_window,
        outgoing_last_audible_target_ms=chosen_eligibility.outgoing_last_audible_ms,
        outgoing_content_preservation_target=chosen_eligibility.outgoing_content_preservation_ratio,
        next_track_entry_window_ms={"t_start_ms": 0, "t_end_ms": 0},
        allowed_transition_class_set=allowed_class_set,
        pair_compatibility_components=compat_payload,
        beat_alignment_target=chosen_eligibility.t_ms if candidate.get("beat_downbeat_aligned") else None,
        downbeat_alignment_target=chosen_eligibility.t_ms if candidate.get("beat_downbeat_aligned") else None,
        permitted_tempo_ratio=permitted_tempo_ratio,
        permitted_pitch_shift=permitted_pitch_shift,
        energy_continuity_target=energy_target,
        vocal_collision_constraints=vocal_constraint,
        bass_collision_constraints=bass_constraint,
        analysis_confidence=chosen_eligibility.confidence,
        reason_codes=chosen_eligibility.acceptance_reason_codes,
        candidate_rank_trace=candidate_trace,
        candidate_trace=candidate_trace,
    )


def build_fallback_decision(fixture_id, intent, policy_name, decision_type, reason_codes, candidate_trace, confidence="LOW"):
    assert decision_type in ("PLAY_THROUGH", "NO_SPECIAL_TRANSITION")
    effective_end = None
    if candidate_trace:
        effective_end = candidate_trace[-1].get("effective_content_end_ms")
    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type=decision_type,
        current_track_effective_content_end_ms=effective_end,
        allowed_transition_class_set=["NO_SPECIAL_TRANSITION"] if decision_type == "NO_SPECIAL_TRANSITION" else [],
        analysis_confidence=confidence,
        reason_codes=reason_codes,
        candidate_rank_trace=candidate_trace,
        candidate_trace=candidate_trace,
    )
