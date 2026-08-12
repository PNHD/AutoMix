"""
Writes M0/M1 renders (which don't need the browser bridge) to
results/rendered/ + results/render_meta/ (diagnostic variant, all 16 cells'
worth of M0/M1) and results/rendered_clean/ + results/render_meta_clean/
(clean variant, ONLY the specific (scenario, method) cells the owner
listening pack actually needs -- PM STAGE A REVIEW R4 repair).

M2 must be produced beforehand via:
    python dsp/render_m2_signalsmith.py prepare <id> [variant]   (+ open the printed URL in a real browser)
    python dsp/render_m2_signalsmith.py finish <id> [variant]    (or `fallback <id> [variant]` for scenario D)
M3 is produced via:
    python dsp/render_m3_rubberband.py <id> [variant]

Usage:
    python scripts/render_all.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp import render_m0, render_m1  # noqa: E402
from dsp.render_m2_signalsmith import (  # noqa: E402
    _write_result, RESULTS_RENDERED, RESULTS_META, RESULTS_RENDERED_CLEAN, RESULTS_META_CLEAN,
)

SCENARIOS = ["R3-A", "R3-B", "R3-C", "R3-D"]

# The exact (scenario, method) cells the owner-listening pack draws from
# (scripts/build_listening_pack.py's SCENARIO_PLAN) -- only these need a
# CLEAN render; every other cell only needs the diagnostic render.
CLEAN_CELLS_NEEDED = {
    ("R3-A", "M1"), ("R3-B", "M1"), ("R3-C", "M1"), ("R3-D", "M1"),
    ("R3-D", "M0"),
}


def render_one(mod, name, tid, variant):
    t0 = time.perf_counter()
    audio, sr, meta = mod.render(tid, variant)
    wall_s = time.perf_counter() - t0
    meta["render_wall_time_s"] = wall_s
    meta["real_time_factor"] = wall_s / meta["output_duration_s"] if meta["output_duration_s"] else None
    out_dir = RESULTS_RENDERED if variant == "diagnostic" else RESULTS_RENDERED_CLEAN
    meta_dir = RESULTS_META if variant == "diagnostic" else RESULTS_META_CLEAN
    _write_result(tid, name, audio, sr, meta, out_dir, meta_dir)
    print(f"{tid} {name} [{variant}]: wrote render, wall={wall_s:.3f}s rtf={meta['real_time_factor']:.4f} sr={sr}")


def main():
    for tid in SCENARIOS:
        for mod, name in [(render_m0, "M0"), (render_m1, "M1")]:
            render_one(mod, name, tid, "diagnostic")
            if (tid, name) in CLEAN_CELLS_NEEDED:
                render_one(mod, name, tid, "clean")


if __name__ == "__main__":
    main()
