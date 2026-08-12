"""
P0-M3-R2 (Apple-like redesign) -- pair-level mixability gate.

Evaluates whether the OUTGOING and INCOMING track are "extremely suitable"
for complex dynamic mixing (FULL_DJ_BLEND) before that class is ever
offered. Every component is returned individually and explained with a
reason code; nothing is collapsed into an unexplained composite score
(spec section D).

Source discipline: Apple publicly documents that genre/tempo incompatibility
can prevent a dynamic transition (Apple Support "Transition songs in Music
on iPhone": "Albums and some genres play without transitions"). The
key/harmonic, energy, phrase/structure, and vocal/bass collision components
below are this PROJECT's clean-room quality gate, not a claim about Apple's
undocumented internal implementation -- see
docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md
"Apple-like behavioral target -- public evidence vs project inference".
"""

from dataclasses import dataclass, field, asdict

# P0 placeholder thresholds -- PROJECT_INFERENCE, sensitivity-testable in a
# later pass, never attributed to Apple. Single source of truth for
# contract.py's DSP-envelope fields (R3, PM REVIEW #2): these ARE deviation/
# range ceilings, never literal ratios -- see contract.py's
# permitted_tempo_ratio_max_deviation / permitted_pitch_shift_semitones_*.
MAX_JUSTIFIED_TEMPO_STRETCH_PCT = 0.12
HALF_DOUBLE_TIME_TOLERANCE_PCT = 0.03
PERMITTED_MAX_PITCH_SHIFT_SEMITONES = 3

COMPATIBLE_GENRE_FAMILIES = {
    "four_on_the_floor_electronic": {"house", "electronic", "edm", "techno", "dance", "disco"},
    "pop_rock": {"pop", "rock", "pop-rock", "indie"},
    "rnb_hiphop": {"r&b", "hip-hop", "hiphop", "soul"},
    "ambient_downtempo": {"ambient", "downtempo", "chillout", "experimental"},
}

CONFIDENCE_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

REASON = {
    "GENRE_COMPATIBLE_SAME_FAMILY": "outgoing and incoming genre tags share a recognized compatible genre family",
    "GENRE_INCOMPATIBLE": "outgoing and incoming genre tags share no recognized compatible family; Apple publicly documents genre incompatibility as a reason a dynamic transition may not occur",
    "TEMPO_DIRECT_COMPATIBLE": "BPM ratio is within the direct-compatibility tolerance without correction",
    "TEMPO_HALF_DOUBLE_COMPATIBLE": "BPM ratio matches a legitimate half/double-time relation within tolerance",
    "TEMPO_EXCESSIVE_STRETCH_REQUIRED": "required tempo stretch exceeds MAX_JUSTIFIED_TEMPO_STRETCH_PCT; BPM alone never authorizes a complex transition (P5)",
    "BEAT_CONFIDENCE_SUFFICIENT": "beat-tracking confidence is HIGH on both sides of the pair",
    "BEAT_CONFIDENCE_INSUFFICIENT": "beat-tracking confidence is below HIGH; FULL_DJ_BLEND requires demonstrated beat lock, not merely a BPM number",
    "DOWNBEAT_CONFIDENCE_SUFFICIENT": "downbeat/bar-phase confidence is HIGH",
    "DOWNBEAT_CONFIDENCE_INSUFFICIENT": "downbeat/bar-phase confidence is below HIGH",
    "HARMONIC_COMPATIBLE": "harmonic/key relationship is annotated compatible",
    "HARMONIC_UNKNOWN": "no harmonic/key annotation supplied; treated as neutral, not disqualifying",
    "HARMONIC_INCOMPATIBLE": "harmonic/key relationship is annotated incompatible",
    "ENERGY_CONTINUITY_STRONG": "energy/momentum contour continues smoothly across the pair boundary",
    "ENERGY_CONTINUITY_WEAK": "energy/momentum contour is discontinuous or unannotated",
    "STRUCTURE_COMPATIBLE": "phrase/section boundaries are annotated compatible on both sides",
    "STRUCTURE_UNKNOWN": "no phrase/section compatibility annotation supplied",
    "VOCAL_COLLISION_RISK_HIGH_PAIR": "outgoing/incoming vocal activity overlap risk is HIGH at the proposed boundary",
    "VOCAL_COLLISION_RISK_ACCEPTABLE": "outgoing/incoming vocal activity overlap risk is LOW or NONE",
    "BASS_PERCUSSION_COLLISION_RISK_HIGH": "bass/percussion collision risk is HIGH at the proposed boundary",
    "BASS_PERCUSSION_COLLISION_RISK_ACCEPTABLE": "bass/percussion collision risk is LOW, NONE, or not supplied",
    "INTRO_OUTRO_TEXTURE_COMPATIBLE": "outgoing outro texture and incoming intro texture are annotated compatible for overlap",
    "INTRO_OUTRO_TEXTURE_UNKNOWN": "no intro/outro texture annotation supplied",
    "ANALYSIS_CONFIDENCE_LOW_PAIR": "overall pair analysis confidence is below HIGH; conservative downgrade applied rather than fabricated certainty",
    "ANALYSIS_CONFIDENCE_SUFFICIENT": "overall pair analysis confidence is HIGH",
    "STRUCTURE_COMPATIBILITY_REQUIRED_FOR_FULL_DJ": "FULL_DJ_BLEND requires structure_compatibility to be KNOWN and COMPATIBLE, not merely absent/UNKNOWN (R4 -- PM REVIEW #2)",
    "TEXTURE_COMPATIBILITY_REQUIRED_FOR_FULL_DJ": "FULL_DJ_BLEND requires intro_outro_texture_compatibility to be KNOWN and COMPATIBLE, not merely absent/UNKNOWN (R4 -- PM REVIEW #2)",
    "HARMONIC_UNKNOWN_DOWNGRADED": "harmonic relationship is UNKNOWN and no explicit harmonic_not_load_bearing_reason exception was supplied; FULL_DJ_BLEND is withheld rather than silently treated as COMPATIBLE (R4 -- PM REVIEW #2)",
    "HARMONIC_NOT_LOAD_BEARING_EXCEPTION_APPLIED": "harmonic relationship is UNKNOWN but an explicit, narrow, style-specific harmonic_not_load_bearing_reason exception was supplied and accepted",
    "PAIR_FULLY_COMPATIBLE_COMPLEX_MIX_ELIGIBLE": "every hard-gating component passed; FULL_DJ_BLEND may be offered (not forced)",
}


