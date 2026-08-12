"""
Tier-B real-music private validation harness (PM OWNER LISTENING
DIRECTION UPDATE, Task 3). Consumes an owner-supplied, LOCAL-ONLY manifest
(real_music/MANIFEST_SCHEMA.md) pointing at local WAV/FLAC/MP3/M4A files,
converts them to canonical 44100Hz stereo float32 WAV, builds a real
transition-policy fixture from the manifest's annotations, calls the SAME
accepted R2 planner every other scenario in this pass uses
(`policy.boundary.plan_transition_boundary`), applies this pass's tempo-
mode selection (dsp/tempo_modes.py), and renders a same-boundary A/B/C
loudness-curve + tempo comparator (PM REVIEW "PRE-REAL-MUSIC REPAIR
REQUIRED" R4):

  A -- current equal-power reference, no tempo correction.
  B -- late-outgoing-hold candidate (dsp/mixing.py `late_hold`), no tempo
       correction -- isolates the gain-curve variable exactly like
       scripts/render_loudness_shootout.py does for the synthetic pass.
  C -- conditional tempo-match candidate, rendered ONLY when FULL_DJ_BLEND
       is allowed and dsp.tempo_modes.select_tempo_mode says a real
       correction is warranted for this boundary. Uses ffmpeg Rubber Band
       (QUALITY_REFERENCE_ONLY engine, no browser round-trip needed) at
       the planner's own `required_tempo_ratio`, the SAME onset/entry/
       overlap boundary as A/B, and NEVER the not-yet-pitch-preserving
       MATCH_AND_RETURN_TO_NATIVE ramp (dsp/tempo_modes.py's own gate
       already prevents that mode from ever being selected; this script
       adds a second, redundant fail-closed check before it would ever
       call dsp.tempo_ramp.apply_return_to_native_ramp, belt-and-braces
       against a future regression in that gate). M2 (Signalsmith) is NOT
       rendered automatically -- it requires the same manual browser
       round-trip every synthetic scenario in this pass required; this
       script prints the exact next-step instructions instead of silently
       skipping it (see `m2_manual_instructions`, deliberately excluded
       from `--summary-out`, R2 repair below).

PM REVIEW "PRE-REAL-MUSIC REPAIR REQUIRED" R2 (private-path-leak repair):
no raw exception text, ffmpeg stderr, or filesystem path is ever placed in
a string that could reach `--summary-out` or stdout. Every failure is
converted to one of a small enumerated set of error codes
(INPUT_DECODE_FAILED / INVALID_MANIFEST / PLANNER_REJECTED /
RENDER_FAILED); only the error CODE and, at most, the offending
exception's CLASS NAME are ever surfaced. `--summary-out` is built from an
explicit field ALLOWLIST (never a denylist) so a newly added field can
never leak by omission. ffmpeg's own stderr (which routinely embeds the
input path/filename) is written only to a LOCAL-ONLY per-pair debug log
file inside `--work-dir` (already gitignored), never printed, never
included in any exception message, never written to `--summary-out`.

PM REVIEW R3 (truthful success accounting): the script tracks
`pair_attempted_count` / `pair_success_count` / `pair_failure_count`
explicitly and only ever reports `OWNER_REAL_MUSIC_LISTENING_REQUIRED`
when every category `real_music/MANIFEST_SCHEMA.md` requires
(`close_tempo_minimal_stretch`, `conditional_tempo_correction`,
`incompatible_downgrade`) has at least one pair that rendered
successfully. Otherwise it reports a truthful `PARTIAL` or
`OWNER_REAL_MUSIC_INPUT_REQUIRED` with machine-readable
`failure_reason_codes` -- it can never again claim "N pairs rendered" from
`len(summaries)` when N pairs actually failed before rendering.

No audio, path, or filename from a real manifest is ever written to a
committed location.

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
from dataclasses import asdict
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
)
from dsp.tempo_modes import select_tempo_mode, NATIVE_TEMPO, MATCH_AND_RETURN_TO_NATIVE  # noqa: E402
from dsp.tempo_ramp import ramp_is_safe  # noqa: E402
from dsp.render_m3_rubberband import ffmpeg_rubberband_stretch, FFMPEG_BIN  # noqa: E402

from policy.boundary import plan_transition_boundary  # noqa: E402
from policy.eligibility import SEAMLESS_FULL_TRACK_DEFAULT  # noqa: E402

CANONICAL_SR = 44100
POST_ROLL_S = 15.0
LOUDNESS_CURVE_CANDIDATE = "late_hold"  # this pass's evidence-backed CANDIDATE only -- not yet an accepted product default (R4)

ERR_INPUT_DECODE_FAILED = "INPUT_DECODE_FAILED"
ERR_INVALID_MANIFEST = "INVALID_MANIFEST"
ERR_PLANNER_REJECTED = "PLANNER_REJECTED"
ERR_RENDER_FAILED = "RENDER_FAILED"
ERR_ENVIRONMENT_BLOCKED = "ENVIRONMENT_BLOCKED"

REQUIRED_CATEGORIES = (
    "close_tempo_minimal_stretch",
    "conditional_tempo_correction",
    "incompatible_downgrade",
)

# R2 repair: explicit ALLOWLIST of fields ever written to --summary-out.
# Deliberately excludes "m2_manual_instructions" (embeds a local work-dir
# path) and any raw exception text -- a newly added result field can never
# leak into the committed-safe summary just by being added to `result`.
SUMMARY_SAFE_TOP_LEVEL_KEYS = (
    "pair_id", "category", "status", "decision_type",
    "allowed_transition_class_set", "required_tempo_ratio", "tempo_mode",
    "tempo_mode_evidence", "onset_ms", "content_end_ms", "entry_ms",
    "overlap_duration_ms", "render_wall_time_s", "error_code",
)
SUMMARY_SAFE_RENDER_KEYS = (
    "curve", "safety", "loudness_max_dip_db", "loudness_max_rise_db",
    "applied_tempo_ratio",
)


class RealMusicPipelineError(Exception):
    """
    R2 repair: the ONLY exception type this script raises for a
    caught/expected failure. Carries an enumerated `code` and, at most, a
    short human `detail` that this module guarantees never contains a
    filesystem path, filename, or raw subprocess/ffmpeg output -- callers
    must never pass `str(some_other_exception)` as `detail`.
    """

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def convert_to_canonical_wav(src_path: str, dst_path: Path, debug_log_path: Path) -> None:
    """
    Converts via ffmpeg. On failure, the FULL ffmpeg stderr (which
    routinely embeds the source path/filename) is written ONLY to
    `debug_log_path` -- a file inside the gitignored, LOCAL-ONLY
    `--work-dir` -- never printed, never raised, never written anywhere
    that could reach `--summary-out` (R2 repair).
    """
    cmd = [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error",
           "-i", src_path, "-ac", "2", "-ar", str(CANONICAL_SR), "-c:a", "pcm_f32le", str(dst_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        debug_log_path.write_text(result.stderr or "", encoding="utf-8", errors="replace")
        raise RealMusicPipelineError(ERR_INPUT_DECODE_FAILED, f"ffmpeg exit code {result.returncode}; see local {debug_log_path.name} for detail")


def build_tx_fixture(pair: dict) -> dict:
    try:
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
                # PM STAGE B REVIEW R4 repair: wire the manifest's real
                # detected leading-silence evidence through to
                # policy.boundary.incoming_effective_content_start_ms so a
                # genuinely-detected nonzero entry candidate with
                # is_authored_silence_skip=True is actually ACCEPTED by
                # policy.boundary._entry_eligibility instead of being
                # rejected as "skips meaningful intro without evidence" --
                # this field was previously never populated, which forced
                # every real-music manifest to use entry_candidate_t_ms=0
                # regardless of what the analyzer actually detected.
                "leading_silence_is_authored_non_musical": inc.get("leading_silence_is_authored_non_musical", False),
                "leading_silence_ms": inc.get("leading_silence_ms", 0),
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
    except KeyError as e:
        raise RealMusicPipelineError(ERR_INVALID_MANIFEST, f"missing required manifest field {e}") from e


def render_curve_variant(segs: dict, sr: int, curve: str, incoming_overlap, incoming_post,
                          use_bass_handoff: bool, pair_dir: Path, out_name: str,
                          pre_roll_len: int, content_end_render_smp: int) -> dict:
    from dsp.loudness_diagnostics import compute_transition_loudness_diagnostics
    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=use_bass_handoff, curve=curve,
    )
    safe_audio, safety = apply_headroom_and_safety(rendered)
    write_wav_float32(pair_dir / out_name, safe_audio, sr)
    loudness = compute_transition_loudness_diagnostics(safe_audio, sr, pre_roll_len, content_end_render_smp)
    return {
        "curve": curve,
        "safety": safety,
        "loudness_max_dip_db": loudness["maximum_loudness_dip_db"],
        "loudness_max_rise_db": loudness["maximum_loudness_rise_db"],
    }


def render_pair(pair: dict, work_dir: Path) -> dict:
    pair_id = pair["pair_id"]
    pair_dir = work_dir / pair_id
    pair_dir.mkdir(parents=True, exist_ok=True)

    out_wav = pair_dir / "outgoing.wav"
    in_wav = pair_dir / "incoming.wav"
    convert_to_canonical_wav(pair["outgoing"]["path"], out_wav, pair_dir / "outgoing_ffmpeg_error.log")
    convert_to_canonical_wav(pair["incoming"]["path"], in_wav, pair_dir / "incoming_ffmpeg_error.log")

    try:
        out_audio, sr1 = read_wav_float(out_wav)
        in_audio, sr2 = read_wav_float(in_wav)
    except Exception as e:  # noqa: BLE001
        raise RealMusicPipelineError(ERR_INPUT_DECODE_FAILED, type(e).__name__) from e
    if sr1 != CANONICAL_SR or sr2 != CANONICAL_SR:
        raise RealMusicPipelineError(ERR_INPUT_DECODE_FAILED, f"conversion did not produce canonical {CANONICAL_SR}Hz audio")

    fixture = build_tx_fixture(pair)
    try:
        decision = plan_transition_boundary(fixture, SEAMLESS_FULL_TRACK_DEFAULT)
    except Exception as e:  # noqa: BLE001
        raise RealMusicPipelineError(ERR_PLANNER_REJECTED, type(e).__name__) from e
    decision_dict = asdict(decision)
    (pair_dir / "planner_decision.json").write_text(json.dumps(decision_dict, indent=2), encoding="utf-8")

    tempo_mode, tempo_evidence = select_tempo_mode(decision_dict, prefer_return_to_native=True)
    assert tempo_mode != MATCH_AND_RETURN_TO_NATIVE, (
        "select_tempo_mode must never return MATCH_AND_RETURN_TO_NATIVE while its ramp_is_safe "
        "gate is unvalidated for this ratio -- see dsp/tempo_modes.py R1 repair"
    )

    try:
        ctx = {"decision": decision_dict, "sr": CANONICAL_SR, "outgoing_audio": out_audio, "incoming_audio": in_audio}
        segs = compute_segments(ctx, post_roll_s=POST_ROLL_S)
        sr = CANONICAL_SR
        overlap_len = segs["overlap_len_smp"]

        result = {
            "pair_id": pair_id,
            "category": pair.get("category"),
            "status": "SUCCESS",
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

        incoming_overlap_native = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
        incoming_post_native = segs["incoming_raw_segment"][overlap_len:]
        pre_roll_len = segs["onset_smp"] - max(0, segs["onset_smp"] - ms_to_samples(15000, sr))
        content_end_render_smp = pre_roll_len + overlap_len

        # R4 -- A: current equal-power reference, no tempo correction (always rendered).
        result["renders"]["A"] = render_curve_variant(
            segs, sr, "equal_power", incoming_overlap_native, incoming_post_native,
            False, pair_dir, "A_equal_power_reference.wav", pre_roll_len, content_end_render_smp,
        )
        # R4 -- B: late-outgoing-hold loudness-curve CANDIDATE, no tempo correction (always rendered, same boundary as A).
        result["renders"]["B"] = render_curve_variant(
            segs, sr, LOUDNESS_CURVE_CANDIDATE, incoming_overlap_native, incoming_post_native,
            False, pair_dir, "B_late_hold_candidate.wav", pre_roll_len, content_end_render_smp,
        )

        full_dj_allowed = "FULL_DJ_BLEND" in decision_dict["allowed_transition_class_set"]
        result["m2_manual_instructions"] = (
            None if not full_dj_allowed else
            f"FULL_DJ_BLEND is allowed for {pair_id} -- to render M2 (Signalsmith), run the same "
            f"prepare/finish browser-bridge flow dsp/render_m2_signalsmith.py uses for the synthetic "
            f"scenarios, pointed at this pair's local work-dir incoming.wav from "
            f"entry_ms={segs['entry_ms']} with rate={decision_dict.get('required_tempo_ratio')} "
            f"(not run automatically by this script)."
        )

        # R4 -- C: conditional tempo-match candidate, SAME boundary, rendered only when a real
        # correction is actually warranted for this pair (never the unsafe return-to-native ramp).
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

            in_path = pair_dir / "c_stretch_input.wav"
            out_path = pair_dir / "c_stretch_output.wav"
            write_wav_float32(in_path, stretch_input, sr)
            ffmpeg_rubberband_stretch(in_path, out_path, ratio, pitch_scale)
            stretched, sr_out = read_wav_float(out_path)
            if sr_out != sr:
                raise SampleRateMismatchError(f"{pair_id}: C-candidate ffmpeg output sr {sr_out} != {sr}")

            align_offset_ms = compute_alignment_offset_ms(decision_dict, segs, ratio)
            stretched_aligned = apply_time_offset(stretched, align_offset_ms, sr)
            incoming_overlap_c = fit_exact_length(stretched_aligned[:overlap_len], overlap_len)
            incoming_post_c = stretched_aligned[overlap_len:overlap_len + ms_to_samples(POST_ROLL_S * 1000, sr)]

            # Belt-and-braces (R1): even though select_tempo_mode already guarantees
            # tempo_mode != MATCH_AND_RETURN_TO_NATIVE today, never apply that ramp here
            # without independently re-checking its own safety gate first.
            if tempo_mode == MATCH_AND_RETURN_TO_NATIVE:
                safe, _safety_evidence = ramp_is_safe(ratio)
                if not safe:
                    raise RealMusicPipelineError(ERR_RENDER_FAILED, "return-to-native ramp selected but ramp_is_safe reports unsafe -- refusing to render")

            result["renders"]["C"] = render_curve_variant(
                segs, sr, LOUDNESS_CURVE_CANDIDATE, incoming_overlap_c, incoming_post_c,
                True, pair_dir, "C_conditional_tempo_candidate.wav", pre_roll_len, content_end_render_smp,
            )
            result["renders"]["C"]["applied_tempo_ratio"] = ratio

        (pair_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    except RealMusicPipelineError:
        raise
    except Exception as e:  # noqa: BLE001
        # R2 repair: never propagate str(e) -- a render/alignment/subprocess
        # failure this deep may embed a local work-dir path (e.g. ffmpeg
        # rubberband stderr). Only the exception's class name crosses this
        # boundary.
        raise RealMusicPipelineError(ERR_RENDER_FAILED, type(e).__name__) from e


def sanitize_summary_entry(entry: dict) -> dict:
    """R2 repair: explicit ALLOWLIST -- see SUMMARY_SAFE_* above."""
    clean = {k: entry[k] for k in SUMMARY_SAFE_TOP_LEVEL_KEYS if k in entry}
    if "renders" in entry:
        clean["renders"] = {
            method: {k: v for k, v in r.items() if k in SUMMARY_SAFE_RENDER_KEYS}
            for method, r in entry["renders"].items()
        }
    return clean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to a LOCAL-ONLY manifest JSON (real_music/MANIFEST_SCHEMA.md). Never committed.")
    parser.add_argument("--work-dir", required=True, help="LOCAL-ONLY output directory. Never committed.")
    parser.add_argument("--summary-out", default=None, help="Optional path to write a private-content-free summary JSON (explicit field allowlist, no paths/filenames -- see SUMMARY_SAFE_* in this file).")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print("RESULT: OWNER_REAL_MUSIC_INPUT_REQUIRED")
        print(f"No manifest found at {manifest_path}. Copy real_music/manifest.example.json to a "
              f"local path, fill in real owner-supplied audio paths + honest annotations per "
              f"real_music/MANIFEST_SCHEMA.md, then re-run with --manifest pointing at it.")
        sys.exit(0)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("RESULT: OWNER_REAL_MUSIC_INPUT_REQUIRED")
        print(f"RESULT_REASON_CODE: {ERR_INVALID_MANIFEST}")
        print("Manifest file exists but is not valid JSON.")
        sys.exit(0)

    pairs = manifest.get("pairs", [])
    if len(pairs) < 1:
        print(f"RESULT: OWNER_REAL_MUSIC_INPUT_REQUIRED")
        print(f"RESULT_REASON_CODE: {ERR_INVALID_MANIFEST}")
        print("Manifest has no pairs.")
        sys.exit(0)
    # PM STAGE B REVIEW REPAIR: previously required len(pairs) >= 3 up
    # front, which made the missing_categories/PARTIAL accounting logic
    # below (already correctly designed for "some but not all required
    # categories succeeded") unreachable whenever honest pair selection
    # legitimately found fewer than 3 valid categories (see
    # select_real_music_pairs.py -- selection must reject rather than
    # fabricate a category with no valid pair). A manifest may now contain
    # 1 or 2 pairs; the per-category success accounting further below
    # still reports the truthful PARTIAL/OWNER_REAL_MUSIC_LISTENING_REQUIRED
    # result, never claiming a category succeeded that was never attempted.

    if not FFMPEG_BIN or not Path(FFMPEG_BIN).exists():
        print("RESULT: BLOCKED")
        print(f"RESULT_REASON_CODE: {ERR_ENVIRONMENT_BLOCKED}")
        print("ffmpeg binary not found -- cannot convert or stretch real-music input.")
        sys.exit(0)

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    attempted = 0
    succeeded = 0
    failed = 0
    failure_reason_codes = []
    succeeded_categories = set()
    summaries = []

    for pair in pairs:
        attempted += 1
        t0 = time.perf_counter()
        try:
            result = render_pair(pair, work_dir)
            result["render_wall_time_s"] = time.perf_counter() - t0
            summaries.append(result)
            succeeded += 1
            succeeded_categories.add(pair.get("category"))
            print(f"{pair['pair_id']} ({pair.get('category')}): SUCCESS decision_type={result['decision_type']} "
                  f"classes={result['allowed_transition_class_set']} tempo_mode={result['tempo_mode']}")
        except RealMusicPipelineError as e:
            failed += 1
            failure_reason_codes.append(e.code)
            summaries.append({"pair_id": pair.get("pair_id"), "category": pair.get("category"), "status": "FAILED", "error_code": e.code})
            print(f"{pair.get('pair_id', '?')} ({pair.get('category')}): FAILED -- {e.code}")
        except Exception as e:  # noqa: BLE001
            # Defense in depth: render_pair() should only ever raise
            # RealMusicPipelineError, but never let an unexpected exception's
            # message (which could embed a path) reach stdout either.
            failed += 1
            failure_reason_codes.append(ERR_RENDER_FAILED)
            summaries.append({"pair_id": pair.get("pair_id"), "category": pair.get("category"), "status": "FAILED", "error_code": ERR_RENDER_FAILED})
            print(f"{pair.get('pair_id', '?')} ({pair.get('category')}): FAILED -- {ERR_RENDER_FAILED} ({type(e).__name__})")

    print(f"\nPAIR_ATTEMPTED_COUNT={attempted}")
    print(f"PAIR_SUCCESS_COUNT={succeeded}")
    print(f"PAIR_FAILURE_COUNT={failed}")

    missing_categories = sorted(set(REQUIRED_CATEGORIES) - succeeded_categories)
    if succeeded > 0 and not missing_categories:
        status = "OWNER_REAL_MUSIC_LISTENING_REQUIRED"
        print(f"RESULT: {status} ({succeeded}/{attempted} pairs rendered to {work_dir}, local only; "
              f"all required categories {REQUIRED_CATEGORIES} have a successful render)")
    elif succeeded > 0:
        status = "PARTIAL"
        print(f"RESULT: {status} ({succeeded}/{attempted} pairs rendered; missing required categories: {missing_categories})")
    else:
        status = "OWNER_REAL_MUSIC_INPUT_REQUIRED"
        print(f"RESULT: {status} (0/{attempted} pairs rendered successfully)")
    if failure_reason_codes:
        print(f"FAILURE_REASON_CODES={sorted(set(failure_reason_codes))}")

    if args.summary_out:
        clean = [sanitize_summary_entry(s) for s in summaries]
        out = {
            "result": status,
            "pair_attempted_count": attempted,
            "pair_success_count": succeeded,
            "pair_failure_count": failed,
            "missing_required_categories": missing_categories,
            "failure_reason_codes": sorted(set(failure_reason_codes)),
            "pairs": clean,
        }
        Path(args.summary_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote content-free summary to {args.summary_out}")


if __name__ == "__main__":
    main()
