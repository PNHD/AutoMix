"""
P0-M3-R2 (Apple-like redesign) -- policy candidates plus the decision
procedure that picks a single transition/PLAY_THROUGH/NO_SPECIAL_TRANSITION
outcome per (fixture, policy, intent[, pair]).

Product direction (Issue #6 "PM PRODUCT DIRECTION UPDATE"): the ONLY
current product-default recommendation is SEAMLESS_FULL_TRACK_DEFAULT.
Every other policy below exists purely as a baseline/negative/research
control for comparison and MUST NOT influence the recommended engine's
behavior.

Policies:
  1. NAIVE_EARLIEST_COMPATIBLE       -- adversarial baseline; earliest
     technically-compatible point wins, no structure/confidence/
     preservation awareness at all (OWNER_SUBJECTIVE_REFERENCE motivation
     only -- see P0-M3-R2-OWNER-LISTENING-REFERENCE.md).
  2. BPM_KEY_ONLY_EARLY              -- SimpMusic-class baseline (P0-M1):
     BPM/key compatibility plus a small fixed fraction floor.
  3. TAIL_ONLY_NATURAL_EXIT_BIASED   -- fixed-late-fraction baseline;
     over-restrictive on long tracks (Task F contrast).
  4. FIXED_SECONDS_BEFORE_END_ONLY   -- adversarial baseline; accepts only
     a candidate within a single fixed N-seconds-of-absolute-end window,
     regardless of track duration. Demonstrates why "one fixed seconds
     rule" fails across very different track lengths (spec: "Do not
     implement fixed 'N seconds before end' only").
  5. SEAMLESS_FULL_TRACK_DEFAULT     -- THE RECOMMENDED product-default
     engine (policy/eligibility.py). Ranks ALL eligible near-end candidates
     (policy/ranking.py); never returns the first eligible candidate.
  6. BALANCED_MIX_RESEARCH_CONTROL   -- same engine, run under the
     BALANCED_MIX intent (lower preservation floor). Research/negative
     control ONLY; carries no acceptance criterion and never affects the
     default row.
  7. EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL -- same engine's structural/
     vocal-safety guards, but reachable ONLY when the caller's own intent
     argument is HIGHLIGHT_EXPLICIT. Unlike the superseded prior
     implementation, this policy does NOT silently rewrite a mismatched
     caller intent to HIGHLIGHT_EXPLICIT -- see _explicit_highlight_eval.
"""

from .eligibility import evaluate_candidate, EligibilityResult, VALID_INTENTS, DEFAULT_INTENT
from .ranking import rank_eligible_candidates
from .compatibility import downgrade_transition_class_set, evaluate_pair_compatibility
from .contract import build_transition_decision, build_fallback_decision
from .metrics import effective_content_end_ms as _effective_content_end_ms

POLICY_NAMES = (
    "NAIVE_EARLIEST_COMPATIBLE",
    "BPM_KEY_ONLY_EARLY",
    "TAIL_ONLY_NATURAL_EXIT_BIASED",
    "FIXED_SECONDS_BEFORE_END_ONLY",
    "SEAMLESS_FULL_TRACK_DEFAULT",
    "BALANCED_MIX_RESEARCH_CONTROL",
    "EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL",
)

BPM_KEY_ONLY_FRACTION_FLOOR = 0.10
TAIL_ONLY_FRACTION_FLOOR = 0.70
FIXED_SECONDS_BEFORE_END_WINDOW_MS = 30_000  # P0 adversarial-baseline placeholder, deliberately naive


def _fraction_consumed(fixture, t_ms):
    duration_ms = fixture["duration_ms"]
    return round(t_ms / duration_ms, 4) if duration_ms else 0.0


