"""P0-M3-R3 RM014 incoming-entry anchor feasibility -- harmonic
re-evaluation for the best 1-2 machine-derived candidate anchors (Issue #7
PM comment id 5310893724).

Reuses the EXACT existing bounded harmonic methodology already accepted for
Issue #7 (``wsl_bounded_audio_oracles.py``'s ``cqt_key_at``/``_profile_key``:
librosa CQT chroma + Krumhansl-Schmuckler profiles, reimplemented here
byte-for-byte identically to
``pair_stability/analyze_harmonic_sensitivity.py``'s ``key_in_window``/
``_profile_key``, itself already accepted) and the EXACT unmodified
``select_real_music_pairs.harmonic_relationship`` pairwise semantics.
Neither function is changed. No new estimator, no new confidence threshold,
no ``harmonic_relationship()`` change (A8 scope).

RM014 ONLY -- RM041 audio is NOT re-decoded; the already-accepted RM041
exit cells from ``pair_stability/results/harmonic_sensitivity.json`` are
reused verbatim for the pair-relation comparison.

Repeats the same window-length x perturbation sweep as the accepted 0-ms
pass, but rooted at each candidate anchor instead of 0 ms, and reports a
direct comparison against the accepted 0-ms result.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PureWindowsPath

import librosa
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "scripts"))

from select_real_music_pairs import harmonic_relationship  # noqa: E402

TRACK = "RM014"
ANALYSIS_SR = 44_100
FEATURE_SR = 22_050
HOP = 512
WINDOW_LENGTHS_S = [10.0, 15.0, 20.0, 30.0]
PERTURBATIONS_MS = [-1000, -500, 0, 500, 1000]

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def windows_to_wsl(value: str) -> Path:
    if re.match(r"^[A-Za-z]:[\\/]", value):
        path = PureWindowsPath(value)
        drive = path.drive.rstrip(":").lower()
        return Path("/mnt") / drive / Path(*path.parts[1:])
    return Path(value)


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1, dtype=np.float32)
    if sr != ANALYSIS_SR:
        mono = librosa.resample(mono, orig_sr=sr, target_sr=ANALYSIS_SR, res_type="soxr_hq")
        sr = ANALYSIS_SR
    return np.asarray(mono, dtype=np.float32), sr


def _profile_key(chroma: np.ndarray) -> dict:
    vector = np.mean(chroma, axis=1)
    total = float(np.sum(vector))
    if total <= 1e-12:
        return {"root": None, "mode": None, "top_score": None, "second_score": None, "margin": 0.0, "confidence": "NONE"}
    vector = vector / total
    scored = []
    for mode, profile in (("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)):
        for root in range(12):
            rolled = np.roll(profile, root)
            score = float(np.corrcoef(vector, rolled)[0, 1])
            scored.append((score, root, mode))
    scored.sort(reverse=True)
    best, second = scored[0], scored[1]
    margin = best[0] - second[0]
    confidence = "HIGH" if margin >= 0.08 else "MEDIUM" if margin >= 0.04 else "LOW"
    return {
        "root": PITCH_CLASSES[best[1]],
        "mode": best[2],
        "top_score": round(best[0], 6),
        "second_score": round(second[0], 6),
        "margin": round(margin, 6),
        "confidence": confidence,
    }


def key_in_window(y: np.ndarray, sr: int, start_ms: float, end_ms: float) -> dict:
    duration_ms = len(y) / sr * 1000.0
    if start_ms < 0 or end_ms > duration_ms or end_ms <= start_ms:
        return {"status": "OUT_OF_AVAILABLE_AUDIO_RANGE"}
    start = int(round(start_ms / 1000.0 * sr))
    end = int(round(end_ms / 1000.0 * sr))
    window = y[start:end]
    if len(window) < sr * 2:
        return {"status": "OUT_OF_AVAILABLE_AUDIO_RANGE"}
    feature_y = librosa.resample(window, orig_sr=sr, target_sr=FEATURE_SR, res_type="soxr_hq")
    harmonic = librosa.effects.harmonic(feature_y)
    chroma = librosa.feature.chroma_cqt(y=harmonic, sr=FEATURE_SR, hop_length=HOP)
    estimate = _profile_key(chroma)
    return {
        "status": "MEASURED",
        "window_start_ms": round(start_ms, 1),
        "window_end_ms": round(end_ms, 1),
        **estimate,
    }


def sweep_entry(y: np.ndarray, sr: int, boundary_ms: float) -> list[dict]:
    cells = []
    for length_s in WINDOW_LENGTHS_S:
        for pert_ms in PERTURBATIONS_MS:
            start_ms = boundary_ms + pert_ms
            end_ms = start_ms + length_s * 1000.0
            estimate = key_in_window(y, sr, start_ms, end_ms)
            cells.append({
                "role": "entry",
                "window_length_s": length_s,
                "boundary_perturbation_ms": pert_ms,
                **estimate,
            })
    return cells


def summarize_stability(cells: list[dict]) -> dict:
    measured = [c for c in cells if c["status"] == "MEASURED"]
    root_modes = [(c["root"], c["mode"]) for c in measured]
    distinct = sorted(set(root_modes))
    counts = {f"{r} {m}": root_modes.count((r, m)) for r, m in distinct}
    agreement_fraction = (max(counts.values()) / len(measured)) if measured else None
    high_conf = sum(1 for c in measured if c["confidence"] == "HIGH")
    return {
        "n_measured": len(measured),
        "n_total_cells": len(cells),
        "distinct_root_mode_count": len(distinct),
        "root_mode_counts": counts,
        "modal_agreement_fraction": round(agreement_fraction, 4) if agreement_fraction is not None else None,
        "high_confidence_cell_count": high_conf,
        "root_mode_100pct_agreement": len(distinct) == 1 and len(measured) == len(cells),
    }


def pair_with_rm041_exit(entry_cells: list[dict], rm041_exit_cells: list[dict]) -> list[dict]:
    exit_by_key = {(c["window_length_s"], c["boundary_perturbation_ms"]): c for c in rm041_exit_cells}
    rows = []
    for entry_cell in entry_cells:
        key = (entry_cell["window_length_s"], entry_cell["boundary_perturbation_ms"])
        exit_cell = exit_by_key.get(key)
        if exit_cell is None or exit_cell["status"] != "MEASURED" or entry_cell["status"] != "MEASURED":
            rows.append({**{"window_length_s": key[0], "boundary_perturbation_ms": key[1]}, "status": "EXCLUDED_OUT_OF_RANGE", "relation": None})
            continue
        exit_key = {"root": exit_cell["root"], "mode": exit_cell["mode"], "confidence": exit_cell["confidence"]}
        entry_key = {"root": entry_cell["root"], "mode": entry_cell["mode"], "confidence": entry_cell["confidence"]}
        relation = harmonic_relationship(exit_key, entry_key)
        rows.append({
            "window_length_s": key[0],
            "boundary_perturbation_ms": key[1],
            "status": "MEASURED",
            "exit_root_mode": f"{exit_cell['root']} {exit_cell['mode']}",
            "entry_root_mode": f"{entry_cell['root']} {entry_cell['mode']}",
            "relation": relation if relation is not None else "UNKNOWN",
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--intro-clusters", required=True)
    parser.add_argument("--accepted-harmonic-sensitivity", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    if TRACK not in mapping:
        raise ValueError("OPAQUE_ID_MISSING_FROM_APPROVED_MAPPING")

    clusters = json.loads(Path(args.intro_clusters).read_text(encoding="utf-8"))
    top_candidates = clusters["clusters_ranked"][:2]

    accepted = json.loads(Path(args.accepted_harmonic_sensitivity).read_text(encoding="utf-8"))
    accepted_entry_cells_0ms = accepted["rm014_entry_cells"]
    accepted_exit_cells_rm041 = accepted["rm041_exit_cells"]
    accepted_summary_0ms = summarize_stability(accepted_entry_cells_0ms)

    y, sr = load_audio(windows_to_wsl(str(mapping[TRACK])))

    candidates_out = {}
    for c in top_candidates:
        boundary_ms = c["center_ms"]
        entry_cells = sweep_entry(y, sr, boundary_ms)
        summary = summarize_stability(entry_cells)
        pair_rows = pair_with_rm041_exit(entry_cells, accepted_exit_cells_rm041)
        key = f"rank{c['diagnostic_rank']}_center_{boundary_ms}ms"
        candidates_out[key] = {
            "candidate_center_ms": boundary_ms,
            "candidate_diagnostic_rank": c["diagnostic_rank"],
            "candidate_support_count": c["support_count"],
            "entry_cells": entry_cells,
            "stability_summary": summary,
            "pair_relation_vs_accepted_rm041_exit_cells": pair_rows,
            "vs_accepted_0ms_result": {
                "0ms_modal_agreement_fraction": accepted_summary_0ms["modal_agreement_fraction"],
                "candidate_modal_agreement_fraction": summary["modal_agreement_fraction"],
                "0ms_high_confidence_cell_count": accepted_summary_0ms["high_confidence_cell_count"],
                "candidate_high_confidence_cell_count": summary["high_confidence_cell_count"],
                "0ms_distinct_root_mode_count": accepted_summary_0ms["distinct_root_mode_count"],
                "candidate_distinct_root_mode_count": summary["distinct_root_mode_count"],
                "materially_improves_stability": (
                    (summary["modal_agreement_fraction"] or 0) > (accepted_summary_0ms["modal_agreement_fraction"] or 0)
                    and summary["distinct_root_mode_count"] <= accepted_summary_0ms["distinct_root_mode_count"]
                ),
            },
        }

    output = {
        "schema_version": 1,
        "scope": "RM014 entry ONLY (RM041 exit audio not re-decoded; accepted RM041 exit cells reused verbatim)",
        "methodology_source": "wsl_bounded_audio_oracles.py::cqt_key_at/_profile_key via pair_stability/analyze_harmonic_sensitivity.py (unmodified methodology)",
        "pair_relation_function_source": "select_real_music_pairs.harmonic_relationship (imported unmodified)",
        "window_lengths_s_tested": WINDOW_LENGTHS_S,
        "boundary_perturbations_ms_tested": PERTURBATIONS_MS,
        "accepted_0ms_entry_cells": accepted_entry_cells_0ms,
        "accepted_0ms_stability_summary": accepted_summary_0ms,
        "candidates": candidates_out,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    for key, c in candidates_out.items():
        print(f"{key}: modal_agreement={c['stability_summary']['modal_agreement_fraction']} "
              f"distinct_root_modes={c['stability_summary']['distinct_root_mode_count']} "
              f"materially_improves={c['vs_accepted_0ms_result']['materially_improves_stability']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
