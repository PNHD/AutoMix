"""
PM STAGE A REVIEW R1 repair: "All M0/M1/M2/M3 final renders for one
scenario must share sample rate, channel count, and comparable sample/
time-domain boundary semantics" + "Add machine assertions that planned
overlap duration in milliseconds is invariant across methods except where
the transition class itself intentionally differs."

This is the verifier that would have caught the original R1 defect
(M2 writing 48kHz-labeled output while mixing 44.1kHz-domain arrays,
which silently shrank R3-A/C's reported overlap_duration_ms from 10000 to
9187.5 and R3-B's from 11000 to 10106.25).

Usage:
    python scripts/verify_cross_method_consistency.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

META_DIR = ROOT / "results" / "render_meta"
SCENARIOS = ["R3-A", "R3-B", "R3-C", "R3-D"]
METHODS = ["M0", "M1", "M2", "M3"]
OVERLAP_DURATION_TOLERANCE_MS = 0.05  # sub-sample rounding only, not a real tolerance band

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def main():
    for tid in SCENARIOS:
        metas = {}
        for method in METHODS:
            path = META_DIR / f"{tid}_{method}.json"
            if not path.exists():
                failures.append(f"{tid}_{method}.json missing -- cannot verify cross-method consistency")
                print(f"FAIL: {tid}_{method}.json missing")
                continue
            metas[method] = json.loads(path.read_text(encoding="utf-8"))

        if len(metas) < 2:
            continue

        # canonical_sample_rate is the authoritative field (R1 repair) --
        # every render produced after this repair sets it explicitly.
        sample_rates = {m: d.get("canonical_sample_rate") for m, d in metas.items()}
        channels = {m: d.get("channels") for m, d in metas.items()}
        overlap_ms = {m: d.get("overlap_duration_ms") for m, d in metas.items()}

        distinct_srs = set(sample_rates.values())
        check(len(distinct_srs) == 1 and None not in distinct_srs, f"{tid}: all methods share one canonical_sample_rate: {sample_rates}")

        distinct_channels = set(channels.values())
        check(len(distinct_channels) == 1 and None not in distinct_channels, f"{tid}: all methods share one channel count: {channels}")

        distinct_overlaps = set(overlap_ms.values())
        if len(distinct_overlaps) == 1:
            check(True, f"{tid}: overlap_duration_ms is invariant across methods: {overlap_ms}")
        else:
            max_diff = max(overlap_ms.values()) - min(overlap_ms.values())
            check(
                max_diff <= OVERLAP_DURATION_TOLERANCE_MS,
                f"{tid}: overlap_duration_ms invariant within {OVERLAP_DURATION_TOLERANCE_MS}ms across methods: {overlap_ms} (max diff {max_diff}ms)",
            )

    print(f"\n{'ALL CHECKS PASS' if not failures else f'{len(failures)} CHECK(S) FAILED'}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
