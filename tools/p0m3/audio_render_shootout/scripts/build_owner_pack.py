"""
Assembles P0-M3-R3-OWNER-LISTENING.zip (LOCAL ONLY -- never committed,
Issue #7 "BLINDED OWNER LISTENING PACK").

Contains ONLY: LISTENING_INSTRUCTIONS.md, OWNER_RATINGS_TEMPLATE.json, and
the blinded WAV clips (opaque S#-X.wav names). Deliberately excludes
blind_key.json and every other internal file.

Usage:
    python scripts/build_owner_pack.py
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

BLIND_KEY_PATH = ROOT / "results" / "blind_key.json"
CLIPS_DIR = ROOT / "results" / "listening_clips"
SRC_DIR = ROOT / "results" / "owner_pack_src"
ZIP_PATH = REPO_ROOT / "P0-M3-R3-OWNER-LISTENING.zip"

RATING_FIELDS = [
    "seamlessness_continuity",
    "timing_rhythmic_naturalness",
    "stretch_pitch_naturalness",
    "bass_low_end_transition",
    "momentum_excitement",
    "overall_preference",
]
YES_NO_FIELDS = [
    "noticeable_hard_discontinuity",
    "annoying_or_fatiguing_artifact",
    "acceptable_for_normal_automix",
]


def build_ratings_template(clip_names: list[str]) -> dict:
    template = {"instructions": "Fill in one entry per clip. 1-5 scale for rating fields; 'yes'/'no' for the yes/no fields.", "clips": {}}
    for name in sorted(clip_names):
        entry = {field: None for field in RATING_FIELDS}
        entry.update({field: None for field in YES_NO_FIELDS})
        entry["optional_note"] = ""
        template["clips"][name] = entry
    return template


def main():
    blind_key = json.loads(BLIND_KEY_PATH.read_text(encoding="utf-8"))
    clip_names = [entry["clip_name"].replace(".wav", "") for entry in blind_key["clip_manifest"]]

    SRC_DIR.mkdir(parents=True, exist_ok=True)
    ratings_template = build_ratings_template(clip_names)
    (SRC_DIR / "OWNER_RATINGS_TEMPLATE.json").write_text(json.dumps(ratings_template, indent=2), encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(SRC_DIR / "LISTENING_INSTRUCTIONS.md", "LISTENING_INSTRUCTIONS.md")
        zf.write(SRC_DIR / "OWNER_RATINGS_TEMPLATE.json", "OWNER_RATINGS_TEMPLATE.json")
        for entry in blind_key["clip_manifest"]:
            clip_path = CLIPS_DIR / entry["clip_name"]
            zf.write(clip_path, entry["clip_name"])

    print(f"Wrote {ZIP_PATH} with {len(clip_names)} clips + instructions + ratings template")
    print(f"Zip contents: {zipfile.ZipFile(ZIP_PATH).namelist()}")


if __name__ == "__main__":
    main()
