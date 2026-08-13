"""Build the local-only non-self-referential runtime-probe PM ZIP once."""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACK_FILES = [
    "AGENTS.md",
    ".agents/skills/automix-task-contract/SKILL.md",
    ".agents/skills/automix-forensic-research/SKILL.md",
    ".agents/skills/automix-code-review/SKILL.md",
    "docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md",
    "docs/research/P0-M3-R3-ANALYZER-EVIDENCE-RECOVERY.md",
    "docs/research/P0-M3-R3-ALL-IN-ONE-RUNTIME-PROBE.md",
    "tools/p0m3/all_in_one_runtime_probe/probe_runtime.py",
    "tools/p0m3/all_in_one_runtime_probe/verify_runtime_probe.py",
    "tools/p0m3/all_in_one_runtime_probe/build_pm_pack.py",
    "tools/p0m3/all_in_one_runtime_probe/EXACT_COMMANDS.md",
    "tools/p0m3/all_in_one_runtime_probe/results/runtime_probe_sanitized.json",
    "tools/p0m3/all_in_one_runtime_probe/results/runtime_probe_validation.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--handoff", required=True)
    args = parser.parse_args()
    output = Path(args.out).resolve()
    handoff = Path(args.handoff).resolve()
    if output.exists():
        raise SystemExit("OUTPUT_ALREADY_EXISTS_BUILD_ONCE_REQUIRED")
    missing = [name for name in PACK_FILES if not (REPO / name).is_file()]
    if missing or not handoff.is_file():
        raise SystemExit("PACK_INPUT_MISSING:" + ",".join(missing + ([str(handoff)] if not handoff.is_file() else [])))
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in PACK_FILES:
            archive.write(REPO / name, name.replace("\\", "/"))
        archive.write(handoff, "HANDOFF_TO_PM.md")
    print(f"PM_PACK_CREATED entries={len(PACK_FILES) + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
