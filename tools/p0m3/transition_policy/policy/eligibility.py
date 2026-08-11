"""
P0-M3-R2 Task B -- deterministic transition-eligibility model.

Research-only prototype. This module computes, for a single current-track
candidate exit point, an explicit machine-readable eligibility record. It
never implements audio DSP (P0-M3-R2 scope boundary) and never reads any
next-track/queue field (P4: queue order is independent of current-track
exit timing -- enforced structurally: no function in this module accepts
a "next track quality" argument at all).

Ground-truth-only fixture fields (is_premature_trap, is_valid_natural_exit,
is_preferred_earliest_valid_exit, is_vocal_collision_trap,
highlight_eligible) are NEVER read here -- only by the benchmark scorer in
run_benchmark.py. See fixtures/manifest.json
"note_on_ground_truth_isolation".
"""

from dataclasses import dataclass, field
from typing import Optional

CONFIDENCE_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
CONFIDENCE_MULTIPLIER = {"NONE": 0.0, "LOW": 0.4, "MEDIUM": 0.75, "HIGH": 1.0}

# Intent-specific song-preservation fraction floors (Task C).
# Deliberately NOT the sole guard: see REQUIRES_STRUCTURAL_EVIDENCE below,
# which is enforced independently of these numbers (AC5).
FRACTION_FLOOR = {
    "FULL_SONG_DEFAULT": 0.55,
    "BALANCED_MIX": 0.30,
    "HIGHLIGHT_EXPLICIT": 0.0,
}
SHORT_TRACK_FRACTION_FLOOR = {
    "FULL_SONG_DEFAULT": 0.40,
    "BALANCED_MIX": 0.20,
    "HIGHLIGHT_EXPLICIT": 0.0,
}
SHORT_TRACK_DURATION_MS_THRESHOLD = 100_000

VALID_INTENTS = ("FULL_SONG_DEFAULT", "BALANCED_MIX", "HIGHLIGHT_EXPLICIT")

REASON = {
    "STRUCTURAL_EVIDENCE_PRESENT": "at least one of in_acceptable_exit_region / is_outro_tail_opportunity / musical_unit_complete is true",
    "NO_STRUCTURAL_EVIDENCE": "none of in_acceptable_exit_region / is_outro_tail_opportunity / musical_unit_complete is true -- BPM/key compatibility alone never authorizes an early exit (P5)",
    "BELOW_PRESERVATION_FRACTION_FLOOR": "fraction_consumed is below this intent's song-preservation floor",
    "SHORT_TRACK_EXCEPTION_APPLIED": "duration_ms is below the short-track threshold; the lower short-track fraction floor was used instead of the normal-length floor",
    "LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY": "structure_confidence is NONE or LOW; the planner does not fabricate certainty from an unverified/UNKNOWN annotation source (AC9)",
    "VOCAL_COLLISION_RISK_HIGH": "vocal_collision_risk is HIGH at this candidate; rejected regardless of structural score or intent",
    "HIGHLIGHT_INTENT_BYPASSES_FRACTION_FLOOR": "HIGHLIGHT_EXPLICIT intent explicitly permits shortened playback; the preservation fraction floor does not apply, but structural evidence and vocal-safety guards still do",
    "END_OF_TRACK_NATURAL_HANDOFF": "this is the end-of-track marker; no earlier candidate was eligible, so the track played to its natural/authored boundary",
}


@dataclass
class EligibilityResult:
    candidate_id: str
    t_ms: int
    fraction_consumed: float
    eligible: bool
    rejection_reason_codes: list = field(default_factory=list)
    acceptance_reason_codes: list = field(default_factory=list)
    song_preservation_score: float = 0.0
    musical_structure_score: float = 0.0
    timing_score: float = 0.0
    confidence: str = "NONE"
    confidence_reason: str = ""
    preferred_transition_class_set: list = field(default_factory=list)


def _structure_score(candidate: dict) -> float:
    score = 0.0
    if candidate.get("in_acceptable_exit_region"):
        score += 0.4
    if candidate.get("beat_downbeat_aligned"):
        score += 0.2
    if candidate.get("musical_unit_complete"):
        score += 0.2
    if candidate.get("is_outro_tail_opportunity"):
        score += 0.2
    return round(score, 4)


def _has_structural_evidence(candidate: dict) -> bool:
    return bool(
        candidate.get("in_acceptable_exit_region")
        or candidate.get("is_outro_tail_opportunity")
        or candidate.get("musical_unit_complete")
    )


