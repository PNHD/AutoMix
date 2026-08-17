"""Build the local-only, non-self-referential PM review archive for the
RM014 entry-anchor feasibility pass. Run once; does not overwrite."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

NEW_WORK_FILES = [
    "docs/research/P0-M3-R3-RM014-ENTRY-ANCHOR-FEASIBILITY.md",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/derive_intro_clusters.py",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/content_preservation_analysis.py",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/harmonic_reeval_candidates.py",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/verify_entry_anchor_feasibility.py",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/build_pm_pack.py",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/EXACT_COMMANDS.md",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/intro_clusters.json",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/content_preservation.json",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/harmonic_reeval.json",
    "tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/verifier_output.json",
]

# Required accepted prior provenance this pass reused (not rerun): the 10
# raw All-In-One run files, the cross-seed metrics, the accepted 0ms
# harmonic sensitivity cells, the accepted madmom benchmark grid, and the
# accepted boundary source -- included so a reviewer can verify no
# numeric input was altered without re-running anything.
PRIOR_PROVENANCE_FILES = [
    "docs/research/P0-M3-R3-RM041-RM014-EVIDENCE-STABILITY.md",
    "tools/p0m3/all_in_one_runtime_probe/pair_stability/results/cross_seed_metrics.json",
    "tools/p0m3/all_in_one_runtime_probe/pair_stability/results/harmonic_sensitivity.json",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/real_evidence/results/three_pair_replay_sanitized.json",
] + [
    f"tools/p0m3/all_in_one_runtime_probe/pair_stability/results/raw_runs/RM014-seed{s}.json"
    for s in range(5)
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        raise FileExistsError("PM_REVIEW_ZIP_ALREADY_EXISTS_BUILD_ONCE_REQUIRED")

    files = [(root / relative, relative) for relative in NEW_WORK_FILES + PRIOR_PROVENANCE_FILES]
    files.append((Path(args.handoff).resolve(), "HANDOFF_TO_PM.md"))

    missing = [str(path) for path, _ in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"PM_PACK_INPUT_MISSING: {missing}")

    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, arcname in files:
            archive.write(path, arcname)
    print(f"ENTRIES={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
