"""
P0-M3-R2 (Apple-like redesign, PM REVIEW #2 repair) -- planner output
contract.

The smallest provider-independent handoff the P0-M3-R3 DSP-execution pass
needs. This module defines only the SHAPE of that handoff; it never
implements Signalsmith Stretch / Rubber Band / any DSP execution (AC16).

PM REVIEW #2 repairs applied here:
- R2: transition_onset_window_ms is now a REAL narrow window (an exact cue
  timestamp, or an explicit authored onset region) -- never
  chosen_onset..effective_content_end.
- R2: next_track_entry_window_ms is populated from a real incoming-entry
  candidate when one was planned (policy/boundary.py); it is explicitly
  None (never a fabricated 0..0) when no incoming track was modeled for a
  given fixture.
- R3: permitted_tempo_ratio / permitted_pitch_shift (ambiguous, unitless)
  are replaced by required_tempo_ratio + permitted_tempo_ratio_max_deviation
  and required_pitch_shift_semitones + permitted_pitch_shift_semitones_min/max.
- Alignment contract: beat_alignment_target/downbeat_alignment_target
  (which exposed a single outgoing timestamp as if it specified both sides)
  are replaced by outgoing_*/incoming_* pairs plus beat_phase_relation /
  bar_phase_relation.

P0-M3-R3 alignment-anchor contract separation (RM014 diagnostic,
docs/research/P0-M3-R3-RM014-ENTRY-ANCHOR-FEASIBILITY.md, "Case B"):
`entry_candidate["t_ms"]` means ONLY the audible/source entry time; it never
silently changes meaning. `resolve_alignment_targets()` below resolves a
candidate's beat/downbeat ALIGNMENT reference as a separate, optional
concept -- a later alignment anchor never moves the audible entry window
(see policy/boundary.py's incoming-entry planning, unchanged by this repair).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

from .compatibility import evaluate_pair_compatibility, downgrade_transition_class_set, PERMITTED_MAX_PITCH_SHIFT_SEMITONES
from .compatibility import MAX_JUSTIFIED_TEMPO_STRETCH_PCT as PERMITTED_TEMPO_RATIO_MAX_DEVIATION


@dataclass
class PlannerDecision:
    fixture_id: str
    listener_intent: str
    policy_name: str

    # AC10: PLAY_THROUGH / NO_SPECIAL_TRANSITION are first-class results,
    # not error states. decision_type is one of:
    #   "TRANSITION" | "PLAY_THROUGH" | "NO_SPECIAL_TRANSITION"
    decision_type: str

    # --- Outgoing side: song-preservation / timing (spec section B) ---
    current_track_effective_content_end_ms: Optional[int] = None
    selected_outgoing_exit_candidate_id: Optional[str] = None
    # A REAL narrow onset window: {t_start_ms, t_end_ms} where t_start==t_end
    # for an exact cue timestamp, or an explicit authored narrow region --
    # NEVER onset..effective_content_end (R2 repair).
    transition_onset_window_ms: Optional[dict] = None
    outgoing_last_audible_target_ms: Optional[int] = None
    outgoing_content_preservation_target: Optional[float] = None

    # --- Incoming side: entry planning (R2 repair -- no more universal 0,0) ---
    selected_incoming_entry_candidate_id: Optional[str] = None
    incoming_effective_content_start_ms: Optional[int] = None
    # {t_start_ms, t_end_ms}. None (not {0,0}) when no incoming track was
    # modeled for this fixture -- see incoming_entry_reason_codes.
    next_track_entry_window_ms: Optional[dict] = None
    incoming_entry_reason_codes: list = field(default_factory=list)
    incoming_phrase_section_evidence: Optional[bool] = None

    # --- Transition class / pair compatibility (spec sections D/E) ---
    allowed_transition_class_set: list = field(default_factory=list)
    pair_compatibility_components: Optional[dict] = None    # None when no pair was supplied/computed (compatibility unproven)

    # --- Alignment contract: BOTH sides identified explicitly, never one
    # outgoing timestamp reused as if it specified the incoming side too. ---
    outgoing_beat_alignment_target_ms: Optional[int] = None
    incoming_beat_alignment_target_ms: Optional[int] = None
    outgoing_downbeat_alignment_target_ms: Optional[int] = None
    incoming_downbeat_alignment_target_ms: Optional[int] = None
    # R9 (PM REVIEW #3) repair: these are OBSERVED-relation fields only, and
    # this project has no beat-index/bar-position metadata to ever actually
    # DERIVE a measured phase relation -- so they must never claim "ALIGNED"
    # (that was fabricated from eligibility, not measured). Valid values:
    # "NOT_MEASURED" (both-side targets exist but no real phase measurement
    # was computed) | "NOT_APPLICABLE" (one or both targets are missing).
    beat_phase_relation: str = "NOT_APPLICABLE"
    bar_phase_relation: str = "NOT_APPLICABLE"
    # R9 (new): the RENDER-PLAN action for the DSP engine, explicitly
    # distinct from the (never-fabricated) observed-relation fields above.
    # "NOT_APPLICABLE" when either side's target is missing.
    beat_alignment_action: str = "NOT_APPLICABLE"
    bar_alignment_action: str = "NOT_APPLICABLE"

    # --- Tempo/pitch contract (R3 repair -- unambiguous units/semantics) ---
    required_tempo_ratio: Optional[float] = None                    # literal playback-rate ratio needed to beat-match
    permitted_tempo_ratio_max_deviation: Optional[float] = None      # max |ratio - 1.0| tolerated for FULL_DJ_BLEND; a DEVIATION, never a ratio itself
    required_pitch_shift_semitones: Optional[int] = None
    permitted_pitch_shift_semitones_min: Optional[int] = None
    permitted_pitch_shift_semitones_max: Optional[int] = None

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

    # Full per-(outgoing,incoming) boundary evaluation trace, including
    # boundary_rank/selected/selection_reason_codes for every candidate
    # combination considered -- not merely the winner (PM REVIEW #2: "Do
    # not stop trace generation at the winner").
    candidate_rank_trace: list = field(default_factory=list)

    # Retained for backward-compatible field name; identical to
    # candidate_rank_trace.
    candidate_trace: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def resolve_alignment_targets(candidate: dict):
    """
    A1 (alignment-anchor contract separation): resolves a candidate's
    beat/downbeat ALIGNMENT reference independently of its audible
    entry/exit timestamp (candidate["t_ms"], which keeps its existing
    meaning unchanged everywhere else -- see policy/boundary.py's
    incoming-entry window, which is NEVER derived from this function).

    EXPLICIT mode: if EITHER `beat_alignment_target_ms` or
    `downbeat_alignment_target_ms` is present on the candidate, EXPLICIT
    mode applies. A missing field is NOT backfilled from t_ms -- a
    partially explicit candidate stays partially known (A1: "explicit mode
    always wins over legacy mode").

    LEGACY mode: only when NEITHER explicit field is present. Reproduces
    the pre-existing `beat_downbeat_aligned` behavior exactly: both targets
    equal t_ms when true, else both None.

    Returns (beat_target_ms, downbeat_target_ms, source) where source is
    one of "EXPLICIT" | "LEGACY_T_MS" | "NONE".
    """
    has_explicit_beat = "beat_alignment_target_ms" in candidate
    has_explicit_downbeat = "downbeat_alignment_target_ms" in candidate
    if has_explicit_beat or has_explicit_downbeat:
        beat_target = candidate.get("beat_alignment_target_ms") if has_explicit_beat else None
        downbeat_target = candidate.get("downbeat_alignment_target_ms") if has_explicit_downbeat else None
        return beat_target, downbeat_target, "EXPLICIT"
    if candidate.get("beat_downbeat_aligned"):
        t_ms = candidate["t_ms"]
        return t_ms, t_ms, "LEGACY_T_MS"
    return None, None, "NONE"


def _compatibility_payload(pair: Optional[dict]):
    if pair is None:
        return None, None
    result = evaluate_pair_compatibility(pair)
    return result, result.to_dict()


def _onset_window(candidate: dict, t_ms: int) -> dict:
    """
    R2 repair: a REAL narrow onset window. If the candidate carries an
    explicit authored `onset_window_ms: [start, end]` region, use it
    verbatim. Otherwise the candidate represents an exact cue timestamp --
    t_start_ms == t_end_ms. Never onset..effective_content_end.
    """
    region = candidate.get("onset_window_ms")
    if region:
        return {"t_start_ms": region[0], "t_end_ms": region[1]}
    return {"t_start_ms": t_ms, "t_end_ms": t_ms}


def build_transition_decision(fixture_id, intent, policy_name, chosen_eligibility, candidate, candidate_trace, pair=None):
    """
    Legacy single-track (outgoing-exit-only) builder, used by fixtures that
    do not model an incoming track at all (the original 14 timing
    fixtures, letters A-N). Pair compatibility, if supplied, is a single
    GLOBAL value applied uniformly -- it cannot differentiate between
    candidates (that requires policy/boundary.py's per-boundary planner,
    used by fixtures that DO model incoming entries).
    """
    compat_result, compat_payload = _compatibility_payload(pair)
    allowed_class_set = downgrade_transition_class_set(chosen_eligibility.preferred_transition_class_set, compat_result)

    required_tempo_ratio = None
    required_pitch_shift = None
    permitted_tempo_dev = None
    permitted_pitch_min = None
    permitted_pitch_max = None
    if "FULL_DJ_BLEND" in allowed_class_set and compat_result is not None:
        required_tempo_ratio = compat_result.required_tempo_ratio
        permitted_tempo_dev = PERMITTED_TEMPO_RATIO_MAX_DEVIATION
        # R7 (PM REVIEW #3): deterministic pitch policy, mirrored from
        # policy/boundary.py's per-boundary logic.
        if compat_result.harmonic_compatibility == "COMPATIBLE":
            required_pitch_shift = 0
            permitted_pitch_min, permitted_pitch_max = -PERMITTED_MAX_PITCH_SHIFT_SEMITONES, PERMITTED_MAX_PITCH_SHIFT_SEMITONES
        elif compat_result.harmonic_exception_applied:
            required_pitch_shift = 0
            permitted_pitch_min, permitted_pitch_max = 0, 0

    onset_window = _onset_window(candidate, chosen_eligibility.transition_onset_ms)

    vocal_constraint = "NO_HIGH_RISK_OVERLAP_PERMITTED"
    bass_constraint = "NO_HIGH_RISK_OVERLAP_PERMITTED"
    energy_target = "MAINTAIN_OR_INCREASE_MOMENTUM_WHERE_PAIR_COMPATIBLE"
    if compat_result is not None:
        vocal_constraint = f"PAIR_VOCAL_COLLISION_RISK={compat_result.vocal_collision_risk}"
        bass_constraint = f"PAIR_BASS_PERCUSSION_COLLISION_RISK={compat_result.bass_percussion_collision_risk}"
        energy_target = f"PAIR_ENERGY_CONTINUITY={compat_result.energy_continuity}"

    outgoing_beat_target, outgoing_downbeat_target, _outgoing_alignment_source = resolve_alignment_targets(candidate)

    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type="TRANSITION",
        current_track_effective_content_end_ms=chosen_eligibility.effective_content_end_ms,
        selected_outgoing_exit_candidate_id=candidate.get("candidate_id"),
        transition_onset_window_ms=onset_window,
        outgoing_last_audible_target_ms=chosen_eligibility.outgoing_last_audible_ms,
        outgoing_content_preservation_target=chosen_eligibility.outgoing_content_preservation_ratio,
        selected_incoming_entry_candidate_id=None,
        incoming_effective_content_start_ms=None,
        next_track_entry_window_ms=None,
        incoming_entry_reason_codes=["INCOMING_ENTRY_NOT_MODELED_FOR_THIS_FIXTURE"],
        incoming_phrase_section_evidence=None,
        allowed_transition_class_set=allowed_class_set,
        pair_compatibility_components=compat_payload,
        outgoing_beat_alignment_target_ms=outgoing_beat_target,
        incoming_beat_alignment_target_ms=None,
        outgoing_downbeat_alignment_target_ms=outgoing_downbeat_target,
        incoming_downbeat_alignment_target_ms=None,
        beat_phase_relation="NOT_APPLICABLE",
        bar_phase_relation="NOT_APPLICABLE",
        required_tempo_ratio=required_tempo_ratio,
        permitted_tempo_ratio_max_deviation=permitted_tempo_dev,
        required_pitch_shift_semitones=required_pitch_shift,
        permitted_pitch_shift_semitones_min=permitted_pitch_min,
        permitted_pitch_shift_semitones_max=permitted_pitch_max,
        energy_continuity_target=energy_target,
        vocal_collision_constraints=vocal_constraint,
        bass_collision_constraints=bass_constraint,
        analysis_confidence=chosen_eligibility.confidence,
        reason_codes=chosen_eligibility.acceptance_reason_codes,
        candidate_rank_trace=candidate_trace,
        candidate_trace=candidate_trace,
    )


def build_boundary_transition_decision(
    fixture_id, intent, policy_name,
    exit_candidate, exit_result, entry_candidate,
    incoming_effective_content_start_ms, incoming_entry_reason_codes,
    winner_entry, boundary_trace,
):
    """
    New boundary-plan builder (R1/R2 repair): the winner is a complete
    (outgoing exit, incoming entry, pair compatibility AT that boundary)
    plan, not an outgoing exit selected in isolation.
    """
    compat_payload = winner_entry["pair_compatibility_components"]
    allowed_class_set = winner_entry["allowed_transition_class_set"]

    # A1/A6 (alignment-anchor contract separation): the SAME canonical
    # resolver is used for both sides. In LEGACY mode (no explicit
    # candidate-level alignment fields) this reproduces the prior coupled
    # t_ms-reuse behavior exactly -- TX-01..07 are unaffected. In EXPLICIT
    # mode (e.g. TX-08), the incoming alignment reference is resolved
    # independently of entry_candidate["t_ms"], which keeps its own,
    # unchanged meaning as the audible/source entry time (see
    # `entry_window` below, which is NEVER derived from these targets).
    outgoing_beat_target, outgoing_downbeat_target, _outgoing_alignment_source = resolve_alignment_targets(exit_candidate)
    incoming_beat_target, incoming_downbeat_target, _incoming_alignment_source = resolve_alignment_targets(entry_candidate)

    # R9 (PM REVIEW #3) repair: beat_phase_relation/bar_phase_relation are
    # OBSERVED-relation fields. This project has no beat-index/bar-position
    # metadata to derive a real measured phase from, so they must NEVER
    # claim "ALIGNED" -- that was previously fabricated from
    # eligible_for_dynamic_mix, not measured. beat_alignment_action/
    # bar_alignment_action are the separate, explicit RENDER-PLAN
    # instruction for the DSP engine.
    #
    # PM REVIEW (pre-flight consistency fix, folded into final real-corpus
    # replay): beat and bar/downbeat are INDEPENDENT presence checks -- the
    # PARTIAL EXPLICIT alignment mode (A1/A10) means a boundary can have a
    # known beat target with no downbeat target, or vice versa. Deriving
    # both pairs of fields from a single both_beat_targets_known flag let a
    # bar/downbeat action leak out when only the beat side was actually
    # known. validated/actionable per-side status is read from
    # winner_entry (computed once in policy/boundary.py, not recomputed
    # here) so an incoming target that precedes its own audible entry
    # forces NOT_APPLICABLE on exactly the affected action -- the raw
    # (unclamped) target values above remain visible for diagnostic
    # provenance regardless.
    incoming_beat_invalid = winner_entry.get("incoming_beat_alignment_invalid", False)
    incoming_downbeat_invalid = winner_entry.get("incoming_downbeat_alignment_invalid", False)
    both_beat_targets_known = (
        outgoing_beat_target is not None
        and incoming_beat_target is not None
        and not incoming_beat_invalid
    )
    both_downbeat_targets_known = (
        outgoing_downbeat_target is not None
        and incoming_downbeat_target is not None
        and not incoming_downbeat_invalid
    )
    beat_phase_relation = "NOT_MEASURED" if both_beat_targets_known else "NOT_APPLICABLE"
    bar_phase_relation = "NOT_MEASURED" if both_downbeat_targets_known else "NOT_APPLICABLE"
    beat_alignment_action = "ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET" if both_beat_targets_known else "NOT_APPLICABLE"
    bar_alignment_action = "ALIGN_OUTGOING_DOWNBEAT_TARGET_TO_INCOMING_DOWNBEAT_TARGET" if both_downbeat_targets_known else "NOT_APPLICABLE"

    required_tempo_ratio = None
    required_pitch_shift = None
    permitted_tempo_dev = None
    permitted_pitch_min = None
    permitted_pitch_max = None
    if "FULL_DJ_BLEND" in allowed_class_set:
        required_tempo_ratio = winner_entry["required_tempo_ratio"]
        permitted_tempo_dev = PERMITTED_TEMPO_RATIO_MAX_DEVIATION
        # R7 (PM REVIEW #3): pitch is computed per-boundary in
        # policy/boundary.py (deterministic: real envelope for harmonic
        # COMPATIBLE, an explicit ZERO-width envelope for a validated
        # non-tonal exception -- never a nonzero range alongside a null
        # required value).
        required_pitch_shift = winner_entry["required_pitch_shift_semitones"]
        permitted_pitch_min, permitted_pitch_max = winner_entry["permitted_pitch_shift_semitones_range"]

    compat_dict = compat_payload or {}
    vocal_constraint = f"PAIR_VOCAL_COLLISION_RISK={compat_dict.get('vocal_collision_risk', 'UNKNOWN')}"
    bass_constraint = f"PAIR_BASS_PERCUSSION_COLLISION_RISK={compat_dict.get('bass_percussion_collision_risk', 'UNKNOWN')}"
    energy_target = f"PAIR_ENERGY_CONTINUITY={compat_dict.get('energy_continuity', 'UNKNOWN')}"

    onset_window = _onset_window(exit_candidate, exit_result.transition_onset_ms)
    entry_region = entry_candidate.get("onset_window_ms")
    if entry_region:
        entry_window = {"t_start_ms": entry_region[0], "t_end_ms": entry_region[1]}
    else:
        entry_window = {"t_start_ms": entry_candidate["t_ms"], "t_end_ms": entry_candidate["t_ms"]}

    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type="TRANSITION",
        current_track_effective_content_end_ms=exit_result.effective_content_end_ms,
        selected_outgoing_exit_candidate_id=exit_candidate["candidate_id"],
        transition_onset_window_ms=onset_window,
        outgoing_last_audible_target_ms=exit_result.outgoing_last_audible_ms,
        outgoing_content_preservation_target=exit_result.outgoing_content_preservation_ratio,
        selected_incoming_entry_candidate_id=entry_candidate["candidate_id"],
        incoming_effective_content_start_ms=incoming_effective_content_start_ms,
        next_track_entry_window_ms=entry_window,
        incoming_entry_reason_codes=incoming_entry_reason_codes,
        incoming_phrase_section_evidence=bool(entry_candidate.get("phrase_section_evidence", False)),
        allowed_transition_class_set=allowed_class_set,
        pair_compatibility_components=compat_payload,
        outgoing_beat_alignment_target_ms=outgoing_beat_target,
        incoming_beat_alignment_target_ms=incoming_beat_target,
        outgoing_downbeat_alignment_target_ms=outgoing_downbeat_target,
        incoming_downbeat_alignment_target_ms=incoming_downbeat_target,
        beat_phase_relation=beat_phase_relation,
        bar_phase_relation=bar_phase_relation,
        beat_alignment_action=beat_alignment_action,
        bar_alignment_action=bar_alignment_action,
        required_tempo_ratio=required_tempo_ratio,
        permitted_tempo_ratio_max_deviation=permitted_tempo_dev,
        required_pitch_shift_semitones=required_pitch_shift,
        permitted_pitch_shift_semitones_min=permitted_pitch_min,
        permitted_pitch_shift_semitones_max=permitted_pitch_max,
        energy_continuity_target=energy_target,
        vocal_collision_constraints=vocal_constraint,
        bass_collision_constraints=bass_constraint,
        analysis_confidence=exit_result.confidence,
        reason_codes=exit_result.acceptance_reason_codes + winner_entry["selection_reason_codes"],
        candidate_rank_trace=boundary_trace,
        candidate_trace=boundary_trace,
    )


def build_fallback_decision(fixture_id, intent, policy_name, decision_type, reason_codes, candidate_trace, confidence="LOW"):
    assert decision_type in ("PLAY_THROUGH", "NO_SPECIAL_TRANSITION")
    effective_end = None
    if candidate_trace:
        last = candidate_trace[-1]
        effective_end = last.get("effective_content_end_ms")
        if effective_end is None:
            components = last.get("outgoing_preservation_components")
            if components:
                effective_end = components.get("effective_content_end_ms")
    return PlannerDecision(
        fixture_id=fixture_id,
        listener_intent=intent,
        policy_name=policy_name,
        decision_type=decision_type,
        current_track_effective_content_end_ms=effective_end,
        incoming_entry_reason_codes=["NOT_APPLICABLE_NO_TRANSITION_SELECTED"],
        allowed_transition_class_set=["NO_SPECIAL_TRANSITION"] if decision_type == "NO_SPECIAL_TRANSITION" else [],
        analysis_confidence=confidence,
        reason_codes=reason_codes,
        candidate_rank_trace=candidate_trace,
        candidate_trace=candidate_trace,
    )
