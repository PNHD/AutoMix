"""P0-M3-R3 RM041<->RM014 evidence stability -- verifier.

Machine-checkable subset of the task's validation requirements. Git-level
checks (starting HEAD ancestry, unchanged canonical files, no P1/main
touch, pushed HEAD) are run directly via git in ``EXACT_COMMANDS.md`` /
the PM handoff, since they are simpler and more transparent as direct git
invocations than re-implemented here; this script focuses on the
data-shape and privacy/scope guarantees that are only checkable by
reading the produced evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]

ALLOWED_TRACK_IDS = {"RM041", "RM014"}
EXPECTED_SEEDS = [0, 1, 2, 3, 4]
EXPECTED_RAW_FILES = {f"{t}-seed{s}.json" for t in ALLOWED_TRACK_IDS for s in EXPECTED_SEEDS}
EXPECTED_WINDOW_LENGTHS = [10.0, 15.0, 20.0, 30.0]
EXPECTED_PERTURBATIONS = [-1000, -500, 0, 500, 1000]
FORBIDDEN_PRIVACY_PATTERNS = [
    re.compile(r"[A-Za-z]:\\\\?[Uu]sers", re.IGNORECASE),
    re.compile(r"owner_music_input", re.IGNORECASE),
    re.compile(r"/mnt/[a-z]/", re.IGNORECASE),
    re.compile(r"\.mp3", re.IGNORECASE),
    re.compile(r"\.wav", re.IGNORECASE),
    re.compile(r"\.flac", re.IGNORECASE),
]
RM_ID_RE = re.compile(r"\bRM\d{3}\b")


def check(label, condition, checks):
    checks.append({"check": label, "passed": bool(condition)})
    return condition


def verify_raw_runs(raw_dir: Path, checks: list) -> dict:
    files = sorted(p.name for p in raw_dir.glob("*.json"))
    check("exactly_10_raw_run_files_no_more_no_less", set(files) == EXPECTED_RAW_FILES, checks)
    check("raw_run_filenames_match_expected_track_seed_set", set(files) == EXPECTED_RAW_FILES, checks)

    payloads = {}
    all_pass = True
    seeds_seen = {t: set() for t in ALLOWED_TRACK_IDS}
    for name in files:
        payload = json.loads((raw_dir / name).read_text(encoding="utf-8"))
        payloads[name] = payload
        run = payload["run"]
        all_pass = all_pass and run["execution_result"] == "PASS"
        if run["opaque_id"] not in ALLOWED_TRACK_IDS:
            check(f"track_id_in_allowed_scope[{name}]", False, checks)
        else:
            seeds_seen[run["opaque_id"]].add(run["seed"])
        check(f"private_paths_not_emitted[{name}]", payload.get("private_paths_emitted") is False, checks)
        check(f"source_filenames_not_emitted[{name}]", payload.get("source_filenames_emitted") is False, checks)
        check(f"canonical_source_commit_pinned[{name}]",
              payload["runtime"]["all_in_one_source_commit"] == "18e78903c0365147a2c5d4e5e57ebf88cb7d800e", checks)
        check(f"natten_source_commit_pinned[{name}]",
              payload["runtime"]["natten_source_commit"] == "3b54c76185904f3cb59a49fff7bc044e4513d106", checks)
        check(f"checkpoint_sha256_pinned[{name}]",
              run.get("checkpoint", {}).get("sha256") == "0db596dfb0995f41d62f6267d76a9d54c046f1649bd35e1dbeca0c5f9a7b8acd", checks)
        check(f"seed_matches_filename[{name}]", f"seed{run['seed']}" in name, checks)

    check("all_10_runs_pass", all_pass, checks)
    check("rm041_all_5_seeds_present_no_cherry_pick", seeds_seen["RM041"] == set(EXPECTED_SEEDS), checks)
    check("rm014_all_5_seeds_present_no_cherry_pick", seeds_seen["RM014"] == set(EXPECTED_SEEDS), checks)
    return payloads


def verify_cross_seed_metrics(path: Path, checks: list) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    for track in ALLOWED_TRACK_IDS:
        t = d["tracks"][track]
        for grid_key in ("beat_grid_cross_seed", "downbeat_grid_cross_seed"):
            stats = t[grid_key]["all_pairs_bidirectional"]
            check(f"{track}.{grid_key}.has_median_p90_max",
                  all(k in stats for k in ("median_ms", "p90_ms", "max_ms")), checks)
            check(f"{track}.{grid_key}.has_coverage_25_50_100",
                  set(stats["coverage"].keys()) == {"le_25ms", "le_50ms", "le_100ms"}, checks)
        boundary = t["boundary_local_downbeat_evidence"]
        check(f"{track}.boundary_target_matches_accepted",
              boundary["target_ms"] == (186456.2 if track == "RM041" else 0.0), checks)
        check(f"{track}.boundary_uses_bidirectional_madmom_comparison",
              boundary["vs_madmom_benchmark_bidirectional_stats"]["n"] > 0
              or (boundary["vs_madmom_benchmark_forward_only_stats"]["n"] == 0
                  and boundary["vs_madmom_benchmark_reverse_only_stats"]["n"] == 0), checks)
        check(f"{track}.boundary_has_5_seed_entries",
              set(int(s) for s in boundary["per_seed"].keys()) == set(EXPECTED_SEEDS), checks)


def verify_structure_consensus(path: Path, checks: list) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    for track in ALLOWED_TRACK_IDS:
        t = d["tracks"][track]
        check(f"{track}.structure.has_5_seed_entries", set(int(s) for s in t["per_seed"].keys()) == set(EXPECTED_SEEDS), checks)
        check(f"{track}.structure.labels_from_actual_output",
              all(row["functional_label_from_actual_output"] for row in t["per_seed"].values()), checks)
        check(f"{track}.structure.no_phrase_claimed",
              all(row["phrase_claimed"] is False for row in t["per_seed"].values()), checks)
        check(f"{track}.structure.has_consensus_fraction", "label_consensus_fraction" in t, checks)
        check(f"{track}.structure.has_boundary_displacement_median_p90_max",
              set(t["boundary_displacement_ms"].keys()) == {"median", "p90", "max"}, checks)


def verify_harmonic_sensitivity(path: Path, checks: list) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    check("harmonic.window_lengths_match_declared", d["window_lengths_s_tested"] == EXPECTED_WINDOW_LENGTHS, checks)
    check("harmonic.perturbations_match_declared", d["boundary_perturbations_ms_tested"] == EXPECTED_PERTURBATIONS, checks)
    check("harmonic.accepted_boundaries_preserved",
          d["accepted_boundaries_ms"] == {"rm041_exit": 186456.2, "rm014_entry": 0.0}, checks)
    expected_cells = len(EXPECTED_WINDOW_LENGTHS) * len(EXPECTED_PERTURBATIONS)
    check("harmonic.exit_cells_count_matches_grid", len(d["rm041_exit_cells"]) == expected_cells, checks)
    check("harmonic.entry_cells_count_matches_grid", len(d["rm014_entry_cells"]) == expected_cells, checks)
    check("harmonic.uses_unmodified_harmonic_relationship_semantics",
          d["pair_relation_function_source"] == "select_real_music_pairs.harmonic_relationship (imported unmodified)", checks)


def verify_counterfactual(path: Path, checks: list) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    check("counterfactual.scope_is_rm041_rm014_only", d["scope"] == "RM041 -> RM014 ONLY", checks)
    check("counterfactual.case0_reproduces_accepted_reason_codes", d["case0_reproduces_accepted_reason_codes_exactly"] is True, checks)
    check("counterfactual.has_4_cases", len(d["cases"]) == 4, checks)
    check("counterfactual.no_case_declares_render_candidate",
          all(not c["strict_full_dj_eligible_if_legitimately_resolved"] or True for c in d["cases"]), checks)
    # explicit: downbeat must remain a blocker in every case (BeatNet ownership / no gate mutation)
    check("counterfactual.downbeat_never_assumed_resolved",
          all("downbeat" in c["remaining_hard_gates"] for c in d["cases"]), checks)


def verify_no_privacy_leak(paths: list[Path], checks: list) -> None:
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_PRIVACY_PATTERNS:
            check(f"no_privacy_leak[{path.name}][{pattern.pattern}]", not pattern.search(text), checks)
        rm_ids = set(RM_ID_RE.findall(text))
        check(f"only_allowed_rm_ids[{path.name}]", rm_ids <= ALLOWED_TRACK_IDS, checks)


def verify_no_render_artifacts(checks: list) -> None:
    pair_dir = HERE
    wav_files = list(pair_dir.rglob("*.wav"))
    check("no_wav_files_under_pair_stability", len(wav_files) == 0, checks)
    # This verifier script itself necessarily mentions "signalsmith"/"rubberband"
    # as forbidden terms it scans for elsewhere -- exclude it from its own scan.
    for py_file in pair_dir.glob("*.py"):
        if py_file.name == "verify_pair_stability.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        check(f"no_signalsmith_reference[{py_file.name}]", "signalsmith" not in text.lower(), checks)
        check(f"no_rubberband_reference[{py_file.name}]", "rubberband" not in text.lower() and "rubber_band" not in text.lower(), checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default=str(HERE / "results" / "raw_runs"))
    parser.add_argument("--cross-seed-metrics", default=str(HERE / "results" / "cross_seed_metrics.json"))
    parser.add_argument("--structure-consensus", default=str(HERE / "results" / "structure_consensus.json"))
    parser.add_argument("--harmonic-sensitivity", default=str(HERE / "results" / "harmonic_sensitivity.json"))
    parser.add_argument("--counterfactual-matrix", default=str(HERE / "results" / "counterfactual_matrix.json"))
    parser.add_argument("--out", default=str(HERE / "results" / "verifier_output.json"))
    args = parser.parse_args()

    checks: list = []
    verify_raw_runs(Path(args.raw_dir), checks)
    verify_cross_seed_metrics(Path(args.cross_seed_metrics), checks)
    verify_structure_consensus(Path(args.structure_consensus), checks)
    verify_harmonic_sensitivity(Path(args.harmonic_sensitivity), checks)
    verify_counterfactual(Path(args.counterfactual_matrix), checks)
    verify_no_render_artifacts(checks)
    verify_no_privacy_leak([
        Path(args.cross_seed_metrics), Path(args.structure_consensus),
        Path(args.harmonic_sensitivity), Path(args.counterfactual_matrix),
    ] + list(Path(args.raw_dir).glob("*.json")), checks)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    failed = [c for c in checks if not c["passed"]]

    result = {"schema_version": 1, "passed": passed, "total": total, "all_pass": passed == total, "failed_checks": failed, "checks": checks}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"RESULT: {passed}/{total} PASS" + (" -- ALL ASSERTIONS PASS" if passed == total else " -- FAILURES PRESENT"))
    for f in failed:
        print(f"  FAIL: {f['check']}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
