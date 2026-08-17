"""
P0-M4-R2 PF4 -- source-only owner NG4 ground-truth annotation pack builder.

The frozen NG4 subset (23 of the 50 pairs; SS12.6) needs an expected
`transition_class_policy` that is NOT derived from the planner's own output
(that would be circular -- `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-
CONTRACT.md` SS16 / Issue #9 PF4). No pre-existing MANUAL annotation covers
these specific combinatorial real pairs (only the ORIGINAL V1/V2/V3
FULL_DJ-investigation pairs have any prior human involvement, and that
involvement was pair-SELECTION, never a "what class should this be" label;
a repository-wide search for every NG4 pair's opaque-ID combination found
no such annotation anywhere -- see the accompanying report). Per PF4, this
script builds the source-only owner annotation pack instead:

  - the owner hears ONLY the unprocessed outgoing ending and unprocessed
    incoming beginning of each NG4 pair -- no crossfade, no candidate/
    baseline identity, no dev/holdout label;
  - clips are decoded via the SAME accepted `real_music_pipeline.
    convert_to_canonical_wav` ffmpeg path already used elsewhehere in this
    task (no new decode logic), then trimmed to a fixed, deterministic
    window (last CLIP_SECONDS of the outgoing track, first CLIP_SECONDS of
    the incoming track) -- no analyzer chooses the window, so this stage
    cannot leak a "smart" boundary back into the label;
  - pairs are assigned a random blind token (`NG4-01`..`NG4-23`, shuffled
    independently of split/selection order) so the response template and
    audio filenames never carry opaque IDs, split membership, or
    ordering information;
  - the audio clips, the blind key (token -> opaque IDs/split), and the
    filled response template are ALL local-only -- gitignored, never
    committed, per this task's privacy contract ("owner annotation/
    listening packs" are explicitly listed as private/local-only).

Only THIS SCRIPT (containing no real data) is a tracked deliverable.

Usage:
    python tools/p0m4/narrow_validation/build_ng4_annotation_pack.py \
        --pack-dir tools/p0m4/narrow_validation/work_local/ng4_annotation_pack
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCRIPTS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "scripts"
CORPUS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "real_music" / "work_local" / "corpus"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HERE))

import real_music_pipeline as rmp  # noqa: E402
from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402

CANONICAL_SR = 44100
CLIP_SECONDS = 20.0  # fixed, deterministic, never analyzer-chosen

ALLOWED_CLASSES = ["NO_SPECIAL_TRANSITION", "GAPLESS", "SIMPLE_CROSSFADE"]

INSTRUCTIONS_TEXT = """\
# NG4 Source-Only Transition-Class Annotation -- Instructions

Thank you for listening. This is NOT a preference/quality comparison (that
listening happens later, blinded, in a separate step). This step only asks:
"given these two unprocessed clips, what is the musically appropriate way
to move from one to the other?"

There are 23 short sets, each labeled with a blind code like `NG4-07`. You
have NO information about which real tracks these are, which split they
belong to, or how any candidate engine would handle them -- and you don't
need that information for this task.

## What to do, per set

Each set has exactly two short (~20s) unprocessed clips:

  - `A_outgoing_ending.wav` -- the raw last ~20 seconds of one track,
    completely unprocessed (no fade applied).
  - `B_incoming_beginning.wav` -- the raw first ~20 seconds of a different
    track, completely unprocessed.

Listen to A, then B (in that order -- that is the order they would play).
Then decide which ONE of these three labels best describes the
appropriate transition between them:

  - **NO_SPECIAL_TRANSITION** -- these are two ordinary, separate songs.
    Playing B right after A (with a plain cut or a brief natural pause,
    no fade) is the normal, correct thing to do. This is the label for
    the VAST majority of real-world song pairs -- pick this whenever
    nothing below clearly applies.
  - **GAPLESS** -- these genuinely sound like two parts of ONE continuous
    musical work (e.g. a deliberately segued pair, a live medley, or an
    album sequenced so the ending of A visibly/audibly runs straight into
    the start of B with no natural pause). Only pick this if you would be
    surprised or annoyed by ANY gap or fade being inserted here -- it
    should feel like one piece of music, not two songs placed next to
    each other.
  - **SIMPLE_CROSSFADE** -- these are two separate songs (not one
    continuous work), but a brief overlapping volume fade between the
    end of A and the start of B would sound pleasant/appropriate here
    (e.g. A fades out gently while B fades in, so there's a short
    moment where both are audible together). Pick this only when a
    fade would clearly be an IMPROVEMENT over a plain cut/pause, not
    merely "harmless".

Also record:

  - **confidence**: HIGH / MEDIUM / LOW -- how sure you are of this label.
  - **note** (optional): one line, anything you noticed.

## Please don't try to guess the songs or the split

Blind codes carry no information about track identity, ordering, or which
half of the validation a pair belongs to. Just listen and react normally
to the two clips as presented.

