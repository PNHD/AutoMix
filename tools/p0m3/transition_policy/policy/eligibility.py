"""
P0-M3-R2 (Apple-like redesign) -- deterministic transition-eligibility
model, redesigned around near-end song preservation rather than raw
fraction_consumed.

Research-only prototype. This module computes, for a single current-track
candidate, an explicit machine-readable eligibility record including the
new preservation/timing metrics (policy/metrics.py). It never implements
audio DSP (P0-M3-R2 scope boundary) and never reads any next-track/queue
field for TIMING purposes (P4: queue order is independent of current-track
exit timing). Pair-COMPATIBILITY (policy/compatibility.py) may influence
which TRANSITION CLASS is offered, never WHEN to exit -- that separation is
structural, not just behavioral (P3).

Ground-truth-only fixture fields (is_premature_trap, is_valid_natural_exit,
is_preferred_earliest_valid_exit, is_vocal_collision_trap,
highlight_eligible) are NEVER read here -- only by the benchmark scorer in
run_benchmark.py. See fixtures/manifest.json
"note_on_ground_truth_isolation".
"""

from dataclasses import dataclass, field
from typing import Optional

from . import metrics as metrics_mod

CONFIDENCE_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
CONFIDENCE_MULTIPLIER = {"NONE": 0.0, "LOW": 0.4, "MEDIUM": 0.75, "HIGH": 1.0}

# Product direction (Issue #6, "PM PRODUCT DIRECTION UPDATE -- APPLE-LIKE
# NEAR-END LISTENING TARGET"): SEAMLESS_FULL_TRACK_DEFAULT is the ONLY
# current product-default candidate. BALANCED_MIX is retained solely as a
# research/negative control and must never influence default behavior.
# HIGHLIGHT_EXPLICIT is retained solely as a research/negative control,
# reachable only via explicit listener intent (never silently).
SEAMLESS_FULL_TRACK_DEFAULT = "SEAMLESS_FULL_TRACK_DEFAULT"
BALANCED_MIX = "BALANCED_MIX"
HIGHLIGHT_EXPLICIT = "HIGHLIGHT_EXPLICIT"
VALID_INTENTS = (SEAMLESS_FULL_TRACK_DEFAULT, BALANCED_MIX, HIGHLIGHT_EXPLICIT)
DEFAULT_INTENT = SEAMLESS_FULL_TRACK_DEFAULT

# outgoing_content_preservation_ratio floors, keyed by intent.
# SEAMLESS_FULL_TRACK_DEFAULT: project benchmark proposal (see metrics.py),
# sensitivity-tested at 0.90/0.93/0.95/0.97/0.98 in
# results/sensitivity_matrix.json. Preferred band 0.97-1.00; acceptable P0
# default-candidate band 0.95-1.00; <0.90 is catastrophic absent an
# explicit authored exception (metrics.CATASTROPHIC_PRESERVATION_CEILING).
# BALANCED_MIX's lower floor exists ONLY to give the research/negative
# control something to differ on; it is never used by default behavior and
# carries no acceptance criterion of its own.
PRESERVATION_FLOOR = {
    SEAMLESS_FULL_TRACK_DEFAULT: metrics_mod.DEFAULT_PRESERVATION_FLOOR,
    BALANCED_MIX: 0.65,
    HIGHLIGHT_EXPLICIT: 0.0,
}

