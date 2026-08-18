"""
P0-M5-R1 repair verifier -- synthetic unit checks proving two repair
passes' fixes, entirely against synthetic data (no private corpus):

  - repair 1 (BLOCKER 1, Issue #10 comment `5322363724`): local tempo now
    comes from `beats_s` (not `downbeats_s`), the octave-ambiguity guard
    rejects a half/double misread, and the direct-ratio/no-folding rule is
    unchanged;
  - repair 2 (BLOCKER B, Issue #10 comment `5322996856`): the outgoing
    exit downbeat snap is now bounded to `min(4 local bars, 10 seconds)`
    instead of the old, permissive 45-second window that could pull a
    complex-mix exit more than 15 seconds earlier than the cached R2 late
    exit.

Usage:
    python tools/p0m5/apple_like_vertical_slice/verify_pair_discovery.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pair_discovery as pd  # noqa: E402

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def synth_beats(bpm: float, n: int = 40, start_s: float = 0.0) -> list:
    interval = 60.0 / bpm
    return [round(start_s + i * interval, 6) for i in range(n)]


def main() -> int:
    # 1. local_beat_tempo_near recovers the true BPM from beat events, not
    #    a bar/downbeat rate.
    beats_120 = synth_beats(120.0, start_s=100.0)
    est = pd.local_beat_tempo_near(beats_120, anchor_s=110.0)
    check("local_beat_tempo_near recovers ~120 BPM from beats_s", est is not None and abs(est - 120.0) < 0.5, str(est))

    # 2. Reproduces the exact PM-cited defect scenario: two tracks whose
    #    BAR rate coincides (~31.25) but whose true beat tempo is ~125 vs
    #    ~63.83 BPM (a near-exact octave relationship) -- direct-ratio-only
    #    tempo correction must reject this pair (correction >> 6%).
    out_beats = synth_beats(125.0, start_s=200.0)
    in_beats = synth_beats(63.83, start_s=0.0)
    out_bpm = pd.local_beat_tempo_near(out_beats, anchor_s=210.0)
    in_bpm = pd.local_beat_tempo_near(in_beats, anchor_s=5.0)
    ratio = in_bpm / out_bpm
    correction = abs(ratio - 1.0)
    check(
        "PM-cited defect scenario (125 vs 63.83 BPM) now fails the direct 6% envelope",
        correction > pd.MAX_TEMPO_CORRECTION,
        f"correction={correction:.4f}",
    )

    # 3. octave_ambiguous: a local estimate that is ~2x the track's own
    #    documented median must be flagged.
    check("octave_ambiguous flags a ~2x local/track-median mismatch", pd.octave_ambiguous(124.0, 62.0), "")
    check("octave_ambiguous flags a ~0.5x local/track-median mismatch", pd.octave_ambiguous(62.0, 124.0), "")
    check("octave_ambiguous does NOT flag a genuinely matching tempo", not pd.octave_ambiguous(120.0, 121.0), "")
    check("octave_ambiguous does NOT flag an ordinary non-octave difference (e.g. 120 vs 128)", not pd.octave_ambiguous(120.0, 128.0), "")

    # 4. Direct ratio only -- no half/double folding anywhere in the module
    #    (grep-level self-check: the word "fold" must not appear as active
    #    logic, only in comments explaining its absence).
    src = (HERE / "pair_discovery.py").read_text(encoding="utf-8")
    check("no half/double-time folding function exists in pair_discovery.py", "def fold" not in src and "normalized_bpm_ratio" not in src)

    # 5. Stretch-cover band classification.
    check("2.0% correction classified as stretch-cover", pd.STRETCH_COVER_MIN <= 0.02 <= pd.STRETCH_COVER_MAX)
    check("6.0% correction classified as stretch-cover (band boundary inclusive)", pd.STRETCH_COVER_MIN <= 0.06 <= pd.STRETCH_COVER_MAX)
    check("1.9% correction NOT classified as stretch-cover", not (pd.STRETCH_COVER_MIN <= 0.019 <= pd.STRETCH_COVER_MAX))
    check("0.0% correction NOT classified as stretch-cover", not (pd.STRETCH_COVER_MIN <= 0.0 <= pd.STRETCH_COVER_MAX))

    # 6. bar-period helper is independent of the beat-tempo helper (returns
    #    a period in seconds, not a bpm-shaped value) -- proves the two
    #    concerns (tempo vs bar-phase/window-sizing) are no longer conflated.
    downbeats_2s_bars = [0.0, 2.0, 4.0, 6.0, 8.0]
    bar_period = pd.local_bar_period_s_near(downbeats_2s_bars, anchor_s=4.0)
    check("local_bar_period_s_near returns a period in seconds (2.0s bars)", bar_period is not None and abs(bar_period - 2.0) < 1e-6, str(bar_period))

    # 7. BLOCKER B (Issue #10 comment 5322996856): bounded exit-downbeat
    #    neighborhood -- reproduces the PM-cited RM099->RM071 shape (raw
    #    exit far from the nearest forward downbeat, only a much-earlier
    #    backward one available) using synthetic data, and proves the
    #    fix now fails closed instead of snapping ~15s backward.
    bar_period_2s = 2.0  # -> neighborhood = min(4*2.0, 10.0) = 8.0s
    far_backward_only = [0.0, 50.0, 100.0]  # nothing within 8s of exit_t_s=120.0 forward or back
    check(
        "bounded_exit_downbeat: PM-cited shape (only a far backward downbeat available) now fails closed",
        pd.bounded_exit_downbeat(far_backward_only, exit_t_s=120.0, local_bar_period_s=bar_period_2s) is None,
    )

    forward_within_bound = [125.0, 200.0]  # 5s forward, within the 8s bound
    check(
        "bounded_exit_downbeat: prefers the nearest forward downbeat within the bound",
        pd.bounded_exit_downbeat(forward_within_bound, exit_t_s=120.0, local_bar_period_s=bar_period_2s) == 125.0,
    )

    forward_too_far = [135.0]  # 15s forward, OUTSIDE the 8s bound
    backward_within_bound = [115.0]  # 5s backward, within the 8s bound
    check(
        "bounded_exit_downbeat: rejects a forward candidate outside the bound and correctly falls back to a valid backward one within the bound",
        pd.bounded_exit_downbeat(forward_too_far + backward_within_bound, exit_t_s=120.0, local_bar_period_s=bar_period_2s) == 115.0,
    )

    # Neighborhood cap: 4 bars at a slow tempo (bar_period=5s -> 20s) must
    # still be capped at the 10s ceiling, never wider.
    slow_bar_period = 5.0
    just_outside_10s_cap = [131.0]  # 11s forward -- inside "4 bars" (20s) but OUTSIDE the 10s hard cap
    check(
        "bounded_exit_downbeat: 10s hard cap applies even when 4 local bars would be wider",
        pd.bounded_exit_downbeat(just_outside_10s_cap, exit_t_s=120.0, local_bar_period_s=slow_bar_period) is None,
    )
    just_inside_10s_cap = [129.0]  # 9s forward -- inside both the bar-based and the 10s cap
    check(
        "bounded_exit_downbeat: accepts a candidate just inside the 10s hard cap",
        pd.bounded_exit_downbeat(just_inside_10s_cap, exit_t_s=120.0, local_bar_period_s=slow_bar_period) == 129.0,
    )

    check("EXIT_NEIGHBORHOOD_MAX_BARS is exactly 4 (PM-specified)", pd.EXIT_NEIGHBORHOOD_MAX_BARS == 4)
    check("EXIT_NEIGHBORHOOD_MAX_S is exactly 10.0 (PM-specified)", pd.EXIT_NEIGHBORHOOD_MAX_S == 10.0)
    check("the old 45s permissive constant no longer exists", not hasattr(pd, "DOWNBEAT_SEARCH_WINDOW_S"))

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
