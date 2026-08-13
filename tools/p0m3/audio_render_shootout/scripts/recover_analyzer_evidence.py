"""P0-M3-R3 bounded analyzer-evidence recovery for Issue #7.

The exact work set is derived from the cached top-10 V1 and top-10 V2 near
misses.  Only that deduplicated set is handed to the local WSL oracle worker.
Private paths exist solely in a gitignored job file.  All committed-safe
outputs contain opaque RM IDs and generic measurements only.

This runner preserves canonical R2 behavior.  Recovered evidence is applied
to an in-memory diagnostic overlay, then passed through the real existing R2
evaluator.  A confidence-ledger diagnostic is reported separately and cannot
create an ``HONEST_RENDER_CANDIDATE`` by itself.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import subprocess
import sys
from pathlib import Path, PureWindowsPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(HERE))

import pair_gate_audit as audit  # noqa: E402
import select_real_music_pairs as selector  # noqa: E402

OPAQUE_ID_RE = re.compile(r"^RM\d{3}$")
FRAME_HOP = 256
DOWNBEAT_MATCH_TOLERANCE_MS = 100.0
DOWNBEAT_CONFLICT_TOLERANCE_MS = 250.0
DOWNBEAT_MIN_EVENT_COUNT = 8
DOWNBEAT_MIN_MEDIAN_ACTIVATION = 0.20
DOWNBEAT_MAX_INTERVAL_CV = 0.12


def derive_subset(trace: dict) -> dict:
    lanes = {}
    all_ids = set()
    for label, key in (
        ("V1", "v1_near_misses_top10_ranked_by_fewest_failed_gates"),
        ("V2", "v2_near_misses_top10_ranked_by_fewest_failed_gates"),
    ):
        rows = trace.get(key, [])
        if len(rows) != 10:
            raise ValueError(f"{label}_NEAR_MISS_COUNT_NOT_10")
        pairs = []
        for row in rows:
            out_id, in_id = row["outgoing_opaque_id"], row["incoming_opaque_id"]
            if not OPAQUE_ID_RE.fullmatch(out_id) or not OPAQUE_ID_RE.fullmatch(in_id):
                raise ValueError("INVALID_OPAQUE_ID_IN_TRACE")
            pairs.append({"outgoing_opaque_id": out_id, "incoming_opaque_id": in_id})
            all_ids.update((out_id, in_id))
        lanes[label] = pairs
    return {
        "schema_version": 1,
        "derivation": "EXACT_UNION_OF_CACHED_TOP_10_V1_AND_TOP_10_V2_NEAR_MISSES",
        "source_trace_fields": [
            "v1_near_misses_top10_ranked_by_fewest_failed_gates",
            "v2_near_misses_top10_ranked_by_fewest_failed_gates",
        ],
        "v1_pair_count": len(lanes["V1"]),
        "v2_pair_count": len(lanes["V2"]),
        "unique_track_count": len(all_ids),
        "opaque_track_ids": sorted(all_ids),
        "pairs": lanes,
    }


def windows_to_wsl(path: Path | str) -> str:
    p = PureWindowsPath(str(Path(path).resolve()))
    if not p.drive:
        raise ValueError("WINDOWS_PATH_WITHOUT_DRIVE")
    drive = p.drive.rstrip(":").lower()
    return "/mnt/" + drive + "/" + "/".join(p.parts[1:])


def write_private_job(subset: dict, analysis: dict, id_map: dict, path: Path) -> None:
    rows = []
    for opaque_id in subset["opaque_track_ids"]:
        if opaque_id not in analysis or opaque_id not in id_map:
            raise ValueError("SUBSET_ID_MISSING_FROM_CACHE_OR_MAPPING")
        track = analysis[opaque_id]
        rows.append({
            "opaque_id": opaque_id,
            "private_path": windows_to_wsl(id_map[opaque_id]),
            "exit_candidate_t_ms": track["candidates"]["exit_candidate_t_ms"],
            "entry_candidate_t_ms": track["candidates"]["entry_candidate_t_ms"],
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tracks": rows}, indent=2), encoding="utf-8")


def run_wsl_worker(worker: Path, job: Path, output: Path, python_path: str) -> None:
    command = [
        "wsl", "--exec", python_path,
        windows_to_wsl(worker),
        "--job", windows_to_wsl(job),
        "--out", windows_to_wsl(output),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60 * 90)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("WSL_ORACLE_PROCESS_TIMEOUT") from exc
    if result.returncode not in (0, 2):
        raise RuntimeError(f"WSL_ORACLE_PROCESS_FAILED_EXIT_{result.returncode}")
    if not output.exists():
        raise RuntimeError("WSL_ORACLE_OUTPUT_MISSING")


def current_downbeat_grid_ms(track: dict) -> list[float]:
    frame_rate = float(track["sample_rate_analysis_hz"]) / FRAME_HOP
    period = float(track["tempo"]["period_frames"])
    base = float(track["beat"]["phase_frame"]) + float(track["downbeat"]["phase_of_4"]) * period
    step = 4.0 * period
    if frame_rate <= 0 or step <= 0:
        return []
    times = []
    frame = base
    duration_ms = float(track["duration_ms"])
    while frame / frame_rate * 1000.0 <= duration_ms:
        if frame >= 0:
            times.append(frame / frame_rate * 1000.0)
        frame += step
    return times


def nearest_error_ms(value: float, candidates: list[float]) -> float | None:
    return min((abs(value - candidate) for candidate in candidates), default=None)


def classify_downbeat(track: dict, oracle: dict) -> dict:
    measured = oracle.get("downbeat", {})
    oracle_times = [float(x) for x in measured.get("downbeats_ms", [])]
    heuristic_times = current_downbeat_grid_ms(track)
    errors = [nearest_error_ms(value, heuristic_times) for value in oracle_times]
    errors = [value for value in errors if value is not None]
    median_error = float(sorted(errors)[len(errors) // 2]) if errors else None
    count = int(measured.get("downbeat_count", 0))
    activation = measured.get("median_downbeat_activation")
    interval_cv = measured.get("downbeat_interval_cv")
    stable = count >= DOWNBEAT_MIN_EVENT_COUNT and interval_cv is not None and interval_cv <= DOWNBEAT_MAX_INTERVAL_CV
    activation_ok = activation is not None and activation >= DOWNBEAT_MIN_MEDIAN_ACTIVATION
    if stable and activation_ok and median_error is not None and median_error <= DOWNBEAT_MATCH_TOLERANCE_MS:
        status = "RESOLVED_HIGH"
    elif count >= DOWNBEAT_MIN_EVENT_COUNT and median_error is not None and median_error > DOWNBEAT_CONFLICT_TOLERANCE_MS:
        status = "RESOLVED_CONFLICT"
    else:
        status = "STILL_UNKNOWN"
    return {
        **measured,
        "current_heuristic_agreement_median_error_ms": round(median_error, 3) if median_error is not None else None,
        "agreement_tolerance_ms_project_diagnostic": DOWNBEAT_MATCH_TOLERANCE_MS,
        "resolution_rule_project_diagnostic": {
            "minimum_downbeat_count": DOWNBEAT_MIN_EVENT_COUNT,
            "minimum_median_downbeat_activation": DOWNBEAT_MIN_MEDIAN_ACTIVATION,
            "maximum_downbeat_interval_cv": DOWNBEAT_MAX_INTERVAL_CV,
            "resolved_high_maximum_median_grid_error_ms": DOWNBEAT_MATCH_TOLERANCE_MS,
            "resolved_conflict_minimum_median_grid_error_ms_exclusive": DOWNBEAT_CONFLICT_TOLERANCE_MS,
            "calibrated_product_confidence": False,
        },
        "status": status,
    }


def key_agreement(cached: dict, independent: dict) -> str:
    estimate = independent.get("estimate", {})
    if estimate.get("confidence") not in ("MEDIUM", "HIGH") or estimate.get("root") is None:
        return "STILL_UNKNOWN"
    if cached.get("root") is None or cached.get("confidence") == "NONE":
        return "STILL_UNKNOWN"
    if cached.get("root") == estimate.get("root") and cached.get("mode") == estimate.get("mode"):
        return "RESOLVED_AGREEMENT"
    return "RESOLVED_CONFLICT"


def overlay_track(track: dict, oracle: dict) -> tuple[dict, dict]:
    recovered = copy.deepcopy(track)
    downbeat = classify_downbeat(track, oracle)
    structure = oracle.get("structure", {})
    structure_status = "STILL_UNKNOWN_BOUNDARY_ONLY_NO_FUNCTIONAL_LABELS"
    harmonic_exit = oracle.get("harmonic", {}).get("exit", {})
    harmonic_entry = oracle.get("harmonic", {}).get("entry", {})
    exit_agreement = key_agreement(track.get("key_at_exit", track["key"]), harmonic_exit)
    entry_agreement = key_agreement(track.get("key_at_entry", track["key"]), harmonic_entry)

    recovered.setdefault("evidence_recovery", {})
    recovered["evidence_recovery"]["downbeat"] = {
        "source": downbeat.get("source", "MADMOM_RNN_DOWNBEAT_PLUS_DBN_BENCHMARK_ONLY"),
        "status": downbeat["status"],
    }
    recovered["evidence_recovery"]["structure"] = {
        "source": structure.get("source", "LIBROSA_SECTION_ORACLE_UNAVAILABLE"),
        "status": structure_status,
    }
    recovered["evidence_recovery"]["harmonic"] = {
        "source": "LIBROSA_CQT_KRUMHANSL_BENCHMARK_ONLY",
        "status": f"EXIT_{exit_agreement}__ENTRY_{entry_agreement}",
    }
    recovered["evidence_recovery"]["genre_style"] = {
        "source": "GENRE_STYLE_ORACLE_UNAVAILABLE",
        "status": "STILL_UNKNOWN",
    }
    if downbeat["status"] == "RESOLVED_HIGH":
        recovered["downbeat"]["confidence"] = "HIGH"
    elif downbeat["status"] == "RESOLVED_CONFLICT":
        # Conflicting oracle evidence is conservative UNKNOWN for replay;
        # never cherry-pick the cached heuristic merely because it passes.
        recovered["downbeat"]["confidence"] = "LOW"

    for field, agreement, independent in (
        ("key_at_exit", exit_agreement, harmonic_exit),
        ("key_at_entry", entry_agreement, harmonic_entry),
    ):
        if agreement == "RESOLVED_AGREEMENT":
            estimate = independent["estimate"]
            recovered[field]["confidence"] = estimate["confidence"]
        elif agreement == "RESOLVED_CONFLICT":
            recovered[field]["confidence"] = "LOW"

    safe_downbeat = {key: value for key, value in downbeat.items() if key != "beat_events"}
    safe = {
        "status": "OK",
        "downbeat": safe_downbeat,
        "structure": {**structure, "status": structure_status},
        "harmonic": {
            "exit": {**harmonic_exit, "agreement_with_cached_local_estimate": exit_agreement},
            "entry": {**harmonic_entry, "agreement_with_cached_local_estimate": entry_agreement},
        },
        "genre_style": {
            "source": "GENRE_STYLE_ORACLE_UNAVAILABLE",
            "status": "STILL_UNKNOWN",
            "cached_generic_style_evidence_available": bool(track.get("genre_tags")),
        },
    }
    return recovered, safe


def nearest_boundary_report(track: dict, oracle: dict, role: str) -> dict:
    target_ms = float(track["candidates"]["exit_candidate_t_ms" if role == "outgoing_exit" else "entry_candidate_t_ms"])
    boundaries = oracle.get("structure", {}).get("boundary_candidates", [])
    nearest = min(boundaries, key=lambda row: abs(float(row["t_ms"]) - target_ms), default=None)
    bpm = float(track["tempo"]["bpm"])
    beat_ms = 60_000.0 / bpm if bpm > 0 else None
    if nearest is None:
        distance_ms = None
    else:
        distance_ms = abs(float(nearest["t_ms"]) - target_ms)
    preceding = [float(row["t_ms"]) for row in boundaries if float(row["t_ms"]) <= target_ms]
    following = [float(row["t_ms"]) for row in boundaries if float(row["t_ms"]) > target_ms]
    return {
        "target_t_ms": round(target_ms, 1),
        "detected_section_interval_ms": [max(preceding) if preceding else 0.0, min(following) if following else round(float(track["duration_ms"]), 1)],
        "functional_label": None,
        "functional_label_status": "NOT_AVAILABLE_FROM_BOUNDARY_ONLY_ORACLE",
        "nearest_section_boundary_ms": nearest["t_ms"] if nearest else None,
        "boundary_distance_ms": round(distance_ms, 1) if distance_ms is not None else None,
        "boundary_distance_beats": round(distance_ms / beat_ms, 3) if distance_ms is not None and beat_ms else None,
        "boundary_distance_bars_assuming_cached_meter_4": round(distance_ms / (beat_ms * 4.0), 3) if distance_ms is not None and beat_ms else None,
        "analyzer_source": oracle.get("structure", {}).get("source"),
        "analyzer_status": "STILL_UNKNOWN_BOUNDARY_ONLY_NO_FUNCTIONAL_LABELS",
        "current_heuristic_method": track["candidates"].get("exit_structure_evidence_method") if role == "outgoing_exit" else (
            "INSTRUMENTAL_LEAD_DETECTED" if track["candidates"].get("entry_has_detected_intro") else
            "AUTHORED_SILENCE_SKIP" if track["candidates"].get("entry_is_authored_silence_skip") else "TRACK_START"
        ),
    }


def pair_harmonic_status(out_track: dict, in_track: dict, out_oracle: dict, in_oracle: dict) -> dict:
    current_out = selector.corroborated_key(out_track.get("key_at_exit", out_track["key"]), out_track["key"])
    current_in = selector.corroborated_key(in_track.get("key_at_entry", in_track["key"]), in_track["key"])
    current_relation = selector.harmonic_relationship(current_out, current_in)
    oracle_out = out_oracle.get("harmonic", {}).get("exit", {}).get("estimate", {})
    oracle_in = in_oracle.get("harmonic", {}).get("entry", {}).get("estimate", {})
    independent_relation = selector.harmonic_relationship(oracle_out, oracle_in)
    if current_relation is not None and current_relation == independent_relation:
        status = "RESOLVED_COMPATIBLE" if current_relation == "COMPATIBLE" else "RESOLVED_INCOMPATIBLE"
    elif current_relation is not None and independent_relation is not None:
        status = "RESOLVED_CONFLICT"
    else:
        status = "STILL_UNKNOWN"
    return {
        "current_local_estimate": {"outgoing": current_out, "incoming": current_in, "relation": current_relation},
        "independent_estimate": {"outgoing": oracle_out, "incoming": oracle_in, "relation": independent_relation},
        "status": status,
        "effective_boundary_local_relation": independent_relation,
    }


def replay_pair(
    category: str,
    original_row: dict,
    cached: dict,
    recovered: dict,
    oracle_tracks: dict,
) -> dict:
    out_id, in_id = original_row["outgoing_opaque_id"], original_row["incoming_opaque_id"]
    original_ci, original_compat, original_status, original_failed = audit.classify_pair(cached[out_id], cached[in_id])
    recovered_ci, recovered_compat, recovered_status, recovered_failed = audit.classify_pair(recovered[out_id], recovered[in_id])
    diagnostic = audit.confidence_ledger_diagnostic(recovered_status)
    resolved_unknown = [
        gate for gate in audit.GATE_ORDER
        if original_status[gate] == audit.UNKNOWN_EVIDENCE and recovered_status[gate] == audit.PASS
    ]
    remaining_incompatible = [gate for gate in audit.GATE_ORDER if recovered_status[gate] == audit.MEASURED_INCOMPATIBLE]
    remaining_unknown = [gate for gate in audit.GATE_ORDER if recovered_status[gate] == audit.UNKNOWN_EVIDENCE]
    honest = bool(recovered_compat.overall_dynamic_mix_eligible and selector.exit_candidate_renderable(recovered[out_id]))
    return {
        "category": category,
        "outgoing_opaque_id": out_id,
        "incoming_opaque_id": in_id,
        "original_failed_gates_from_cached_trace": original_row["failed_gates"],
        "original_failed_gates_recomputed": original_failed,
        "original_gate_status": original_status,
        "unknown_gates_resolved_by_new_evidence": resolved_unknown,
        "measured_incompatibilities_remaining": remaining_incompatible,
        "unknown_evidence_remaining": remaining_unknown,
        "current_strict_r2_verdict_after_recovery": "FULL_DJ_ELIGIBLE" if recovered_compat.overall_dynamic_mix_eligible else "FULL_DJ_WITHHELD",
        "current_strict_r2_failed_gates_after_recovery": recovered_failed,
        "current_strict_r2_reason_codes_after_recovery": recovered_compat.reason_codes,
        "confidence_ledger_diagnostic_verdict": "ELIGIBLE_DIAGNOSTIC_ONLY" if diagnostic["eligible"] else "WITHHELD_DIAGNOSTIC",
        "confidence_ledger_diagnostic": diagnostic,
        "confidence_ledger": recovered_ci["_confidence_ledger"],
        "honest_render_candidate_under_existing_r2": honest,
        "outgoing_boundary": nearest_boundary_report(cached[out_id], oracle_tracks[out_id], "outgoing_exit"),
        "incoming_boundary": nearest_boundary_report(cached[in_id], oracle_tracks[in_id], "incoming_entry"),
        "harmonic_recovery": pair_harmonic_status(cached[out_id], cached[in_id], oracle_tracks[out_id], oracle_tracks[in_id]),
    }


def result_enum(replays: list[dict]) -> str:
    if any(row["honest_render_candidate_under_existing_r2"] for row in replays):
        return "REAL_RENDER_CANDIDATE_RECOVERED"
    has_unknown = any(row["unknown_evidence_remaining"] for row in replays)
    has_incompatible = any(row["measured_incompatibilities_remaining"] for row in replays)
    if has_unknown and has_incompatible:
        return "ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY"
    if has_unknown:
        return "ANALYZER_EVIDENCE_STILL_INSUFFICIENT"
    if has_incompatible:
        return "MEASURED_INCOMPATIBILITY_DOMINATES"
    return "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--subset-out", required=True)
    parser.add_argument("--evidence-out", required=True)
    parser.add_argument("--wsl-python", default="/home/pnhd/allinone_venv/bin/python")
    parser.add_argument("--reuse-oracle-output", action="store_true")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    cached = json.loads((corpus_dir / "corpus_analysis.local.json").read_text(encoding="utf-8"))
    id_map = json.loads((corpus_dir / "id_map.local.json").read_text(encoding="utf-8"))
    subset = derive_subset(trace)
    Path(args.subset_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.subset_out).write_text(json.dumps(subset, indent=2), encoding="utf-8")

    work_dir = Path(args.work_dir)
    private_job = work_dir / "oracle_job.private.local.json"
    oracle_output = work_dir / "oracle_output.opaque.local.json"
    write_private_job(subset, cached, id_map, private_job)
    if not args.reuse_oracle_output or not oracle_output.exists():
        run_wsl_worker(HERE / "wsl_bounded_audio_oracles.py", private_job, oracle_output, args.wsl_python)
    oracle = json.loads(oracle_output.read_text(encoding="utf-8"))
    if set(oracle.get("tracks", {})) != set(subset["opaque_track_ids"]):
        raise RuntimeError("ORACLE_TRACK_SET_DIFFERS_FROM_DERIVED_SUBSET")

    recovered = {}
    sanitized_tracks = {}
    for opaque_id in subset["opaque_track_ids"]:
        row = oracle["tracks"][opaque_id]
        if row.get("status") != "OK":
            recovered[opaque_id] = copy.deepcopy(cached[opaque_id])
            sanitized_tracks[opaque_id] = {"status": "STILL_UNKNOWN", "error_code": row.get("error_code", "ORACLE_FAILED")}
            continue
        recovered[opaque_id], sanitized_tracks[opaque_id] = overlay_track(cached[opaque_id], row)

    replays = []
    for category, key in (
        ("V1", "v1_near_misses_top10_ranked_by_fewest_failed_gates"),
        ("V2", "v2_near_misses_top10_ranked_by_fewest_failed_gates"),
    ):
        for row in trace[key]:
            replays.append(replay_pair(category, row, cached, recovered, oracle["tracks"]))

    result = result_enum(replays)
    report = {
        "schema_version": 1,
        "result": result,
        "quality_pass_claimed": False,
        "render_candidate_count": sum(1 for row in replays if row["honest_render_candidate_under_existing_r2"]),
        "subset": subset,
        "confidence_ownership": {
            "canonical_r2_behavior": "UNCHANGED",
            "canonical_analysis_confidence": "MIN_OF_STRUCTURE_GENRE_HARMONIC_PRESERVED_FOR_BASELINE_ONLY",
            "confidence_ledger_diagnostic": "DIAGNOSTIC_ONLY_DOES_NOT_COUNT_AGGREGATE_AS_INDEPENDENT_GATE",
            "production_gate_changes": False,
        },
        "analyzer_provenance": {
            "all_in_one": {
                "retrieved_at_utc_date": "2026-08-13",
                "baseline_commit": "18e78903c0365147a2c5d4e5e57ebf88cb7d800e",
                "baseline_source": "https://github.com/mir-aidj/all-in-one/commit/18e78903c0365147a2c5d4e5e57ebf88cb7d800e",
                "published_compatibility_probe_commit": "5c2b2ce571c04054a0b54ceba365c0b8c1188099",
                "published_compatibility_source": "https://github.com/mir-aidj/all-in-one/pull/37",
                "upstream_blocker_source": "https://github.com/mir-aidj/all-in-one/issues/30",
                "installed_natten": "0.21.7+torch2130cu126",
                "status": "BLOCKED_NATTEN_0_21_API_IMPORT",
                "failure_code": "MISSING_LEGACY_AND_NA1D_QK_FUNCTIONAL_SYMBOLS",
                "license_boundary": "MIT_CODE; CHECKPOINT_TRAINING_AUDIO_PROVENANCE_REMAINS_UNKNOWN; NOT_EXECUTED",
            },
            "downbeat": {
                "source": "madmom RNNDownBeatProcessor + DBNDownBeatTrackingProcessor",
                "installed_ref": "27f032e8947204902c675e5e341a3faf5dc86dae",
                "role": "BENCHMARK_ONLY",
                "versions": oracle.get("analyzer_versions", {}),
                "confidence_note": "Raw RNN activation and DBN stability are diagnostics, not calibrated product confidence.",
                "license_boundary": "Installed metadata reports BSD and CC BY-NC-SA components; benchmark-only, not approved for production adoption.",
            },
            "structure": {
                "source": "librosa beat-synchronous CQT+MFCC+spectral-contrast change points",
                "role": "BENCHMARK_ONLY_BOUNDARY_EVIDENCE",
                "functional_labels": False,
                "phrase_claimed": False,
                "license": "librosa 0.11.0 ISC; benchmark algorithm written in this repository",
            },
            "harmonic": {
                "source": "librosa CQT + Krumhansl-Schmuckler profiles",
                "role": "BENCHMARK_ONLY_INDEPENDENT_FRONTEND",
                "license": "librosa 0.11.0 ISC; Krumhansl profiles used as research reference",
                "confidence_rule_project_diagnostic": "HIGH if top-two profile-score margin >=0.08; MEDIUM if >=0.04; otherwise LOW; not calibrated product confidence",
            },
            "genre_style": {
                "preferred_oracle": "Essentia Discogs-EffNet",
                "status": "GENRE_STYLE_ORACLE_UNAVAILABLE",
                "environment_evidence": "No installed Essentia/TensorFlow runtime; pip index returned no matching essentia distribution for WSL Python 3.12.",
                "production_adoption": False,
            },
            "beat_ownership": "UNCHANGED_CACHED_STAGE_B_BEAT_EVIDENCE; MADMOM_NOT_PROMOTED_TO_BEAT_PRODUCT_TRUTH",
        },
        "tracks": sanitized_tracks,
        "near_miss_replay": replays,
        "classification_counts": {
            "pairs_total": len(replays),
            "pairs_with_unknown_remaining": sum(1 for row in replays if row["unknown_evidence_remaining"]),
            "pairs_with_measured_incompatibility_remaining": sum(1 for row in replays if row["measured_incompatibilities_remaining"]),
            "strict_full_dj_eligible": sum(1 for row in replays if row["current_strict_r2_verdict_after_recovery"] == "FULL_DJ_ELIGIBLE"),
            "diagnostic_eligible": sum(1 for row in replays if row["confidence_ledger_diagnostic"]["eligible"]),
        },
        "explicit_non_actions": [
            "NO_WHOLE_CORPUS_RERUN",
            "NO_RENDERING",
            "NO_SIGNALSMITH",
            "NO_RUBBER_BAND",
            "NO_OWNER_LISTENING_PACK",
            "NO_TRACK_NAME_WEB_RESEARCH",
            "NO_P1_WORK",
        ],
    }
    Path(args.evidence_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.evidence_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"RESULT={result}")
    print(f"SUBSET_TRACKS={subset['unique_track_count']} PAIRS={len(replays)}")
    return 0 if result != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
