"""
P0-M3-R2 Task G -- planner output contract.

The smallest provider-independent handoff a future DSP execution pass
needs. This module defines only the SHAPE of that handoff; it never
implements Signalsmith Stretch / Rubber Band / any DSP execution (AC16).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class PlannerDecision:
    fixture_id: str
    listener_intent: str
    policy_name: str

    # AC10: PLAY_THROUGH / NO_SPECIAL_TRANSITION are first-class results,
    # not error states. decision_type is one of:
    #   "TRANSITION" | "PLAY_THROUGH" | "NO_SPECIAL_TRANSITION"
    decision_type: str

    # Populated only when decision_type == "TRANSITION".
    current_track_exit_window_ms: Optional[dict] = None  # {"t_start_ms":..,"t_end_ms":..}
    next_track_entry_window_ms: Optional[dict] = None     # provider-independent placeholder; no next-track audio referenced
    preferred_transition_class_set: list = field(default_factory=list)
    beat_downbeat_alignment_target_ms: Optional[int] = None
    permitted_tempo_pitch_envelope: Optional[dict] = None  # {"tempo_ratio_max_deviation":0.12,"max_pitch_shift_semitones":3}

    confidence: str = "NONE"
    reason_codes: list = field(default_factory=list)

    # AC11: queue ordering never grants permission to exit the current
    # track early. This field is always true and is asserted by verify.py
    # against the fact that no eligibility computation in this package ever
    # reads a "next track quality"/queue field.
    queue_order_independent_of_exit_timing: bool = True

    # Full per-candidate evaluation trace for this fixture/intent/policy
    # triple (AC12: candidate decisions expose reason codes / traceable
    # evidence).
    candidate_trace: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_transition_decision(fixture_id, intent, policy_name, chosen_eligibility, candidate, candidate_trace):
    permitted_envelope = None
    if "FULL_DJ_BLEND" in chosen_eligibility.preferred_transition_class_set:
        permitted_envelope = {
            "tempo_ratio_max_deviation": 0.12,
            "max_pitch_shift_semitones": 3,
        }
    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type="TRANSITION",
        current_track_exit_window_ms={
            "t_start_ms": chosen_eligibility.t_ms,
            "t_end_ms": chosen_eligibility.t_ms,
        },
        next_track_entry_window_ms={"t_start_ms": 0, "t_end_ms": 0},
        preferred_transition_class_set=chosen_eligibility.preferred_transition_class_set,
        beat_downbeat_alignment_target_ms=chosen_eligibility.t_ms if candidate.get("beat_downbeat_aligned") else None,
        permitted_tempo_pitch_envelope=permitted_envelope,
        confidence=chosen_eligibility.confidence,
        reason_codes=chosen_eligibility.acceptance_reason_codes,
        candidate_trace=candidate_trace,
    )


def build_fallback_decision(fixture_id, intent, policy_name, decision_type, reason_codes, candidate_trace, confidence="LOW"):
    assert decision_type in ("PLAY_THROUGH", "NO_SPECIAL_TRANSITION")
    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type=decision_type,
        confidence=confidence,
        reason_codes=reason_codes,
        candidate_trace=candidate_trace,
    )
