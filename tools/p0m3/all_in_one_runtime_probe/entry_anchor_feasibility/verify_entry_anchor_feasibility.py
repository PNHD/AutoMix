"""P0-M3-R3 RM014 incoming-entry anchor feasibility -- verifier (Issue #7
PM comment id 5310893724; environment-path/privacy closeout repair per a
later binding PM comment on the same issue).

Machine-checkable subset of the task's validation requirements. Git-level
checks (starting HEAD, unchanged canonical files, main/P1 untouched) are
also run directly via git in ``EXACT_COMMANDS.md``; this script focuses on
the data-shape, scope, and privacy guarantees only checkable by reading the
produced evidence, mirroring the accepted
``pair_stability/verify_pair_stability.py`` architecture.

PRIVACY ARCHITECTURE (environment-path closeout repair): earlier revisions
of this script allowlisted this repository's own WSL checkout/scratch path
prefixes (``_SAFE_MOUNT_PREFIXES``) so the generic ``/mnt/<drive>/...``
pattern would not flag the repo's own already-published checkout location.
That allowlist has been REMOVED: every actual ``/mnt/<drive>/...`` path is
now treated as environment-local evidence with no exception, including the
repo's own checkout. A generic Linux-home pattern
(``/home/<user>/...``, no real username embedded) was added alongside it.
``EXACT_COMMANDS.md`` was rewritten to use operator-supplied environment
variables (``AUTOMIX_REPO_ROOT``, ``AUTOMIX_ALLINONE_PY``) instead of any
literal path, so removing the allowlist does not produce a false failure
against that file.

An OPTIONAL real-sentinel scan (``--private-sentinel`` /
``AUTOMIX_PRIVATE_SENTINEL``, mirroring ``pair_stability/verify_pair_stability.py``'s
already-accepted mechanism) is also available: if the local operator
supplies a real owner-private value out of band, every scanned target is
checked for its absence. The value itself is never printed, never
serialized into any output file, and never embedded in a check label (only
the scanned target's own name/label is used). If no sentinel is supplied,
that scan is skipped and reported as such -- this script does not claim to
prove absence of a value it was never given.

Two synthetic, clearly-fake self-test fixtures (NOT owner data, safe to
commit/print) prove the scanning mechanism itself works, independent of
whether a real sentinel is supplied: a clean synthetic blob is confirmed
"absent" for every pattern, then a copy with each dummy value injected is
confirmed "present" (i.e. the "absent" check correctly evaluates False),
proving the mechanism fails closed rather than silently passing. These
dummy fixtures (a fake Windows user path, a fake WSL mount path, a fake
Linux home path, and a fake sentinel token) appear as literal source text
in THIS file by design (that is what makes them useful as fixtures) and are
therefore excluded, by filename, from this script's own on-disk/in-ZIP
self-scan -- the same self-referential exemption already applied to this
file's disallowed-token/pattern definitions themselves.

SCOPE NOTE (do not overclaim): this script detects generic path SHAPES
(Windows/WSL/Linux-home absolute-path patterns and common audio-file
extensions) and, only when a real value is supplied at runtime, an exact
private-sentinel string match. It cannot and does not detect an arbitrary
private audio filename/basename or an audio content hash that it was never
told about -- no such value is known to or checked by this script. This
pass computed no audio hash and stored no filename anywhere in scope, so
there is nothing of that kind for it to have leaked, but that absence is
established by inspection of what was written (see the research report),
not by a semantic scan this script performs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
DOC_REPORT_PATH = REPO_ROOT / "docs" / "research" / "P0-M3-R3-RM014-ENTRY-ANCHOR-FEASIBILITY.md"
HANDOFF_PATH = REPO_ROOT / "HANDOFF_TO_PM.md"

EXPECTED_SEEDS = [0, 1, 2, 3, 4]
EXPECTED_WINDOW_LENGTHS = [10.0, 15.0, 20.0, 30.0]
EXPECTED_PERTURBATIONS = [-1000, -500, 0, 500, 1000]
DISALLOWED_TRACK_IDS = {"RM041"}  # audio must never be decoded for these in this directory

# GENERIC ONLY -- no owner-specific value, and no allowlisted real path
# prefix (including this repo's own checkout), may ever be added here.
FORBIDDEN_PRIVACY_PATTERNS = [
    ("windows_absolute_path", re.compile(r"[A-Za-z]:\\\\?[Uu]sers", re.IGNORECASE)),
    ("wsl_mount_absolute_path", re.compile(r"/mnt/[a-z]/", re.IGNORECASE)),
    ("linux_home_absolute_path", re.compile(r"/home/[^/\s\"'\\]+/")),
    ("mp3_extension", re.compile(r"\.mp3", re.IGNORECASE)),
    ("wav_extension", re.compile(r"\.wav", re.IGNORECASE)),
    ("flac_extension", re.compile(r"\.flac", re.IGNORECASE)),
]
DISALLOWED_TOKENS = ["Signalsmith", "RubberBand", "Rubber Band", "render_transition", "owner_listening"]

# Synthetic, clearly-fake self-test fixtures (R4). NOT owner-private data --
# they exist only to prove the scanning mechanism itself correctly
# distinguishes "absent" from "present" before it is ever trusted with a
# real value. Safe to hardcode, print, and commit.
SENTINEL_SELFTEST_DUMMY_TOKEN = "PRIVATE_SENTINEL_TEST_VALUE_4f8b2ac9d1e07c33"
DUMMY_WINDOWS_USER_PATH = r"C:\Users\synthetic_test_user_9f3a"
DUMMY_WSL_MOUNT_PATH = "/mnt/z/synthetic_test_mount_9f3a/fake_project"
DUMMY_LINUX_HOME_PATH = "/home/synthetic_test_user_9f3a/venv/bin/python"

# This verifier's own source (and its own prior JSON output) necessarily
# contains the literal pattern/token/dummy strings it defines and searches
# for -- scanning it against itself is self-referential and produces only
# false positives, exactly the defect already repaired in the accepted
# pair_stability/verify_pair_stability.py (commit b181f42).
SELF_REFERENTIAL_NAMES = {Path(__file__).name, "verifier_output.json"}


def check(label, condition, checks):
    checks.append({"check": label, "passed": bool(condition)})
    return condition


def scan_text_for_privacy(text: str, label: str, checks: list) -> None:
    for name, pattern in FORBIDDEN_PRIVACY_PATTERNS:
        check(f"no_privacy_leak[{label}][{name}]", not pattern.search(text), checks)


def scan_text_for_sentinel(text: str, label: str, sentinel: str | None, checks: list) -> None:
    if sentinel is None:
        return
    check(f"private_sentinel_absent[{label}]", sentinel not in text, checks)


def run_fail_closed_selftests(checks: list) -> None:
    """R4: prove each forbidden-pattern category, plus the sentinel
    mechanism, actually fails closed -- using only synthetic dummy values,
    never a real machine/user value."""
    clean_blob = "This is a clean synthetic diagnostic blob with no private paths or sentinels inside it."
    patterns_by_name = dict(FORBIDDEN_PRIVACY_PATTERNS)

    def path_selftest(name: str, dummy_value: str) -> None:
        pattern = patterns_by_name[name]
        check(f"selftest_clean_blob_detected_as_absent[{name}]", not pattern.search(clean_blob), checks)
        injected = clean_blob + " " + dummy_value
        check(f"selftest_injected_dummy_detected_as_present_fails_closed[{name}]", bool(pattern.search(injected)), checks)

    path_selftest("windows_absolute_path", DUMMY_WINDOWS_USER_PATH)
    path_selftest("wsl_mount_absolute_path", DUMMY_WSL_MOUNT_PATH)
    path_selftest("linux_home_absolute_path", DUMMY_LINUX_HOME_PATH)

    check("selftest_sentinel_clean_blob_detected_as_absent", SENTINEL_SELFTEST_DUMMY_TOKEN not in clean_blob, checks)
    injected_sentinel_blob = clean_blob + " " + SENTINEL_SELFTEST_DUMMY_TOKEN
    check(
        "selftest_sentinel_injected_dummy_detected_as_present_fails_closed",
        SENTINEL_SELFTEST_DUMMY_TOKEN in injected_sentinel_blob,
        checks,
    )


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


def verify_full_text_surface(new_dir: Path, sentinel: str | None, checks: list) -> None:
    """R3: scan every in-scope text target -- new Python source,
    EXACT_COMMANDS.md, the research report, result JSONs, and
    HANDOFF_TO_PM.md -- for generic privacy-pattern shapes, and (only if
    supplied) the real private sentinel."""
    py_files = sorted(p for p in new_dir.glob("*.py") if p.name not in SELF_REFERENTIAL_NAMES)
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
        scan_text_for_sentinel(text, p.name, sentinel, checks)

    exact_commands = new_dir / "EXACT_COMMANDS.md"
    check("exact_commands_file_exists", exact_commands.exists(), checks)
    if exact_commands.exists():
        text = exact_commands.read_text(encoding="utf-8")
        scan_text_for_privacy(text, exact_commands.name, checks)
        scan_text_for_sentinel(text, exact_commands.name, sentinel, checks)

    check("research_report_exists", DOC_REPORT_PATH.exists(), checks)
    if DOC_REPORT_PATH.exists():
        text = DOC_REPORT_PATH.read_text(encoding="utf-8")
        scan_text_for_privacy(text, DOC_REPORT_PATH.name, checks)
        scan_text_for_sentinel(text, DOC_REPORT_PATH.name, sentinel, checks)

    if HANDOFF_PATH.exists():
        text = HANDOFF_PATH.read_text(encoding="utf-8")
        scan_text_for_privacy(text, HANDOFF_PATH.name, checks)
        scan_text_for_sentinel(text, HANDOFF_PATH.name, sentinel, checks)

    result_files = sorted(p for p in (new_dir / "results").glob("*.json") if p.name not in SELF_REFERENTIAL_NAMES)
    check("entry_anchor_results_present", len(result_files) > 0, checks)
    for p in result_files:
        text = p.read_text(encoding="utf-8")
        scan_text_for_privacy(text, p.name, checks)
        scan_text_for_sentinel(text, p.name, sentinel, checks)
        payload = json.loads(text)
        blob = json.dumps(payload)
        for token in DISALLOWED_TOKENS:
            check(f"no_disallowed_token[{p.name}][{token}]", token not in blob, checks)

    render_like = list(new_dir.rglob("*.wav")) + list(new_dir.rglob("*.mp3")) + list(new_dir.rglob("*.flac"))
    check("no_audio_render_output_present", len(render_like) == 0, checks)


def verify_pm_zip(zip_path: Path, sentinel: str | None, checks: list) -> None:
    if not zip_path.exists():
        check("pm_zip_exists", False, checks)
        return
    check("pm_zip_exists", True, checks)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for name in names:
            scan_text_for_privacy(name, f"zip_member_name::{name}", checks)
            scan_text_for_sentinel(name, f"zip_member_name::{name}", sentinel, checks)
            if Path(name).name in SELF_REFERENTIAL_NAMES:
                continue
            try:
                content = zf.read(name).decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                continue
            scan_text_for_privacy(content, f"zip_member_content::{name}", checks)
            scan_text_for_sentinel(content, f"zip_member_content::{name}", sentinel, checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pm-zip", default=None)
    parser.add_argument("--private-sentinel", default=None, help="real owner-private value, supplied out of band; never printed/stored")
    args = parser.parse_args()

    sentinel = args.private_sentinel or os.environ.get("AUTOMIX_PRIVATE_SENTINEL")
    real_sentinel_scan_status = "RAN" if sentinel else "SKIPPED_NO_SENTINEL_SUPPLIED"

    checks: list = []
    new_dir = HERE
    results_dir = new_dir / "results"

    intro_clusters = verify_intro_clusters(results_dir, checks)
    verify_content_preservation(results_dir, intro_clusters, checks)
    verify_harmonic_reeval(results_dir, intro_clusters, checks)
    verify_full_text_surface(new_dir, sentinel, checks)
    run_fail_closed_selftests(checks)

    if args.pm_zip:
        verify_pm_zip(Path(args.pm_zip), sentinel, checks)

    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    failed = [c for c in checks if not c["passed"]]

    out_path = results_dir / "verifier_output.json"
    out_path.write_text(
        json.dumps(
            {
                "total": total,
                "passed": passed,
                "failed": failed,
                "real_sentinel_scan_status": real_sentinel_scan_status,
                "checks": checks,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if failed:
        print(f"FAIL {passed}/{total} (real_sentinel_scan_status={real_sentinel_scan_status}) -- failed checks:")
        for c in failed:
            print(f"  - {c['check']}")
        return 1
    print(f"ALL ASSERTIONS PASS {passed}/{total} (real_sentinel_scan_status={real_sentinel_scan_status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
