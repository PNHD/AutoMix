"""
P0-M5-R1 Phase D -- M0 (simple baseline) / M1 (APPLE_LIKE_V1) render for the
8 frozen pairs.

REPAIR PASS (PM review, Issue #10 comment `5322363724`,
`P0_M5_R1_PRELISTEN_REPAIR_REQUIRED`, BLOCKERS 2 + 3):

  - BLOCKER 3: the prior pass sent EVERY M1 tail through the Signalsmith
    phase-vocoder path, including the 8/8 pairs that (in the unrepaired
    Phase C) needed no correction at all (`rate=1.0`) -- an identity pass
    through analysis/resynthesis is not bit-identical to raw audio and
    introduces an avoidable raw-vs-processed seam. Repaired: Signalsmith
    is now bypassed ENTIRELY whenever `abs(rate - 1.0) <= UNITY_RATE_EPSILON`
    -- the raw, unprocessed outgoing window is used directly as the M1
    tail in that case (`stretch_bypassed=True` recorded honestly).
  - BLOCKER 2: the worker's `tailPadS` (safety/latency headroom for the
    OfflineAudioContext render, requested from the worker but never meant
    to become transition content) was previously left in the retained M1
    program, inflating M1's overlap length relative to M0's by
    `tailPadS` seconds. Repaired: `finish()` now trims the stretched
    output to EXACTLY the expected rate-converted window duration (after
    also discarding the warm-up prefix, unchanged from the prior pass),
    and asserts the retained duration is within a small documented
    tolerance of that expectation before use -- a violation is recorded
    as `M1_DURATION_CONTRACT_DEFECT`, never silently padded/truncated.

Reuses, unmodified: `dsp.wav_io.read_wav_float/write_wav_float32`,
`dsp.mixing.assemble_transition_render`/`apply_headroom_and_safety`, and
(for non-unity-rate pairs only) the existing accepted browser-driven
Signalsmith Stretch bridge (`web/stretch_worker.html` + `scripts/serve.py`,
official pinned `SignalsmithStretch.mjs`, no new stretcher implementation)
to stretch the OUTGOING tail (not the incoming track) so the incoming
track is never permanently retimed.

Two-phase pattern (mirrors `dsp/render_m2_signalsmith.py`'s prepare/finish
split, required because a real Web Audio API is not available in plain
Python):

    prepare  -- for each of the 8 frozen pairs, if the pair needs actual
                stretch (non-unity rate), writes the raw outgoing tail
                (+ warm-up context) to `serve_tmp/` and emits the exact
                stretch_worker.html job URL (driven by an external
                browser-automation step -- not this script). Unity-rate
                pairs get a `"bypass": true` job record and no browser
                work at all.
    finish   -- after any non-bypassed browser jobs have completed and
                uploaded their stretched output + sidecar back to
                `serve_tmp/`, assembles the final M0 and M1 clips and
                writes sanitized machine evidence.

M1 algorithm (Issue #10 Phase D, as repaired):
    - transition window: an integer number of bars (from the OUTGOING
      side's own bar period at the exit anchor -- `outgoing_bar_period_s`,
      a genuine bar-period-in-seconds field, never a bpm-shaped value that
      could be confused with tempo) targeting ~12s, clamped to [8, 16]s;
    - outgoing tail (of that window length, starting exactly at the
      snapped exit downbeat) is stretched by `rate = tempo_ratio` via the
      browser Signalsmith bridge WHEN `rate` is not ~1.0; otherwise the
      raw tail is used directly (BLOCKER 3);
    - the incoming overlap is taken UNSTRETCHED, starting exactly at its
      own snapped entry downbeat, for exactly the (possibly stretched)
      tail's resulting duration -- both sides' segment starts ARE their
      downbeat anchors by construction, so beat alignment is definitional
      (offset 0), not a computed shift;
    - equal-power gain law, WITH the existing accepted bass-handoff EQ
      swap (`use_bass_handoff=True`);
    - after the overlap, incoming continues from unstretched native audio
      -- it is never touched beyond the overlap slice, so it can never be
      left "permanently stretched."

M0 algorithm (unchanged by this repair): the SAME window length (same
source pair, same preservation intent) at the pair's RAW (un-snapped) R2
candidate boundary -- NO stretch, NO bass handoff, equal-power gain only.

Usage:
    python tools/p0m5/apple_like_vertical_slice/apple_like_render.py prepare \
        --pair-manifest tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json \
        --serve-tmp tools/p0m3/audio_render_shootout/serve_tmp \
        --jobs-out tools/p0m5/apple_like_vertical_slice/work_local/m1_stretch_jobs.json

    # (external: drive each NON-bypassed job's URL in a real browser until DONE)

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

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DSP_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout"

sys.path.insert(0, str(DSP_DIR))

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety, equal_power_gains  # noqa: E402

CANONICAL_SR = 44100
SERVER_BASE_URL = "http://127.0.0.1:8765"
BLOCK_MS = 120.0
TARGET_WINDOW_S = 12.0
WINDOW_MIN_S = 8.0
WINDOW_MAX_S = 16.0
PRE_ROLL_S = 10.0
POST_ROLL_S = 12.0
WARMUP_S = 1.0  # see module docstring / prior-pass safety_checks.py finding
TAIL_PAD_S_REQUESTED = 0.5  # worker plumbing only -- BLOCKER 2: never retained past finish()'s trim
# BLOCKER 3: Signalsmith is bypassed entirely at/below this rate deviation.
# Tight enough that no genuine stretch-cover pair (>=2% by Phase C design)
# can ever accidentally bypass; loose enough to treat float round-trip
# noise around an exact 1.0 as still "unity".
UNITY_RATE_EPSILON = 0.001
# BLOCKER 2: tolerance for the retained-processed-program duration
# assertion, documented and fixed -- not tuned per pair.
DURATION_CONTRACT_TOLERANCE_S = 0.01


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
        bar_period_s = pair["outgoing_bar_period_s"] if pair.get("outgoing_bar_period_s") else 2.0
        bars, window_s = choose_window_bars(bar_period_s)
        window_smp = ms_to_smp(window_s, sr)
        rate = pair["tempo_ratio"]

        bypass = abs(rate - 1.0) <= UNITY_RATE_EPSILON
        if bypass:
            jobs.append({
                "scenario": tag, "out_id": out_id, "in_id": in_id, "sr": sr, "rate": rate,
                "window_bars": bars, "requested_window_s": round(window_s, 3),
                "bypass": True,
            })
            print(f"{tag}: rate={rate} within +/-{UNITY_RATE_EPSILON} of unity -- Signalsmith BYPASSED (BLOCKER 3)")
            continue

        warmup_smp = min(exit_smp, ms_to_smp(WARMUP_S, sr))
        tail_with_warmup = out_audio[exit_smp - warmup_smp: exit_smp + window_smp]
        actual_window_s = (tail_with_warmup.shape[0] - warmup_smp) / sr  # honest -- may be shorter if track ends early

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
            "bypass": False,
            "window_bars": bars,
            "requested_window_s": round(window_s, 3),
            "actual_window_s": round(actual_window_s, 3),
            "warmup_input_samples": int(warmup_smp),
            "window_input_samples": int(window_smp),
            "input_name": input_name,
            "output_name": output_name,
            "sidecar_name": sidecar_name,
            "url": (
                f"{SERVER_BASE_URL}/web/stretch_worker.html?"
                f"input=/serve_tmp/{input_name}&rate={rate}&semitones=0"
                f"&output={output_name}&blockMs={BLOCK_MS}&tailPadS={TAIL_PAD_S_REQUESTED}"
                f"&expectedSampleRate={sr}&sidecar={sidecar_name}"
            ),
        }
        jobs.append(job)
        print(f"{tag}: window={actual_window_s:.2f}s ({bars} bars) rate={rate} url={job['url']}")

    Path(args.jobs_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.jobs_out).write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    non_bypassed = sum(1 for j in jobs if not j["bypass"])
    print(f"\nWrote {len(jobs)} job records to {args.jobs_out} ({non_bypassed} require an actual browser stretch job, {len(jobs) - non_bypassed} bypassed).")
    if non_bypassed:
        print("Next: drive each non-bypassed job's 'url' in a real browser until its page title reads 'DONE ...', then run 'finish'.")
    else:
        print("Next: no browser jobs needed -- run 'finish' directly.")
    return 0


def render_m0(out_audio, in_audio, sr, exit_smp, entry_smp, window_smp):
    pre_start = max(0, exit_smp - ms_to_smp(PRE_ROLL_S, sr))
    outgoing_pre = out_audio[pre_start:exit_smp]
    outgoing_overlap = out_audio[exit_smp: exit_smp + window_smp]
    n = outgoing_overlap.shape[0]
    incoming_overlap = in_audio[entry_smp: entry_smp + n]
    if incoming_overlap.shape[0] < n:
        pad = np.zeros((n - incoming_overlap.shape[0], incoming_overlap.shape[1]), dtype=incoming_overlap.dtype)
        incoming_overlap = np.concatenate([incoming_overlap, pad], axis=0)
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


def micro_splice_fade(raw_tail: np.ndarray, processed_head: np.ndarray, fade_smp: int) -> np.ndarray:
    """PM re-review finding (this repair pass): even after correctly
    trimming warm-up + the Signalsmith node's own reported processing
    latency, a real, measurable amplitude discontinuity remains exactly at
    the raw-audio/processed-audio splice (z~12-15, a ~0.6-amplitude jump
    against a ~0.04 local baseline) -- an inherent property of splicing
    directly-decoded PCM against phase-vocoder analysis/resynthesis
    output, not a further timing offset to hunt for. The correct,
    standard fix is a short internal equal-power blend AT the seam itself
    (the same public-domain `equal_power_gains` primitive already used
    for every crossfade in this codebase, reused here for a `fade_smp`
    micro-splice, not a new DSP technique) rather than expecting a hard
    cut between two differently-reconstructed signals to be seamless."""
    fade_smp = min(fade_smp, raw_tail.shape[0], processed_head.shape[0])
    if fade_smp <= 0:
        return processed_head
    g_out, g_in = equal_power_gains(fade_smp)
    blended = raw_tail[-fade_smp:] * g_out[:, None] + processed_head[:fade_smp] * g_in[:, None]
    return np.concatenate([blended, processed_head[fade_smp:]], axis=0)


MICRO_SPLICE_FADE_S = 0.010  # 10ms -- short enough to be inaudible as its own event, long enough to hide the reconstruction seam


def render_m1(out_audio, in_audio, sr, exit_smp, entry_smp, stretched_tail, rate, stretch_bypassed: bool):
    pre_start = max(0, exit_smp - ms_to_smp(PRE_ROLL_S, sr))
    outgoing_pre = out_audio[pre_start:exit_smp]

    if not stretch_bypassed:
        # Only needed when stretched_tail actually went through Signalsmith
        # -- the bypass path uses raw audio contiguous with outgoing_pre,
        # verified defect-free by the exact-splice check (no seam exists).
        fade_smp = ms_to_smp(MICRO_SPLICE_FADE_S, sr)
        stretched_tail = micro_splice_fade(outgoing_pre, stretched_tail, fade_smp)

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
        "stretch_bypassed": stretch_bypassed,
        "micro_splice_fade_applied": not stretch_bypassed,
    }


def finish(args) -> int:
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
        exit_smp_m0 = ms_to_smp(pair["exit_anchor_raw_s"], sr)
        entry_smp_m0 = ms_to_smp(pair["entry_anchor_raw_s"], sr)
        bar_period_s = pair["outgoing_bar_period_s"] if pair.get("outgoing_bar_period_s") else 2.0
        bars, window_s = choose_window_bars(bar_period_s)
        window_smp = ms_to_smp(window_s, sr)

        # --- M0 ---
        m0_audio, m0_safety, m0_meta = render_m0(out_audio, in_audio, sr, exit_smp_m0, entry_smp_m0, window_smp)
        write_wav_float32(render_out / f"{tag}_M0.wav", m0_audio, sr)

        # --- M1 ---
        duration_contract_ok = True
        duration_contract_detail = None
        if job["bypass"]:
            stretched_tail = out_audio[exit_smp: exit_smp + window_smp]
        else:
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

            # BLOCKER 2: discard the rate-scaled warm-up prefix AND the
            # worker's tailPadS suffix -- retain EXACTLY the expected
            # rate-converted window duration, never the raw worker output
            # length (which includes latency/padding plumbing).
            #
            # PM re-review finding (this repair pass, caught by the new
            # exact-splice hard check, BLOCKER 4's own new tool): trimming
            # by the rate-converted warm-up alone still left a large,
            # measurable discontinuity exactly at the retained tail's first
            # sample (z~15, amplitude jump ~0.6 against a ~0.04 local
            # baseline). Root cause: the Signalsmith node's OWN reported
            # `stretch_latency_s` (already queried and recorded by the
            # pinned upstream worker, per its documented "how far ahead you
            # might want to schedule things" contract) is the algorithm's
            # intrinsic processing/lookahead delay -- our schedule call
            # starts input at output-time 0 with no latency compensation,
            # so the first `stretch_latency_s` worth of output is still
            # ramping up internally even after the rate-mapped warm-up is
            # skipped. Fix: also skip `stretch_latency_s` (converted to
            # samples) beyond the rate-mapped warm-up before taking the
            # retained window -- uses only information the SAME official
            # pinned node already reports for exactly this purpose, no new
            # capability.
            rate = job["rate"]
            latency_s = sidecar.get("stretch_latency_s") or 0.0
            latency_smp = ms_to_smp(latency_s, sr)
            warmup_out_smp = int(round(job.get("warmup_input_samples", 0) / rate)) + latency_smp
            expected_window_out_smp = int(round(job["window_input_samples"] / rate))
            available_after_warmup = stretched.shape[0] - warmup_out_smp
            tolerance_smp = ms_to_smp(DURATION_CONTRACT_TOLERANCE_S, sr)

            if available_after_warmup < expected_window_out_smp - tolerance_smp:
                evidence.append({"scenario": tag, "status": "M1_DURATION_CONTRACT_DEFECT", "out_id": out_id, "in_id": in_id,
                                  "detail": f"available={available_after_warmup} expected>={expected_window_out_smp - tolerance_smp}"})
                print(f"{tag}: M1 BLOCKED -- duration-contract defect (available={available_after_warmup}, expected>={expected_window_out_smp - tolerance_smp})")
                continue

            stretched_tail = stretched[warmup_out_smp: warmup_out_smp + expected_window_out_smp]
            actual_deviation_s = abs(stretched_tail.shape[0] - expected_window_out_smp) / sr
            duration_contract_ok = actual_deviation_s <= DURATION_CONTRACT_TOLERANCE_S
            duration_contract_detail = {
                "expected_window_out_samples": expected_window_out_smp,
                "retained_samples": int(stretched_tail.shape[0]),
                "deviation_s": round(actual_deviation_s, 5),
                "tolerance_s": DURATION_CONTRACT_TOLERANCE_S,
                "latency_compensation_s": round(latency_s, 5),
            }
            if not duration_contract_ok:
                evidence.append({"scenario": tag, "status": "M1_DURATION_CONTRACT_DEFECT", "out_id": out_id, "in_id": in_id, "detail": duration_contract_detail})
                print(f"{tag}: M1 BLOCKED -- duration-contract deviation {actual_deviation_s:.4f}s exceeds tolerance {DURATION_CONTRACT_TOLERANCE_S}s")
                continue

        m1_audio, m1_safety, m1_meta = render_m1(out_audio, in_audio, sr, exit_smp, entry_smp, stretched_tail, job["rate"], job["bypass"])
        write_wav_float32(render_out / f"{tag}_M1.wav", m1_audio, sr)

        m1_record = {
            "overlap_ms": m1_meta["overlap_ms"],
            "applied_tempo_ratio": m1_meta["applied_tempo_ratio"],
            "beat_alignment_applied": m1_meta["beat_alignment_applied"],
            "bass_eq_handoff_applied": m1_meta["bass_eq_handoff_applied"],
            "stretch_bypassed": m1_meta["stretch_bypassed"],
            "duration_contract_ok": duration_contract_ok,
            "duration_contract_detail": duration_contract_detail,
            "safety": {k: m1_safety[k] for k in ("pre_peak_dbfs", "post_peak_dbfs", "applied_headroom_gain_db", "nan_inf_sample_count", "clipped_sample_count")},
            "output_duration_s": m1_audio.shape[0] / sr,
        }
        if not job["bypass"]:
            m1_record["stretch_engine_latency_s"] = sidecar.get("stretch_latency_s")
            m1_record["stretch_requested_rate"] = sidecar.get("requested_tempo_rate")
            m1_record["stretch_sample_rate_assertions_passed"] = sidecar.get("sample_rate_assertions_passed")

        evidence.append({
            "scenario": tag,
            "status": "SUCCESS",
            "out_id": out_id,
            "in_id": in_id,
            "split": pair["split"],
            "is_stretch_cover_candidate": pair.get("is_stretch_cover_candidate", False),
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
            "m1": m1_record,
        })
        print(f"{tag}: SUCCESS m0_dur={m0_audio.shape[0]/sr:.2f}s m1_dur={m1_audio.shape[0]/sr:.2f}s rate={job['rate']} bypass={job['bypass']}")

    out = {
        "scenario_count": len(evidence),
        "success_count": sum(1 for e in evidence if e["status"] == "SUCCESS"),
        "stretch_applied_count": sum(1 for e in evidence if e["status"] == "SUCCESS" and not e["m1"]["stretch_bypassed"]),
        "scenarios": evidence,
    }
    Path(args.evidence_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nRESULT: {out['success_count']}/{out['scenario_count']} scenarios rendered ({out['stretch_applied_count']} with real Signalsmith stretch applied). Wrote {args.evidence_out}")
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
