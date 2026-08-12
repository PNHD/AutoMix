"""
P0-M3-R3 STAGE B -- builds a NEW LOCAL-ONLY blinded real-music owner
listening pack (`P0-M3-R3-REAL-MUSIC-OWNER-LISTENING.zip`), per the newest
Issue #7 PM comment ("Create a NEW local-only blind mapping for this
real-music pack. Do not reuse any synthetic-pack seed/mapping. Do not
commit seed/key. Do not expose mapping in Claude's owner-facing handoff.").

Reads the per-pair renders `real_music_pipeline.py` (A/B, + ffmpeg-
rubberband reference-only C) and `real_music_signalsmith.py` (owner-facing
Signalsmith C) already wrote to `real_music/work_local/renders/<PAIR_ID>/`.
For the owner-facing pack, candidate C is ALWAYS the Signalsmith render
(`C_conditional_tempo_candidate_SIGNALSMITH_OWNER.wav`) -- the
ffmpeg-Rubber-Band C (`C_conditional_tempo_candidate.wav`) is
PM/reference-only and is never included here (Issue #7 PM STAGE B comment:
"Signalsmith Stretch is the OWNER-LISTENING production candidate ... Do not
use Rubber Band as the sole C candidate in owner listening").

Blinding: a NEW seed, required via AUTOMIX_R3_REAL_MUSIC_BLIND_SEED (never
hardcoded, never the synthetic pack's seed/env-var). Opaque clip filenames
(`V1-A.wav`, `V1-B.wav`, ...). Strips all metadata (dsp.wav_io.write_wav_pcm16
emits only RIFF/fmt /data -- no tag chunk to leak into). The seed + full
blind key stay LOCAL ONLY (gitignored, PM-review evidence only via opaque
clip IDs) and are never written into the owner-facing ZIP.

Usage:
    AUTOMIX_R3_REAL_MUSIC_BLIND_SEED=<secret integer> python scripts/build_real_music_owner_pack.py
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float, write_wav_pcm16  # noqa: E402

RENDERS_DIR = ROOT / "real_music" / "work_local" / "renders"
CLIPS_DIR = ROOT / "real_music" / "work_local" / "owner_listening_clips"
BLIND_KEY_PATH = ROOT / "real_music" / "work_local" / "real_music_blind_key.local.json"
ZIP_PATH = REPO_ROOT / "P0-M3-R3-REAL-MUSIC-OWNER-LISTENING.zip"

BLIND_SEED_ENV_VAR = "AUTOMIX_R3_REAL_MUSIC_BLIND_SEED"

CANONICAL_SR = 44100
PRE_ROLL_S = 15.0  # matches real_music_pipeline.py's render_curve_variant pre_roll construction
CLIP_WINDOW_S = 30.0  # within the PM-requested ~25-40s focused-excerpt band

PAIR_CANDIDATE_FILES = {
    "A": "A_equal_power_reference.wav",
    "B": "B_late_hold_candidate.wav",
    "C": "C_conditional_tempo_candidate_SIGNALSMITH_OWNER.wav",  # owner-facing C is ALWAYS Signalsmith
}

YES_NO_FIELDS = [
    "SEAMLESS_ENOUGH_FOR_NORMAL_LISTENING",
    "VOLUME_DIP_OR_JUMP_NOTICEABLE",
    "TEMPO_OR_STRETCH_ARTIFACT_NOTICEABLE",
    "TIMING_OR_BEAT_FEELS_WRONG",
]

INSTRUCTIONS = """# P0-M3-R3 Real-Music Owner Listening -- Instructions

Three transition SETS (V1, V2, V3), each with 2-3 candidate clips (A, B,
and sometimes C). Clips within one set share the exact same transition
point in the same two songs -- only the mixing METHOD differs between A/B/C.
You do not need to know what each letter technically does; just compare
how they sound.

Blinding is about DSP/method identity only, NOT song identity -- you may
recognize the songs by ear, that's fine and expected.

For EACH set, listen to all of its clips (A/B, or A/B/C) and fill in:

- BEST: the letter you liked most
- SECOND: the letter you liked second-most
- WORST: the letter you liked least (leave blank / "N/A_ONLY_TWO_CLIPS" if
  the set only has 2 clips)
- SEAMLESS_ENOUGH_FOR_NORMAL_LISTENING: YES/NO (for your BEST clip)
- VOLUME_DIP_OR_JUMP_NOTICEABLE: YES/NO
- TEMPO_OR_STRETCH_ARTIFACT_NOTICEABLE: YES/NO
- TIMING_OR_BEAT_FEELS_WRONG: YES/NO
- OPTIONAL_NOTE: anything else worth telling us
- OVERALL_SCORE_1_TO_5: optional, only if useful

