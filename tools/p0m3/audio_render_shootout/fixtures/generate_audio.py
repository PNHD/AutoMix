"""
Renders the synthetic outgoing/incoming source WAVs for every P0-M3-R3
scenario (fixtures/scenario_fixtures.py's audio_plan blocks) via
fixtures/synth.py.

Audio is written to audio_local/ (gitignored, LOCAL ONLY -- AGENTS.md rule 4
/ Issue #7 "Audio source WAVs and rendered WAVs: LOCAL ONLY, NOT
COMMITTED"). Ground-truth metadata (beat/downbeat grid, marker sample
positions, section boundaries) is committed to fixtures/ground_truth/ since
it is metadata, not audio, and is required to compute machine alignment
metrics later.

Usage:
    python fixtures/generate_audio.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from synth import make_track  # noqa: E402
from dsp.wav_io import write_wav_float32  # noqa: E402
from scenario_fixtures import ALL_SCENARIOS  # noqa: E402

AUDIO_DIR = ROOT / "audio_local"
GT_DIR = HERE / "ground_truth"


def render_scenario_audio(scenario: dict):
    tid = scenario["transition_id"]
    if "reuses_audio_from" in scenario:
        print(f"{tid}: reuses audio from {scenario['reuses_audio_from']} (no independent render)")
        return
    plan = scenario["audio_plan"]
    for side in ("outgoing", "incoming"):
        spec = plan[side]
        stereo, gt = make_track(spec)
        wav_path = AUDIO_DIR / f"{tid}_{side}.wav"
        write_wav_float32(wav_path, stereo, spec.get("sr", 44100))
        gt_path = GT_DIR / f"{tid}_{side}.ground_truth.json"
        gt_path.write_text(json.dumps(gt, indent=2), encoding="utf-8")
        print(f"{tid}: wrote {wav_path.name} ({stereo.shape[0]/44100:.2f}s, "
              f"{len(gt['beats_ms'])} beats, markers@{gt['marker_ms']}ms)")


def main():
    AUDIO_DIR.mkdir(exist_ok=True)
    GT_DIR.mkdir(exist_ok=True)
    for scenario in ALL_SCENARIOS:
        render_scenario_audio(scenario)
    print(f"\nSource audio written to {AUDIO_DIR} (gitignored, local only)")
    print(f"Ground-truth metadata written to {GT_DIR} (committed)")


if __name__ == "__main__":
    main()
