"""
P0-M3-R3 STAGE B REAL-EVIDENCE REPAIR -- transparent V1/V2/V3 real-music
pair selection.

Repairs applied per the newest Issue #7 PM comment ("PM STAGE B REVIEW --
CURRENT OWNER PACK INVALID / REAL-EVIDENCE REPAIR REQUIRED"), replacing the
prior pass's fabricated/non-independent evidence:

  R1 -- genre_tags come from real owner-local embedded-tag evidence
        (analyze_owner_corpus.py::extract_local_genre_tags), never a
        universal ["pop"] default. UNKNOWN (empty list) fails the existing
        R2 genre_ok gate exactly like any other real genre mismatch --
        compatibility.py itself was never weakened.
  R2 -- structure_compatibility comes from INDEPENDENT evidence
        (a detected instrumental tail, or a bar-synchronous novelty peak
        -- see analyze_owner_corpus.py) -- never from beat/downbeat
        confidence alone. musical_unit_complete on the manifest's outgoing
        candidate is set from that SAME independent evidence.
  R3 -- bass_percussion_collision_risk and intro_outro_texture_compatible
        are computed from MEASURED boundary-local low-frequency energy/
        onset-density (bass) and spectral-centroid/flatness/onset-density
        (texture) evidence -- never a hardcoded constant, never RMS+vocal
        alone. The canonical R2 analysis_confidence aggregate is preserved
        byte-for-behavior for baseline comparison, while a transparent
        per-lane confidence ledger makes its ownership explicit and prevents
        research diagnostics from counting the aggregate as a new analyzer.
  R4 -- entry_candidate_t_ms uses the REAL analyzer-detected value
        (silence-skip or instrumental-lead end), with
        leading_silence_is_authored_non_musical/leading_silence_ms wired
        into the manifest so real_music_pipeline.py's build_tx_fixture()
        bridge (also repaired this pass) can actually get it accepted by
        the real R2 planner instead of being forced back to 0ms.
  R5/R6 -- PRE-RENDER source-level loudness/bass energy-gap diagnostics
        participate directly in ranking (never post-render listening
        cherry-picking); ranking order is hard gates -> preservation ->
        clean entry -> structure/texture/vocal/bass safety -> source
        energy continuity -> harmonic -> tempo burden -> opaque-ID
        tie-break LAST (deliberately last, not first).

Selection happens BEFORE any rendering, exactly as before.

Usage:
    python scripts/select_real_music_pairs.py \
        --corpus-dir real_music/work_local/corpus \
        --manifest-out real_music/manifest.local.json \
        --trace-out real_music/work_local/selection_trace.local.json \
        --rationale-out real_music/work_local/selection_rationale_sanitized.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

from policy.compatibility import evaluate_pair_compatibility, _tempo_relation  # noqa: E402

CONF_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# PM STAGE B REVIEW R3 repair: thresholds calibrated against this corpus's
# own observed gap-distribution statistics (same calibration methodology
# used for the beat/downbeat/key confidence thresholds) -- NOT arbitrary,
# NOT tuned per-pair after the fact. See docs/research for the calibration
# sample. Selecting "compatible" texture/energy means genuinely BETTER than
# a typical (median) random pairing from this corpus, not merely "not the
# worst".
TEXTURE_CENTROID_GAP_RATIO_MAX = 0.20
TEXTURE_FLATNESS_GAP_MAX = 0.10
TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX = 0.20
ENERGY_STRONG_MAX_DB = 13.0
ENERGY_MODERATE_MAX_DB = 26.0


def min_conf(*vals):
    return min(vals, key=lambda v: CONF_ORDER.get(v, 0))


def corroborated_key(local_key: dict, whole_track_key: dict) -> dict:
    """Two INDEPENDENT measurement windows (whole-track average vs.
    boundary-localized) agreeing on the exact same (root, mode) is real
    corroborating evidence -- never lowers confidence, never changes the
    reported (root, mode)."""
    if local_key["root"] is None or whole_track_key["root"] is None:
        return local_key
    if local_key["root"] != whole_track_key["root"] or local_key["mode"] != whole_track_key["mode"]:
        return local_key
    best = max(local_key["confidence"], whole_track_key["confidence"], key=lambda c: CONF_ORDER.get(c, 0))
    if CONF_ORDER.get(best, 0) < CONF_ORDER["MEDIUM"]:
        best = "MEDIUM"
    return {**local_key, "confidence": best, "corroborated_by_whole_track_agreement": True}


def harmonic_relationship(key_a: dict, key_b: dict):
    if key_a["confidence"] not in ("MEDIUM", "HIGH") or key_b["confidence"] not in ("MEDIUM", "HIGH"):
        return None
    if key_a["root"] is None or key_b["root"] is None:
        return None
    ra, rb = PITCH_CLASSES.index(key_a["root"]), PITCH_CLASSES.index(key_b["root"])
    ma, mb = key_a["mode"], key_b["mode"]
    if ra == rb and ma == mb:
        return "COMPATIBLE"
    diff = (rb - ra) % 12
    if ma != mb:
        if ma == "major" and mb == "minor" and diff == 9:
            return "COMPATIBLE"
        if ma == "minor" and mb == "major" and diff == 3:
            return "COMPATIBLE"
        return "INCOMPATIBLE"
    if diff in (5, 7):
        return "COMPATIBLE"
    return "INCOMPATIBLE"


def _entry_structural_evidence(in_a: dict) -> bool:
    """The incoming side always has SOME independent structural evidence in
    this analyzer's construction -- track start (0ms) is inherently a
    section start by definition, and a detected instrumental-lead-end or
    authored-silence-skip point is likewise a genuine section-start (the
    point where the authored intro ends), never fabricated from beat/
    downbeat. Written out explicitly (not just assumed always-True) so a
    future analyzer change that produces an entry NOT backed by one of
    these three cases is honestly caught here, not silently passed."""
    c = in_a["candidates"]
    at_track_start = abs(c["entry_candidate_t_ms"]) < 1.0
    return bool(at_track_start or c["entry_has_detected_intro"] or c["entry_is_authored_silence_skip"])


def _combine_risk_min_side(risk_a: str, risk_b: str) -> str:
    """A collision/activity risk requires BOTH sides to be concurrently
    active -- bounded by whichever side is SAFER (lower), since a
    vocal-light or bass-light side means there is nothing to collide with
    regardless of the other side's level."""
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    combined = min(order.get(risk_a, 0), order.get(risk_b, 0))
    return {0: "LOW", 1: "MEDIUM", 2: "HIGH"}[combined]