def _naive_preservation_fields(fixture, t_ms):
    """
    Baseline policies (1-4) have no overlap/preservation model of their
    own -- they are adversarial/naive by design. To keep them comparable
    on the same preservation/timing metric surface as the recommended
    engine, they are scored under pure CUT semantics: no overlap credit,
    outgoing_last_audible_ms == t_ms exactly (worst case, zero overlap).
    This is intentionally punitive -- it is what makes their nonzero
    premature_exit_rate/low mean-preservation numbers meaningful evidence
    rather than an artifact of a missing field.
    """
    duration_ms = fixture["duration_ms"]
    ratio = round(t_ms / duration_ms, 4) if duration_ms else 0.0
    return {
        "effective_content_end_ms": duration_ms,
        "transition_onset_ms": t_ms,
        "transition_onset_ratio": ratio,
        "overlap_duration_ms": 0,
        "outgoing_last_audible_ms": t_ms,
        "outgoing_content_preservation_ratio": ratio,
        "outgoing_content_lost_ms": max(0, duration_ms - t_ms),
    }


def _naive_earliest_compatible_eval(fixture, candidate, intent, floor_override=None) -> EligibilityResult:
    t_ms = candidate["t_ms"]
    technically_compatible = bool(candidate.get("beat_downbeat_aligned") or candidate.get("source") == "technical_mix_point")
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        eligible=technically_compatible,
        rejection_reason_codes=[] if technically_compatible else ["NOT_TECHNICALLY_COMPATIBLE"],
        acceptance_reason_codes=["TECHNICALLY_COMPATIBLE_MIX_POINT"] if technically_compatible else [],
        confidence="N/A -- policy does not model confidence",
        confidence_reason="NAIVE_EARLIEST_COMPATIBLE ignores structure/confidence/preservation entirely by design (adversarial baseline)",
        preferred_transition_class_set=["FULL_DJ_BLEND"] if technically_compatible else [],
        **_naive_preservation_fields(fixture, t_ms),
    )


def _bpm_key_only_early_eval(fixture, candidate, intent, floor_override=None) -> EligibilityResult:
    t_ms = candidate["t_ms"]
    fraction = _fraction_consumed(fixture, t_ms)
    technically_compatible = bool(candidate.get("beat_downbeat_aligned"))
    floor = floor_override if floor_override is not None else BPM_KEY_ONLY_FRACTION_FLOOR
    eligible = technically_compatible and fraction >= floor
    reasons = []
    if not technically_compatible:
        reasons.append("NOT_BPM_KEY_COMPATIBLE")
    if fraction < floor:
        reasons.append("BELOW_FIXED_SMALL_FRACTION_FLOOR")
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        eligible=eligible,
        rejection_reason_codes=reasons,
        acceptance_reason_codes=["BPM_KEY_COMPATIBLE_ABOVE_FLOOR"] if eligible else [],
        confidence="N/A -- policy does not model confidence",
        confidence_reason="BPM_KEY_ONLY_EARLY ignores structure/confidence/preservation entirely by design (SimpMusic-class baseline, P0-M1)",
        preferred_transition_class_set=["SIMPLE_CROSSFADE", "FULL_DJ_BLEND"] if eligible else [],
        **_naive_preservation_fields(fixture, t_ms),
    )


def _tail_only_natural_exit_biased_eval(fixture, candidate, intent, floor_override=None) -> EligibilityResult:
    t_ms = candidate["t_ms"]
    fraction = _fraction_consumed(fixture, t_ms)
    structural = bool(candidate.get("in_acceptable_exit_region") or candidate.get("is_outro_tail_opportunity"))
    vocal_high = candidate.get("vocal_collision_risk") == "HIGH"
    floor = floor_override if floor_override is not None else TAIL_ONLY_FRACTION_FLOOR
    eligible = structural and fraction >= floor and not vocal_high
    reasons = []
    if not structural:
        reasons.append("NO_STRUCTURAL_EVIDENCE")
    if fraction < floor:
        reasons.append("BELOW_HARD_LATE_FRACTION_RULE")
    if vocal_high:
        reasons.append("VOCAL_COLLISION_RISK_HIGH")
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        eligible=eligible,
        rejection_reason_codes=reasons,
        acceptance_reason_codes=["LATE_STRUCTURAL_REGION"] if eligible else [],
        confidence=candidate.get("structure_confidence", "NONE"),
        confidence_reason="TAIL_ONLY_NATURAL_EXIT_BIASED uses a single hard late-fraction rule, no duration-normalized structure/preservation model",
        preferred_transition_class_set=["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"] if eligible else [],
        **_naive_preservation_fields(fixture, t_ms),
    )


