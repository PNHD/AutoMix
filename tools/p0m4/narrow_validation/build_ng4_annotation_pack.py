"""
P0-M4-R2 PF4 -- source-only owner NG4 ground-truth annotation pack builder.

The frozen NG4 subset (23 of the 50 pairs; SS12.6) needs an expected
`transition_class_policy` that is NOT derived from the planner's own output
(that would be circular -- `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-
CONTRACT.md` SS16 / Issue #9 PF4). No pre-existing MANUAL annotation covers
these specific combinatorial real pairs. Per PF4, this script builds the
source-only owner annotation pack instead:

  - the owner hears ONLY the unprocessed outgoing ending and unprocessed
    incoming beginning of each NG4 pair -- no crossfade, no candidate/
    baseline identity, no dev/holdout label;
  - clips are decoded via the SAME accepted `real_music_pipeline.
    convert_to_canonical_wav` ffmpeg path already used elsewhere in this
    task (no new decode logic), then trimmed to a fixed, deterministic
    window (last CLIP_SECONDS of the outgoing track, first CLIP_SECONDS of
    the incoming track) -- no analyzer chooses the window;
  - pairs are assigned a random blind token (`NG4-01`..`NG4-23`, shuffled
    independently of split/selection order) so the response template and
    audio filenames never carry opaque IDs, split membership, or ordering
    information;
  - the audio clips, the blind key (token -> opaque IDs/split), and the
    filled response template are ALL local-only -- gitignored, never
    committed.

PM REVIEW REPAIR (`PHASE0_PF4_REPAIR_REQUIRED`, Issue #9 comment
`5318289406`): the response schema previously forced the owner to pick
exactly ONE `assigned_class` per pair. That is materially narrower than
the accepted P0-M2 `transition_class_policy` schema
(`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` SS6), which explicitly
allows MULTIPLE classes to be simultaneously correct choices for one pair
via `accepted_unconditional`. The owner-facing schema is repaired here to
judge each of the three authorized narrow rendered classes INDEPENDENTLY
(true/false/unset), never forcing a single winner. See
`ng4_policy_materialization.py` for how a completed response row is later
mapped onto the full `transition_class_policy` object -- that mapping is
NOT run in this pass (no owner responses exist yet).

Only THIS SCRIPT (containing no real data) and its sibling
`patch_ng4_pack_schema.py` are tracked deliverables.

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

# The three authorized OBSERVABLE narrow rendered classes (contract SS7 /
# benchmark contract SS16.7) -- the ONLY classes ever offered to the owner.
# FULL_DJ_BLEND / SHORT_EQ_BLEND / non-natural CUT are deterministic
# contract-forbidden outputs, never an owner annotation question -- see
# ng4_policy_materialization.FORBIDDEN_NARROW_CLASSES, which adds them to
# `rejected` mechanically, with no owner involvement.
NARROW_CLASSES = ["NO_SPECIAL_TRANSITION", "GAPLESS", "SIMPLE_CROSSFADE"]

INSTRUCTIONS_TEXT = """\
# NG4 Source-Only Transition-Class Annotation -- Instructions

Thank you for listening. This is NOT a preference/quality comparison (that
listening happens later, blinded, in a separate step), and it is NOT
"which one transition would you pick". This step only asks, independently
for each of three possible transition STYLES: "would this style be a
musically acceptable way to move from clip A to clip B, assuming it were
executed competently?"

There are 23 short sets, each labeled with a blind code like `NG4-07`. You
have NO information about which real tracks these are, which split they
belong to, whether either candidate engine would actually choose this
pair, or how any candidate/baseline system would handle them -- and you
don't need any of that information for this task.

## What to do, per set

Each set has exactly two short (~20s) unprocessed clips:

  - `A_outgoing_ending.wav` -- the raw last ~20 seconds of one track,
    completely unprocessed (no fade applied).
  - `B_incoming_beginning.wav` -- the raw first ~20 seconds of a different
    track, completely unprocessed.

Listen to A, then B (in that order -- that is the order they would play).

