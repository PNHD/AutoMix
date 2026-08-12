"""
Builds the P0-M3-R3 blinded owner listening pack + the PM's blind_key.json
(Issue #7 "BLINDED OWNER LISTENING PACK").

Selection (11 clips, within the "approximately 9-12" target):
  Scenario S1 (=R3-A, no-stretch control):    M1, M2, M3   (3 clips)
  Scenario S2 (=R3-B, moderate stretch):      M1, M2, M3   (3 clips)
  Scenario S3 (=R3-C, half/double residual):  M1, M2, M3   (3 clips)
  Scenario S4 (=R3-D, incompatible fallback): M0, M1       (2 clips)
M0 is excluded from S1-S3 (it exists to demonstrate the DSP-metric contrast
in the PM machine-metrics report, not as a shippable candidate worth
spending the owner's limited listening budget on) but IS included in S4,
because M1/M2/M3 are DSP-IDENTICAL for S4 (FULL_DJ_BLEND withheld -> all
three render the byte-identical SIMPLE_CROSSFADE fallback, verified via
matching SHA-256 during authoring) -- pairing two identical clips would
waste the owner's listening budget on a no-op comparison. S4 instead pairs
M0 (weak linear baseline) against M1 (equal-power fallback reference), the
one real audible difference scenario D's audio can actually demonstrate.

PM STAGE A REVIEW R4 repair: clips are extracted EXCLUSIVELY from
results/rendered_clean/ (marker-free source audio, dsp/render_common.py
`variant="clean"`) -- never from results/rendered/ (diagnostic,
marker-embedded). The prior pass's owner ZIP drew from the diagnostic
render set, so its 13kHz ticks could appear in owner-listening audio; that
pack is invalidated and this rebuild sources only from the clean path.

PM STAGE A REVIEW R5 repair: the blind seed is NOT hardcoded in this
(committed) source file. It is REQUIRED via the AUTOMIX_R3_BLIND_SEED
environment variable at run time (a local/PM-only input) -- the script
refuses to run without it, and never falls back to a default. This is a
NEW seed for this rebuild; it is unrelated to the previously-committed
(now removed) seed, so the repaired pack's mapping cannot be derived from
old repository history.

Usage:
    AUTOMIX_R3_BLIND_SEED=<your-secret-random-integer> python scripts/build_listening_pack.py
"""
import hashlib
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float, write_wav_pcm16  # noqa: E402
from dsp.render_common import compute_segments, load_scenario_context  # noqa: E402

RENDERED_CLEAN_DIR = ROOT / "results" / "rendered_clean"
CLIPS_DIR = ROOT / "results" / "listening_clips"  # local only (gitignored via *.wav)
BLIND_KEY_PATH = ROOT / "results" / "blind_key.json"  # local only, gitignored (R5 repair) -- PM-zip evidence only

BLIND_SEED_ENV_VAR = "AUTOMIX_R3_BLIND_SEED"

CLIP_WINDOW_S = 28.0  # target clip length, roughly centered on the transition (Issue #7: ~20-35s)

SCENARIO_PLAN = [
    ("S1", "R3-A", ["M1", "M2", "M3"]),
    ("S2", "R3-B", ["M1", "M2", "M3"]),
    ("S3", "R3-C", ["M1", "M2", "M3"]),
    ("S4", "R3-D", ["M0", "M1"]),
]


def require_blind_seed() -> int:
    raw = os.environ.get(BLIND_SEED_ENV_VAR)
    if not raw:
        print(
            f"ERROR: {BLIND_SEED_ENV_VAR} environment variable is required (PM STAGE A REVIEW R5 repair -- "
            "the blind seed must never be hardcoded in committed source). "
            f"Example: {BLIND_SEED_ENV_VAR}=<secret-random-integer> python scripts/build_listening_pack.py",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return int(raw)
    except ValueError:
        print(f"ERROR: {BLIND_SEED_ENV_VAR} must be an integer, got {raw!r}", file=sys.stderr)
        sys.exit(1)


def extract_clip(transition_id: str, method: str) -> tuple:
    audio, sr = read_wav_float(RENDERED_CLEAN_DIR / f"{transition_id}_{method}.wav")
    ctx = load_scenario_context(transition_id, variant="clean")
    segs = compute_segments(ctx)
    # Center the clip on the middle of the overlap window (relative to the
    # render, which always starts with the same 15s pre-roll -- see
    # dsp/render_common.PRE_ROLL_S).
    pre_roll_smp = segs["onset_smp"] - max(0, segs["onset_smp"] - int(round(15.0 * sr)))
    overlap_smp = segs["overlap_len_smp"]
    center = pre_roll_smp + overlap_smp // 2
    half_window = int(round(CLIP_WINDOW_S / 2 * sr))
    start = max(0, center - half_window)
    end = min(audio.shape[0], center + half_window)
    return audio[start:end], sr


def build():
    blind_seed = require_blind_seed()
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    blind_key = {"seed": blind_seed, "scenarios": {}}
    manifest = []

    for scenario_label, transition_id, methods in SCENARIO_PLAN:
        rng = random.Random(f"{blind_seed}:{transition_id}")
        letters = list("ABCDEFGH")[: len(methods)]
        shuffled_methods = methods[:]
        rng.shuffle(shuffled_methods)
        letter_to_method = dict(zip(letters, shuffled_methods))
        blind_key["scenarios"][scenario_label] = {
            "internal_transition_id": transition_id,
            "letter_to_method": letter_to_method,
        }
        for letter, method in letter_to_method.items():
            clip, sr = extract_clip(transition_id, method)
            clip_name = f"{scenario_label}-{letter}.wav"
            clip_path = CLIPS_DIR / clip_name
            write_wav_pcm16(clip_path, clip, sr)
            sha256 = hashlib.sha256(clip_path.read_bytes()).hexdigest()
            manifest.append({
                "clip_name": clip_name,
                "scenario_label": scenario_label,
                "letter": letter,
                "internal_transition_id": transition_id,
                "internal_method": method,
                "sha256": sha256,
                "duration_s": clip.shape[0] / sr,
                "sample_rate": sr,
                "channels": clip.shape[1],
                "source_variant": "clean",
            })
            print(f"{clip_name}: {transition_id}/{method} -> {clip.shape[0]/sr:.2f}s sha256={sha256[:12]}...")

    blind_key["clip_manifest"] = manifest
    BLIND_KEY_PATH.write_text(json.dumps(blind_key, indent=2), encoding="utf-8")
    print(f"\nWrote {len(manifest)} blinded clips (sourced from CLEAN renders only) to {CLIPS_DIR}")
    print(f"Wrote blind key (PM-ONLY, gitignored, never in owner pack) to {BLIND_KEY_PATH}")


if __name__ == "__main__":
    build()
