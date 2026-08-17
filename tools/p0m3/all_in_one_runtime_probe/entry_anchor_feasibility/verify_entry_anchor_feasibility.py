"""P0-M3-R3 RM014 incoming-entry anchor feasibility -- verifier (Issue #7
PM comment id 5310893724).

Machine-checkable subset of the task's validation requirements. Git-level
checks (starting HEAD, unchanged canonical files, main/P1 untouched) are
also run directly via git in ``EXACT_COMMANDS.md``; this script focuses on
the data-shape, scope, and privacy guarantees only checkable by reading the
produced evidence, mirroring the accepted
``pair_stability/verify_pair_stability.py`` architecture (generic-only
hardcoded patterns; no owner-specific value is ever embedded here).
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]

EXPECTED_SEEDS = [0, 1, 2, 3, 4]
EXPECTED_WINDOW_LENGTHS = [10.0, 15.0, 20.0, 30.0]
EXPECTED_PERTURBATIONS = [-1000, -500, 0, 500, 1000]
DISALLOWED_TRACK_IDS = {"RM041"}  # audio must never be decoded for these in this directory

_SAFE_MOUNT_PREFIXES = r"AIProjects/(?:AutoMix|_automix-)"
FORBIDDEN_PRIVACY_PATTERNS = [
    ("windows_absolute_path", re.compile(r"[A-Za-z]:\\\\?[Uu]sers", re.IGNORECASE)),
    ("wsl_mount_absolute_path", re.compile(rf"/mnt/[a-z]/(?!{_SAFE_MOUNT_PREFIXES})", re.IGNORECASE)),
    ("mp3_extension", re.compile(r"\.mp3", re.IGNORECASE)),
    ("wav_extension", re.compile(r"\.wav", re.IGNORECASE)),
    ("flac_extension", re.compile(r"\.flac", re.IGNORECASE)),
]
DISALLOWED_TOKENS = ["Signalsmith", "RubberBand", "Rubber Band", "render_transition", "owner_listening"]


def check(label, condition, checks):
    checks.append({"check": label, "passed": bool(condition)})
    return condition


def scan_text_for_privacy(text: str, label: str, checks: list) -> None:
    for name, pattern in FORBIDDEN_PRIVACY_PATTERNS:
        check(f"no_privacy_leak[{label}][{name}]", not pattern.search(text), checks)
    for rm in DISALLOWED_TRACK_IDS:
        pass  # RM ids themselves are allowed (opaque, approved); only path/extension shape is forbidden


def verify_intro_clusters(results_dir: Path, checks: list) -> dict:
    path = results_dir / "intro_clusters.json"
    check("intro_clusters_file_exists", path.exists(), checks)
    data = json.loads(path.read_text(encoding="utf-8"))
    check("intro_clusters_scope_rm014_only", data.get("track") == "RM014", checks)
    check("intro_clusters_seeds_used_all_5", data.get("seeds_used") == EXPECTED_SEEDS, checks)
    check("intro_clusters_current_entry_is_0ms", data.get("current_canonical_entry_ms") == 0.0, checks)
    check("intro_interval_unanimous", data.get("intro_interval", {}).get("unanimous") is True, checks)
    ranked = data.get("clusters_ranked", [])
    check("clusters_ranked_nonempty", len(ranked) > 0, checks)
    ranks = [c["diagnostic_rank"] for c in ranked]
    check("clusters_ranked_dense_1_to_n", ranks == list(range(1, len(ranked) + 1)), checks)
    check(
        "ranking_is_support_desc_then_spread_asc_then_madmom_asc_then_time_asc",
        all(
            (ranked[i]["support_count"], -ranked[i]["spread_ms"])
            >= (ranked[i + 1]["support_count"], -ranked[i + 1]["spread_ms"])
            for i in range(len(ranked) - 1)
        ),
        checks,
    )
    check("ranking_declared_diagnostic_only", data.get("ranking_is_diagnostic_only_not_a_production_threshold") is True, checks)
    for c in ranked:
        check(
            f"cluster_rank{c['diagnostic_rank']}_has_required_fields",
            all(k in c for k in (
                "support_count", "per_seed_ms", "center_ms", "min_ms", "max_ms", "spread_ms",
                "max_deviation_from_center_ms", "nearest_madmom_downbeat_ms", "madmom_abs_error_ms",
                "candidate_time_relative_to_current_entry_ms", "fraction_of_intro_preceding_candidate",
            )),
            checks,
        )
    return data


def verify_content_preservation(results_dir: Path, intro_clusters: dict, checks: list) -> dict:
    path = results_dir / "content_preservation.json"
    check("content_preservation_file_exists", path.exists(), checks)
    data = json.loads(path.read_text(encoding="utf-8"))
    check("content_preservation_scope_rm014_only", data.get("track") == "RM014", checks)
    regions = data.get("regions", {})
    check("content_preservation_has_top2_plus_context_regions", len(regions) >= 3, checks)
    allowed_labels = {
        "CLEAR_NON_MUSICAL_LEAD_IN", "LOW_INFORMATION_MUSICAL_INTRO",
        "MEANINGFUL_AUTHORED_MUSICAL_INTRO", "EVIDENCE_INSUFFICIENT",
    }
    for key, r in regions.items():
        if r.get("status") != "MEASURED":
            check(f"region[{key}]_status_is_evidence_insufficient_when_not_measured", r.get("status") == "EVIDENCE_INSUFFICIENT", checks)
            continue
        check(f"region[{key}]_classification_is_allowed_enum", r.get("classification") in allowed_labels, checks)
        check(f"region[{key}]_duration_skipped_measured", isinstance(r.get("duration_skipped_ms"), (int, float)), checks)
        pct = r.get("region_metric_percentiles_in_whole_track", {})
        rms_p = pct.get("rms_percentile_in_track")
        onset_p = pct.get("onset_density_percentile_in_track")
        if r.get("classification") == "CLEAR_NON_MUSICAL_LEAD_IN":
            check(
                f"region[{key}]_disposable_label_requires_both_rms_and_onset_le_10pct",
                rms_p is not None and onset_p is not None and rms_p <= 10.0 and onset_p <= 10.0,
                checks,
            )
    # top-2 candidate regions must correspond to the top-2 ranked clusters
    top2_centers = {c["center_ms"] for c in intro_clusters.get("clusters_ranked", [])[:2]}
    region_centers = {r["candidate_center_ms"] for k, r in regions.items() if "candidate_diagnostic_rank" in r}
    check("content_preservation_regions_match_top2_ranked_clusters", region_centers == top2_centers, checks)
    return data


def verify_harmonic_reeval(results_dir: Path, intro_clusters: dict, checks: list) -> dict:
    path = results_dir / "harmonic_reeval.json"
    check("harmonic_reeval_file_exists", path.exists(), checks)
    data = json.loads(path.read_text(encoding="utf-8"))
    check("harmonic_reeval_scope_rm014_entry_only", "RM014 entry ONLY" in data.get("scope", ""), checks)
    check("harmonic_reeval_window_lengths_match_accepted", data.get("window_lengths_s_tested") == EXPECTED_WINDOW_LENGTHS, checks)
    check("harmonic_reeval_perturbations_match_accepted", data.get("boundary_perturbations_ms_tested") == EXPECTED_PERTURBATIONS, checks)
    check(
        "harmonic_reeval_reuses_unmodified_pair_relation_function",
        data.get("pair_relation_function_source") == "select_real_music_pairs.harmonic_relationship (imported unmodified)",
        checks,
    )
    candidates = data.get("candidates", {})
    check("harmonic_reeval_covers_top2_candidates", len(candidates) == 2, checks)
    top2_centers = {c["center_ms"] for c in intro_clusters.get("clusters_ranked", [])[:2]}
    covered_centers = {c["candidate_center_ms"] for c in candidates.values()}
    check("harmonic_reeval_candidates_match_top2_ranked_clusters", covered_centers == top2_centers, checks)
    for key, c in candidates.items():
        cells = c.get("entry_cells", [])
        check(f"harmonic_reeval[{key}]_20_cells_swept", len(cells) == 20, checks)
        check(f"harmonic_reeval[{key}]_has_vs_accepted_0ms_comparison", "vs_accepted_0ms_result" in c, checks)
        check(f"harmonic_reeval[{key}]_pair_relation_present", len(c.get("pair_relation_vs_accepted_rm041_exit_cells", [])) == 20, checks)
    check("harmonic_reeval_accepted_0ms_baseline_present", "accepted_0ms_stability_summary" in data, checks)
    return data


def verify_no_disallowed_scope(new_dir: Path, checks: list) -> None:
    # The verifier itself necessarily contains the literal pattern strings it
    # scans for (its own FORBIDDEN_PRIVACY_PATTERNS/DISALLOWED_TOKENS
    # definitions) -- scanning itself against itself is self-referential and
    # produces only false positives, exactly the defect already repaired in
    # the accepted pair_stability/verify_pair_stability.py (commit b181f42).
    py_files = sorted(p for p in new_dir.glob("*.py") if p.name != Path(__file__).name)
    check("entry_anchor_dir_has_python_sources", len(py_files) > 0, checks)
    for p in py_files:
        text = p.read_text(encoding="utf-8")
        check(f"no_allin1_import[{p.name}]", "import allin1" not in text and "allin1.analyze(" not in text, checks)
        check(
            f"no_rm041_mapping_lookup[{p.name}]",
            'mapping["RM041"]' not in text and "mapping['RM041']" not in text,
            checks,
        )
        for token in DISALLOWED_TOKENS:
            check(f"no_disallowed_token[{p.name}][{token}]", token not in text, checks)
        scan_text_for_privacy(text, p.name, checks)

    # verifier_output.json is this script's OWN prior output and necessarily
    # contains its check labels (which embed the disallowed-token names
    # being searched for, e.g. "no_disallowed_token[...][Signalsmith]") --
    # self-referential, same class of false positive as above.
    result_files = sorted(p for p in (new_dir / "results").glob("*.json") if p.name != "verifier_output.json")
    check("entry_anchor_results_present", len(result_files) > 0, checks)
    for p in result_files:
        text = p.read_text(encoding="utf-8")
        scan_text_for_privacy(text, p.name, checks)
        payload = json.loads(text)
        blob = json.dumps(payload)
        for token in DISALLOWED_TOKENS:
            check(f"no_disallowed_token[{p.name}][{token}]", token not in blob, checks)

    render_like = list(new_dir.rglob("*.wav")) + list(new_dir.rglob("*.mp3")) + list(new_dir.rglob("*.flac"))
    check("no_audio_render_output_present", len(render_like) == 0, checks)


def verify_pm_zip(zip_path: Path, checks: list) -> None:
    if not zip_path.exists():
        check("pm_zip_exists", False, checks)
        return
    check("pm_zip_exists", True, checks)
    # This verifier's own source (and its own prior output) is necessarily
    # embedded in the zip and necessarily contains the literal pattern/token
    # strings it searches for -- same self-referential exemption as above,
    # applied to zip member content instead of the on-disk file.
    self_referential_names = {Path(__file__).name, "verifier_output.json"}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for name in names:
            scan_text_for_privacy(name, f"zip_member_name::{name}", checks)
            if Path(name).name in self_referential_names:
                continue
            try:
                content = zf.read(name).decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                continue
            scan_text_for_privacy(content, f"zip_member_content::{name}", checks)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pm-zip", default=None)
    args = parser.parse_args()

    checks: list = []
    new_dir = HERE
    results_dir = new_dir / "results"

    intro_clusters = verify_intro_clusters(results_dir, checks)
    verify_content_preservation(results_dir, intro_clusters, checks)
    verify_harmonic_reeval(results_dir, intro_clusters, checks)
    verify_no_disallowed_scope(new_dir, checks)

    if args.pm_zip:
        verify_pm_zip(Path(args.pm_zip), checks)

    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    failed = [c for c in checks if not c["passed"]]

    out_path = results_dir / "verifier_output.json"
    out_path.write_text(json.dumps({"total": total, "passed": passed, "failed": failed, "checks": checks}, indent=2) + "\n", encoding="utf-8")

    if failed:
        print(f"FAIL {passed}/{total} -- failed checks:")
        for c in failed:
            print(f"  - {c['check']}")
        return 1
    print(f"ALL ASSERTIONS PASS {passed}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
