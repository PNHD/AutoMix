"""
P0-M3-R1 disposable benchmark harness — synthetic fixture generator.

Generates deterministic, fully synthetic PCM16 WAV fixtures with EXACT
timing ground truth (beat/downbeat/meter/section/phrase), so the analyzer
shootout can measure beat/downbeat/cue/structure error against a ground
truth that has zero measurement uncertainty (SYNTHETIC_EXACT, per
docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md's annotation_sources enum).

Scope discipline (per Issue #5 / .agents/skills/automix-forensic-research):
  - 100% synthetically synthesized (sine/click/noise-burst DSP). No sampled
    or copyrighted material of any kind is read or embedded.
  - provenance = SYNTHETIC, license = "N/A (generated, owner-created)" for
    every fixture, consistent with the corpus manifest schema's provenance
    enum (SYNTHETIC | OWNER_CREATED | PUBLIC_DOMAIN | CC0 | PERMISSIVE_OTHER).
  - Musical content is deliberately simple (clicks/tones/noise bursts), not
    representative pop/EDM/rock material. Per Issue #5 Task C, cue/structure
    results on these fixtures are smoke/regression evidence only, not a
    proxy for real-world musical quality.
  - Generated .wav audio bytes are intentionally NOT committed to git (see
    ../.gitignore) even though they are owner-generated with no third-party
    rights question, per Issue #5 Task C's default-to-ignored instruction.
    Only this generator script (deterministic, reproduces byte-identical
    output) and the resulting ground-truth JSON manifest are committed.

Run:
    python generate_fixtures.py --out-dir ../local_audio --manifest-out ../fixtures/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import wave
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

SR = 44100  # sample rate, Hz


# ---------------------------------------------------------------------------
# Low-level synth primitives
# ---------------------------------------------------------------------------

def click(t_sec: float, dur_sec: float, freq_hz: float, amp: float, n_samples: int, sr: int = SR) -> np.ndarray:
    """A short exponentially-decaying sine burst ('click') placed at t_sec."""
    out = np.zeros(n_samples, dtype=np.float64)
    start = int(round(t_sec * sr))
    length = int(round(dur_sec * sr))
    if start >= n_samples:
        return out
    length = min(length, n_samples - start)
    if length <= 0:
        return out
    tt = np.arange(length) / sr
    envelope = np.exp(-tt / (dur_sec / 5.0))
    tone = np.sin(2 * math.pi * freq_hz * tt)
    out[start:start + length] += amp * envelope * tone
    return out


def noise_burst(t_sec: float, dur_sec: float, amp: float, n_samples: int, sr: int = SR, seed: int = 0) -> np.ndarray:
    """A short noise burst (percussive 'hat'-like transient), deterministic via seed."""
    out = np.zeros(n_samples, dtype=np.float64)
    start = int(round(t_sec * sr))
    length = int(round(dur_sec * sr))
    if start >= n_samples:
        return out
    length = min(length, n_samples - start)
    if length <= 0:
        return out
    rng = np.random.RandomState(seed + start)
    tt = np.arange(length) / sr
    envelope = np.exp(-tt / (dur_sec / 4.0))
    out[start:start + length] += amp * envelope * rng.uniform(-1, 1, size=length)
    return out


def sustained_tone(t0_sec: float, t1_sec: float, freq_hz: float, amp: float, n_samples: int, sr: int = SR) -> np.ndarray:
    out = np.zeros(n_samples, dtype=np.float64)
    start = max(0, int(round(t0_sec * sr)))
    end = min(n_samples, int(round(t1_sec * sr)))
    if end <= start:
        return out
    tt = np.arange(end - start) / sr
    # short attack/release to avoid clicks at boundaries
    ramp = min(0.01 * sr, (end - start) / 2)
    env = np.ones(end - start)
    if ramp > 0:
        r = int(ramp)
        env[:r] *= np.linspace(0, 1, r)
        env[-r:] *= np.linspace(1, 0, r)
    out[start:end] += amp * env * np.sin(2 * math.pi * freq_hz * tt)
    return out


def write_wav(path: str, samples: np.ndarray, sr: int = SR) -> str:
    samples = np.clip(samples, -1.0, 1.0)
    pcm16 = (samples * 32767.0).astype(np.int16)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return digest


# ---------------------------------------------------------------------------
# Fixture builders — each returns (samples, ground_truth_dict)
# ---------------------------------------------------------------------------

def build_constant_grid(bpm: float, n_bars: int, beats_per_bar: int = 4, accent_beat: int = 0,
                         tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    beat_period = 60.0 / bpm
    n_beats = n_bars * beats_per_bar
    total_sec = n_beats * beat_period + tail_sec
    n_samples = int(math.ceil(total_sec * SR))
    out = np.zeros(n_samples, dtype=np.float64)
    beat_ts = []
    downbeat_idx = []
    for i in range(n_beats):
        t = i * beat_period
        beat_ts.append(round(t * 1000))
        is_downbeat = (i % beats_per_bar) == accent_beat
        if is_downbeat:
            downbeat_idx.append(i)
            out += click(t, 0.08, 220.0, 0.9, n_samples)
        else:
            out += click(t, 0.05, 880.0, 0.5, n_samples)
    gt = {
        "bpm": bpm,
        "meter": {"numerator": beats_per_bar, "denominator": 4, "confidence": 1.0},
        "beat_timestamps_ms": beat_ts,
        "downbeat_indices": downbeat_idx,
        "duration_sec": round(total_sec, 3),
    }
    return out, gt


def build_phase_offset(bpm: float, n_bars: int, offset_beats: float, beats_per_bar: int = 4,
                        tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    """Same as constant grid but the whole click grid is shifted by offset_beats
    (e.g. 0.5 = deliberate half-beat phase offset from t=0)."""
    beat_period = 60.0 / bpm
    n_beats = n_bars * beats_per_bar
    lead_in = offset_beats * beat_period
    total_sec = lead_in + n_beats * beat_period + tail_sec
    n_samples = int(math.ceil(total_sec * SR))
    out = np.zeros(n_samples, dtype=np.float64)
    beat_ts = []
    downbeat_idx = []
    for i in range(n_beats):
        t = lead_in + i * beat_period
        beat_ts.append(round(t * 1000))
        is_downbeat = (i % beats_per_bar) == 0
        if is_downbeat:
            downbeat_idx.append(i)
            out += click(t, 0.08, 220.0, 0.9, n_samples)
        else:
            out += click(t, 0.05, 880.0, 0.5, n_samples)
    gt = {
        "bpm": bpm,
        "meter": {"numerator": beats_per_bar, "denominator": 4, "confidence": 1.0},
        "beat_timestamps_ms": beat_ts,
        "downbeat_indices": downbeat_idx,
        "duration_sec": round(total_sec, 3),
        "phase_offset_beats_from_zero": offset_beats,
    }
    return out, gt


def build_wrong_downbeat_phase(bpm: float, n_bars: int, true_accent_beat: int, beats_per_bar: int = 4,
                                tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    """A grid with a regular, evenly-spaced beat click train (all beats identical
    amplitude/timbre EXCEPT one beat position per bar carries the low-pitched
    'downbeat' accent at a position other than beat 0) -- tests whether a
    tracker's bar-phase/downbeat assignment is independently correct from
    beat detection, not merely BPM-consistent."""
    return build_constant_grid(bpm, n_bars, beats_per_bar=beats_per_bar, accent_beat=true_accent_beat,
                                tail_sec=tail_sec)


def build_non_4_4(bpm: float, n_bars: int, beats_per_bar: int, tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    out, gt = build_constant_grid(bpm, n_bars, beats_per_bar=beats_per_bar, accent_beat=0, tail_sec=tail_sec)
    gt["meter"] = {"numerator": beats_per_bar, "denominator": 4, "confidence": 1.0}
    return out, gt


def build_sections(bpm: float, bars_per_section: list[tuple[str, int]], beats_per_bar: int = 4,
                    tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    """Labeled section changes via distinct layering per section:
    silence(intro) -> kick+hat(verse) -> +bass tone(chorus) -> +melody(chorus2) -> kick-only(outro)."""
    beat_period = 60.0 / bpm
    total_bars = sum(n for _, n in bars_per_section)
    n_beats = total_bars * beats_per_bar
    total_sec = n_beats * beat_period + tail_sec
    n_samples = int(math.ceil(total_sec * SR))
    out = np.zeros(n_samples, dtype=np.float64)

    beat_ts = []
    downbeat_idx = []
    section_boundaries = []
    t_cursor = 0.0
    beat_i = 0
    layer_by_label = {
        "intro": ("kick",),
        "verse": ("kick", "hat"),
        "chorus": ("kick", "hat", "bass"),
        "bridge": ("kick", "bass"),
        "outro": ("kick",),
    }
    for label, n_bars_here in bars_per_section:
        sec_start = t_cursor
        layers = layer_by_label.get(label, ("kick",))
        for b in range(n_bars_here):
            for beat_in_bar in range(beats_per_bar):
                t = t_cursor
                beat_ts.append(round(t * 1000))
                is_downbeat = beat_in_bar == 0
                if is_downbeat:
                    downbeat_idx.append(beat_i)
                if "kick" in layers:
                    out += click(t, 0.09, 110.0, 0.85, n_samples)
                if "hat" in layers and beat_in_bar % 1 == 0:
                    out += noise_burst(t + beat_period / 2, 0.03, 0.25, n_samples, seed=beat_i)
                if "bass" in layers and is_downbeat:
                    out += sustained_tone(t, t + beat_period * beats_per_bar * 0.9, 55.0, 0.2, n_samples)
                t_cursor += beat_period
                beat_i += 1
        section_boundaries.append({
            "t_start_ms": round(sec_start * 1000),
            "t_end_ms": round(t_cursor * 1000),
            "label": label,
        })

    gt = {
        "bpm": bpm,
        "meter": {"numerator": beats_per_bar, "denominator": 4, "confidence": 1.0},
        "beat_timestamps_ms": beat_ts,
        "downbeat_indices": downbeat_idx,
        "section_boundaries": section_boundaries,
        "phrase_boundaries_ms": [s["t_start_ms"] for s in section_boundaries],
        "duration_sec": round(total_sec, 3),
    }
    return out, gt


def build_intro_body_outro_energy(bpm: float, n_bars: int, beats_per_bar: int = 4,
                                   tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    """Known, monotonic energy envelope: quiet intro (25%) -> full body (50%) -> fading outro (25%),
    with an explicit RMS-envelope ground truth so an energy/onset heuristic can be graded."""
    beat_period = 60.0 / bpm
    n_beats = n_bars * beats_per_bar
    total_sec = n_beats * beat_period + tail_sec
    n_samples = int(math.ceil(total_sec * SR))
    out = np.zeros(n_samples, dtype=np.float64)

    intro_end_bar = int(n_bars * 0.25)
    outro_start_bar = int(n_bars * 0.75)

    beat_ts = []
    downbeat_idx = []
    energy_envelope_points = []  # (t_ms, target_rms_0_1)
    for i in range(n_beats):
        t = i * beat_period
        bar_idx = i // beats_per_bar
        beat_ts.append(round(t * 1000))
        is_downbeat = (i % beats_per_bar) == 0
        if is_downbeat:
            downbeat_idx.append(i)
        if bar_idx < intro_end_bar:
            amp = 0.25
        elif bar_idx >= outro_start_bar:
            frac = (bar_idx - outro_start_bar) / max(1, (n_bars - outro_start_bar))
            amp = 0.9 * (1.0 - frac) + 0.1
        else:
            amp = 0.9
        out += click(t, 0.08, 130.0, amp, n_samples)
        if bar_idx >= intro_end_bar:
            out += noise_burst(t + beat_period / 2, 0.03, amp * 0.3, n_samples, seed=i)
        energy_envelope_points.append((round(t * 1000), round(amp, 3)))

    gt = {
        "bpm": bpm,
        "meter": {"numerator": beats_per_bar, "denominator": 4, "confidence": 1.0},
        "beat_timestamps_ms": beat_ts,
        "downbeat_indices": downbeat_idx,
        "duration_sec": round(total_sec, 3),
        "section_boundaries": [
            {"t_start_ms": 0, "t_end_ms": round(intro_end_bar * beats_per_bar * beat_period * 1000), "label": "intro"},
            {"t_start_ms": round(intro_end_bar * beats_per_bar * beat_period * 1000),
             "t_end_ms": round(outro_start_bar * beats_per_bar * beat_period * 1000), "label": "verse"},
            {"t_start_ms": round(outro_start_bar * beats_per_bar * beat_period * 1000),
             "t_end_ms": round(n_beats * beat_period * 1000), "label": "outro"},
        ],
        "energy_envelope_ms_amp": energy_envelope_points,
    }
    return out, gt


def build_variable_tempo(bpm_start: float, bpm_end: float, total_beats: int, beats_per_bar: int = 4,
                          tail_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    """Linear tempo ramp: instantaneous BPM(beat_index) = lerp(bpm_start, bpm_end).
    Beat timestamps computed by integrating instantaneous beat period exactly
    (closed-form for a linear BPM ramp), giving exact ground truth despite
    non-constant tempo."""
    beat_ts_sec = [0.0]
    for i in range(1, total_beats):
        frac = (i - 0.5) / total_beats
        bpm_i = bpm_start + (bpm_end - bpm_start) * frac
        beat_ts_sec.append(beat_ts_sec[-1] + 60.0 / bpm_i)
    total_sec = beat_ts_sec[-1] + tail_sec
    n_samples = int(math.ceil(total_sec * SR))
    out = np.zeros(n_samples, dtype=np.float64)
    beat_ts = []
    downbeat_idx = []
    instantaneous_bpm = []
    for i, t in enumerate(beat_ts_sec):
        beat_ts.append(round(t * 1000))
        is_downbeat = (i % beats_per_bar) == 0
        if is_downbeat:
            downbeat_idx.append(i)
            out += click(t, 0.08, 220.0, 0.9, n_samples)
        else:
            out += click(t, 0.05, 880.0, 0.5, n_samples)
        frac = i / max(1, total_beats - 1)
        instantaneous_bpm.append(round(bpm_start + (bpm_end - bpm_start) * frac, 2))

    gt = {
        "bpm_start": bpm_start,
        "bpm_end": bpm_end,
        "bpm": round((bpm_start + bpm_end) / 2, 2),  # nominal/mean, for scalar-BPM baseline comparison
        "meter": {"numerator": beats_per_bar, "denominator": 4, "confidence": 1.0},
        "beat_timestamps_ms": beat_ts,
        "downbeat_indices": downbeat_idx,
        "instantaneous_bpm_per_beat": instantaneous_bpm,
        "duration_sec": round(total_sec, 3),
        "tempo_curve": "linear",
    }
    return out, gt


# ---------------------------------------------------------------------------
# Fixture registry
# ---------------------------------------------------------------------------

@dataclass
class FixtureSpec:
    fixture_id: str
    description: str
    builder: Callable[[], tuple[np.ndarray, dict]]
    fixture_class: str  # e.g. "constant_grid", "phase_offset", "meter", "structure", "energy", "variable_tempo"


def registry() -> list[FixtureSpec]:
    return [
        FixtureSpec(
            "FIX-A-constant-120bpm-4-4",
            "Constant 120 BPM, 4/4, 16 bars, exact beat grid, downbeat accented on beat 1.",
            lambda: build_constant_grid(120.0, 16, beats_per_bar=4, accent_beat=0),
            "constant_grid",
        ),
        FixtureSpec(
            "FIX-B-half-beat-phase-offset",
            "Constant 128 BPM, 4/4, 12 bars, grid deliberately offset 0.5 beat from t=0 "
            "(tests whether trackers lock onto the true phase rather than an arbitrary one).",
            lambda: build_phase_offset(128.0, 12, offset_beats=0.5, beats_per_bar=4),
            "phase_offset",
        ),
        FixtureSpec(
            "FIX-C-wrong-downbeat-phase",
            "Constant 100 BPM, 4/4, 12 bars, evenly spaced beats but the low-pitched "
            "'downbeat' accent falls on beat index 2 (0-based) of every bar, not beat 0 "
            "(tests downbeat/bar-phase correctness independent of beat correctness).",
            lambda: build_wrong_downbeat_phase(100.0, 12, true_accent_beat=2, beats_per_bar=4),
            "bar_phase",
        ),
        FixtureSpec(
            "FIX-D-4-4-reference",
            "Constant 140 BPM, 4/4, 12 bars — same-meter reference paired with FIX-E's 3/4 case.",
            lambda: build_non_4_4(140.0, 12, beats_per_bar=4),
            "meter",
        ),
        FixtureSpec(
            "FIX-E-non-4-4-waltz",
            "Constant 90 BPM, 3/4 (waltz), 16 bars — deliberate non-4/4 meter case.",
            lambda: build_non_4_4(90.0, 16, beats_per_bar=3),
            "meter",
        ),
        FixtureSpec(
            "FIX-F-8bar-16bar-sections",
            "128 BPM, 4/4: intro(8 bars, kick only) -> verse(8 bars, +hats) -> "
            "chorus(16 bars, +bass) -> outro(8 bars, kick only). Exact section "
            "boundaries and phrase boundaries (=section starts) as ground truth.",
            lambda: build_sections(128.0, [("intro", 8), ("verse", 8), ("chorus", 16), ("outro", 8)]),
            "structure",
        ),
        FixtureSpec(
            "FIX-G-intro-body-outro-energy",
            "110 BPM, 4/4, 32 bars: quiet intro (25%) -> full-energy body (50%) -> "
            "fading outro (25%), exact per-beat target-amplitude envelope as ground truth.",
            lambda: build_intro_body_outro_energy(110.0, 32),
            "energy",
        ),
        FixtureSpec(
            "FIX-H-variable-tempo-ramp",
            "Linear tempo ramp 100 BPM -> 130 BPM over 96 beats, 4/4, exact "
            "per-beat instantaneous BPM and beat timestamps via closed-form integration.",
            lambda: build_variable_tempo(100.0, 130.0, 96),
            "variable_tempo",
        ),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "..", "local_audio"))
    ap.add_argument("--manifest-out", default=os.path.join(os.path.dirname(__file__), "manifest.json"))
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    manifest = {"sample_rate": SR, "generator": "generate_fixtures.py", "fixtures": []}

    for spec in registry():
        samples, gt = spec.builder()
        wav_path = os.path.join(out_dir, f"{spec.fixture_id}.wav")
        checksum = write_wav(wav_path, samples)
        entry = {
            "fixture_id": spec.fixture_id,
            "description": spec.description,
            "fixture_class": spec.fixture_class,
            "wav_relpath": os.path.relpath(wav_path, os.path.dirname(args.manifest_out)).replace("\\", "/"),
            "checksum": {"algo": "sha256", "value": checksum},
            "provenance": "SYNTHETIC",
            "license": "N/A (procedurally generated, owner-created, no third-party material)",
            "ground_truth": gt,
        }
        manifest["fixtures"].append(entry)
        print(f"wrote {wav_path} sha256={checksum[:12]}...")

    with open(args.manifest_out, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"manifest written to {args.manifest_out} ({len(manifest['fixtures'])} fixtures)")


if __name__ == "__main__":
    main()
