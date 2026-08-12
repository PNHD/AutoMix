"""
PM OWNER LISTENING DIRECTION UPDATE, Task 4 "SIMPLIFY OWNER RATING UX".

Builds the compact per-transition-set rubric (BEST/SECOND/WORST +
4 yes/no + optional note + optional 1-5 overall) that replaces the old
6-dimension-per-clip matrix (tools/p0m3/audio_render_shootout/results/
owner_pack_src/OWNER_RATINGS_TEMPLATE.json, still used for/kept as
historical record of the invalidated-for-quality-decisions synthetic
pack -- not used again).

This module is generic (works for the synthetic pack's letter/scenario
shape too), but its primary purpose is for the NEXT real-music pack --
see scripts/real_music_pipeline.py / real_music/MANIFEST_SCHEMA.md. Since
no owner-supplied real music is available this pass, this script also
supports a `--demo` mode that generates a template for a representative
3-set/2-3-letter shape so the generator itself is verifiable without real
clips.

Usage:
    python scripts/build_simplified_rating_template.py --demo
    # or, once a real pack's clip manifest exists:
    python scripts/build_simplified_rating_template.py --sets-json <path to {"S1": ["A","B","C"], ...}>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

YES_NO_FIELDS = [
    "SEAMLESS_ENOUGH_FOR_NORMAL_LISTENING",
    "VOLUME_DIP_OR_JUMP_NOTICEABLE",
    "TEMPO_OR_STRETCH_ARTIFACT_NOTICEABLE",
    "TIMING_OR_BEAT_FEELS_WRONG",
]


def build_simplified_template(sets: dict) -> dict:
    """`sets`: {set_label: [letters...]}, e.g. {"S1": ["A","B","C"]}."""
    template = {
        "instructions": "Per set: BEST/SECOND/WORST are clip letters from that set's own list (leave WORST blank if the set has only 2 clips). Four fields are 'YES'/'NO'. OPTIONAL_NOTE is free text. OVERALL_SCORE_1_TO_5 is optional (1-5 or null).",
        "sets": {},
    }
    for set_label, letters in sets.items():
        entry = {
            "clip_letters": letters,
            "BEST": None,
            "SECOND": None,
            "WORST": None if len(letters) >= 3 else "N/A_ONLY_TWO_CLIPS",
        }
        entry.update({f: None for f in YES_NO_FIELDS})
        entry["OPTIONAL_NOTE"] = ""
        entry["OVERALL_SCORE_1_TO_5"] = None
        template["sets"][set_label] = entry
    return template


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sets-json", default=None, help='Path to a JSON file: {"S1": ["A","B","C"], ...}')
    parser.add_argument("--demo", action="store_true", help="Generate a representative demo template (3 sets, matching this pass's 3 required real-music pair categories) to verify the generator without real clips.")
    parser.add_argument("--out", default=None, help="Output path (default: stdout)")
    args = parser.parse_args()

    if args.demo:
        sets = {
            "S1": ["A", "B"],       # close_tempo_minimal_stretch -- M1 vs M3 (M2 pending manual browser step)
            "S2": ["A", "B"],       # conditional_tempo_correction -- M1 vs M3
            "S3": ["A"],            # incompatible_downgrade -- only the allowed fallback exists, nothing to compare
        }
    elif args.sets_json:
        sets = json.loads(Path(args.sets_json).read_text(encoding="utf-8"))
    else:
        parser.error("either --demo or --sets-json is required")
        return

    template = build_simplified_template(sets)
    out_text = json.dumps(template, indent=2)
    if args.out:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(out_text)


if __name__ == "__main__":
    main()
