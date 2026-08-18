"""
P0-M5-R1 Phase E -- machine safety/contract checks on all rendered clips
(8 scenarios x M0/M1).

REPAIR PASS (PM review, Issue #10 comment `5322363724`,
`P0_M5_R1_PRELISTEN_REPAIR_REQUIRED`, BLOCKER 4): the prior pass promoted
ANY hit from the windowed edge proxy (`discontinuity_proxy_at_edges`,
scanning a full 50ms window around each splice) to a hard failure. That
proxy is explicitly documented upstream as a heuristic, not a perceptual
click detector, and a legitimate kick/snare transient landing near (not
AT) a splice boundary can trip it without any renderer defect being
present -- the prior pass's own `VALIDATION_OUTPUT.txt` showed exactly
this (`RESULT: 9 SAFETY FAILURE(S)`) while the report still called the
pack "machine-verified and ready", which PM correctly flagged as
self-contradictory.

Repaired:
  - the windowed edge proxy is now DIAGNOSTIC ONLY -- always computed and
    reported, NEVER added to `failures`/the exit code;
  - a NEW exact-splice hard check (`exact_splice_check`) evaluates the
    ACTUAL single-sample discontinuity at `edge-1 -> edge` (per the two
    real internal render boundaries), normalized (robust z-score) against
    LOCAL sample-delta statistics computed from a surrounding window that
    EXCLUDES the seam itself (so the seam sample can never inflate its
    own baseline and hide a real defect, and an ordinary nearby transient
    the proxy would have flagged does not by itself fail this check,
    since it is not increasing the specific edge-1->edge delta beyond
    local statistics) -- this is a hard failure;
  - hard failures remain: NaN/Inf, uncontrolled clipping, wrong sample-
    rate/channels, an M1 duration-contract defect (BLOCKER 2, cross-
    checked against `render_evidence_sanitized.json`'s own
    `duration_contract_ok` field AND independently re-verified against
    the written WAV file's actual duration here), and genuine exact-
    splice discontinuity;
  - this script now genuinely exits 0 when no hard failure exists --
    verified by actually running it after each repair, not asserted.

Per Issue #10 Phase E: "Beat This anchor agreement is model evidence, not
ground truth. Machine alignment metrics cannot override owner hearing." --
this script's role remains limited to catching an obvious RENDERER defect
before the owner pack is built; it never substitutes for the owner's ears.

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

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DSP_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout"
sys.path.insert(0, str(DSP_DIR))

from dsp.wav_io import read_wav_float  # noqa: E402
from dsp.safety_metrics import nan_inf_count, peak_dbfs, clipped_sample_count, discontinuity_proxy_at_edges  # noqa: E402

PRE_ROLL_S = 10.0  # must match apple_like_render.py's PRE_ROLL_S
DIAGNOSTIC_EDGE_WINDOW_MS = 50.0  # unchanged windowed-proxy scope, diagnostic only now
EXACT_SPLICE_BASELINE_WINDOW_MS = 50.0
EXACT_SPLICE_EXCLUDE_RADIUS_SAMPLES = 3
EXACT_SPLICE_Z_THRESHOLD = 8.0  # same convention as the rest of dsp/safety_metrics.py
DURATION_TOLERANCE_S = 0.02  # WAV-file-level cross-check tolerance, deliberately looser than the in-process 0.01s contract tolerance (accounts for float32 WAV round-trip)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def exact_splice_check(audio: np.ndarray, sr: int, edge_sample: int,
                        baseline_window_ms: float = EXACT_SPLICE_BASELINE_WINDOW_MS,
                        exclude_radius: int = EXACT_SPLICE_EXCLUDE_RADIUS_SAMPLES,
                        z_threshold: float = EXACT_SPLICE_Z_THRESHOLD) -> dict:
    """PM repair (BLOCKER 4): the actual `edge-1 -> edge` sample delta,
    normalized against LOCAL sample-delta statistics that EXCLUDE the
    seam itself. This is a precise, single-point check -- not a window
    scan -- so an ordinary transient sitting NEAR (not exactly at) the
    boundary cannot trip it the way the old windowed proxy could."""
    mono = audio.mean(axis=1) if audio.ndim == 2 else audio
    if edge_sample <= 0 or edge_sample >= len(mono):
        return {"edge_sample": edge_sample, "splice_delta": 0.0, "baseline_median": 0.0, "z_score": 0.0, "is_discontinuity": False, "note": "EDGE_OUT_OF_RANGE"}

    splice_delta = float(abs(mono[edge_sample] - mono[edge_sample - 1]))

    half_win = max(exclude_radius + 8, int(round(baseline_window_ms / 1000.0 * sr / 2)))
    lo = max(0, edge_sample - half_win)
    hi = min(len(mono), edge_sample + half_win)
    segment = mono[lo:hi]
    if segment.size < 3:
        return {"edge_sample": edge_sample, "splice_delta": splice_delta, "baseline_median": 0.0, "z_score": 0.0, "is_discontinuity": False, "note": "INSUFFICIENT_BASELINE_SAMPLES"}

    deltas = np.abs(np.diff(segment))
    # deltas[k] == |segment[k+1] - segment[k]|; the splice delta itself is
    # deltas[edge_idx] where edge_idx corresponds to (edge_sample-1, edge_sample).
    edge_idx = (edge_sample - 1) - lo
    mask = np.ones(len(deltas), dtype=bool)
    for off in range(-exclude_radius, exclude_radius + 1):
        idx = edge_idx + off
        if 0 <= idx < len(mask):
            mask[idx] = False
    baseline = deltas[mask]
    if baseline.size < 8:
        return {"edge_sample": edge_sample, "splice_delta": splice_delta, "baseline_median": 0.0, "z_score": 0.0, "is_discontinuity": False, "note": "INSUFFICIENT_BASELINE_SAMPLES"}

    median = float(np.median(baseline))
    mad = float(np.median(np.abs(baseline - median))) + 1e-9
    z = abs(splice_delta - median) / (1.4826 * mad)
    return {
        "edge_sample": edge_sample,
        "splice_delta": splice_delta,
        "baseline_median": median,
        "z_score": round(float(z), 3),
        "is_discontinuity": bool(z > z_threshold),
        "note": None,
    }


def check_clip(path: Path, overlap_ms: float) -> dict:
    audio, sr = read_wav_float(path)
    edge1 = int(round(PRE_ROLL_S * sr))
    edge2 = edge1 + int(round(overlap_ms / 1000.0 * sr))
    edge1 = min(edge1, audio.shape[0] - 1)
    edge2 = min(edge2, audio.shape[0] - 1)

    diagnostic = discontinuity_proxy_at_edges(audio, sr, edge_samples=[edge1, edge2], window_ms=DIAGNOSTIC_EDGE_WINDOW_MS)
    exact_edge1 = exact_splice_check(audio, sr, edge1)
    exact_edge2 = exact_splice_check(audio, sr, edge2)

    return {
        "sample_rate": sr,
        "channels": audio.shape[1],
        "duration_s": round(audio.shape[0] / sr, 3),
        "nan_inf_count": nan_inf_count(audio),
        "peak_dbfs": round(peak_dbfs(audio), 3),
        "clipped_sample_count": clipped_sample_count(audio),
        "diagnostic_windowed_edge_proxy": diagnostic,  # DIAGNOSTIC ONLY -- never a hard failure (BLOCKER 4)
        "exact_splice_check": {"edge1": exact_edge1, "edge2": exact_edge2},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render-dir", required=True)
    ap.add_argument("--render-evidence", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    render_dir = Path(args.render_dir)
    evidence = load_json(Path(args.render_evidence))
    scenario_by_tag = {s["scenario"]: s for s in evidence["scenarios"]}

    checks = []
    failures = []
    warnings = []
    for tag, s in scenario_by_tag.items():
        if s["status"] != "SUCCESS":
            failures.append(f"{tag}: SCENARIO_NOT_SUCCESSFUL status={s['status']}")
            continue
        for method in ("M0", "M1"):
            clip_path = render_dir / f"{tag}_{method}.wav"
            if not clip_path.exists():
                failures.append(f"{tag}_{method}: MISSING_RENDER_FILE")
                continue

            method_evidence = s[method.lower()]
            overlap_ms = method_evidence["overlap_ms"]
            c = check_clip(clip_path, overlap_ms)
            c["scenario"] = tag
            c["method"] = method
            checks.append(c)

            if c["nan_inf_count"] > 0:
                failures.append(f"{tag}_{method}: NAN_INF_DETECTED count={c['nan_inf_count']}")
            if c["clipped_sample_count"] > 0:
                failures.append(f"{tag}_{method}: UNCONTROLLED_CLIPPING count={c['clipped_sample_count']}")
            if c["sample_rate"] != 44100 or c["channels"] != 2:
                failures.append(f"{tag}_{method}: UNEXPECTED_FORMAT sr={c['sample_rate']} ch={c['channels']}")

            diag_hits = c["diagnostic_windowed_edge_proxy"]["total_discontinuity_count"]
            if diag_hits > 0:
                warnings.append(f"{tag}_{method}: diagnostic windowed-edge-proxy hit count={diag_hits} (NOT a hard failure -- heuristic proxy, see module docstring)")

            for edge_name, edge_result in c["exact_splice_check"].items():
                if edge_result["is_discontinuity"]:
                    failures.append(f"{tag}_{method}: EXACT_SPLICE_DISCONTINUITY at {edge_name} z_score={edge_result['z_score']}")

            # BLOCKER 2 cross-check: M1's in-process duration-contract flag,
            # plus an independent re-verification against the actual
            # written WAV duration vs. the evidence's own recorded value.
            if method == "M1" and not method_evidence.get("duration_contract_ok", True):
                failures.append(f"{tag}_{method}: DURATION_CONTRACT_DEFECT (recorded at render time) detail={method_evidence.get('duration_contract_detail')}")

            expected_duration_s = method_evidence.get("output_duration_s")
            if expected_duration_s is not None and abs(c["duration_s"] - expected_duration_s) > DURATION_TOLERANCE_S:
                failures.append(f"{tag}_{method}: DURATION_CONTRACT_DEFECT file_duration={c['duration_s']} != recorded={expected_duration_s} (tolerance={DURATION_TOLERANCE_S})")

    out = {
        "clip_count": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "warning_count": len(warnings),
        "warnings": warnings,
        "checks": checks,
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    for c in checks:
        diag_hits = c["diagnostic_windowed_edge_proxy"]["total_discontinuity_count"]
        e1z = c["exact_splice_check"]["edge1"]["z_score"]
        e2z = c["exact_splice_check"]["edge2"]["z_score"]
        print(f"{c['scenario']}_{c['method']}: dur={c['duration_s']}s peak={c['peak_dbfs']}dBFS nan_inf={c['nan_inf_count']} clip={c['clipped_sample_count']} "
              f"exact_splice_z=[{e1z},{e2z}] diagnostic_proxy_hits={diag_hits}")
    print()
    if warnings:
        print(f"DIAGNOSTIC WARNINGS ({len(warnings)}, non-blocking): {warnings}")
        print()
    if failures:
        print(f"RESULT: {len(failures)} SAFETY FAILURE(S) -- {failures}")
        return 1
    print(f"RESULT: ALL {len(checks)} CLIPS PASS SAFETY CHECKS (0 hard failures, {len(warnings)} non-blocking diagnostic warnings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
