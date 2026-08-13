"""Machine verifier for the bounded Issue #7 analyzer-evidence recovery."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import pair_gate_audit as audit  # noqa: E402
import recover_analyzer_evidence as recovery  # noqa: E402


class Verifier:
    def __init__(self) -> None:
        self.assertions = 0
        self.failures: list[str] = []

    def check(self, condition: bool, label: str) -> None:
        self.assertions += 1
        if condition:
            print(f"PASS {self.assertions}: {label}")
        else:
            self.failures.append(label)
            print(f"FAIL {self.assertions}: {label}")


def tracked_text(repo: Path) -> dict[str, str]:
    names = subprocess.check_output(["git", "ls-files"], cwd=repo, text=True).splitlines()
    output = {}
    for name in names:
        path = repo / name
        try:
            output[name] = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--subset", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline", default="7ccb5c72461e4237d85b621946be7cc4443f0350")
    args = parser.parse_args()

    repo = ROOT.parents[2]
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    subset = json.loads(Path(args.subset).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    analysis = json.loads((Path(args.corpus_dir) / "corpus_analysis.local.json").read_text(encoding="utf-8"))
    id_map = json.loads((Path(args.corpus_dir) / "id_map.local.json").read_text(encoding="utf-8"))
    v = Verifier()

    # 1. Exact bounded subset derivation.
    independently_derived = recovery.derive_subset(trace)
    v.check(subset == independently_derived, "subset manifest exactly equals independent top-10 V1/V2 union derivation")
    v.check(subset["v1_pair_count"] == 10 and subset["v2_pair_count"] == 10, "exactly ten cached near misses from each category")
    v.check(set(evidence["tracks"]) == set(subset["opaque_track_ids"]), "no extra corpus track appears in recovered track evidence")

    # 2. Canonical R2 behavior remains the baseline and is reproducible.
    replay_by_pair = {
        (row["category"], row["outgoing_opaque_id"], row["incoming_opaque_id"]): row
        for row in evidence["near_miss_replay"]
    }
    canonical_match = True
    for category, key in (("V1", "v1_near_misses_top10_ranked_by_fewest_failed_gates"), ("V2", "v2_near_misses_top10_ranked_by_fewest_failed_gates")):
        for source in trace[key]:
            out_id, in_id = source["outgoing_opaque_id"], source["incoming_opaque_id"]
            _ci, _compat, _status, failed = audit.classify_pair(analysis[out_id], analysis[in_id])
            row = replay_by_pair[(category, out_id, in_id)]
            canonical_match &= failed == row["original_failed_gates_recomputed"]
    v.check(canonical_match, "canonical cached R2 failed-gate results reproduce exactly")
    v.check(evidence["confidence_ownership"]["canonical_r2_behavior"] == "UNCHANGED", "artifact labels canonical R2 behavior unchanged")

    # 3. Confidence-ledger diagnostics cannot silently become production.
    v.check(all(not row["confidence_ledger_diagnostic"]["aggregate_analysis_confidence_counted_as_independent"] for row in evidence["near_miss_replay"]), "diagnostic never double-counts aggregate analysis_confidence")
    v.check(all(row["honest_render_candidate_under_existing_r2"] == (row["current_strict_r2_verdict_after_recovery"] == "FULL_DJ_ELIGIBLE") for row in evidence["near_miss_replay"]), "honest candidates derive only from strict existing R2 verdict")
    v.check(evidence["confidence_ownership"]["production_gate_changes"] is False, "diagnostic declares no production gate changes")

    # 4. Beat ownership and conservative UNKNOWN/CONFLICT semantics.
    v.check(evidence["analyzer_provenance"]["beat_ownership"].startswith("UNCHANGED_"), "BeatNet/beat ownership remains unchanged")
    allowed_resolutions = {"downbeat", "harmonic"}
    v.check(all(set(row["unknown_gates_resolved_by_new_evidence"]).issubset(allowed_resolutions) for row in evidence["near_miss_replay"]), "UNKNOWN becomes PASS only in lanes with explicit new oracle evidence")
    conflicting_ids = {
        opaque_id for opaque_id, row in evidence["tracks"].items()
        if row.get("downbeat", {}).get("status") == "RESOLVED_CONFLICT"
    }
    conflict_safe = True
    for row in evidence["near_miss_replay"]:
        if {row["outgoing_opaque_id"], row["incoming_opaque_id"]} & conflicting_ids:
            conflict_safe &= row["current_strict_r2_verdict_after_recovery"] != "FULL_DJ_ELIGIBLE"
    v.check(conflict_safe, "conflicting downbeat evidence is never cherry-picked into strict eligibility")

    # 5. Any recovered candidate must pass the real evaluator, not diagnostic prose.
    v.check(all(not row["honest_render_candidate_under_existing_r2"] or not row["current_strict_r2_failed_gates_after_recovery"] for row in evidence["near_miss_replay"]), "every recovered candidate has zero strict R2 failed gates")

    # 6. Privacy: scan tracked text and committed-safe artifacts for the
    # locally supplied sentinel and every private basename. Never print them.
    sentinel = os.environ.get("AUTOMIX_R3_PRIVATE_ROOT_SENTINEL")
    v.check(bool(sentinel), "private-root sentinel supplied via local environment")
    texts = tracked_text(repo)
    safe_artifacts = [Path(args.subset), Path(args.evidence)]
    safe_blob = "\n".join(texts.values()) + "\n" + "\n".join(path.read_text(encoding="utf-8") for path in safe_artifacts)
    if sentinel:
        v.check(sentinel.lower() not in safe_blob.lower(), "private-root sentinel absent from tracked and committed-safe evidence")
    else:
        v.check(False, "private-root sentinel absence could not be tested")
    basenames = [Path(value).name for value in id_map.values()]
    v.check(all(name not in safe_blob for name in basenames), "all private source basenames absent from tracked and committed-safe evidence")
    serialized = json.dumps(evidence).lower()
    v.check("private_path" not in serialized and "source_basename" not in serialized and "owner_audio_hash" not in serialized, "committed-safe schema contains no private path/basename/audio-hash fields")

    # 7. No render/P1 work in this bounded diff.
    changed = subprocess.check_output(["git", "diff", "--name-only", args.baseline], cwd=repo, text=True).splitlines()
    forbidden_suffixes = (".wav", ".flac", ".mp3", ".m4a")
    v.check(not any(name.lower().endswith(forbidden_suffixes) for name in changed), "bounded diff contains no audio files")
    v.check(not any("owner-listening" in name.lower() or "rendered" in name.lower() or name.lower().startswith("p1") for name in changed), "bounded diff contains no owner-pack, render-output, or P1 paths")
    v.check(set(evidence["explicit_non_actions"]) >= {"NO_RENDERING", "NO_OWNER_LISTENING_PACK", "NO_P1_WORK"}, "artifact records render/listening/P1 non-actions")

    report = {
        "result": "PASS" if not v.failures else "FAIL",
        "assertions": v.assertions,
        "failures": v.failures,
        "baseline": args.baseline,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"VERIFIER_RESULT={report['result']} ASSERTIONS={v.assertions} FAILURES={len(v.failures)}")
    return 0 if not v.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
