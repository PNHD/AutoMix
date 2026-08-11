"""
Candidate runner: CUE-DETR (ETH-DISCO/cue-detr), pinned revision
d0462856ed2f59a1fb65267cfbe87340a65ad1bb, MIT-licensed code, MIT-licensed
checkpoint (per HF repository metadata tag on `disco-eth/cue-detr`, no
separate LICENSE file/text was found in the checkpoint repo itself, so the
metadata tag is the sole textual evidence -- recorded in
docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md).

The inference/preprocessing pipeline below is a direct, minimally-adapted
port of the pinned repository's own `cue_points.py` (MIT license).
**Third-party notice (PM REPAIR R3):** the full ETH DISCO MIT copyright and
permission notice covering this adaptation is reproduced in
`tools/p0m3/analyzer_shootout/THIRD_PARTY_NOTICES.md` under the heading
"ETH-DISCO/cue-detr -- candidates/run_cuedetr.py". Do not remove or relocate
that notice without keeping it mapped to this file.

Adaptation from upstream (both are non-algorithmic, MIT terms preserved):
  (a) processes one file at a time and returns our normalized
      AnalyzerResult instead of writing a `_cue_points.txt` file;
  (b) upstream's own file-extension convention (`*.mp3` glob) is exercised
      unmodified by transcoding our synthetic WAV fixtures to MP3 with
      ffmpeg -qscale:a 2 -- no algorithmic logic was changed.
No GPL/AGPL source was consulted or copied for this runner.

**PM REPAIR R4 (transitive asset audit):** the pinned upstream script loads
`DetrForObjectDetection.from_pretrained('disco-eth/cue-detr')` with the
library default `use_pretrained_backbone=True`, which triggers an
additional ~98 MB download of `timm/resnet50.a1_in1k` (ImageNet-pretrained
ResNet-50 backbone weights) purely to initialize the backbone BEFORE the
checkpoint's own state_dict is loaded on top and overwrites every backbone
parameter. This was verified empirically: loading with
`use_pretrained_backbone=False` (skips the timm download entirely) vs.
`use_pretrained_backbone=True` produces BIT-IDENTICAL inference output
(detection scores and box positions compared exactly equal, max score
diff = 0.0) on the same input, because `disco-eth/cue-detr` already
checkpoints a full state_dict including a fine-tuned backbone. This
runner therefore uses `use_pretrained_backbone=False` and no longer
downloads or depends on `timm/resnet50.a1_in1k` at all. Machine-readable
proof of this claim (PM REVIEW #2 R12): `results/cuedetr_backbone_equivalence.json`,
produced by `generate_backbone_equivalence_evidence()` below. See
`docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` Sec 1.1 for the full
license audit of the now-removed asset.

CUE-DETR was trained on EDM tracks with real spectral/timbral content and
manually-annotated expert cue points (EDM-CUE). Our fixtures are simple
synthetic click/tone/noise-burst material with NO authored cue regions, so
per Issue #5 Task D these results are SMOKE/REGRESSION evidence only, not a
quality measurement of CUE-DETR's real-world cue-point accuracy.

--- PM REVIEW #2 R8: canonical correctness is FRESH-PER-CALL, always ---
`run()` below constructs a brand-new DetrForObjectDetection/DetrImageProcessor
pair on every call and never reuses one across fixtures, for the same
correctness-isolation reason documented in candidates/run_beatnet.py. A
same-fixture fresh-vs-warm equivalence test
(results/warm_cold_equivalence.json) independently verified CUE-DETR's
eval-mode forward pass IS output-identical whether the model object is
freshly constructed or reused (expected for a dropout-disabled,
batchnorm-frozen `model.eval()` PyTorch module with no persistent hidden
state) -- but `run()` still always constructs fresh, both for methodological
uniformity with BeatNet and because per-call construction cost here (~1-2s)
is cheap relative to inference. Warm-reuse timing is measured only by the
separate `eval/run_runtime_profile.py`.

--- PM REVIEW #2 R9: non-overlapping timing fields ---
`model_load_wall_sec` covers `.from_pretrained(...)` calls only;
`inference_wall_sec`'s timer starts strictly after those calls return;
`total_call_wall_sec` equals their sum exactly. `asset_fetch_wall_sec` is
always None: the checkpoint is loaded from Hugging Face's local disk cache
(already downloaded in an earlier pass), and no separate network-vs-disk
instrumentation exists inside a single `from_pretrained()` call.

--- PM REVIEW #2 R10: filtered, not clamped ---
Raw predictions outside `[0, track_duration_ms]` are FILTERED OUT of the
validated `cue_points_ms`/`cue_score` arrays (removed entirely, never
clamped into range). `raw_cue_points_ms`/`raw_cue_score` preserve every
raw prediction and its score, in parallel, unfiltered.
"""
from __future__ import annotations

