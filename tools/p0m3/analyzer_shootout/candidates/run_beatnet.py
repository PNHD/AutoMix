"""
Candidate runner: BeatNet (mjhydri/BeatNet), pinned revision
81cedd4beeb7235262db80969a0c9ce9a48a0ed4, offline mode + DBN
(non-causal) inference -- the mode intended for whole-file analysis.

Output format per upstream BeatNet.process() docstring: numpy_array
(num_beats, 2), column 0 = beat time in seconds, column 1 = beat position
within the bar as chosen by madmom's DBNDownBeatTrackingProcessor
(beats_per_bar candidates [2,3,4]); position == 1 marks a downbeat. This
also makes BeatNet's offline path meter-adaptive (2/3/4 beats-per-bar),
which is exercised by fixture FIX-E (3/4 waltz).

--- Windows/Python-3.10 compatibility shims (documented, not silent) ---
Installed via: pip install git+https://github.com/mjhydri/BeatNet.git@81cedd4beeb7235262db80969a0c9ce9a48a0ed4
plus: pip install "git+https://github.com/CPJKU/madmom" (via PyPI madmom==0.16.1,
built from source with MSVC Build Tools 2022 present on this machine) and
torch (CPU wheel) and pyaudio.

madmom 0.16.1 (last real PyPI release, 2018-era code) does not import
cleanly on Python 3.10 / numpy>=1.24 because it references two names the
standard library / numpy removed after that code was written:
  1. `from collections import MutableSequence` -- moved to
     collections.abc in Python 3.3, and the collections-level alias was
     removed in Python 3.10 (madmom/processors.py).
  2. `np.float` / `np.int` / etc -- deprecated aliases for Python builtins,
     removed in numpy 1.24 (madmom/io/__init__.py and others).
These are restored here as harness-local compatibility aliases BEFORE
importing madmom/BeatNet. This does not modify madmom's own source or
algorithmic behavior; it only re-exposes stdlib/numpy names that CPython
and numpy themselves deprecated-then-removed after madmom's last release,
exactly as numpy's own deprecation notice recommends. This is a real,
reproducible environment blocker for BeatNet on any current Python
(documented for the portability matrix, Issue #5 Task E), not something
papered over silently -- see docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md.
"""
from __future__ import annotations

import collections
import collections.abc
import os
import sys
import time
import tracemalloc

if not hasattr(collections, "MutableSequence"):
    collections.MutableSequence = collections.abc.MutableSequence
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable

import numpy as np  # noqa: E402

for _name, _val in (("float", float), ("int", int), ("complex", complex), ("bool", bool)):
    if not hasattr(np, _name):
        setattr(np, _name, _val)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.schema import AnalyzerResult  # noqa: E402


def run(fixture_id: str, wav_path: str, model: int = 1) -> AnalyzerResult:
    result = AnalyzerResult(
        candidate_id="beatnet",
        candidate_kind="ML_MODEL",
        fixture_id=fixture_id,
        run_state="OK",
        device="cpu",
        notes="Offline mode, DBN (non-causal) inference, pinned model checkpoint "
              f"model-{model}.pt (repo-bundled). beats_per_bar candidates=[2,3,4] "
              "(meter-adaptive).",
    )
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        from BeatNet.BeatNet import BeatNet
        estimator = BeatNet(model, mode="offline", inference_model="DBN", plot=[], thread=False, device="cpu")
        output = estimator.process(wav_path)
    except Exception as exc:
        result.run_state = "FAILED"
        result.error = f"{type(exc).__name__}: {exc}"
        result.wall_time_sec = time.perf_counter() - t0
        tracemalloc.stop()
        return result

    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    output = np.asarray(output)
    if output.ndim != 2 or output.shape[1] < 2:
        result.run_state = "FAILED"
        result.error = f"unexpected BeatNet output shape {output.shape}"
        result.wall_time_sec = wall
        return result

    beat_times_ms = (output[:, 0] * 1000.0).tolist()
    beat_positions = output[:, 1].astype(int).tolist()
    downbeat_times_ms = [t for t, p in zip(beat_times_ms, beat_positions) if p == 1]

    result.beat_timestamps_ms = [round(t, 1) for t in beat_times_ms]
    result.beat_position_in_bar = beat_positions
    result.downbeat_timestamps_ms = [round(t, 1) for t in downbeat_times_ms]
    inferred_meter = max(beat_positions) if beat_positions else None
    result.meter_numerator = inferred_meter
    result.meter_denominator = 4
    result.meter_confidence = None  # DBN does not expose a scalar meter-confidence via this API
    result.bpm = None  # BeatNet's offline/DBN path does not directly return a scalar BPM
    result.wall_time_sec = round(wall, 4)
    result.is_cold_run = True
    result.peak_memory_mb = round(peak / (1024 * 1024), 2)
    result.model_checkpoint_size_mb = None
    return result