Then, for **EACH of the three styles below, independently**, answer
true/false: "would this style be a musically acceptable transition here?"
More than one can be true. Zero, one, two, or all three can be true --
whatever is honestly correct for this specific pair. Do NOT feel you must
pick only one, and do NOT feel you must mark something acceptable just to
have an answer.

  - **NO_SPECIAL_TRANSITION** -- playing B right after A with a plain cut
    or a brief natural pause (no fade) would be a normal, acceptable way
    to sequence these two tracks. This is acceptable for the VAST
    majority of ordinary song pairs.
  - **GAPLESS** -- these genuinely sound like two parts of ONE continuous
    musical work (e.g. a deliberately segued pair, a live medley, or an
    album sequenced so the ending of A visibly/audibly runs straight into
    the start of B with no natural pause). Mark this true only if you
    would be surprised or annoyed by ANY gap or fade being inserted here
    -- it should feel like one piece of music, not two songs placed next
    to each other. For most ordinary pairs this will be false.
  - **SIMPLE_CROSSFADE** -- a brief overlapping volume fade between the
    end of A and the start of B would sound pleasant/appropriate here
    (e.g. A fades out gently while B fades in, so there's a short moment
    where both are audible together). Mark this true whenever a fade
    would clearly be an acceptable (not necessarily best) way to move
    between them -- it is common for this to be true AT THE SAME TIME as
    `NO_SPECIAL_TRANSITION` for an ordinary pair of separate songs; both
    can be reasonable choices.

### Examples

- Two ordinary, unrelated songs: `NO_SPECIAL_TRANSITION` = true,
  `SIMPLE_CROSSFADE` = true (both are fine), `GAPLESS` = false.
- A live-medley-style segue / one continuous work split into two files:
  `GAPLESS` = true; `NO_SPECIAL_TRANSITION` and `SIMPLE_CROSSFADE` are
  likely both false (a gap or fade would be jarring here).
- Two songs that would sound genuinely awkward with ANY of the three
  styles (e.g. an abrupt style clash): all three can be false.

Also record:

  - **confidence**: HIGH / MEDIUM / LOW -- how sure you are, overall, of
    this set of three answers.
  - **note** (optional): one line, anything you noticed.

## What you are NOT judging here

You are judging the STYLE in the abstract, assuming competent execution --
never a specific candidate implementation's actual audio quality. Whether
a particular engine's rendered crossfade sounds good, has a volume dip, a
tempo artifact, etc. is judged later, in a separate blinded listening
step, on actually-rendered audio. Do not try to guess whether this pair
became a `SIMPLE_CROSSFADE` candidate or not -- that information is not
available to you and is irrelevant to this step.

## Please don't try to guess the songs or the split

Blind codes carry no information about track identity, ordering, or which
half of the validation a pair belongs to. Just listen and react normally
to the two clips as presented.

## When you're done

Fill in every row of `response_template.json`: set each of
`class_acceptability.NO_SPECIAL_TRANSITION` / `.GAPLESS` /
`.SIMPLE_CROSSFADE` to `true` or `false` (never leave any of the three as
`null`), plus `confidence`, plus an optional `note`. Save it back in
place. Please don't rename, reorder, or delete any files.
"""


def build_response_template(tokens: list) -> dict:
    """Shared schema builder -- used by both a fresh pack build and
    `patch_ng4_pack_schema.py`'s in-place repair of an existing pack, so
    the two paths can never drift apart."""
    return {
        "narrow_classes": NARROW_CLASSES,
        "instructions": "See INSTRUCTIONS.md in this same directory. For every token, set each of the three "
                        "class_acceptability values to true or false (never leave null) -- more than one may be true.",
        "responses": [
            {
                "token": token,
                "class_acceptability": {c: None for c in NARROW_CLASSES},
                "confidence": None,
                "note": "",
            }
            for token in tokens
        ],
    }


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
    tokens = []

    for i, idx in enumerate(order, start=1):
        pr = ng4_pairs[idx]
        token = f"NG4-{i:02d}"
        tokens.append(token)
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

    (pack_dir / "blind_key.local.json").write_text(json.dumps(blind_key, indent=2), encoding="utf-8")
    (pack_dir / "response_template.json").write_text(json.dumps(build_response_template(tokens), indent=2), encoding="utf-8")
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
