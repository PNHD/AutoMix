"""
P0-M3-R2 PM REVIEW #2 repair (R1 + R2) -- complete transition BOUNDARY
planning.

The prior pass ranked outgoing exit candidates in isolation, then applied
one global pair-compatibility object only AFTER a winner was already
selected. That structurally prevented pair compatibility from ever
influencing WHICH near-end exit gets chosen, and left incoming-entry
planning as a hardcoded next_track_entry_window_ms = {0, 0} placeholder.

This module ranks COMPLETE boundary plans instead:

    outgoing exit candidate
        x incoming entry candidate
        x pair compatibility evaluated AT that specific (exit, entry) pair

Safety ordering is structural, not just behavioral (R1's explicit
requirement -- "pair compatibility may rank only among already-safe
near-end outgoing candidates; it must NEVER authorize leaving the outgoing
song early"):

  Phase 1 -- filter outgoing candidates to the SAFE set using the existing
  eligibility guards (policy/eligibility.py: structural evidence,
  confidence, vocal safety, preservation floor). Pair compatibility is
  never consulted in this phase.

  Phase 2 -- for every (safe exit, entry) combination, evaluate entry
  eligibility (policy/boundary.py's own guard: never silently skip
  meaningful incoming intro content) and pair compatibility AT that
  boundary, then rank all eligible boundary plans via
  policy/ranking.rank_boundary_plans (preservation tier first, then
  pair-compatibility tier, then structure/energy/confidence, then a
  content-keyed tie-break -- never array position).
"""

from . import eligibility as elig_mod
from .compatibility import evaluate_pair_compatibility, downgrade_transition_class_set
from .ranking import rank_boundary_plans
from .contract import build_boundary_transition_decision, build_fallback_decision

INCOMING_REASON = {
    "ENTRY_AT_TRACK_START": "t_ms == 0; always a valid entry point",
    "AUTHORED_LEADING_SILENCE_SKIPPED": "entry candidate skips only authored non-musical leading silence (leading_silence_is_authored_non_musical=true), never real content",
    "PHRASE_CUE_EVIDENCE_PRESENT": "entry candidate is supported by explicit phrase/section or cue evidence, justifying a later-than-zero start",
    "ENTRY_SKIPS_MEANINGFUL_INTRO_WITHOUT_EVIDENCE": "entry candidate starts after 0ms with no authored-silence-skip or phrase/cue evidence -- would silently remove meaningful intro content; rejected",
    "NO_ELIGIBLE_ENTRY_FOR_ANY_SAFE_EXIT": "at least one outgoing exit was safe, but no incoming entry candidate was eligible for any of them",
    "NO_SAFE_OUTGOING_EXIT": "no outgoing candidate cleared the preservation/structural/confidence/vocal-safety guards; incoming entry was never evaluated",
}


def incoming_effective_content_start_ms(incoming_track: dict) -> int:
    if incoming_track.get("leading_silence_is_authored_non_musical", False):
        return incoming_track.get("leading_silence_ms", 0)
    return 0


def _entry_eligibility(incoming_track: dict, entry_candidate: dict):
    t_ms = entry_candidate["t_ms"]
    if t_ms == 0:
        return True, ["ENTRY_AT_TRACK_START"]
    content_start = incoming_effective_content_start_ms(incoming_track)
    if entry_candidate.get("is_authored_silence_skip") and t_ms <= content_start:
        return True, ["AUTHORED_LEADING_SILENCE_SKIPPED"]
    if entry_candidate.get("phrase_section_evidence") or entry_candidate.get("cue_evidence"):
        return True, ["PHRASE_CUE_EVIDENCE_PRESENT"]
    return False, ["ENTRY_SKIPS_MEANINGFUL_INTRO_WITHOUT_EVIDENCE"]


def _entry_structure_score(entry_candidate: dict) -> float:
    score = 0.0
    if entry_candidate.get("phrase_section_evidence"):
        score += 0.5
    if entry_candidate.get("beat_downbeat_aligned"):
        score += 0.5
    return round(score, 4)


def _boundary_pair_compat(tx_fixture: dict, exit_id: str, entry_id: str):
    outgoing_track = tx_fixture["outgoing_track"]
    incoming_track = tx_fixture["incoming_track"]
    base_pair = {
        "outgoing": {"genre_tags": outgoing_track.get("genre_tags", []), "bpm": outgoing_track.get("bpm", 0)},
        "incoming": {"genre_tags": incoming_track.get("genre_tags", []), "bpm": incoming_track.get("bpm", 0)},
    }
    base_pair.update(tx_fixture.get("pair_base", {}))
    override = tx_fixture.get("boundary_overrides", {}).get(f"{exit_id}|{entry_id}")
    if override:
        base_pair = {**base_pair, **override}
    return evaluate_pair_compatibility(base_pair)


