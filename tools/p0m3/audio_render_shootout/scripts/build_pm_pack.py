"""
Assembles P0-M3-R3-PM-REVIEW.zip (LOCAL ONLY -- never committed, Issue #7
"PM REVIEW PACK").

Includes: research report + provenance docs, entire harness source, all
fixture/ground-truth/planner-decision metadata, machine result JSON,
blind_key.json (with clip hashes), the blinded listening WAVs themselves
(synthetic, project-generated -- explicitly permitted for forensic PM
review), and HANDOFF_TO_PM.md. Excludes: vendor/ (re-fetchable, pinned
commit documented separately), .venv/, audio_local/ + results/rendered/
(the full 16-way non-blinded render set -- regenerable exactly via the
documented commands; kept out to keep this ZIP a reasonable size), no
private owner music (none exists in this pass).

Usage:
    python scripts/build_pm_pack.py
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # tools/p0m3/audio_render_shootout
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

ZIP_PATH = REPO_ROOT / "P0-M3-R3-PM-REVIEW.zip"

DOC_FILES = [
    REPO_ROOT / "docs" / "research" / "P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md",
    REPO_ROOT / "docs" / "research" / "P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md",
    REPO_ROOT / "HANDOFF_TO_PM.md",
]

HARNESS_GLOBS = [
    "README.md", "requirements.txt", ".gitignore",
    "fixtures/*.py", "fixtures/*.md",
    "fixtures/planner_decisions/*.json",
    "fixtures/ground_truth/*.json",
    "dsp/*.py",
    "web/*.html",
    "scripts/*.py",
]

RESULT_FILES = [
    "results/machine_metrics.json",
    "results/blind_key.json",
]
RESULT_GLOBS = [
    "results/render_meta/*.json",
]

LISTENING_CLIPS_GLOB = "results/listening_clips/*.wav"


def main():
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in DOC_FILES:
            zf.write(doc, doc.relative_to(REPO_ROOT).as_posix())

        for pattern in HARNESS_GLOBS:
            for path in sorted(ROOT.glob(pattern)):
                if path.is_file():
                    zf.write(path, (Path("tools/p0m3/audio_render_shootout") / path.relative_to(ROOT)).as_posix())

        for rel in RESULT_FILES:
            path = ROOT / rel
            zf.write(path, (Path("tools/p0m3/audio_render_shootout") / rel).as_posix())

        for pattern in RESULT_GLOBS:
            for path in sorted(ROOT.glob(pattern)):
                zf.write(path, (Path("tools/p0m3/audio_render_shootout") / path.relative_to(ROOT)).as_posix())

        for path in sorted(ROOT.glob(LISTENING_CLIPS_GLOB)):
            zf.write(path, (Path("tools/p0m3/audio_render_shootout") / path.relative_to(ROOT)).as_posix())

    names = zipfile.ZipFile(ZIP_PATH).namelist()
    print(f"Wrote {ZIP_PATH} with {len(names)} entries")
    for n in names:
        print(" ", n)


if __name__ == "__main__":
    main()
