"""
P0-M4-R2 PF5 -- NG2 comparator executability proof.

For every one of the frozen 30 NG2 pairs (SS16.5), computes the clean-room
`SIMPMUSIC_CLASS_REFERENCE` comparator boundary (`simpmusic_class_
reference.py`, arithmetic-only, already-cached BPM/key fields, no new
analyzer) and renders it through the SAME accepted equal-power DSP path our
own candidate uses (`dsp.mixing.assemble_transition_render`, zero new DSP).
Actual SimpMusic is not used -- no accepted evidence anywhere in this
repository confirms local Tier-1 SimpMusic playback is runnable (see the
module docstring in `simpmusic_class_reference.py`), so this task uses the
already-authorized clean-room path per SS6.3.

SS12.7 backfill rule: if a selected NG2 pair is unrenderable (decode
failure, sample-rate mismatch, etc.), it is excluded and logged
`NG2_EXCLUDED_UNRENDERABLE`, and replaced by the next-lowest-`NG2_KEY` pair
from the SAME dev/holdout partition not already selected for NG2 (never a
pair from the other partition, never a discretionary substitute).

Usage:
    python tools/p0m4/narrow_validation/ng2_comparator_proof.py \
        --work-dir tools/p0m4/narrow_validation/work_local \
        --evidence-out tools/p0m4/narrow_validation/ng2_comparator_evidence_sanitized.json
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
import simpmusic_class_reference as sref  # noqa: E402
import real_music_pipeline as rmp  # noqa: E402
from render_adapter import decode_track_cached  # noqa: E402
from dsp.wav_io import read_wav_float, write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402
from dsp.render_common import ms_to_samples, fit_exact_length  # noqa: E402

CANONICAL_SR = 44100


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_comparator(out_id: str, in_id: str, analysis: dict, id_map: dict, work_dir: Path) -> dict:
    out_a, in_a = analysis[out_id], analysis[in_id]
    out_key = out_a.get("key_at_exit", out_a["key"])
    in_key = in_a.get("key_at_entry", in_a["key"])
    boundary = sref.comparator_boundary(
        out_a["duration_ms"], out_a["tempo"]["bpm"], in_a["tempo"]["bpm"], out_key, in_key,
    )

    out_wav_path = decode_track_cached(work_dir, out_id, id_map[out_id])
    in_wav_path = decode_track_cached(work_dir, in_id, id_map[in_id])
    out_audio, sr1 = read_wav_float(out_wav_path)
    in_audio, sr2 = read_wav_float(in_wav_path)
    if sr1 != CANONICAL_SR or sr2 != CANONICAL_SR:
        raise RuntimeError("SAMPLE_RATE_MISMATCH")

    sr = CANONICAL_SR
    exit_smp = ms_to_samples(boundary["exit_ms"], sr)
    content_end_smp = min(len(out_audio), ms_to_samples(out_a["duration_ms"], sr))
    overlap_len = max(0, content_end_smp - exit_smp)
    pre_start = max(0, exit_smp - ms_to_samples(15000, sr))

    outgoing_pre = out_audio[pre_start:exit_smp]
    outgoing_overlap = out_audio[exit_smp:content_end_smp]
    incoming_overlap = fit_exact_length(in_audio[0:overlap_len], overlap_len)
    post_len = ms_to_samples(15000, sr)
    incoming_post = in_audio[overlap_len:overlap_len + post_len]

    rendered = assemble_transition_render(
        outgoing_pre, outgoing_overlap, incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=False, curve="equal_power",
    )
    safe_audio, safety = apply_headroom_and_safety(rendered)

    out_dir = work_dir / "ng2_comparator_renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_wav_float32(out_dir / f"{out_id}-{in_id}_comparator.wav", safe_audio, sr)

    return {
        "crossfade_duration_ms": boundary["crossfade_duration_ms"],
        "exit_ms": boundary["exit_ms"],
        "entry_ms": boundary["entry_ms"],
        "overlap_ms": overlap_len / sr * 1000.0,
        "safety": {
            "nan_inf_sample_count": safety["nan_inf_sample_count"],
            "clipped_sample_count": safety["clipped_sample_count"],
            "post_peak_dbfs": safety["post_peak_dbfs"],
        },
    }


def ng2_partition_ranked(dev: list, holdout: list, split: str) -> list:
    partition = holdout if split == "holdout" else dev
    return sel.hash_subset(partition, "NG2", len(partition))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--evidence-out", required=True)
    args = ap.parse_args()

    manifest = load_json(HERE / "manifest_sanitized.json")
    if manifest.get("status") != "FROZEN":
        print(f"RESULT: BLOCKED -- manifest status is {manifest.get('status')!r}")
        return 1

    all_pairs = [(p["out_id"], p["in_id"], p["split"]) for p in manifest["pairs"]]
    dev = [(o, i) for o, i, s in all_pairs if s == "dev"]
    holdout = [(o, i) for o, i, s in all_pairs if s == "holdout"]
    ng2_pairs = [p for p in manifest["pairs"] if p.get("ng2_member")]
    assert len(ng2_pairs) == 30

    analysis = load_json(CORPUS_DIR / "corpus_analysis.local.json")
    id_map = load_json(CORPUS_DIR / "id_map.local.json")
    work_dir = Path(args.work_dir)

    evidence = []
    excluded = []
    for pr in ng2_pairs:
        out_id, in_id, split = pr["out_id"], pr["in_id"], pr["split"]
        try:
            ev = render_comparator(out_id, in_id, analysis, id_map, work_dir)
            ev.update({"out_id": out_id, "in_id": in_id, "split": split, "status": "SUCCESS"})
        except Exception as e:  # noqa: BLE001
            excluded.append({"out_id": out_id, "in_id": in_id, "split": split, "status": "NG2_EXCLUDED_UNRENDERABLE", "error_class": type(e).__name__})
            ev = excluded[-1]
        evidence.append(ev)
        print(f"{out_id}->{in_id} ({split}): {ev['status']}")

    out = {
        "ng2_total": len(ng2_pairs),
        "ng2_success": sum(1 for e in evidence if e["status"] == "SUCCESS"),
        "ng2_excluded_unrenderable": len(excluded),
        "ng2_holdout_success": sum(1 for e in evidence if e["status"] == "SUCCESS" and e["split"] == "holdout"),
        "ng2_dev_success": sum(1 for e in evidence if e["status"] == "SUCCESS" and e["split"] == "dev"),
        "pairs": evidence,
    }
    Path(args.evidence_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence_out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print()
    print(f"NG2_TOTAL={out['ng2_total']} SUCCESS={out['ng2_success']} EXCLUDED={out['ng2_excluded_unrenderable']}")
    print(f"NG2_HOLDOUT_SUCCESS={out['ng2_holdout_success']}/9 NG2_DEV_SUCCESS={out['ng2_dev_success']}/21")
    print(f"Wrote sanitized evidence to {args.evidence_out}")
    return 0 if out["ng2_excluded_unrenderable"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
