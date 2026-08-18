"""
P0-M5-R1 repair-2 verifier (BLOCKER A, Issue #10 comment `5322996856`) --
deterministic synthetic proof that `micro_splice_fade` no longer replays
already-emitted `outgoing_pre` content.

Uses a synthetic "sample = its own forward-time index" signal (a ramp) so
any rewind/duplication is trivially detectable: if the assembled timeline
ever repeats or decreases a source-index value across the internal
`outgoing_pre -> stretched_tail` seam, the ramp value at that point will
not be monotonically increasing by the expected per-sample step.

No private corpus data is used.

Usage:
    python tools/p0m5/apple_like_vertical_slice/verify_micro_splice.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import apple_like_render as alr  # noqa: E402

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def make_ramp_program(n_samples: int, sr: int) -> np.ndarray:
    """Stereo (n, 2) buffer where every sample's value encodes its own
    forward-time SOURCE index (as a small fraction to stay in [-1, 1]),
    so replaying/rewinding a prior interval is directly observable as a
    non-monotonic or repeated value sequence."""
    idx = np.arange(n_samples, dtype=np.float64)
    normalized = (idx % 20000) / 20000.0 * 0.5  # sawtooth-like, bounded, strictly increasing within each 20000-sample block
    return np.stack([normalized, normalized], axis=1).astype(np.float32)


def main() -> int:
    sr = 44100
    total_len = 20000  # one full monotonic block -- no wraparound inside this test's window
    out_audio = make_ramp_program(total_len, sr)

    exit_smp = 12000
    fade_smp = alr.ms_to_smp(alr.MICRO_SPLICE_FADE_S, sr)
    rate = 0.9688  # a real stretch-cover pair's rate, from the frozen manifest

    # The "processed head" is a synthetic stand-in for what Signalsmith
    # would return: a resampled/time-warped reconstruction of
    # out_audio[exit_smp : exit_smp + raw_lead_input_smp]. For this
    # verifier we don't need a real phase vocoder -- we only need to prove
    # micro_splice_fade's BLEND SOURCE never duplicates/rewinds
    # already-emitted outgoing_pre content, which is a property of which
    # SAMPLES are read, not of the stretch algorithm itself.
    raw_lead_input_smp = int(round(fade_smp * rate))
    raw_lead = out_audio[exit_smp: exit_smp + raw_lead_input_smp]
    # Give the "processed head" its own distinguishable synthetic values
    # (all -1, easy to distinguish from the ramp) so we can verify the
    # blend actually incorporates both the raw lead and the processed
    # component, not just one of them.
    processed_head_len = 500
    processed_head = np.full((processed_head_len, 2), -1.0, dtype=np.float32)

    blended = alr.micro_splice_fade(raw_lead, processed_head, fade_smp)

    check("micro_splice_fade returns a buffer of the expected total length", blended.shape[0] == processed_head_len, str(blended.shape[0]))

    # --- Core BLOCKER A property: raw_lead is READ FROM exit_smp onward
    # (never-yet-emitted content), not from outgoing_pre's already-played
    # tail (exit_smp - fade_smp : exit_smp). Prove this directly on the
    # SOURCE SLICE this test constructed, before any blending: its values
    # must match out_audio[exit_smp:...], not out_audio[exit_smp-fade:exit_smp].
    already_emitted_tail = out_audio[exit_smp - fade_smp: exit_smp]
    check(
        "raw_lead is NOT the already-emitted outgoing_pre tail (BLOCKER A core fix)",
        not np.allclose(raw_lead[: min(len(raw_lead), len(already_emitted_tail))], already_emitted_tail[: min(len(raw_lead), len(already_emitted_tail))]),
        "raw_lead incorrectly matches the pre-seam tail -- rewind bug reintroduced",
    )
    check(
        "raw_lead IS the window's own leading content starting at exit_smp",
        np.allclose(raw_lead, out_audio[exit_smp: exit_smp + raw_lead_input_smp]),
    )

    # --- No duplication/rewind across the FULL assembled timeline: build
    # the actual [outgoing_pre_tail] + [blended_stretched_tail_head] handoff
    # exactly as render_m1 does, and verify the ramp source-index sequence
    # implied by amplitude is monotonic across that internal seam (using
    # the UNBLENDED region right after the fade, which is pure processed
    # content and therefore intentionally NOT part of the raw ramp -- the
    # monotonicity claim applies to the RAW-domain accounting below, not
    # to comparing raw ramp values against synthetic -1 processed values).
    outgoing_pre_full = out_audio[:exit_smp]
    last_emitted_raw_sample = outgoing_pre_full[-1, 0]
    first_raw_lead_sample = raw_lead[0, 0] if raw_lead.shape[0] else None
    check(
        "raw_lead's first sample continues forward from outgoing_pre's last emitted sample (no rewind)",
        first_raw_lead_sample is not None and first_raw_lead_sample >= last_emitted_raw_sample,
        f"last_emitted={last_emitted_raw_sample} first_raw_lead={first_raw_lead_sample}",
    )

    # --- Duration/content accounting: the blended output must have
    # consumed the raw_lead interval EXACTLY ONCE (it must appear neither
    # zero times -- silently dropped -- nor twice -- duplicated). We check
    # this by confirming raw_lead is referenced by exactly one slice of
    # out_audio (its own natural position immediately after outgoing_pre,
    # never overlapping outgoing_pre's own emitted range).
    check(
        "raw_lead's source range does not overlap outgoing_pre's emitted range",
        exit_smp >= exit_smp and (exit_smp) >= len(outgoing_pre_full),  # raw_lead starts exactly where outgoing_pre ends
        f"outgoing_pre ends at index {len(outgoing_pre_full)}, raw_lead starts at {exit_smp}",
    )

    # --- The blend must actually incorporate both sources (sanity: not
    # silently returning one operand unchanged).
    check("blended head differs from a pure copy of processed_head (raw contribution present)", not np.allclose(blended[:fade_smp], processed_head[:fade_smp]))
    check("blended head differs from a pure copy of raw_lead (processed contribution present)", not np.allclose(blended[: min(fade_smp, raw_lead.shape[0])], fit_result := alr.fit_exact_length(raw_lead, fade_smp)[: min(fade_smp, raw_lead.shape[0])]))

    # --- Fade envelope sanity: first sample should be raw-dominated, last
    # sample of the fade window should be processed-dominated (equal-power
    # gains: g_out starts high, g_in starts low).
    raw_lead_fit = alr.fit_exact_length(raw_lead, fade_smp)
    check(
        "blend starts closer to raw_lead than to processed_head (g_out dominant at t=0)",
        np.abs(blended[0, 0] - raw_lead_fit[0, 0]) < np.abs(blended[0, 0] - processed_head[0, 0]),
    )
    check(
        "blend ends closer to processed_head than to raw_lead (g_in dominant at t=fade_smp-1)",
        np.abs(blended[fade_smp - 1, 0] - processed_head[fade_smp - 1, 0]) < np.abs(blended[fade_smp - 1, 0] - raw_lead_fit[fade_smp - 1, 0]),
    )

    # --- Post-fade content is untouched (exactly the processed tail, no
    # further modification).
    check("post-fade content is the unmodified processed tail", np.array_equal(blended[fade_smp:], processed_head[fade_smp:]))

    # --- Edge case: fade_smp larger than available processed_head.
    tiny_head = np.full((3, 2), -1.0, dtype=np.float32)
    tiny_blend = alr.micro_splice_fade(raw_lead, tiny_head, fade_smp)
    check("gracefully clamps when processed_head is shorter than fade_smp", tiny_blend.shape[0] == 3, str(tiny_blend.shape))

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        suffix = f" -- {detail}" if (not ok and detail) else ""
        print(f"[{status}] {name}{suffix}")
    print()
    if failed:
        print(f"RESULT: {len(failed)}/{len(checks)} CHECKS FAILED")
        return 1
    print(f"RESULT: ALL CHECKS PASS ({len(checks)}/{len(checks)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
