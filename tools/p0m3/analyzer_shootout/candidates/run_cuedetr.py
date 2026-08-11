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
parameter. This was verified empirically this repair pass: loading with
`use_pretrained_backbone=False` (skips the timm download entirely, backbone
starts from the architecture only) vs. `use_pretrained_backbone=True`
(downloads+initializes the timm backbone first) produces BIT-IDENTICAL
inference output (detection scores and box positions compared exactly
equal, max score diff = 0.0) on the same input, because `disco-eth/cue-detr`
already checkpoints a full state_dict including a fine-tuned backbone. This
runner therefore uses `use_pretrained_backbone=False` and no longer
downloads or depends on `timm/resnet50.a1_in1k` at all. See
`docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` Sec 1 for the full
before/after asset audit including the now-removed timm asset's own
license (Apache-2.0), recorded for completeness even though it is no
longer part of this runner's dependency graph.

CUE-DETR was trained on EDM tracks with real spectral/timbral content and
manually-annotated expert cue points (EDM-CUE). Our fixtures are simple
synthetic click/tone/noise-burst material with NO authored cue regions, so
per Issue #5 Task D these results are SMOKE/REGRESSION evidence only, not a
quality measurement of CUE-DETR's real-world cue-point accuracy.
"""
from __future__ import annotations

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

# Module-level singleton cache -- PM REPAIR R1: a run is only ever "warm" if
# THIS exact object is reused, not merely because some other file/process
# happened to run fast. _CALL_COUNT distinguishes the first (cold) call in
# this process from every later (warm) one.
_MODEL = None
_PROCESSOR = None
_DEVICE = None
_CHECKPOINT_SIZE_MB = None
_TOTAL_ASSET_FOOTPRINT_MB = None
_CALL_COUNT = 0


def _dir_size_mb(path: str) -> float:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return round(total / (1024 * 1024), 2)


def _measure_asset_sizes():
    """Best-effort measurement of on-disk HF cache size for the two assets
    this runner actually requires post-R4 (checkpoint + tiny processor
    config). Returns (checkpoint_size_mb, total_footprint_mb), either None
    if the cache layout can't be located (never fabricated)."""
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        sizes = {}
        for repo in cache.repos:
            sizes[repo.repo_id] = round(repo.size_on_disk / (1024 * 1024), 2)
        checkpoint_mb = sizes.get("disco-eth/cue-detr")
        processor_mb = sizes.get("facebook/detr-resnet-50")
        if checkpoint_mb is None:
            return None, None
        total = checkpoint_mb + (processor_mb or 0.0)
        return checkpoint_mb, round(total, 2)
    except Exception:
        return None, None


def _load_model(checkpoint: str = "disco-eth/cue-detr") -> float:
    """Loads (once) and returns the wall-clock seconds spent doing so.
    Returns 0.0 on subsequent calls (nothing loaded, model already resident)."""
    global _MODEL, _PROCESSOR, _DEVICE, _CHECKPOINT_SIZE_MB, _TOTAL_ASSET_FOOTPRINT_MB
    if _MODEL is not None:
        return 0.0
    t0 = time.perf_counter()
    _PROCESSOR = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    # PM REPAIR R4: use_pretrained_backbone=False -- proven bit-identical
    # output vs. the upstream default (see module docstring); skips an
    # unnecessary ~98MB timm/resnet50.a1_in1k download entirely.
    _MODEL = DetrForObjectDetection.from_pretrained(checkpoint, use_pretrained_backbone=False)
    _MODEL.to(_DEVICE)
    _MODEL.eval()
    load_wall = time.perf_counter() - t0
    _CHECKPOINT_SIZE_MB, _TOTAL_ASSET_FOOTPRINT_MB = _measure_asset_sizes()
    return load_wall


