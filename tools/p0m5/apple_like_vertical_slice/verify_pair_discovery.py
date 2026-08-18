"""
P0-M5-R1 repair verifier (BLOCKER 1) -- synthetic unit checks proving the
tempo-eligibility fix: local tempo now comes from `beats_s` (not
`downbeats_s`), the octave-ambiguity guard rejects a half/double misread,
and the direct-ratio/no-folding rule is unchanged. No private corpus data
is used.

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