@dataclass
class PairCompatibilityResult:
    genre_compatibility: str  # "COMPATIBLE" | "INCOMPATIBLE"
    tempo_compatibility: str  # "DIRECT" | "HALF_DOUBLE" | "EXCESSIVE_STRETCH"
    required_tempo_stretch_pct: float
    # R3 (PM REVIEW #2): unambiguous tempo fields, distinct from the
    # deviation-percent above. required_tempo_ratio is the LITERAL
    # playback-rate ratio (bpm_out / bpm_in) needed to align the incoming
    # track's tempo grid to the outgoing track's, regardless of which
    # relation matched. tempo_requires_playback_rate_change is False for a
    # HALF_DOUBLE relation (grid/downbeat REINTERPRETATION only -- no actual
    # speed change is needed to beat-match a legitimate half/double-time
    # pair) and True for DIRECT (a real, if small, rate correction) or
    # EXCESSIVE_STRETCH (rejected before use, but still reported honestly).
    required_tempo_ratio: float
    tempo_requires_playback_rate_change: bool
    beat_compatibility: str  # "SUFFICIENT" | "INSUFFICIENT"
    downbeat_compatibility: str  # "SUFFICIENT" | "INSUFFICIENT"
    harmonic_compatibility: str  # "COMPATIBLE" | "INCOMPATIBLE" | "UNKNOWN"
    energy_continuity: str  # "STRONG" | "WEAK"
    structure_compatibility: str  # "COMPATIBLE" | "UNKNOWN"
    vocal_collision_risk: str  # candidate/pair annotated risk level
    bass_percussion_collision_risk: str
    intro_outro_texture_compatibility: str  # "COMPATIBLE" | "UNKNOWN"
    analysis_confidence: str
    overall_dynamic_mix_eligible: bool
    reason_codes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _genre_families(genre_tags):
    families = set()
    tags = {g.lower() for g in genre_tags}
    for family, members in COMPATIBLE_GENRE_FAMILIES.items():
        if tags & members:
            families.add(family)
    return families


def _tempo_relation(bpm_out: float, bpm_in: float):
    """
    Returns (relation, required_tempo_stretch_pct, required_tempo_ratio,
    requires_playback_rate_change).
    """
    if bpm_out <= 0 or bpm_in <= 0:
        return "EXCESSIVE_STRETCH", 1.0, 1.0, True
    literal_ratio = round(bpm_out / bpm_in, 4)
    direct_deviation = abs(bpm_in - bpm_out) / bpm_out
    if direct_deviation <= MAX_JUSTIFIED_TEMPO_STRETCH_PCT:
        return "DIRECT", round(direct_deviation, 4), literal_ratio, True
    half_deviation = abs(bpm_in - bpm_out / 2) / (bpm_out / 2)
    double_deviation = abs(bpm_in - bpm_out * 2) / (bpm_out * 2)
    best_hd_deviation = min(half_deviation, double_deviation)
    if best_hd_deviation <= HALF_DOUBLE_TIME_TOLERANCE_PCT:
        # Legitimate half/double-time relation: no real playback-speed
        # correction is needed, only a downbeat/bar-grid reinterpretation
        # (e.g. treating every other beat as a downbeat).
        return "HALF_DOUBLE", round(best_hd_deviation, 4), 1.0, False
    return "EXCESSIVE_STRETCH", round(direct_deviation, 4), literal_ratio, True