def _recovery_sources(track: dict, lane: str, fallback: str) -> list[str]:
    evidence = track.get("evidence_recovery", {}).get(lane, {})
    source = evidence.get("source")
    return [source] if source else [fallback]


def build_confidence_ledger(
    out_a: dict,
    in_a: dict,
    *,
    structure_compatibility: str,
    harmonic: str | None,
    texture_compatible: bool,
    vocal_collision_risk: str,
    bass_percussion_collision_risk: str,
) -> dict:
    """Research-only ownership ledger for every independent evidence lane.

    The accepted R2 evaluator still receives its original scalar fields.
    This ledger is additional provenance: it never changes a production gate
    and never treats the legacy ``analysis_confidence`` minimum as a ninth
    measurement.  Recovered-oracle sources are read only from explicit local
    overlays created by the bounded Issue #7 recovery runner.
    """
    beat_conf = min_conf(out_a["beat"]["confidence"], in_a["beat"]["confidence"])
    downbeat_conf = min_conf(out_a["downbeat"]["confidence"], in_a["downbeat"]["confidence"])
    out_key_eff = corroborated_key(out_a.get("key_at_exit", out_a["key"]), out_a["key"])
    in_key_eff = corroborated_key(in_a.get("key_at_entry", in_a["key"]), in_a["key"])
    harmonic_conf = min_conf(out_key_eff["confidence"], in_key_eff["confidence"])

    def lane(sources, confidence, status, evidence_type):
        return {
            "sources": sorted(set(sources)),
            "confidence": confidence,
            "status": status,
            "evidence_type": evidence_type,
        }

    return {
        "beat_confidence_source": lane(
            _recovery_sources(out_a, "beat", "CACHED_STAGE_B_ONSET_AUTOCORRELATION")
            + _recovery_sources(in_a, "beat", "CACHED_STAGE_B_ONSET_AUTOCORRELATION"),
            beat_conf,
            "SUFFICIENT" if beat_conf == "HIGH" else "INSUFFICIENT",
            "BEAT_TIMING_MEASUREMENT",
        ),
        "downbeat_confidence_source": lane(
            _recovery_sources(out_a, "downbeat", "CACHED_STAGE_B_KICK_PHASE_HEURISTIC")
            + _recovery_sources(in_a, "downbeat", "CACHED_STAGE_B_KICK_PHASE_HEURISTIC"),
            downbeat_conf,
            "SUFFICIENT" if downbeat_conf == "HIGH" else "INSUFFICIENT",
            "BAR_PHASE_MEASUREMENT",
        ),
        "structure_confidence_source": lane(
            _recovery_sources(out_a, "structure", out_a["candidates"].get("exit_structure_evidence_method", "UNKNOWN"))
            + _recovery_sources(in_a, "structure", "CACHED_STAGE_B_ENTRY_BOUNDARY"),
            out_a["candidates"].get("exit_structure_confidence", "NONE"),
            "SUFFICIENT" if structure_compatibility == "COMPATIBLE" else "INSUFFICIENT",
            "SECTION_OR_FUNCTIONAL_BOUNDARY_EVIDENCE",
        ),
        "genre_style_confidence_source": lane(
            _recovery_sources(out_a, "genre_style", out_a.get("genre_tag_provenance", "UNKNOWN"))
            + _recovery_sources(in_a, "genre_style", in_a.get("genre_tag_provenance", "UNKNOWN")),
            "HIGH" if (out_a.get("genre_tags") and in_a.get("genre_tags")) else "NONE",
            "AVAILABLE" if (out_a.get("genre_tags") and in_a.get("genre_tags")) else "UNKNOWN",
            "OWNER_LOCAL_GENERIC_STYLE_OR_AUDIO_ORACLE",
        ),
        "harmonic_confidence_source": lane(
            _recovery_sources(out_a, "harmonic", "CACHED_STAGE_B_STFT_CHROMA")
            + _recovery_sources(in_a, "harmonic", "CACHED_STAGE_B_STFT_CHROMA"),
            harmonic_conf,
            "AVAILABLE" if harmonic is not None else "UNKNOWN",
            "BOUNDARY_LOCAL_KEY_CHROMA_MEASUREMENT",
        ),
        "vocal_proxy_confidence_source": lane(
            ["CACHED_STAGE_B_VOCAL_FORMANT_ENERGY_PROXY"],
            "HEURISTIC_PROXY",
            "MEASURED",
            "VOCAL_ACTIVITY_PROXY_NOT_SOURCE_SEPARATION",
        ),
        "texture_measurement_confidence_source": lane(
            [out_a.get("texture", {}).get("method", "CACHED_STAGE_B_BOUNDARY_TEXTURE"),
             in_a.get("texture", {}).get("method", "CACHED_STAGE_B_BOUNDARY_TEXTURE")],
            "MEASURED",
            "COMPATIBLE" if texture_compatible else "INCOMPATIBLE",
            "BOUNDARY_LOCAL_TIMBRAL_RHYTHMIC_FEATURES",
        ),
        "bass_measurement_confidence_source": lane(
            [out_a.get("bass_percussion", {}).get("method", "CACHED_STAGE_B_LOW_BAND_ACTIVITY"),
             in_a.get("bass_percussion", {}).get("method", "CACHED_STAGE_B_LOW_BAND_ACTIVITY")],
            "MEASURED",
            "SAFE" if bass_percussion_collision_risk != "HIGH" else "UNSAFE",
            "BOUNDARY_LOCAL_LOW_FREQUENCY_ACTIVITY",
        ),
    }


