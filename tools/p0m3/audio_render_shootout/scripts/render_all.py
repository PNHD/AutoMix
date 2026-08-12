"""
Writes M0/M1 renders (which don't need the browser bridge) to
results/rendered/ + results/render_meta/, matching M2/M3's output layout.

M2 must be produced beforehand via:
    python dsp/render_m2_signalsmith.py prepare <id>   (+ open the printed URL in a real browser)
    python dsp/render_m2_signalsmith.py finish <id>    (or `fallback <id>` for scenario D)
M3 is produced via:
    python dsp/render_m3_rubberband.py <id>

Usage:
    python scripts/render_all.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp import render_m0, render_m1  # noqa: E402
from dsp.render_m2_signalsmith import _write_result  # noqa: E402

SCENARIOS = ["R3-A", "R3-B", "R3-C", "R3-D"]


def main():
    for tid in SCENARIOS:
        for mod, name in [(render_m0, "M0"), (render_m1, "M1")]:
            t0 = time.perf_counter()
            audio, sr, meta = mod.render(tid)
            wall_s = time.perf_counter() - t0
            meta["render_wall_time_s"] = wall_s
            meta["real_time_factor"] = wall_s / meta["output_duration_s"] if meta["output_duration_s"] else None
            _write_result(tid, name, audio, sr, meta)
            print(f"{tid} {name}: wrote render, wall={wall_s:.3f}s rtf={meta['real_time_factor']:.4f}")


if __name__ == "__main__":
    main()