def evaluate_pair_compatibility(pair: dict) -> PairCompatibilityResult:
    outgoing = pair["outgoing"]
    incoming = pair["incoming"]
    reasons = []

    out_families = _genre_families(outgoing.get("genre_tags", []))
    in_families = _genre_families(incoming.get("genre_tags", []))
    genre_ok = bool(out_families & in_families)
    reasons.append("GENRE_COMPATIBLE_SAME_FAMILY" if genre_ok else "GENRE_INCOMPATIBLE")

    tempo_relation, stretch_pct, required_ratio, requires_rate_change = _tempo_relation(outgoing.get("bpm", 0), incoming.get("bpm", 0))
    tempo_ok = tempo_relation in ("DIRECT", "HALF_DOUBLE")
    reasons.append({
        "DIRECT": "TEMPO_DIRECT_COMPATIBLE",
        "HALF_DOUBLE": "TEMPO_HALF_DOUBLE_COMPATIBLE",
        "EXCESSIVE_STRETCH": "TEMPO_EXCESSIVE_STRETCH_REQUIRED",
    }[tempo_relation])

    beat_conf = pair.get("beat_confidence", "NONE")
    beat_ok = CONFIDENCE_ORDER.get(beat_conf, 0) >= CONFIDENCE_ORDER["HIGH"]
    reasons.append("BEAT_CONFIDENCE_SUFFICIENT" if beat_ok else "BEAT_CONFIDENCE_INSUFFICIENT")

    downbeat_conf = pair.get("downbeat_confidence", "NONE")
    downbeat_ok = CONFIDENCE_ORDER.get(downbeat_conf, 0) >= CONFIDENCE_ORDER["HIGH"]
    reasons.append("DOWNBEAT_CONFIDENCE_SUFFICIENT" if downbeat_ok else "DOWNBEAT_CONFIDENCE_INSUFFICIENT")

    harmonic = pair.get("harmonic_relationship")  # "COMPATIBLE" | "INCOMPATIBLE" | None
    harmonic_not_load_bearing_reason = pair.get("harmonic_not_load_bearing_reason")
    if harmonic is None:
        harmonic_label = "UNKNOWN"
        reasons.append("HARMONIC_UNKNOWN")
        if harmonic_not_load_bearing_reason:
            harmonic_ok = True
            reasons.append("HARMONIC_NOT_LOAD_BEARING_EXCEPTION_APPLIED")
        else:
            harmonic_ok = False
            reasons.append("HARMONIC_UNKNOWN_DOWNGRADED")
    elif harmonic == "COMPATIBLE":
        harmonic_label = "COMPATIBLE"
        harmonic_ok = True
        reasons.append("HARMONIC_COMPATIBLE")
    else:
        harmonic_label = "INCOMPATIBLE"
        harmonic_ok = False
        reasons.append("HARMONIC_INCOMPATIBLE")

    energy_ok = pair.get("energy_continuity") == "STRONG"
    reasons.append("ENERGY_CONTINUITY_STRONG" if energy_ok else "ENERGY_CONTINUITY_WEAK")

    structure_ok = pair.get("structure_compatibility") == "COMPATIBLE"
    reasons.append("STRUCTURE_COMPATIBLE" if structure_ok else "STRUCTURE_UNKNOWN")
    if not structure_ok:
        reasons.append("STRUCTURE_COMPATIBILITY_REQUIRED_FOR_FULL_DJ")

    vocal_risk = pair.get("vocal_collision_risk", "NONE")
    vocal_ok = vocal_risk not in ("HIGH", "MEDIUM")
    reasons.append("VOCAL_COLLISION_RISK_HIGH_PAIR" if not vocal_ok else "VOCAL_COLLISION_RISK_ACCEPTABLE")

    bass_risk = pair.get("bass_percussion_collision_risk", "NONE")
    bass_ok = bass_risk != "HIGH"
    reasons.append("BASS_PERCUSSION_COLLISION_RISK_HIGH" if not bass_ok else "BASS_PERCUSSION_COLLISION_RISK_ACCEPTABLE")

    texture_ok = pair.get("intro_outro_texture_compatible", False)
    reasons.append("INTRO_OUTRO_TEXTURE_COMPATIBLE" if texture_ok else "INTRO_OUTRO_TEXTURE_UNKNOWN")
    if not texture_ok:
        reasons.append("TEXTURE_COMPATIBILITY_REQUIRED_FOR_FULL_DJ")

    analysis_conf = pair.get("analysis_confidence", "NONE")
    analysis_ok = CONFIDENCE_ORDER.get(analysis_conf, 0) >= CONFIDENCE_ORDER["HIGH"]
    reasons.append("ANALYSIS_CONFIDENCE_SUFFICIENT" if analysis_ok else "ANALYSIS_CONFIDENCE_LOW_PAIR")

    # Hard gate (R4, PM REVIEW #2 -- tightened): every one of these must
    # pass before FULL_DJ_BLEND is ever offered. BPM/tempo compatibility
    # alone is explicitly NOT sufficient (P5) -- genre, tempo, beat,
    # downbeat, structure (KNOWN + COMPATIBLE, not merely UNKNOWN),
    # intro/outro texture (KNOWN + COMPATIBLE, not merely UNKNOWN),
    # vocal-safety, bass/percussion-safety, analysis confidence, and
    # harmonic (COMPATIBLE, or UNKNOWN only under an explicit narrow
    # exception) are all independently required.
    overall_eligible = (
        genre_ok and tempo_ok and beat_ok and downbeat_ok
        and structure_ok and texture_ok
        and vocal_ok and bass_ok and analysis_ok
        and harmonic_ok
    )
    if overall_eligible:
        reasons.append("PAIR_FULLY_COMPATIBLE_COMPLEX_MIX_ELIGIBLE")

    return PairCompatibilityResult(
        genre_compatibility="COMPATIBLE" if genre_ok else "INCOMPATIBLE",
        tempo_compatibility=tempo_relation,
        required_tempo_stretch_pct=stretch_pct,
        required_tempo_ratio=required_ratio,
        tempo_requires_playback_rate_change=requires_rate_change,
        beat_compatibility="SUFFICIENT" if beat_ok else "INSUFFICIENT",
        downbeat_compatibility="SUFFICIENT" if downbeat_ok else "INSUFFICIENT",
        harmonic_compatibility=harmonic_label,
        energy_continuity="STRONG" if energy_ok else "WEAK",
        structure_compatibility="COMPATIBLE" if structure_ok else "UNKNOWN",
        vocal_collision_risk=vocal_risk,
        bass_percussion_collision_risk=bass_risk,
        intro_outro_texture_compatibility="COMPATIBLE" if texture_ok else "UNKNOWN",
        analysis_confidence=analysis_conf,
        overall_dynamic_mix_eligible=overall_eligible,
        reason_codes=reasons,
    )