def build_pair_compat_input(out_a: dict, in_a: dict) -> dict:
    # R1: real genre evidence, never fabricated.
    genre_out = out_a.get("genre_tags", [])
    genre_in = in_a.get("genre_tags", [])

    # Harmonic: boundary-localized + whole-track corroboration (unchanged
    # methodology from the prior pass -- this was already independent of
    # beat/downbeat, not part of the PM's R2/R3 findings).
    out_key_eff = corroborated_key(out_a.get("key_at_exit", out_a["key"]), out_a["key"])
    in_key_eff = corroborated_key(in_a.get("key_at_entry", in_a["key"]), in_a["key"])
    harmonic = harmonic_relationship(out_key_eff, in_key_eff)

    beat_conf = min_conf(out_a["beat"]["confidence"], in_a["beat"]["confidence"])
    downbeat_conf = min_conf(out_a["downbeat"]["confidence"], in_a["downbeat"]["confidence"])

    # R2: structure_compatibility from INDEPENDENT evidence only.
    out_structure_evidence = bool(out_a["candidates"]["exit_is_outro_tail_opportunity"] or out_a["candidates"]["exit_novelty_peak_detected"])
    in_structure_evidence = _entry_structural_evidence(in_a)
    structure_compatibility = "COMPATIBLE" if (out_structure_evidence and in_structure_evidence) else "UNKNOWN"

    exit_vr = out_a["candidates"]["exit_vocal_collision_risk"]
    entry_vr = in_a["candidates"]["entry_vocal_collision_risk"]
    vocal_collision_risk = _combine_risk_min_side(exit_vr, entry_vr)

    # R3: MEASURED bass/percussion collision risk (never hardcoded LOW).
    bass_percussion_collision_risk = _combine_risk_min_side(
        out_a["bass_percussion"]["exit_bass_activity"], in_a["bass_percussion"]["entry_bass_activity"],
    )

    # R3: MEASURED texture compatibility from timbral (centroid/flatness)
    # + rhythmic (onset density) boundary-local evidence, not RMS/vocal
    # alone.
    out_tex, in_tex = out_a["texture"], in_a["texture"]
    centroid_gap_ratio = abs(out_tex["exit_spectral_centroid_hz"] - in_tex["entry_spectral_centroid_hz"]) / max(
        out_tex["exit_spectral_centroid_hz"], in_tex["entry_spectral_centroid_hz"], 1.0)
    flatness_gap = abs(out_tex["exit_spectral_flatness"] - in_tex["entry_spectral_flatness"])
    onset_density_gap_ratio = abs(out_tex["exit_onset_density_per_s"] - in_tex["entry_onset_density_per_s"]) / max(
        out_tex["exit_onset_density_per_s"], in_tex["entry_onset_density_per_s"], 0.1)
    texture_compatible = bool(
        centroid_gap_ratio <= TEXTURE_CENTROID_GAP_RATIO_MAX
        and flatness_gap <= TEXTURE_FLATNESS_GAP_MAX
        and onset_density_gap_ratio <= TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX
        and vocal_collision_risk != "HIGH"
    )

    # R5: PRE-RENDER source-level loudness/energy-continuity diagnostics.
    projected_loudness_gap_db = abs(out_a["loudness"]["exit_region_rms_db"] - in_a["loudness"]["entry_region_rms_db"])
    projected_bass_gap_db = abs(out_a["bass_percussion"]["exit_bass_energy_db"] - in_a["bass_percussion"]["entry_bass_energy_db"])
    combined_energy_gap_db = projected_loudness_gap_db + 0.5 * projected_bass_gap_db
    if combined_energy_gap_db <= ENERGY_STRONG_MAX_DB:
        energy_continuity_bucket = "STRONG"
    elif combined_energy_gap_db <= ENERGY_MODERATE_MAX_DB:
        energy_continuity_bucket = "MODERATE"
    else:
        energy_continuity_bucket = "WEAK"
    # compatibility.py's own field only distinguishes STRONG vs not-STRONG
    # (energy_ok = energy_continuity == "STRONG"); MODERATE/WEAK both
    # correctly fail that specific gate the same way real acoustic evidence
    # would.
    energy_continuity_field = "STRONG" if energy_continuity_bucket == "STRONG" else "WEAK"

    # Canonical R2 baseline: preserve the existing scalar aggregate exactly.
    # measurements underlying structure/genre/harmonic evidence for THIS
    # pair/boundary -- not the outgoing candidate's own structure label
    # repeated. Deliberately does NOT re-test beat/downbeat/vocal/bass/
    # texture pass-fail here: those already have their OWN dedicated gates
    # in compatibility.py (BEAT_CONFIDENCE_INSUFFICIENT etc.) -- re-folding
    # them into analysis_confidence would require the SAME evidence to
    # independently clear the SAME bar twice.  The confidence-ledger
    # diagnostic in pair_gate_audit.py therefore does not count this scalar
    # as another independent measurement; changing the canonical R2 contract
    # remains PM-owned.
    structure_strength = out_a["candidates"]["exit_structure_confidence"] if structure_compatibility == "COMPATIBLE" else "LOW"
    genre_strength = "HIGH" if (genre_out and genre_in) else "LOW"
    harmonic_strength = min_conf(out_key_eff["confidence"], in_key_eff["confidence"]) if harmonic is not None else "LOW"
    analysis_confidence = min_conf(structure_strength, genre_strength, harmonic_strength)
    confidence_ledger = build_confidence_ledger(
        out_a,
        in_a,
        structure_compatibility=structure_compatibility,
        harmonic=harmonic,
        texture_compatible=texture_compatible,
        vocal_collision_risk=vocal_collision_risk,
        bass_percussion_collision_risk=bass_percussion_collision_risk,
    )

    return {
        "outgoing": {"genre_tags": genre_out, "bpm": out_a["tempo"]["bpm"]},
        "incoming": {"genre_tags": genre_in, "bpm": in_a["tempo"]["bpm"]},
        "beat_confidence": beat_conf,
        "downbeat_confidence": downbeat_conf,
        "harmonic_relationship": harmonic,
        "energy_continuity": energy_continuity_field,
        "structure_compatibility": structure_compatibility,
        "vocal_collision_risk": vocal_collision_risk,
        "bass_percussion_collision_risk": bass_percussion_collision_risk,
        "intro_outro_texture_compatible": texture_compatible,
        "analysis_confidence": analysis_confidence,
        "_confidence_ledger": confidence_ledger,
        "_out_structure_evidence": out_structure_evidence,
        "_in_structure_evidence": in_structure_evidence,
        "_projected_loudness_gap_db": round(projected_loudness_gap_db, 2),
        "_projected_bass_gap_db": round(projected_bass_gap_db, 2),
        "_combined_energy_gap_db": round(combined_energy_gap_db, 2),
        "_energy_continuity_bucket": energy_continuity_bucket,
        "_centroid_gap_ratio": round(centroid_gap_ratio, 3),
        "_flatness_gap": round(flatness_gap, 3),
        "_onset_density_gap_ratio": round(onset_density_gap_ratio, 3),
    }


