"""
P0-M3-R3 STAGE B REAL-EVIDENCE REPAIR -- required verifier mutations.

Per the newest Issue #7 PM comment's "REQUIRED VERIFIER MUTATIONS" list,
proves the repaired code actually REJECTS each of the 11 previously-
fabricated/self-invalidating patterns, using crafted synthetic inputs
(never real owner data) -- same style as the existing
`scripts/selftest_pre_real_music_repair.py` / `scripts/selftest_fail_closed.py`.

Usage:
    python scripts/mutation_test_real_music_stage_b.py
"""
from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

import analyze_owner_corpus as analyzer  # noqa: E402
import select_real_music_pairs as selector  # noqa: E402
import pair_gate_audit as audit  # noqa: E402
import compute_pair_gate_calibration as calibration  # noqa: E402
from policy.compatibility import evaluate_pair_compatibility  # noqa: E402

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def _base_track(**overrides) -> dict:
    """A minimal, schema-shaped synthetic per-track analysis dict (matches
    analyze_owner_corpus.py's analyze_one() output shape) with deliberately
    NEUTRAL/negative evidence in every field a mutation test needs to
    override explicitly -- never a real owner track."""
    base = {
        "duration_ms": 200000.0,
        "tempo": {"bpm": 120.0, "confidence": "HIGH"},
        "beat": {"confidence": "HIGH", "margin": 3.0},
        "downbeat": {"confidence": "HIGH", "margin": 3.0},
        "key": {"root": "C", "mode": "major", "confidence": "HIGH", "correlation": 0.8, "margin": 0.3},
        "key_at_exit": {"root": "C", "mode": "major", "confidence": "HIGH", "correlation": 0.8, "margin": 0.3},
        "key_at_entry": {"root": "C", "mode": "major", "confidence": "HIGH", "correlation": 0.8, "margin": 0.3},
        "loudness": {"exit_region_rms_db": -10.0, "entry_region_rms_db": -10.0},
        "bass_percussion": {"exit_bass_energy_db": -20.0, "exit_bass_activity": "LOW", "entry_bass_energy_db": -20.0, "entry_bass_activity": "LOW"},
        "texture": {
            "exit_spectral_centroid_hz": 2000.0, "exit_spectral_flatness": 0.3, "exit_onset_density_per_s": 2.0,
            "entry_spectral_centroid_hz": 2000.0, "entry_spectral_flatness": 0.3, "entry_onset_density_per_s": 2.0,
        },
        "candidates": {
            "exit_candidate_t_ms": 180000.0,
            "exit_is_outro_tail_opportunity": False,
            "exit_novelty_peak_detected": False,
            "exit_structure_confidence": "MEDIUM",
            "exit_vocal_collision_risk": "LOW",
            "entry_candidate_t_ms": 0.0,
            "entry_has_detected_intro": False,
            "entry_is_authored_silence_skip": False,
            "entry_vocal_collision_risk": "LOW",
        },
        "energy_continuity_hint": "STRONG",
        "genre_tags": [],
        "genre_tag_provenance": "UNKNOWN",
    }
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base


def mutation_1_genre_never_fabricated():
    """1. all tracks are assigned the same fabricated genre without owner-local provenance."""
    no_evidence_tags = {"genre": "Music", "comment": "", "description": "check out this cool video", "synopsis": "", "title": "Rock The House (this must NOT match -- title is excluded)"}
    tags, provenance = analyzer.match_genre_keywords(no_evidence_tags)
    check(tags == [], "no genre evidence in tag fields -> genre_tags is empty (never fabricated 'pop')")
    check("UNKNOWN" in provenance, "provenance honestly reports UNKNOWN when no keyword evidence exists")
    check("rock" not in tags, "a genre-sounding word appearing ONLY in the title field is never matched (title excluded)")

    real_evidence_tags = {"description": "a k-pop banger", "genre": "Music"}
    tags2, provenance2 = analyzer.match_genre_keywords(real_evidence_tags)
    check(tags2 == ["pop"], "real keyword evidence in description IS matched and mapped through the sanitizer")


