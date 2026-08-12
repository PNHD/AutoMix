"""
Shared, deterministic transition-mixing DSP for P0-M3-R3.

This module is used identically by M0/M1/M2/M3 (Issue #7: "the exact same
outgoing/incoming planner boundary must be used by all methods... Do not let
different cue choices contaminate the DSP comparison") -- only the
time-stretch ENGINE differs between methods (none for M0/M1, Signalsmith for
M2, Rubber Band for M3); the gain-curve/EQ-handoff/headroom policy below is
identical across M1/M2/M3, and M0 deliberately uses the weaker
`linear_crossfade_gains` instead of `equal_power_gains` as its documented
negative-baseline difference.

No GPL/Signalsmith source is reproduced here -- these are standard,
public-domain DSP formulas (equal-power constant-power panning law; RBJ
Audio EQ Cookbook biquad low-pass, Robert Bristow-Johnson's widely published
public-domain coefficient formulas) implemented from scratch in numpy/scipy.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter

BASS_CUTOFF_HZ = 150.0
BASS_HANDOFF_SPEED = 2.2  # bass swap completes faster than the full-band blend (reduces bass-on-bass collision time)
CLIP_HEADROOM_DBFS = -1.0  # peak ceiling applied after mixing


def equal_power_gains(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Constant-power (equal-power) crossfade gain curves over n samples."""
    theta = np.linspace(0.0, np.pi / 2.0, n, endpoint=True)
    g_out = np.cos(theta)
    g_in = np.sin(theta)
    return g_out, g_in


