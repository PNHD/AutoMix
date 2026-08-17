"""P0-M3-R3 RM041<->RM014 evidence stability -- cross-seed All-In-One runner.

Runs the SAME canonical public ``allin1.analyze`` pipeline used by the
accepted P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE pass
(``tools/p0m3/all_in_one_runtime_probe/real_evidence/run_real_pipeline.py``),
for exactly one (opaque track id, deterministic seed) combination per
invocation. The deterministic seed itself is supplied to the interpreter
via the ``AUTOMIX_DETERMINISTIC_SEED`` environment variable consumed by
``deterministic_site/sitecustomize.py`` (same mechanism as the accepted
pass) -- this script only reads that value back to record it and to
cross-check it against the ``--expected-seed`` argument the driver passes,
so a seed mismatch fails loudly instead of silently analyzing the wrong
seed.

Private paths are read only from the existing approved local opaque
mapping and are never written to the output file. Only opaque RM ids,
numeric measurements, and non-private runtime/checkpoint identity fields
are emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path, PureWindowsPath

import allin1
import natten
import torch

OPAQUE_ID = re.compile(r"^RM\d{3}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_TRACK_IDS = {"RM041", "RM014"}
ALLOWED_SEEDS = {0, 1, 2, 3, 4}
CANONICAL_SOURCE_COMMIT = "18e78903c0365147a2c5d4e5e57ebf88cb7d800e"
NATTEN_SOURCE_COMMIT = "3b54c76185904f3cb59a49fff7bc044e4513d106"
CHECKPOINT_REVISION_ACCEPTED = "379e5fd010b3fdd0ee8381ff8cbcfa51d70b5c19"
CHECKPOINT_FILENAME = "harmonix-fold0-0vra4ys2.pth"
CHECKPOINT_SHA256_ACCEPTED = "0db596dfb0995f41d62f6267d76a9d54c046f1649bd35e1dbeca0c5f9a7b8acd"
FFMPEG_RELEASE_TAG = "autobuild-2026-08-12-13-15"
FFMPEG_ARCHIVE_SHA256 = "cf55934e9faa1969bff4c3fc1e1352707c9c9384e4d7986388830a8c8a726913"


def windows_to_wsl(value: str) -> Path:
    if re.match(r"^[A-Za-z]:[\\/]", value):
        path = PureWindowsPath(value)
        drive = path.drive.rstrip(":").lower()
        return Path("/mnt") / drive / Path(*path.parts[1:])
    return Path(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runtime_identity(expected_seed: int) -> dict:
    source_root = Path(allin1.__file__).resolve().parents[2]
    source_commit = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
    ).strip()
    diff = subprocess.run(
        ["git", "-C", str(source_root), "diff", "--ignore-space-at-eol", "--quiet"]
    )
    if source_commit != CANONICAL_SOURCE_COMMIT or diff.returncode != 0:
        raise ValueError("CANONICAL_SOURCE_PIN_OR_SEMANTIC_CLEANLINESS_FAILED")
    ffmpeg_line = subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]
    ffprobe_line = subprocess.check_output(["ffprobe", "-version"], text=True).splitlines()[0]
    observed = {
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "natten_version": natten.__version__,
        "natten_source_commit": NATTEN_SOURCE_COMMIT,
        "all_in_one_source_commit": source_commit,
        "source_semantic_diff_ignoring_eol_clean": True,
        "public_api": "allin1.analyze",
        "public_api_source": "src/allin1/analyze.py::analyze",
        "model_name": "harmonix-fold0",
        "deterministic_control": {
            "sitecustomize_rng_seed": os.environ.get("AUTOMIX_DETERMINISTIC_SEED"),
            "applies_to_demucs_subprocess": True,
            "upstream_source_modified": False,
        },
        "audio_decode_tools": {
            "ffmpeg_version_line": ffmpeg_line,
            "ffprobe_version_line": ffprobe_line,
            "distribution": "BtbN/FFmpeg-Builds_PINNED_LINUX64_GPL_ARCHIVE",
            "release_tag": os.environ.get("AUTOMIX_FFMPEG_RELEASE_TAG"),
            "archive_sha256": os.environ.get("AUTOMIX_FFMPEG_ARCHIVE_SHA256"),
            "environment_isolated": True,
            "system_install_changed": False,
        },
    }
    expected = {
        "python_version": "3.10.18",
        "torch_version": "2.0.0+cu118",
        "torch_cuda_build": "11.8",
        "cuda_available": True,
        "natten_version": "0.14.6",
    }
    for key, value in expected.items():
        if observed[key] != value:
            raise ValueError(f"RUNTIME_PIN_MISMATCH_{key.upper()}")
    if observed["audio_decode_tools"]["release_tag"] != FFMPEG_RELEASE_TAG:
        raise ValueError("FFMPEG_RELEASE_TAG_MISMATCH")
    if observed["audio_decode_tools"]["archive_sha256"] != FFMPEG_ARCHIVE_SHA256:
        raise ValueError("FFMPEG_ARCHIVE_HASH_MISMATCH")
    seed_env = observed["deterministic_control"]["sitecustomize_rng_seed"]
    if seed_env is None or int(seed_env) != expected_seed:
        raise ValueError("DETERMINISTIC_SEED_MISMATCH")
    return observed


def checkpoint_identity(path_value: str) -> dict:
    path = Path(path_value)
    resolved = path.resolve()
    revision = next((part for part in path.parts if HEX40.fullmatch(part)), None)
    if revision is None:
        revision = next((part for part in resolved.parts if HEX40.fullmatch(part)), None)
    return {
        "repository": "taejunkim/allinone",
        "filename": path.name,
        "loader_resolved_revision": revision,
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
        "loader_revision_argument": None,
    }


def finite_count(values) -> tuple[int, int]:
    nan = 0
    inf = 0
    for value in values:
        number = float(value)
        nan += int(math.isnan(number))
        inf += int(math.isinf(number))
    return nan, inf


def validate_result(result) -> tuple[dict, bool]:
    beats_ms = [round(float(value) * 1000.0, 3) for value in result.beats]
    downbeats_ms = [round(float(value) * 1000.0, 3) for value in result.downbeats]
    beat_positions = [int(value) for value in result.beat_positions]
    segments = [
        {"start_ms": round(float(seg.start) * 1000.0, 3),
         "end_ms": round(float(seg.end) * 1000.0, 3),
         "label": str(seg.label)}
        for seg in result.segments
    ]
    numeric = beats_ms + downbeats_ms + beat_positions
    numeric += [number for seg in segments for number in (seg["start_ms"], seg["end_ms"])]
    nan, inf = finite_count(numeric)
    schema_valid = bool(
        isinstance(result.bpm, (int, type(None)))
        and len(beats_ms) == len(beat_positions)
        and beats_ms == sorted(beats_ms)
        and downbeats_ms == sorted(downbeats_ms)
        and bool(segments)
        and all(seg["start_ms"] <= seg["end_ms"] and bool(seg["label"]) for seg in segments)
        and nan == 0 and inf == 0
    )
    return {
        "bpm": result.bpm,
        "beats_ms": beats_ms,
        "downbeats_ms": downbeats_ms,
        "beat_positions": beat_positions,
        "beat_count": len(beats_ms),
        "downbeat_count": len(downbeats_ms),
        "segments": segments,
        "functional_labels": [seg["label"] for seg in segments],
        "functional_label_source": "AnalysisResult.segments_FROM_ALL_IN_ONE_POSTPROCESSING",
        "phrase_claimed": False,
        "calibrated_confidence_claimed": False,
        "nan_count": nan,
        "inf_count": inf,
    }, schema_valid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--track-id", required=True, choices=sorted(ALLOWED_TRACK_IDS))
    parser.add_argument("--seed", type=int, required=True, choices=sorted(ALLOWED_SEEDS))
    parser.add_argument("--execution-order", type=int, required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.track_id not in ALLOWED_TRACK_IDS:
        raise ValueError("TRACK_OUTSIDE_FIXED_PAIR_SCOPE")
    if args.seed not in ALLOWED_SEEDS:
        raise ValueError("SEED_OUTSIDE_DECLARED_SET")

    runtime = runtime_identity(expected_seed=args.seed)

    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    if args.track_id not in mapping:
        raise ValueError("OPAQUE_ID_MISSING_FROM_APPROVED_MAPPING")
    source = windows_to_wsl(str(mapping[args.track_id]))
    if not source.is_file():
        raise ValueError("APPROVED_MAPPED_AUDIO_MISSING")

    scratch = Path(args.scratch)
    call_dir = scratch / f"{args.track_id}-seed{args.seed}"
    call_dir.mkdir(parents=True, exist_ok=True)

    analyze_module = importlib.import_module("allin1.analyze")
    loaders_module = importlib.import_module("allin1.models.loaders")
    original_inference = analyze_module.run_inference
    original_download = loaders_module.hf_hub_download
    inference_times = []
    checkpoint_records = []

    def timed_inference(*call_args, **call_kwargs):
        started = time.perf_counter()
        result = original_inference(*call_args, **call_kwargs)
        inference_times.append(time.perf_counter() - started)
        return result

    def captured_download(*call_args, **call_kwargs):
        path_value = original_download(*call_args, **call_kwargs)
        checkpoint_records.append(checkpoint_identity(path_value))
        return path_value

    analyze_module.run_inference = timed_inference
    loaders_module.hf_hub_download = captured_download
    started = time.perf_counter()
    row: dict
    try:
        result = allin1.analyze(
            source,
            model="harmonix-fold0",
            device="cuda",
            include_activations=False,
            include_embeddings=False,
            demix_dir=call_dir / "demix",
            spec_dir=call_dir / "spec",
            keep_byproducts=False,
            overwrite=True,
            multiprocess=False,
        )
        total_wall = time.perf_counter() - started
        semantic, schema_valid = validate_result(result)
        if len(inference_times) != 1 or len(checkpoint_records) != 1:
            raise ValueError("EXPECTED_ONE_INFERENCE_AND_ONE_CHECKPOINT_LOAD")
        checkpoint = checkpoint_records[0]
        if checkpoint["filename"] != CHECKPOINT_FILENAME:
            raise ValueError("CHECKPOINT_FILENAME_MISMATCH")
        if checkpoint["loader_resolved_revision"] != CHECKPOINT_REVISION_ACCEPTED:
            raise ValueError("CHECKPOINT_REVISION_MISMATCH")
        if checkpoint["sha256"] != CHECKPOINT_SHA256_ACCEPTED:
            raise ValueError("CHECKPOINT_HASH_MISMATCH")
        row = {
            "execution_order": args.execution_order,
            "opaque_id": args.track_id,
            "seed": args.seed,
            "execution_result": "PASS",
            "public_api_total_wall_sec": round(total_wall, 6),
            "inference_wall_sec": round(inference_times[0], 6),
            "output_schema_valid": schema_valid,
            "checkpoint": checkpoint,
            "evidence_class": "BENCHMARK_MODEL_OUTPUT_UNCALIBRATED",
            "semantic_output": semantic,
        }
    except Exception as exc:  # private message stays only in the redirected local log
        row = {
            "execution_order": args.execution_order,
            "opaque_id": args.track_id,
            "seed": args.seed,
            "execution_result": "FAIL",
            "failure_class": type(exc).__name__,
            "failure_reason_code": "ALL_IN_ONE_PUBLIC_AUDIO_PIPELINE_FAILED",
        }
    finally:
        analyze_module.run_inference = original_inference
        loaders_module.hf_hub_download = original_download

    payload = {
        "schema_version": 1,
        "runtime": runtime,
        "run": row,
        "private_paths_emitted": False,
        "source_filenames_emitted": False,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if row["execution_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