## When you're done

Fill in every row of `response_template.json` (one of the three labels for
`assigned_class`, plus `confidence`, plus an optional `note`) and save it
back in place. Please don't rename, reorder, or delete any files.
"""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ms_to_smp(ms: float, sr: int) -> int:
    return int(round(ms / 1000.0 * sr))


def extract_clip(audio, sr: int, start_smp: int, end_smp: int):
    start_smp = max(0, start_smp)
    end_smp = min(audio.shape[0], end_smp)
    return audio[start_smp:end_smp]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-dir", required=True, help="LOCAL-ONLY output directory for the annotation pack. Never committed.")
    ap.add_argument("--seed-file", default=None, help="Optional path to a local file holding the blind-shuffle RNG seed, for reproducible re-generation. LOCAL-ONLY.")
    args = ap.parse_args()

    manifest = load_json(HERE / "manifest_sanitized.json")
    if manifest.get("status") != "FROZEN":
        print(f"RESULT: BLOCKED -- manifest status is {manifest.get('status')!r}, not FROZEN")
        return 1

    ng4_pairs = [p for p in manifest["pairs"] if p.get("ng4_member")]
    if len(ng4_pairs) != 23:
        print(f"RESULT: BLOCKED -- expected exactly 23 NG4 pairs, found {len(ng4_pairs)}")
        return 1

    analysis = load_json(CORPUS_DIR / "corpus_analysis.local.json")
    id_map = load_json(CORPUS_DIR / "id_map.local.json")

    pack_dir = Path(args.pack_dir)
    clips_dir = pack_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    decode_dir = pack_dir / "decoded_cache"
    decode_dir.mkdir(parents=True, exist_ok=True)

    # Random, non-derivable blind-token assignment -- deliberately NOT a
    # function of the SS12 selection salt, so a reader of selection.py can
    # never recover pair identity/order from the token alone.
    rng = random.SystemRandom()
    order = list(range(len(ng4_pairs)))
    rng.shuffle(order)

    blind_key = {}
    response_template = []

    for i, idx in enumerate(order, start=1):
        pr = ng4_pairs[idx]
        token = f"NG4-{i:02d}"
        out_id, in_id = pr["out_id"], pr["in_id"]
        blind_key[token] = {"out_id": out_id, "in_id": in_id, "split": pr["split"]}

        out_wav_path = decode_dir / f"{out_id}.wav"
        if not out_wav_path.exists():
            rmp.convert_to_canonical_wav(id_map[out_id], out_wav_path, decode_dir / f"{out_id}_ffmpeg_error.log")
        in_wav_path = decode_dir / f"{in_id}.wav"
        if not in_wav_path.exists():
            rmp.convert_to_canonical_wav(id_map[in_id], in_wav_path, decode_dir / f"{in_id}_ffmpeg_error.log")

        out_audio, sr_o = read_wav_float(out_wav_path)
        in_audio, sr_i = read_wav_float(in_wav_path)
        assert sr_o == CANONICAL_SR and sr_i == CANONICAL_SR

        clip_len = ms_to_smp(CLIP_SECONDS * 1000, CANONICAL_SR)
        ending_clip = extract_clip(out_audio, CANONICAL_SR, out_audio.shape[0] - clip_len, out_audio.shape[0])
        beginning_clip = extract_clip(in_audio, CANONICAL_SR, 0, clip_len)

        write_wav_float32(clips_dir / f"{token}_A_outgoing_ending.wav", ending_clip, CANONICAL_SR)
        write_wav_float32(clips_dir / f"{token}_B_incoming_beginning.wav", beginning_clip, CANONICAL_SR)

        response_template.append({
            "token": token,
            "assigned_class": None,  # owner fills: one of ALLOWED_CLASSES
            "confidence": None,      # owner fills: HIGH / MEDIUM / LOW
            "note": "",
        })

    (pack_dir / "blind_key.local.json").write_text(json.dumps(blind_key, indent=2), encoding="utf-8")
    (pack_dir / "response_template.json").write_text(json.dumps({
        "allowed_classes": ALLOWED_CLASSES,
        "instructions": "See INSTRUCTIONS.md in this same directory. Fill assigned_class + confidence for every row.",
        "responses": response_template,
    }, indent=2), encoding="utf-8")
    (pack_dir / "INSTRUCTIONS.md").write_text(INSTRUCTIONS_TEXT, encoding="utf-8")

    print(f"RESULT: OWNER_NG4_GROUND_TRUTH_REQUIRED")
    print(f"Built {len(ng4_pairs)}-pair source-only annotation pack at: {pack_dir}")
    print(f"  clips:              {clips_dir}")
    print(f"  blind key (LOCAL):  {pack_dir / 'blind_key.local.json'}")
    print(f"  response template:  {pack_dir / 'response_template.json'}")
    print(f"  instructions:       {pack_dir / 'INSTRUCTIONS.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
