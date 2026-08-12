"""
Conditional tempo adaptation (PM OWNER LISTENING DIRECTION UPDATE
"BINDING PRODUCT CLARIFICATION" + "TASK 2"). Tempo adaptation is NOT a
universal behavior -- this module decides, from the ACCEPTED R2
`PlannerDecision` alone (never a new/independent tempo decision), which of
three modes applies to a given boundary:

  NATIVE_TEMPO
      No meaningful correction is applied. Used whenever FULL_DJ_BLEND is
      not offered, no real tempo correction is required, or the required
      correction falls outside this project's own preferred consumer zone.

  MATCH_INCOMING_DURING_OVERLAP
      Incoming is tempo-matched to outgoing FOR THE DURATION OF THE
      OVERLAP ONLY. Used when pair compatibility already passed, a
      dynamic class is allowed, the correction is modest and inside the
      R2 envelope, and R2's own boundary-planning already determined beat/
      downbeat alignment evidence exists on both sides
      (`boundary_beat_downbeat_alignable` -- see
      tools/p0m3/transition_policy/policy/boundary.py -- surfaces as
      non-null `*_beat_alignment_target_ms` fields in the decision).

  MATCH_AND_RETURN_TO_NATIVE
      Same eligibility as MATCH_INCOMING_DURING_OVERLAP, plus a smooth,
      deterministic ramp back to native tempo over a bounded settling
      region after the overlap ends (dsp/tempo_ramp.py). Only selected
      when the caller explicitly opts in (`prefer_return_to_native=True`)
      AND the ramp implementation's own safety check
      (`dsp.tempo_ramp.ramp_is_safe`) passes; otherwise this module falls
      back to MATCH_INCOMING_DURING_OVERLAP and reports why, per Issue
      comment's explicit escape hatch ("If a safe return-to-native
      implementation cannot be demonstrated yet, keep the incoming tempo
      stable... and report the gap honestly").

      PM REVIEW "PRE-REAL-MUSIC REPAIR REQUIRED" R1: `dsp.tempo_ramp
      .ramp_is_safe` now actually exists (it previously did not -- the
      claim above was false) and runs a deterministic sinusoid
      pitch-drift measurement. The CURRENT `dsp/tempo_ramp.py` ramp is a
      sample-domain resampler (ordinary varispeed), so `ramp_is_safe`
      honestly reports `False` for every non-trivial correction this
      project's fixtures ever require (PM independently measured ~-85
      cents drift at `matched_rate=1.05`) -- meaning `select_tempo_mode`
      below NEVER actually returns `MATCH_AND_RETURN_TO_NATIVE` today,
      regardless of `prefer_return_to_native`. Its effective status is
      `NOT_YET_VALIDATED_PITCH_PRESERVING` (see that constant below);
      eligible corrections resolve to `MATCH_INCOMING_DURING_OVERLAP` and
      stay at the matched tempo through the rendered excerpt instead, per
      explicit PM direction ("Do not force return-to-native yet"). A
      future pitch-preserving return-to-native implementation (e.g.
      running the already-approved Signalsmith engine over the settling
      region instead of this resampler) would need to pass the same real
      `ramp_is_safe` gate before this mode could ever be returned again.

The outgoing track's tempo is NEVER altered by this module (or by any
renderer in this harness) -- only the incoming side is ever a stretch
target, matching R2's own contract
(`beat_alignment_action = ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET`,
never the reverse). Pitch is always preserved (`semitones=0` in every
Signalsmith/Rubber Band call this project makes) unless a future planner
pass explicitly authorizes a nonzero `required_pitch_shift_semitones`
(currently never -- see fixtures/pitch_shift_stress_conclusion.md).
"""
from __future__ import annotations

from dsp.tempo_ramp import ramp_is_safe

NATIVE_TEMPO = "NATIVE_TEMPO"
MATCH_INCOMING_DURING_OVERLAP = "MATCH_INCOMING_DURING_OVERLAP"
MATCH_AND_RETURN_TO_NATIVE = "MATCH_AND_RETURN_TO_NATIVE"

# PM REVIEW "PRE-REAL-MUSIC REPAIR REQUIRED" R1: reported in
# `evidence["return_to_native_status"]` whenever a boundary is eligible for
# return-to-native but the ramp's own pitch-preservation gate (above) has
# not (yet) passed -- distinct from an actually-selected mode, since
# `select_tempo_mode` never returns `MATCH_AND_RETURN_TO_NATIVE` while this
# applies.
NOT_YET_VALIDATED_PITCH_PRESERVING = "NOT_YET_VALIDATED_PITCH_PRESERVING"

# PROJECT_INFERENCE consumer-quality benchmark buckets (PM OWNER LISTENING
# DIRECTION UPDATE) -- NOT Apple/Spotify-disclosed thresholds. R2's own
# MAX_JUSTIFIED_TEMPO_STRETCH_PCT=0.12 (tools/p0m3/transition_policy/
# policy/compatibility.py) remains the hard planner-envelope ceiling; these
# are a STRICTER, narrower preferred zone inside that ceiling for this
# real-listening pass.
SAFE_ZONE_MAX_DEVIATION = 0.02       # 0-2%: normally safe candidate zone
CONDITIONAL_ZONE_MAX_DEVIATION = 0.06  # 2-6%: conditional quality zone -- must be listened to
# >6%: DOWNGRADE_CANDIDATE_ZONE -- default downgrade unless later human evidence justifies otherwise

SAFE_ZONE = "SAFE_ZONE_0_2_PCT"
CONDITIONAL_ZONE = "CONDITIONAL_ZONE_2_6_PCT"
DOWNGRADE_ZONE = "DOWNGRADE_CANDIDATE_ZONE_GT_6_PCT"