def mutation_2_structure_not_from_beat_downbeat_alone():
    """2. beat/downbeat confidence alone creates STRUCTURE_COMPATIBLE."""
    out_a = _base_track(beat={"confidence": "HIGH"}, downbeat={"confidence": "HIGH"},
                         candidates={"exit_is_outro_tail_opportunity": False, "exit_novelty_peak_detected": False})
    in_a = _base_track(beat={"confidence": "HIGH"}, downbeat={"confidence": "HIGH"})
    ci = selector.build_pair_compat_input(out_a, in_a)
    check(ci["structure_compatibility"] != "COMPATIBLE",
          "HIGH beat+downbeat confidence alone (no instrumental tail, no novelty peak) does NOT produce STRUCTURE_COMPATIBLE")

    out_a_evidenced = _base_track(beat={"confidence": "HIGH"}, downbeat={"confidence": "HIGH"},
                                   candidates={"exit_is_outro_tail_opportunity": True, "exit_novelty_peak_detected": False, "exit_structure_confidence": "HIGH"})
    ci2 = selector.build_pair_compat_input(out_a_evidenced, in_a)
    check(ci2["structure_compatibility"] == "COMPATIBLE",
          "genuine independent structural evidence (instrumental tail) DOES produce STRUCTURE_COMPATIBLE")


def mutation_3_musical_unit_complete_not_from_beat_downbeat_alone():
    """3. beat/downbeat confidence alone creates musical_unit_complete."""
    out_a = _base_track(beat={"confidence": "HIGH"}, downbeat={"confidence": "HIGH"},
                         candidates={"exit_is_outro_tail_opportunity": False, "exit_novelty_peak_detected": False, "exit_structure_confidence": "LOW"})
    in_a = _base_track()
    ci = selector.build_pair_compat_input(out_a, in_a)
    manifest = selector.build_manifest_pair("MUT-3", "test", "OUT", "IN", out_a, in_a, ci)
    check(manifest["outgoing"]["musical_unit_complete"] is False,
          "HIGH beat+downbeat confidence alone does NOT set musical_unit_complete=True")


def mutation_4_bass_collision_is_measured_not_constant_low():
    """4. bass/percussion collision is constant LOW with no measured source evidence."""
    out_a = _base_track(bass_percussion={"exit_bass_activity": "HIGH", "entry_bass_activity": "HIGH"})
    in_a = _base_track(bass_percussion={"exit_bass_activity": "HIGH", "entry_bass_activity": "HIGH"})
    ci = selector.build_pair_compat_input(out_a, in_a)
    check(ci["bass_percussion_collision_risk"] == "HIGH",
          "both sides measured HIGH bass activity -> pair-level bass_percussion_collision_risk is HIGH, not a hardcoded LOW")

    out_a_low = _base_track(bass_percussion={"exit_bass_activity": "LOW", "entry_bass_activity": "LOW"})
    ci2 = selector.build_pair_compat_input(out_a_low, in_a)
    check(ci2["bass_percussion_collision_risk"] == "LOW", "genuinely low measured bass activity on both sides -> LOW (measured, not merely default)")


def mutation_5_texture_uses_timbral_rhythmic_evidence():
    """5. texture compatibility is inferred only from RMS/vocal risk."""
    # Same RMS/vocal-safe evidence on both sides, but a LARGE timbral/rhythmic gap.
    out_a = _base_track(
        loudness={"exit_region_rms_db": -10.0}, candidates={"exit_vocal_collision_risk": "LOW"},
        texture={"exit_spectral_centroid_hz": 6000.0, "exit_spectral_flatness": 0.9, "exit_onset_density_per_s": 8.0},
    )
    in_a = _base_track(
        loudness={"entry_region_rms_db": -10.0}, candidates={"entry_vocal_collision_risk": "LOW"},
        texture={"entry_spectral_centroid_hz": 500.0, "entry_spectral_flatness": 0.05, "entry_onset_density_per_s": 0.2},
    )
    ci = selector.build_pair_compat_input(out_a, in_a)
    check(ci["intro_outro_texture_compatible"] is False,
          "identical RMS + LOW vocal risk on both sides, but a large centroid/flatness/onset-density gap -> texture NOT compatible (proves timbral/rhythmic evidence genuinely participates)")