import json
import os
import sys
import time
import tracemalloc

import numpy as np
import torch
import librosa
from PIL import Image
from matplotlib import cm
from scipy.signal import find_peaks
from transformers import DetrImageProcessor, DetrForObjectDetection

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.schema import AnalyzerResult  # noqa: E402
from common.runtime import process_peak_rss_mb  # noqa: E402

OVERLAP = 0.75
W_BBOX = 21
W_WIN = 355
PADDING = 266

_ASSET_SIZE_CACHE: dict[str, tuple] = {}


def _measure_asset_sizes() -> tuple[float | None, float | None]:
    if "sizes" in _ASSET_SIZE_CACHE:
        return _ASSET_SIZE_CACHE["sizes"]
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        sizes = {repo.repo_id: round(repo.size_on_disk / (1024 * 1024), 2) for repo in cache.repos}
        checkpoint_mb = sizes.get("disco-eth/cue-detr")
        processor_mb = sizes.get("facebook/detr-resnet-50")
        if checkpoint_mb is None:
            result = (None, None)
        else:
            result = (checkpoint_mb, round(checkpoint_mb + (processor_mb or 0.0), 2))
    except Exception:
        result = (None, None)
    _ASSET_SIZE_CACHE["sizes"] = result
    return result


def construct_model(checkpoint: str = "disco-eth/cue-detr"):
    """Constructs and returns a brand-new (processor, model, device) tuple.
    Standalone so both canonical run() (always fresh) and the separate,
    non-canonical eval/run_runtime_profile.py (deliberately reuses the
    returned model across fixtures) share one real construction path."""
    processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # PM REPAIR R4: use_pretrained_backbone=False -- proven bit-identical
    # output vs. the upstream default; see generate_backbone_equivalence_evidence().
    model = DetrForObjectDetection.from_pretrained(checkpoint, use_pretrained_backbone=False)
    model.to(device)
    model.eval()
    return processor, model, device


def _mel_image(audio_path: str):
    y, sr = librosa.load(audio_path)  # standard librosa default sr=22050
    track_duration_ms = (len(y) / sr) * 1000.0
    M = librosa.feature.melspectrogram(y=y, sr=22050, n_fft=2048)
    M_db = librosa.power_to_db(M, ref=np.max)
    arr = M_db[::-1]
    sm = cm.ScalarMappable(cmap="viridis")
    sm.set_clim(arr.min(), arr.max())
    rgba = sm.to_rgba(arr, bytes=True)
    rgb_shape = (rgba.shape[1], rgba.shape[0])
    rgba = np.require(rgba, requirements="C")
    im = Image.frombuffer("RGBA", rgb_shape, rgba, "raw", "RGBA", 0, 1)
    image = np.array(im)[:, :, :3]
    return image, track_duration_ms


def _windows(image):
    image_w = image.shape[1] + PADDING
    n_windows = int(np.floor(image_w / (W_WIN * (1 - OVERLAP))))
    images, borders = [], []
    for i in range(n_windows):
        l = int(np.floor(i * W_WIN * (1 - OVERLAP))) - PADDING
        r = l + W_WIN
        borders.append(l)
        if l < 0:
            segment = image[:, :r]
            pad = -l
            segment = np.pad(segment, ((0, 0), (pad, 0), (0, 0)), mode="linear_ramp")
        elif r > image.shape[1]:
            segment = image[:, l:]
            pad = r - l - segment.shape[1]
            segment = np.pad(segment, ((0, 0), (0, pad), (0, 0)), mode="linear_ramp")
        else:
            segment = image[:, l:r]
        images.append(segment)
    return images, borders


