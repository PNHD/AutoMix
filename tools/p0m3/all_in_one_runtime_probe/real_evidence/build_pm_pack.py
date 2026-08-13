"""Build the local-only, non-self-referential PM review archive once."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

REPO_FILES = [
    "docs/research/P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE.md",
    "docs/research/P0-M3-R3-ALL-IN-ONE-RUNTIME-PROBE.md",
    "docs/research/P0-M3-R3-ANALYZER-EVIDENCE-RECOVERY.md",
    "docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md",
    "tools/p0m3/all_in_one_runtime_probe/results/runtime_probe_sanitized.json",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/derive_frontier.py",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/run_real_pipeline.py",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/deterministic_site/sitecustomize.py",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/compile_evidence.py",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/verify_real_evidence.py",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/build_pm_pack.py",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/EXACT_COMMANDS.md",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/frontier_derivation_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_preflight_environment_failure_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_checkpoint_cache_environment_failure_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_checkpoint_provenance_harness_failure_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_unseeded_repeat_failure_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_smoke_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/expanded_runs_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/all_in_one_real_evidence_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/three_pair_replay_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/validation_precommit.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--post-push-validation", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        raise FileExistsError("PM_REVIEW_ZIP_ALREADY_EXISTS_BUILD_ONCE_REQUIRED")
    files = [(root / relative, relative) for relative in REPO_FILES]
    files.extend([
        (Path(args.handoff).resolve(), "HANDOFF_TO_PM.md"),
        (Path(args.post_push_validation).resolve(), "post_push_validation.json"),
    ])
    missing = [str(path) for path, _ in files if not path.is_file()]
    if missing:
        raise FileNotFoundError("PM_PACK_INPUT_MISSING")
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, arcname in files:
            archive.write(path, arcname)
    print(f"ENTRIES={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
