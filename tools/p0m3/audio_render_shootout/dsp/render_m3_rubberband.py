"""
M3 -- Rubber Band quality-reference render (Issue #7 "M3 -- Rubber Band R3
quality reference. Only if legally/environmentally runnable as an isolated
research tool. Use the same boundary, correction, gain/EQ policy as M2 so
the time-stretch algorithm is the main changed variable.").

Per docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md sec.2, Rubber Band is
invoked ONLY as an external `ffmpeg -af rubberband=...` subprocess (tier 2
of Issue #7's probe order -- an already-available FFmpeg build with
--enable-librubberband). No Rubber Band source/binary is linked or vendored
into this repository. `QUALITY_REFERENCE_ONLY` -- never a shipping-core
candidate (AC3).

Synchronous (no browser round-trip needed, unlike M2) -- everything runs in
one Python process via subprocess.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402
from dsp.render_common import (  # noqa: E402
    load_scenario_context, compute_segments, fit_exact_length, ms_to_samples,
    compute_alignment_offset_ms, apply_time_offset, require_full_dj_alignment_fields,
)
from dsp.render_m2_signalsmith import full_dj_allowed, POST_ROLL_STRETCH_S, _write_result  # noqa: E402

FFMPEG_BIN = shutil.which("ffmpeg") or r"C:\Users\phamn\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
SERVE_TMP = ROOT / "serve_tmp"


def ffmpeg_rubberband_stretch(input_path: Path, output_path: Path, tempo_ratio: float, pitch_scale: float = 1.0):
    """
    Runs ffmpeg's `rubberband` audio filter (backed by --enable-librubberband)
    as an isolated external process. `tempo` is Rubber Band's own tempo-scale
    factor (>1 = faster/shorter, matching this harness's `required_tempo_ratio`
    convention -- verified empirically below via measured output duration).
    """
    cmd = [
        FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_path),
        "-af", f"rubberband=tempo={tempo_ratio}:pitch={pitch_scale}",
        "-c:a", "pcm_f32le",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg rubberband filter failed (exit {result.returncode}): {result.stderr}")
    return cmd


def render(transition_id: str) -> dict:
    import time
    t0 = time.perf_counter()
    ctx = load_scenario_context(transition_id)
    decision = ctx["decision"]

    if not full_dj_allowed(decision):
        return _render_fallback(ctx, decision, transition_id)

    require_full_dj_alignment_fields(decision)
    segs = compute_segments(ctx, post_roll_s=POST_ROLL_STRETCH_S)
    sr = segs["sr"]
    ratio = decision["required_tempo_ratio"]
    semitones = decision.get("required_pitch_shift_semitones") or 0
    pitch_scale = 2.0 ** (semitones / 12.0)

    needed_output_smp = segs["overlap_len_smp"] + ms_to_samples(POST_ROLL_STRETCH_S * 1000, sr)
    needed_input_smp = int(np.ceil(needed_output_smp * ratio))
    entry_smp = segs["entry_smp"]
    available = ctx["incoming_audio"][entry_smp:entry_smp + needed_input_smp]
    stretch_input = fit_exact_length(available, needed_input_smp)
    input_padded_samples = max(0, needed_input_smp - available.shape[0])

    in_path = SERVE_TMP / f"{transition_id}_m3_input.wav"
    out_path = SERVE_TMP / f"{transition_id}_m3_output.wav"
    write_wav_float32(in_path, stretch_input, sr)
    cmd = ffmpeg_rubberband_stretch(in_path, out_path, ratio, pitch_scale)
    stretched, sr_out = read_wav_float(out_path)
    assert sr_out == sr

    measured_input_s = stretch_input.shape[0] / sr
    measured_output_s = stretched.shape[0] / sr
    measured_ratio = measured_input_s / measured_output_s if measured_output_s else float("nan")

    align_offset_ms = compute_alignment_offset_ms(decision, segs, ratio)
    stretched_aligned = apply_time_offset(stretched, align_offset_ms, sr)

    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(stretched_aligned[:overlap_len], overlap_len)
    incoming_post = stretched_aligned[overlap_len:overlap_len + ms_to_samples(POST_ROLL_STRETCH_S * 1000, sr)]

    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=True,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)

    metadata = {
        "method": "M3",
        "method_role": "rubberband_quality_reference_only",
        "engine": "ffmpeg_librubberband_filter_subprocess",
        "engine_provenance_doc": "docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md",
        "ffmpeg_command": cmd,
        "transition_id": transition_id,
        "rendered_transition_class": "FULL_DJ_BLEND",
        "planner_allowed_transition_class_set": decision["allowed_transition_class_set"],
        "gain_law": "equal_power",
        "bass_eq_handoff_applied": True,
        "applied_tempo_ratio": ratio,
        "planner_required_tempo_ratio": decision.get("required_tempo_ratio"),
        "measured_input_output_ratio": measured_ratio,
        "applied_pitch_shift_semitones": semitones,
        "planner_required_pitch_shift_semitones": decision.get("required_pitch_shift_semitones"),
        "applied_alignment_offset_ms": align_offset_ms,
        "beat_alignment_applied": True,
        "beat_alignment_action": decision.get("beat_alignment_action"),
        "bar_alignment_action": decision.get("bar_alignment_action"),
        "outgoing_beat_alignment_target_ms": decision.get("outgoing_beat_alignment_target_ms"),
        "incoming_beat_alignment_target_ms": decision.get("incoming_beat_alignment_target_ms"),
        "input_padded_samples": input_padded_samples,
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "entry_ms": segs["entry_ms"],
        "overlap_len_samples": overlap_len,
        "overlap_duration_ms": overlap_len / sr * 1000.0,
        "output_duration_s": safe_audio.shape[0] / sr,
        "safety": safety_diag,
        "render_wall_time_s": time.perf_counter() - t0,
        "real_time_factor": (time.perf_counter() - t0) / (safe_audio.shape[0] / sr),
    }
    _write_result(transition_id, "M3", safe_audio, sr, metadata)
    return metadata


def _render_fallback(ctx, decision, transition_id):
    segs = compute_segments(ctx)
    sr = segs["sr"]
    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
    incoming_post = segs["incoming_raw_segment"][overlap_len:]
    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=False,
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)
    metadata = {
        "method": "M3",
        "method_role": "rubberband_quality_reference_only_documented_fallback",
        "engine": "none_full_dj_blend_withheld_by_planner",
        "transition_id": transition_id,
        "rendered_transition_class": decision["allowed_transition_class_set"][0] if decision["allowed_transition_class_set"] else "NO_SPECIAL_TRANSITION",
        "planner_allowed_transition_class_set": decision["allowed_transition_class_set"],
        "gain_law": "equal_power",
        "bass_eq_handoff_applied": False,
        "applied_tempo_ratio": 1.0,
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
    }
    _write_result(transition_id, "M3", safe_audio, sr, metadata)
    return metadata


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python dsp/render_m3_rubberband.py <transition_id>")
        sys.exit(1)
    result = render(sys.argv[1])
    print(json.dumps(result, indent=2))
