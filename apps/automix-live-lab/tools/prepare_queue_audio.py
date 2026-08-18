"""
Local DSP Live queue preparation for the AutoMix Live Lab prototype
(Issue #11, PM comments 5323227813 / 5323231023, Lane S3).

Builds a runnable live-queue manifest from the ALREADY FROZEN and
ALREADY ACCEPTED P0-M5-R1 8-pair manifest
(tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json) --
this script does not re-run Beat This, does not re-discover pairs, and
does not recompute any anchor/tempo value. It only trims raw decoded
excerpts (via ffmpeg, sample-accurate PCM re-encode, no re-analysis) so
a browser Web Audio engine can load a live 6-item queue without
fetching full 3-4 minute tracks, and reuses `choose_window_bars` from
the accepted `apple_like_render.py` unmodified (imported, not copied).

Queue design (6 dev-split pairs = 6 transitions, "at least 5 consecutive
transitions" per the task instruction):

  - 5 of 6 dev pairs have tempo_ratio == 1.0 (no stretch needed, per the
    accepted BLOCKER-3 bypass rule already in apple_like_render.py) --
    these are prepared as RAW trimmed excerpts (outgoing pre-roll +
    window, incoming window + tail) and the live engine
    (LocalDSPPlaybackAdapter + deck-engine.js) performs the actual
    equal-power crossfade + bass/EQ handoff LIVE at runtime via Web
    Audio gain/biquad automation -- this is the genuine "live two-deck"
    path.
  - The 1 remaining dev pair (S01, RM055->RM052, tempo_ratio=0.9688, a
    genuine <=6% Signalsmith stretch-cover pair) reuses the EXACT
    already-rendered, already safety-checked accepted M1 clip
    (work_local/renders/S01_M1.wav, unmodified bytes) as ONE queue item
    played as a single continuous scheduled unit. This is an honest,
    disclosed reuse of the existing accepted offline Signalsmith
    pipeline, not a live re-implementation of Signalsmith stretch in
    the browser (out of scope for this pass -- see report). The live
    engine still schedules it gaplessly against its live-two-deck
    neighbors in the queue, so the OVERALL session is still one
    continuous live playback with zero silence between any two of the
    6 transitions.

Usage:
    python apps/automix-live-lab/tools/prepare_queue_audio.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
REPO_ROOT = APP_ROOT.parents[1]
P0M5_DIR = REPO_ROOT / "tools" / "p0m5" / "apple_like_vertical_slice"
DECODED_DIR = P0M5_DIR / "work_local" / "decoded"
RENDERS_DIR = P0M5_DIR / "work_local" / "renders"
MANIFEST_PATH = P0M5_DIR / "pair_manifest_sanitized.json"

OUT_DIR = APP_ROOT / "work_local" / "queue_audio"

sys.path.insert(0, str(P0M5_DIR))
from apple_like_render import choose_window_bars, PRE_ROLL_S  # noqa: E402  (reused, not reimplemented)

INCOMING_TAIL_S = 10.0  # seconds of "incoming continues at native tempo" heard before the next queue item cuts in
BASS_CUTOFF_HZ = 150.0  # reused verbatim from tools/p0m3/audio_render_shootout/dsp/mixing.py
BASS_HANDOFF_SPEED = 2.2  # reused verbatim from the same module

# Manifest order tags for the 6 dev-split pairs (indices 1,4,5,6,7,8 -> S01,S04,S05,S06,S07,S08).
DEV_TAGS_IN_ORDER = ["S01", "S04", "S05", "S06", "S07", "S08"]


def ffmpeg_trim(src: Path, dst: Path, start_s: float, dur_s: float) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{max(0.0, start_s):.6f}",
        "-i", str(src),
        "-t", f"{dur_s:.6f}",
        "-c:a", "pcm_f32le",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def probe_duration_s(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("status") != "FROZEN":
        print(f"RESULT: BLOCKED -- pair manifest status {manifest.get('status')!r}, not FROZEN")
        return 1

    pairs_by_index = {f"S{idx:02d}": p for idx, p in enumerate(manifest["pairs"], start=1)}
    dev_tags = [t for t in DEV_TAGS_IN_ORDER if pairs_by_index[t]["split"] == "dev"]
    if dev_tags != DEV_TAGS_IN_ORDER:
        print(f"RESULT: BLOCKED -- expected dev tags {DEV_TAGS_IN_ORDER}, manifest split assignment changed: {dev_tags}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    queue_items = []

    for tag in DEV_TAGS_IN_ORDER:
        pair = pairs_by_index[tag]
        out_id, in_id = pair["out_id"], pair["in_id"]
        tempo_ratio = pair["tempo_ratio"]
        is_stretch = pair.get("is_stretch_cover_candidate", False)

        if is_stretch:
            # Reuse the exact accepted M1 render for this one stretch-cover pair.
            src = RENDERS_DIR / f"{tag}_M1.wav"
            dst = OUT_DIR / f"{tag}_baked.wav"
            shutil.copyfile(src, dst)
            dur_s = probe_duration_s(dst)
            queue_items.append({
                "tag": tag,
                "mode": "baked_transition",
                "out_id": out_id,
                "in_id": in_id,
                "tempo_ratio": tempo_ratio,
                "tempo_correction_pct": round(pair["tempo_correction"] * 100.0, 2),
                "beat_downbeat_sync": True,
                "bass_eq_handoff": True,
                "stretch_engine": "signalsmith_offline_accepted_m1_render",
                "file": f"{tag}_baked.wav",
                "duration_s": round(dur_s, 3),
                "source_note": "Reuses tools/p0m5/apple_like_vertical_slice/work_local/renders/S01_M1.wav verbatim (accepted P0-M5-R1 pipeline, <=6% Signalsmith outgoing-tail stretch), not re-stretched by this app.",
            })
            print(f"{tag}: BAKED (stretch-cover, rate={tempo_ratio}) -> {dst.name} ({dur_s:.2f}s)")
            continue

        bar_period_s = pair["outgoing_bar_period_s"] or 2.0
        bars, window_s = choose_window_bars(bar_period_s)
        exit_anchor_s = pair["exit_anchor_s"]
        entry_anchor_s = pair["entry_anchor_s"]

        out_trim_start = max(0.0, exit_anchor_s - PRE_ROLL_S)
        out_trim_dur = (exit_anchor_s - out_trim_start) + window_s
        exit_offset_in_file_s = exit_anchor_s - out_trim_start

        in_trim_start = entry_anchor_s
        in_trim_dur = window_s + INCOMING_TAIL_S

        out_file = OUT_DIR / f"{tag}_out.wav"
        in_file = OUT_DIR / f"{tag}_in.wav"
        ffmpeg_trim(DECODED_DIR / f"{out_id}.wav", out_file, out_trim_start, out_trim_dur)
        ffmpeg_trim(DECODED_DIR / f"{in_id}.wav", in_file, in_trim_start, in_trim_dur)

        queue_items.append({
            "tag": tag,
            "mode": "live_two_deck",
            "out_id": out_id,
            "in_id": in_id,
            "tempo_ratio": tempo_ratio,
            "tempo_correction_pct": round(pair["tempo_correction"] * 100.0, 2),
            "beat_downbeat_sync": True,
            "bass_eq_handoff": True,
            "bass_cutoff_hz": BASS_CUTOFF_HZ,
            "bass_handoff_speed": BASS_HANDOFF_SPEED,
            "window_bars": bars,
            "window_s": round(window_s, 3),
            "out_file": out_file.name,
            "in_file": in_file.name,
            "exit_offset_s": round(exit_offset_in_file_s, 3),
            "entry_offset_s": 0.0,
            "out_duration_s": round(probe_duration_s(out_file), 3),
            "in_duration_s": round(probe_duration_s(in_file), 3),
        })
        print(f"{tag}: LIVE_TWO_DECK (rate=1.0, {bars} bars/{window_s:.2f}s) -> {out_file.name} + {in_file.name}")

    manifest_out = {
        "schema": "automix_live_queue_v1",
        "source_manifest": "tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json",
        "item_count": len(queue_items),
        "transition_count": len(queue_items),
        "items": queue_items,
    }
    out_path = APP_ROOT / "src" / "data" / "queue_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest_out, indent=2), encoding="utf-8")
    print(f"\nRESULT: {len(queue_items)} queue items prepared, wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
