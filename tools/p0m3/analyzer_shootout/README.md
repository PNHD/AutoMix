# P0-M3-R1 analyzer shootout harness (disposable)

**Status: disposable P0-M3 benchmark-execution prototype.** This is not
production engine code (`AGENTS.md` P0 rule: no production app
implementation during P0 unless a task explicitly authorizes a disposable
experiment -- Issue #5 explicitly does). Nothing under this directory is a
dependency of any future shipping AutoMix core; components here are
isolated one-off runner scripts, not a library API.

Full narrative report: [`docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md`](../../../docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md).
Artifact/license audit: [`docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md`](../../../docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md).
Third-party code notices (required by the MIT terms of the one direct code
port in this harness): [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Layout

```
fixtures/generate_fixtures.py   deterministic synthetic WAV fixture generator + ground-truth manifest.json
fixtures/manifest.json          committed ground truth (SYNTHETIC_EXACT), no audio bytes
local_audio/                    generated .wav/.mp3 fixtures -- gitignored, regenerate locally
common/schema.py                normalized AnalyzerResult comparison shape (Issue #5 Task B)
baselines/                      3 required negative baselines (pure numpy/scipy, no ML deps)
candidates/run_beatnet.py       BeatNet (mjhydri/BeatNet @ 81cedd4b) runner + documented Windows/py3.10 compat shims.
                                 run() = canonical, ALWAYS fresh-per-call (correctness-safe, PM REVIEW #2 R8).
                                 construct_estimator()/run_with_estimator() = building blocks reused only by
                                 the separate profiling/equivalence scripts below, never by run() itself.
candidates/run_cuedetr.py       CUE-DETR (ETH-DISCO/cue-detr @ d0462856) runner, adapted from upstream cue_points.py (MIT).
                                 Same run()-is-canonical-fresh-per-call split as run_beatnet.py. Also exposes
                                 generate_backbone_equivalence_evidence() (R12 machine-readable proof generator).
eval/metrics.py                 beat/downbeat/phrase/section/BPM error metrics vs. SYNTHETIC_EXACT ground truth,
                                 including the two-sided TP/FP/FN/precision/recall/F1 boundary_event_metrics().
eval/run_shootout.py            CLI orchestrator; merges CANONICAL (fresh-per-call) results across venvs into results/.
eval/run_runtime_profile.py     SEPARATE, non-canonical warm-reuse performance profiler -> results/runtime_profile.json.
                                 Never read by run_shootout.py; never feeds correctness metrics.
eval/warm_equivalence_test.py   Same-fixture cold-vs-warm equivalence test -> results/warm_cold_equivalence.json.
eval/verify_repair.py           Programmatic verification of every PM-repair claim (10 assertion groups); run this
                                 after regenerating results to confirm nothing regressed.
results/raw/*.json              one AnalyzerResult per (candidate, fixture), CANONICAL (fresh-per-call) only -- committed
results/metrics.json            computed metrics, canonical -- committed
results/all_raw.json            merged canonical raw results -- committed
results/SUMMARY.md              machine-generated table, canonical -- committed
results/runtime_profile.json    separate warm-reuse PERFORMANCE data only -- committed, but not correctness evidence
results/warm_cold_equivalence.json   same-fixture equivalence test evidence -- committed
results/cuedetr_backbone_equivalence.json   machine-readable use_pretrained_backbone=False proof -- committed
results/lane_decisions.json     machine-readable Issue #5 Task F lane decisions, enum-validated -- committed
requirements/*.lock.txt         exact `pip freeze` from each real install attempt -- committed for reproducibility
```

## Canonical correctness vs. performance profiling (PM REVIEW #2 R8)

**`results/all_raw.json`/`results/metrics.json`/`results/SUMMARY.md` are
produced exclusively from fresh-per-call runs** (`candidates/run_*.py`'s
`run()` function constructs a brand-new model/estimator every single
call). This is deliberate: an earlier repair pass reused one BeatNet
estimator across fixtures and found it changed BeatNet's own output
depending on which fixture had run before it (`results/warm_cold_equivalence.json`
proves this concretely — see the main report Sec 5.3). Canonical
correctness numbers must never depend on fixture processing order, so
they never use that reuse path.

Two **separate** artifacts exist purely to characterize warm-reuse
performance, and neither is ever merged into canonical results:
- `results/runtime_profile.json` (`eval/run_runtime_profile.py`) —
  deliberately reuses one model across all 8 fixtures, timing only.
- `results/warm_cold_equivalence.json` (`eval/warm_equivalence_test.py`) —
  answers whether that reuse is even safe, on one fixed fixture, isolating
  state-carryover from input variation.

## Why two/three separate venvs

BeatNet's pinned dependency (`numba==0.54.1`) requires Python `<3.10`
which this machine's Python (3.10.6) cannot satisfy, and BeatNet's
`madmom` dependency additionally needs `numpy<1.24` at **runtime** (not
just install time -- see compat notes in `candidates/run_beatnet.py`).
CUE-DETR pins `numpy==1.26.4` and a much newer `torch`/`transformers`
stack. These requirement sets are mutually incompatible in one
environment, so each candidate was installed into its own throwaway venv
(outside the repo, not committed) and `run_shootout.py` merges the
resulting `results/raw/*.json` files across separate invocations (each
invocation re-scans `results/raw/` and regenerates `metrics.json` /
`SUMMARY.md` from the full accumulated set, so results from different
venvs correctly combine even though no single process imports every
candidate).

## Reproduce

```bash
# 1. Generate fixtures (any Python 3.10+ with numpy; no ML deps)
python fixtures/generate_fixtures.py --out-dir local_audio --manifest-out fixtures/manifest.json

# 2. Negative baselines only (numpy/scipy only)
python eval/run_shootout.py --candidates baselines

# 3. BeatNet (separate venv -- see requirements/beatnet.lock.txt for the exact freeze).
#    On Windows this REQUIRES MSVC Build Tools (madmom compiles Cython
#    extensions) and numpy<1.24 at runtime:
python -m venv .venv-beatnet
.venv-beatnet/Scripts/python.exe -m pip install numpy cython scipy "librosa>=0.8.0" mido pytest matplotlib wheel setuptools
#   -- run the following from an "x64 Native Tools / Developer" prompt (vcvars64.bat) so cl.exe is on PATH --
.venv-beatnet/Scripts/python.exe -m pip install --no-build-isolation madmom
.venv-beatnet/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-beatnet/Scripts/python.exe -m pip install "git+https://github.com/mjhydri/BeatNet.git@81cedd4beeb7235262db80969a0c9ce9a48a0ed4"
.venv-beatnet/Scripts/python.exe -m pip install pyaudio
.venv-beatnet/Scripts/python.exe -m pip install "numpy==1.23.5"   # downgrade AFTER madmom builds; madmom's DBN needs numpy<1.24 at import/runtime
.venv-beatnet/Scripts/python.exe eval/run_shootout.py --candidates beatnet

# 4. CUE-DETR (separate venv -- see requirements/cuedetr.lock.txt). Requires ffmpeg
#    on PATH to transcode the generated WAV fixtures to MP3 (upstream's own
#    cue_points.py only globs *.mp3):
python -m venv .venv-cuedetr
.venv-cuedetr/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-cuedetr/Scripts/python.exe -m pip install "transformers==4.42.3" "scipy==1.14.0" matplotlib "pillow==10.4.0" "librosa==0.10.2.post1" "numpy==1.26.4" "timm==1.0.7"
ffmpeg -y -i local_audio/FIX-A....wav -codec:a libmp3lame -qscale:a 2 local_audio/mp3/FIX-A....mp3   # repeat per fixture
.venv-cuedetr/Scripts/python.exe eval/run_shootout.py --candidates cuedetr

# 5. Re-merge everything into results/ (safe to run from any venv, does not re-run candidates):
python eval/run_shootout.py --candidates none

# 6. (Optional) separate warm-reuse performance profiling -- NOT correctness data:
.venv-beatnet/Scripts/python.exe eval/run_runtime_profile.py --candidate beatnet
.venv-cuedetr/Scripts/python.exe eval/run_runtime_profile.py --candidate cuedetr

# 7. (Optional) same-fixture cold-vs-warm equivalence test:
.venv-beatnet/Scripts/python.exe eval/warm_equivalence_test.py --candidate beatnet
.venv-cuedetr/Scripts/python.exe eval/warm_equivalence_test.py --candidate cuedetr

# 8. Verify every repaired claim programmatically (run from either venv):
python eval/verify_repair.py
```

## What was NOT executed and why

- **All-In-One Music Structure Analyzer** -- `SOURCE_ONLY_INSPECTED` /
  `BLOCKED_ENVIRONMENT`. Upstream's own README requires building NATTEN
  from source on Windows via `make` (`git clone .../NATTEN && make`);
  this machine has no `make` (checked: `where make` -> not found).
  `pip install natten` was attempted directly as a fallback and did not
  resolve to a working wheel within 60s (no prebuilt Windows wheel on
  PyPI for this torch/Python combination), consistent with upstream's
  own documented Windows install path. Not attempted further, per Issue
  #5's stop condition that a single blocked candidate does not block the
  rest of the task. Code/config/checkpoint provenance was still inspected
  (see the license matrix and main report).
- **Essentia** -- `SOURCE_ONLY_INSPECTED`. No Windows wheel exists on
  PyPI (`pip index versions essentia` -> `No matching distribution
  found`), and Essentia's own build system (waf, custom C++ toolchain)
  is a multi-dependency from-source build not attempted here, consistent
  with this project's standing decision
  (`docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`: "Do not make
  the core depend on Essentia during P0" -- AGPLv3, reference/oracle
  only). Not required for this pass's AC4 (BeatNet and CUE-DETR were
  both actually executed).

## Legal/scope notes

- No commercial/copyrighted audio was downloaded, generated, or committed.
  All fixtures are 100% procedurally synthesized (`fixtures/generate_fixtures.py`).
- `local_audio/` (generated .wav/.mp3) is gitignored per Issue #5 Task C's
  default-to-local instruction, even though these specific files carry no
  third-party rights question (owner-generated/SYNTHETIC).
- The BeatNet (CC BY 4.0) and CUE-DETR (MIT, checkpoint per HF metadata
  tag) model checkpoints were downloaded to the local Hugging Face /
  package cache **outside this repository** for benchmark execution only;
  they are not committed, vendored, or made a build dependency of
  anything under `tools/` or any future production path.
