"""
Distinct outgoing/incoming diagnostic marker signatures (PM STAGE A REVIEW
R3 repair: "Use distinct diagnostic marker signatures for outgoing vs
incoming... different robust codes/frequencies/chirps, not the same
template").

Shared between `fixtures/synth.py` (embeds the marker into diagnostic
source audio at authoring time) and `dsp/safety_metrics.py` (builds the
IDENTICAL template waveform to matched-filter-detect it post-render) --
kept in one module so the embedded waveform and the detection template can
never drift apart.

The two markers are chosen to be spectrally and structurally distinct, not
merely differently-timed instances of the same template, so a
matched-filter search using the WRONG template scores low by construction
-- this is what makes "detected the same peak twice" structurally
impossible now, not merely unlikely.
"""
from __future__ import annotations

import numpy as np

# Outgoing: a single decaying pure tone.
#
# Amplitude/duration were tuned empirically (see
# docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md "R3 repair") against
# this project's own synthetic drum layers: `fixtures/synth.py`'s hats are
# a first-difference of white noise (i.e. deliberately broadband/high-pass
# content) and DO carry real energy in the 9-18kHz band, so a marker at
# the previous amplitude (0.22) was frequently outscored in matched-filter
# correlation by a nearby hat transient that happened to resemble the
# template better than the (partially masked, additively mixed) true
# marker did. Raising amplitude well above the local mix level and
# lengthening the marker make the true position the dominant, unambiguous
# correlation peak in practice -- verified empirically post-repair.
OUTGOING_MARKER_SPEC = {
    "role": "outgoing",
    "kind": "decaying_sine",
    "freq_hz": 9500.0,
    "decay_rate": 2200.0,
    "duration_s": 0.010,
    "amplitude": 0.85,
}

# Incoming: an upward chirp (rising instantaneous frequency) at a
# non-overlapping frequency band with a different decay rate -- both the
# spectral content AND the time-domain shape differ from the outgoing
# marker, so cross-template correlation stays low.
INCOMING_MARKER_SPEC = {
    "role": "incoming",
    "kind": "decaying_chirp",
    "freq_start_hz": 15500.0,
    "freq_end_hz": 19500.0,
    "decay_rate": 1800.0,
    "duration_s": 0.012,
    "amplitude": 0.85,
}

MARKER_SPECS_BY_ROLE = {
    "outgoing": OUTGOING_MARKER_SPEC,
    "incoming": INCOMING_MARKER_SPEC,
}


def marker_spec_for_role(role: str) -> dict:
    if role not in MARKER_SPECS_BY_ROLE:
        raise ValueError(f"unknown marker role {role!r}, expected 'outgoing' or 'incoming'")
    return MARKER_SPECS_BY_ROLE[role]


def build_marker_waveform(spec: dict, n: int, sr: int) -> np.ndarray:
    """Synthesizes exactly `n` samples of the marker described by `spec` at sample rate `sr`."""
    if n <= 0:
        return np.zeros(0)
    t = np.arange(n) / sr
    decay_rate = spec["decay_rate"]
    amplitude = spec["amplitude"]
    kind = spec["kind"]
    if kind == "decaying_sine":
        return np.sin(2 * np.pi * spec["freq_hz"] * t) * np.exp(-t * decay_rate) * amplitude
    if kind == "decaying_chirp":
        dur = n / sr
        f0, f1 = spec["freq_start_hz"], spec["freq_end_hz"]
        inst_freq = f0 + (f1 - f0) * (t / dur if dur > 0 else np.zeros_like(t))
        phase = 2 * np.pi * np.cumsum(inst_freq) / sr
        return np.sin(phase) * np.exp(-t * decay_rate) * amplitude
    raise ValueError(f"unknown marker kind {kind!r}")


def marker_duration_samples(spec: dict, sr: int) -> int:
    return max(1, int(round(spec["duration_s"] * sr)))