def build_manifest_pair(pair_id: str, category: str, out_id: str, in_id: str, out_a: dict, in_a: dict, compat_input: dict):
    exit_conf = out_a["candidates"]["exit_structure_confidence"]
    both_grid_strong_in = in_a["beat"]["confidence"] == "HIGH" and in_a["downbeat"]["confidence"] == "HIGH"

    # R2 repair: musical_unit_complete comes from the SAME independent
    # structural evidence used for structure_compatibility above -- never
    # from beat/downbeat confidence alone.
    musical_unit_complete = bool(compat_input["_out_structure_evidence"] and exit_conf != "LOW")

    outgoing = {
        "path": None,
        "duration_ms": out_a["duration_ms"],
        "bpm": out_a["tempo"]["bpm"],
        "genre_tags": out_a.get("genre_tags", []),
        "exit_candidate_t_ms": int(round(out_a["candidates"]["exit_candidate_t_ms"])),
        "beat_downbeat_aligned": bool(out_a["beat"]["confidence"] == "HIGH" and out_a["downbeat"]["confidence"] == "HIGH"),
        "in_acceptable_exit_region": bool(out_a["candidates"]["exit_candidate_t_ms"] / max(out_a["duration_ms"], 1.0) >= 0.5),
        "musical_unit_complete": musical_unit_complete,
        "is_outro_tail_opportunity": bool(out_a["candidates"]["exit_is_outro_tail_opportunity"]),
        "vocal_collision_risk": out_a["candidates"]["exit_vocal_collision_risk"],
        "structure_confidence": exit_conf,
        "energy_continuity_hint": out_a["energy_continuity_hint"],
    }
    incoming = {
        "path": None,
        "bpm": in_a["tempo"]["bpm"],
        "genre_tags": in_a.get("genre_tags", []),
        "entry_candidate_t_ms": int(round(in_a["candidates"]["entry_candidate_t_ms"])),
        "beat_downbeat_aligned": bool(both_grid_strong_in),
        "phrase_section_evidence": bool(in_a["candidates"]["entry_has_detected_intro"]),
        "is_authored_silence_skip": bool(in_a["candidates"]["entry_is_authored_silence_skip"]),
    }
    # R4 repair: wire the real detected leading-silence evidence through so
    # real_music_pipeline.py::build_tx_fixture() can actually get a nonzero
    # entry accepted by the real R2 planner instead of forcing 0ms.
    if incoming["is_authored_silence_skip"]:
        incoming["leading_silence_is_authored_non_musical"] = True
        incoming["leading_silence_ms"] = incoming["entry_candidate_t_ms"]
    else:
        incoming["leading_silence_is_authored_non_musical"] = False
        incoming["leading_silence_ms"] = 0

    pair_compatibility = {k: v for k, v in compat_input.items() if not k.startswith("_")}
    return {
        "pair_id": pair_id,
        "category": category,
        "outgoing": outgoing,
        "incoming": incoming,
        "pair_compatibility": pair_compatibility,
    }


