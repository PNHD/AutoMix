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
from .contract import build_boundary_transition_decision, build_fallback_decision, resolve_alignment_targets

INCOMING_REASON = {
    "ENTRY_AT_TRACK_START": "t_ms == 0; always a valid entry point",
    "AUTHORED_LEADING_SILENCE_SKIPPED": "entry candidate skips only authored non-musical leading silence (leading_silence_is_authored_non_musical=true), never real content",
    "PHRASE_CUE_EVIDENCE_PRESENT": "entry candidate is supported by explicit phrase/section or cue evidence, justifying a later-than-zero start",
    "ENTRY_SKIPS_MEANINGFUL_INTRO_WITHOUT_EVIDENCE": "entry candidate starts after 0ms with no authored-silence-skip or phrase/cue evidence -- would silently remove meaningful intro content; rejected",
    "NO_ELIGIBLE_ENTRY_FOR_ANY_SAFE_EXIT": "at least one outgoing exit was safe, but no incoming entry candidate was eligible for any of them",
    "NO_SAFE_OUTGOING_EXIT": "no outgoing candidate cleared the preservation/structural/confidence/vocal-safety guards; incoming entry was never evaluated",
    "FULL_DJ_BLEND_WITHHELD_NO_BOUNDARY_ALIGNMENT_EVIDENCE": "R5 (PM REVIEW #3) / A5 (alignment-anchor contract separation): FULL_DJ_BLEND requires a RESOLVED beat AND downbeat alignment target (policy/contract.resolve_alignment_targets) on BOTH the outgoing exit AND the incoming entry candidates of THIS specific boundary -- pair-level beat/downbeat CONFIDENCE alone is not renderable alignment evidence",
    "BOUNDARY_ALIGNMENT_EVIDENCE_PRESENT": "both the outgoing exit and incoming entry candidates of this boundary carry resolved beat/downbeat alignment evidence",
    "SEPARATE_INCOMING_ALIGNMENT_ANCHOR_PRESENT": "A7: the incoming candidate's resolved alignment target(s) differ from its own audible entry t_ms -- an explicit, separate alignment anchor, not a coincidental match",
    "ENTRY_AND_ALIGNMENT_ANCHOR_COINCIDE": "A7: the incoming candidate's resolved alignment target(s) equal its own audible entry t_ms (legacy behavior, or an explicit anchor authored at the same point)",
    "PARTIAL_INCOMING_ALIGNMENT_EVIDENCE": "A1/A10: the incoming candidate supplied only ONE of beat_alignment_target_ms/downbeat_alignment_target_ms explicitly -- the missing side is never backfilled from t_ms, so FULL_DJ_BLEND is withheld",
    "INVALID_INCOMING_ALIGNMENT_TARGET_PRECEDES_ENTRY": "A4: an incoming alignment target preceded the candidate's own audible entry t_ms -- rejected outright (fail closed), never clamped or rewritten",
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

            # R5 (PM REVIEW #3) / A5 (alignment-anchor contract separation):
            # FULL_DJ_BLEND additionally requires RESOLVED TARGET PRESENCE
            # on BOTH sides of THIS specific boundary -- pair-level
            # beat/downbeat CONFIDENCE (compat.beat_compatibility/
            # downbeat_compatibility, already required above) is analyzer
            # trust, not proof that the SELECTED exit/entry candidates
            # actually carry renderable alignment targets. Each side's
            # target is resolved by the SAME canonical helper
            # (policy/contract.resolve_alignment_targets): EXPLICIT
            # candidate-level fields when present (A1), else the legacy
            # beat_downbeat_aligned boolean (unchanged behavior for
            # TX-01..07).
            exit_beat_target, exit_downbeat_target, exit_alignment_source = resolve_alignment_targets(exit_c)
            entry_beat_target, entry_downbeat_target, entry_alignment_source = resolve_alignment_targets(entry_c)
            entry_t_ms = entry_c["t_ms"]

            # A4: an incoming alignment target must never precede the
            # candidate's own audible entry -- fail closed (withhold),
            # never clamp/rewrite the timestamp. Tracked PER SIDE (not only
            # combined) so the decision builder can withhold exactly the
            # affected action (beat vs bar) instead of both (PM REVIEW --
            # pre-flight consistency fix folded into final real-corpus
            # replay).
            incoming_beat_alignment_invalid = entry_beat_target is not None and entry_beat_target < entry_t_ms
            incoming_downbeat_alignment_invalid = entry_downbeat_target is not None and entry_downbeat_target < entry_t_ms
            invalid_incoming_alignment = incoming_beat_alignment_invalid or incoming_downbeat_alignment_invalid
            # A7 provenance: does the resolved alignment target genuinely
            # differ from the candidate's own entry t_ms? (Independent of
            # validity -- an invalid target still "differs".)
            incoming_alignment_separate_from_entry = bool(
                entry_alignment_source != "NONE" and (
                    (entry_beat_target is not None and entry_beat_target != entry_t_ms)
                    or (entry_downbeat_target is not None and entry_downbeat_target != entry_t_ms)
                )
            )

            if invalid_incoming_alignment:
                entry_reasons = entry_reasons + ["INVALID_INCOMING_ALIGNMENT_TARGET_PRECEDES_ENTRY"]
            elif entry_alignment_source != "NONE":
                if entry_beat_target is None or entry_downbeat_target is None:
                    entry_reasons = entry_reasons + ["PARTIAL_INCOMING_ALIGNMENT_EVIDENCE"]
                elif incoming_alignment_separate_from_entry:
                    entry_reasons = entry_reasons + ["SEPARATE_INCOMING_ALIGNMENT_ANCHOR_PRESENT"]
                else:
                    entry_reasons = entry_reasons + ["ENTRY_AND_ALIGNMENT_ANCHOR_COINCIDE"]

            boundary_alignable = (
                exit_beat_target is not None and exit_downbeat_target is not None
                and entry_beat_target is not None and entry_downbeat_target is not None
                and not invalid_incoming_alignment
            )
            if not boundary_alignable and "FULL_DJ_BLEND" in allowed_classes:
                allowed_classes = [c for c in allowed_classes if c != "FULL_DJ_BLEND"]
                entry_reasons = entry_reasons + ["FULL_DJ_BLEND_WITHHELD_NO_BOUNDARY_ALIGNMENT_EVIDENCE"]
            elif boundary_alignable and "FULL_DJ_BLEND" in allowed_classes:
                entry_reasons = entry_reasons + ["BOUNDARY_ALIGNMENT_EVIDENCE_PRESENT"]

            # R7 (PM REVIEW #3): deterministic pitch policy. COMPATIBLE
            # harmonic -> no correction needed, full envelope. A validated
            # structured non-tonal exception -> no correction needed AND no
            # envelope is offered either (there is no tonal basis to justify
            # any pitch range). Anything else -> FULL_DJ_BLEND is already
            # withheld by the hard gate, so pitch is simply unknown/unused.
            if compat.harmonic_compatibility == "COMPATIBLE":
                required_pitch = 0
                pitch_range = (-3, 3)
            elif compat.harmonic_exception_applied:
                required_pitch = 0
                pitch_range = (0, 0)
            else:
                required_pitch = None
                pitch_range = (None, None)

            entry_struct = _entry_structure_score(entry_c)
            combined_structure_score = round((exit_result.musical_structure_score + entry_struct) / 2, 4)

            trace_entry = {
                "outgoing_candidate_id": exit_c["candidate_id"],
                "incoming_candidate_id": entry_c["candidate_id"],
                "eligible": bool(entry_ok),
                "entry_reason_codes": entry_reasons,
                "outgoing_content_preservation_ratio": exit_result.outgoing_content_preservation_ratio,
                "preservation_band": exit_result.preservation_band,
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
                "boundary_beat_downbeat_alignable": boundary_alignable,
                # A7 (alignment-anchor contract separation) trace provenance
                # -- present for EVERY boundary candidate, not only the
                # winner.
                "incoming_entry_t_ms": entry_t_ms,
                "incoming_beat_alignment_target_ms": entry_beat_target,
                "incoming_downbeat_alignment_target_ms": entry_downbeat_target,
                "incoming_beat_alignment_invalid": incoming_beat_alignment_invalid,
                "incoming_downbeat_alignment_invalid": incoming_downbeat_alignment_invalid,
                "incoming_alignment_target_source": entry_alignment_source,
                "incoming_alignment_separate_from_entry": incoming_alignment_separate_from_entry,
                "outgoing_beat_alignment_target_ms": exit_beat_target,
                "outgoing_downbeat_alignment_target_ms": exit_downbeat_target,
                "outgoing_alignment_target_source": exit_alignment_source,
                "pair_compatibility_components": compat.to_dict(),
                "energy_continuity_priority": compat.energy_continuity,
                "required_tempo_ratio": compat.required_tempo_ratio,
                "required_pitch_shift_semitones": required_pitch,
                "permitted_pitch_shift_semitones_range": pitch_range,
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