def _preferred_transition_class_set(candidate: dict, structure_score: float, confidence: str) -> list:
    """
    P2: a transition is allowed to do less. This function never returns a
    set containing FULL_DJ_BLEND alone -- a technically compatible pair
    never *forces* a full DJ blend; simpler fallback classes are always
    co-listed so a downstream DSP pass keeps discretion (P0-M2 taxonomy).
    """
    beat_ok = bool(candidate.get("beat_downbeat_aligned"))
    if beat_ok and structure_score >= 0.8 and confidence == "HIGH":
        return ["FULL_DJ_BLEND", "SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"]
    if candidate.get("in_acceptable_exit_region") or candidate.get("musical_unit_complete"):
        return ["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"]
    if candidate.get("is_outro_tail_opportunity") and not beat_ok:
        return ["GAPLESS", "NO_SPECIAL_TRANSITION", "CUT"]
    return ["SIMPLE_CROSSFADE"]


def evaluate_candidate(fixture: dict, candidate: dict, intent: str, fraction_floor_override: Optional[float] = None) -> EligibilityResult:
    """
    Deterministic per-candidate eligibility evaluation (Task B).

    fraction_floor_override: used only by the sensitivity sweep (Task E) to
    vary the FULL_SONG_DEFAULT/BALANCED_MIX preservation floor while holding
    every other guard fixed. Never used by HIGHLIGHT_EXPLICIT (which has no
    floor by design).
    """
    if intent not in VALID_INTENTS:
        raise ValueError(f"unknown intent {intent!r}")

    duration_ms = fixture["duration_ms"]
    t_ms = candidate["t_ms"]
    fraction_consumed = round(t_ms / duration_ms, 4) if duration_ms else 0.0
    confidence = candidate.get("structure_confidence", "NONE")
    structure_score = _structure_score(candidate)
    song_preservation_score = round(min(1.0, fraction_consumed), 4)
    confidence_mult = CONFIDENCE_MULTIPLIER.get(confidence, 0.0)
    timing_score = round(confidence_mult * (0.5 * song_preservation_score + 0.5 * structure_score), 4)

    rejection_reasons = []
    acceptance_reasons = []

    # Guard 1 (safety-independent of intent): vocal collision risk.
    if candidate.get("vocal_collision_risk") == "HIGH":
        rejection_reasons.append("VOCAL_COLLISION_RISK_HIGH")

    # Guard 2: confidence-aware fallback (AC9). A NONE/LOW-confidence
    # annotation is never trusted to authorize a transition, regardless of
    # what it claims about structure or beat alignment.
    if CONFIDENCE_ORDER.get(confidence, 0) < CONFIDENCE_ORDER["MEDIUM"]:
        rejection_reasons.append("LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY")

    # Guard 3: structural evidence is mandatory in ALL intents, including
    # HIGHLIGHT_EXPLICIT (P0 binding: HIGHLIGHT_EXPLICIT permits an EARLIER
    # exit, it does not permit an arbitrary/unstructured cut). BPM/key
    # compatibility alone (P5) never satisfies this guard.
    if _has_structural_evidence(candidate):
        acceptance_reasons.append("STRUCTURAL_EVIDENCE_PRESENT")
    else:
        rejection_reasons.append("NO_STRUCTURAL_EVIDENCE")

    # Guard 4: intent-specific song-preservation fraction floor. Not applied
    # under HIGHLIGHT_EXPLICIT (explicit user intent permits shortened
    # playback -- P0 Task A). This is ONE signal among several (AC5), never
    # the sole guard -- guards 1-3 apply identically regardless of fraction.
    if intent == "HIGHLIGHT_EXPLICIT":
        acceptance_reasons.append("HIGHLIGHT_INTENT_BYPASSES_FRACTION_FLOOR")
    else:
        is_short_track = duration_ms < SHORT_TRACK_DURATION_MS_THRESHOLD
        if fraction_floor_override is not None:
            floor = fraction_floor_override
        elif is_short_track:
            floor = SHORT_TRACK_FRACTION_FLOOR[intent]
        else:
            floor = FRACTION_FLOOR[intent]
        if fraction_consumed < floor:
            rejection_reasons.append("BELOW_PRESERVATION_FRACTION_FLOOR")
        elif is_short_track and fraction_floor_override is None:
            acceptance_reasons.append("SHORT_TRACK_EXCEPTION_APPLIED")

    eligible = len(rejection_reasons) == 0

    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        fraction_consumed=fraction_consumed,
        eligible=eligible,
        rejection_reason_codes=rejection_reasons,
        acceptance_reason_codes=acceptance_reasons,
        song_preservation_score=song_preservation_score,
        musical_structure_score=structure_score,
        timing_score=timing_score,
        confidence=confidence,
        confidence_reason=REASON.get(
            "LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY" if confidence in ("NONE", "LOW") else "STRUCTURAL_EVIDENCE_PRESENT"
        ),
        preferred_transition_class_set=_preferred_transition_class_set(candidate, structure_score, confidence),
    )