def exit_candidate_renderable(out_a: dict) -> bool:
    """
    The REAL accepted R2 eligibility guard (policy/eligibility.py Guard 2,
    `LOW_CONFIDENCE_NO_FABRICATED_CERTAINTY`) rejects ANY exit candidate
    whose structure_confidence is below MEDIUM, independent of transition
    CLASS (this applies even to a downgraded SIMPLE_CROSSFADE/V3 pair, not
    only FULL_DJ_BLEND) -- a pair whose outgoing exit candidate is LOW
    confidence produces `NO_SPECIAL_TRANSITION` (no renderable transition
    at all), not merely a downgraded one. This was previously invisible
    because the old (beat/downbeat-derived) structure_confidence was
    fabricated HIGH/MEDIUM far more often than the real evidence supports.
    Filtering on this HERE (before ranking) avoids selecting a pair that
    the real planner would then refuse to render.
    """
    return out_a["candidates"]["exit_structure_confidence"] in ("MEDIUM", "HIGH")


def build_candidate(out_id: str, in_id: str, out_a: dict, in_a: dict, relation: str, stretch_pct: float, ratio: float, require_full_dj: bool):
    compat_input = build_pair_compat_input(out_a, in_a)
    compat = evaluate_pair_compatibility({**compat_input})
    hard_gate_pass = (compat.overall_dynamic_mix_eligible if require_full_dj else True) and exit_candidate_renderable(out_a)
    return {
        "out_id": out_id, "in_id": in_id, "relation": relation, "stretch_pct": stretch_pct, "ratio": ratio,
        "compat_input": compat_input, "compat": compat, "hard_gate_pass": hard_gate_pass,
    }


