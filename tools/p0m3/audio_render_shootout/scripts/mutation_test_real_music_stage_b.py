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
    ]
    for i, t in enumerate(tests, start=1):
        print(f"\n--- mutation {i}: {t.__doc__.strip()} ---")
        t()

    print(f"\n{'ALL MUTATION TESTS PASS' if not failures else f'{len(failures)} MUTATION CHECK(S) FAILED'} ({len(tests)} mutations, see above for individual assertion counts)")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
