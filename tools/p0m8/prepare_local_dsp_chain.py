"""
P0-M8-R1 -- LocalDSP consumer quality slice: chain audio preparation.

Prepares the audio assets for ONE genuine multi-hop AutoMix chain
discovered by `discover_local_dsp_graph.py` (which itself reuses
`pair_discovery.py`'s `evaluate_pair` unmodified -- no new beat model, no
new analysis pass). This script only trims already-decoded local audio
via ffmpeg (sample-accurate PCM re-encode, same tool/approach already
accepted for `apps/automix-live-lab/tools/prepare_queue_audio.py`) -- it
does not run Beat This, does not compute any new anchor/tempo value, and
does not touch the frozen P0-M5-R1 pair manifest.

Unlike the P0-M6 fixed 6-item demo queue (each item a SHORT, independent
pre/post-roll excerpt around one isolated transition), this script trims
each chain track to its full PLAYABLE SPAN -- from the anchor where it was
entered through to the anchor where IT exits into the next hop (or a
settle-in tail for the terminal track) -- so the browser engine can play
one genuinely continuous "current track" per hop (preserving almost all of
each outgoing song, not just a ~20s clip), matching the Phase C quality
contract.

Chain (near-native tempo only, tempo_correction == 0.0 for all 3 hops --
no live pitch-shift/stretch risk, `choose_window_bars` reused unmodified
from `apple_like_render.py`):

    RM062 --exit185.26/window11.52--> RM076 --exit174.02/window12.00--> RM010 --exit199.12/window11.20--> RM099 (terminal)

Usage:
    python tools/p0m8/prepare_local_dsp_chain.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
P0M5_DIR = REPO_ROOT / "tools" / "p0m5" / "apple_like_vertical_slice"
DECODED_DIR = P0M5_DIR / "work_local" / "decoded"
APP_ROOT = REPO_ROOT / "apps" / "automix-live-lab"
OUT_DIR = APP_ROOT / "work_local" / "local_dsp_chain"

sys.path.insert(0, str(P0M5_DIR))
from apple_like_render import choose_window_bars  # noqa: E402 (reused, not reimplemented)

BASS_CUTOFF_HZ = 150.0  # reused verbatim, same as prepare_queue_audio.py
BASS_HANDOFF_SPEED = 2.2  # reused verbatim, same as prepare_queue_audio.py
TERMINAL_TAIL_S = 60.0  # settle-in listen time after the last real transition


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
    graph = json.loads((HERE / "local_dsp_graph.json").read_text(encoding="utf-8"))
    adjacency = graph["adjacency"]

    def edge(out_id: str, in_id: str) -> dict:
        for e in adjacency[out_id]:
            if e["in_id"] == in_id:
                return e
        raise KeyError(f"{out_id}->{in_id} not found in adjacency")

    hops = [("RM062", "RM076"), ("RM076", "RM010"), ("RM010", "RM099")]
    edges = [edge(o, i) for o, i in hops]
    for (o, i), e in zip(hops, edges):
        assert e["tempo_correction"] == 0.0, f"{o}->{i} is not near-native (correction={e['tempo_correction']}); this script only handles the zero-correction chain"

    # windows, keyed by the OUTGOING track of each hop
    windows = {}
    for (out_id, in_id), e in zip(hops, edges):
        bars, window_s = choose_window_bars(e["outgoing_bar_period_s"])
        windows[out_id] = {"in_id": in_id, "exit_anchor_s": e["exit_anchor_s"], "entry_anchor_s": e["entry_anchor_s"], "window_bars": bars, "window_s": round(window_s, 3), "evidence": e}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tracks_out = []

    # --- RM062 (seed): [0, exit+window] ---
    w = windows["RM062"]
    trim_start = 0.0
    trim_end = w["exit_anchor_s"] + w["window_s"]
    dst = OUT_DIR / "RM062_seed.wav"
    ffmpeg_trim(DECODED_DIR / "RM062.wav", dst, trim_start, trim_end - trim_start)
    dur = probe_duration_s(dst)
    tracks_out.append({
        "tag": "RM062", "role": "seed", "file": dst.name, "duration_s": round(dur, 3),
        "trim_start_s": trim_start, "exit_offset_s": round(w["exit_anchor_s"] - trim_start, 3),
        "window_s": w["window_s"], "next_tag": "RM076",
        "bass_cutoff_hz": BASS_CUTOFF_HZ, "bass_handoff_speed": BASS_HANDOFF_SPEED,
        "tempo_ratio": w["evidence"]["tempo_ratio"], "tempo_correction_pct": round(w["evidence"]["tempo_correction"] * 100.0, 2),
        "exit_structure_confidence": w["evidence"]["exit_structure_confidence"], "harmonic_relationship": w["evidence"]["harmonic_relationship"],
    })
    print(f"RM062 (seed): [{trim_start:.2f},{trim_end:.2f}] -> {dst.name} ({dur:.2f}s), exit_offset={w['exit_anchor_s']-trim_start:.2f}s window={w['window_s']}s")

    # --- RM076 (middle): [entry_from_RM062, exit+window_into_RM010] ---
    entry_r76 = windows["RM062"]["entry_anchor_s"]
    w = windows["RM076"]
    trim_start = entry_r76
    trim_end = w["exit_anchor_s"] + w["window_s"]
    dst = OUT_DIR / "RM076_mid.wav"
    ffmpeg_trim(DECODED_DIR / "RM076.wav", dst, trim_start, trim_end - trim_start)
    dur = probe_duration_s(dst)
    tracks_out.append({
        "tag": "RM076", "role": "middle", "file": dst.name, "duration_s": round(dur, 3),
        "trim_start_s": trim_start, "exit_offset_s": round(w["exit_anchor_s"] - trim_start, 3),
        "window_s": w["window_s"], "next_tag": "RM010",
        "bass_cutoff_hz": BASS_CUTOFF_HZ, "bass_handoff_speed": BASS_HANDOFF_SPEED,
        "tempo_ratio": w["evidence"]["tempo_ratio"], "tempo_correction_pct": round(w["evidence"]["tempo_correction"] * 100.0, 2),
        "exit_structure_confidence": w["evidence"]["exit_structure_confidence"], "harmonic_relationship": w["evidence"]["harmonic_relationship"],
    })
    print(f"RM076 (mid): [{trim_start:.2f},{trim_end:.2f}] -> {dst.name} ({dur:.2f}s), exit_offset={w['exit_anchor_s']-trim_start:.2f}s window={w['window_s']}s")

    # --- RM010 (middle): [entry_from_RM076, exit+window_into_RM099] ---
    entry_r10 = windows["RM076"]["entry_anchor_s"]
    w = windows["RM010"]
    trim_start = entry_r10
    trim_end = w["exit_anchor_s"] + w["window_s"]
    dst = OUT_DIR / "RM010_mid.wav"
    ffmpeg_trim(DECODED_DIR / "RM010.wav", dst, trim_start, trim_end - trim_start)
    dur = probe_duration_s(dst)
    tracks_out.append({
        "tag": "RM010", "role": "middle", "file": dst.name, "duration_s": round(dur, 3),
        "trim_start_s": trim_start, "exit_offset_s": round(w["exit_anchor_s"] - trim_start, 3),
        "window_s": w["window_s"], "next_tag": "RM099",
        "bass_cutoff_hz": BASS_CUTOFF_HZ, "bass_handoff_speed": BASS_HANDOFF_SPEED,
        "tempo_ratio": w["evidence"]["tempo_ratio"], "tempo_correction_pct": round(w["evidence"]["tempo_correction"] * 100.0, 2),
        "exit_structure_confidence": w["evidence"]["exit_structure_confidence"], "harmonic_relationship": w["evidence"]["harmonic_relationship"],
    })
    print(f"RM010 (mid): [{trim_start:.2f},{trim_end:.2f}] -> {dst.name} ({dur:.2f}s), exit_offset={w['exit_anchor_s']-trim_start:.2f}s window={w['window_s']}s")

    # --- RM099 (terminal): [entry_from_RM010, entry + window + tail], no further hop ---
    entry_r99 = windows["RM010"]["entry_anchor_s"]
    last_window_s = windows["RM010"]["window_s"]
    trim_start = entry_r99
    trim_end = entry_r99 + last_window_s + TERMINAL_TAIL_S
    dst = OUT_DIR / "RM099_terminal.wav"
    ffmpeg_trim(DECODED_DIR / "RM099.wav", dst, trim_start, trim_end - trim_start)
    dur = probe_duration_s(dst)
    tracks_out.append({
        "tag": "RM099", "role": "terminal", "file": dst.name, "duration_s": round(dur, 3),
        "trim_start_s": trim_start, "exit_offset_s": None, "window_s": None, "next_tag": None,
        "bass_cutoff_hz": BASS_CUTOFF_HZ, "bass_handoff_speed": BASS_HANDOFF_SPEED,
        "tempo_ratio": None, "tempo_correction_pct": None,
        "exit_structure_confidence": None, "harmonic_relationship": None,
    })
    print(f"RM099 (terminal): [{trim_start:.2f},{trim_end:.2f}] -> {dst.name} ({dur:.2f}s)")

    manifest = {
        "schema": "p0m8_local_dsp_chain_v1",
        "seed_tag": "RM062",
        "track_count": len(tracks_out),
        "transition_count": sum(1 for t in tracks_out if t["next_tag"]),
        "tracks": tracks_out,
    }
    out_path = APP_ROOT / "src" / "data" / "local_dsp_chain.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nRESULT: {manifest['track_count']} tracks / {manifest['transition_count']} transitions prepared, wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
