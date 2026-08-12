"""
M2 -- Signalsmith Stretch candidate render (Issue #7 "M2 -- Signalsmith
candidate: planner boundary; required tempo correction from PlannerDecision;
explicit beat/downbeat alignment action; equal-power gains; transparent,
documented bass/EQ swap appropriate to SHORT_EQ/FULL_DJ; no arbitrary new
cue selection").

Because native compilation is unavailable in this environment
(docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md sec.1.1), the actual
time-stretch is performed by the OFFICIAL, PINNED, UNMODIFIED
`web/release/SignalsmithStretch.mjs` running in a real browser
AudioWorklet/OfflineAudioContext (web/stretch_worker.html), driven manually
in two phases from this process since a real Web Audio API is not available
in plain Python/Node:

    python dsp/render_m2_signalsmith.py prepare <transition_id> [variant]
        -- writes the raw incoming segment that needs stretching to
           serve_tmp/, and prints the exact stretch_worker.html URL to open
           in a real browser (rate/semitones/blockMs taken VERBATIM from the
           PlannerDecision, never invented; expectedSampleRate is the
           canonical fixture rate, PM STAGE A REVIEW R1 repair).

    python dsp/render_m2_signalsmith.py finish <transition_id> [variant]
        -- reads the stretched WAV + sidecar JSON the browser uploaded back
           to serve_tmp/, asserts sample-rate/channel parity (fail closed,
           R1 repair), applies the SAME shared mixing engine (dsp/mixing.py)
           used by every other method, and writes the final render +
           metadata (including the R6 latency/scheduling sidecar).

`variant`: "diagnostic" (default, marker-embedded source, full pipeline/
metrics) or "clean" (marker-free source, owner-listening renders only --
PM STAGE A REVIEW R4 repair). Diagnostic and clean jobs use separate
input/output/sidecar filenames so they never collide.

When FULL_DJ_BLEND is not in the planner's allowed_transition_class_set
(scenario D), there is nothing to stretch -- `render_fallback` renders the
SAME allowed fallback class M1 would (documented, not a silent
downgrade -- Issue #7 "the renderer must produce only the allowed fallback;
it must not force complex DSP").
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety, normalize_sample_rate, SampleRateMismatchError  # noqa: E402
from dsp.render_common import (  # noqa: E402
    load_scenario_context, compute_segments, fit_exact_length, ms_to_samples,
    compute_alignment_offset_ms, apply_time_offset, require_full_dj_alignment_fields,
    PlannerContractError, save_premix_diagnostic,
)

SERVE_TMP = ROOT / "serve_tmp"
SERVE_TMP.mkdir(exist_ok=True)
RESULTS_RENDERED = ROOT / "results" / "rendered"
RESULTS_META = ROOT / "results" / "render_meta"
RESULTS_RENDERED_CLEAN = ROOT / "results" / "rendered_clean"
RESULTS_META_CLEAN = ROOT / "results" / "render_meta_clean"

SERVER_BASE_URL = "http://127.0.0.1:8765"
BLOCK_MS = 120.0
POST_ROLL_STRETCH_S = 15.0  # how much post-overlap incoming content to also stretch, so no mid-clip tempo jump


def full_dj_allowed(decision: dict) -> bool:
    return "FULL_DJ_BLEND" in decision.get("allowed_transition_class_set", [])


def prepare_job(transition_id: str, variant: str = "diagnostic") -> dict:
    ctx = load_scenario_context(transition_id, variant=variant)
    decision = ctx["decision"]
    segs = compute_segments(ctx, post_roll_s=POST_ROLL_STRETCH_S)
    sr = segs["sr"]

    if not full_dj_allowed(decision):
        raise RuntimeError(f"{transition_id}: FULL_DJ_BLEND not allowed by planner -- use render_fallback(), no browser job needed")
    require_full_dj_alignment_fields(decision)

    ratio = decision["required_tempo_ratio"]
    semitones = decision.get("required_pitch_shift_semitones") or 0

    needed_output_smp = segs["overlap_len_smp"] + ms_to_samples(POST_ROLL_STRETCH_S * 1000, sr)
    needed_input_smp = int(np.ceil(needed_output_smp * ratio))
    # Pull directly from the full incoming track (not the native-length-
    # capped segs["incoming_raw_segment"]) -- a rate>1 stretch needs MORE
    # raw input samples than the native-tempo output length would suggest.
    entry_smp = segs["entry_smp"]
    available = ctx["incoming_audio"][entry_smp:entry_smp + needed_input_smp]
    stretch_input = fit_exact_length(available, needed_input_smp)
    # If the raw incoming track doesn't have enough material, fit_exact_length
    # zero-pads -- honestly recorded via input_padded_samples below.
    input_padded_samples = max(0, needed_input_smp - available.shape[0])

    tag = f"{transition_id}_{variant}"
    input_name = f"{tag}_m2_input.wav"
    output_name = f"{tag}_m2_output.wav"
    sidecar_name = f"{tag}_m2_sidecar.json"
    write_wav_float32(SERVE_TMP / input_name, stretch_input, sr)

    job = {
        "transition_id": transition_id,
        "variant": variant,
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
    (SERVE_TMP / f"{tag}_m2_job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    print(json.dumps(job, indent=2))
    return job


def finish_job(transition_id: str, variant: str = "diagnostic") -> dict:
    t0 = time.perf_counter()
    tag = f"{transition_id}_{variant}"
    job = json.loads((SERVE_TMP / f"{tag}_m2_job.json").read_text(encoding="utf-8"))
    output_path = SERVE_TMP / job["output_name"]
    sidecar_path = SERVE_TMP / job["sidecar_name"]
    if not output_path.exists():
        raise RuntimeError(f"{output_path} not found -- did the browser job finish and upload?")
    if not sidecar_path.exists():
        raise RuntimeError(f"{sidecar_path} not found -- R6 latency/scheduling sidecar is required, browser job did not upload it")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))

    ctx = load_scenario_context(transition_id, variant=variant)
    decision = ctx["decision"]
    segs = compute_segments(ctx, post_roll_s=POST_ROLL_STRETCH_S)
    canonical_sr = segs["sr"]

    # R1 repair: read the ACTUAL bytes' sample rate from the WAV file
    # itself (never just trust the sidecar's self-reported value) and fail
    # closed on any un-normalized mismatch against the canonical render
    # rate. The browser-side fix (web/stretch_worker.html now decodes/
    # renders at an explicitly requested rate and asserts it itself before
    # upload) should make this branch a no-op in practice; this is
    # defense-in-depth, not the primary fix.
    stretched, sr_from_file = read_wav_float(output_path)
    resample_applied = False
    if sr_from_file != canonical_sr:
        stretched, resample_applied = normalize_sample_rate(stretched, sr_from_file, canonical_sr)
        if not resample_applied:
            raise SampleRateMismatchError(
                f"{transition_id}/{variant}: M2 output sample rate {sr_from_file} != canonical {canonical_sr} "
                "and no normalization was applied -- failing closed (R1 repair)."
            )
    sr = canonical_sr

    if sidecar.get("output_sample_rate") != sr_from_file:
        raise SampleRateMismatchError(
            f"{transition_id}/{variant}: sidecar-reported output_sample_rate "
            f"{sidecar.get('output_sample_rate')} disagrees with the actual WAV file's "
            f"{sr_from_file} -- refusing to trust either value silently."
        )
    if stretched.shape[1] != sidecar.get("channels"):
        raise RuntimeError(f"{transition_id}/{variant}: channel count mismatch between WAV ({stretched.shape[1]}) and sidecar ({sidecar.get('channels')})")

    align_offset_ms = compute_alignment_offset_ms(decision, segs, job["rate"])
    stretched_aligned = apply_time_offset(stretched, align_offset_ms, sr)

    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(stretched_aligned[:overlap_len], overlap_len)
    incoming_post = stretched_aligned[overlap_len:overlap_len + ms_to_samples(POST_ROLL_STRETCH_S * 1000, sr)]

    if variant == "diagnostic":
        save_premix_diagnostic(transition_id, "M2", segs["outgoing_overlap"], incoming_overlap, sr)

    # Clean (owner-listening) renders use the SAME real M2 gain/EQ/alignment
    # policy as diagnostic renders -- only the underlying source audio
    # (marker-free) differs, never the DSP policy itself.
    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=True,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)

    metadata = {
        "method": "M2",
        "method_role": "signalsmith_stretch_candidate",
        "variant": variant,
        "engine": "official_pinned_web_release_wasm_webaudio_fallback",
        "engine_provenance_doc": "docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md",
        "transition_id": transition_id,
        "rendered_transition_class": "FULL_DJ_BLEND",
        "planner_allowed_transition_class_set": decision["allowed_transition_class_set"],
        "gain_law": "equal_power",
        "bass_eq_handoff_applied": True,
        "applied_tempo_ratio": job["rate"],
        "planner_required_tempo_ratio": decision.get("required_tempo_ratio"),
        "applied_pitch_shift_semitones": job["semitones"],
        "planner_required_pitch_shift_semitones": decision.get("required_pitch_shift_semitones"),
        "applied_alignment_offset_ms": align_offset_ms,
        "beat_alignment_applied": True,
        "beat_alignment_action": decision.get("beat_alignment_action"),
        "bar_alignment_action": decision.get("bar_alignment_action"),
        "outgoing_beat_alignment_target_ms": decision.get("outgoing_beat_alignment_target_ms"),
        "incoming_beat_alignment_target_ms": decision.get("incoming_beat_alignment_target_ms"),
        "input_padded_samples": job["input_padded_samples"],
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "entry_ms": segs["entry_ms"],
        "overlap_len_samples": overlap_len,
        "overlap_duration_ms": overlap_len / sr * 1000.0,
        "output_duration_s": safe_audio.shape[0] / sr,
        "safety": safety_diag,
        # R1: explicit sample-rate/channel parity evidence.
        "canonical_sample_rate": canonical_sr,
        "browser_output_sample_rate_from_file": sr_from_file,
        "sample_rate_resample_applied": resample_applied,
        "channels": safe_audio.shape[1],
        # R6: latency/scheduling sidecar, verbatim from the browser job.
        "signalsmith_job_sidecar": sidecar,
        "render_wall_time_s_note": "measures only this process's post-stretch mixing/assembly; the WASM stretch itself runs in a separate browser process/tab and its wall time is NOT captured by this harness (documented limitation, not fabricated as 0)",
        "render_wall_time_s_python_side": time.perf_counter() - t0,
    }
    out_dir = RESULTS_RENDERED if variant == "diagnostic" else RESULTS_RENDERED_CLEAN
    meta_dir = RESULTS_META if variant == "diagnostic" else RESULTS_META_CLEAN
    _write_result(transition_id, "M2", safe_audio, sr, metadata, out_dir, meta_dir)
    return metadata


def render_fallback(transition_id: str, variant: str = "diagnostic") -> dict:
    """No browser job needed: FULL_DJ_BLEND withheld, render the SAME allowed fallback M1 renders."""
    ctx = load_scenario_context(transition_id, variant=variant)
    decision = ctx["decision"]
    if full_dj_allowed(decision):
        raise RuntimeError(f"{transition_id}: FULL_DJ_BLEND IS allowed -- use prepare_job/finish_job, not render_fallback")
    segs = compute_segments(ctx)
    sr = segs["sr"]
    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
    incoming_post = segs["incoming_raw_segment"][overlap_len:]

    if variant == "diagnostic":
        save_premix_diagnostic(transition_id, "M2", segs["outgoing_overlap"], incoming_overlap, sr)

    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=False,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)
    metadata = {
        "method": "M2",
        "method_role": "signalsmith_stretch_candidate_documented_fallback",
        "variant": variant,
        "engine": "none_full_dj_blend_withheld_by_planner",
        "transition_id": transition_id,
        "rendered_transition_class": decision["allowed_transition_class_set"][0] if decision["allowed_transition_class_set"] else "NO_SPECIAL_TRANSITION",
        "planner_allowed_transition_class_set": decision["allowed_transition_class_set"],
        "gain_law": "equal_power",
        "bass_eq_handoff_applied": False,
        "applied_tempo_ratio": 1.0,
        "planner_required_tempo_ratio": decision.get("required_tempo_ratio"),
        "applied_pitch_shift_semitones": 0,
        "applied_alignment_offset_ms": 0.0,
        "beat_alignment_applied": False,
        "fallback_reason": "FULL_DJ_BLEND withheld by R2 pair-compatibility gate -- see planner reason_codes",
        "planner_reason_codes": decision.get("reason_codes", []),
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "entry_ms": segs["entry_ms"],
        "overlap_len_samples": overlap_len,
        "overlap_duration_ms": overlap_len / sr * 1000.0,
        "output_duration_s": safe_audio.shape[0] / sr,
        "safety": safety_diag,
        "canonical_sample_rate": sr,
        "channels": safe_audio.shape[1],
    }
    out_dir = RESULTS_RENDERED if variant == "diagnostic" else RESULTS_RENDERED_CLEAN
    meta_dir = RESULTS_META if variant == "diagnostic" else RESULTS_META_CLEAN
    _write_result(transition_id, "M2", safe_audio, sr, metadata, out_dir, meta_dir)
    return metadata


def _write_result(transition_id: str, method: str, audio: np.ndarray, sr: int, metadata: dict, out_dir: Path = RESULTS_RENDERED, meta_dir: Path = RESULTS_META):
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    write_wav_float32(out_dir / f"{transition_id}_{method}.wav", audio, sr)
    (meta_dir / f"{transition_id}_{method}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in ("prepare", "finish", "fallback"):
        print(__doc__)
        sys.exit(1)
    action, tid = sys.argv[1], sys.argv[2]
    variant_arg = sys.argv[3] if len(sys.argv) == 4 else "diagnostic"
    if action == "prepare":
        prepare_job(tid, variant_arg)
    elif action == "finish":
        result = finish_job(tid, variant_arg)
        print(json.dumps(result, indent=2))
    elif action == "fallback":
        result = render_fallback(tid, variant_arg)
        print(json.dumps(result, indent=2))
