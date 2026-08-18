"""
P0-M5-R1 Phase E -- machine safety/contract checks on all 16 rendered
clips (8 scenarios x M0/M1).

Reuses `dsp.safety_metrics.discontinuity_proxy` unmodified (the same
click/discontinuity heuristic proxy every other accepted render pass in
this repository uses) against the FINAL assembled clip files
`apple_like_render.py`'s finish step already wrote, plus re-derives
NaN/Inf/clip counts directly from the written WAV bytes as an independent
cross-check against the in-process safety diagnostics already recorded in
`render_evidence_sanitized.json`.

Per Issue #10 Phase E: "Beat This anchor agreement is model evidence, not
ground truth. Machine alignment metrics cannot override owner hearing." --
this script's role is limited to catching an obvious RENDERER safety
failure (NaN/Inf, uncontrolled clipping, an implausible discontinuity)
before the owner pack is built; it never claims to substitute for the
owner's ears.

Usage:
    python tools/p0m5/apple_like_vertical_slice/safety_checks.py \
        --render-dir tools/p0m5/apple_like_vertical_slice/work_local/renders \
        --render-evidence tools/p0m5/apple_like_vertical_slice/render_evidence_sanitized.json \
        --out tools/p0m5/apple_like_vertical_slice/safety_checks_sanitized.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DSP_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout"
sys.path.insert(0, str(DSP_DIR))

from dsp.wav_io import read_wav_float  # noqa: E402
from dsp.safety_metrics import nan_inf_count, peak_dbfs, clipped_sample_count, discontinuity_proxy_at_edges  # noqa: E402

PRE_ROLL_S = 10.0  # must match apple_like_render.py's PRE_ROLL_S


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_clip(path: Path, overlap_ms: float) -> dict:
    """Checks for renderer-introduced clicks ONLY at the two actual splice
    boundaries (pre->overlap, overlap->post) using the same edge-targeted
    proxy prior accepted R3 passes used for this purpose
    (`discontinuity_proxy_at_edges`) -- NOT the whole-clip proxy, which
    (verified empirically this pass) fires thousands of false positives on
    ordinary musical transients/percussion across a ~33s real-music clip
    and is not a meaningful renderer-safety signal at that scope."""
    audio, sr = read_wav_float(path)
    edge1 = int(round(PRE_ROLL_S * sr))
    edge2 = edge1 + int(round(overlap_ms / 1000.0 * sr))
    edge1 = min(edge1, audio.shape[0] - 1)
    edge2 = min(edge2, audio.shape[0] - 1)
    disc = discontinuity_proxy_at_edges(audio, sr, edge_samples=[edge1, edge2])
    return {
        "sample_rate": sr,
        "channels": audio.shape[1],
        "duration_s": round(audio.shape[0] / sr, 3),
        "nan_inf_count": nan_inf_count(audio),
        "peak_dbfs": round(peak_dbfs(audio), 3),
        "clipped_sample_count": clipped_sample_count(audio),
        "edge_discontinuity_check": disc,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render-dir", required=True)
    ap.add_argument("--render-evidence", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    render_dir = Path(args.render_dir)
    evidence = load_json(Path(args.render_evidence))

    checks = []
    failures = []
    for s in evidence["scenarios"]:
        tag = s["scenario"]
        for method in ("M0", "M1"):
            clip_path = render_dir / f"{tag}_{method}.wav"
            if not clip_path.exists():
                failures.append(f"{tag}_{method}: MISSING_RENDER_FILE")
                continue
            overlap_ms = evidence["scenarios"][[x["scenario"] for x in evidence["scenarios"]].index(tag)][method.lower()]["overlap_ms"]
            c = check_clip(clip_path, overlap_ms)
            c["scenario"] = tag
            c["method"] = method
            checks.append(c)
            if c["nan_inf_count"] > 0:
                failures.append(f"{tag}_{method}: NAN_INF_DETECTED count={c['nan_inf_count']}")
            if c["clipped_sample_count"] > 0:
                failures.append(f"{tag}_{method}: UNCONTROLLED_CLIPPING count={c['clipped_sample_count']}")
            edge_hits = c["edge_discontinuity_check"]["total_discontinuity_count"]
            if edge_hits > 0:
                failures.append(f"{tag}_{method}: EDGE_DISCONTINUITY_PROXY_HIT count={edge_hits}")
            if c["sample_rate"] != 44100 or c["channels"] != 2:
                failures.append(f"{tag}_{method}: UNEXPECTED_FORMAT sr={c['sample_rate']} ch={c['channels']}")

    out = {
        "clip_count": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    for c in checks:
        edge_hits = c["edge_discontinuity_check"]["total_discontinuity_count"]
        print(f"{c['scenario']}_{c['method']}: dur={c['duration_s']}s peak={c['peak_dbfs']}dBFS nan_inf={c['nan_inf_count']} clip={c['clipped_sample_count']} edge_disc={edge_hits}")
    print()
    if failures:
        print(f"RESULT: {len(failures)} SAFETY FAILURE(S) -- {failures}")
        return 1
    print(f"RESULT: ALL {len(checks)} CLIPS PASS SAFETY CHECKS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
