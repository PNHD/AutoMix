"""
P0-M4-R2 PF5 -- SIMPMUSIC_CLASS_REFERENCE clean-room NG2 comparator.

`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` SS6.2/SS6.3/SS16.5
requires the NG2 comparator to be either actual SimpMusic (Tier-1
`IDENTICAL_AUDIO_COMPARISON`, if local playback is confirmed runnable) or
the already-authorized clean-room `SIMPMUSIC_CLASS_REFERENCE`. No accepted
evidence anywhere in this repository confirms actual SimpMusic is locally
Tier-1-runnable (`docs/research/P0-M1-SIMPMUSIC-AUTOMIX-FORENSIC.md` only
forensically analyzed the pinned source tree via `git fetch`; it was never
built or played back for audio comparison) -- so this task uses the
clean-room path, exactly as SS6.3 anticipates.

This module re-implements ONLY the public, `REIMPLEMENT_CLEAN_ROOM`-
classified arithmetic formulas P0-M1 SS6 already cited to exact SimpMusic
file/line ranges (equal-power cos/sin crossfade curve; Auto-duration
BPM/key-gap arithmetic; the standard, industry-public Camelot-wheel
key-distance convention used by essentially every DJ/harmonic-mixing tool,
not SimpMusic-specific IP) -- no SimpMusic/`core` GPLv3 source is read,
copied, or executed by this module. DJ mode is OFF (P0-M1 SS10's own
recommendation: score the plain equal-power path as the primary NG2
baseline), so no biquad filter sweep is reproduced either -- the comparator
uses the SAME `dsp.mixing.assemble_transition_render(use_equal_power=True,
use_bass_handoff=False, curve="equal_power")` call our own candidate
already uses (SS9.1 of the rescope contract) -- zero new DSP.

Formulas (P0-M1 SS6, "Auto crossfade duration" / "Camelot key mapping" /
"Camelot distance" rows), applied to already-cached corpus_analysis fields
(bpm, key root/mode) -- no new analyzer:

    base_ms          = 30000 - (clamp(bpm, 70, 170) - 70) * 230
    bpm_gap_factor    = 1 + |1 - normalized_ratio| * 2.0
        normalized_ratio = next_bpm / current_bpm, halved/doubled while
        >1.5 or <0.67 (half/double-time normalization)
    key_gap_factor    = 1.0 / 1.1 / 1.25 / 1.4 by Camelot distance
                        <=1 / ==2 / <=4 / else; UNKNOWN_GAP_DEFAULT_FACTOR
                        = 1.25 if either side's key is missing/low-confidence
    duration_ms       = base_ms * bpm_gap_factor * key_gap_factor,
                        snapped to the nearest of [8,16,24,32,40,48,64,80,96]
                        beats (beat_ms = 60000/bpm), clamped to [20000,45000]
    AUTO_FALLBACK_DURATION_MS = 30000 if BPM missing/<=0

Exit point (outgoing): duration_ms before the outgoing track's own full
duration -- pure arithmetic from `duration_ms`, never a chosen musical
point (P0-M1 SS8 level 7, `CUE_AWARE: NOT_FOUND_IN_PINNED_BASELINE`).
Entry point (incoming): always t=0 (P0-M1 SS8 level 3, incoming always
starts at 0) -- which also matches this task's own NG3 binding default.
"""
from __future__ import annotations

