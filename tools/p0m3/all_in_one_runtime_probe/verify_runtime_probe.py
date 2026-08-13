"""Verify the P0-M3-R3 All-In-One runtime-probe evidence and scope."""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RESULT_ENUM = {
    "ALL_IN_ONE_RUNTIME_RECOVERED_SYNTHETIC_ONLY",
    "ALL_IN_ONE_RUNTIME_RECOVERED_BOUNDED_REAL",
    "ALL_IN_ONE_BLOCKED_OBSOLETE_RUNTIME",
    "BLOCKED_ENVIRONMENT",
    "FAIL",
}
EXPECTED_START = "2d68c86ec3e47e53a92448bf16bf8f6255cbf8a3"
EXPECTED_CANONICAL = "18e78903c0365147a2c5d4e5e57ebf88cb7d800e"
EXPECTED_PR37 = "5c2b2ce571c04054a0b54ceba365c0b8c1188099"
ALLOWED_PREFIXES = (
    "docs/research/P0-M3-R3-ALL-IN-ONE-RUNTIME-PROBE.md",
    "tools/p0m3/all_in_one_runtime_probe/",
)


class Verifier:
    def __init__(self) -> None:
        self.assertions = 0
        self.failures: list[str] = []

    def check(self, condition: bool, label: str) -> None:
        self.assertions += 1
        print(f"{'PASS' if condition else 'FAIL'} {self.assertions}: {label}")
        if not condition:
            self.failures.append(label)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def changed_files() -> list[str]:
    names = set(git("diff", "--name-only", EXPECTED_START).splitlines())
    for line in git("status", "--porcelain=v1").splitlines():
        if line.startswith("?? ") and line[3:].startswith(ALLOWED_PREFIXES):
            names.add(line[3:])
    return sorted(name for name in names if name)


