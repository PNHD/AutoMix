"""
P0-M5-R1 Phase B -- one-time per-track Beat This analysis pass over the
existing authorized owner corpus (the same 100 opaque-ID `RM###` tracks
P0-M4-R2 already used).

For each opaque track: decode once (ffmpeg, canonical 44100Hz stereo
float32 -- reuses `real_music_pipeline.convert_to_canonical_wav`, no new
decode logic), run Beat This once (`beat_this_runtime.analyze_file`), and
cache the full beats/downbeats arrays LOCALLY ONLY
(`work_local/beat_cache/<opaque_id>.json`) -- never committed, since
per-track beat timing arrays are audio-analysis output an owner could in
principle reconstruct provenance from combined with other data; tracked
output is a SANITIZED AGGREGATE (opaque ID + counts/derived scalars only,
no raw timing arrays) per Issue #10's privacy policy.

This is the ONLY new corpus analyzer pass this task authorizes (Issue #10
Phase B: "This is the only new corpus analyzer pass authorized in this
task"). No per-song threshold iteration.

Usage:
    python tools/p0m5/apple_like_vertical_slice/corpus_beat_analysis.py \
        --decoded-cache tools/p0m5/apple_like_vertical_slice/work_local/decoded \
        --beat-cache tools/p0m5/apple_like_vertical_slice/work_local/beat_cache \
        --aggregate-out tools/p0m5/apple_like_vertical_slice/beat_analysis_aggregate_sanitized.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCRIPTS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "scripts"
CORPUS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "real_music" / "work_local" / "corpus"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HERE))

import real_music_pipeline as rmp  # noqa: E402
import beat_this_runtime as bt  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bpm_series(times_s: list) -> list:
    """Instantaneous BPM from consecutive downbeat (or beat) intervals."""
    out = []
    for a, b in zip(times_s, times_s[1:]):
        interval = b - a
        if interval > 0:
            out.append(60.0 / interval)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decoded-cache", required=True)
    ap.add_argument("--beat-cache", required=True)
    ap.add_argument("--aggregate-out", required=True)
    ap.add_argument("--torch-home", default=str(HERE / "work_local" / "torch_cache"))
    ap.add_argument("--limit", type=int, default=None, help="debug only: cap number of tracks processed")
    args = ap.parse_args()

    os.environ.setdefault("TORCH_HOME", args.torch_home)

    id_map = load_json(CORPUS_DIR / "id_map.local.json")
    ids = sorted(id_map.keys())
    if args.limit:
        ids = ids[: args.limit]

    decoded_dir = Path(args.decoded_cache)
    beat_dir = Path(args.beat_cache)
    decoded_dir.mkdir(parents=True, exist_ok=True)
    beat_dir.mkdir(parents=True, exist_ok=True)

    aggregate = {}
    t_start = time.time()
    for i, opaque_id in enumerate(ids, start=1):
        beat_cache_path = beat_dir / f"{opaque_id}.json"
        if beat_cache_path.exists():
            cached = load_json(beat_cache_path)
            aggregate[opaque_id] = cached["summary"]
            print(f"[{i}/{len(ids)}] {opaque_id}: CACHED status={cached['summary']['status']}")
            continue

        wav_path = decoded_dir / f"{opaque_id}.wav"
        try:
            if not wav_path.exists():
                rmp.convert_to_canonical_wav(id_map[opaque_id], wav_path, decoded_dir / f"{opaque_id}_ffmpeg_error.log")
            t0 = time.time()
            result = bt.analyze_file(wav_path, device="cuda")
            elapsed = time.time() - t0

            beat_bpms = bpm_series(result["beats_s"])
            bar_periods_s = [b - a for a, b in zip(result["downbeats_s"], result["downbeats_s"][1:]) if b > a]
            summary = {
                "status": "SUCCESS",
                "beat_count": len(result["beats_s"]),
                "downbeat_count": len(result["downbeats_s"]),
                "median_beat_bpm": round(statistics.median(beat_bpms), 2) if beat_bpms else None,
                "median_bar_period_s": round(statistics.median(bar_periods_s), 4) if bar_periods_s else None,
                "first_downbeat_s": round(result["downbeats_s"][0], 3) if result["downbeats_s"] else None,
                "last_downbeat_s": round(result["downbeats_s"][-1], 3) if result["downbeats_s"] else None,
                "inference_wall_time_s": round(elapsed, 2),
            }
            beat_cache_path.write_text(json.dumps({"summary": summary, "beats_s": result["beats_s"], "downbeats_s": result["downbeats_s"]}, indent=2), encoding="utf-8")
            aggregate[opaque_id] = summary
            print(f"[{i}/{len(ids)}] {opaque_id}: SUCCESS beats={summary['beat_count']} downbeats={summary['downbeat_count']} bpm~{summary['median_beat_bpm']} ({elapsed:.1f}s)")
        except Exception as e:  # noqa: BLE001
            summary = {"status": "FAILED", "error_class": type(e).__name__}
            beat_cache_path.write_text(json.dumps({"summary": summary}, indent=2), encoding="utf-8")
            aggregate[opaque_id] = summary
            print(f"[{i}/{len(ids)}] {opaque_id}: FAILED {type(e).__name__}")

    Path(args.aggregate_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.aggregate_out).write_text(json.dumps({
        "track_count": len(ids),
        "success_count": sum(1 for v in aggregate.values() if v["status"] == "SUCCESS"),
        "failure_count": sum(1 for v in aggregate.values() if v["status"] != "SUCCESS"),
        "total_wall_time_s": round(time.time() - t_start, 1),
        "tracks": aggregate,
    }, indent=2), encoding="utf-8")

    print(f"\nDone in {time.time() - t_start:.1f}s. Wrote sanitized aggregate to {args.aggregate_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
