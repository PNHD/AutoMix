"""
Deterministic, seeded, music-like synthetic audio generator for P0-M3-R3.

Not a click track: each track has drums (kick/snare/hat), a moving bass
line, a chord pad, and a melodic/vocal-like sustained lead, arranged into
authored sections (intro/verse/chorus/outro) with controlled energy
variation, over a known, exact beat/downbeat/bar grid derived directly from
the fixture's own bpm (Issue #7 "AUDIO FIXTURES").

A short, distinctive diagnostic "alignment marker" is embedded at each
requested `marker_ms` position (exact sample-accurate ground truth, since
this project authors the waveform numerically) so post-render beat/
downbeat alignment error can be measured against synthetic ground truth by
matched-filter peak detection, not merely asserted. Outgoing and incoming
tracks use INDEPENDENTLY IDENTIFIABLE marker signatures (`dsp/markers.py`)
-- never the same template on both sides (PM STAGE A REVIEW R3 repair) --
so a matched-filter search can never mechanically "detect the same peak
twice" and report a false relative alignment error of `0.0`.

Diagnostic markers are audible-ish, high-frequency ticks and MUST NOT
appear in owner-listening audio (PM STAGE A REVIEW R4 repair). Pass
`embed_markers=False` to synthesize CLEAN audio with no diagnostic content
at all -- used only for the owner listening pack. Diagnostic (marker-
embedded) audio is used only for the full DSP pipeline / machine alignment
metrics / PM forensic review, never for owner listening.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dsp.markers import marker_spec_for_role, build_marker_waveform, marker_duration_samples  # noqa: E402

SR = 44100

# Deterministic, small, minor-leaning chord-root movement (semitone offsets
# from the track's root_hz), cycled one degree per bar -- i, bVII, bVI, IV-ish.
CHORD_PROGRESSION_SEMITONES = [0, -2, -4, 5]
MELODY_SCALE_SEMITONES = [0, 3, 5, 7, 10, 12]  # minor pentatonic + octave


def _semitone_ratio(n: float) -> float:
    return 2.0 ** (n / 12.0)


def _kick(n: int, sr: int) -> np.ndarray:
    if n <= 0:
        return np.zeros(0)
    t = np.arange(n) / sr
    freq = 150.0 * np.exp(-t * 18.0) + 45.0
    phase = 2 * np.pi * np.cumsum(freq) / sr
    env = np.exp(-t * 14.0)
    return np.sin(phase) * env


def _snare(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    if n <= 0:
        return np.zeros(0)
    t = np.arange(n) / sr
    noise = rng.standard_normal(n)
    env = np.exp(-t * 30.0)
    tone = np.sin(2 * np.pi * 190.0 * t) * np.exp(-t * 40.0) * 0.5
    return noise * env * 0.6 + tone


def _hat(n: int, sr: int, rng: np.random.Generator) -> np.ndarray:
    if n <= 0:
        return np.zeros(0)
    t = np.arange(n) / sr
    noise = rng.standard_normal(n)
    env = np.exp(-t * 70.0)
    hp = np.diff(noise, prepend=0.0)
    return hp * env


def _osc(freq_hz: np.ndarray | float, n: int, sr: int, shape: str = "sine") -> np.ndarray:
    if n <= 0:
        return np.zeros(0)
    t = np.arange(n) / sr
    if shape == "saw":
        ph = (freq_hz * t) % 1.0
        return 2.0 * ph - 1.0
    return np.sin(2 * np.pi * freq_hz * t)


def _active_section(sections: list[dict], t_s: float) -> dict:
    for sec in sections:
        if sec["start_s"] <= t_s < sec["end_s"]:
            return sec
    return sections[-1]


def make_track(spec: dict, sr: int = SR, marker_role: str | None = None, embed_markers: bool = True) -> tuple[np.ndarray, dict]:
    """
    spec: {bpm, duration_s, seed, root_hz, sections:[{start_s,end_s,label,energy,layers}], marker_ms:[...]}
    marker_role: "outgoing" | "incoming" -- selects which distinct marker
        signature (dsp/markers.py) to embed; REQUIRED when embed_markers=True.
    embed_markers: False produces CLEAN audio (no diagnostic marker content
        at all) -- used only for owner-listening renders (R4 repair).
    Returns (stereo_float32[n, 2], ground_truth_dict).
    """
    bpm = float(spec["bpm"])
    duration_s = float(spec["duration_s"])
    seed = int(spec["seed"])
    root_hz = float(spec["root_hz"])
    sections = spec["sections"]
    marker_ms = spec.get("marker_ms", []) if embed_markers else []
    if embed_markers and marker_ms and marker_role is None:
        raise ValueError("marker_role is required when embed_markers=True and marker_ms is non-empty")

    rng = np.random.default_rng(seed)
    n_total = int(round(duration_s * sr))
    buf = np.zeros(n_total, dtype=np.float64)

    beat_dur_s = 60.0 / bpm
    ground_truth = {
        "sr": sr,
        "bpm": bpm,
        "duration_s": duration_s,
        "beat_dur_s": beat_dur_s,
        "sections": sections,
        "beats_ms": [],
        "downbeats_ms": [],
        "marker_ms": list(marker_ms),
        "markers_embedded": bool(embed_markers and marker_ms),
        "marker_role": marker_role if (embed_markers and marker_ms) else None,
    }

    t = 0.0
    beat_idx = 0
    while t < duration_s:
        sec = _active_section(sections, t)
        layers = set(sec["layers"])
        energy = float(sec["energy"])
        beat_in_bar = beat_idx % 4
        bar_idx = beat_idx // 4

        start_smp = int(round(t * sr))
        beat_len_smp = int(round(beat_dur_s * sr))
        end_smp = min(n_total, start_smp + beat_len_smp)
        n = end_smp - start_smp
        if n <= 0:
            break

        ground_truth["beats_ms"].append(round(t * 1000.0, 3))
        if beat_in_bar == 0:
            ground_truth["downbeats_ms"].append(round(t * 1000.0, 3))

        chord_root_semi = CHORD_PROGRESSION_SEMITONES[bar_idx % len(CHORD_PROGRESSION_SEMITONES)]
        chord_freq = root_hz * _semitone_ratio(chord_root_semi)

        if "kick" in layers and beat_in_bar in (0, 2):
            k = _kick(min(n, int(0.25 * sr)), sr) * (0.9 * energy)
            buf[start_smp:start_smp + len(k)] += k

        if "snare" in layers and beat_in_bar in (1, 3):
            s = _snare(min(n, int(0.20 * sr)), sr, rng) * (0.55 * energy)
            buf[start_smp:start_smp + len(s)] += s

        if "hat" in layers:
            for sub in range(2):
                sub_start = start_smp + sub * (beat_len_smp // 2)
                sub_n = min(n_total - sub_start, int(0.06 * sr))
                if sub_n > 0:
                    h = _hat(sub_n, sr, rng) * (0.16 * energy)
                    buf[sub_start:sub_start + sub_n] += h

        if "bass" in layers:
            bass_freq = chord_freq / 2.0
            tone = _osc(bass_freq, n, sr, "saw") * (0.28 * energy)
            ramp = np.arange(n) / max(1, int(0.01 * sr))
            attack = np.minimum(1.0, ramp)
            decay = np.exp(-np.arange(n) / (sr * 0.35))
            buf[start_smp:end_smp] += tone * attack * decay

        if "pad" in layers:
            triad_semitones = (0, 3, 7)
            pad = np.zeros(n)
            for iv in triad_semitones:
                pad += _osc(chord_freq * _semitone_ratio(iv), n, sr, "sine")
            pad *= (0.09 * energy / len(triad_semitones)) * 3.0
            buf[start_smp:end_smp] += pad

        if "melody" in layers and beat_in_bar in (0, 2):
            note_semi = MELODY_SCALE_SEMITONES[(bar_idx + beat_idx) % len(MELODY_SCALE_SEMITONES)]
            mel_freq = chord_freq * 2.0 * _semitone_ratio(note_semi)
            vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * np.arange(n) / sr)
            tone = _osc(mel_freq * vib, n, sr, "sine")
            env = np.sin(np.pi * np.clip(np.arange(n) / max(1, n), 0, 1))
            buf[start_smp:end_smp] += tone * env * (0.22 * energy)

        beat_idx += 1
        t += beat_dur_s

    marker_sample_positions = []
    marker_spec = None
    if embed_markers and marker_ms:
        marker_spec = marker_spec_for_role(marker_role)
        marker_len = marker_duration_samples(marker_spec, sr)
        for ms in marker_ms:
            smp = int(round(ms / 1000.0 * sr))
            mn = min(max(0, n_total - smp), marker_len)
            if mn > 0:
                blip = build_marker_waveform(marker_spec, mn, sr)
                buf[smp:smp + mn] += blip
            marker_sample_positions.append(smp)
    ground_truth["marker_sample_positions"] = marker_sample_positions
    ground_truth["marker_spec"] = marker_spec

    peak = float(np.max(np.abs(buf))) if buf.size else 1.0
    if peak > 0:
        buf = buf / peak * 0.85

    stereo = np.stack([buf, buf], axis=1).astype(np.float32)
    return stereo, ground_truth
