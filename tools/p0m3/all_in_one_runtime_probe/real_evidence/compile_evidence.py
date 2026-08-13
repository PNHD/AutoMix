"""Compile four-track All-In-One output and replay only the derived frontier."""
from __future__ import annotations

import argparse
import copy
import json
import statistics
from pathlib import Path

EXPECTED_TRACKS = ["RM010", "RM014", "RM041", "RM081"]


def nearest_median(values: list[float], references: list[float]) -> float | None:
    if not values or not references:
        return None
    return statistics.median(min(abs(value - ref) for ref in references) for value in values)


def boundary_report(run: dict, target_ms: float, role: str) -> dict:
    output = run["semantic_output"]
    segments = output["segments"]
    index = next(
        (i for i, seg in enumerate(segments)
         if seg["start_ms"] <= target_ms < seg["end_ms"]
         or (i == len(segments) - 1 and target_ms == seg["end_ms"])),
        None,
    )
    if index is None:
        raise ValueError("BOUNDARY_OUTSIDE_ALL_IN_ONE_SEGMENTS")
    segment = segments[index]
    boundaries = sorted({value for seg in segments for value in (seg["start_ms"], seg["end_ms"])})
    nearest = min(boundaries, key=lambda value: abs(value - target_ms))
    distance_ms = abs(nearest - target_ms)
    beats = output["beats_ms"]
    beat_interval = statistics.median(b - a for a, b in zip(beats, beats[1:])) if len(beats) > 1 else None
    meter = output["meter_evidence"]["maximum_beat_position"]
    return {
        "role": role,
        "target_t_ms": target_ms,
        "functional_section_containing_boundary": [segment["start_ms"], segment["end_ms"]],
        "functional_label": segment["label"],
        "previous_functional_label": segments[index - 1]["label"] if index > 0 else None,
        "next_functional_label": segments[index + 1]["label"] if index + 1 < len(segments) else None,
        "nearest_functional_section_boundary_ms": nearest,
        "boundary_distance_ms": round(distance_ms, 3),
        "boundary_distance_beats": round(distance_ms / beat_interval, 3) if beat_interval else None,
        "boundary_distance_bars": round(distance_ms / (beat_interval * meter), 3) if beat_interval and meter else None,
        "meter_used_for_bar_distance": meter,
        "analyzer_source": "ALL_IN_ONE_CANONICAL_PUBLIC_AUDIO_PIPELINE",
        "evidence_class": "BENCHMARK_MODEL_OUTPUT_UNCALIBRATED",
        "functional_label_from_actual_output": True,
        "phrase_claimed": False,
        "outro_fabricated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontier", required=True)
    parser.add_argument("--smoke", required=True)
    parser.add_argument("--expanded", required=True)
    parser.add_argument("--accepted-evidence", required=True)
    parser.add_argument("--evidence-out", required=True)
    parser.add_argument("--replay-out", required=True)
    args = parser.parse_args()

    frontier = json.loads(Path(args.frontier).read_text(encoding="utf-8"))
    smoke = json.loads(Path(args.smoke).read_text(encoding="utf-8"))
    expanded = json.loads(Path(args.expanded).read_text(encoding="utf-8"))
    accepted = json.loads(Path(args.accepted_evidence).read_text(encoding="utf-8"))
    runs = smoke["runs"] + expanded["runs"]
    if [(row["opaque_id"], row["execution_order"]) for row in runs] != [
        ("RM014", 1), ("RM014", 2), ("RM010", 3), ("RM041", 4), ("RM081", 5)
    ]:
        raise ValueError("PRIVATE_EXECUTION_ORDER_MISMATCH")
    if not all(row["execution_result"] == "PASS" and row["output_schema_valid"] for row in runs):
        raise ValueError("REAL_PIPELINE_RUN_FAILED")

    rm014_a, rm014_b = runs[:2]
    exact_fields = ["bpm", "beats_ms", "downbeats_ms", "beat_positions", "segments"]
    repeat_equal = all(
        rm014_a["semantic_output"][field] == rm014_b["semantic_output"][field]
        for field in exact_fields
    )
    if not repeat_equal:
        raise ValueError("RM014_DETERMINISTIC_REPEAT_FAILED")

    first_runs = {row["opaque_id"]: row for row in runs if row["run_index"] == 1}
    accepted_pairs = {
        (row["category"], row["outgoing_opaque_id"], row["incoming_opaque_id"]): row
        for row in accepted["near_miss_replay"]
    }
    track_boundaries: dict[str, list[dict]] = {opaque_id: [] for opaque_id in EXPECTED_TRACKS}
    replays = []
    for pair in frontier["derived_pairs"]:
        key = (pair["category"], pair["outgoing_opaque_id"], pair["incoming_opaque_id"])
        baseline = accepted_pairs[key]
        outgoing = pair["outgoing_opaque_id"]
        incoming = pair["incoming_opaque_id"]
        out_boundary = boundary_report(first_runs[outgoing], baseline["outgoing_boundary"]["target_t_ms"], "outgoing_exit")
        in_boundary = boundary_report(first_runs[incoming], baseline["incoming_boundary"]["target_t_ms"], "incoming_entry")
        track_boundaries[outgoing].append(out_boundary)
        track_boundaries[incoming].append(in_boundary)
        is_candidate = baseline["current_strict_r2_verdict_after_recovery"] == "FULL_DJ_ELIGIBLE"
        replays.append({
            "category": pair["category"],
            "outgoing_opaque_id": outgoing,
            "incoming_opaque_id": incoming,
            "pre_all_in_one_failed_gates": baseline["current_strict_r2_failed_gates_after_recovery"],
            "new_all_in_one_evidence": {
                "outgoing_boundary": out_boundary,
                "incoming_boundary": in_boundary,
                "outgoing_downbeat_evidence": "SEE_FOUR_TRACK_EVIDENCE",
                "incoming_downbeat_evidence": "SEE_FOUR_TRACK_EVIDENCE",
                "evidence_class": "BENCHMARK_MODEL_OUTPUT_UNCALIBRATED",
            },
            "downbeat_status_before": baseline["confidence_ledger"]["downbeat_confidence_source"]["status"],
            "downbeat_status_after": "STRICT_R2_UNCHANGED_DIAGNOSTIC_ONLY",
            "structure_status_before": baseline["confidence_ledger"]["structure_confidence_source"]["status"],
            "structure_status_after": "STRICT_R2_UNCHANGED_FUNCTIONAL_OUTPUT_DIAGNOSTIC_ONLY",
            "harmonic_status": "UNCHANGED",
            "genre_style_status": "UNCHANGED",
            "texture_status": "UNCHANGED",
            "canonical_analysis_confidence_behavior": "UNCHANGED",
            "strict_existing_r2_verdict": baseline["current_strict_r2_verdict_after_recovery"],
            "confidence_ledger_diagnostic_verdict": baseline["confidence_ledger_diagnostic_verdict"],
            "exact_remaining_blockers": baseline["current_strict_r2_failed_gates_after_recovery"],
            "strict_reason_codes_unchanged": baseline["current_strict_r2_reason_codes_after_recovery"],
            "real_render_candidate": is_candidate,
        })

    tracks = {}
    for opaque_id in EXPECTED_TRACKS:
        run = first_runs[opaque_id]
        prior = accepted["tracks"][opaque_id]["downbeat"]
        allin1_downbeats = run["semantic_output"]["downbeats_ms"]
        prior_downbeats = [float(value) for value in prior["downbeats_ms"]]
        median_error = nearest_median(allin1_downbeats, prior_downbeats)
        if median_error is not None and median_error > 250.0:
            comparison = "CONFLICT"
        elif median_error is not None and median_error <= 100.0:
            comparison = "AGREEMENT_DIAGNOSTIC"
        else:
            comparison = "STILL_UNKNOWN"
        tracks[opaque_id] = {
            "execution_result": run["execution_result"],
            "public_api_total_wall_sec": run["public_api_total_wall_sec"],
            "inference_wall_sec": run["inference_wall_sec"],
            "output_schema_valid": run["output_schema_valid"],
            "bpm": run["semantic_output"]["bpm"],
            "beats_ms": run["semantic_output"]["beats_ms"],
            "downbeats_ms": allin1_downbeats,
            "beat_positions": run["semantic_output"]["beat_positions"],
            "meter_evidence": run["semantic_output"]["meter_evidence"],
            "segments": run["semantic_output"]["segments"],
            "relevant_boundaries": track_boundaries[opaque_id],
            "downbeat_comparison": {
                "prior_benchmark_source": prior["source"],
                "prior_status": prior["status"],
                "all_in_one_vs_prior_median_nearest_error_ms": round(median_error, 3) if median_error is not None else None,
                "diagnostic_comparison": comparison,
                "strict_r2_status": "UNCHANGED",
            },
            "functional_label_source": run["semantic_output"]["functional_label_source"],
            "evidence_class": run["evidence_class"],
            "calibrated_confidence_claimed": False,
            "phrase_claimed": False,
            "nan_count": run["semantic_output"]["nan_count"],
            "inf_count": run["semantic_output"]["inf_count"],
        }

    checkpoint = rm014_a["checkpoint"]
    candidate_count = sum(1 for row in replays if row["real_render_candidate"])
    result = (
        "REAL_RENDER_CANDIDATE_RECOVERED_EXISTING_R2"
        if candidate_count else "ALL_IN_ONE_REAL_PIPELINE_VALIDATED_RESIDUAL_BLOCKERS"
    )
    evidence = {
        "schema_version": 1,
        "task": "P0-M3-R3_ALL_IN_ONE_REAL_EVIDENCE",
        "result": result,
        "starting_head": frontier["starting_head"],
        "accepted_runtime_result": "ALL_IN_ONE_RUNTIME_RECOVERED_SYNTHETIC_ONLY",
        "accepted_analyzer_result_unchanged": "ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY",
        "quality_pass_claimed": False,
        "runtime": smoke["runtime"],
        "checkpoint": checkpoint,
        "public_audio_api": {
            "call": "allin1.analyze(path, model='harmonix-fold0', device='cuda', keep_byproducts=False, multiprocess=False)",
            "source_symbol": "src/allin1/analyze.py::analyze",
            "real_audio_loading": True,
            "demucs_preprocessing": True,
            "spectrogram_preprocessing": True,
            "model_inference": True,
            "direct_feature_tensor_test_path": False,
        },
        "execution_order": [{"order": row["execution_order"], "opaque_id": row["opaque_id"], "run_index": row["run_index"]} for row in runs],
        "rm014_repeat": {
            "exact_fields_compared": exact_fields,
            "deterministic_repeat_exact": repeat_equal,
            "first_inference_wall_sec": rm014_a["inference_wall_sec"],
            "second_inference_wall_sec": rm014_b["inference_wall_sec"],
        },
        "intervening_failures_preserved": [
            {
                "reason_code": "FFPROBE_NOT_EXECUTABLE_IN_ISOLATED_ENVIRONMENT",
                "class": "ENVIRONMENT",
                "private_audio_decoded": False,
            },
            {
                "reason_code": "WINDOWS_TO_WSL_FFMPEG_BRIDGE_DECODE_FAILED",
                "class": "DISCARDED_ENVIRONMENT_BRIDGE",
                "accepted_as_analyzer_evidence": False,
            },
            {
                "reason_code": "OFFLINE_CHECKPOINT_CACHE_NOT_AVAILABLE_FOR_PUBLIC_LOADER",
                "class": "ENVIRONMENT",
                "inference_reached": False,
            },
            {
                "reason_code": "CHECKPOINT_SNAPSHOT_REVISION_PARSER_USED_RESOLVED_BLOB_PATH",
                "class": "HARNESS_PROVENANCE_PARSER",
                "analyzer_output_rejected": True,
            },
            {
                "reason_code": "UNSEEDED_DEMUCS_REPEAT_NOT_DETERMINISTIC",
                "class": "DETERMINISTIC_RUNTIME_DIAGNOSIS",
                "analyzer_output_rejected": True,
            },
        ],
        "tracks": tracks,
        "evidence_class": "BENCHMARK_MODEL_OUTPUT_UNCALIBRATED",
        "all_in_one_confidence_calibrated": False,
        "beat_ownership": "BEATNET_UNCHANGED_ALL_IN_ONE_BEATS_DIAGNOSTIC_ONLY",
        "strict_r2_behavior": "UNCHANGED",
        "render_candidate_count": candidate_count,
        "license_boundary": {
            "all_in_one_code": "MIT",
            "checkpoint_repository_metadata": "SELF_DECLARED_MIT",
            "benchmark": "CLEAR_FOR_BENCHMARK",
            "production_evaluation": "UNKNOWN_NEEDS_LEGAL_REVIEW",
            "verdict_changed": False,
        },
        "scope_attestation": {
            "private_track_count": 4,
            "private_track_ids": EXPECTED_TRACKS,
            "tracks_outside_frontier": 0,
            "pairs_replayed": 3,
            "render_count": 0,
            "signalsmith_runs": 0,
            "rubber_band_runs": 0,
            "owner_listening_pack_created": False,
            "p1_production_work": False,
            "private_paths_emitted": False,
            "source_filenames_emitted": False,
            "audio_hashes_emitted": False,
        },
    }
    replay = {
        "schema_version": 1,
        "result": evidence["result"],
        "pair_count": len(replays),
        "pairs": replays,
        "harmonic_status_unchanged_for_all": True,
        "genre_style_status_unchanged_for_all": True,
        "texture_status_unchanged_for_all": True,
        "canonical_analysis_confidence_unchanged_for_all": True,
        "strict_r2_gates_unchanged": True,
        "render_candidate_count": candidate_count,
    }
    for path_value, payload in ((args.evidence_out, evidence), (args.replay_out, replay)):
        path = Path(path_value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
