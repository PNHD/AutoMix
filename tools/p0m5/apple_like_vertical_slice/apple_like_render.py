"""
P0-M5-R1 Phase D -- M0 (simple baseline) / M1 (APPLE_LIKE_V1) render for the
8 frozen pairs.

Reuses, unmodified: `dsp.wav_io.read_wav_float/write_wav_float32`,
`dsp.mixing.assemble_transition_render`/`apply_headroom_and_safety`
(the same equal-power gain law + bass-handoff machinery every other
accepted method in this repository uses), and the existing accepted
browser-driven Signalsmith Stretch bridge (`web/stretch_worker.html` +
`scripts/serve.py`, official pinned `SignalsmithStretch.mjs`, no new
stretcher implementation) for the ONE new thing this task's M1 candidate
needs: stretching the OUTGOING tail (not the incoming track, unlike the
existing R3 M2 method) so the incoming track is never permanently
retimed.

Two-phase pattern (mirrors `dsp/render_m2_signalsmith.py`'s prepare/finish
split, required because a real Web Audio API is not available in plain
Python):

    prepare  -- for each of the 8 frozen pairs, writes the raw outgoing
                tail segment that needs stretching to `serve_tmp/`, and
                emits the exact stretch_worker.html job URL (driven by an
                external browser-automation step -- not this script).
    finish   -- after the browser jobs have completed and uploaded their
                stretched output + sidecar back to `serve_tmp/`, assembles
                the final M0 and M1 clips and writes sanitized machine
                evidence.

M1 algorithm (Issue #10 Phase D):
    - transition window: an integer number of bars (from the OUTGOING
      side's bar period at the exit anchor) targeting ~12s, clamped to
      [8, 16]s;
    - outgoing tail (of that window length, starting exactly at the
      snapped exit downbeat) is stretched by `rate = tempo_ratio` (the
      pair's cached `incoming_local_bpm / outgoing_local_bpm`, already
      bounded to within 6% by Phase C's hard eligibility gate) via the
      browser Signalsmith bridge;
    - the incoming overlap is taken UNSTRETCHED, starting exactly at its
      own snapped entry downbeat, for exactly the stretched tail's
      resulting duration -- both sides' segment starts ARE their downbeat
      anchors by construction, so beat alignment is definitional (offset
      0), not a computed shift;
    - equal-power gain law, WITH the existing accepted bass-handoff EQ
      swap (`use_bass_handoff=True`);
    - after the overlap, incoming continues from unstretched native audio
      -- it is never touched beyond the overlap slice, so it can never be
      left "permanently stretched."

M0 algorithm: the SAME exit/entry anchors and SAME window length (same
source pair, same broad transition region, same preservation intent) but
NO stretch (outgoing tail and incoming overlap both natural-tempo, same
window length), NO bass handoff, equal-power gain only -- i.e. exactly
`dsp/render_m1.py`'s existing "do less" reference, just at this pair's
specific anchors instead of a synthetic fixture's.

Usage:
    python tools/p0m5/apple_like_vertical_slice/apple_like_render.py prepare \
        --pair-manifest tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json \
        --serve-tmp tools/p0m3/audio_render_shootout/serve_tmp \
        --jobs-out tools/p0m5/apple_like_vertical_slice/work_local/m1_stretch_jobs.json

    # (external: drive each job's URL in a real browser until DONE)

    python tools/p0m5/apple_like_vertical_slice/apple_like_render.py finish \
        --pair-manifest tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json \
        --serve-tmp tools/p0m3/audio_render_shootout/serve_tmp \
        --jobs-in tools/p0m5/apple_like_vertical_slice/work_local/m1_stretch_jobs.json \
        --decoded-cache tools/p0m5/apple_like_vertical_slice/work_local/decoded \
        --render-out tools/p0m5/apple_like_vertical_slice/work_local/renders \
        --evidence-out tools/p0m5/apple_like_vertical_slice/render_evidence_sanitized.json
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

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402

CANONICAL_SR = 44100
SERVER_BASE_URL = "http://127.0.0.1:8765"
BLOCK_MS = 120.0
TARGET_WINDOW_S = 12.0
WINDOW_MIN_S = 8.0
WINDOW_MAX_S = 16.0
PRE_ROLL_S = 10.0
POST_ROLL_S = 12.0
# Issue #10 Phase D: "If implementation details require stretching a short
# outgoing pre-roll before overlap to make alignment continuous, do so
# deterministically and record it." Measured this pass (safety_checks.py):
# splicing UNPROCESSED outgoing_pre directly against Signalsmith-processed
# tail (even at rate=1.0) produces a measurable edge-discontinuity-proxy
# hit at that internal seam -- the phase-vocoder analysis/resynthesis
# cycle is not bit-identical to the raw signal even in near-identity mode,
# and a cold-started filter/window state at the very first processed
# sample makes it worse. Fix: feed the stretch job WARMUP_S extra seconds
# of context immediately before the true window start, then discard the
# corresponding (rate-scaled) warm-up portion of the processed output
# before using it -- the algorithm has "seen" continuous prior context by
# the time the retained audio begins, and the true splice point coincides
# with fully-settled processing.
WARMUP_S = 1.0


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ms_to_smp(ms_or_s: float, sr: int, is_ms: bool = False) -> int:
    s = ms_or_s / 1000.0 if is_ms else ms_or_s
    return int(round(s * sr))


def choose_window_bars(bar_period_s: float) -> tuple[int, float]:
    if bar_period_s <= 0:
        return 1, TARGET_WINDOW_S
    bars = max(1, round(TARGET_WINDOW_S / bar_period_s))
    window_s = bars * bar_period_s
    # Nudge to the [8,16]s envelope deterministically if the initial guess
    # lands outside it (e.g. very slow/fast local tempo).
    while window_s < WINDOW_MIN_S and bars < 64:
        bars += 1
        window_s = bars * bar_period_s
    while window_s > WINDOW_MAX_S and bars > 1:
        bars -= 1
        window_s = bars * bar_period_s
    return bars, window_s


def scenario_tag(index: int) -> str:
    return f"S{index:02d}"


def prepare(args) -> int:
    manifest = load_json(Path(args.pair_manifest))
    if manifest.get("status") != "FROZEN":
        print(f"RESULT: BLOCKED -- pair manifest status {manifest.get('status')!r}, not FROZEN")
        return 1

    decoded_dir = Path(args.decoded_cache) if args.decoded_cache else HERE / "work_local" / "decoded"
    serve_tmp = Path(args.serve_tmp)
    serve_tmp.mkdir(parents=True, exist_ok=True)

    jobs = []
    for idx, pair in enumerate(manifest["pairs"], start=1):
        tag = scenario_tag(idx)
        out_id, in_id = pair["out_id"], pair["in_id"]
        out_audio, sr = read_wav_float(decoded_dir / f"{out_id}.wav")
        assert sr == CANONICAL_SR

        exit_smp = ms_to_smp(pair["exit_anchor_s"], sr)
        bar_period_s = 60.0 / pair["outgoing_local_bpm"] if pair["outgoing_local_bpm"] else 2.0
        bars, window_s = choose_window_bars(bar_period_s)
        window_smp = ms_to_smp(window_s, sr)

        warmup_smp = min(exit_smp, ms_to_smp(WARMUP_S, sr))
        tail_with_warmup = out_audio[exit_smp - warmup_smp: exit_smp + window_smp]
        actual_window_s = (tail_with_warmup.shape[0] - warmup_smp) / sr  # honest -- may be shorter if track ends early

        rate = pair["tempo_ratio"]
        input_name = f"apple_v1_{tag}_m1_input.wav"
        output_name = f"apple_v1_{tag}_m1_output.wav"
        sidecar_name = f"apple_v1_{tag}_m1_sidecar.json"
        write_wav_float32(serve_tmp / input_name, tail_with_warmup, sr)

        job = {
            "scenario": tag,
            "out_id": out_id,
            "in_id": in_id,
            "sr": sr,
            "rate": rate,
            "window_bars": bars,
            "requested_window_s": round(window_s, 3),
            "actual_window_s": round(actual_window_s, 3),
            "warmup_input_samples": int(warmup_smp),
            "input_name": input_name,
            "output_name": output_name,
            "sidecar_name": sidecar_name,
            "url": (
                f"{SERVER_BASE_URL}/web/stretch_worker.html?"
                f"input=/serve_tmp/{input_name}&rate={rate}&semitones=0"
                f"&output={output_name}&blockMs={BLOCK_MS}&tailPadS=0.5"
                f"&expectedSampleRate={sr}&sidecar={sidecar_name}"
            ),
        }
        jobs.append(job)
        print(f"{tag}: window={actual_window_s:.2f}s ({bars} bars) rate={rate} url={job['url']}")

    Path(args.jobs_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.jobs_out).write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    print(f"\nWrote {len(jobs)} M1 stretch jobs to {args.jobs_out}")
    print("Next: drive each job's 'url' in a real browser until its page title reads 'DONE ...', then run 'finish'.")
    return 0


def render_m0(out_audio, in_audio, sr, exit_smp, entry_smp, window_smp):
    pre_start = max(0, exit_smp - ms_to_smp(PRE_ROLL_S, sr))
    outgoing_pre = out_audio[pre_start:exit_smp]
    outgoing_overlap = out_audio[exit_smp: exit_smp + window_smp]
    n = outgoing_overlap.shape[0]
    incoming_overlap = in_audio[entry_smp: entry_smp + n]
    if incoming_overlap.shape[0] < n:
        pad = __import__("numpy").zeros((n - incoming_overlap.shape[0], incoming_overlap.shape[1]), dtype=incoming_overlap.dtype)
        incoming_overlap = __import__("numpy").concatenate([incoming_overlap, pad], axis=0)
    incoming_post = in_audio[entry_smp + n: entry_smp + n + ms_to_smp(POST_ROLL_S, sr)]

    rendered = assemble_transition_render(
        outgoing_pre, outgoing_overlap, incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=False, curve="equal_power",
    )
    safe_audio, safety = apply_headroom_and_safety(rendered)
    return safe_audio, safety, {
        "overlap_ms": n / sr * 1000.0,
        "applied_tempo_ratio": 1.0,
        "beat_alignment_applied": False,
        "bass_eq_handoff_applied": False,
    }


def render_m1(out_audio, in_audio, sr, exit_smp, entry_smp, stretched_tail, rate):
    import numpy as np
    pre_start = max(0, exit_smp - ms_to_smp(PRE_ROLL_S, sr))
    outgoing_pre = out_audio[pre_start:exit_smp]
    n = stretched_tail.shape[0]
    incoming_overlap = in_audio[entry_smp: entry_smp + n]
    if incoming_overlap.shape[0] < n:
        pad = np.zeros((n - incoming_overlap.shape[0], incoming_overlap.shape[1]), dtype=incoming_overlap.dtype)
        incoming_overlap = np.concatenate([incoming_overlap, pad], axis=0)
    incoming_post = in_audio[entry_smp + n: entry_smp + n + ms_to_smp(POST_ROLL_S, sr)]

    rendered = assemble_transition_render(
        outgoing_pre, stretched_tail, incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=True, curve="equal_power",
    )
    safe_audio, safety = apply_headroom_and_safety(rendered)
    return safe_audio, safety, {
        "overlap_ms": n / sr * 1000.0,
        "applied_tempo_ratio": rate,
        "beat_alignment_applied": True,
        "bass_eq_handoff_applied": True,
    }


def finish(args) -> int:
    import numpy as np
    manifest = load_json(Path(args.pair_manifest))
    jobs = {j["scenario"]: j for j in load_json(Path(args.jobs_in))}
    decoded_dir = Path(args.decoded_cache) if args.decoded_cache else HERE / "work_local" / "decoded"
    serve_tmp = Path(args.serve_tmp)
    render_out = Path(args.render_out)
    render_out.mkdir(parents=True, exist_ok=True)

    evidence = []
    for idx, pair in enumerate(manifest["pairs"], start=1):
        tag = scenario_tag(idx)
        job = jobs[tag]
        out_id, in_id = pair["out_id"], pair["in_id"]

        out_audio, sr = read_wav_float(decoded_dir / f"{out_id}.wav")
        in_audio, sr2 = read_wav_float(decoded_dir / f"{in_id}.wav")
        assert sr == sr2 == CANONICAL_SR

        exit_smp = ms_to_smp(pair["exit_anchor_s"], sr)
        entry_smp = ms_to_smp(pair["entry_anchor_s"], sr)
        # M0 deliberately uses the RAW (un-snapped) R2 candidate points --
        # not the beat-snapped anchors -- so "no beat/downbeat alignment"
        # (Issue #10 Phase D M0 spec) is a genuine property of the M0
        # render, not merely inherited from M1's beat-aware placement.
        exit_smp_m0 = ms_to_smp(pair["exit_anchor_raw_s"], sr)
        entry_smp_m0 = ms_to_smp(pair["entry_anchor_raw_s"], sr)
        bar_period_s = 60.0 / pair["outgoing_local_bpm"] if pair["outgoing_local_bpm"] else 2.0
        bars, window_s = choose_window_bars(bar_period_s)
        window_smp = ms_to_smp(window_s, sr)

        # --- M0 ---
        m0_audio, m0_safety, m0_meta = render_m0(out_audio, in_audio, sr, exit_smp_m0, entry_smp_m0, window_smp)
        write_wav_float32(render_out / f"{tag}_M0.wav", m0_audio, sr)

        # --- M1 ---
        output_path = serve_tmp / job["output_name"]
        sidecar_path = serve_tmp / job["sidecar_name"]
        if not output_path.exists() or not sidecar_path.exists():
            evidence.append({"scenario": tag, "status": "M1_STRETCH_JOB_NOT_FINISHED", "out_id": out_id, "in_id": in_id})
            print(f"{tag}: M1 BLOCKED -- stretch job output/sidecar not found (browser job not finished)")
            continue
        stretched, sr_out = read_wav_float(output_path)
        sidecar = load_json(sidecar_path)
        if sr_out != CANONICAL_SR:
            evidence.append({"scenario": tag, "status": "M1_SAMPLE_RATE_MISMATCH", "out_id": out_id, "in_id": in_id})
            print(f"{tag}: M1 BLOCKED -- output sample rate {sr_out} != {CANONICAL_SR}")
            continue

        # Discard the rate-scaled warm-up portion (see WARMUP_S docstring
        # above) -- the retained stretched_tail begins exactly at the true
        # window start, with the algorithm's internal state already
        # settled from the discarded warm-up context.
        warmup_out_smp = int(round(job.get("warmup_input_samples", 0) / job["rate"]))
        stretched_tail = stretched[warmup_out_smp:]

        m1_audio, m1_safety, m1_meta = render_m1(out_audio, in_audio, sr, exit_smp, entry_smp, stretched_tail, job["rate"])
        write_wav_float32(render_out / f"{tag}_M1.wav", m1_audio, sr)

        evidence.append({
            "scenario": tag,
            "status": "SUCCESS",
            "out_id": out_id,
            "in_id": in_id,
            "split": pair["split"],
            "window_bars": bars,
            "requested_window_s": round(window_s, 3),
            "m0": {
                "overlap_ms": m0_meta["overlap_ms"],
                "applied_tempo_ratio": m0_meta["applied_tempo_ratio"],
                "beat_alignment_applied": m0_meta["beat_alignment_applied"],
                "bass_eq_handoff_applied": m0_meta["bass_eq_handoff_applied"],
                "safety": {k: m0_safety[k] for k in ("pre_peak_dbfs", "post_peak_dbfs", "applied_headroom_gain_db", "nan_inf_sample_count", "clipped_sample_count")},
                "output_duration_s": m0_audio.shape[0] / sr,
            },
            "m1": {
                "overlap_ms": m1_meta["overlap_ms"],
                "applied_tempo_ratio": m1_meta["applied_tempo_ratio"],
                "beat_alignment_applied": m1_meta["beat_alignment_applied"],
                "bass_eq_handoff_applied": m1_meta["bass_eq_handoff_applied"],
                "stretch_engine_latency_s": sidecar.get("stretch_latency_s"),
                "stretch_requested_rate": sidecar.get("requested_tempo_rate"),
                "stretch_sample_rate_assertions_passed": sidecar.get("sample_rate_assertions_passed"),
                "safety": {k: m1_safety[k] for k in ("pre_peak_dbfs", "post_peak_dbfs", "applied_headroom_gain_db", "nan_inf_sample_count", "clipped_sample_count")},
                "output_duration_s": m1_audio.shape[0] / sr,
            },
        })
        print(f"{tag}: SUCCESS m0_dur={m0_audio.shape[0]/sr:.1f}s m1_dur={m1_audio.shape[0]/sr:.1f}s rate={job['rate']}")

    out = {
        "scenario_count": len(evidence),
        "success_count": sum(1 for e in evidence if e["status"] == "SUCCESS"),
        "scenarios": evidence,
    }
    Path(args.evidence_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nRESULT: {out['success_count']}/{out['scenario_count']} scenarios rendered. Wrote {args.evidence_out}")
    return 0 if out["success_count"] == out["scenario_count"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--pair-manifest", required=True)
    p_prep.add_argument("--serve-tmp", required=True)
    p_prep.add_argument("--jobs-out", required=True)
    p_prep.add_argument("--decoded-cache", default=None)

    p_fin = sub.add_parser("finish")
    p_fin.add_argument("--pair-manifest", required=True)
    p_fin.add_argument("--serve-tmp", required=True)
    p_fin.add_argument("--jobs-in", required=True)
    p_fin.add_argument("--decoded-cache", default=None)
    p_fin.add_argument("--render-out", required=True)
    p_fin.add_argument("--evidence-out", required=True)

    args = ap.parse_args()
    if args.cmd == "prepare":
        return prepare(args)
    return finish(args)


if __name__ == "__main__":
    raise SystemExit(main())