def _fixed_seconds_before_end_only_eval(fixture, candidate, intent, floor_override=None) -> EligibilityResult:
    t_ms = candidate["t_ms"]
    duration_ms = fixture["duration_ms"]
    remaining_ms = duration_ms - t_ms
    structural = bool(candidate.get("in_acceptable_exit_region") or candidate.get("is_outro_tail_opportunity") or candidate.get("musical_unit_complete"))
    vocal_high = candidate.get("vocal_collision_risk") == "HIGH"
    within_fixed_window = remaining_ms <= FIXED_SECONDS_BEFORE_END_WINDOW_MS
    eligible = structural and within_fixed_window and not vocal_high
    reasons = []
    if not structural:
        reasons.append("NO_STRUCTURAL_EVIDENCE")
    if not within_fixed_window:
        reasons.append(f"OUTSIDE_FIXED_{FIXED_SECONDS_BEFORE_END_WINDOW_MS}MS_BEFORE_END_WINDOW")
    if vocal_high:
        reasons.append("VOCAL_COLLISION_RISK_HIGH")
    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        eligible=eligible,
        rejection_reason_codes=reasons,
        acceptance_reason_codes=["WITHIN_FIXED_SECONDS_WINDOW"] if eligible else [],
        confidence=candidate.get("structure_confidence", "NONE"),
        confidence_reason=(
            f"FIXED_SECONDS_BEFORE_END_ONLY uses one fixed {FIXED_SECONDS_BEFORE_END_WINDOW_MS}ms-before-absolute-end "
            "window regardless of track duration -- deliberately naive, demonstrates spec requirement 'do not use a "
            "fixed N-seconds-before-end rule' by construction"
        ),
        preferred_transition_class_set=["SIMPLE_CROSSFADE"] if eligible else [],
        **_naive_preservation_fields(fixture, t_ms),
    )


def _seamless_engine_eval(fixture, candidate, intent, floor_override=None) -> EligibilityResult:
    return evaluate_candidate(fixture, candidate, intent, floor_override)


def _explicit_highlight_eval(fixture, candidate, intent, floor_override=None) -> EligibilityResult:
    """
    R1 (kept binding by the newest PM comment, section J): the intent gate
    is structural, not caller-convention-only. This policy NEVER silently
    substitutes HIGHLIGHT_EXPLICIT for whatever intent the caller actually
    passed -- if intent != HIGHLIGHT_EXPLICIT, it returns an ineligible
    result carrying an explicit INTENT_POLICY_MISMATCH reason instead of
    evaluating (and possibly transitioning) under a different intent than
    the one the returned decision claims to represent.
    """
    if intent != "HIGHLIGHT_EXPLICIT":
        content_end = _effective_content_end_ms(fixture)
        return EligibilityResult(
            candidate_id=candidate["candidate_id"],
            t_ms=candidate["t_ms"],
            eligible=False,
            rejection_reason_codes=["INTENT_POLICY_MISMATCH"],
            acceptance_reason_codes=[],
            effective_content_end_ms=content_end,
            transition_onset_ms=candidate["t_ms"],
            outgoing_last_audible_ms=candidate["t_ms"],
            outgoing_content_preservation_ratio=round(candidate["t_ms"] / content_end, 4) if content_end else 0.0,
            confidence="N/A -- policy rejected before evaluation due to intent mismatch",
            confidence_reason="EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL only evaluates candidates when intent==HIGHLIGHT_EXPLICIT; it never rewrites a mismatched caller-supplied intent",
            preferred_transition_class_set=[],
        )
    return evaluate_candidate(fixture, candidate, "HIGHLIGHT_EXPLICIT", floor_override)