EXACT_MATCH_TOLERANCE = 0.001  # matches R2's own EXACT_TEMPO_MATCH_TOLERANCE


def classify_tempo_benchmark_zone(deviation: float) -> str:
    if deviation <= SAFE_ZONE_MAX_DEVIATION:
        return SAFE_ZONE
    if deviation <= CONDITIONAL_ZONE_MAX_DEVIATION:
        return CONDITIONAL_ZONE
    return DOWNGRADE_ZONE


def select_tempo_mode(decision: dict, prefer_return_to_native: bool = True) -> tuple[str, dict]:
    """
    Returns (mode, evidence_dict). `decision` is a real R2 PlannerDecision
    (as dict, e.g. json.load of fixtures/planner_decisions/*.json) --
    never independently re-decided.
    """
    allowed_classes = decision.get("allowed_transition_class_set") or []
    evidence = {"allowed_transition_class_set": allowed_classes}

    # Rule 1+2: pair compatibility already passed AND a dynamic class is allowed.
    if "FULL_DJ_BLEND" not in allowed_classes:
        evidence["reason"] = "FULL_DJ_BLEND not in allowed_transition_class_set -- pair compatibility/timing/alignment-evidence gate did not pass; tempo left at native by rule (never force-corrected for an incompatible/ungated pair)"
        return NATIVE_TEMPO, evidence

    ratio = decision.get("required_tempo_ratio")
    if ratio is None:
        evidence["reason"] = "required_tempo_ratio is null -- no tempo contract to act on"
        return NATIVE_TEMPO, evidence

    deviation = round(abs(ratio - 1.0), 6)
    zone = classify_tempo_benchmark_zone(deviation)
    evidence.update({"required_tempo_ratio": ratio, "deviation": deviation, "benchmark_zone": zone})

    # Rule 3: required correction is modest and inside the R2 hard envelope.
    max_dev = decision.get("permitted_tempo_ratio_max_deviation")
    if max_dev is not None and deviation > max_dev:
        evidence["reason"] = f"deviation {deviation} exceeds R2's own hard envelope ceiling {max_dev} -- native tempo, not force-corrected"
        return NATIVE_TEMPO, evidence

    # PM's project-benchmark downgrade rule: >6% is a default downgrade
    # candidate even if technically inside R2's wider 12% hard ceiling.
    if zone == DOWNGRADE_ZONE:
        evidence["reason"] = f"deviation {deviation} is in the >{CONDITIONAL_ZONE_MAX_DEVIATION*100:.0f}% project downgrade-candidate zone -- default to native tempo / simpler class rather than force time-stretch, absent later human evidence justifying otherwise"
        evidence["downgrade_recommended"] = True
        return NATIVE_TEMPO, evidence

    # Rule: do NOT automatically change tempo when tracks already align
    # naturally (an exact/near-exact relation needs no playback-rate
    # correction at all -- mirrors R2's own tempo_requires_playback_rate_change).
    pair = decision.get("pair_compatibility_components") or {}
    requires_change = pair.get("tempo_requires_playback_rate_change", deviation > EXACT_MATCH_TOLERANCE)
    if not requires_change or deviation <= EXACT_MATCH_TOLERANCE:
        evidence["reason"] = "tracks already align naturally (no meaningful correction required) -- native tempo, not corrected for its own sake"
        return NATIVE_TEMPO, evidence

    # Rule 4: beat/downbeat alignment evidence materially applies to THIS
    # boundary (not just pair-level confidence) -- R2's own per-boundary
    # alignability gate already enforced this as a precondition for
    # FULL_DJ_BLEND ever being offered (policy/boundary.py R5), so its
    # presence here is confirmed via the non-null alignment targets.
    both_targets_known = (
        decision.get("outgoing_beat_alignment_target_ms") is not None
        and decision.get("incoming_beat_alignment_target_ms") is not None
    )
    if not both_targets_known:
        evidence["reason"] = "FULL_DJ_BLEND allowed but boundary-level beat/downbeat alignment targets are missing -- fail closed to native tempo rather than guess an alignment target (mirrors dsp.render_common.require_full_dj_alignment_fields)"
        return NATIVE_TEMPO, evidence

    evidence["reason"] = f"pair-compatible, FULL_DJ_BLEND allowed, deviation {deviation} within envelope and zone={zone}, boundary alignment evidence present -- tempo-matching materially improves alignment"
    if zone == CONDITIONAL_ZONE:
        evidence["listening_required"] = True

    if prefer_return_to_native:
        safe, ramp_evidence = ramp_is_safe(ratio)
        evidence["return_to_native_ramp_safety_check"] = ramp_evidence
        if safe:
            return MATCH_AND_RETURN_TO_NATIVE, evidence
        evidence["return_to_native_status"] = NOT_YET_VALIDATED_PITCH_PRESERVING
        evidence["reason"] += (
            f" -- MATCH_AND_RETURN_TO_NATIVE was preferred but dsp.tempo_ramp.ramp_is_safe reports "
            f"unsafe pitch drift ({ramp_evidence.get('cents_drift')} cents vs "
            f"{ramp_evidence.get('tolerance_cents')} cent tolerance); falling back to "
            f"MATCH_INCOMING_DURING_OVERLAP (stable matched tempo through the excerpt) per explicit "
            f"PM direction not to force an unvalidated return-to-native ramp"
        )
        return MATCH_INCOMING_DURING_OVERLAP, evidence
    return MATCH_INCOMING_DURING_OVERLAP, evidence
