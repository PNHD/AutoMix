"""
P0-M3-R2 Task E -- five policy candidates plus the decision procedure that
picks a single transition/PLAY_THROUGH/NO_SPECIAL_TRANSITION outcome per
(fixture, policy, intent).

Policies:
  1. NAIVE_EARLIEST_COMPATIBLE       -- adversarial baseline; earliest
     technically-compatible point wins, no structure/confidence/intent
     awareness at all. Reproduces the owner's Offtrack-class failure mode
     by construction (OWNER_SUBJECTIVE_REFERENCE, not a reconstruction of
     Offtrack internals -- see P0-M3-R2-OWNER-LISTENING-REFERENCE.md).
  2. BPM_KEY_ONLY_EARLY              -- SimpMusic-class baseline (P0-M1):
     BPM/key compatibility plus a small fixed fraction floor, still no
     structural evidence requirement.
  3. TAIL_ONLY_NATURAL_EXIT_BIASED   -- conservative baseline; a single
     hard late-fraction rule, no nuanced structure scoring -- demonstrates
     over-restrictiveness on long tracks (Task C / AC7).
  4. STRUCTURE_AWARE_PRESERVATION    -- the Task B eligibility model
     (policy/eligibility.py), run under FULL_SONG_DEFAULT or BALANCED_MIX.
     This is the recommended candidate (see the planner doc's recommendation).
  5. EXPLICIT_HIGHLIGHT              -- the identical Task B eligibility
     model, but always evaluated under HIGHLIGHT_EXPLICIT regardless of the
     nominally-requested intent -- demonstrating that shortened playback is
     only ever reachable via explicit opt-in (P0 Task A/AC4), never as a
     silent default (AC1).
"""

from dataclasses import asdict

from .eligibility import evaluate_candidate, EligibilityResult
from .contract import build_transition_decision, build_fallback_decision

POLICY_NAMES = (
    "NAIVE_EARLIEST_COMPATIBLE",
    "BPM_KEY_ONLY_EARLY",
    "TAIL_ONLY_NATURAL_EXIT_BIASED",
    "STRUCTURE_AWARE_PRESERVATION",
    "EXPLICIT_HIGHLIGHT",
)

BPM_KEY_ONLY_FRACTION_FLOOR = 0.10
TAIL_ONLY_FRACTION_FLOOR = 0.70


def _naive_earliest_compatible_eval(fixture, candidate, intent, fraction_floor_override=None) -> EligibilityResult:
    duration_ms = fixture["duration_ms"]
    t_ms = candidate["t_ms"]
    fraction_consumed = round(t_ms / duration_ms, 4) if duration_ms else 0.0
    technically_compatible = bool(candidate.get("beat_downbeat_aligned") or candidate.get("source") == "technical_mix_point")
    eligible = technically_compatible
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        fraction_consumed=fraction_consumed,
        eligible=eligible,
        rejection_reason_codes=[] if eligible else ["NOT_TECHNICALLY_COMPATIBLE"],
        acceptance_reason_codes=["TECHNICALLY_COMPATIBLE_MIX_POINT"] if eligible else [],
        song_preservation_score=0.0,
        musical_structure_score=0.0,
        timing_score=1.0 if eligible else 0.0,
        confidence="N/A -- policy does not model confidence",
        confidence_reason="NAIVE_EARLIEST_COMPATIBLE ignores structure/confidence entirely by design (adversarial baseline)",
        preferred_transition_class_set=["FULL_DJ_BLEND"] if eligible else [],
    )


def _bpm_key_only_early_eval(fixture, candidate, intent, fraction_floor_override=None) -> EligibilityResult:
    duration_ms = fixture["duration_ms"]
    t_ms = candidate["t_ms"]
    fraction_consumed = round(t_ms / duration_ms, 4) if duration_ms else 0.0
    technically_compatible = bool(candidate.get("beat_downbeat_aligned"))
    floor = fraction_floor_override if fraction_floor_override is not None else BPM_KEY_ONLY_FRACTION_FLOOR
    eligible = technically_compatible and fraction_consumed >= floor
    reasons = []
    if not technically_compatible:
        reasons.append("NOT_BPM_KEY_COMPATIBLE")
    if fraction_consumed < floor:
        reasons.append("BELOW_FIXED_SMALL_FRACTION_FLOOR")
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        fraction_consumed=fraction_consumed,
        eligible=eligible,
        rejection_reason_codes=reasons,
        acceptance_reason_codes=["BPM_KEY_COMPATIBLE_ABOVE_FLOOR"] if eligible else [],
        song_preservation_score=fraction_consumed,
        musical_structure_score=0.0,
        timing_score=fraction_consumed if eligible else 0.0,
        confidence="N/A -- policy does not model confidence",
        confidence_reason="BPM_KEY_ONLY_EARLY ignores structure/confidence entirely by design (SimpMusic-class baseline, P0-M1)",
        preferred_transition_class_set=["SIMPLE_CROSSFADE", "FULL_DJ_BLEND"] if eligible else [],
    )


