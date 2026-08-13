"""Probe an isolated All-In-One runtime without modifying third-party source.

This script is intentionally generic. It records import/model/checkpoint/synthetic
gates and fails closed: synthetic inference is unreachable until strict checkpoint
loading has succeeded. It never accepts private audio.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path


LEGACY_SYMBOLS = (
    "natten1dqkrpb",
    "natten1dav",
    "natten2dqkrpb",
    "natten2dav",
)
PR37_SYMBOLS = ("na1d_qk", "na1d_av", "na2d_qk", "na2d_av")
OBSERVATION_SYMBOLS = LEGACY_SYMBOLS + PR37_SYMBOLS + (
    "na1d",
    "na2d",
    "neighborhood_attention_generic",
)


def git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def failure(exc: BaseException) -> dict[str, str]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback_tail": "\n".join(traceback.format_exc().splitlines()[-12:]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path-id", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--expected-natten", required=True)
    parser.add_argument("--checkpoint-cache")
    parser.add_argument("--run-synthetic", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output = Path(args.out).resolve()
    record: dict[str, object] = {
        "schema_version": 1,
        "path_id": args.path_id,
        "source_commit": git_head(source_root),
        "expected_source_commit": args.expected_source_commit,
        "source_clean": subprocess.run(
            ["git", "diff", "--quiet", "--ignore-space-at-eol", "HEAD", "--"],
            cwd=source_root,
            check=False,
        ).returncode == 0,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ladder": [],
        "private_audio_supported": False,
        "private_track_count": 0,
    }
    if record["source_commit"] != args.expected_source_commit:
        raise SystemExit("SOURCE_COMMIT_MISMATCH")

    import torch
    import natten
    from natten import functional as natten_functional

    record.update(
        {
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "natten": importlib.metadata.version("natten"),
            "natten_import_version": natten.__version__,
            "natten_expected": args.expected_natten,
            "observed_symbols": {
                name: hasattr(natten_functional, name) for name in OBSERVATION_SYMBOLS
            },
        }
    )
    if record["natten"] != args.expected_natten:
        raise SystemExit("NATTEN_VERSION_MISMATCH")
    record["ladder"].append("ENVIRONMENT_INSPECTED")

    try:
        import allin1

        record["allin1_module"] = str(Path(allin1.__file__).resolve())
        record["import_result"] = "PASS"
        record["ladder"].append("IMPORT_PASS")
    except Exception as exc:  # imported code is the probe target
        record["import_result"] = "FAIL"
        record["import_failure"] = failure(exc)
        record["model_construction_result"] = "NOT_REACHED_IMPORT_FAILED"
        record["checkpoint_load_result"] = "NOT_REACHED_IMPORT_FAILED"
        record["synthetic_inference_result"] = "NOT_REACHED_MODEL_LOAD_REQUIRED"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return 23

    from allin1.config import Config, HarmonixConfig
    from allin1.models.allinone import AllInOne

    try:
        model = AllInOne(Config(data=HarmonixConfig())).to("cuda")
        record["model_construction_result"] = "PASS"
        record["parameter_count"] = sum(p.numel() for p in model.parameters())
        record["ladder"].append("MODEL_CONSTRUCTION_PASS")
    except Exception as exc:
        record["model_construction_result"] = "FAIL"
        record["model_construction_failure"] = failure(exc)
        record["checkpoint_load_result"] = "NOT_REACHED_MODEL_CONSTRUCTION_FAILED"
        record["synthetic_inference_result"] = "NOT_REACHED_MODEL_LOAD_REQUIRED"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return 24

    if not args.checkpoint_cache:
        record["checkpoint_load_result"] = "NOT_REQUESTED"
        record["synthetic_inference_result"] = "NOT_REACHED_MODEL_LOAD_REQUIRED"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return 0

    from huggingface_hub import HfApi, hf_hub_download
    from allin1.models.loaders import NAME_TO_FILE, load_pretrained_model

    try:
        repo_revision = HfApi().model_info("taejunkim/allinone").sha
        start = time.perf_counter()
        model = load_pretrained_model(
            "harmonix-fold0", cache_dir=args.checkpoint_cache, device="cuda"
        )
        record["checkpoint_load_wall_sec"] = time.perf_counter() - start
        filename = NAME_TO_FILE["harmonix-fold0"]
        checkpoint_path = Path(
            hf_hub_download(
                repo_id="taejunkim/allinone",
                filename=filename,
                revision=repo_revision,
                cache_dir=args.checkpoint_cache,
            )
        )
        checkpoint = torch.load(checkpoint_path, map_location="cuda")
        strict_result = model.load_state_dict(checkpoint["state_dict"], strict=True)
        model_state = model.state_dict()
        shape_mismatches = [
            key
            for key, value in checkpoint["state_dict"].items()
            if key not in model_state or tuple(value.shape) != tuple(model_state[key].shape)
        ]
        record.update(
            {
                "checkpoint_source": "taejunkim/allinone",
                "checkpoint_revision": repo_revision,
                "checkpoint_filename": filename,
                "checkpoint_sha256": sha256_file(checkpoint_path),
                "checkpoint_bytes": checkpoint_path.stat().st_size,
                "checkpoint_load_result": "PASS",
                "strict_load": True,
                "missing_keys": list(strict_result.missing_keys),
                "unexpected_keys": list(strict_result.unexpected_keys),
                "shape_mismatches": shape_mismatches,
                "state_dict_key_sets_equal": set(checkpoint["state_dict"]) == set(model_state),
            }
        )
        record["ladder"].append("REAL_CHECKPOINT_STRICT_LOAD_PASS")
    except Exception as exc:
        record["checkpoint_load_result"] = "FAIL"
        record["checkpoint_load_failure"] = failure(exc)
        record["synthetic_inference_result"] = "NOT_REACHED_MODEL_LOAD_REQUIRED"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return 25

    if args.run_synthetic:
        values = torch.linspace(
            -1.0, 1.0, steps=1 * 4 * 128 * 81, dtype=torch.float32, device="cuda"
        )
        inputs = values.reshape(1, 4, 128, 81)

        def run_once():
            torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                result = model(inputs)
            torch.cuda.synchronize()
            tensors = {
                "logits_beat": result.logits_beat.detach().cpu(),
                "logits_downbeat": result.logits_downbeat.detach().cpu(),
                "logits_section": result.logits_section.detach().cpu(),
                "logits_function": result.logits_function.detach().cpu(),
                "embeddings": result.embeddings.detach().cpu(),
            }
            return time.perf_counter() - start, tensors

        first_sec, first = run_once()
        second_sec, second = run_once()
        record.update(
            {
                "synthetic_inference_result": "PASS",
                "synthetic_repeat_wall_sec": [first_sec, second_sec],
                "synthetic_output_shapes": {
                    key: list(value.shape) for key, value in first.items()
                },
                "synthetic_nan_count": sum(
                    torch.isnan(value).sum().item() for value in first.values()
                ),
                "synthetic_inf_count": sum(
                    torch.isinf(value).sum().item() for value in first.values()
                ),
                "deterministic_repeat_exact": all(
                    torch.equal(first[key], second[key]) for key in first
                ),
                "deterministic_repeat_max_abs_diff": max(
                    (first[key] - second[key]).abs().max().item() for key in first
                ),
            }
        )
        record["ladder"].append("SYNTHETIC_INFERENCE_PASS")
    else:
        record["synthetic_inference_result"] = "NOT_REQUESTED"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
