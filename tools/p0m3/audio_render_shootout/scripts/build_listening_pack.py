"""
Builds the P0-M3-R3 blinded owner listening pack + the PM's blind_key.json
(Issue #7 "BLINDED OWNER LISTENING PACK").

Selection (11 clips, within the "approximately 9-12" target):
  Scenario S1 (=R3-A, no-stretch control):    M1, M2, M3   (3 clips)
  Scenario S2 (=R3-B, moderate stretch):      M1, M2, M3   (3 clips)
  Scenario S3 (=R3-C, half/double residual):  M1, M2, M3   (3 clips)
  Scenario S4 (=R3-D, incompatible fallback): M1, M2       (2 clips)
M0 is excluded from S1-S3 (it exists to demonstrate the DSP-metric contrast
in the PM machine-metrics report, not as a shippable candidate worth
spending the owner's limited listening budget on) but IS included in S4,
because M1/M2/M3 are DSP-IDENTICAL for S4 (FULL_DJ_BLEND withheld -> all
three render the byte-identical SIMPLE_CROSSFADE fallback, verified via
matching SHA-256 during authoring) -- pairing two identical clips would
waste the owner's listening budget on a no-op comparison. S4 instead pairs
M0 (weak linear baseline) against M1 (equal-power fallback reference), the
one real audible difference scenario D's audio can actually demonstrate.

Blind letter mapping is a deterministic, seeded per-scenario shuffle
(never alphabetical-by-method-name, so letter order carries no information)
-- reproducible from BLIND_SEED, recorded ONLY in the PM's blind_key.json,
never in the owner pack.

Usage:
    python scripts/build_listening_pack.py
"""
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float, write_wav_pcm16  # noqa: E402
from dsp.render_common import compute_segments, load_scenario_context  # noqa: E402

RENDERED_DIR = ROOT / "results" / "rendered"
CLIPS_DIR = ROOT / "results" / "listening_clips"  # local only (gitignored via *.wav)
BLIND_KEY_PATH = ROOT / "results" / "blind_key.json"

BLIND_SEED = 20260812  # deterministic; changing this would silently reshuffle blinding, so it is pinned and recorded in the PM zip only

CLIP_WINDOW_S = 28.0  # target clip length, roughly centered on the transition (Issue #7: ~20-35s)

SCENARIO_PLAN = [
    ("S1", "R3-A", ["M1", "M2", "M3"]),
    ("S2", "R3-B", ["M1", "M2", "M3"]),
    ("S3", "R3-C", ["M1", "M2", "M3"]),
    ("S4", "R3-D", ["M0", "M1"]),
]


def extract_clip(transition_id: str, method: str) -> tuple:
    audio, sr = read_wav_float(RENDERED_DIR / f"{transition_id}_{method}.wav")
    ctx = load_scenario_context(transition_id)
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
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    blind_key = {"seed": BLIND_SEED, "scenarios": {}}
    manifest = []

    for scenario_label, transition_id, methods in SCENARIO_PLAN:
        rng = random.Random(f"{BLIND_SEED}:{transition_id}")
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
            })
            print(f"{clip_name}: {transition_id}/{method} -> {clip.shape[0]/sr:.2f}s sha256={sha256[:12]}...")

    blind_key["clip_manifest"] = manifest
    BLIND_KEY_PATH.write_text(json.dumps(blind_key, indent=2), encoding="utf-8")
    print(f"\nWrote {len(manifest)} blinded clips to {CLIPS_DIR}")
    print(f"Wrote blind key (PM-ONLY, never in owner pack) to {BLIND_KEY_PATH}")


if __name__ == "__main__":
    build()