POLICY_EVAL = {
    "NAIVE_EARLIEST_COMPATIBLE": _naive_earliest_compatible_eval,
    "BPM_KEY_ONLY_EARLY": _bpm_key_only_early_eval,
    "TAIL_ONLY_NATURAL_EXIT_BIASED": _tail_only_natural_exit_biased_eval,
    "FIXED_SECONDS_BEFORE_END_ONLY": _fixed_seconds_before_end_only_eval,
    "SEAMLESS_FULL_TRACK_DEFAULT": _seamless_engine_eval,
    "BALANCED_MIX_RESEARCH_CONTROL": _seamless_engine_eval,
    "EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL": _explicit_highlight_eval,
}

# Policies whose recommended full-track behavior is RANKED among all
# eligible candidates rather than "first eligible wins" (spec section E /
# PM comment R2, still binding). The adversarial/baseline policies are
# intentionally left as greedy-first-eligible -- that greediness is part of
# what makes them adversarial baselines.
RANKED_POLICIES = {"SEAMLESS_FULL_TRACK_DEFAULT", "BALANCED_MIX_RESEARCH_CONTROL"}


def _trace_entry(candidate, result: EligibilityResult, pair_compat=None) -> dict:
    return {
        "candidate_id": result.candidate_id,
        "t_ms": result.t_ms,
        "source": candidate.get("source"),
        "eligible": result.eligible,
        "rejection_reason_codes": result.rejection_reason_codes,
        "acceptance_reason_codes": result.acceptance_reason_codes,
        "effective_content_end_ms": result.effective_content_end_ms,
        "transition_onset_ms": result.transition_onset_ms,
        "transition_onset_ratio": result.transition_onset_ratio,
        "overlap_duration_ms": result.overlap_duration_ms,
        "outgoing_last_audible_ms": result.outgoing_last_audible_ms,
        "outgoing_content_preservation_ratio": result.outgoing_content_preservation_ratio,
        "outgoing_content_lost_ms": result.outgoing_content_lost_ms,
        "preservation_band": result.preservation_band,
        "musical_structure_score": result.musical_structure_score,
        "confidence": result.confidence,
        "preferred_transition_class_set": result.preferred_transition_class_set,
        "energy_continuity_priority": result.energy_continuity_priority,
        # PM REVIEW #2 R1: pair compatibility now participates in ranking
        # itself (policy/ranking.py's sort key), not merely applied to the
        # already-selected winner afterward. A single-track fixture's `pair`
        # (if supplied) is one global value applied uniformly to every
        # candidate -- it can inform ranking but, being uniform, cannot by
        # itself differentiate between candidates on the SAME fixture; true
        # per-boundary differentiation requires policy/boundary.py's
        # per-(exit,entry) compatibility, used by fixtures that model an
        # incoming track.
        "eligible_for_dynamic_mix": bool(pair_compat.overall_dynamic_mix_eligible) if pair_compat is not None else False,
        "eligible_rank": None,  # filled in by ranking for RANKED_POLICIES
    }


