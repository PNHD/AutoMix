"""
Candidate runner: CUE-DETR (ETH-DISCO/cue-detr), pinned revision
d0462856ed2f59a1fb65267cfbe87340a65ad1bb, MIT-licensed code, MIT-licensed
checkpoint (per HF repository metadata tag on `disco-eth/cue-detr`, no
separate LICENSE file/text was found in the checkpoint repo itself, so the
metadata tag is the sole textual evidence -- recorded in
docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md).

The inference/preprocessing pipeline below is a direct, minimally-adapted
port of the pinned repository's own `cue_points.py` (MIT license,
attribution preserved here), restructured to:
  (a) process one file at a time and return our normalized AnalyzerResult
      instead of writing a `_cue_points.txt` file, and
  (b) accept any audio format librosa can load (the upstream script only
      globs for `.mp3`; our fixtures were losslessly-generated as WAV and
      transcoded to MP3 with ffmpeg -qscale:a 2 purely so the SAME upstream
      file-extension convention could be exercised unmodified -- no
      algorithmic logic was changed).
No GPL/AGPL source was consulted or copied for this runner.

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

OVERLAP = 0.75
W_BBOX = 21
W_WIN = 355
PADDING = 266

_MODEL = None
_PROCESSOR = None
_DEVICE = None


def _load_model(checkpoint: str = "disco-eth/cue-detr"):
    global _MODEL, _PROCESSOR, _DEVICE
    if _MODEL is None:
        _PROCESSOR = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
        _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        _MODEL = DetrForObjectDetection.from_pretrained(checkpoint)
        _MODEL.to(_DEVICE)
        _MODEL.eval()
    return _MODEL, _PROCESSOR, _DEVICE


def run(fixture_id: str, audio_path: str, sensitivity: float = 0.9, radius_bars: int = 16) -> AnalyzerResult:
    result = AnalyzerResult(
        candidate_id="cue_detr",
        candidate_kind="ML_MODEL",
        fixture_id=fixture_id,
        run_state="OK",
        notes="Direct port of upstream cue_points.py (MIT). SMOKE/REGRESSION evidence only on "
              "synthetic fixtures -- no authored cue-point ground truth exists for these fixtures "
              "(Issue #5 Task D). facebook/detr-resnet-50 image-processor config (Apache-2.0, Meta) "
              "downloaded alongside the disco-eth/cue-detr checkpoint (MIT per HF tag).",
    )
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        model, image_processor, device = _load_model()
        result.device = device

        y, sr = librosa.load(audio_path)  # standard librosa default sr=22050
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
            cue_times_sec = librosa.frames_to_time(cue_positions)
        else:
            cue_times_sec, cue_scores = [], []

        result.cue_points_ms = [round(float(t) * 1000, 1) for t in cue_times_sec]
        result.cue_confidence = cue_scores
        result.model_checkpoint_size_mb = None  # HF cache size not measured per-call
    except Exception as exc:
        result.run_state = "FAILED"
        result.error = f"{type(exc).__name__}: {exc}"

    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.wall_time_sec = round(wall, 4)
    result.is_cold_run = True
    result.peak_memory_mb = round(peak / (1024 * 1024), 2)
    return result
