"""
Shared OS-level process memory measurement helper (PM REPAIR R1).

Prefers real process peak RSS via `psutil` when importable. On Windows,
`psutil.Process().memory_info().peak_wset` is the OS-reported peak working
set size for this process since it started -- a genuine process-level peak,
not a Python-object-level approximation. When `psutil` is unavailable, the
caller must fall back to `tracemalloc` and label it explicitly as such
(never as process peak memory) -- see `python_tracemalloc_peak_mb` in
`common/schema.py`.
"""
from __future__ import annotations

import os
from typing import Optional


def process_peak_rss_mb() -> tuple[Optional[float], str]:
    """Returns (peak_rss_mb_or_None, memory_measurement_method)."""
    try:
        import psutil
    except ImportError:
        return None, "UNAVAILABLE_PSUTIL_NOT_INSTALLED"

    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()
    peak_bytes = getattr(mem, "peak_wset", None)  # Windows-specific field
    if peak_bytes is None:
        # Non-Windows psutil builds don't expose a peak field directly;
        # `rss` is a current-value-only proxy here, not a true peak, so we
        # do not silently claim it is one.
        return None, "UNAVAILABLE_NO_PEAK_FIELD_ON_THIS_PLATFORM"
    return round(peak_bytes / (1024 * 1024), 2), "PSUTIL_PROCESS_PEAK_WSET_RSS"
