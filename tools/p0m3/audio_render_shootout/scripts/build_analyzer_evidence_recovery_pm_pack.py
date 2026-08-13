"""Build the local-only non-self-referential Issue #7 PM review ZIP."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]

PACK_FILES = [
    "AGENTS.md",
    ".agents/skills/automix-task-contract/SKILL.md",
    ".agents/skills/automix-forensic-research/SKILL.md",
    ".agents/skills/automix-code-review/SKILL.md",
    "docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md",
    "docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md",
    "docs/research/P0-M3-R3-ANALYZER-EVIDENCE-RECOVERY.md",
    "tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py",
    "tools/p0m3/audio_render_shootout/scripts/pair_gate_audit.py",
    "tools/p0m3/audio_render_shootout/scripts/recover_analyzer_evidence.py",
    "tools/p0m3/audio_render_shootout/scripts/wsl_bounded_audio_oracles.py",
    "tools/p0m3/audio_render_shootout/scripts/verify_analyzer_evidence_recovery.py",
    "tools/p0m3/audio_render_shootout/scripts/selftest_analyzer_evidence_recovery.py",
    "tools/p0m3/audio_render_shootout/scripts/build_analyzer_evidence_recovery_pm_pack.py",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_subset.json",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_validation.json",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_selftest.json",
    "tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_environment_probes.json",
    "HANDOFF_TO_PM.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = Path(args.out).resolve()
    missing = [name for name in PACK_FILES if not (REPO_ROOT / name).is_file()]
    if missing:
        raise SystemExit("PACK_INPUT_MISSING:" + ",".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in PACK_FILES:
            archive.write(REPO_ROOT / name, name.replace("\\", "/"))
    print(f"PM_PACK_CREATED entries={len(PACK_FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
