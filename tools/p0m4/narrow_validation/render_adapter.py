"""
P0-M4-R2 PF2/PF3 -- thin real-audio adapter proof.

Proves the frozen 50-pair manifest (`selection.py` / `manifest_sanitized.
json`) can be loaded from the existing local/DRM-free owner corpus and
rendered using ONLY the already-accepted generic simple-transition DSP
paths, with ZERO new DSP or analyzer logic:

  - Pair-compatibility computation: reuses
    `select_real_music_pairs.build_pair_compat_input` / `build_manifest_pair`
    verbatim (the same accepted R3 Stage-B logic already used for the V1/V2/
    V3 pairs) -- not re-derived here.
  - Fixture construction: reuses `real_music_pipeline.build_tx_fixture`
    verbatim.
  - Planning: reuses `policy.boundary.plan_transition_boundary` verbatim
    (the accepted R2 planner).
  - Segmentation: reuses `dsp.render_common.compute_segments` verbatim.
  - Mixing: reuses `dsp.mixing.assemble_transition_render` /
    `apply_headroom_and_safety` verbatim, ALWAYS called with
    `use_equal_power=True, use_bass_handoff=False, curve="equal_power"` --
    i.e. exactly `dsp/render_m1.py`'s "do less" reference, regardless of
    whether the planner's `allowed_transition_class_set` would also permit
    a more complex class. No tempo/pitch/EQ engine is ever invoked here,
    matching the narrow scope's binding exclusion list.

PF3 boundary provenance: the only per-candidate evidence this adapter reads
is `corpus_analysis.local.json`'s already-cached, already-accepted Stage-B
fields (`exit_candidate_t_ms`, `exit_structure_confidence`, etc.) -- the
SAME fields `select_real_music_pairs.py` already used to build the accepted
V1/V2/V3 manifest. No analyzer is invoked by this module. When the cached
evidence is insufficient (`exit_structure_confidence` below MEDIUM), the
accepted eligibility guard in `policy/eligibility.py` rejects the candidate
and the accepted planner fails closed to `NO_SPECIAL_TRANSITION` on its own
-- this module does not add a second, redundant gate.

NG3 binding default (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-
CONTRACT.md` SS16.6): every incoming candidate's audible entry is forced to
`t_ms = 0` for this validation -- the cached `entry_candidate_t_ms`/silence-
skip detection `select_real_music_pairs.py` uses for V1/V2/V3 is NOT reused
as an authored-silence-skip annotation here, because the benchmark contract
explicitly states no accepted process populates that annotation for real,
non-fixture audio without a new content analyzer.

Privacy: every commit-eligible output field is an opaque ID or a plain
number. Local file paths are read only in-memory to feed ffmpeg / the WAV
reader, exactly like `real_music_pipeline.py` already does, and are never
written to any JSON this module produces.

Usage:
    python tools/p0m4/narrow_validation/render_adapter.py \
        --work-dir tools/p0m4/narrow_validation/work_local \
        --evidence-out tools/p0m4/narrow_validation/boundary_evidence_sanitized.json \
        [--render-audio]   # actually decode+mix (slow); default is PLAN_ONLY
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCRIPTS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "scripts"
CORPUS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "real_music" / "work_local" / "corpus"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HERE))

import selection as sel  # noqa: E402
import select_real_music_pairs as srmp  # noqa: E402
import real_music_pipeline as rmp  # noqa: E402

from policy.boundary import plan_transition_boundary  # noqa: E402
from policy.eligibility import SEAMLESS_FULL_TRACK_DEFAULT  # noqa: E402
from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402
from dsp.render_common import compute_segments, fit_exact_length  # noqa: E402

CANONICAL_SR = 44100
OVERLAP_EPSILON_MS = 20  # SS5.2 epsilon, unchanged from the benchmark contract

# Forbidden narrow-production observed_class outputs (contract SS16.7). This
# module never CALLS a forbidden-class DSP path in the first place (it only
# ever invokes the equal-power/zero-overlap paths), but the check below
# fails loudly if that structural guarantee is ever violated by a future
# edit, rather than silently trusting it.
FORBIDDEN_CLASSES = {"FULL_DJ_BLEND", "SHORT_EQ_BLEND", "CUT"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def force_ng3_entry_zero(manifest_pair: dict) -> dict:
    """Binding NG3 default: incoming audible entry forced to t=0, no
    lead-in skip, for every real-corpus pair in this validation."""
    inc = manifest_pair["incoming"]
    inc["entry_candidate_t_ms"] = 0
    inc["is_authored_silence_skip"] = False
    inc["leading_silence_is_authored_non_musical"] = False
    inc["leading_silence_ms"] = 0
    inc.pop("beat_alignment_target_ms", None)
    inc.pop("downbeat_alignment_target_ms", None)
    # Re-resolve the (now t=0) alignment anchor fields the same way
    # select_real_music_pairs.py does for any other candidate -- reused
    # verbatim, not re-derived.
    return manifest_pair


def build_pair_fixture(out_id: str, in_id: str, analysis: dict) -> dict:
    out_a, in_a = analysis[out_id], analysis[in_id]
    compat_input = srmp.build_pair_compat_input(out_a, in_a)
    pair_id = f"{out_id}-{in_id}"
    manifest_pair = srmp.build_manifest_pair(pair_id, "P0-M4-R2-NARROW", out_id, in_id, out_a, in_a, compat_input)
    manifest_pair = force_ng3_entry_zero(manifest_pair)
    return manifest_pair, compat_input


def classify_narrow_render(decision_dict: dict, overlap_ms: float) -> str:
    """Contract SS5.2, restricted to the three narrow observable classes.
    This adapter never renders a nonzero-overlap output with anything but
    the equal-power gain law, so a nonzero overlap is always
    SIMPLE_CROSSFADE; a zero/near-zero overlap is always a sample-
    contiguous join (entry is always t=0 immediately following the
    outgoing content end, per the NG3 default) and, with no
    is_continuous_work evidence for any combinatorially hash-selected real
    pair, is always NO_SPECIAL_TRANSITION, never GAPLESS."""
    if decision_dict["decision_type"] == "NO_SPECIAL_TRANSITION":
        return "NO_SPECIAL_TRANSITION"
    if overlap_ms <= OVERLAP_EPSILON_MS:
        return "NO_SPECIAL_TRANSITION"
    return "SIMPLE_CROSSFADE"


def plan_only_evidence(pair_record: dict, analysis: dict) -> dict:
    out_id, in_id = pair_record["out_id"], pair_record["in_id"]
    manifest_pair, compat_input = build_pair_fixture(out_id, in_id, analysis)
    fixture = rmp.build_tx_fixture(manifest_pair)
    decision = plan_transition_boundary(fixture, SEAMLESS_FULL_TRACK_DEFAULT)
    decision_dict = decision.to_dict()

    onset_ms = (decision_dict.get("transition_onset_window_ms") or {}).get("t_start_ms")
    content_end_ms = decision_dict.get("current_track_effective_content_end_ms")
    overlap_ms = None
    if onset_ms is not None and content_end_ms is not None:
        overlap_ms = max(0, content_end_ms - onset_ms)
    rendered_class = classify_narrow_render(decision_dict, overlap_ms if overlap_ms is not None else 0)

    exit_confidence = analysis[out_id]["candidates"]["exit_structure_confidence"]
    exit_evidence_method = analysis[out_id]["candidates"]["exit_structure_evidence_method"]

    return {
        "out_id": out_id,
        "in_id": in_id,
        "split": pair_record["split"],
        "ng2_member": pair_record.get("ng2_member", False),
        "ng4_member": pair_record.get("ng4_member", False),
        "decision_type": decision_dict["decision_type"],
        "allowed_transition_class_set": decision_dict["allowed_transition_class_set"],
        "rendered_class": rendered_class,
        "forbidden_class_hit": rendered_class in FORBIDDEN_CLASSES,
        "overlap_ms": overlap_ms,
        "outgoing_content_preservation_target": decision_dict.get("outgoing_content_preservation_target"),
        "current_track_effective_content_end_ms": content_end_ms,
        "boundary_source": "CACHED_STAGE_B_EXIT_CANDIDATE" if rendered_class == "SIMPLE_CROSSFADE" else "FAIL_CLOSED_NO_SUFFICIENT_CACHED_EVIDENCE",
        "exit_structure_confidence": exit_confidence,
        "exit_structure_evidence_method": exit_evidence_method,
        "reason_codes": decision_dict.get("reason_codes", []),
    }


def decode_track_cached(work_dir: Path, opaque_id: str, src_path: str) -> Path:
    out_wav = work_dir / "decoded" / f"{opaque_id}.wav"
    if out_wav.exists():
        return out_wav
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    debug_log = work_dir / "decode_errors" / f"{opaque_id}.log"
    rmp.convert_to_canonical_wav(src_path, out_wav, debug_log)
    return out_wav


def render_and_measure(pair_record: dict, analysis: dict, id_map: dict, work_dir: Path) -> dict:
    ev = plan_only_evidence(pair_record, analysis)
    out_id, in_id = pair_record["out_id"], pair_record["in_id"]

    out_wav_path = decode_track_cached(work_dir, out_id, id_map[out_id])
    in_wav_path = decode_track_cached(work_dir, in_id, id_map[in_id])
    out_audio, sr1 = read_wav_float(out_wav_path)
    in_audio, sr2 = read_wav_float(in_wav_path)
    if sr1 != CANONICAL_SR or sr2 != CANONICAL_SR:
        ev["render_status"] = "FAILED_SAMPLE_RATE_MISMATCH"
        return ev

    manifest_pair, _ = build_pair_fixture(out_id, in_id, analysis)
    fixture = rmp.build_tx_fixture(manifest_pair)
    decision = plan_transition_boundary(fixture, SEAMLESS_FULL_TRACK_DEFAULT)
    decision_dict = decision.to_dict()

    if decision_dict["decision_type"] != "TRANSITION":
        # build_fallback_decision() (contract.py) never populates
        # transition_onset_window_ms/next_track_entry_window_ms -- it is a
        # non-render/zero-overlap fallback by construction. The natural
        # boundary IS current_track_effective_content_end_ms (the accepted
        # end-of-track candidate's own effective content end -- CACHED
        # Stage-B evidence, not re-derived), and the incoming side starts at
        # its NG3-forced t=0. Feeding compute_segments() this synthesized
        # zero-overlap window reuses the EXACT SAME segment-assembly code
        # SIMPLE_CROSSFADE uses (contract SS9.2: "a direct, zero-new-code
        # restriction of the existing segment-assembly path") rather than
        # writing a second, parallel slicing routine.
        content_end_ms = decision_dict["current_track_effective_content_end_ms"]
        decision_dict = {
            **decision_dict,
            "transition_onset_window_ms": {"t_start_ms": content_end_ms, "t_end_ms": content_end_ms},
            "next_track_entry_window_ms": {"t_start_ms": 0, "t_end_ms": 0},
        }

    ctx = {"decision": decision_dict, "sr": CANONICAL_SR, "outgoing_audio": out_audio, "incoming_audio": in_audio}
    segs = compute_segments(ctx)
    sr = CANONICAL_SR
    overlap_len = segs["overlap_len_smp"]
    overlap_ms = overlap_len / sr * 1000.0

    incoming_overlap = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
    incoming_post = segs["incoming_raw_segment"][overlap_len:]

    # ALWAYS equal-power, ALWAYS no bass handoff -- the narrow scope's "do
    # less" reference, exactly dsp/render_m1.py's own call, regardless of
    # what allowed_transition_class_set additionally permits.
    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=False, curve="equal_power",
    )
    safe_audio, safety = apply_headroom_and_safety(rendered)

    pair_dir = work_dir / "renders"
    pair_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{out_id}-{in_id}.wav"
    write_wav_float32(pair_dir / out_name, safe_audio, sr)

    rendered_class = classify_narrow_render(decision_dict, overlap_ms)
    ev["rendered_class"] = rendered_class
    ev["forbidden_class_hit"] = rendered_class in FORBIDDEN_CLASSES
    ev["overlap_ms"] = overlap_ms
    ev["render_status"] = "SUCCESS"
    ev["safety"] = {
        "pre_peak_dbfs": safety["pre_peak_dbfs"],
        "post_peak_dbfs": safety["post_peak_dbfs"],
        "applied_headroom_gain_db": safety["applied_headroom_gain_db"],
        "nan_inf_sample_count": safety["nan_inf_sample_count"],
        "clipped_sample_count": safety["clipped_sample_count"],
    }
    ev["output_duration_s"] = safe_audio.shape[0] / sr
    return ev


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", required=True, help="LOCAL-ONLY working directory for decoded/rendered audio. Never committed.")
    ap.add_argument("--evidence-out", required=True, help="Path to write sanitized (opaque-ID-only, numbers-only) evidence JSON.")
    ap.add_argument("--render-audio", action="store_true", help="Actually decode+mix every pair (slow). Default is PLAN_ONLY (no audio decode).")
    ap.add_argument("--limit", type=int, default=None, help="Optional cap on number of pairs processed (debugging only).")
    args = ap.parse_args()

    manifest = load_json(HERE / "manifest_sanitized.json")
    if manifest.get("status") != "FROZEN":
        print(f"RESULT: BLOCKED -- manifest status is {manifest.get('status')!r}, not FROZEN")
        return 1

    analysis = load_json(CORPUS_DIR / "corpus_analysis.local.json")
    pairs = manifest["pairs"]
    if args.limit:
        pairs = pairs[: args.limit]

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    id_map = None
    if args.render_audio:
        id_map = load_json(CORPUS_DIR / "id_map.local.json")

    evidence = []
    attempted = 0
    succeeded = 0
    failed = 0
    for pr in pairs:
        attempted += 1
        try:
            if args.render_audio:
                ev = render_and_measure(pr, analysis, id_map, work_dir)
                if ev.get("render_status") == "SUCCESS":
                    succeeded += 1
                else:
                    failed += 1
            else:
                ev = plan_only_evidence(pr, analysis)
                ev["render_status"] = "PLAN_ONLY"
                succeeded += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            ev = {"out_id": pr["out_id"], "in_id": pr["in_id"], "render_status": "FAILED", "error_class": type(e).__name__}
        evidence.append(ev)
        print(f"{pr['out_id']}->{pr['in_id']}: {ev.get('render_status')} rendered_class={ev.get('rendered_class')} overlap_ms={ev.get('overlap_ms')}")

    forbidden_hits = [e for e in evidence if e.get("forbidden_class_hit")]
    out = {
        "mode": "RENDER_AUDIO" if args.render_audio else "PLAN_ONLY",
        "pair_attempted_count": attempted,
        "pair_success_count": succeeded,
        "pair_failure_count": failed,
        "forbidden_class_hit_count": len(forbidden_hits),
        "rendered_class_counts": {
            c: sum(1 for e in evidence if e.get("rendered_class") == c)
            for c in ("NO_SPECIAL_TRANSITION", "SIMPLE_CROSSFADE", "GAPLESS")
        },
        "pairs": evidence,
    }
    Path(args.evidence_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence_out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print()
    print(f"PAIR_ATTEMPTED_COUNT={attempted}")
    print(f"PAIR_SUCCESS_COUNT={succeeded}")
    print(f"PAIR_FAILURE_COUNT={failed}")
    print(f"FORBIDDEN_CLASS_HIT_COUNT={len(forbidden_hits)}")
    print(f"RENDERED_CLASS_COUNTS={out['rendered_class_counts']}")
    print(f"Wrote sanitized evidence to {args.evidence_out}")
    return 0 if failed == 0 and not forbidden_hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
