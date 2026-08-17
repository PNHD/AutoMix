"""P0-M3-R3 RM041<->RM014 evidence stability -- A6/A7 harmonic window-sensitivity.

Reuses the EXACT independent harmonic-oracle methodology already accepted
for Issue #7 (``tools/p0m3/audio_render_shootout/scripts/wsl_bounded_audio_oracles.py``'s
``cqt_key_at`` / ``_profile_key``: librosa CQT chroma + Krumhansl-Schmuckler
major/minor key profiles) and the EXACT unmodified
``select_real_music_pairs.harmonic_relationship`` pairwise semantics.
Neither function is changed. No new harmonic threshold or oracle is
introduced (A8).

For the two accepted boundaries (RM041 outgoing exit at 186456.2 ms, RM014
incoming entry at 0.0 ms -- taken verbatim from the accepted
``three_pair_replay_sanitized.json`` V2 RM041->RM014 row), this script
sweeps window length {10, 15, 20, 30} seconds and boundary perturbation
{-1000, -500, 0, +500, +1000} ms. A cell whose resulting window would fall
outside the actual available audio (entry perturbations before track
start) is recorded as ``OUT_OF_AVAILABLE_AUDIO_RANGE`` and excluded from
aggregate statistics -- never fabricated.

Private paths are read only from the existing approved local opaque
mapping and are never written to the output file.
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

OPAQUE_ID = re.compile(r"^RM\d{3}$")
ANALYSIS_SR = 44_100
FEATURE_SR = 22_050
HOP = 512
WINDOW_LENGTHS_S = [10.0, 15.0, 20.0, 30.0]
PERTURBATIONS_MS = [-1000, -500, 0, 500, 1000]

RM041_EXIT_ACCEPTED_MS = 186456.2
RM014_ENTRY_ACCEPTED_MS = 0.0

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


def sweep(y: np.ndarray, sr: int, boundary_ms: float, role: str) -> list[dict]:
    cells = []
    for length_s in WINDOW_LENGTHS_S:
        for pert_ms in PERTURBATIONS_MS:
            boundary_perturbed = boundary_ms + pert_ms
            if role == "exit":
                end_ms = boundary_perturbed
                start_ms = end_ms - length_s * 1000.0
            else:
                start_ms = boundary_perturbed
                end_ms = start_ms + length_s * 1000.0
            estimate = key_in_window(y, sr, start_ms, end_ms)
            cells.append({
                "role": role,
                "window_length_s": length_s,
                "boundary_perturbation_ms": pert_ms,
                **estimate,
            })
    return cells


def pair_cells(exit_cells: list[dict], entry_cells: list[dict]) -> list[dict]:
    entry_by_key = {(c["window_length_s"], c["boundary_perturbation_ms"]): c for c in entry_cells}
    rows = []
    for exit_cell in exit_cells:
        key = (exit_cell["window_length_s"], exit_cell["boundary_perturbation_ms"])
        entry_cell = entry_by_key.get(key)
        if entry_cell is None:
            continue
        if exit_cell["status"] != "MEASURED" or entry_cell["status"] != "MEASURED":
            rows.append({
                "window_length_s": key[0],
                "boundary_perturbation_ms": key[1],
                "status": "EXCLUDED_OUT_OF_RANGE",
                "relation": None,
            })
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
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    for track_id in ("RM041", "RM014"):
        if track_id not in mapping:
            raise ValueError("OPAQUE_ID_MISSING_FROM_APPROVED_MAPPING")

    y41, sr41 = load_audio(windows_to_wsl(str(mapping["RM041"])))
    y14, sr14 = load_audio(windows_to_wsl(str(mapping["RM014"])))

    exit_cells = sweep(y41, sr41, RM041_EXIT_ACCEPTED_MS, "exit")
    entry_cells = sweep(y14, sr14, RM014_ENTRY_ACCEPTED_MS, "entry")
    pair_rows = pair_cells(exit_cells, entry_cells)

    output = {
        "schema_version": 1,
        "scope": "RM041 exit -> RM014 entry ONLY",
        "methodology_source": "wsl_bounded_audio_oracles.py::cqt_key_at/_profile_key (unmodified methodology, "
                               "reimplemented here to sweep window/perturbation instead of a single fixed window)",
        "pair_relation_function_source": "select_real_music_pairs.harmonic_relationship (imported unmodified)",
        "accepted_boundaries_ms": {"rm041_exit": RM041_EXIT_ACCEPTED_MS, "rm014_entry": RM014_ENTRY_ACCEPTED_MS},
        "window_lengths_s_tested": WINDOW_LENGTHS_S,
        "boundary_perturbations_ms_tested": PERTURBATIONS_MS,
        "rm041_exit_cells": exit_cells,
        "rm014_entry_cells": entry_cells,
        "pair_relation_by_matched_window_perturbation": pair_rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    measured_exit = sum(1 for c in exit_cells if c["status"] == "MEASURED")
    measured_entry = sum(1 for c in entry_cells if c["status"] == "MEASURED")
    print(f"HARMONIC_SENSITIVITY_COMPLETE exit_measured={measured_exit}/{len(exit_cells)} "
          f"entry_measured={measured_entry}/{len(entry_cells)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
