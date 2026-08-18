"""
P0-M5-R1 Phase F -- blinded owner listening pack.

Builds LOCAL ONLY `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip`: exactly
8 scenarios x 2 blinded methods = 16 real-music mixed WAV clips (copied
verbatim from `apple_like_render.py`'s finish-step output -- never
regenerated here), a blind key (letter -> method, LOCAL ONLY, never
zipped), instructions, and a machine-readable rating template.

Blinding: which letter (A/B) is M0 vs M1 is randomized independently per
scenario using ONE frozen seed (generated fresh by this script and written
ONLY to the local, never-committed, never-zipped blind key) -- never a
human choice, never a fixed pattern (e.g. always "M1=B") an owner could
learn to exploit across scenarios.

Never exposed to the owner: method names, opaque track IDs, dev/holdout
labels, filenames/titles/artists, or the blind key itself.

Usage:
    python tools/p0m5/apple_like_vertical_slice/build_owner_pack.py \
        --render-dir tools/p0m5/apple_like_vertical_slice/work_local/renders \
        --pair-manifest tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json \
        --pack-dir tools/p0m5/apple_like_vertical_slice/work_local/owner_pack
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

INSTRUCTIONS_TEXT = """\
# Apple-Like AutoMix -- Owner Listening Instructions

Thank you for listening. There are 8 scenarios, each with two clips: `A`
and `B`. Both clips in a scenario are the SAME pair of songs, transitioning
at the SAME point, made two different ways -- you're comparing them
against each other.

Each clip is about 30-35 seconds: some of the outgoing song, the
transition itself, then some of the incoming song.

## What to do, per scenario

Listen to both A and B (in either order, as many times as you like), then
answer:

1. **Overall preference**: `A` / `B` / `TIE`.
2. **A seamlessness**: 1-5 (see anchors below).
3. **B seamlessness**: 1-5.
4. **A musical intentionality**: 1-5 -- does this transition sound like it
   was deliberately, musically crafted, or does it sound accidental/
   mechanical?
5. **B musical intentionality**: 1-5.
6. **A unacceptable/veto**: yes/no -- would this be actively bad if it
   happened automatically while you were just listening to music (jarring,
   broken-sounding, wrong)?
7. **B unacceptable/veto**: yes/no.
8. Optional: a one-line free-text note.

### Anchors (used for both seamlessness and musical intentionality)

- **1** -- broken
- **2** -- poor
- **3** -- acceptable
- **4** -- good / intentional
- **5** -- excellent / convincingly seamless

## Please don't try to guess the technique

You are NOT being asked to identify or understand any transition-class
taxonomy, beat-matching, or DSP technique. Just listen and react to the
actual audio. Letters (A/B) are randomly assigned per scenario and carry
no information about how a clip was made.

## When you're done

Fill in every scenario in `OWNER_RATINGS_TEMPLATE.json` and save it back
in place. Please don't rename, reorder, or delete any files.
"""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render-dir", required=True)
    ap.add_argument("--pair-manifest", required=True)
    ap.add_argument("--pack-dir", required=True)
    args = ap.parse_args()

    manifest = load_json(Path(args.pair_manifest))
    if manifest.get("status") != "FROZEN":
        print(f"RESULT: BLOCKED -- pair manifest status {manifest.get('status')!r}, not FROZEN")
        return 1

    render_dir = Path(args.render_dir)
    pack_dir = Path(args.pack_dir)
    clips_dir = pack_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rng = random.SystemRandom()
    seed = rng.getrandbits(64)
    blind_rng = random.Random(seed)

    blind_key = {}
    rating_rows = []
    scenarios = [f"S{idx:02d}" for idx in range(1, len(manifest["pairs"]) + 1)]

    for idx, (tag, pair) in enumerate(zip(scenarios, manifest["pairs"]), start=1):
        m0_path = render_dir / f"{tag}_M0.wav"
        m1_path = render_dir / f"{tag}_M1.wav"
        if not m0_path.exists() or not m1_path.exists():
            print(f"RESULT: BLOCKED -- {tag} missing rendered M0/M1 file")
            return 1

        letters_shuffled = ["A", "B"]
        blind_rng.shuffle(letters_shuffled)
        m0_letter, m1_letter = letters_shuffled[0], letters_shuffled[1]

        shutil.copyfile(m0_path, clips_dir / f"{tag}-{m0_letter}.wav")
        shutil.copyfile(m1_path, clips_dir / f"{tag}-{m1_letter}.wav")

        blind_key[tag] = {
            "out_id": pair["out_id"],
            "in_id": pair["in_id"],
            "split": pair["split"],
            "A_method": "M0" if m0_letter == "A" else "M1",
            "B_method": "M0" if m0_letter == "B" else "M1",
        }
        rating_rows.append({
            "scenario": tag,
            "overall_preference": None,     # "A" | "B" | "TIE"
            "A_seamlessness_1_5": None,
            "B_seamlessness_1_5": None,
            "A_musical_intentionality_1_5": None,
            "B_musical_intentionality_1_5": None,
            "A_unacceptable_veto": None,    # true | false
            "B_unacceptable_veto": None,    # true | false
            "note": "",
        })

    (pack_dir / "blind_key.local.json").write_text(json.dumps({"seed": seed, "scenarios": blind_key}, indent=2), encoding="utf-8")
    (pack_dir / "LISTENING_INSTRUCTIONS.md").write_text(INSTRUCTIONS_TEXT, encoding="utf-8")
    (pack_dir / "OWNER_RATINGS_TEMPLATE.json").write_text(json.dumps({
        "instructions": "See LISTENING_INSTRUCTIONS.md. Fill in every field for every scenario.",
        "anchors": {"1": "broken", "2": "poor", "3": "acceptable", "4": "good / intentional", "5": "excellent / convincingly seamless"},
        "ratings": rating_rows,
    }, indent=2), encoding="utf-8")

    print(f"RESULT: OWNER_APPLE_LIKE_LISTENING_REQUIRED")
    print(f"Built {len(scenarios)}-scenario ({len(scenarios) * 2}-clip) blinded pack at: {pack_dir}")
    print(f"  clips:        {clips_dir} ({len(list(clips_dir.iterdir()))} files)")
    print(f"  blind key (LOCAL, never zipped): {pack_dir / 'blind_key.local.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