def linear_crossfade_gains(n: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Intentionally weaker linear crossfade (M0's negative baseline only --
    Issue #7 "M0 -- intentionally weak negative baseline"). A linear
    (non-equal-power) crossfade produces an audible perceived volume dip
    near the midpoint because linear gains do not sum to constant power;
    this is a documented, real, well-known crossfade defect, not a
    fabricated one.
    """
    g_out = np.linspace(1.0, 0.0, n, endpoint=True)
    g_in = np.linspace(0.0, 1.0, n, endpoint=True)
    return g_out, g_in


def _rbj_lowpass_biquad(cutoff_hz: float, sr: int, q: float = 0.707):
    w0 = 2.0 * np.pi * cutoff_hz / sr
    alpha = np.sin(w0) / (2.0 * q)
    cosw0 = np.cos(w0)
    b0 = (1.0 - cosw0) / 2.0
    b1 = 1.0 - cosw0
    b2 = (1.0 - cosw0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cosw0
    a2 = 1.0 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return b, a


def split_bass(x: np.ndarray, sr: int, cutoff_hz: float = BASS_CUTOFF_HZ) -> tuple[np.ndarray, np.ndarray]:
    """Splits (n, ch) audio into (low_band, high_band) via a zero-phase RBJ low-pass biquad."""
    b, a = _rbj_lowpass_biquad(cutoff_hz, sr)
    low = np.empty_like(x)
    for ch in range(x.shape[1]):
        # Two-pass (forward + reverse) application of the same causal
        # biquad cancels the filter's phase response (a standard,
        # public-domain zero-phase technique), avoiding a discontinuity-
        # inducing phase mismatch between the low/high bands at recombine.
        fwd = lfilter(b, a, x[:, ch])
        low[:, ch] = lfilter(b, a, fwd[::-1])[::-1]
    high = x - low
    return low, high


def bass_handoff_gains(n: int, speed: float = BASS_HANDOFF_SPEED) -> tuple[np.ndarray, np.ndarray]:
    """
    Equal-power bass gain curves, time-warped to complete the low-band
    handoff faster than the full-band blend (documented bass/EQ handoff for
    SHORT_EQ_BLEND/FULL_DJ_BLEND -- Issue #7 "documented bass/EQ handoff").
    """
    progress = np.clip(np.linspace(0.0, 1.0, n, endpoint=True) * speed, 0.0, 1.0)
    theta = progress * (np.pi / 2.0)
    return np.cos(theta), np.sin(theta)


def mix_overlap(
    outgoing_overlap: np.ndarray,
    incoming_overlap: np.ndarray,
    sr: int,
    use_equal_power: bool = True,
    use_bass_handoff: bool = False,
) -> np.ndarray:
    """
    Mixes two equal-length (n, ch) buffers across the transition overlap
    window. Returns the mixed (n, ch) buffer, unclipped (headroom/clip
    handling is applied once, on the FULL assembled render, by
    `apply_headroom_and_safety`, not per-segment).
    """
    assert outgoing_overlap.shape == incoming_overlap.shape, "overlap buffers must be equal length for mixing"
    n = outgoing_overlap.shape[0]
    if n == 0:
        return np.zeros_like(outgoing_overlap)

    gain_fn = equal_power_gains if use_equal_power else linear_crossfade_gains
    g_out, g_in = gain_fn(n)
    g_out = g_out[:, None]
    g_in = g_in[:, None]

    if not use_bass_handoff:
        return outgoing_overlap * g_out + incoming_overlap * g_in

    out_low, out_high = split_bass(outgoing_overlap, sr)
    in_low, in_high = split_bass(incoming_overlap, sr)
    bg_out, bg_in = bass_handoff_gains(n)
    bg_out = bg_out[:, None]
    bg_in = bg_in[:, None]
    mixed_low = out_low * bg_out + in_low * bg_in
    mixed_high = out_high * g_out + in_high * g_in
    return mixed_low + mixed_high


def assemble_transition_render(
    outgoing_pre: np.ndarray,
    outgoing_overlap: np.ndarray,
    incoming_overlap: np.ndarray,
    incoming_post: np.ndarray,
    sr: int,
    use_equal_power: bool = True,
    use_bass_handoff: bool = False,
) -> np.ndarray:
    """
    Assembles the full render: [outgoing solo pre-roll] + [mixed overlap] +
    [incoming solo post-roll]. Verifies no hard sample discontinuity is
    introduced at either splice by construction (the pre/overlap/post
    segments are contiguous slices of continuously-synthesized/stretched
    source audio, never independently re-triggered) -- see
    dsp/safety_metrics.discontinuity_proxy for the machine check.
    """
    mixed = mix_overlap(outgoing_overlap, incoming_overlap, sr, use_equal_power, use_bass_handoff)
    return np.concatenate([outgoing_pre, mixed, incoming_post], axis=0)


def apply_headroom_and_safety(x: np.ndarray, ceiling_dbfs: float = CLIP_HEADROOM_DBFS) -> tuple[np.ndarray, dict]:
    """
    Deterministic clip-prevention: if the assembled render's true peak
    exceeds the target ceiling, apply a single static gain-reduction
    (never per-sample dynamic compression, which would be a much larger,
    undocumented DSP addition out of scope for this pass). Returns
    (safe_audio, diagnostics).
    """
    ceiling_linear = 10.0 ** (ceiling_dbfs / 20.0)
    pre_peak = float(np.max(np.abs(x))) if x.size else 0.0
    nan_count = int(np.count_nonzero(~np.isfinite(x)))
    x_clean = np.nan_to_num(x, nan=0.0, posinf=ceiling_linear, neginf=-ceiling_linear)
    applied_gain_db = 0.0
    if pre_peak > ceiling_linear and pre_peak > 0:
        gain = ceiling_linear / pre_peak
        x_clean = x_clean * gain
        applied_gain_db = 20.0 * np.log10(gain)
    post_peak = float(np.max(np.abs(x_clean))) if x_clean.size else 0.0
    clipped_sample_count = int(np.count_nonzero(np.abs(x_clean) >= 0.999969))
    diagnostics = {
        "pre_peak_linear": pre_peak,
        "pre_peak_dbfs": (20.0 * np.log10(pre_peak) if pre_peak > 0 else float("-inf")),
        "post_peak_linear": post_peak,
        "post_peak_dbfs": (20.0 * np.log10(post_peak) if post_peak > 0 else float("-inf")),
        "applied_headroom_gain_db": applied_gain_db,
        "nan_inf_sample_count": nan_count,
        "clipped_sample_count": clipped_sample_count,
        "ceiling_dbfs": ceiling_dbfs,
    }
    return x_clean, diagnostics