def downgrade_transition_class_set(base_class_set: list, compat: "PairCompatibilityResult | None") -> list:
    """
    Never force FULL_DJ_BLEND: intersect the timing-derived base class set
    with what pair compatibility actually supports. If `compat` is None
    (no pair supplied -- a timing-only fixture), compatibility is UNPROVEN,
    so FULL_DJ_BLEND is withheld by default (spec section D: "extremely
    suitable songs" must be demonstrated, not assumed).
    """
    if compat is None:
        return [c for c in base_class_set if c != "FULL_DJ_BLEND"] or ["SIMPLE_CROSSFADE"]

    allowed = set(base_class_set)
    if not compat.overall_dynamic_mix_eligible:
        allowed.discard("FULL_DJ_BLEND")
    if compat.vocal_collision_risk in ("HIGH", "MEDIUM") or compat.bass_percussion_collision_risk == "HIGH":
        allowed.discard("FULL_DJ_BLEND")
        allowed.discard("SHORT_EQ_BLEND")
    if compat.genre_compatibility == "INCOMPATIBLE" or compat.tempo_compatibility == "EXCESSIVE_STRETCH":
        allowed.discard("FULL_DJ_BLEND")
        allowed.discard("SHORT_EQ_BLEND")
    if compat.beat_compatibility == "INSUFFICIENT" or compat.downbeat_compatibility == "INSUFFICIENT":
        allowed.discard("FULL_DJ_BLEND")
    if compat.analysis_confidence not in ("HIGH",):
        allowed.discard("FULL_DJ_BLEND")

    if not allowed:
        allowed = {"NO_SPECIAL_TRANSITION"}
    # Deterministic ordering: preserve the canonical taxonomy order.
    canonical_order = ["FULL_DJ_BLEND", "SHORT_EQ_BLEND", "SIMPLE_CROSSFADE", "GAPLESS", "CUT", "NO_SPECIAL_TRANSITION"]
    return [c for c in canonical_order if c in allowed]