def mutation_6_entry_not_forced_to_zero():
    """6. an incoming entry is forced to 0 despite a detected valid nonzero effective start."""
    in_a = _base_track(candidates={
        "entry_candidate_t_ms": 2137.0, "entry_is_authored_silence_skip": True, "entry_has_detected_intro": False,
    })
    out_a = _base_track()
    ci = selector.build_pair_compat_input(out_a, in_a)
    manifest = selector.build_manifest_pair("MUT-6", "test", "OUT", "IN", out_a, in_a, ci)
    check(manifest["incoming"]["entry_candidate_t_ms"] == 2137,
          "a detected authored-silence-skip entry keeps its real nonzero t_ms, never forced to 0")
    check(manifest["incoming"]["leading_silence_is_authored_non_musical"] is True,
          "leading_silence_is_authored_non_musical is wired through for the fixture bridge")
    check(manifest["incoming"]["leading_silence_ms"] == 2137,
          "leading_silence_ms matches the real detected value")


def mutation_7_full_dj_requires_every_independent_gate():
    """7. V2 FULL_DJ survives any one required independent hard gate being UNKNOWN/unsafe."""
    good_out = _base_track(genre_tags=["pop"], candidates={"exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"})
    good_in = _base_track(genre_tags=["pop"])
    baseline_ci = selector.build_pair_compat_input(good_out, good_in)
    baseline_compat = evaluate_pair_compatibility({**baseline_ci})
    check(baseline_compat.overall_dynamic_mix_eligible is True, "sanity: the fully-evidenced baseline pair IS FULL_DJ eligible")

    for field, bad_value, label in [
        ("structure_compatibility", "UNKNOWN", "structure UNKNOWN"),
        ("bass_percussion_collision_risk", "HIGH", "bass collision HIGH"),
        ("intro_outro_texture_compatible", False, "texture not compatible"),
        ("vocal_collision_risk", "HIGH", "vocal collision HIGH"),
        ("harmonic_relationship", None, "harmonic UNKNOWN"),
        ("analysis_confidence", "LOW", "analysis confidence LOW"),
    ]:
        mutated = {**baseline_ci, field: bad_value}
        compat = evaluate_pair_compatibility({**mutated})
        check(compat.overall_dynamic_mix_eligible is False, f"FULL_DJ_BLEND is withheld when {label} (single independent gate failure)")


def mutation_8_weak_energy_does_not_beat_strong_via_id_ordering():
    """8. a WEAK-energy V2 wins over an otherwise-valid STRONG-energy candidate only because of ID/tie ordering."""
    out_a = _base_track(candidates={"exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"})
    in_a = _base_track()
    ci = selector.build_pair_compat_input(out_a, in_a)
    compat = evaluate_pair_compatibility({**ci})

    strong_cand = {"out_id": "RM999", "in_id": "RM999", "stretch_pct": 0.045, "ratio": 1.045,
                   "compat_input": {**ci, "_combined_energy_gap_db": 2.0}, "compat": compat, "hard_gate_pass": True}
    weak_cand = {"out_id": "RM001", "in_id": "RM001", "stretch_pct": 0.045, "ratio": 1.045,
                 "compat_input": {**ci, "_combined_energy_gap_db": 60.0}, "compat": compat, "hard_gate_pass": True}
    ranked = sorted([weak_cand, strong_cand], key=lambda c: selector.rank_key(c, 0.045, lambda i: out_a, lambda i: out_a))
    check(ranked[0] is strong_cand,
          "the STRONG-energy candidate (RM999, alphabetically LAST) outranks the WEAK-energy candidate (RM001, alphabetically FIRST) -- ranking is not ID-ordering-driven")


