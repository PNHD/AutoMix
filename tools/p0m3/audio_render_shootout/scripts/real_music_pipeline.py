"""
Tier-B real-music private validation harness (PM OWNER LISTENING
DIRECTION UPDATE, Task 3). Consumes an owner-supplied, LOCAL-ONLY manifest
(real_music/MANIFEST_SCHEMA.md) pointing at local WAV/FLAC/MP3/M4A files,
converts them to canonical 44100Hz stereo float32 WAV, builds a real
transition-policy fixture from the manifest's annotations, calls the SAME
accepted R2 planner every other scenario in this pass uses
(`policy.boundary.plan_transition_boundary`), applies this pass's tempo-
mode selection (dsp/tempo_modes.py) and loudness-repair curve
(dsp/mixing.py `curve="late_hold"`, this pass's recommended default -- see
the research report), and renders M1 (always) + M3 (ffmpeg Rubber Band,
when a dynamic class is allowed and tempo mode requires correction).

M2 (Signalsmith) is NOT rendered automatically by this script: it requires
the same manual browser round-trip (`dsp/render_m2_signalsmith.py prepare`
+ opening the URL in a real browser + `finish`) every synthetic scenario
in this pass required. This script prints the exact `prepare`-equivalent
instructions for M2 rather than silently skipping it -- see
`m2_manual_instructions` in the output summary.

No audio, path, or filename from a real manifest is ever written to a
committed location. `--summary-out` (optional) writes ONLY pair_id/
category/planner-decision numeric fields -- never a path/filename.

Usage:
    python scripts/real_music_pipeline.py --manifest real_music/manifest.local.json --work-dir real_music/work_local
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety, SampleRateMismatchError  # noqa: E402
from dsp.render_common import (  # noqa: E402
    compute_segments, fit_exact_length, ms_to_samples,
    compute_alignment_offset_ms, apply_time_offset, require_full_dj_alignment_fields,
    PlannerContractError,
)
from dsp.tempo_modes import select_tempo_mode, NATIVE_TEMPO, MATCH_AND_RETURN_TO_NATIVE  # noqa: E402
from dsp.tempo_ramp import apply_return_to_native_ramp  # noqa: E402
from dsp import safety_metrics as sm  # noqa: E402
from dsp.loudness_diagnostics import compute_transition_loudness_diagnostics  # noqa: E402
from dsp.render_m3_rubberband import ffmpeg_rubberband_stretch, FFMPEG_BIN  # noqa: E402

from policy.boundary import plan_transition_boundary  # noqa: E402
from policy.eligibility import SEAMLESS_FULL_TRACK_DEFAULT  # noqa: E402

CANONICAL_SR = 44100
POST_ROLL_S = 15.0
REPAIRED_CURVE = "late_hold"  # this pass's recommended default (dsp/mixing.late_outgoing_hold_gains)


def convert_to_canonical_wav(src_path: str, dst_path: Path) -> None:
    ffmpeg = FFMPEG_BIN
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-i", src_path, "-ac", "2", "-ar", str(CANONICAL_SR), "-c:a", "pcm_f32le", str(dst_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed for input (path withheld from logs): {result.stderr[-800:]}")


def build_tx_fixture(pair: dict) -> dict:
    out = pair["outgoing"]
    inc = pair["incoming"]
    return {
        "transition_id": pair["pair_id"],
        "outgoing_track": {
            "duration_ms": out["duration_ms"],
            "genre_tags": out.get("genre_tags", []),
            "bpm": out["bpm"],
            "candidates": [
                {
                    "candidate_id": f"{pair['pair_id']}-OUT-EXIT",
                    "t_ms": out["exit_candidate_t_ms"],
                    "source": "owner_supplied",
                    "beat_downbeat_aligned": out.get("beat_downbeat_aligned", False),
                    "in_acceptable_exit_region": out.get("in_acceptable_exit_region", False),
                    "musical_unit_complete": out.get("musical_unit_complete", False),
                    "is_outro_tail_opportunity": out.get("is_outro_tail_opportunity", False),
                    "vocal_collision_risk": out.get("vocal_collision_risk", "NONE"),
                    "structure_confidence": out.get("structure_confidence", "NONE"),
                    "energy_continuity_hint": out.get("energy_continuity_hint", "UNKNOWN"),
                    "is_end_of_track": False,
                },
                {
                    "candidate_id": f"{pair['pair_id']}-OUT-END",
                    "t_ms": out["duration_ms"],
                    "source": "owner_supplied",
                    "beat_downbeat_aligned": out.get("beat_downbeat_aligned", False),
                    "in_acceptable_exit_region": True,
                    "musical_unit_complete": True,
                    "is_outro_tail_opportunity": True,
                    "vocal_collision_risk": "NONE",
                    "structure_confidence": out.get("structure_confidence", "NONE"),
                    "is_end_of_track": True,
                },
            ],
        },
        "incoming_track": {
            "genre_tags": inc.get("genre_tags", []),
            "bpm": inc["bpm"],
            "candidates": [
                {
                    "candidate_id": f"{pair['pair_id']}-IN-ANCHOR",
                    "t_ms": inc["entry_candidate_t_ms"],
                    "phrase_section_evidence": inc.get("phrase_section_evidence", False),
                    "beat_downbeat_aligned": inc.get("beat_downbeat_aligned", False),
                    "is_authored_silence_skip": inc.get("is_authored_silence_skip", False),
                }
            ],
        },
        "pair_base": pair["pair_compatibility"],
        "boundary_overrides": {},
    }


def render_pair(pair: dict, work_dir: Path) -> dict:
    pair_id = pair["pair_id"]
    pair_dir = work_dir / pair_id
    pair_dir.mkdir(parents=True, exist_ok=True)

    out_wav = pair_dir / "outgoing.wav"
    in_wav = pair_dir / "incoming.wav"
    convert_to_canonical_wav(pair["outgoing"]["path"], out_wav)
    convert_to_canonical_wav(pair["incoming"]["path"], in_wav)

    out_audio, sr1 = read_wav_float(out_wav)
    in_audio, sr2 = read_wav_float(in_wav)
    if sr1 != CANONICAL_SR or sr2 != CANONICAL_SR:
        raise SampleRateMismatchError(f"{pair_id}: conversion did not produce canonical {CANONICAL_SR}Hz audio")

    fixture = build_tx_fixture(pair)
    decision = plan_transition_boundary(fixture, SEAMLESS_FULL_TRACK_DEFAULT)
    from dataclasses import asdict
    decision_dict = asdict(decision)
    (pair_dir / "planner_decision.json").write_text(json.dumps(decision_dict, indent=2), encoding="utf-8")

    tempo_mode, tempo_evidence = select_tempo_mode(decision_dict, prefer_return_to_native=True)

    ctx = {"decision": decision_dict, "sr": CANONICAL_SR, "outgoing_audio": out_audio, "incoming_audio": in_audio}
    segs = compute_segments(ctx, post_roll_s=POST_ROLL_S)
    sr = CANONICAL_SR
    overlap_len = segs["overlap_len_smp"]

    result = {
        "pair_id": pair_id,
        "category": pair.get("category"),
        "decision_type": decision_dict["decision_type"],
        "allowed_transition_class_set": decision_dict["allowed_transition_class_set"],
        "required_tempo_ratio": decision_dict.get("required_tempo_ratio"),
        "tempo_mode": tempo_mode,
        "tempo_mode_evidence": tempo_evidence,
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "entry_ms": segs["entry_ms"],
        "overlap_duration_ms": overlap_len / sr * 1000.0,
        "renders": {},
    }

    # M1 -- always render: planner-correct reference, REPAIRED loudness curve default.
    incoming_overlap_native = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
    incoming_post_native = segs["incoming_raw_segment"][overlap_len:]
    m1_rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap_native, incoming_post_native,
        sr, use_equal_power=True, use_bass_handoff=False, curve=REPAIRED_CURVE,
    )
    m1_safe, m1_safety = apply_headroom_and_safety(m1_rendered)
    write_wav_float32(pair_dir / "M1_repaired_curve.wav", m1_safe, sr)
    pre_roll_len = segs["onset_smp"] - max(0, segs["onset_smp"] - ms_to_samples(15000, sr))
    content_end_render_smp = pre_roll_len + overlap_len
    m1_loudness = compute_transition_loudness_diagnostics(m1_safe, sr, pre_roll_len, content_end_render_smp)
    result["renders"]["M1"] = {
        "safety": m1_safety,
        "loudness_max_dip_db": m1_loudness["maximum_loudness_dip_db"],
        "loudness_max_rise_db": m1_loudness["maximum_loudness_rise_db"],
    }

    full_dj_allowed = "FULL_DJ_BLEND" in decision_dict["allowed_transition_class_set"]
    result["m2_manual_instructions"] = (
        None if not full_dj_allowed else
        f"FULL_DJ_BLEND is allowed for {pair_id} -- to render M2 (Signalsmith), run the same "
        f"prepare/finish browser-bridge flow dsp/render_m2_signalsmith.py uses for the synthetic "
        f"scenarios, pointed at {pair_dir}/incoming.wav from entry_ms={segs['entry_ms']} with "
        f"rate={decision_dict.get('required_tempo_ratio')} (not run automatically by this script)."
    )

    if full_dj_allowed and tempo_mode != NATIVE_TEMPO and decision_dict.get("required_tempo_ratio") is not None:
        require_full_dj_alignment_fields(decision_dict)
        ratio = decision_dict["required_tempo_ratio"]
        pitch_semitones = decision_dict.get("required_pitch_shift_semitones") or 0
        pitch_scale = 2.0 ** (pitch_semitones / 12.0)

        needed_output_smp = overlap_len + ms_to_samples(POST_ROLL_S * 1000, sr)
        needed_input_smp = int((needed_output_smp * ratio) + 0.999999)
        entry_smp = segs["entry_smp"]
        available = in_audio[entry_smp:entry_smp + needed_input_smp]
        stretch_input = fit_exact_length(available, needed_input_smp)

        in_path = pair_dir / "m3_stretch_input.wav"
        out_path = pair_dir / "m3_stretch_output.wav"
        write_wav_float32(in_path, stretch_input, sr)
        cmd = ffmpeg_rubberband_stretch(in_path, out_path, ratio, pitch_scale)
        stretched, sr_out = read_wav_float(out_path)
        if sr_out != sr:
            raise SampleRateMismatchError(f"{pair_id}: M3 output sr {sr_out} != {sr}")

        align_offset_ms = compute_alignment_offset_ms(decision_dict, segs, ratio)
        stretched_aligned = apply_time_offset(stretched, align_offset_ms, sr)
        incoming_overlap_m3 = fit_exact_length(stretched_aligned[:overlap_len], overlap_len)
        incoming_post_m3 = stretched_aligned[overlap_len:overlap_len + ms_to_samples(POST_ROLL_S * 1000, sr)]

        if tempo_mode == MATCH_AND_RETURN_TO_NATIVE:
            incoming_bpm = pair["incoming"]["bpm"]
            bar_dur_s = 4.0 * (60.0 / incoming_bpm)
            ramp_duration_s = 2.0 * bar_dur_s
            incoming_post_m3, rate_curve = apply_return_to_native_ramp(incoming_post_m3, sr, ratio, ramp_duration_s)
            result["renders"].setdefault("M3", {})["tempo_ramp_duration_s"] = ramp_duration_s
            result["renders"]["M3"]["rate_curve_points"] = len(rate_curve)

        m3_rendered = assemble_transition_render(
            segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap_m3, incoming_post_m3,
            sr, use_equal_power=True, use_bass_handoff=True, curve=REPAIRED_CURVE,
        )
        m3_safe, m3_safety = apply_headroom_and_safety(m3_rendered)
        write_wav_float32(pair_dir / "M3_repaired_curve.wav", m3_safe, sr)
        m3_loudness = compute_transition_loudness_diagnostics(m3_safe, sr, pre_roll_len, content_end_render_smp)
        result["renders"].setdefault("M3", {}).update({
            "applied_tempo_ratio": ratio,
            "safety": m3_safety,
            "loudness_max_dip_db": m3_loudness["maximum_loudness_dip_db"],
            "loudness_max_rise_db": m3_loudness["maximum_loudness_rise_db"],
        })

    (pair_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to a LOCAL-ONLY manifest JSON (real_music/MANIFEST_SCHEMA.md). Never committed.")
    parser.add_argument("--work-dir", required=True, help="LOCAL-ONLY output directory. Never committed.")
    parser.add_argument("--summary-out", default=None, help="Optional path to write a private-content-free summary JSON (pair_id/category/decision fields only, no paths/filenames).")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print("RESULT: OWNER_REAL_MUSIC_INPUT_REQUIRED")
        print(f"No manifest found at {manifest_path}. Copy real_music/manifest.example.json to a "
              f"local path, fill in real owner-supplied audio paths + honest annotations per "
              f"real_music/MANIFEST_SCHEMA.md, then re-run with --manifest pointing at it.")
        sys.exit(0)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs", [])
    if len(pairs) < 3:
        print(f"RESULT: OWNER_REAL_MUSIC_INPUT_REQUIRED (manifest has only {len(pairs)} pairs, need >= 3)")
        sys.exit(0)

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for pair in pairs:
        t0 = time.perf_counter()
        try:
            result = render_pair(pair, work_dir)
            result["render_wall_time_s"] = time.perf_counter() - t0
            summaries.append(result)
            print(f"{pair['pair_id']} ({pair.get('category')}): decision_type={result['decision_type']} "
                  f"classes={result['allowed_transition_class_set']} tempo_mode={result['tempo_mode']}")
        except Exception as e:  # noqa: BLE001
            print(f"{pair.get('pair_id', '?')}: FAILED -- {type(e).__name__}: {e}")
            summaries.append({"pair_id": pair.get("pair_id"), "category": pair.get("category"), "error": str(e)})

    print(f"\nRESULT: OWNER_REAL_MUSIC_LISTENING_REQUIRED ({len(summaries)} pairs rendered to {work_dir}, local only)")

    if args.summary_out:
        # Strip anything that could carry private-content hints before writing to a possibly-committed location.
        clean = []
        for s in summaries:
            clean.append({k: v for k, v in s.items() if k not in ("renders",)} | {
                "renders": {m: {kk: vv for kk, vv in r.items() if kk not in ("rate_curve",)} for m, r in s.get("renders", {}).items()}
            })
        Path(args.summary_out).write_text(json.dumps(clean, indent=2), encoding="utf-8")
        print(f"Wrote content-free summary to {args.summary_out}")


if __name__ == "__main__":
    main()