REASON = {
    "STRUCTURAL_EVIDENCE_PRESENT": "at least one of in_acceptable_exit_region / is_outro_tail_opportunity / musical_unit_complete is true",
    "NO_STRUCTURAL_EVIDENCE": "none of in_acceptable_exit_region / is_outro_tail_opportunity / musical_unit_complete is true -- BPM/key compatibility alone never authorizes an early exit (P5)",
    "BELOW_PRESERVATION_FLOOR": "outgoing_content_preservation_ratio is below this intent's preservation floor",
    "CATASTROPHIC_PRESERVATION_LOSS": "outgoing_content_preservation_ratio is below the catastrophic ceiling (0.90) with no authored exception -- default-mode failure",
    "LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY": "structure_confidence is NONE or LOW; the planner does not fabricate certainty from an unverified/UNKNOWN annotation source (AC9)",
    "VOCAL_COLLISION_RISK_HIGH": "vocal_collision_risk is HIGH at this candidate; rejected regardless of structural score or intent",
    "HIGHLIGHT_INTENT_BYPASSES_PRESERVATION_FLOOR": "HIGHLIGHT_EXPLICIT intent explicitly permits shortened playback; the preservation floor does not apply, but structural evidence and vocal-safety guards still do",
    "SEQUENTIAL_ALBUM_INTENT_NO_FORCED_TRANSITION": "fixture is annotated sequential_album_intent=true; dynamic DJ-style transition classes are withheld regardless of otherwise-strong timing/compatibility evidence",
    "END_OF_TRACK_NATURAL_HANDOFF": "this is the end-of-track marker; no earlier candidate was eligible, so the track played to its natural/authored boundary",
    "TRAILING_DEAD_AIR_TRIMMED_NOT_TRUNCATED": "trailing content beyond effective_content_end_ms is authored non-musical dead air, not lost musical content -- this is never reported as truncation",
}


@dataclass
class EligibilityResult:
    candidate_id: str
    t_ms: int
    eligible: bool
    rejection_reason_codes: list = field(default_factory=list)
    acceptance_reason_codes: list = field(default_factory=list)

    # Near-end preservation/timing metrics (spec section B).
    effective_content_end_ms: int = 0
    transition_onset_ms: int = 0
    transition_onset_ratio: float = 0.0
    overlap_duration_ms: int = 0
    outgoing_last_audible_ms: int = 0
    outgoing_content_preservation_ratio: float = 0.0
    outgoing_content_lost_ms: int = 0
    # R8 (PM REVIEW #3): PREFERRED (>=0.97) / ACCEPTABLE (>=floor, <0.97) /
    # UNSAFE (<floor). Computed against whichever floor was ACTUALLY applied
    # for this evaluation (intent + any sensitivity override), so ranking
    # can prioritize the safety band without re-deriving the floor itself.
    preservation_band: str = "UNSAFE"

    musical_structure_score: float = 0.0
    confidence: str = "NONE"
    confidence_reason: str = ""
    preferred_transition_class_set: list = field(default_factory=list)
    energy_continuity_priority: str = "UNKNOWN"


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


def _base_transition_class_set(candidate: dict, structure_score: float, confidence: str) -> list:
    """
    Timing-derived base class set ONLY (P3: separate WHEN from HOW). Pair
    compatibility (policy/compatibility.py) is applied on top of this by
    the caller via compatibility.downgrade_transition_class_set -- this
    function alone never guarantees FULL_DJ_BLEND is actually offered.
    """
    beat_ok = bool(candidate.get("beat_downbeat_aligned"))
    if beat_ok and structure_score >= 0.8 and confidence == "HIGH":
        return ["FULL_DJ_BLEND", "SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"]
    if candidate.get("in_acceptable_exit_region") or candidate.get("musical_unit_complete"):
        return ["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"]
    if candidate.get("is_outro_tail_opportunity") and not beat_ok:
        return ["GAPLESS", "NO_SPECIAL_TRANSITION", "CUT"]
    return ["SIMPLE_CROSSFADE"]


