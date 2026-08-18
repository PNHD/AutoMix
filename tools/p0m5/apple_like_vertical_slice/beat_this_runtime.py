"""
P0-M5-R1 -- thin runtime wrapper around the pinned `Beat This!` beat/downbeat
tracker (`CPJKU/beat_this` @ `b95c8ab0c58c2d9fcfd40508ae8dffbc05ac4f5c`, MIT
code + published weights, per Issue #10's pinned-candidate table).

Isolation:
  - the vendored repo lives at `work_local/vendor/beat_this` (gitignored,
    cloned+pinned by this task, never committed);
  - the two small missing runtime deps (`rotary_embedding_torch`, `soundfile`)
    are installed into `work_local/pylibs` (an isolated `pip install
    --target` directory -- see docs/research/P0-M5-R1-APPLE-LIKE-RAPID-
    VERTICAL-SLICE.md SS Phase A), never the shared/global site-packages;
  - the model checkpoint cache is redirected to `work_local/torch_cache` via
    the `TORCH_HOME` environment variable (set by the caller/CLI entry
    point below), never the user's global `~/.cache/torch`.

No admin/system-wide install was performed for this task -- `torch`/
`torchaudio`/`einops` were already present in the shared research
environment from prior accepted P0-M3 work and are reused, not reinstalled.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK_LOCAL = HERE / "work_local"
PYLIBS = WORK_LOCAL / "pylibs"
BEAT_THIS_VENDOR = WORK_LOCAL / "vendor" / "beat_this"

_PATHS_ADDED = False


def ensure_import_paths() -> None:
    global _PATHS_ADDED
    if _PATHS_ADDED:
        return
    for p in (str(PYLIBS), str(BEAT_THIS_VENDOR)):
        if p not in sys.path:
            sys.path.insert(0, p)
    _PATHS_ADDED = True


_MODEL_CACHE = {}


def get_model(device: str = "cuda", checkpoint: str = "final0"):
    ensure_import_paths()
    from beat_this.inference import File2Beats  # noqa: E402

    key = (device, checkpoint)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = File2Beats(checkpoint_path=checkpoint, device=device, dbn=False)
    return _MODEL_CACHE[key]


def analyze_file(wav_path, device: str = "cuda") -> dict:
    """Returns {"beats_s": [...], "downbeats_s": [...]} -- plain Python
    floats, no torch/numpy objects, safe to json.dumps directly."""
    model = get_model(device=device)
    beats, downbeats = model(str(wav_path))
    return {
        "beats_s": [float(x) for x in beats],
        "downbeats_s": [float(x) for x in downbeats],
    }