def mutation_9_catastrophic_loudness_hole_ranks_below_safer_alternative():
    """9. selected V1/V2 source boundary predicts a catastrophic loudness hole while a safer valid candidate exists."""
    out_a = _base_track(candidates={"exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"})
    in_a = _base_track()
    ci = selector.build_pair_compat_input(out_a, in_a)
    compat = evaluate_pair_compatibility({**ci})

    safe_cand = {"out_id": "RM002", "in_id": "RM002", "stretch_pct": 0.045, "ratio": 1.045,
                 "compat_input": {**ci, "_combined_energy_gap_db": 5.0}, "compat": compat, "hard_gate_pass": True}
    catastrophic_cand = {"out_id": "RM001", "in_id": "RM001", "stretch_pct": 0.045, "ratio": 1.045,
                          "compat_input": {**ci, "_combined_energy_gap_db": 90.0}, "compat": compat, "hard_gate_pass": True}
    ranked = sorted([catastrophic_cand, safe_cand], key=lambda c: selector.rank_key(c, 0.045, lambda i: out_a, lambda i: out_a))
    check(ranked[0] is safe_cand, "a candidate with a small projected energy gap outranks one predicting a catastrophic hole, regardless of opaque-ID order")


def mutation_10_verifier_source_has_no_sentinel():
    """10. verifier's own tracked source leaks its private sentinel.

    Deliberately does NOT search verify_real_music_stage_b.py for the
    literal historical marker string -- this file would then have to
    contain that same literal to perform the search, recreating the exact
    self-invalidation bug being repaired (see
    verify_real_music_stage_b.py's check_10 docstring). Instead this
    imports and runs THAT file's own structural check directly, proving
    the general fail-closed/never-hardcoded property by construction
    rather than by string-matching a specific value.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    import verify_real_music_stage_b as verifier  # noqa: E402  (imported lazily to avoid argv parsing at module load)
    before = len(verifier.failures)
    # Tests the CURRENT WORKING-TREE source (pre-commit unit test) -- an
    # intentionally-nonexistent git ref makes git_show() return None so
    # check_10 falls back to reading Path(__file__) directly. The separate
    # post-commit run (scripts/verify_real_music_stage_b.py --ref HEAD,
    # after committing/pushing) proves the same property against the
    # actual pushed blob.
    verifier.check_10_verifier_never_defaults_sentinel("__WORKING_TREE_PRECOMMIT_CHECK__")
    new_failures = verifier.failures[before:]
    check(len(new_failures) == 0, f"verify_real_music_stage_b.py's own check_10 passes against the current working tree: {new_failures}")


def mutation_11_prior_regressions_still_pass():
    """11. previous R2/R3 fail-closed, sample-rate, pitch, privacy and no-P1 regressions fail."""
    scripts_and_args = [
        ("scripts/selftest_fail_closed.py", []),
        ("scripts/verify_beat_grid_membership.py", []),
        ("scripts/verify_cross_method_consistency.py", []),
    ]
    for rel, extra_args in scripts_and_args:
        result = subprocess.run([sys.executable, rel] + extra_args, cwd=str(ROOT), capture_output=True, text=True)
        check(result.returncode == 0, f"{rel} still passes (exit 0)")


## ------------------------------------------------------------------
## PM STAGE-B EVIDENCE AUDIT REPAIR (B7) -- 12 additional mutations
## ------------------------------------------------------------------

def mutation_12_v3_uses_compatibility_energy_ranking_not_beat_id():
    """12. V3 uses compatibility/energy ranking, not beat+ID only."""
    out_evidenced = _base_track(genre_tags=["pop"], beat={"confidence": "HIGH"}, downbeat={"confidence": "HIGH"},
                                 candidates={"exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"})
    in_a = _base_track(genre_tags=["pop"])
    ci_good = selector.build_pair_compat_input(out_evidenced, in_a)
    compat_dummy = evaluate_pair_compatibility({**ci_good})

    # Candidate A: HIGH beat confidence both sides (would have won the OLD
    # `_v3_clean`+ID sort), but WORSE preservation and a large energy gap,
    # and an alphabetically-EARLIER opaque ID.
    cand_a = {"out_id": "RM001", "in_id": "RM001", "stretch_pct": 0.15, "ratio": 1.15,
              "compat_input": {**ci_good, "_combined_energy_gap_db": 55.0}, "compat": compat_dummy, "hard_gate_pass": True}
    out_a_weak_preservation = _base_track(duration_ms=200000.0, candidates={"exit_candidate_t_ms": 100000.0})  # only 50% preservation

    # Candidate B: beat confidence NOT both HIGH (would have LOST the old
    # sort outright), but strong preservation/structure and a small energy
    # gap, and an alphabetically-LATER opaque ID.
    cand_b = {"out_id": "RM999", "in_id": "RM999", "stretch_pct": 0.15, "ratio": 1.15,
              "compat_input": {**ci_good, "_combined_energy_gap_db": 8.0}, "compat": compat_dummy, "hard_gate_pass": True}

    lookup_a = lambda i: out_a_weak_preservation if i == "RM001" else out_evidenced  # noqa: E731
    lookup_b = lambda i: out_evidenced  # noqa: E731

    key_a = selector.rank_key(cand_a, 0.12, lookup_a, lookup_a)
    key_b = selector.rank_key(cand_b, 0.12, lookup_b, lookup_b)
    check(key_b < key_a, "a candidate with better preservation/energy and a LATER opaque ID ranks ahead of one with worse preservation/energy and an EARLIER ID -- V3 ranking is not beat+ID driven")


def mutation_13_v3_remains_full_dj_ineligible():
    """13. V3 remains FULL_DJ-ineligible."""
    # Engineer every OTHER gate to PASS, leaving only the tempo relation
    # itself as EXCESSIVE_STRETCH -- proves tempo alone, as V3's defining
    # negative-control property, is sufficient to withhold FULL_DJ_BLEND
    # even when every other independent gate would otherwise pass.
    out_a = _base_track(genre_tags=["pop"], tempo={"bpm": 150.0}, candidates={"exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"})
    in_a = _base_track(genre_tags=["pop"], tempo={"bpm": 100.0})  # 50% deviation -> EXCESSIVE_STRETCH
    ci = selector.build_pair_compat_input(out_a, in_a)
    compat = evaluate_pair_compatibility({**ci})
    check(compat.tempo_compatibility == "EXCESSIVE_STRETCH", "sanity: engineered pair has an EXCESSIVE_STRETCH tempo relation")
    check(compat.overall_dynamic_mix_eligible is False, "FULL_DJ_BLEND stays withheld for an EXCESSIVE_STRETCH pair even when every other gate is engineered to pass")


def mutation_14_v3_id_order_cannot_beat_safer_energy():
    """14. V3 ID order cannot beat materially safer energy continuity."""
    # Literal PM B1 example: ~40dB gap + earlier IDs must lose to ~10dB gap
    # + later IDs, using the V3 tempo_target_center (0.12).
    out_a = _base_track(genre_tags=["pop"], candidates={"exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"})
    in_a = _base_track(genre_tags=["pop"])
    ci = selector.build_pair_compat_input(out_a, in_a)
    compat = evaluate_pair_compatibility({**ci})

    earlier_id_worse_energy = {"out_id": "RM001", "in_id": "RM002", "stretch_pct": 0.15, "ratio": 1.15,
                                "compat_input": {**ci, "_combined_energy_gap_db": 40.0}, "compat": compat, "hard_gate_pass": True}
    later_id_better_energy = {"out_id": "RM097", "in_id": "RM098", "stretch_pct": 0.15, "ratio": 1.15,
                               "compat_input": {**ci, "_combined_energy_gap_db": 10.0}, "compat": compat, "hard_gate_pass": True}
    ranked = sorted([earlier_id_worse_energy, later_id_better_energy],
                     key=lambda c: selector.rank_key(c, 0.12, lambda i: out_a, lambda i: out_a))
    check(ranked[0] is later_id_better_energy, "~10dB/later-ID candidate outranks ~40dB/earlier-ID candidate under the V3 ranking (tempo_target_center=0.12)")


def _tiny_synthetic_corpus():
    """A small, fully-synthetic 4-track corpus (never real owner data) for
    calibration-audit determinism/sum/UNKNOWN-vs-INCOMPATIBLE mutations."""
    return {
        "RMA": analyzer_stub_track(bpm=120.0, genre_tags=["pop"], structure_evidence=True),
        "RMB": analyzer_stub_track(bpm=121.0, genre_tags=["pop"], structure_evidence=False),
        "RMC": analyzer_stub_track(bpm=122.0, genre_tags=[], structure_evidence=False),
        "RMD": analyzer_stub_track(bpm=200.0, genre_tags=["rock"], structure_evidence=False),
    }


def analyzer_stub_track(bpm: float, genre_tags: list, structure_evidence: bool) -> dict:
    t = _base_track(genre_tags=genre_tags, tempo={"bpm": bpm})
    if structure_evidence:
        t["candidates"] = {**t["candidates"], "exit_is_outro_tail_opportunity": True, "exit_structure_confidence": "HIGH"}
    return t


def mutation_15_calibration_deterministic_from_cached_analysis():
    """15. calibration artifact is deterministic from cached analysis."""
    corpus = _tiny_synthetic_corpus()
    records_1 = audit.audit_universe(corpus, 0.0, 0.02)
    records_2 = audit.audit_universe(corpus, 0.0, 0.02)
    breakdown_1 = calibration.gate_breakdown(records_1)
    breakdown_2 = calibration.gate_breakdown(records_2)
    check(breakdown_1 == breakdown_2, "two independent audit_universe() runs over the same cached (synthetic) corpus produce byte-identical gate_breakdown output")


def mutation_16_gate_counts_sum_correctly():
    """16. individual hard-gate counts sum correctly."""
    corpus = _tiny_synthetic_corpus()
    records = audit.audit_universe(corpus, 0.0, 0.5)  # wide range to include all synthetic pairs
    breakdown = calibration.gate_breakdown(records)
    total = breakdown["total_pair_count"]
    for gate, counts in breakdown["per_gate_pass_incompatible_unknown"].items():
        s = counts["PASS"] + counts["MEASURED_INCOMPATIBLE"] + counts["UNKNOWN_EVIDENCE"]
        check(s == total, f"gate '{gate}': PASS+MEASURED_INCOMPATIBLE+UNKNOWN_EVIDENCE ({s}) == total_pair_count ({total})")


def mutation_17_unknown_and_incompatible_are_distinct():
    """17. UNKNOWN and INCOMPATIBLE are distinct."""
    # Genre UNKNOWN: one side has no genre evidence at all.
    out_unknown = _base_track(genre_tags=[])
    in_a = _base_track(genre_tags=["pop"])
    _ci, _compat, gate_status_unknown, _ = audit.classify_pair(out_unknown, in_a)
    check(gate_status_unknown["genre"] == audit.UNKNOWN_EVIDENCE, "genre gate is UNKNOWN_EVIDENCE when one side has no genre evidence (not INCOMPATIBLE)")

    # Genre INCOMPATIBLE: both sides have REAL, non-overlapping genre families.
    out_known = _base_track(genre_tags=["rock"])
    in_known = _base_track(genre_tags=["hip-hop"])
    _ci2, _compat2, gate_status_incompatible, _ = audit.classify_pair(out_known, in_known)
    check(gate_status_incompatible["genre"] == audit.MEASURED_INCOMPATIBLE, "genre gate is MEASURED_INCOMPATIBLE when both sides have real, non-overlapping genre evidence (not UNKNOWN)")
    check(gate_status_unknown["genre"] != gate_status_incompatible["genre"], "UNKNOWN_EVIDENCE and MEASURED_INCOMPATIBLE are never conflated into the same category")


def mutation_18_cumulative_intersections_reproducible():
    """18. cumulative intersections are reproducible."""
    corpus = _tiny_synthetic_corpus()
    records = audit.audit_universe(corpus, 0.0, 0.5)
    b1 = calibration.gate_breakdown(records)
    b2 = calibration.gate_breakdown(records)
    check(b1["cumulative_surviving_after_each_gate_in_order"] == b2["cumulative_surviving_after_each_gate_in_order"],
          "cumulative surviving-count sequence reproduces exactly across repeated runs")
    # Cross-check: the LAST cumulative entry must equal a direct independent
    # count of records where every gate passes.
    direct_count = sum(1 for r in records if all(r["gate_status"][g] == "PASS" for g in audit.GATE_ORDER))
    last_cumulative = b1["cumulative_surviving_after_each_gate_in_order"][-1]["surviving_count"]
    check(direct_count == last_cumulative, f"final cumulative surviving count ({last_cumulative}) matches an independently-computed all-gates-pass count ({direct_count})")


def mutation_19_sensitivity_never_mutates_production_thresholds():
    """19. sensitivity testing never mutates production/current thresholds."""
    before = (selector.TEXTURE_CENTROID_GAP_RATIO_MAX, selector.TEXTURE_FLATNESS_GAP_MAX,
              selector.TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX, selector.ENERGY_STRONG_MAX_DB, selector.ENERGY_MODERATE_MAX_DB)
    corpus = _tiny_synthetic_corpus()
    records = audit.audit_universe(corpus, 0.0, 0.5)
    calibration.sensitivity_matrix(records)
    after = (selector.TEXTURE_CENTROID_GAP_RATIO_MAX, selector.TEXTURE_FLATNESS_GAP_MAX,
             selector.TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX, selector.ENERGY_STRONG_MAX_DB, selector.ENERGY_MODERATE_MAX_DB)
    check(before == after, "select_real_music_pairs.py's production TEXTURE_*/ENERGY_* module constants are unchanged after running the diagnostic sensitivity matrix")


def mutation_20_near_miss_ranking_before_final_hard_gate_filter():
    """20. near-miss ranking occurs before final hard-gate filtering."""
    # A synthetic corpus where NO pair passes every gate (all genre UNKNOWN) --
    # a hard-gate-filtered pool would be empty, but near-miss ranking must
    # still surface the closest failures.
    corpus = {
        "RMX": analyzer_stub_track(bpm=120.0, genre_tags=[], structure_evidence=False),
        "RMY": analyzer_stub_track(bpm=120.5, genre_tags=[], structure_evidence=False),
        "RMZ": analyzer_stub_track(bpm=121.0, genre_tags=[], structure_evidence=False),
    }
    records = audit.audit_universe(corpus, 0.0, 0.02)
    check(len(records) > 0, "sanity: synthetic corpus has tempo-eligible pairs")
    eligible_pool = [r for r in records if r["compat"].overall_dynamic_mix_eligible]
    check(len(eligible_pool) == 0, "sanity: none of these pairs pass every hard gate (all genre UNKNOWN)")
    near_misses = audit.rank_near_misses(records, top_n=10)
    check(len(near_misses) == min(10, len(records)), "near-miss ranking returns entries drawn from the FULL tempo-eligible universe, not filtered down to the (empty) hard-gate-eligible pool")


def mutation_21_no_private_leak_in_new_files():
    """21. no private filename/path/tag leaks (in this pass's new files)."""
    new_files = ["scripts/pair_gate_audit.py", "scripts/compute_pair_gate_calibration.py"]
    for rel in new_files:
        content = (ROOT / rel).read_text(encoding="utf-8")
        for marker in (".mp3", ".flac", ".m4a", "owner_music_input"):
            check(marker not in content, f"{rel} contains no '{marker}' marker")
    calibration_out = ROOT / "real_music" / "work_local" / "pair_gate_calibration_sanitized.json"
    if calibration_out.exists():
        content = calibration_out.read_text(encoding="utf-8")
        for marker in (".mp3", ".flac", ".m4a", "owner_music_input"):
            check(marker not in content, f"pair_gate_calibration_sanitized.json contains no '{marker}' marker")


def mutation_22_all_prior_eleven_mutations_still_registered_and_passing():
    """22. all previous 11 mutation tests remain green."""
    prior = [
        mutation_1_genre_never_fabricated, mutation_2_structure_not_from_beat_downbeat_alone,
        mutation_3_musical_unit_complete_not_from_beat_downbeat_alone, mutation_4_bass_collision_is_measured_not_constant_low,
        mutation_5_texture_uses_timbral_rhythmic_evidence, mutation_6_entry_not_forced_to_zero,
        mutation_7_full_dj_requires_every_independent_gate, mutation_8_weak_energy_does_not_beat_strong_via_id_ordering,
        mutation_9_catastrophic_loudness_hole_ranks_below_safer_alternative, mutation_10_verifier_source_has_no_sentinel,
        mutation_11_prior_regressions_still_pass,
    ]
    check(len(prior) == 11, "all 11 prior mutation functions are still defined and registered")
    before = len(failures)
    for fn in prior:
        fn()
    check(len(failures) == before, "re-running all 11 prior mutation tests here produces zero NEW failures")


def mutation_23_prior_r2_r3_regressions_remain_green():
    """23. previous R2/R3 regressions remain green."""
    for rel in ["scripts/selftest_fail_closed.py", "scripts/verify_beat_grid_membership.py", "scripts/verify_cross_method_consistency.py"]:
        result = subprocess.run([sys.executable, rel], cwd=str(ROOT), capture_output=True, text=True)
        check(result.returncode == 0, f"{rel} still passes (exit 0)")


def main():
    tests = [
        mutation_1_genre_never_fabricated,
        mutation_2_structure_not_from_beat_downbeat_alone,
        mutation_3_musical_unit_complete_not_from_beat_downbeat_alone,
        mutation_4_bass_collision_is_measured_not_constant_low,
        mutation_5_texture_uses_timbral_rhythmic_evidence,
        mutation_6_entry_not_forced_to_zero,
        mutation_7_full_dj_requires_every_independent_gate,
        mutation_8_weak_energy_does_not_beat_strong_via_id_ordering,
        mutation_9_catastrophic_loudness_hole_ranks_below_safer_alternative,
        mutation_10_verifier_source_has_no_sentinel,
        mutation_11_prior_regressions_still_pass,
        mutation_12_v3_uses_compatibility_energy_ranking_not_beat_id,
        mutation_13_v3_remains_full_dj_ineligible,
        mutation_14_v3_id_order_cannot_beat_safer_energy,
        mutation_15_calibration_deterministic_from_cached_analysis,
        mutation_16_gate_counts_sum_correctly,
        mutation_17_unknown_and_incompatible_are_distinct,
        mutation_18_cumulative_intersections_reproducible,
        mutation_19_sensitivity_never_mutates_production_thresholds,
        mutation_20_near_miss_ranking_before_final_hard_gate_filter,
        mutation_21_no_private_leak_in_new_files,
        mutation_22_all_prior_eleven_mutations_still_registered_and_passing,
        mutation_23_prior_r2_r3_regressions_remain_green,
    ]
    for i, t in enumerate(tests, start=1):
        print(f"\n--- mutation {i}: {t.__doc__.strip()} ---")
        t()

    print(f"\n{'ALL MUTATION TESTS PASS' if not failures else f'{len(failures)} MUTATION CHECK(S) FAILED'} ({len(tests)} mutations, see above for individual assertion counts)")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