def plan_transition_boundary(tx_fixture: dict, intent: str, floor_override=None, policy_name: str = "SEAMLESS_FULL_TRACK_DEFAULT_BOUNDARY"):
    """
    Canonical full-track boundary planner (the boundary-plan analogue of
    policy/policies.py's decide()). Evaluates every (safe exit, entry)
    combination and returns the PlannerDecision for the best-ranked
    complete boundary plan, with every combination preserved in the trace.
    """
    outgoing_track = tx_fixture["outgoing_track"]
    incoming_track = tx_fixture["incoming_track"]
    transition_id = tx_fixture["transition_id"]

    exit_candidates = [c for c in outgoing_track["candidates"] if not c.get("is_end_of_track")]
    entry_candidates = incoming_track["candidates"]

    # Phase 1: SAFE exit filter -- pair compatibility is NEVER consulted
    # here (R1: it must never authorize an early exit).
    safe_exits = []
    exit_result_by_id = {}
    for c in exit_candidates:
        result = elig_mod.evaluate_candidate(outgoing_track, c, intent, floor_override)
        exit_result_by_id[c["candidate_id"]] = result
        if result.eligible:
            safe_exits.append(c)

    if not safe_exits:
        end_candidate = next(c for c in outgoing_track["candidates"] if c.get("is_end_of_track"))
        end_result = elig_mod.evaluate_candidate(outgoing_track, end_candidate, intent, floor_override)
        trace = [{
            "outgoing_candidate_id": end_candidate["candidate_id"],
            "incoming_candidate_id": None,
            "eligible": False,
            "outgoing_content_preservation_ratio": end_result.outgoing_content_preservation_ratio,
            "effective_content_end_ms": end_result.effective_content_end_ms,
            "selected": False,
        }]
        reason_codes = ["END_OF_TRACK_NATURAL_HANDOFF", "NO_SAFE_OUTGOING_EXIT"] + end_result.rejection_reason_codes + end_result.acceptance_reason_codes
        return build_fallback_decision(transition_id, intent, policy_name, "NO_SPECIAL_TRANSITION", reason_codes, trace, confidence=end_result.confidence)

    boundary_trace = []
    eligible_boundaries = []

    for exit_c in safe_exits:
        exit_result = exit_result_by_id[exit_c["candidate_id"]]
        for entry_c in entry_candidates:
            entry_ok, entry_reasons = _entry_eligibility(incoming_track, entry_c)
            compat = _boundary_pair_compat(tx_fixture, exit_c["candidate_id"], entry_c["candidate_id"])
            allowed_classes = downgrade_transition_class_set(exit_result.preferred_transition_class_set, compat)
            entry_struct = _entry_structure_score(entry_c)
            combined_structure_score = round((exit_result.musical_structure_score + entry_struct) / 2, 4)

            trace_entry = {
                "outgoing_candidate_id": exit_c["candidate_id"],
                "incoming_candidate_id": entry_c["candidate_id"],
                "eligible": bool(entry_ok),
                "entry_reason_codes": entry_reasons,
                "outgoing_content_preservation_ratio": exit_result.outgoing_content_preservation_ratio,
                "musical_structure_score": combined_structure_score,
                "outgoing_structure_score": exit_result.musical_structure_score,
                "incoming_structure_score": entry_struct,
                "outgoing_preservation_components": {
                    "effective_content_end_ms": exit_result.effective_content_end_ms,
                    "transition_onset_ms": exit_result.transition_onset_ms,
                    "outgoing_last_audible_ms": exit_result.outgoing_last_audible_ms,
                    "overlap_duration_ms": exit_result.overlap_duration_ms,
                    "outgoing_content_lost_ms": exit_result.outgoing_content_lost_ms,
                },
                "outgoing_structure_components": {
                    "in_acceptable_exit_region": bool(exit_c.get("in_acceptable_exit_region")),
                    "is_outro_tail_opportunity": bool(exit_c.get("is_outro_tail_opportunity")),
                    "musical_unit_complete": bool(exit_c.get("musical_unit_complete")),
                    "beat_downbeat_aligned": bool(exit_c.get("beat_downbeat_aligned")),
                },
                "pair_compatibility_components": compat.to_dict(),
                "energy_continuity_priority": compat.energy_continuity,
                "required_tempo_ratio": compat.required_tempo_ratio,
                "required_pitch_shift_semitones": 0 if compat.harmonic_compatibility == "COMPATIBLE" else None,
                "eligible_for_dynamic_mix": compat.overall_dynamic_mix_eligible,
                "allowed_transition_class_set": allowed_classes,
                "confidence": exit_result.confidence,
                "effective_content_end_ms": exit_result.effective_content_end_ms,
                "boundary_rank": None,
                "selected": False,
                "selection_reason_codes": [],
            }
            boundary_trace.append(trace_entry)
            if entry_ok:
                eligible_boundaries.append(trace_entry)

    if not eligible_boundaries:
        reason_codes = ["NO_ELIGIBLE_ENTRY_FOR_ANY_SAFE_EXIT"]
        return build_fallback_decision(transition_id, intent, policy_name, "NO_SPECIAL_TRANSITION", reason_codes, boundary_trace, confidence="LOW")

    ranked = rank_boundary_plans(eligible_boundaries)
    winner = ranked[0]
    winner["selected"] = True
    winner["selection_reason_codes"] = ["BEST_RANKED_COMPLETE_BOUNDARY_PLAN"]

    exit_by_id = {c["candidate_id"]: c for c in exit_candidates}
    entry_by_id = {c["candidate_id"]: c for c in entry_candidates}
    winner_exit = exit_by_id[winner["outgoing_candidate_id"]]
    winner_entry_candidate = entry_by_id[winner["incoming_candidate_id"]]
    winner_exit_result = exit_result_by_id[winner["outgoing_candidate_id"]]

    return build_boundary_transition_decision(
        fixture_id=transition_id,
        intent=intent,
        policy_name=policy_name,
        exit_candidate=winner_exit,
        exit_result=winner_exit_result,
        entry_candidate=winner_entry_candidate,
        incoming_effective_content_start_ms=incoming_effective_content_start_ms(incoming_track),
        incoming_entry_reason_codes=winner["entry_reason_codes"],
        winner_entry=winner,
        boundary_trace=boundary_trace,
    )
