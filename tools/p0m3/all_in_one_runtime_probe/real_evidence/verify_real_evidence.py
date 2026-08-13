"""Verify bounded All-In-One real evidence, privacy, and unchanged R2 ownership."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

EXPECTED_START = "64a78894166b873987de57437b2d74d4d057e97a"
EXPECTED_SOURCE = "18e78903c0365147a2c5d4e5e57ebf88cb7d800e"
EXPECTED_NATTEN_SOURCE = "3b54c76185904f3cb59a49fff7bc044e4513d106"
EXPECTED_CHECKPOINT_REVISION = "379e5fd010b3fdd0ee8381ff8cbcfa51d70b5c19"
EXPECTED_CHECKPOINT_HASH = "0db596dfb0995f41d62f6267d76a9d54c046f1649bd35e1dbeca0c5f9a7b8acd"
EXPECTED_TRACKS = {"RM010", "RM014", "RM041", "RM081"}
EXPECTED_PAIRS = {
    ("V1", "RM014", "RM010"),
    ("V2", "RM014", "RM081"),
    ("V2", "RM041", "RM014"),
}


class Checks:
    def __init__(self):
        self.rows: list[dict] = []

    def check(self, condition: bool, name: str) -> None:
        self.rows.append({"name": name, "status": "PASS" if condition else "FAIL"})
        if not condition:
            raise AssertionError(name)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def private_needles(mapping_path: Path) -> list[str]:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    values = []
    for value in mapping.values():
        if not isinstance(value, str):
            continue
        normalized = value.replace("\\", "/")
        values.extend([value, normalized, Path(normalized).name])
    return sorted({value for value in values if len(value) >= 4})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontier", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--replay", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--scan-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--require-origin-match", action="store_true")
    args = parser.parse_args()

    checks = Checks()
    frontier = json.loads(Path(args.frontier).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    replay = json.loads(Path(args.replay).read_text(encoding="utf-8"))

    checks.check(frontier["starting_head"] == EXPECTED_START, "1 starting HEAD exact")
    derived_pairs = {
        (row["category"], row["outgoing_opaque_id"], row["incoming_opaque_id"])
        for row in frontier["derived_pairs"]
    }
    checks.check(derived_pairs == EXPECTED_PAIRS and frontier["derived_pair_count"] == 3,
                 "2 frontier independently derives exactly three pairs")
    checks.check(set(frontier["derived_track_ids"]) == EXPECTED_TRACKS and frontier["derived_track_count"] == 4,
                 "3 frontier independently derives exactly four tracks")
    checks.check(set(evidence["tracks"]) == EXPECTED_TRACKS and evidence["scope_attestation"]["tracks_outside_frontier"] == 0,
                 "4 no track outside frontier analyzed")
    expected_order = [(1, "RM014"), (2, "RM014"), (3, "RM010"), (4, "RM041"), (5, "RM081")]
    observed_order = [(row["order"], row["opaque_id"]) for row in evidence["execution_order"]]
    checks.check(observed_order == expected_order, "5 RM014 executes twice before any other private track")
    api = evidence["public_audio_api"]
    checks.check(api["source_symbol"] == "src/allin1/analyze.py::analyze"
                 and api["real_audio_loading"] and api["demucs_preprocessing"]
                 and api["spectrogram_preprocessing"] and api["model_inference"]
                 and not api["direct_feature_tensor_test_path"],
                 "6 real public audio path used instead of direct feature tensor")
    runtime = evidence["runtime"]
    checkpoint = evidence["checkpoint"]
    checks.check(runtime["all_in_one_source_commit"] == EXPECTED_SOURCE
                 and runtime["python_version"] == "3.10.18"
                 and runtime["torch_version"] == "2.0.0+cu118"
                 and runtime["torch_cuda_build"] == "11.8"
                 and runtime["natten_version"] == "0.14.6"
                 and runtime["natten_source_commit"] == EXPECTED_NATTEN_SOURCE
                 and checkpoint["loader_resolved_revision"] == EXPECTED_CHECKPOINT_REVISION
                 and checkpoint["sha256"] == EXPECTED_CHECKPOINT_HASH,
                 "7 canonical source runtime and checkpoint lineage unchanged")
    checks.check(not evidence["all_in_one_confidence_calibrated"]
                 and evidence["evidence_class"] == "BENCHMARK_MODEL_OUTPUT_UNCALIBRATED"
                 and all(not row["calibrated_confidence_claimed"] for row in evidence["tracks"].values()),
                 "8 All-In-One output not promoted to calibrated HIGH")
    checks.check(evidence["beat_ownership"] == "BEATNET_UNCHANGED_ALL_IN_ONE_BEATS_DIAGNOSTIC_ONLY",
                 "9 BeatNet beat ownership unchanged")
    labels_valid = True
    semantics_valid = True
    for track in evidence["tracks"].values():
        labels = {segment["label"] for segment in track["segments"]}
        for boundary in track["relevant_boundaries"]:
            labels_valid &= boundary["functional_label"] in labels and boundary["functional_label_from_actual_output"]
            semantics_valid &= not boundary["phrase_claimed"] and not boundary["outro_fabricated"]
    checks.check(labels_valid, "10 functional labels originate in actual All-In-One output")
    checks.check(semantics_valid and all(not row["phrase_claimed"] for row in evidence["tracks"].values()),
                 "11 no phrase or outro fabrication")
    invariant_fields = (
        replay["harmonic_status_unchanged_for_all"],
        replay["genre_style_status_unchanged_for_all"],
        replay["texture_status_unchanged_for_all"],
        replay["canonical_analysis_confidence_unchanged_for_all"],
    )
    checks.check(all(invariant_fields), "12 harmonic genre texture and aggregate evidence unchanged")
    checks.check(evidence["strict_r2_behavior"] == "UNCHANGED" and replay["strict_r2_gates_unchanged"],
                 "13 existing R2 strict evaluator and gates unchanged")
    checks.check(
        evidence["render_candidate_count"]
        == replay["render_candidate_count"]
        == sum(1 for row in replay["pairs"] if row["strict_existing_r2_verdict"] == "FULL_DJ_ELIGIBLE"),
        "13b render-candidate enum derives from literal unchanged strict R2 verdicts",
    )
    replay_pairs = {(row["category"], row["outgoing_opaque_id"], row["incoming_opaque_id"]) for row in replay["pairs"]}
    checks.check(replay["pair_count"] == 3 and replay_pairs == EXPECTED_PAIRS,
                 "14 only three frontier pairs replayed")
    scope = evidence["scope_attestation"]
    checks.check(scope["render_count"] == 0 and scope["signalsmith_runs"] == 0
                 and scope["rubber_band_runs"] == 0 and not scope["owner_listening_pack_created"],
                 "15 no render listening Signalsmith or Rubber Band")

    scan_files = [path for path in Path(args.scan_root).rglob("*") if path.is_file()]
    scan_files.append(Path(args.report))
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in scan_files)
    lower = combined.lower()
    # Assemble leak-key sentinels so the tracked verifier cannot invalidate its
    # own full-tree scan by embedding the exact forbidden strings.
    forbidden_keys = [
        '"' + left + right + '"'
        for left, right in (
            ("private", "_path"), ("source", "_path"), ("source", "_filename"),
            ("source", "_basename"), ("art", "ist"), ("ti", "tle"),
            ("al", "bum"), ("raw", "_tags"), ("audio", "_hash"),
        )
    ]
    no_private_values = not any(needle in combined for needle in private_needles(Path(args.mapping)))
    checks.check(no_private_values and not any(token in lower for token in forbidden_keys),
                 "16 no private mapping values filenames paths tags or audio hashes leak")
    checks.check(not scope["p1_production_work"], "17 no P1 production work")

    origin_checked = False
    if args.require_origin_match:
        head = git("rev-parse", "HEAD")
        parent = git("rev-parse", "HEAD^")
        remote = git("ls-remote", "origin", "refs/heads/research/p0-feasibility").split()[0]
        checks.check(parent == EXPECTED_START and head == remote,
                     "18 remote pushed HEAD exact after single bounded commit")
        changed = set(git("diff", "--name-only", f"{EXPECTED_START}..{head}").splitlines())
        allowed = all(
            name == "docs/research/P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE.md"
            or name.startswith("tools/p0m3/all_in_one_runtime_probe/real_evidence/")
            for name in changed
        )
        checks.check(allowed, "19 committed scope limited to report and bounded harness evidence")
        origin_checked = True

    payload = {
        "schema_version": 1,
        "result": "PASS",
        "assertion_count": len(checks.rows),
        "assertions": checks.rows,
        "origin_match_checked": origin_checked,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT=PASS ASSERTIONS={len(checks.rows)} ORIGIN_MATCH_CHECKED={origin_checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