def evaluate_candidate(fixture: dict, candidate: dict, intent: str, preservation_floor_override: Optional[float] = None) -> EligibilityResult:
    """
    Deterministic per-candidate eligibility evaluation.

    preservation_floor_override: used only by the sensitivity sweep to vary
    the SEAMLESS_FULL_TRACK_DEFAULT preservation floor while holding every
    other guard fixed. Never used by HIGHLIGHT_EXPLICIT (no floor by
    design).
    """
    if intent not in VALID_INTENTS:
        raise ValueError(f"unknown intent {intent!r}")

    t_ms = candidate["t_ms"]
    confidence = candidate.get("structure_confidence", "NONE")
    structure_score = _structure_score(candidate)

    pm = metrics_mod.compute_preservation(fixture, t_ms)

    rejection_reasons = []
    acceptance_reasons = []

    # Guard 0: sequential-album intent withholds dynamic DJ-style transition
    # classes structurally, independent of every other signal (spec section
    # F/N). This guard affects preferred_transition_class_set, not
    # eligibility itself -- a sequential album can still have a valid exit
    # point, it simply never gets a DJ-style blend there.
    sequential_album = bool(fixture.get("sequential_album_intent", False))

    # Guard 1 (safety-independent of intent): vocal collision risk.
    if candidate.get("vocal_collision_risk") == "HIGH":
        rejection_reasons.append("VOCAL_COLLISION_RISK_HIGH")

    # Guard 2: confidence-aware fallback (AC9). A NONE/LOW-confidence
    # annotation is never trusted to authorize a transition.
    if CONFIDENCE_ORDER.get(confidence, 0) < CONFIDENCE_ORDER["MEDIUM"]:
        rejection_reasons.append("LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY")

    # Guard 3: structural evidence is mandatory in ALL intents, including
    # HIGHLIGHT_EXPLICIT (HIGHLIGHT_EXPLICIT permits an EARLIER exit, not an
    # arbitrary/unstructured cut). BPM/key compatibility alone (P5) never
    # satisfies this guard.
    if _has_structural_evidence(candidate):
        acceptance_reasons.append("STRUCTURAL_EVIDENCE_PRESENT")
    else:
        rejection_reasons.append("NO_STRUCTURAL_EVIDENCE")

    # Guard 4: intent-specific outgoing-content preservation floor. This is
    # the load-bearing default-mode guard (spec section B/H) -- NOT a raw
    # elapsed-time/fraction-consumed threshold, and NOT applied under
    # HIGHLIGHT_EXPLICIT (explicit user intent permits shortened playback).
    if intent == HIGHLIGHT_EXPLICIT:
        acceptance_reasons.append("HIGHLIGHT_INTENT_BYPASSES_PRESERVATION_FLOOR")
        banding_floor = 0.0  # no real floor under the bypass; nothing bands as UNSAFE here
    else:
        floor = preservation_floor_override if preservation_floor_override is not None else PRESERVATION_FLOOR[intent]
        banding_floor = floor
        if pm.outgoing_content_preservation_ratio < floor:
            rejection_reasons.append("BELOW_PRESERVATION_FLOOR")
            if pm.is_catastrophic_loss:
                rejection_reasons.append("CATASTROPHIC_PRESERVATION_LOSS")

    band = metrics_mod.preservation_band(pm.outgoing_content_preservation_ratio, banding_floor)

    if fixture.get("trailing_dead_air_is_authored_non_musical", False):
        acceptance_reasons.append("TRAILING_DEAD_AIR_TRIMMED_NOT_TRUNCATED")

    eligible = len(rejection_reasons) == 0

    base_class_set = _base_transition_class_set(candidate, structure_score, confidence)
    if sequential_album:
        base_class_set = [c for c in base_class_set if c not in ("FULL_DJ_BLEND", "SHORT_EQ_BLEND")]
        if not base_class_set:
            base_class_set = ["GAPLESS", "NO_SPECIAL_TRANSITION"]
        acceptance_reasons.append("SEQUENTIAL_ALBUM_INTENT_NO_FORCED_TRANSITION")

    energy_priority = candidate.get("energy_continuity_hint", "UNKNOWN")

    return EligibilityResult(
        candidate_id=candidate["candidate_id"],
        t_ms=t_ms,
        eligible=eligible,
        rejection_reason_codes=rejection_reasons,
        acceptance_reason_codes=acceptance_reasons,
        effective_content_end_ms=pm.effective_content_end_ms,
        transition_onset_ms=pm.transition_onset_ms,
        transition_onset_ratio=pm.transition_onset_ratio,
        overlap_duration_ms=pm.overlap_duration_ms,
        outgoing_last_audible_ms=pm.outgoing_last_audible_ms,
        outgoing_content_preservation_ratio=pm.outgoing_content_preservation_ratio,
        outgoing_content_lost_ms=pm.outgoing_content_lost_ms,
        preservation_band=band,
        musical_structure_score=structure_score,
        confidence=confidence,
        confidence_reason=REASON.get(
            "LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY" if confidence in ("NONE", "LOW") else "STRUCTURAL_EVIDENCE_PRESENT"
        ),
        preferred_transition_class_set=base_class_set,
        energy_continuity_priority=energy_priority,
    )