def _tail_only_natural_exit_biased_eval(fixture, candidate, intent, fraction_floor_override=None) -> EligibilityResult:
    duration_ms = fixture["duration_ms"]
    t_ms = candidate["t_ms"]
    fraction_consumed = round(t_ms / duration_ms, 4) if duration_ms else 0.0
    structural = bool(candidate.get("in_acceptable_exit_region") or candidate.get("is_outro_tail_opportunity"))
    vocal_high = candidate.get("vocal_collision_risk") == "HIGH"
    floor = fraction_floor_override if fraction_floor_override is not None else TAIL_ONLY_FRACTION_FLOOR
    eligible = structural and fraction_consumed >= floor and not vocal_high
    reasons = []
    if not structural:
        reasons.append("NO_STRUCTURAL_EVIDENCE")
    if fraction_consumed < floor:
        reasons.append("BELOW_HARD_LATE_FRACTION_RULE")
    if vocal_high:
        reasons.append("VOCAL_COLLISION_RISK_HIGH")
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        fraction_consumed=fraction_consumed,
        eligible=eligible,
        rejection_reason_codes=reasons,
        acceptance_reason_codes=["LATE_STRUCTURAL_REGION"] if eligible else [],
        song_preservation_score=fraction_consumed,
        musical_structure_score=1.0 if structural else 0.0,
        timing_score=fraction_consumed if eligible else 0.0,
        confidence=candidate.get("structure_confidence", "NONE"),
        confidence_reason="TAIL_ONLY_NATURAL_EXIT_BIASED uses a single hard late-fraction rule, no nuanced structure score",
        preferred_transition_class_set=["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"] if eligible else [],
    )


def _structure_aware_eval(fixture, candidate, intent, fraction_floor_override=None) -> EligibilityResult:
    return evaluate_candidate(fixture, candidate, intent, fraction_floor_override)


def _explicit_highlight_eval(fixture, candidate, intent, fraction_floor_override=None) -> EligibilityResult:
    # Always evaluated under HIGHLIGHT_EXPLICIT, regardless of the intent
    # argument passed in -- this policy IS the explicit-opt-in gate.
    return evaluate_candidate(fixture, candidate, "HIGHLIGHT_EXPLICIT", fraction_floor_override)


POLICY_EVAL = {
    "NAIVE_EARLIEST_COMPATIBLE": _naive_earliest_compatible_eval,
    "BPM_KEY_ONLY_EARLY": _bpm_key_only_early_eval,
    "TAIL_ONLY_NATURAL_EXIT_BIASED": _tail_only_natural_exit_biased_eval,
    "STRUCTURE_AWARE_PRESERVATION": _structure_aware_eval,
    "EXPLICIT_HIGHLIGHT": _explicit_highlight_eval,
}


def _trace_entry(candidate, result: EligibilityResult) -> dict:
    return {
        "candidate_id": result.candidate_id,
        "t_ms": result.t_ms,
        "fraction_consumed": result.fraction_consumed,
        "source": candidate.get("source"),
        "eligible": result.eligible,
        "rejection_reason_codes": result.rejection_reason_codes,
        "acceptance_reason_codes": result.acceptance_reason_codes,
        "song_preservation_score": result.song_preservation_score,
        "musical_structure_score": result.musical_structure_score,
        "timing_score": result.timing_score,
        "confidence": result.confidence,
        "preferred_transition_class_set": result.preferred_transition_class_set,
    }


def decide_at_time(fixture: dict, policy_name: str, intent: str, evaluation_time_ms: int, fraction_floor_override=None):
    """
    Simulates a real-time planner query at evaluation_time_ms. Returns a
    PlannerDecision. Only candidates with t_ms <= evaluation_time_ms are
    considered "seen so far" -- this is what makes PLAY_THROUGH meaningfully
    distinct from NO_SPECIAL_TRANSITION (AC10): PLAY_THROUGH means "nothing
    eligible has been seen yet AND the track has not ended"; NO_SPECIAL_
    TRANSITION means "the track reached its natural end with nothing
    eligible selected earlier."
    """
    eval_fn = POLICY_EVAL[policy_name]
    duration_ms = fixture["duration_ms"]
    candidates = fixture["candidates"]
    seen_non_end = [c for c in candidates if not c.get("is_end_of_track") and c["t_ms"] <= evaluation_time_ms]
    trace = []
    for c in seen_non_end:
        result = eval_fn(fixture, c, intent, fraction_floor_override)
        trace.append(_trace_entry(c, result))
        if result.eligible:
            return build_transition_decision(fixture["fixture_id"], intent, policy_name, result, c, trace)

    if evaluation_time_ms >= duration_ms:
        end_candidate = next(c for c in candidates if c.get("is_end_of_track"))
        result = eval_fn(fixture, end_candidate, intent, fraction_floor_override)
        trace.append(_trace_entry(end_candidate, result))
        reason_codes = ["END_OF_TRACK_NATURAL_HANDOFF"] + result.rejection_reason_codes + result.acceptance_reason_codes
        return build_fallback_decision(
            fixture["fixture_id"], intent, policy_name, "NO_SPECIAL_TRANSITION",
            reason_codes, trace, confidence=result.confidence,
        )

    return build_fallback_decision(
        fixture["fixture_id"], intent, policy_name, "PLAY_THROUGH",
        ["NO_ELIGIBLE_CANDIDATE_YET_MORE_TRACK_REMAINS"], trace, confidence="N/A -- re-evaluate later",
    )


def decide(fixture: dict, policy_name: str, intent: str, fraction_floor_override=None):
    """Full-track batch decision: equivalent to querying at the natural end."""
    return decide_at_time(fixture, policy_name, intent, fixture["duration_ms"], fraction_floor_override)