def rank_key(cand: dict, tempo_target_center: float, out_a_lookup, in_a_lookup):
    out_a = out_a_lookup(cand["out_id"])
    preservation_ratio = out_a["candidates"]["exit_candidate_t_ms"] / max(out_a["duration_ms"], 1.0)
    ci = cand["compat_input"]
    return (
        0 if cand["hard_gate_pass"] else 1,                                    # 1. hard safety gates
        -preservation_ratio,                                                    # 2. near-whole-song preservation
        0,                                                                      # 3. clean entry (structurally guaranteed by construction)
        0 if ci["structure_compatibility"] == "COMPATIBLE" else 1,              # 4a. structure
        0 if ci["intro_outro_texture_compatible"] else 1,                       # 4b. texture
        0 if ci["vocal_collision_risk"] not in ("HIGH", "MEDIUM") else 1,       # 4c. vocal safety
        0 if ci["bass_percussion_collision_risk"] != "HIGH" else 1,             # 4d. bass safety
        ci["_combined_energy_gap_db"],                                         # 5. source loudness/energy continuity (smaller = better)
        0 if ci["harmonic_relationship"] == "COMPATIBLE" else 1,                # 6. harmonic
        abs(cand["stretch_pct"] - tempo_target_center),                        # 7. tempo-correction burden
        cand["out_id"], cand["in_id"],                                         # 8. deterministic opaque-ID tie-break LAST
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--manifest-out", required=True)
    ap.add_argument("--trace-out", required=True)
    ap.add_argument("--rationale-out", required=True)
    args = ap.parse_args()

    corpus_dir = Path(args.corpus_dir)
    id_map = json.loads((corpus_dir / "id_map.local.json").read_text(encoding="utf-8"))
    analysis = json.loads((corpus_dir / "corpus_analysis.local.json").read_text(encoding="utf-8"))
    ids = sorted(analysis.keys())

    v1_pool, v2_pool, v3_pool = [], [], []

    for out_id in ids:
        out_a = analysis[out_id]
        for in_id in ids:
            if out_id == in_id:
                continue
            in_a = analysis[in_id]
            relation, stretch_pct, ratio, requires_change = _tempo_relation(out_a["tempo"]["bpm"], in_a["tempo"]["bpm"])

            if relation in ("DIRECT", "HALF_DOUBLE") and stretch_pct <= 0.02:
                cand = build_candidate(out_id, in_id, out_a, in_a, relation, stretch_pct, ratio, require_full_dj=True)
                if cand["hard_gate_pass"]:
                    v1_pool.append(cand)

            if relation in ("DIRECT", "HALF_DOUBLE") and 0.03 <= stretch_pct <= 0.06:
                cand = build_candidate(out_id, in_id, out_a, in_a, relation, stretch_pct, ratio, require_full_dj=True)
                if cand["hard_gate_pass"]:
                    v2_pool.append(cand)

            if relation == "EXCESSIVE_STRETCH":
                cand = build_candidate(out_id, in_id, out_a, in_a, relation, stretch_pct, ratio, require_full_dj=True)
                # PM STAGE-B EVIDENCE AUDIT REPAIR B1: V3 must still
                # produce a RENDERABLE transition (downgraded to whatever
                # class the real planner allows) -- it is a negative CLASS
                # control (FULL_DJ withheld, a genuine EXCESSIVE_STRETCH
                # tempo mismatch), never "no transition at all". Pool
                # MEMBERSHIP is what guarantees the negative-control
                # property (not FULL_DJ eligible + a real measured tempo
                # incompatibility); RANKING among pool members uses the
                # EXACT SAME rank_key() as V1/V2 (previously it used only
                # beat-confidence + opaque-ID, ignoring preservation/
                # structure/texture/vocal/bass/energy/harmonic entirely --
                # see the PM STAGE-B REAL-EVIDENCE REPAIR REVIEW finding).
                if not cand["compat"].overall_dynamic_mix_eligible and exit_candidate_renderable(out_a):
                    v3_pool.append(cand)

    def pick_best(pool, tempo_target_center):
        if not pool:
            return None
        ranked = sorted(pool, key=lambda c: rank_key(c, tempo_target_center, lambda i: analysis[i], lambda i: analysis[i]))
        return ranked[0]

    best_v1 = pick_best(v1_pool, tempo_target_center=0.0)
    best_v2 = pick_best(v2_pool, tempo_target_center=0.045)
    # V3's tempo dimension prefers the SMALLEST useful excess beyond the
    # R2 hard envelope ceiling (0.12) where otherwise equivalent -- "least
    # gratuitously mismatched still-genuine negative control", not the
    # largest deviation available.
    best_v3 = pick_best(v3_pool, tempo_target_center=0.12)

    manifest_pairs = []
    rationale = {}

    def emit(tag, category, best):
        if best is None:
            rationale[tag] = {"status": "NO_VALID_PAIR_FOUND", "category": category}
            return
        out_id, in_id = best["out_id"], best["in_id"]
        out_a, in_a = analysis[out_id], analysis[in_id]
        pair = build_manifest_pair(f"REAL-{tag}", category, out_id, in_id, out_a, in_a, best["compat_input"])
        pair["outgoing"]["path"] = id_map[out_id]
        pair["incoming"]["path"] = id_map[in_id]
        manifest_pairs.append(pair)
        ci = best["compat_input"]
        rationale[tag] = {
            "status": "SELECTED",
            "category": category,
            "outgoing_opaque_id": out_id,
            "incoming_opaque_id": in_id,
            "outgoing_bpm": out_a["tempo"]["bpm"],
            "incoming_bpm": in_a["tempo"]["bpm"],
            "tempo_deviation_pct": round(best["stretch_pct"] * 100, 2),
            "required_tempo_ratio": best["ratio"],
            "outgoing_beat_confidence": out_a["beat"]["confidence"],
            "outgoing_downbeat_confidence": out_a["downbeat"]["confidence"],
            "incoming_beat_confidence": in_a["beat"]["confidence"],
            "incoming_downbeat_confidence": in_a["downbeat"]["confidence"],
            "outgoing_genre_tags": out_a.get("genre_tags", []),
            "incoming_genre_tags": in_a.get("genre_tags", []),
            "structure_compatibility": ci["structure_compatibility"],
            "structure_evidence_method": out_a["candidates"]["exit_structure_evidence_method"],
            "bass_percussion_collision_risk": ci["bass_percussion_collision_risk"],
            "intro_outro_texture_compatible": ci["intro_outro_texture_compatible"],
            "analysis_confidence": ci["analysis_confidence"],
            "harmonic_relationship": ci["harmonic_relationship"],
            "projected_loudness_gap_db": ci["_projected_loudness_gap_db"],
            "projected_bass_gap_db": ci["_projected_bass_gap_db"],
            "combined_energy_gap_db": ci["_combined_energy_gap_db"],
            "energy_continuity_bucket": ci["_energy_continuity_bucket"],
            "overall_dynamic_mix_eligible": best["compat"].overall_dynamic_mix_eligible,
            "reason_codes": best["compat"].reason_codes,
            "selection_pool_size": len(v1_pool if tag == "V1" else v2_pool if tag == "V2" else v3_pool),
        }

    emit("V1", "close_tempo_minimal_stretch", best_v1)
    emit("V2", "conditional_tempo_correction", best_v2)
    emit("V3", "incompatible_downgrade", best_v3)

    Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_out).write_text(json.dumps({"pairs": manifest_pairs}, indent=2), encoding="utf-8")

    # PM STAGE-B EVIDENCE AUDIT REPAIR B4: near-miss forensics, computed
    # from the FULL tempo-eligible universe BEFORE the final hard-gate
    # rejection (deferred import -- pair_gate_audit imports this module
    # too, for its build_pair_compat_input; both only reference each
    # other's attributes at call time, never at import time, so the
    # circularity resolves cleanly).
    import pair_gate_audit
    v1_records = pair_gate_audit.audit_universe(analysis, 0.0, 0.02)
    v2_records = pair_gate_audit.audit_universe(analysis, 0.03, 0.06)

    Path(args.trace_out).parent.mkdir(parents=True, exist_ok=True)
    full_trace = {
        "pool_sizes": {"v1": len(v1_pool), "v2": len(v2_pool), "v3": len(v3_pool)},
        "v1_top5": [(c["out_id"], c["in_id"], round(c["stretch_pct"] * 100, 2), c["compat_input"]["_combined_energy_gap_db"]) for c in sorted(v1_pool, key=lambda c: rank_key(c, 0.0, lambda i: analysis[i], lambda i: analysis[i]))[:5]],
        "v2_top5": [(c["out_id"], c["in_id"], round(c["stretch_pct"] * 100, 2), c["compat_input"]["_combined_energy_gap_db"]) for c in sorted(v2_pool, key=lambda c: rank_key(c, 0.045, lambda i: analysis[i], lambda i: analysis[i]))[:5]],
        "v3_top5": [(c["out_id"], c["in_id"], round(c["stretch_pct"] * 100, 2), c["compat_input"]["_combined_energy_gap_db"]) for c in sorted(v3_pool, key=lambda c: rank_key(c, 0.12, lambda i: analysis[i], lambda i: analysis[i]))[:5]],
        "v1_near_misses_top10_ranked_by_fewest_failed_gates": pair_gate_audit.rank_near_misses(v1_records, top_n=10),
        "v2_near_misses_top10_ranked_by_fewest_failed_gates": pair_gate_audit.rank_near_misses(v2_records, top_n=10),
    }
    Path(args.trace_out).write_text(json.dumps(full_trace, indent=2), encoding="utf-8")

    Path(args.rationale_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.rationale_out).write_text(json.dumps(rationale, indent=2), encoding="utf-8")

    for tag in ("V1", "V2", "V3"):
        print(f"{tag}: {rationale[tag]['status']}" + (f" ({rationale[tag]['outgoing_opaque_id']} -> {rationale[tag]['incoming_opaque_id']})" if rationale[tag]["status"] == "SELECTED" else ""))
    print(f"pool sizes: V1={len(v1_pool)} V2={len(v2_pool)} V3={len(v3_pool)}")


if __name__ == "__main__":
    main()