def run(fixture_id: str, audio_path: str, sensitivity: float = 0.9, radius_bars: int = 16) -> AnalyzerResult:
    global _CALL_COUNT
    result = AnalyzerResult(
        candidate_id="cue_detr",
        candidate_kind="ML_MODEL",
        fixture_id=fixture_id,
        run_state="OK",
        notes="Direct port of upstream cue_points.py (MIT; see THIRD_PARTY_NOTICES.md). SMOKE/REGRESSION "
              "evidence only on synthetic fixtures -- no authored cue-point ground truth exists for these "
              "fixtures (Issue #5 Task D). use_pretrained_backbone=False (PM REPAIR R4): timm backbone "
              "download removed, proven bit-identical output vs. the upstream-default pretrained-backbone path.",
    )
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        was_first_call = _MODEL is None
        asset_fetch_wall = _load_model()
        model, image_processor, device = _MODEL, _PROCESSOR, _DEVICE
        result.device = device
        result.checkpoint_size_mb = _CHECKPOINT_SIZE_MB
        result.total_model_asset_footprint_mb = _TOTAL_ASSET_FOOTPRINT_MB
        _CALL_COUNT += 1
        result.run_phase = "COLD_MODEL_LOAD_INFERENCE" if was_first_call else "WARM_INFERENCE"
        if was_first_call:
            result.asset_fetch_wall_sec = round(asset_fetch_wall, 4)

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

        encoding = image_processor.preprocess(images, do_resize=False, return_tensors="pt")
        pixel_values = encoding["pixel_values"].to(device)
        with torch.no_grad():
            outputs = model(pixel_values)

        to_pixel = [(128, 355)] * pixel_values.shape[0]
        predictions = image_processor.post_process_object_detection(outputs, 0, to_pixel)

        scores, positions = [], []
        for p, l in zip(predictions, borders):
            scores.extend(p["scores"].tolist())
            pos = (p["boxes"][:, 0] + p["boxes"][:, 2]) // 2 + l
            positions.extend(pos.long().tolist())

        if positions:
            scale = lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)) if np.max(x) != np.min(x) else np.zeros_like(x)
            positions, scores = zip(*sorted(zip(positions, scale(np.asarray(scores)))))
            peak_idx, _ = find_peaks(scores, height=sensitivity, distance=radius_bars)
            cue_positions = [positions[idx] for idx in peak_idx]
            cue_scores = [float(scores[idx]) for idx in peak_idx]
            raw_cue_times_ms = [round(float(t) * 1000, 1) for t in librosa.frames_to_time(cue_positions)]
        else:
            raw_cue_times_ms, cue_scores = [], []

        # PM REPAIR R5/R10: preserve raw (possibly negative/out-of-range)
        # model output separately from the validated array; count/report
        # invalid predictions explicitly rather than silently clamping.
        validated, invalid = [], []
        validated_scores = []
        for t, s in zip(raw_cue_times_ms, cue_scores):
            if 0.0 <= t <= track_duration_ms:
                validated.append(t)
                validated_scores.append(s)
            else:
                invalid.append(t)

        result.raw_cue_points_ms = raw_cue_times_ms
        result.cue_points_ms = validated
        result.n_invalid_cue_predictions = len(invalid)
        result.invalid_cue_points_raw_ms = invalid
        # PM REPAIR R5/R9: these are min-max-normalized DETR detection scores
        # across candidate boxes for THIS track, not a calibrated musical-cue
        # confidence. Reported as cue_score/cue_score_kind; cue_confidence
        # stays None.
        result.cue_score = validated_scores
        result.cue_score_kind = "MINMAX_NORMALIZED_DETR_DETECTION_SCORE"
        result.cue_confidence = None
    except Exception as exc:
        result.run_state = "FAILED"
        result.error = f"{type(exc).__name__}: {exc}"

    wall = time.perf_counter() - t0
    _, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_mb, mem_method = process_peak_rss_mb()
    result.wall_time_sec = round(wall, 4)
    result.process_peak_rss_mb = rss_mb
    result.python_tracemalloc_peak_mb = round(py_peak / (1024 * 1024), 2)
    result.memory_measurement_method = mem_method
    return result