def decide_at_time(fixture: dict, policy_name: str, intent: str, evaluation_time_ms: int, floor_override=None, pair: dict = None):
    """
    Time-local query primitive: only candidates with t_ms <= evaluation_time_ms
    are "seen so far". This is what makes PLAY_THROUGH ("nothing eligible has
    been seen yet AND the track has not ended") meaningfully distinct from
    NO_SPECIAL_TRANSITION ("track reached its natural end with nothing
    eligible"). A time-local query CANNOT see future candidates, so it always
    uses greedy first-eligible-so-far semantics -- it is explicitly NOT
    equivalent to the ranked full-track plan (spec "FULL-TRACK VS
    TIME-LOCAL"); decide() below is the canonical offline/full-track planner.
    """
    eval_fn = POLICY_EVAL[policy_name]
    duration_ms = fixture["duration_ms"]
    candidates = fixture["candidates"]
    pair_compat = evaluate_pair_compatibility(pair) if pair is not None else None
    seen_non_end = [c for c in candidates if not c.get("is_end_of_track") and c["t_ms"] <= evaluation_time_ms]
    trace = []
    for c in seen_non_end:
        result = eval_fn(fixture, c, intent, floor_override)
        trace.append(_trace_entry(c, result, pair_compat))
        if result.eligible:
            return build_transition_decision(fixture["fixture_id"], intent, policy_name, result, c, trace, pair)

    if evaluation_time_ms >= duration_ms:
        end_candidate = next(c for c in candidates if c.get("is_end_of_track"))
        result = eval_fn(fixture, end_candidate, intent, floor_override)
        trace.append(_trace_entry(end_candidate, result, pair_compat))
        reason_codes = ["END_OF_TRACK_NATURAL_HANDOFF"] + result.rejection_reason_codes + result.acceptance_reason_codes
        if fixture.get("trailing_dead_air_is_authored_non_musical", False):
            reason_codes.append("TRAILING_DEAD_AIR_TRIMMED_NOT_TRUNCATED")
        return build_fallback_decision(
            fixture["fixture_id"], intent, policy_name, "NO_SPECIAL_TRANSITION",
            reason_codes, trace, confidence=result.confidence,
        )

    return build_fallback_decision(
        fixture["fixture_id"], intent, policy_name, "PLAY_THROUGH",
        ["NO_ELIGIBLE_CANDIDATE_YET_MORE_TRACK_REMAINS"], trace, confidence="N/A -- re-evaluate later",
    )


def decide(fixture: dict, policy_name: str, intent: str, floor_override=None, pair: dict = None):
    """
    Canonical full-track/offline planner: evaluates EVERY non-end candidate
    (order in the fixture's `candidates` array is irrelevant -- see
    ranking.rank_eligible_candidates and the order-invariance tests in
    verify.py), ranks all eligible ones for RANKED_POLICIES, and returns the
    best-ranked candidate's decision. Adversarial baseline policies keep
    greedy first-eligible-in-array-order semantics by design.
    """
    eval_fn = POLICY_EVAL[policy_name]
    duration_ms = fixture["duration_ms"]
    candidates = fixture["candidates"]
    non_end = [c for c in candidates if not c.get("is_end_of_track")]

    if policy_name not in RANKED_POLICIES:
        return decide_at_time(fixture, policy_name, intent, duration_ms, floor_override, pair)

    pair_compat = evaluate_pair_compatibility(pair) if pair is not None else None
    trace = []
    eligible_entries = []
    result_by_candidate_id = {}
    candidate_by_id = {c["candidate_id"]: c for c in non_end}
    for c in non_end:
        result = eval_fn(fixture, c, intent, floor_override)
        entry = _trace_entry(c, result, pair_compat)
        trace.append(entry)
        result_by_candidate_id[c["candidate_id"]] = result
        if result.eligible:
            eligible_entries.append(entry)

    if eligible_entries:
        ranked = rank_eligible_candidates(eligible_entries)
        for entry in ranked:
            for t in trace:
                if t["candidate_id"] == entry["candidate_id"]:
                    t["eligible_rank"] = entry["eligible_rank"]
        winner_entry = ranked[0]
        winner_candidate = candidate_by_id[winner_entry["candidate_id"]]
        winner_result = result_by_candidate_id[winner_entry["candidate_id"]]
        return build_transition_decision(fixture["fixture_id"], intent, policy_name, winner_result, winner_candidate, trace, pair)

    end_candidate = next(c for c in candidates if c.get("is_end_of_track"))
    end_result = eval_fn(fixture, end_candidate, intent, floor_override)
    trace.append(_trace_entry(end_candidate, end_result, pair_compat))
    reason_codes = ["END_OF_TRACK_NATURAL_HANDOFF"] + end_result.rejection_reason_codes + end_result.acceptance_reason_codes
    if fixture.get("trailing_dead_air_is_authored_non_musical", False):
        reason_codes.append("TRAILING_DEAD_AIR_TRIMMED_NOT_TRUNCATED")
    return build_fallback_decision(
        fixture["fixture_id"], intent, policy_name, "NO_SPECIAL_TRANSITION",
        reason_codes, trace, confidence=end_result.confidence,
    )