BEAT_COUNT_OPTIONS = [8, 16, 24, 32, 40, 48, 64, 80, 96]
DURATION_MIN_MS = 20000
DURATION_MAX_MS = 45000
AUTO_FALLBACK_DURATION_MS = 30000
UNKNOWN_GAP_DEFAULT_FACTOR = 1.25

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Standard, public Camelot-wheel major-key numbering (circle-of-fifths order
# starting at C=8B) -- industry-standard harmonic-mixing convention used by
# Mixed In Key, rekordbox, Serato, etc.; not SimpMusic-specific IP.
CAMELOT_NUMBER_BY_PITCH_CLASS = [8, 3, 10, 5, 12, 7, 2, 9, 4, 11, 6, 1]


def camelot(root: str, mode: str):
    """Returns (number 1-12, ring 'A'|'B') or None if root/mode unusable."""
    if root not in PITCH_CLASSES or mode not in ("major", "minor"):
        return None
    idx = PITCH_CLASSES.index(root)
    if mode == "major":
        return CAMELOT_NUMBER_BY_PITCH_CLASS[idx], "B"
    relative_major_idx = (idx + 3) % 12
    return CAMELOT_NUMBER_BY_PITCH_CLASS[relative_major_idx], "A"


def camelot_distance(a, b) -> int:
    if a is None or b is None:
        return None
    num_a, ring_a = a
    num_b, ring_b = b
    circular = min(abs(num_a - num_b), 12 - abs(num_a - num_b))
    return circular + (0 if ring_a == ring_b else 1)


def key_gap_factor(key_a: dict, key_b: dict) -> float:
    """key_a/key_b: {"root": str|None, "mode": str|None, "confidence": str}."""
    if not key_a or not key_b:
        return UNKNOWN_GAP_DEFAULT_FACTOR
    if key_a.get("confidence") not in ("MEDIUM", "HIGH") or key_b.get("confidence") not in ("MEDIUM", "HIGH"):
        return UNKNOWN_GAP_DEFAULT_FACTOR
    ca = camelot(key_a.get("root"), key_a.get("mode"))
    cb = camelot(key_b.get("root"), key_b.get("mode"))
    dist = camelot_distance(ca, cb)
    if dist is None:
        return UNKNOWN_GAP_DEFAULT_FACTOR
    if dist <= 1:
        return 1.0
    if dist == 2:
        return 1.1
    if dist <= 4:
        return 1.25
    return 1.4


def normalized_bpm_ratio(current_bpm: float, next_bpm: float) -> float:
    ratio = next_bpm / current_bpm
    while ratio > 1.5:
        ratio /= 2.0
    while ratio < 0.67:
        ratio *= 2.0
    return ratio


def bpm_gap_factor(current_bpm: float, next_bpm: float) -> float:
    ratio = normalized_bpm_ratio(current_bpm, next_bpm)
    return 1.0 + abs(1.0 - ratio) * 2.0


def snap_to_beat_count(duration_ms: float, bpm: float) -> float:
    beat_ms = 60000.0 / bpm
    best = min(BEAT_COUNT_OPTIONS, key=lambda n: abs(n * beat_ms - duration_ms))
    return best * beat_ms


def resolve_auto_crossfade_duration_ms(current_bpm, next_bpm, current_key: dict, next_key: dict) -> float:
    if not current_bpm or current_bpm <= 0:
        return float(AUTO_FALLBACK_DURATION_MS)
    base_ms = 30000.0 - (max(70.0, min(170.0, current_bpm)) - 70.0) * 230.0
    bgf = bpm_gap_factor(current_bpm, next_bpm) if next_bpm and next_bpm > 0 else UNKNOWN_GAP_DEFAULT_FACTOR
    kgf = key_gap_factor(current_key, next_key)
    duration_ms = base_ms * bgf * kgf
    duration_ms = snap_to_beat_count(duration_ms, current_bpm)
    return max(DURATION_MIN_MS, min(DURATION_MAX_MS, duration_ms))


def comparator_boundary(out_duration_ms: float, out_bpm, in_bpm, out_key: dict, in_key: dict) -> dict:
    """Returns {crossfade_duration_ms, exit_ms, entry_ms} for the
    SIMPMUSIC_CLASS_REFERENCE comparator, applied to one real pair."""
    crossfade_ms = resolve_auto_crossfade_duration_ms(out_bpm, in_bpm, out_key, in_key)
    exit_ms = max(0.0, out_duration_ms - crossfade_ms)
    return {"crossfade_duration_ms": crossfade_ms, "exit_ms": exit_ms, "entry_ms": 0.0}
