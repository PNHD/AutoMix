"""
P0-M4-R2 PF5 verifier (part 1) -- unit checks for the clean-room
`simpmusic_class_reference.py` formulas against synthetic values only (no
private corpus needed).

Usage:
    python tools/p0m4/narrow_validation/verify_simpmusic_class_reference.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import simpmusic_class_reference as sref  # noqa: E402

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def main() -> int:
    # Camelot: C major and A minor are relative keys -- same wheel number,
    # opposite ring (8B vs 8A) -- the standard convention scores this as
    # ADJACENT (distance 1, same tier as a perfect fifth), not identical
    # (distance 0 is reserved for the exact same key+mode).
    c_major = sref.camelot("C", "major")
    a_minor = sref.camelot("A", "minor")
    check("C major / A minor are relative keys (Camelot distance 1, adjacent)", sref.camelot_distance(c_major, a_minor) == 1, f"{c_major} vs {a_minor}")

    # Same key, same mode -> distance 0.
    check("identical key/mode -> Camelot distance 0", sref.camelot_distance(sref.camelot("G", "major"), sref.camelot("G", "major")) == 0)

    # A perfect fifth apart, same mode -> distance 1 (adjacent on the wheel).
    check("C major / G major (perfect fifth) -> Camelot distance 1", sref.camelot_distance(sref.camelot("C", "major"), sref.camelot("G", "major")) == 1)

    # Tritone apart, same mode -> maximally distant (6).
    check("C major / F# major (tritone) -> Camelot distance 6", sref.camelot_distance(sref.camelot("C", "major"), sref.camelot("F#", "major")) == 6)

    check("unknown root returns None", sref.camelot("H", "major") is None)
    check("unknown mode returns None", sref.camelot("C", "dorian") is None)
    check("camelot_distance(None, x) is None", sref.camelot_distance(None, sref.camelot("C", "major")) is None)

    # key_gap_factor tiers.
    hi = {"root": "C", "mode": "major", "confidence": "HIGH"}
    adjacent = {"root": "G", "mode": "major", "confidence": "HIGH"}
    two_away = {"root": "D", "mode": "major", "confidence": "HIGH"}
    far = {"root": "F#", "mode": "major", "confidence": "HIGH"}
    unknown = {"root": None, "mode": None, "confidence": "NONE"}
    check("key_gap_factor: distance<=1 -> 1.0", sref.key_gap_factor(hi, hi) == 1.0)
    check("key_gap_factor: distance==2 -> 1.1", sref.key_gap_factor(hi, two_away) == 1.1)
    check("key_gap_factor: distance<=4 -> 1.25", sref.key_gap_factor(hi, {"root": "A", "mode": "major", "confidence": "HIGH"}) == 1.25)
    check("key_gap_factor: distance>4 (tritone) -> 1.4", sref.key_gap_factor(hi, far) == 1.4)
    check("key_gap_factor: missing key -> UNKNOWN_GAP_DEFAULT_FACTOR (1.25)", sref.key_gap_factor(hi, unknown) == sref.UNKNOWN_GAP_DEFAULT_FACTOR)
    check("key_gap_factor: low-confidence key treated as missing", sref.key_gap_factor(hi, {"root": "C", "mode": "major", "confidence": "LOW"}) == sref.UNKNOWN_GAP_DEFAULT_FACTOR)

    # bpm_gap_factor: identical BPM -> ratio 1.0 -> factor 1.0.
    check("bpm_gap_factor: identical BPM -> 1.0", sref.bpm_gap_factor(120.0, 120.0) == 1.0)
    # Half/double normalization: 240 vs 120 should normalize to ratio 1.0 (double-time).
    check("bpm_gap_factor: double-time normalizes to ratio 1.0", sref.bpm_gap_factor(120.0, 240.0) == 1.0)
    check("bpm_gap_factor: half-time normalizes to ratio 1.0", sref.bpm_gap_factor(120.0, 60.0) == 1.0)

    # Auto duration: BPM missing/<=0 -> AUTO_FALLBACK_DURATION_MS.
    check(
        "resolve_auto_crossfade_duration_ms: BPM<=0 -> fallback 30000ms",
        sref.resolve_auto_crossfade_duration_ms(0, 120.0, hi, hi) == 30000.0,
    )

    # Auto duration always within [20000, 45000] across a spread of inputs.
    out_of_bounds = []
    for bpm_a in (70, 90, 110, 130, 150, 170):
        for bpm_b in (70, 100, 130, 160, 170):
            for key_b in (hi, two_away, far, unknown):
                d = sref.resolve_auto_crossfade_duration_ms(bpm_a, bpm_b, hi, key_b)
                if not (sref.DURATION_MIN_MS <= d <= sref.DURATION_MAX_MS):
                    out_of_bounds.append((bpm_a, bpm_b, d))
    check("resolve_auto_crossfade_duration_ms always within [20000,45000]ms", len(out_of_bounds) == 0, str(out_of_bounds[:5]))

    # comparator_boundary: exit_ms never negative, entry_ms always 0.
    b = sref.comparator_boundary(200000.0, 120.0, 121.0, hi, adjacent)
    check("comparator_boundary: entry_ms == 0", b["entry_ms"] == 0.0, str(b))
    check("comparator_boundary: exit_ms == duration - crossfade, non-negative", b["exit_ms"] == 200000.0 - b["crossfade_duration_ms"] and b["exit_ms"] >= 0)

    # Short track: exit_ms floors at 0, never negative.
    b_short = sref.comparator_boundary(10000.0, 120.0, 120.0, hi, hi)
    check("comparator_boundary: short track floors exit_ms at 0 (never negative)", b_short["exit_ms"] == 0.0, str(b_short))

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