def raw_predict(processor, model, device, audio_path: str, sensitivity: float = 0.9, radius_bars: int = 16):
    """Returns (raw_cue_times_ms, raw_scores, track_duration_ms) -- the raw,
    unfiltered model output, plus timing is left to the caller."""
    image, track_duration_ms = _mel_image(audio_path)
    images, borders = _windows(image)

    encoding = processor.preprocess(images, do_resize=False, return_tensors="pt")
    pixel_values = encoding["pixel_values"].to(device)
    with torch.no_grad():
        outputs = model(pixel_values)

    to_pixel = [(128, 355)] * pixel_values.shape[0]
    predictions = processor.post_process_object_detection(outputs, 0, to_pixel)

    scores, positions = [], []
    for p, l in zip(predictions, borders):
        scores.extend(p["scores"].tolist())
        pos = (p["boxes"][:, 0] + p["boxes"][:, 2]) // 2 + l
        positions.extend(pos.long().tolist())

    if not positions:
        return [], [], track_duration_ms

    scale = lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)) if np.max(x) != np.min(x) else np.zeros_like(x)
    positions, scores = zip(*sorted(zip(positions, scale(np.asarray(scores)))))
    peak_idx, _ = find_peaks(scores, height=sensitivity, distance=radius_bars)
    cue_positions = [positions[idx] for idx in peak_idx]
    cue_scores = [float(scores[idx]) for idx in peak_idx]
    raw_cue_times_ms = [round(float(t) * 1000, 1) for t in librosa.frames_to_time(cue_positions)]
    return raw_cue_times_ms, cue_scores, track_duration_ms


def run_with_model(processor, model, device, fixture_id: str, audio_path: str,
                    estimator_lifecycle: str = "FRESH_PER_CALL",
                    model_load_wall_sec: float | None = None) -> AnalyzerResult:
    checkpoint_mb, total_mb = _measure_asset_sizes()
    result = AnalyzerResult(
        candidate_id="cue_detr",
        candidate_kind="ML_MODEL",
        fixture_id=fixture_id,
        run_state="OK",
        device=device,
        checkpoint_size_mb=checkpoint_mb,
        total_model_asset_footprint_mb=total_mb,
        estimator_lifecycle=estimator_lifecycle,
        notes="Direct port of upstream cue_points.py (MIT; see THIRD_PARTY_NOTICES.md). SMOKE/REGRESSION "
              "evidence only on synthetic fixtures -- no authored cue-point ground truth exists for these "
              "fixtures (Issue #5 Task D). use_pretrained_backbone=False (PM REPAIR R4): timm backbone "
              "download removed, proven bit-identical output (results/cuedetr_backbone_equivalence.json).",
    )
    result.model_load_wall_sec = model_load_wall_sec
    tracemalloc.start()
    t_infer_start = time.perf_counter()
    try:
        raw_times_ms, raw_scores, track_duration_ms = raw_predict(processor, model, device, audio_path)

        # PM REVIEW #2 R10: FILTER (remove), do not clamp. Preserve raw
        # timestamps AND raw scores in parallel for full auditability.
        validated_ms, validated_scores, invalid_ms = [], [], []
        for t, s in zip(raw_times_ms, raw_scores):
            if 0.0 <= t <= track_duration_ms:
                validated_ms.append(t)
                validated_scores.append(s)
            else:
                invalid_ms.append(t)

        result.raw_cue_points_ms = raw_times_ms
        result.raw_cue_score = raw_scores
        result.cue_points_ms = validated_ms
        result.n_invalid_cue_predictions = len(invalid_ms)
        result.invalid_cue_points_raw_ms = invalid_ms
        result.cue_score = validated_scores
        result.cue_score_kind = "MINMAX_NORMALIZED_DETR_DETECTION_SCORE"
        result.cue_confidence = None  # never fabricated; no calibrated confidence exists here
    except Exception as exc:
        result.run_state = "FAILED"
        result.error = f"{type(exc).__name__}: {exc}"

    t_infer_end = time.perf_counter()
    _, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_mb, mem_method = process_peak_rss_mb()
    result.inference_wall_sec = round(t_infer_end - t_infer_start, 4)
    result.asset_fetch_wall_sec = None
    result.total_call_wall_sec = round((result.model_load_wall_sec or 0.0) + result.inference_wall_sec, 4)
    result.process_peak_rss_mb = rss_mb
    result.python_tracemalloc_peak_mb = round(py_peak / (1024 * 1024), 2)
    result.memory_measurement_method = mem_method
    return result