def python_definitions(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out")
    parser.add_argument("--require-origin-match", action="store_true")
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    paths = {row["path_id"]: row for row in evidence["paths"]}
    p1 = paths["P1_CANONICAL_LEGACY"]
    p2 = paths["P2_PR37_CLAIMED_MATRIX"]
    scope = evidence["scope_attestation"]
    v = Verifier()

    # 1. Baseline branch/HEAD and binding task.
    v.check(evidence["starting_head"] == EXPECTED_START, "accepted starting HEAD recorded exactly")
    v.check(evidence["branch"] == "research/p0-feasibility", "target branch recorded exactly")
    v.check(evidence["binding_issue_comment_id"] == 5277857804, "latest binding Issue #7 comment recorded")
    v.check(git("branch", "--show-current") == "research/p0-feasibility", "verifier runs on target branch")

    # 2. Exact source and environment pins, with distinct isolation.
    v.check(p1["source_commit"] == EXPECTED_CANONICAL, "canonical All-In-One pin exact")
    v.check(p2["source_commit"] == EXPECTED_PR37, "PR #37 head pin exact")
    v.check(p1["natten_source_commit"] == "3b54c76185904f3cb59a49fff7bc044e4513d106", "official NATTEN v0.14.6 source commit exact")
    v.check(p1["natten_version"] == "0.14.6+torch200cu118", "canonical NATTEN build exact")
    v.check(p2["natten_version"] == "0.21.0+torch270cu128", "PR #37 NATTEN build exact")
    v.check(p1["environment_id"] != p2["environment_id"], "P1 and P2 environment IDs are distinct")
    v.check(p1["python_version"] != p2["python_version"], "P1 and P2 independently pin Python versions")

    # 3. Canonical unmodified import/model/checkpoint integrity.
    v.check(p1["source_clean"] is True, "canonical source checkout was unmodified")
    v.check(p1["import_result"] == "PASS" and p1["model_construction_result"] == "PASS", "canonical import and model construction pass")
    v.check(p1["checkpoint_load_result"] == "PASS" and p1["strict_load"] is True, "real checkpoint strict load passes")
    v.check(not p1["missing_keys"] and not p1["unexpected_keys"], "no missing/unexpected-key workaround accepted")
    v.check(not p1["shape_mismatches"] and p1["state_dict_key_sets_equal"], "no shape coercion or key-set modification accepted")
    v.check(len(p1["checkpoint_sha256"]) == 64 and p1["checkpoint_bytes"] > 0, "checkpoint integrity digest and byte size recorded")

    # 4. Ladder gating and deterministic synthetic behavior.
    ladder = p1["ladder"]
    v.check(ladder.index("REAL_CHECKPOINT_STRICT_LOAD_PASS") < ladder.index("SYNTHETIC_INFERENCE_PASS"), "synthetic smoke occurs only after model-load pass")
    v.check(p1["synthetic_inference_result"] == "PASS", "canonical synthetic smoke passes")
    v.check(p1["synthetic_nan_count"] == 0 and p1["synthetic_inf_count"] == 0, "synthetic smoke has no NaN/Inf")
    v.check(p1["deterministic_repeat_exact"] is True and p1["deterministic_repeat_max_abs_diff"] == 0.0, "synthetic repeat is bit-exact")

    # 5. PR claim is tested independently, not inferred.
    expected_pr_symbols = {name: False for name in ("na1d_qk", "na1d_av", "na2d_qk", "na2d_av")}
    v.check(all(p2["observed_natten_symbols"][name] == value for name, value in expected_pr_symbols.items()), "all four PR-expected public symbols recorded absent")
    v.check(p2["import_result"] == "FAIL_MISSING_EXPECTED_NATTEN_SYMBOLS", "unmodified PR import failure recorded")
    v.check(p2["model_construction_result"].startswith("NOT_REACHED"), "PR model construction correctly not reached")
    v.check(p2["checkpoint_load_result"].startswith("NOT_REACHED"), "PR checkpoint load correctly not reached")

    # 6. No modern attention implementation or semantic adapter was added.
    probe_python = list(HERE.glob("*.py"))
    definitions = set().union(*(python_definitions(path) for path in probe_python))
    forbidden_defs = {"na1d", "na2d", "neighborhood_attention_generic", "na1d_qk", "na1d_av", "na2d_qk", "na2d_av"}
    v.check(not definitions.intersection(forbidden_defs), "no custom modern/split attention function is implemented")
    v.check(evidence["optional_v0_15_1"]["attempted"] is False, "optional v0.15.1 adapter correctly not attempted")

    # 7. Privacy and bounded-use gates.
    v.check(scope["private_track_count"] == 0, "private smoke count is zero")
    v.check(scope["private_track_count"] <= 3, "private subset usage cannot exceed three")
    v.check(scope["private_track_ids"] == [], "no opaque or private track was used")
    v.check(scope["private_smoke_gate"] == "NOT_REACHED_BY_CHOICE_AFTER_SYNTHETIC_PASS", "private smoke is explicitly skipped after synthetic pass")
    serialized = json.dumps(evidence).lower()
    v.check(all(token not in serialized for token in ("private_path", "source_basename", "owner_audio_hash", "track_title", "artist")), "machine evidence schema contains no private leakage fields")

    # 8. Diff is restricted to probe/report/validation and contains no prohibited work.
    changed = changed_files()
    v.check(bool(changed) and all(name.startswith(ALLOWED_PREFIXES) for name in changed), "diff is restricted to authorized report/probe paths")
    v.check(not any(Path(name).suffix.lower() in {".wav", ".flac", ".mp3", ".m4a", ".zip", ".pth", ".whl"} for name in changed), "diff contains no audio, ZIP, checkpoint, or wheel")
    v.check(scope["owner_render_count"] == 0 and scope["owner_listening_pack_created"] is False, "no owner rendering or listening pack")
    v.check(scope["signalsmith_runs"] == 0 and scope["rubber_band_runs"] == 0, "no Signalsmith or Rubber Band run")
    v.check(scope["p1_production_work"] is False, "no P1 production work")
    v.check(evidence["result"] in RESULT_ENUM and evidence["result"] == "ALL_IN_ONE_RUNTIME_RECOVERED_SYNTHETIC_ONLY", "exact accepted result enum used")
    v.check(evidence["accepted_prior_result_unchanged"] == "ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY", "accepted analyzer-evidence verdict remains unchanged")

    if args.require_origin_match:
        local = git("rev-parse", "HEAD")
        remote = git("rev-parse", "origin/research/p0-feasibility")
        v.check(local == remote, "local HEAD equals pushed origin target")

    report = {
        "result": "PASS" if not v.failures else "FAIL",
        "assertions": v.assertions,
        "failures": v.failures,
        "starting_head": EXPECTED_START,
        "origin_match_required": args.require_origin_match,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"VERIFIER_RESULT={report['result']} ASSERTIONS={v.assertions} FAILURES={len(v.failures)}")
    return 0 if not v.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
