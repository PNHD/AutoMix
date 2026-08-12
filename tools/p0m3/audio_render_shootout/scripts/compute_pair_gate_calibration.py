"""
P0-M3-R3 STAGE-B EVIDENCE AUDIT REPAIR (B2/B3/B6) -- builds
`real_music/work_local/pair_gate_calibration_sanitized.json` from the
EXISTING cached corpus analysis only (`real_music/work_local/corpus/
corpus_analysis.local.json`) -- no audio is re-decoded, no analyzer is
re-run, nothing is rendered.

Produces, for the V1 (<=2% tempo deviation) and V2 (3-6%) tempo-eligible
universes separately:
  - total pair count before hard gates
  - exact PASS / MEASURED_INCOMPATIBLE / UNKNOWN_EVIDENCE count per
    independent R2 gate (never conflating "unproven" with "incompatible")
  - cumulative surviving count after each gate, applied in
    pair_gate_audit.GATE_ORDER
  - final intersection (FULL_DJ-eligible) count
  - percentile distributions (min/p05/p10/p20/p25/p50/p75/p80/p90/p95/max)
    of the 6 measured pair-feature gaps
  - an HONEST statement of whether the 5 hardcoded texture/energy
    thresholds have a reproducible derivation (they do not -- see
    THRESHOLD_CALIBRATION_NOT_PREVIOUSLY_PROVEN below)

Also produces a DIAGNOSTIC-ONLY threshold sensitivity matrix (B3):
texture thresholds at 0.75x/1x/1.25x/1.5x, energy thresholds at
comparable tighter/current/looser variants, recombined with the
UNCHANGED other gate statuses already computed above. This NEVER mutates
`select_real_music_pairs.py`'s production `TEXTURE_*`/`ENERGY_*`
constants and NEVER selects or renders a pair from a relaxed variant.

Usage:
    python scripts/compute_pair_gate_calibration.py \
        --corpus-dir real_music/work_local/corpus \
        --out real_music/work_local/pair_gate_calibration_sanitized.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import pair_gate_audit as audit  # noqa: E402
import select_real_music_pairs as selector  # noqa: E402
from policy.compatibility import evaluate_pair_compatibility  # noqa: E402

UNIVERSES = {"V1": (0.0, 0.02), "V2": (0.03, 0.06)}

PERCENTILES = [0, 5, 10, 20, 25, 50, 75, 80, 90, 95, 100]
METRICS = ["_centroid_gap_ratio", "_flatness_gap", "_onset_density_gap_ratio",
           "_projected_loudness_gap_db", "_projected_bass_gap_db", "_combined_energy_gap_db"]

THRESHOLD_CALIBRATION_STATEMENT = (
    "THRESHOLD_CALIBRATION_NOT_PREVIOUSLY_PROVEN. The 5 hardcoded values "
    "(TEXTURE_CENTROID_GAP_RATIO_MAX=0.20, TEXTURE_FLATNESS_GAP_MAX=0.10, "
    "TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX=0.20, ENERGY_STRONG_MAX_DB=13.0, "
    "ENERGY_MODERATE_MAX_DB=26.0) were originally picked during the prior "
    "session from ad-hoc, interactive percentile calculations run against "
    "a SMALL 20-TRACK SAMPLE subset (not the full 100-track corpus, not "
    "restricted to the V1/V2 tempo-eligible universes) -- those "
    "calculations were never saved as a runnable script and cannot be "
    "reproduced from any committed artifact. They are therefore honestly "
    "labeled PROJECT HEURISTIC values pending real validation, NOT a "
    "proven calibration. This file's own percentile distributions (below), "
    "computed reproducibly from the full cached 100-track analysis "
    "restricted to each real tempo-eligible universe, are offered as the "
    "basis for a FUTURE, properly-documented calibration pass -- they are "
    "NOT used here to silently justify the existing thresholds after the "
    "fact, and the existing thresholds were NOT changed by this audit."
)


def percentiles_of(values: list[float]) -> dict:
    if not values:
        return {f"p{p}": None for p in PERCENTILES}
    arr = np.array(values, dtype=float)
    return {f"p{p}": round(float(np.percentile(arr, p)), 4) for p in PERCENTILES}


def gate_breakdown(records: list[dict]) -> dict:
    total = len(records)
    per_gate = {}
    for gate in audit.GATE_ORDER:
        counts = {"PASS": 0, "MEASURED_INCOMPATIBLE": 0, "UNKNOWN_EVIDENCE": 0}
        for r in records:
            counts[r["gate_status"][gate]] += 1
        per_gate[gate] = counts

    cumulative = []
    surviving_ids = set(range(total))  # index-based
    for gate in audit.GATE_ORDER:
        surviving_ids = {i for i in surviving_ids if records[i]["gate_status"][gate] == "PASS"}
        cumulative.append({"after_gate": gate, "surviving_count": len(surviving_ids)})

    final_eligible = sum(1 for r in records if r["compat"].overall_dynamic_mix_eligible)
    return {
        "total_pair_count": total,
        "per_gate_pass_incompatible_unknown": per_gate,
        "cumulative_surviving_after_each_gate_in_order": cumulative,
        "gate_order": audit.GATE_ORDER,
        "final_full_dj_eligible_intersection_count": final_eligible,
    }


def metric_distributions(records: list[dict]) -> dict:
    out = {}
    for m in METRICS:
        vals = [r["compat_input"][m] for r in records]
        out[m.lstrip("_")] = {"n": len(vals), **percentiles_of(vals)}
    return out


def sensitivity_matrix(records: list[dict]) -> dict:
    """B3: diagnostic-only re-evaluation at threshold multipliers. Reuses
    each record's ALREADY-COMPUTED gate_status for every gate EXCEPT
    texture/energy (which are recomputed at each multiplier from the raw
    cached _centroid_gap_ratio/_flatness_gap/_onset_density_gap_ratio/
    _combined_energy_gap_db values) -- analysis_confidence is unaffected
    (it depends only on structure/genre/harmonic strength, never texture/
    energy, by construction -- see select_real_music_pairs.py)."""
    multipliers = [0.75, 1.0, 1.25, 1.50]
    base_centroid = selector.TEXTURE_CENTROID_GAP_RATIO_MAX
    base_flatness = selector.TEXTURE_FLATNESS_GAP_MAX
    base_onset = selector.TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX
    base_strong = selector.ENERGY_STRONG_MAX_DB

    results = []
    for mult in multipliers:
        centroid_max = base_centroid * mult
        flatness_max = base_flatness * mult
        onset_max = base_onset * mult
        strong_max = base_strong * mult

        surviving = 0
        dominant_fail_counts = {g: 0 for g in audit.GATE_ORDER}
        for r in records:
            ci = r["compat_input"]
            texture_ok_variant = (
                ci["_centroid_gap_ratio"] <= centroid_max
                and ci["_flatness_gap"] <= flatness_max
                and ci["_onset_density_gap_ratio"] <= onset_max
                and ci["vocal_collision_risk"] != "HIGH"
            )
            energy_ok_variant = ci["_combined_energy_gap_db"] <= strong_max  # only affects reported energy_continuity, not overall_dynamic_mix_eligible (see compatibility.py -- energy is NOT a hard gate)

            statuses = dict(r["gate_status"])
            statuses["texture"] = "PASS" if texture_ok_variant else "MEASURED_INCOMPATIBLE"
            all_pass = all(statuses[g] == "PASS" for g in audit.GATE_ORDER)
            if all_pass:
                surviving += 1
            for g in audit.GATE_ORDER:
                if statuses[g] != "PASS":
                    dominant_fail_counts[g] += 1

        dominant_gate = max(dominant_fail_counts, key=dominant_fail_counts.get) if records else None
        results.append({
            "texture_centroid_gap_ratio_max": round(centroid_max, 4),
            "texture_flatness_gap_max": round(flatness_max, 4),
            "texture_onset_density_gap_ratio_max": round(onset_max, 4),
            "energy_strong_max_db_diagnostic_only": round(strong_max, 2),
            "multiplier": mult,
            "surviving_count": surviving,
            "dominant_failing_gate": dominant_gate,
            "fail_counts_per_gate": dominant_fail_counts,
        })
    return {
        "note": "DIAGNOSTIC ONLY -- production thresholds in select_real_music_pairs.py are UNCHANGED by this computation. energy_strong_max_db is NOT a hard FULL_DJ gate in compatibility.py (only reported), included here for completeness against the PM's requested energy-threshold sensitivity variants.",
        "variants": results,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    corpus_dir = Path(args.corpus_dir)
    analysis = json.loads((corpus_dir / "corpus_analysis.local.json").read_text(encoding="utf-8"))

    report = {
        "threshold_calibration_statement": THRESHOLD_CALIBRATION_STATEMENT,
        "current_production_thresholds": {
            "TEXTURE_CENTROID_GAP_RATIO_MAX": selector.TEXTURE_CENTROID_GAP_RATIO_MAX,
            "TEXTURE_FLATNESS_GAP_MAX": selector.TEXTURE_FLATNESS_GAP_MAX,
            "TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX": selector.TEXTURE_ONSET_DENSITY_GAP_RATIO_MAX,
            "ENERGY_STRONG_MAX_DB": selector.ENERGY_STRONG_MAX_DB,
            "ENERGY_MODERATE_MAX_DB": selector.ENERGY_MODERATE_MAX_DB,
        },
        "universes": {},
    }

    for label, (lo, hi) in UNIVERSES.items():
        records = audit.audit_universe(analysis, lo, hi)
        report["universes"][label] = {
            "tempo_deviation_range_pct": [lo * 100, hi * 100],
            "gate_breakdown": gate_breakdown(records),
            "metric_distributions": metric_distributions(records),
            "sensitivity_matrix": sensitivity_matrix(records),
        }
        print(f"{label}: {len(records)} tempo-eligible pairs audited")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