Fill in OWNER_RATINGS_TEMPLATE.json directly and return it.
"""


def require_blind_seed() -> int:
    raw = os.environ.get(BLIND_SEED_ENV_VAR)
    if not raw:
        print(
            f"ERROR: {BLIND_SEED_ENV_VAR} is required (must be a NEW seed, never the synthetic pack's "
            f"AUTOMIX_R3_BLIND_SEED). Example: {BLIND_SEED_ENV_VAR}=<secret-random-integer> python {Path(__file__).name}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return int(raw)
    except ValueError:
        print(f"ERROR: {BLIND_SEED_ENV_VAR} must be an integer, got {raw!r}", file=sys.stderr)
        sys.exit(1)


def discover_pair_candidates(pair_id: str) -> dict:
    pair_dir = RENDERS_DIR / pair_id
    result = json.loads((pair_dir / "result.json").read_text(encoding="utf-8"))
    available = {}
    for letter, fname in PAIR_CANDIDATE_FILES.items():
        path = pair_dir / fname
        if path.exists():
            available[letter] = path
    return available, result


def extract_clip(wav_path: Path, overlap_duration_ms: float):
    audio, sr = read_wav_float(wav_path)
    pre_roll_smp = int(round(min(PRE_ROLL_S, 1e9) * sr))  # renders always have a full 15s pre-roll (near-end candidates)
    overlap_smp = int(round(overlap_duration_ms / 1000.0 * sr))
    center = pre_roll_smp + overlap_smp // 2
    half_window = int(round(CLIP_WINDOW_S / 2 * sr))
    start = max(0, center - half_window)
    end = min(audio.shape[0], center + half_window)
    return audio[start:end], sr


def main():
    blind_seed = require_blind_seed()
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    blind_key = {"seed": blind_seed, "sets": {}}
    manifest = []
    ratings_sets = {}

    for pair_id in ("REAL-V1", "REAL-V2", "REAL-V3"):
        set_label = pair_id.replace("REAL-", "")
        available, result = discover_pair_candidates(pair_id)
        letters = sorted(available.keys())
        if not letters:
            print(f"WARNING: no rendered candidates found for {pair_id}, skipping")
            continue

        rng = random.Random(f"{blind_seed}:{pair_id}")
        blind_letters = list("ABCDEFGH")[: len(letters)]
        shuffled_internal = letters[:]
        rng.shuffle(shuffled_internal)
        blind_to_internal = dict(zip(blind_letters, shuffled_internal))
        blind_key["sets"][set_label] = {
            "internal_pair_id": pair_id,
            "blind_letter_to_internal_candidate": blind_to_internal,
        }

        overlap_ms = result["overlap_duration_ms"]
        for blind_letter, internal_letter in blind_to_internal.items():
            wav_path = RENDERS_DIR / pair_id / PAIR_CANDIDATE_FILES[internal_letter]
            clip, sr = extract_clip(wav_path, overlap_ms)
            clip_name = f"{set_label}-{blind_letter}.wav"
            clip_path = CLIPS_DIR / clip_name
            write_wav_pcm16(clip_path, clip, sr)
            sha256 = hashlib.sha256(clip_path.read_bytes()).hexdigest()
            manifest.append({
                "clip_name": clip_name,
                "set_label": set_label,
                "blind_letter": blind_letter,
                "internal_pair_id": pair_id,
                "internal_candidate": internal_letter,
                "sha256": sha256,
                "duration_s": clip.shape[0] / sr,
                "sample_rate": sr,
                "channels": clip.shape[1],
            })
            print(f"{clip_name}: {pair_id}/{internal_letter} -> {clip.shape[0]/sr:.2f}s sha256={sha256[:12]}...")

        entry = {
            "clip_letters": blind_letters,
            "BEST": None,
            "SECOND": None,
            "WORST": None if len(blind_letters) >= 3 else "N/A_ONLY_TWO_CLIPS",
        }
        entry.update({f: None for f in YES_NO_FIELDS})
        entry["OPTIONAL_NOTE"] = ""
        entry["OVERALL_SCORE_1_TO_5"] = None
        ratings_sets[set_label] = entry

    blind_key["clip_manifest"] = manifest
    Path(BLIND_KEY_PATH).parent.mkdir(parents=True, exist_ok=True)
    BLIND_KEY_PATH.write_text(json.dumps(blind_key, indent=2), encoding="utf-8")

    ratings_template = {
        "instructions": (
            "Per set: BEST/SECOND/WORST are clip letters from that set's own list "
            "(leave WORST as 'N/A_ONLY_TWO_CLIPS' if the set has only 2 clips). "
            "Four fields are 'YES'/'NO'. OPTIONAL_NOTE is free text. "
            "OVERALL_SCORE_1_TO_5 is optional (1-5 or null)."
        ),
        "sets": ratings_sets,
    }

    src_dir = ROOT / "real_music" / "work_local" / "owner_pack_src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "LISTENING_INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (src_dir / "OWNER_RATINGS_TEMPLATE.json").write_text(json.dumps(ratings_template, indent=2), encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(src_dir / "LISTENING_INSTRUCTIONS.md", "LISTENING_INSTRUCTIONS.md")
        zf.write(src_dir / "OWNER_RATINGS_TEMPLATE.json", "OWNER_RATINGS_TEMPLATE.json")
        for entry in manifest:
            zf.write(CLIPS_DIR / entry["clip_name"], entry["clip_name"])

    print(f"\nWrote {ZIP_PATH} with {len(manifest)} clips + instructions + ratings template")
    print(f"Zip contents: {zipfile.ZipFile(ZIP_PATH).namelist()}")
    print(f"Wrote LOCAL-ONLY blind key (never committed, never in owner ZIP) to {BLIND_KEY_PATH}")


if __name__ == "__main__":
    main()