def run(fixture_id: str, audio_path: str) -> AnalyzerResult:
    """Canonical correctness entry point (PM REVIEW #2 R8): constructs a
    brand-new processor/model every call. This is the ONLY function
    eval/run_shootout.py calls to produce all_raw.json/metrics.json rows."""
    t_load_start = time.perf_counter()
    try:
        processor, model, device = construct_model()
    except Exception as exc:
        result = AnalyzerResult(
            candidate_id="cue_detr", candidate_kind="ML_MODEL", fixture_id=fixture_id,
            run_state="FAILED", error=f"{type(exc).__name__}: {exc}",
            estimator_lifecycle="FRESH_PER_CALL",
        )
        result.model_load_wall_sec = round(time.perf_counter() - t_load_start, 4)
        return result
    model_load_wall = time.perf_counter() - t_load_start
    return run_with_model(processor, model, device, fixture_id, audio_path,
                           estimator_lifecycle="FRESH_PER_CALL",
                           model_load_wall_sec=round(model_load_wall, 4))


def generate_backbone_equivalence_evidence(audio_path: str, fixture_id: str, out_path: str) -> dict:
    """PM REVIEW #2 R12: persists machine-readable evidence for the R4
    use_pretrained_backbone=False bit-identical claim, comparing
    use_pretrained_backbone=True (upstream default) vs False (this
    runner's choice) on the SAME input file with the SAME dependency
    versions in this process. Writes and returns the evidence dict.
    Does not download/commit any model weights beyond what the harness
    already required for candidate execution (checkpoint stays in the
    local HF cache, never committed to git)."""
    import transformers
    results = {}
    for use_pretrained in (True, False):
        processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = DetrForObjectDetection.from_pretrained("disco-eth/cue-detr", use_pretrained_backbone=use_pretrained)
        model.to(device)
        model.eval()
        raw_times_ms, raw_scores, duration_ms = raw_predict(processor, model, device, audio_path)
        results[use_pretrained] = {"raw_cue_points_ms": raw_times_ms, "raw_cue_score": raw_scores}

    scores_true = results[True]["raw_cue_score"]
    scores_false = results[False]["raw_cue_score"]
    positions_true = results[True]["raw_cue_points_ms"]
    positions_false = results[False]["raw_cue_points_ms"]
    scores_equal = scores_true == scores_false
    positions_equal = positions_true == positions_false
    max_score_diff = max((abs(a - b) for a, b in zip(scores_true, scores_false)), default=0.0)

    evidence = {
        "claim": "use_pretrained_backbone=False produces bit-identical CUE-DETR output vs. the "
                 "upstream-default use_pretrained_backbone=True, because disco-eth/cue-detr's checkpoint "
                 "state_dict fully overwrites the backbone regardless of its initialization.",
        "checkpoint": "disco-eth/cue-detr",
        "processor_config": "facebook/detr-resnet-50",
        "compared_fixture": fixture_id,
        "compared_input_path": os.path.basename(audio_path),
        "dependency_versions": {
            "torch": torch.__version__,
            "transformers": transformers.__version__,
        },
        "compared_fields": ["raw_cue_points_ms (box positions -> frame time)", "raw_cue_score (DETR detection score)"],
        "use_pretrained_backbone_True": results[True],
        "use_pretrained_backbone_False": results[False],
        "positions_equal": positions_equal,
        "scores_equal": scores_equal,
        "max_score_diff": max_score_diff,
        "verdict": "BIT_IDENTICAL" if (positions_equal and scores_equal) else "DIFFERS",
    }
    with open(out_path, "w") as fh:
        json.dump(evidence, fh, indent=2)
    return evidence
