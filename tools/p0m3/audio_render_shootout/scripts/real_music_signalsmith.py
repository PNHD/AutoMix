"""
P0-M3-R3 STAGE B -- real-music OWNER-FACING candidate C (Signalsmith
Stretch), the production tempo-match engine per the newest Issue #7 PM
comment ("Signalsmith Stretch is the OWNER-LISTENING production candidate
... Rubber Band remains PM/reference-only and must not be the sole
owner-facing tempo candidate").

`scripts/real_music_pipeline.py`'s own candidate C uses ffmpeg's Rubber
Band filter (QUALITY_REFERENCE_ONLY, PM/engineering-reference use per
`docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md`) because a real
WebAudio API is not available in plain Python -- exactly the same
constraint `dsp/render_m2_signalsmith.py` documents for the synthetic
scenarios, solved the same documented way: a manual two-phase browser round
trip through the OFFICIAL, PINNED, UNMODIFIED
`web/release/SignalsmithStretch.mjs` running in `web/stretch_worker.html`.

This module is the real-music analogue of `dsp/render_m2_signalsmith.py`'s
prepare_job/finish_job, adapted to read from a real-music pair's rendered
work directory (`real_music_pipeline.py`'s `outgoing.wav` / `incoming.wav`
/ `planner_decision.json`) instead of the synthetic scenario fixtures --
same shared DSP engine (`dsp/mixing.py`, `dsp/loudness_diagnostics.py`),
same alignment/rate-parity fail-closed checks, same
MATCH_AND_RETURN_TO_NATIVE safety gate. Never re-decides tempo/alignment
independently of the real planner_decision.json already written by
real_music_pipeline.py for this pair.

Usage:
    python scripts/real_music_signalsmith.py prepare REAL-V2 --work-dir real_music/work_local/renders
    # ... open the printed URL in a real browser, wait for the upload ...
    python scripts/real_music_signalsmith.py finish REAL-V2 --work-dir real_music/work_local/renders
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety, normalize_sample_rate, SampleRateMismatchError  # noqa: E402
from dsp.render_common import (  # noqa: E402
    compute_segments, fit_exact_length, ms_to_samples,
    compute_alignment_offset_ms, apply_time_offset, require_full_dj_alignment_fields,
)
from dsp.loudness_diagnostics import compute_transition_loudness_diagnostics  # noqa: E402
from dsp.tempo_modes import select_tempo_mode, MATCH_AND_RETURN_TO_NATIVE  # noqa: E402
from dsp.tempo_ramp import ramp_is_safe  # noqa: E402

SERVE_TMP = ROOT / "serve_tmp"
SERVE_TMP.mkdir(exist_ok=True)
SERVER_BASE_URL = "http://127.0.0.1:8765"
BLOCK_MS = 120.0
POST_ROLL_S = 15.0
CANONICAL_SR = 44100
LOUDNESS_CURVE = "late_hold"  # same candidate-C loudness policy as real_music_pipeline.py's ffmpeg-rubberband C


def _load_pair(pair_id: str, work_dir: Path):
    pair_dir = work_dir / pair_id
    out_audio, sr1 = read_wav_float(pair_dir / "outgoing.wav")
    in_audio, sr2 = read_wav_float(pair_dir / "incoming.wav")
    if sr1 != CANONICAL_SR or sr2 != CANONICAL_SR:
        raise SampleRateMismatchError(f"{pair_id}: expected canonical {CANONICAL_SR}Hz source audio")
    decision = json.loads((pair_dir / "planner_decision.json").read_text(encoding="utf-8"))
    return pair_dir, out_audio, in_audio, decision


def prepare_job(pair_id: str, work_dir: Path) -> dict:
    pair_dir, out_audio, in_audio, decision = _load_pair(pair_id, work_dir)
    if "FULL_DJ_BLEND" not in decision.get("allowed_transition_class_set", []):
        raise RuntimeError(f"{pair_id}: FULL_DJ_BLEND not allowed by planner -- no Signalsmith job needed")
    require_full_dj_alignment_fields(decision)

    ctx = {"decision": decision, "sr": CANONICAL_SR, "outgoing_audio": out_audio, "incoming_audio": in_audio}
    segs = compute_segments(ctx, post_roll_s=POST_ROLL_S)
    sr = segs["sr"]

    ratio = decision["required_tempo_ratio"]
    semitones = decision.get("required_pitch_shift_semitones") or 0

    needed_output_smp = segs["overlap_len_smp"] + ms_to_samples(POST_ROLL_S * 1000, sr)
    needed_input_smp = int(np.ceil(needed_output_smp * ratio))
    entry_smp = segs["entry_smp"]
    available = in_audio[entry_smp:entry_smp + needed_input_smp]
    stretch_input = fit_exact_length(available, needed_input_smp)
    input_padded_samples = max(0, needed_input_smp - available.shape[0])

    tag = f"{pair_id}_realmusic_signalsmith"
    input_name = f"{tag}_input.wav"
    output_name = f"{tag}_output.wav"
    sidecar_name = f"{tag}_sidecar.json"
    write_wav_float32(SERVE_TMP / input_name, stretch_input, sr)

    job = {
        "pair_id": pair_id,
        "sr": sr,
        "rate": ratio,
        "semitones": semitones,
        "block_ms": BLOCK_MS,
        "input_name": input_name,
        "output_name": output_name,
        "sidecar_name": sidecar_name,
        "needed_output_smp": needed_output_smp,
        "input_padded_samples": input_padded_samples,
        "url": (
            f"{SERVER_BASE_URL}/web/stretch_worker.html?"
            f"input=/serve_tmp/{input_name}&rate={ratio}&semitones={semitones}"
            f"&output={output_name}&blockMs={BLOCK_MS}&tailPadS=1.5"
            f"&expectedSampleRate={sr}&sidecar={sidecar_name}"
        ),
    }
    (SERVE_TMP / f"{tag}_job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    print(json.dumps(job, indent=2))
    return job


def finish_job(pair_id: str, work_dir: Path) -> dict:
    pair_dir, out_audio, in_audio, decision = _load_pair(pair_id, work_dir)
    tag = f"{pair_id}_realmusic_signalsmith"
    job = json.loads((SERVE_TMP / f"{tag}_job.json").read_text(encoding="utf-8"))
    output_path = SERVE_TMP / job["output_name"]
    sidecar_path = SERVE_TMP / job["sidecar_name"]
    if not output_path.exists():
        raise RuntimeError(f"{output_path} not found -- did the browser job finish and upload?")
    if not sidecar_path.exists():
        raise RuntimeError(f"{sidecar_path} not found -- latency/scheduling sidecar required, browser job did not upload it")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))

    ctx = {"decision": decision, "sr": CANONICAL_SR, "outgoing_audio": out_audio, "incoming_audio": in_audio}
    segs = compute_segments(ctx, post_roll_s=POST_ROLL_S)
    canonical_sr = segs["sr"]

    stretched, sr_from_file = read_wav_float(output_path)
    resample_applied = False
    if sr_from_file != canonical_sr:
        stretched, resample_applied = normalize_sample_rate(stretched, sr_from_file, canonical_sr)
        if not resample_applied:
            raise SampleRateMismatchError(
                f"{pair_id}: Signalsmith output rate {sr_from_file} != canonical {canonical_sr}, no normalization applied -- failing closed."
            )
    sr = canonical_sr

    if sidecar.get("output_sample_rate") != sr_from_file:
        raise SampleRateMismatchError(
            f"{pair_id}: sidecar-reported output_sample_rate {sidecar.get('output_sample_rate')} "
            f"disagrees with actual WAV file {sr_from_file}."
        )
    if stretched.shape[1] != sidecar.get("channels"):
        raise RuntimeError(f"{pair_id}: channel mismatch WAV={stretched.shape[1]} sidecar={sidecar.get('channels')}")

    # Belt-and-braces: this pass's tempo_mode is already guaranteed
    # MATCH_INCOMING_DURING_OVERLAP (never MATCH_AND_RETURN_TO_NATIVE) by
    # dsp/tempo_modes.py's own ramp_is_safe gate -- re-verify here too
    # before ever treating this render as safe.
    tempo_mode, tempo_evidence = select_tempo_mode(decision, prefer_return_to_native=True)
    if tempo_mode == MATCH_AND_RETURN_TO_NATIVE:
        safe, _ = ramp_is_safe(job["rate"])
        if not safe:
            raise RuntimeError(f"{pair_id}: MATCH_AND_RETURN_TO_NATIVE selected but ramp_is_safe reports unsafe -- refusing to render")

    align_offset_ms = compute_alignment_offset_ms(decision, segs, job["rate"])
    stretched_aligned = apply_time_offset(stretched, align_offset_ms, sr)

    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(stretched_aligned[:overlap_len], overlap_len)
    incoming_post = stretched_aligned[overlap_len:overlap_len + ms_to_samples(POST_ROLL_S * 1000, sr)]

    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=True, curve=LOUDNESS_CURVE,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)

    pre_roll_len = segs["onset_smp"] - max(0, segs["onset_smp"] - ms_to_samples(15000, sr))
    content_end_render_smp = pre_roll_len + overlap_len
    loudness = compute_transition_loudness_diagnostics(safe_audio, sr, pre_roll_len, content_end_render_smp)

    out_name = "C_conditional_tempo_candidate_SIGNALSMITH_OWNER.wav"
    write_wav_float32(pair_dir / out_name, safe_audio, sr)

    metadata = {
        "pair_id": pair_id,
        "candidate": "C_SIGNALSMITH_OWNER_FACING",
        "engine": "official_pinned_web_release_wasm_webaudio_fallback",
        "engine_provenance_doc": "docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md",
        "tempo_mode": tempo_mode,
        "curve": LOUDNESS_CURVE,
        "bass_eq_handoff_applied": True,
        "applied_tempo_ratio": job["rate"],
        "planner_required_tempo_ratio": decision.get("required_tempo_ratio"),
        "applied_pitch_shift_semitones": job["semitones"],
        "applied_alignment_offset_ms": align_offset_ms,
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "entry_ms": segs["entry_ms"],
        "overlap_duration_ms": overlap_len / sr * 1000.0,
        "output_duration_s": safe_audio.shape[0] / sr,
        "safety": safety_diag,
        "canonical_sample_rate": canonical_sr,
        "browser_output_sample_rate_from_file": sr_from_file,
        "sample_rate_resample_applied": resample_applied,
        "channels": safe_audio.shape[1],
        "signalsmith_job_sidecar": sidecar,
        "loudness_max_dip_db": loudness["maximum_loudness_dip_db"],
        "loudness_max_rise_db": loudness["maximum_loudness_rise_db"],
    }
    (pair_dir / "C_signalsmith_owner_result.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["prepare", "finish"])
    ap.add_argument("pair_id")
    ap.add_argument("--work-dir", required=True)
    args = ap.parse_args()
    work_dir = Path(args.work_dir)
    if args.action == "prepare":
        prepare_job(args.pair_id, work_dir)
    else:
        finish_job(args.pair_id, work_dir)


if __name__ == "__main__":
    main()
