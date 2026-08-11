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

--- PM REVIEW #2 R8: canonical correctness is FRESH-PER-CALL, always ---
`run()` below is the ONLY entry point used to produce canonical
all_raw.json/metrics.json rows. It constructs a brand-new BeatNet
estimator on every single call and never reuses one across fixtures, so
correctness fields (beat_timestamps_ms, beat_position_in_bar,
downbeat_timestamps_ms, meter) can never be contaminated by another
fixture's prior in-process state. This was made mandatory after PM REVIEW
#2 found that the PM REPAIR R1 pass's cross-fixture estimator caching
(then labeled "warm") measurably changed BeatNet's own output between
identical-methodology runs (see
docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md Sec 8 for the same-fixture
equivalence test that reproduces and quantifies this). Warm-resident
reuse is now measured ONLY by the separate, non-canonical
`eval/run_runtime_profile.py` script, whose output
(results/runtime_profile.json) is never merged into canonical results.

--- PM REVIEW #2 R9: non-overlapping timing fields ---
`model_load_wall_sec` covers construction only; `inference_wall_sec`'s
timer starts strictly after construction returns; `total_call_wall_sec`
is defined to equal their sum exactly (asserted by eval/verify_repair.py).
`asset_fetch_wall_sec` is always None here: BeatNet's checkpoints ship
inside the pip-installed package (no runtime network fetch occurs, and
none is separately instrumented even if pip itself fetched something at
install time, which is outside any single analyzer call's timing).
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
from common.runtime import process_peak_rss_mb  # noqa: E402

_CHECKPOINT_SIZES_MB: dict[int, float] = {}


def _checkpoint_size_mb(model: int) -> float | None:
    if model in _CHECKPOINT_SIZES_MB:
        return _CHECKPOINT_SIZES_MB[model]
    try:
        import BeatNet
        models_dir = os.path.join(os.path.dirname(BeatNet.__file__), "models")
        path = os.path.join(models_dir, f"model-{model}.pt")
        size = round(os.path.getsize(path) / (1024 * 1024), 3)
        _CHECKPOINT_SIZES_MB[model] = size
        return size
    except Exception:
        return None


def construct_estimator(model: int = 1, mode: str = "offline", inference_model: str = "DBN", device: str = "cpu"):
    """Constructs and returns a brand-new BeatNet estimator. Exposed as a
    standalone function so both canonical run() (always fresh) and the
    separate, non-canonical eval/run_runtime_profile.py (deliberately
    reuses the returned object across fixtures) share one real
    construction code path, without run() itself ever caching anything."""
    from BeatNet.BeatNet import BeatNet
    return BeatNet(model, mode=mode, inference_model=inference_model, plot=[], thread=False, device=device)


def run_with_estimator(estimator, fixture_id: str, wav_path: str, model: int = 1,
                        estimator_lifecycle: str = "FRESH_PER_CALL",
                        model_load_wall_sec: float | None = None) -> AnalyzerResult:
    """Runs inference with an already-constructed estimator and fills in an
    AnalyzerResult. `model_load_wall_sec` must be the caller-measured
    construction time for THIS call (0.0 if the estimator was reused and no
    construction occurred on this call) -- never measured inside this
    function, so the inference timer below is guaranteed to start only
    after construction has already finished."""
    result = AnalyzerResult(
        candidate_id="beatnet",
        candidate_kind="ML_MODEL",
        fixture_id=fixture_id,
        run_state="OK",
        device="cpu",
        checkpoint_size_mb=_checkpoint_size_mb(model),
        estimator_lifecycle=estimator_lifecycle,
        notes="Offline mode, DBN (non-causal) inference, pinned model checkpoint "
              f"model-{model}.pt (repo-bundled, CC BY 4.0). beats_per_bar candidates=[2,3,4] "
              "(meter-adaptive). checkpoint_size_mb/total_model_asset_footprint_mb are equal here: "
              "exactly one .pt file is loaded per estimator instance.",
    )
    result.total_model_asset_footprint_mb = result.checkpoint_size_mb
    result.model_load_wall_sec = model_load_wall_sec
    tracemalloc.start()
    t_infer_start = time.perf_counter()
    try:
        output = estimator.process(wav_path)
    except Exception as exc:
        result.run_state = "FAILED"
        result.error = f"{type(exc).__name__}: {exc}"
        _finalize_timing(result, t_infer_start)
        return result

    output = np.asarray(output)
    if output.ndim != 2 or output.shape[1] < 2:
        result.run_state = "FAILED"
        result.error = f"unexpected BeatNet output shape {output.shape}"
        _finalize_timing(result, t_infer_start)
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
    _finalize_timing(result, t_infer_start)
    return result


def _finalize_timing(result: AnalyzerResult, t_infer_start: float) -> None:
    t_infer_end = time.perf_counter()
    _, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_mb, mem_method = process_peak_rss_mb()
    result.inference_wall_sec = round(t_infer_end - t_infer_start, 4)
    result.asset_fetch_wall_sec = None  # never separately measured for BeatNet (no runtime network fetch)
    result.total_call_wall_sec = round((result.model_load_wall_sec or 0.0) + result.inference_wall_sec, 4)
    result.process_peak_rss_mb = rss_mb
    result.python_tracemalloc_peak_mb = round(py_peak / (1024 * 1024), 2)
    result.memory_measurement_method = mem_method


def run(fixture_id: str, wav_path: str, model: int = 1) -> AnalyzerResult:
    """Canonical correctness entry point (PM REVIEW #2 R8): constructs a
    brand-new estimator every call. This is the ONLY function eval/run_shootout.py
    calls to produce all_raw.json/metrics.json rows."""
    t_load_start = time.perf_counter()
    try:
        estimator = construct_estimator(model=model, mode="offline", inference_model="DBN", device="cpu")
    except Exception as exc:
        result = AnalyzerResult(
            candidate_id="beatnet", candidate_kind="ML_MODEL", fixture_id=fixture_id,
            run_state="FAILED", error=f"{type(exc).__name__}: {exc}",
            estimator_lifecycle="FRESH_PER_CALL",
        )
        result.model_load_wall_sec = round(time.perf_counter() - t_load_start, 4)
        return result
    model_load_wall = time.perf_counter() - t_load_start
    return run_with_estimator(estimator, fixture_id, wav_path, model=model,
                               estimator_lifecycle="FRESH_PER_CALL",
                               model_load_wall_sec=round(model_load_wall, 4))
