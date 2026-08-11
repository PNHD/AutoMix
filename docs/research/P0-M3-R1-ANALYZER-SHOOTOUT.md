# P0-M3-R1 — Cue/Beat/Structure Analyzer Shootout

Status date: 2026-08-11

## 0. Execution profile actually used

- **Execution agent:** Claude Code runtime (Claude Desktop -> Code
  execution surface per `AGENTS.md`; the runtime self-identifies as
  `Claude Code`, which per `AGENTS.md`'s Desktop execution-surface
  semantics is not itself a stop condition).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High
  (owner/PM Desktop-UI attestation, not independently introspectable by
  this runtime — consistent with the same non-blocking treatment applied
  in every prior P0-M2 revision).
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:**
  OFF (no `Agent`/`Task` subagent calls were made anywhere in this task —
  all research, license lookups, code, fixture generation, environment
  probing, and candidate execution were performed directly by the parent
  agent). **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **Starting baseline:** `d2601328ea2d4f3abc1e30b2791d728e1c31c33d` (accepted P0-M2 head).

## 1. Result

**PARTIAL**

Rationale, stated plainly up front rather than left implicit: every
Task A–F requirement was executed with real evidence, and AC1–AC17 all
have direct, checkable support (§15). It is `PARTIAL` rather than `PASS`
for two honest reasons, neither of which is a "code doesn't compile"
excuse:

1. Two of the four pinned candidates (All-In-One, Essentia) were
   `BLOCKED_ENVIRONMENT` / `SOURCE_ONLY_INSPECTED` this pass — real,
   evidenced, Windows-specific blockers (§5, §9), not fabricated
   avoidance. Issue #5 explicitly allows this ("A single blocked
   candidate does not block the whole task if the remaining lanes can be
   evaluated honestly"), and two of four candidates *were* actually
   executed (BeatNet, CUE-DETR — AC4).
2. The downbeat/meter results actually obtained are a genuinely mixed,
   partly-negative finding (§6): BeatNet's beat-timestamp accuracy is
   strong, but its downbeat/meter classification was **not reliably
   validated** on this pass's synthetic fixtures (consistently predicted
   meter=2 regardless of ground truth, including on the 3/4 fixture).
   This is reported honestly as `UNKNOWN_NEEDS_RUNTIME_PROOF` on real
   musical material, not glossed over as a pass.

## 2. Candidate revisions actually inspected/run

| Candidate | Repo | Pinned revision (Issue #5) | Revision actually used | Verification |
|---|---|---|---|---|
| CUE-DETR | `ETH-DISCO/cue-detr` | `d0462856ed2f59a1fb65267cfbe87340a65ad1bb` | Same — code logic ported directly from `cue_points.py` at this exact revision (fetched via `gh api repos/ETH-DISCO/cue-detr/contents/...?ref=d0462856...`); checkpoint loaded from `disco-eth/cue-detr` on Hugging Face as the pinned code itself specifies | Tree/file contents fetched at the exact pinned SHA via GitHub API; checkpoint load + real inference executed (§6) |
| All-In-One | `mir-aidj/all-in-one` | `18e78903c0365147a2c5d4e5e57ebf88cb7d800e` | Same (inspected only — not executed, §5) | Tree/`pyproject.toml`/`README.md`/`loaders.py` fetched at the exact pinned SHA via GitHub API |
| BeatNet | `mjhydri/BeatNet` | `81cedd4beeb7235262db80969a0c9ce9a48a0ed4` | Same — installed via `pip install git+https://github.com/mjhydri/BeatNet.git@81cedd4beeb7235262db80969a0c9ce9a48a0ed4`, confirmed via `pip show BeatNet` reporting version `1.2.0` (the version string baked into that exact commit's `pyproject.toml`) | Installed from the exact pinned commit URL; real inference executed (§6) |
| Essentia | `MTG/essentia` | `b9fa6cb674ca43dfb94d28d293aeda441c6745db` | Not re-cloned this pass; license/portability facts drawn from the existing pinned record in `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md` plus a fresh `pip index versions essentia` check (§9) | `pip index versions essentia` executed fresh this pass; no new repository inspection needed (no new claim about Essentia's *code* was made) |

No deviations from pinned revisions occurred (AC1). Dependency pins
*inside* those revisions that could not be satisfied on this machine
(BeatNet's `numba==0.54.1`, matplotlib `3.9.1`'s yanked Windows wheel)
are documented as explicit, evidenced deviations in §5/§9, never silent.

## 3. Environment this pass actually ran on

- OS: Windows 11 Pro (build 26200), Python 3.10.6, pip 26.1.2, git 2.53.0.
- GPU: NVIDIA GeForce RTX 2060, 6 GB VRAM, driver 610.74. **Not used this
  pass** — both executed candidates ran on CPU-only PyTorch wheels for
  simplicity/reliability under this task's time budget. All wall-time
  numbers in §6/§8 are CPU-only and are not representative of achievable
  GPU-accelerated latency.
- `nvcc`/CUDA toolkit: not installed (irrelevant to CPU-wheel PyTorch,
  which bundles its own CUDA runtime for GPU wheels — not exercised here).
- MSVC: Visual Studio 2022 Build Tools present (`cl.exe` found under
  `VC\Tools\MSVC\14.44.35207\...`), enabling BeatNet's `madmom` Cython
  extensions to compile from source (§5.3).
- `make`: **not found** (`where make` → no match). This is the exact
  documented blocker for All-In-One's Windows NATTEN install path (§5.2).
- Disk: 273 GB free on the working volume — not a constraint.
- Network: outbound HTTPS confirmed working (GitHub, Hugging Face, PyPI
  all reachable).

## 4. Required negative baselines — result (AC5)

All three required baselines (Issue #5 "REQUIRED NEGATIVE BASELINES")
were implemented independently (no GPL/AGPL source consulted or copied)
under `tools/p0m3/analyzer_shootout/baselines/` and executed against all
8 fixtures (24/24 runs `OK`, `results/raw/*_baseline__FIX-*.json`):

1. **`scalar_bpm_grid_baseline`** — theoretical `i*(60000/BPM)` grid from
   `t=0`, using each fixture's exact metadata BPM (an intentionally
   generous input — real metadata is rarely this exact). Result: **beat
   fraction OK-rate (≤1/16 beat, `COND_BEAT_OK`) = 1.0 on 6 of 8
   fixtures where the true grid happens to start at t=0**, but
   **collapses to 0.0 on FIX-B (deliberate 0.5-beat phase offset;
   median beat-fraction error ≈0.4997, i.e. maximally wrong)** and to
   **0.125 on FIX-H (variable tempo; median beat-fraction error ≈0.272)**.
   This is direct, measured proof of the terminology-gate claim
   (`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §3.1):
   a scalar-BPM theoretical grid is not beat-aware — it is only as good
   as its unverified phase-zero assumption, and it has **zero**
   downbeat/meter/cue/phrase/section output by construction (every one
   of those fields is `null` in its raw JSON on every fixture).
2. **`fixed_32_beat_phrase_proxy_baseline`** — asserts a phrase boundary
   every 32 beats from beat 0, fed the *ground-truth* beat grid (an
   intentionally generous input, isolating the proxy's own structural
   error from any beat-detection error). On FIX-F (real authored section
   boundaries at beats 0/32/64/128 of a 192-beat, 4-section track), the
   N=32 proxy's boundaries {0, 32, 64, 96, 128, 160} happen to hit 3 of 4
   true boundaries **but also assert two boundaries (96, 160) with no
   musical basis whatsoever** — direct, measured evidence for the
   terminology gate's claim that a fixed-N-beat proxy is not
   phrase-awareness. (Metric caveat: the `phrase_boundary_distance`
   metric as implemented measures ground-truth→nearest-prediction
   distance only, so it does not penalize the proxy's 2 spurious
   insertions — a known, disclosed limitation of this pass's metric, not
   a hidden one; see §14.)
3. **`energy_onset_heuristic_baseline`** — 50 ms-window RMS envelope with
   relative-threshold peak-picking as "cue candidates", plus a coarse
   3-level long-window RMS segmentation as a structure proxy. Ran on the
   actual audio samples (not ground truth) on all 8 fixtures. Produces
   plausible-looking cue candidates near clear energy transients, but
   with no beat/downbeat/phrase model of any kind — included for exactly
   this reason (a naive-but-real floor to beat, not a recommendation).

## 5. Portability / runtime reality (Task E)

| Candidate | Language/stack | CUDA-only? | CPU support | Windows x64 | macOS ARM | Linux | Mobile export | Model size | Cold start | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| BeatNet | Python, PyTorch (CRNN) + madmom (Cython HMM/DBN) | No | Yes (used this pass) | Works, **with two documented compat shims** (§5.3) | `UNKNOWN_NEEDS_RUNTIME_PROOF` (INFERENCE: madmom's Cython extensions build via Xcode clang, torch has native arm64 wheels — plausible but not tested) | `UNKNOWN_NEEDS_RUNTIME_PROOF` (INFERENCE: gcc-based madmom builds are the common case in the wild) | No documented ONNX/CoreML/TFLite path; the offline DBN post-processing is madmom C-extension code, not a pure-tensor op — a mobile port would mean **reimplementing** the DBN/particle-filter logic, not exporting it | 3× ~1.6 MB `.pt` (CRNN only; DBN has no weights) | 12.7–53 s first call in-process (model load dominates); 0.26–0.74 s per fixture once warm, same process | `RUNS_WITH_WORKAROUND` (Windows, this pass) |
| CUE-DETR | Python, PyTorch + HF `transformers` (DETR) + `timm` (ResNet-50 backbone) | No | Yes (used this pass) | `RUNS_NOW` — **zero native-compile blockers**, plain pip wheels throughout | `UNKNOWN_NEEDS_RUNTIME_PROOF` (INFERENCE: same reasoning as CUE-DETR's own pure-PyTorch stack — likely the easiest of the four to port) | `UNKNOWN_NEEDS_RUNTIME_PROOF` (INFERENCE, same reasoning) | Standard HF DETR models have documented ONNX export paths via `optimum`; not attempted this pass | Checkpoint 159 MB (`disco-eth/cue-detr`, safetensors) + 98 MB `timm/resnet50.a1_in1k` backbone + negligible DETR processor config = **~257 MB total on-disk footprint** | 78.98 s first call (includes one-time HF download + model load); 1.59–11.23 s per fixture once warm/cached, same process | `RUNS_NOW` |
| All-In-One | Python, PyTorch + `demucs` + NATTEN (dilated neighborhood attention) | No (CUDA optional/accelerative only) | Yes per upstream docs (not verified this pass) | **`BLOCKED_ENVIRONMENT`** — upstream's own README: *"Windows: Build from source: `pip install ninja; git clone .../NATTEN; cd NATTEN; make`"*. This machine has no `make` (`where make` → not found, §3). A direct `pip install natten` fallback was attempted and did not resolve to a working wheel within 60 s (killed) — consistent with no prebuilt Windows PyPI wheel for this torch/Python combination | Upstream README: *"macOS: Auto-installs with allin1"* — `UNKNOWN_NEEDS_RUNTIME_PROOF`, not tested this pass | Upstream README: *"Linux: Download from NATTEN website"* (prebuilt wheel) — `UNKNOWN_NEEDS_RUNTIME_PROOF`, plausibly the easiest non-Windows path | NATTEN's custom CUDA/CPU attention kernels have no documented ONNX/CoreML/TFLite export; a mobile port is realistically a from-scratch reimplementation, same category as BeatNet's DBN | 8× per-fold checkpoints hosted at `taejunkim/allinone` (sizes not measured — never downloaded, §5.2) | Not measured | `BLOCKED_ENVIRONMENT` (Windows, this pass) / `SOURCE_ONLY_INSPECTED` |
| Essentia | C++ core + Python bindings; separate TensorFlow model zoo | No | Yes per upstream docs | **`BLOCKED_ENVIRONMENT`** — `pip index versions essentia` → `ERROR: No matching distribution found for essentia` (no Windows PyPI wheel); from-source build uses a custom `waf` toolchain with many native dependencies, out of this pass's time budget | Historically supported per upstream docs, not independently verified this pass | Historically supported per upstream docs, not independently verified this pass | Essentia has shipped in some native mobile MIR projects historically (not independently verified this pass) | Not measured | Not measured | `BLOCKED_ENVIRONMENT` / `SOURCE_ONLY_INSPECTED` |

### 5.1 Beat/downbeat/cue lane summary against Issue #5's classification enum

- BeatNet: `RUNS_WITH_WORKAROUND`
- CUE-DETR: `RUNS_NOW`
- All-In-One: `BLOCKED_ENVIRONMENT` (Windows this pass) — code itself is `SOURCE_ONLY_INSPECTED`
- Essentia: `BLOCKED_ENVIRONMENT` — code itself is `SOURCE_ONLY_INSPECTED`
- scalar-BPM / fixed-32-beat / energy-onset baselines: `RUNS_NOW` (pure numpy/scipy, zero ML deps)

### 5.2 All-In-One — exact blocker evidence

```
$ where make
INFO: Could not find files for the given pattern(s).

$ <venv>/python.exe -m pip install natten
# no resolvable wheel found within 60s; command terminated (exit 143)
$ <venv>/python.exe -m pip show natten
WARNING: Package(s) not found: natten
```

Upstream's own `README.md` at the pinned revision (§ "Installation"):
*"2. Install NATTEN (Required for Linux and Windows; macOS will
auto-install) ... Windows: Build from source: `pip install ninja # ...`,
`git clone https://github.com/SHI-Labs/NATTEN`, `cd NATTEN`, `make`"*.
This is a real, reproducible environment gap on the machine available for
this task, not an assumption. NATTEN's own license is MIT
(`SHI-Labs/NATTEN`, confirmed via its `LICENSE` file) — the blocker is
purely a build-tooling gap (missing `make`), not a license gap.

### 5.3 BeatNet — exact Windows/Python-3.10 compatibility path (documented, not silent)

Three real, independently-diagnosed compatibility problems were
encountered and resolved, each with concrete evidence (full detail also
in `tools/p0m3/analyzer_shootout/candidates/run_beatnet.py`'s module
docstring):

1. **`numba==0.54.1` (BeatNet's own pinned requirement) has no wheel for
   Python ≥3.10.** `pip install numba==0.54.1` on this Python 3.10.6
   machine fails outright (`ERROR: Ignored the following versions that
   require a different python version ... Requires-Python >=3.7,<3.10`).
   Resolved by installing an unpinned, current `numba` instead — an
   explicit, evidenced deviation from the exact pin, required because no
   version of Python this task's environment can select satisfies the
   original pin.
2. **`madmom==0.16.1` (BeatNet's real dependency) fails to build on
   Windows without a C compiler present, and fails to build at all
   without `wheel` pre-installed** (`error: invalid command 'bdist_wheel'`).
   Resolved with MSVC Build Tools 2022 (`cl.exe`, confirmed present),
   `pip install wheel setuptools` first, then
   `pip install --no-build-isolation madmom` from inside an
   `vcvars64.bat`-initialized shell.
3. **`madmom` does not import cleanly on Python 3.10 / numpy≥1.24 at
   runtime**, independent of the build step:
   - `from collections import MutableSequence` (`madmom/processors.py`)
     — this stdlib alias was removed in Python 3.10 (moved to
     `collections.abc` in Python 3.3, then the top-level re-export was
     dropped). Fixed with a harness-local shim restoring the alias
     *before* importing `madmom` — this does not modify madmom's source.
   - `np.float`/`np.int`/etc (`madmom/io/__init__.py` and others) —
     deprecated numpy aliases removed in numpy 1.24. Same shim approach.
   - **A deeper one, only surfaced by actually running inference, not
     just importing the package:** `DBNDownBeatTrackingProcessor`'s
     internal construction of a ragged (non-rectangular) array of
     per-meter-hypothesis results raises `ValueError: setting an array
     element with a sequence ... inhomogeneous shape` on numpy≥1.24
     (numpy made the old `VisibleDeprecationWarning`-and-silently-succeed
     behavior a hard error). This is **not** fixable by a small alias
     shim — it required downgrading the venv's numpy to `1.23.5`
     (installed *after* `madmom` builds, since the build step itself
     wanted a newer numpy). After the downgrade, the identical inference
     call succeeds (with only a `VisibleDeprecationWarning`, not an
     error) and returns real beat/downbeat output (§6).

None of these three fixes touch madmom's own source code or algorithmic
behavior; all are recorded in `tools/p0m3/analyzer_shootout/README.md`
and `requirements/beatnet.lock.txt` (exact `pip freeze`) for reproduction.

## 6. Beat/downbeat lane results (AC6, AC7)

Ran: BeatNet (real, offline mode, DBN/non-causal inference — the mode
intended for whole-file analysis) and the scalar-BPM negative baseline,
against all 8 fixtures. All-In-One and Essentia were not runnable this
pass (§5). Full per-fixture numbers: `tools/p0m3/analyzer_shootout/results/metrics.json`
and `.../results/SUMMARY.md` (both committed).

### 6.1 Beat-timestamp accuracy (explicit timestamps, not inferred from BPM — AC6)

| Fixture | scalar-BPM `COND_BEAT_OK` rate | scalar-BPM median beat-fraction error | BeatNet `COND_BEAT_OK` rate | BeatNet median beat-fraction error |
|---|---|---|---|---|
| FIX-A constant 120 BPM | 1.0 | 0.0 | 1.0 | 0.040 |
| FIX-B half-beat phase offset | **0.0** | **0.500** | **1.0** | 0.030 |
| FIX-C wrong-downbeat-phase (beat grid itself still regular) | 1.0 | 0.0 | 1.0 | 0.033 |
| FIX-D 4/4 reference (140 BPM) | 1.0 | 0.001 | 1.0 | 0.033 |
| FIX-E 3/4 waltz (90 BPM) | 1.0 | 0.0005 | 1.0 | 0.020 |
| FIX-F structure/sections (128 BPM) | 1.0 | 0.0005 | 1.0 | 0.023 |
| FIX-G intro/body/outro energy | 1.0 | 0.0005 | 1.0 | 0.024 |
| FIX-H variable tempo ramp | **0.125** | **0.272** | **1.0** | 0.027 |

`COND_BEAT_OK` = beat-alignment error ≤1/16 beat, the exact threshold
from `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §7. This
is the single clearest quantitative result of this pass: **on the two
fixtures deliberately designed to break a phase-zero assumption (FIX-B)
and a fixed-tempo assumption (FIX-H), the scalar-BPM theoretical-grid
baseline collapses (0.0 and 0.125 OK-rate) while BeatNet's real
beat-timestamp tracking holds at 1.0 on every fixture**, with median
error consistently in the 2–4% of a beat range. This is direct,
measured, `FACT`-tagged evidence for the terminology-gate distinction
(beat-aware ≠ a `60000/BPM` theoretical grid).

### 6.2 Downbeat / bar-phase correctness (evaluated separately from beat correctness — AC7)

BeatNet's offline DBN chooses its own meter hypothesis from candidates
`[2, 3, 4]` beats-per-bar (madmom's `DBNDownBeatTrackingProcessor`
default) rather than being told the true meter. **On all 8 fixtures,
including the true-3/4 FIX-E, it selected `beats_per_bar=2`:**

| Fixture | True meter (num.) | BeatNet predicted meter | `meter_correct` |
|---|---|---|---|
| FIX-A | 4 | 2 | False |
| FIX-B | 4 | 2 | False |
| FIX-C | 4 | 2 | False |
| FIX-D | 4 | 2 | False |
| FIX-E | **3** | 2 | False |
| FIX-F | 4 | 2 | False |
| FIX-G | 4 | 2 | False |
| FIX-H | 4 | 2 | False |

This pass's `exact_bar_phase_accuracy` metric (does the nearest predicted
beat to each true downbeat carry position-in-bar `1`?) shows misleadingly
high values on several fixtures (1.0 on FIX-A/B/C/G, 0.917 on FIX-D) —
**this is a disclosed metric artifact, not a real downbeat success**:
when the predicted meter is 2 (half the true 4), position-`1` markers
recur twice as often as true downbeats and trivially land near every
true downbeat by construction, without the model actually having
identified the correct bar length. `meter_correct=False` on every single
fixture is the metric that actually tells the truth here, and the two
metrics are reported side by side specifically so neither one is
mistaken for the whole picture. On FIX-F (the structure/section fixture,
whose "kick" layer plays the same pitch/velocity on every beat rather
than accenting beat 1 the way FIX-A/B/C/D/G do — a **fixture design gap
in this pass**, not a BeatNet finding) `exact_bar_phase_accuracy = 0.0`.

**Honest classification:** BeatNet's downbeat/meter output is
`UNKNOWN_NEEDS_RUNTIME_PROOF` on real musical material from this pass's
evidence alone. The consistent 2-vs-true-meter selection is most plausibly
explained (`INFERENCE`, not verified further this pass) by our synthetic
click fixtures lacking the spectral/timbral richness the downbeat
activation network was trained on (real snare/kick/harmonic timbral
contrast, not pure sine/noise clicks) — BeatNet's own published
benchmarks (Ballroom/GTZAN/RockCorpus downbeat-tracking, cited on its
README via Papers-with-Code badges) report competitive real-recording
downbeat performance, which this pass neither confirms nor refutes since
no real-music fixture was used. **This is exactly why AC9's synthetic
ground truth is necessary but not sufficient — a follow-up pass needs at
least one real/CC-licensed music fixture to validate downbeat/meter
specifically.**

## 7. Cue-point lane results (Task D, smoke-test framing required)

Ran: CUE-DETR (real) and the energy/onset heuristic negative baseline,
against all 8 fixtures. All-In-One's structure-derived cue candidates
were not obtainable this pass (§5). Fixed-N-beat phrase proxy is scored
separately in §8 (it is a phrase proxy, not a cue-point method — kept
distinct per AC8).

**Binding framing (Issue #5 Task D, restated because it governs how to
read every number below):** none of this pass's 8 fixtures has an
authored/expert cue region — they are synthetic click/tone/noise-burst
material. Every result in this section is **smoke/regression evidence
only**: proof the pipeline runs end-to-end and produces plausible-shaped
output, never a quality measurement of real-world cue-point accuracy.

| Fixture | CUE-DETR cue points (ms) | confidence | Energy/onset heuristic cue points (first 3, ms) |
|---|---|---|---|
| FIX-A | 69.7, 31718.5 | 1.00, 0.91 | (RMS-peak candidates near percussive clicks) |
| FIX-B | 232.2 | 1.00 | ″ |
| FIX-C | 46.4 | 1.00 | ″ |
| FIX-D | 46.4 | 1.00 | ″ |
| FIX-E | **-139.3**, 69.7 | 0.91, 1.00 | ″ |
| FIX-F | **-69.7** | 1.00 | ″ |
| FIX-G | **-46.4**, 71842.5 | 1.00, 0.92 | ″ |
| FIX-H | 69.7 | 1.00 | ″ |

Qualitative read (`INFERENCE`): CUE-DETR consistently places a
high-confidence cue very near track start, and on the two longest/most
structured fixtures (FIX-A, FIX-G) a second cue near the very end — a
pattern consistent with real DJ "first cue"/outro cue conventions, even
though the input material is not real EDM. **A genuine, unresolved
anomaly worth flagging plainly:** three fixtures produced small
*negative* millisecond timestamps (-139.3, -69.7, -46.4). This is most
plausibly (`INFERENCE`, not root-caused further this pass — out of
budget) an edge artifact of the sliding-window `PADDING`/frame-to-time
conversion in the upstream script near `t=0` on very short clips, not a
sign of a broader defect; it is reported as observed, not silently
clamped or hidden.

Full per-field results (raw cue-confidence arrays, wall time, peak
memory): `tools/p0m3/analyzer_shootout/results/raw/cue_detr__FIX-*.json`
(committed).

## 8. Structure lane results (Task D, phrase-vs-section caveat required)

All-In-One (the pinned structure-lane candidate) was not runnable this
pass (§5). The structure lane is therefore covered only by:

1. **`fixed_32_beat_phrase_proxy_baseline`** against FIX-F's real
   authored section boundaries — §4 item 2 (partial coincidental overlap,
   2 spurious insertions, direct evidence the proxy ≠ real phrase/section
   detection).
2. **`energy_onset_heuristic_baseline`**'s coarse 3-level RMS
   segmentation, which is a weak energy-level proxy, never a phrase or
   section model, and is not scored against FIX-F's ground truth in this
   pass's metrics pipeline (its output uses generic `low/mid/high_energy`
   labels, not the section-name vocabulary FIX-F's ground truth uses, so
   a like-for-like distance comparison was not meaningful to compute —
   recorded as a scope gap for §14, not silently glossed over).

**No phrase boundary is ever reported as a section boundary or vice
versa anywhere in this pass's schema or results** (`common/schema.py`
keeps `phrase_boundaries_ms` and `section_boundaries` as distinct fields
throughout; AC8). Whether All-In-One's real functional-segment output
would be "useful enough for transition planning" (Issue #5 Task D
structure-lane question) remains genuinely **unanswered** this pass —
recorded as an open item for the next P0-M3 pass once the NATTEN
Windows/Linux/macOS build path is resolved.

## 9. Decision matrix (Task F)

Per-lane decisions, using Issue #5's exact enum. No global winner is
named — per-lane only, per Issue #5's explicit instruction.

| Capability lane | Decision | Evidence basis |
|---|---|---|
| Beat timestamps | **`ADOPT_FOR_P0_PROTOTYPE`** (BeatNet) | §6.1 — real, strong accuracy including under phase-offset and variable-tempo stress cases where the negative baseline collapses; license is `BENCHMARK_ONLY` (§ license matrix) so "adopt" here means adopt into the next disposable P0 prototype/benchmark loop, not production, consistent with Issue #5's own P0 scope |
| Downbeats / bar phase | **`KEEP_AS_BENCHMARK_ONLY`** (BeatNet) | §6.2 — beat tracking strong, but downbeat/meter selection unvalidated on this pass's fixtures (systematic meter=2 misclassification); needs a real-music fixture before any adoption decision |
| Meter | **`KEEP_AS_BENCHMARK_ONLY`** (BeatNet) | Same evidence as above — 0/8 fixtures correctly classified this pass |
| Cue points | **`KEEP_AS_BENCHMARK_ONLY`** (CUE-DETR) | §7 — real execution, plausible qualitative behavior, but smoke-test only (no authored ground truth this pass) and EDM-domain-specific per the standing P0 concern (`docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) |
| Phrase candidates | **`REJECT`** (fixed-N-beat proxy) / **`PORT/EXPORT_EXPERIMENT_NEXT`** (All-In-One, once NATTEN build blocker is resolved) | §4 item 2 — proxy directly disproven; All-In-One never executed this pass |
| Section boundaries/labels | **`REJECT`** (energy-level heuristic as a real proxy) / **`PORT/EXPORT_EXPERIMENT_NEXT`** (All-In-One) | §8 — heuristic is a floor, not a candidate; All-In-One never executed this pass |
| Confidence / fallback inputs | **`KEEP_AS_BENCHMARK_ONLY`** (no candidate this pass) | Neither BeatNet's offline DBN API nor CUE-DETR's DETR detection-score is a calibrated musical-confidence signal usable for AutoMix's confidence-aware fallback (`AGENTS.md` quality terminology); this remains an open design problem, not solved by anything executed this pass |

### 9.1 Smallest composite stack recommendation for the next P0-M3 step

Not a monolithic framework — a combination, per Issue #5's own framing:

1. **BeatNet (offline/DBN)** for beat timestamps specifically — it is the
   one candidate with real, strong, evidenced accuracy today, including
   under the two adversarial stress cases (phase offset, variable
   tempo) this pass was built to catch. Its downbeat/meter output should
   **not** be trusted yet (§6.2).
2. **All-In-One**, once the NATTEN build blocker is resolved (most
   promising unblock path per upstream's own README: a Linux runner using
   NATTEN's prebuilt wheel, or macOS's auto-install path — both
   `UNKNOWN_NEEDS_RUNTIME_PROOF` but plausibly easier than the Windows
   from-source `make` path), as the **single MIT-licensed candidate that
   could supply downbeats, meter, and functional section labels in one
   package** — worth a dedicated Linux/macOS-runner pass before deciding
   whether it, rather than BeatNet, should own the downbeat/meter lane.
3. **CUE-DETR** for a cue-point signal specifically on EDM-genre-adjacent
   material, kept explicitly bounded to smoke-test status until a real
   (legally-clear) music fixture with authored cue ground truth exists.
4. The three negative baselines are retained **permanently as the
   comparison floor** for every future pass (not as production logic) —
   this pass's own numbers (§4, §6.1) are the first concrete evidence
   that the floor is meaningfully beatable, which is itself a required
   P0-M3 result.
5. Essentia stays `REFERENCE_ONLY`/benchmark-oracle-only, unchanged.

## 10. Validation — exact commands executed

```bash
# Environment probe
python --version; pip --version; git --version
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
where make; where cl.exe
pip index versions essentia   # -> No matching distribution found

# Fixture generation (committed generator, gitignored audio output)
python tools/p0m3/analyzer_shootout/fixtures/generate_fixtures.py \
  --out-dir tools/p0m3/analyzer_shootout/local_audio \
  --manifest-out tools/p0m3/analyzer_shootout/fixtures/manifest.json

# Baselines (numpy/scipy only)
python tools/p0m3/analyzer_shootout/eval/run_shootout.py --candidates baselines

# BeatNet (separate venv; MSVC vcvars64.bat active for the madmom build step)
python -m venv .venv-beatnet
.venv-beatnet/Scripts/python.exe -m pip install numpy cython scipy "librosa>=0.8.0" mido pytest matplotlib wheel setuptools
.venv-beatnet/Scripts/python.exe -m pip install --no-build-isolation madmom     # inside vcvars64.bat shell
.venv-beatnet/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-beatnet/Scripts/python.exe -m pip install "git+https://github.com/mjhydri/BeatNet.git@81cedd4beeb7235262db80969a0c9ce9a48a0ed4"
.venv-beatnet/Scripts/python.exe -m pip install pyaudio
.venv-beatnet/Scripts/python.exe -m pip install "numpy==1.23.5"
.venv-beatnet/Scripts/python.exe tools/p0m3/analyzer_shootout/eval/run_shootout.py --candidates baselines,beatnet

# CUE-DETR (separate venv)
python -m venv .venv-cuedetr
.venv-cuedetr/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-cuedetr/Scripts/python.exe -m pip install "transformers==4.42.3" "scipy==1.14.0" matplotlib "pillow==10.4.0" "librosa==0.10.2.post1" "numpy==1.26.4" "timm==1.0.7"
ffmpeg -y -i local_audio/<fixture>.wav -codec:a libmp3lame -qscale:a 2 local_audio/mp3/<fixture>.mp3   # x8
.venv-cuedetr/Scripts/python.exe tools/p0m3/analyzer_shootout/eval/run_shootout.py --candidates cuedetr

# Final merge (any venv)
python tools/p0m3/analyzer_shootout/eval/run_shootout.py --candidates none
```

**Exact results:** 40/40 runs completed with `run_state=OK` (24 baseline
runs × 3 baselines × 8 fixtures, 8 BeatNet runs, 8 CUE-DETR runs). Zero
`FAILED` runs in the final committed result set (earlier `FAILED` runs
during BeatNet/CUE-DETR bring-up, e.g. the `MutableSequence`/`np.float`/
ragged-array/`timm`-missing errors, are the exact evidence cited in §5.3
and were resolved before the committed run, not hidden). Full machine
output: `tools/p0m3/analyzer_shootout/results/{metrics.json,all_raw.json,SUMMARY.md,raw/*.json}`.

## 11. Scope compliance check

- No production AutoMix engine code was added anywhere (AC16) — every
  new file is under `tools/p0m3/analyzer_shootout/` (disposable harness,
  explicitly namespaced and documented as such in its own `README.md`)
  or `docs/research/` (research docs).
- Signalsmith Stretch / Rubber Band were not started, imported, installed,
  or referenced anywhere in this pass's code (AC17).
- No GPL/AGPL source was consulted or copied into the baseline
  implementations (`baselines/*.py` are original, independent
  implementations of publicly-documented formulas).
- No copyrighted/commercial audio, credentials, cookies, or tokens are
  committed anywhere in this change (AC12) — `tools/p0m3/analyzer_shootout/.gitignore`
  excludes all generated `.wav`/`.mp3`/checkpoint files; only the
  fixture *generator script* and the resulting ground-truth JSON
  (numbers only, no audio bytes) are committed.

## 12. Portability matrix — condensed answer to Issue #5 Task E's platform table

| Platform | BeatNet | CUE-DETR | All-In-One | Essentia |
|---|---|---|---|---|
| Windows x64 | `RUNS_WITH_WORKAROUND` (evidenced, §5.3) | `RUNS_NOW` (evidenced, §6/§7) | `BLOCKED_ENVIRONMENT` (evidenced, §5.2) | `BLOCKED_ENVIRONMENT` (evidenced, §9 code below) |
| macOS Apple Silicon | `UNKNOWN_NEEDS_RUNTIME_PROOF` | `UNKNOWN_NEEDS_RUNTIME_PROOF` | `UNKNOWN_NEEDS_RUNTIME_PROOF` (upstream claims auto-install) | `UNKNOWN_NEEDS_RUNTIME_PROOF` |
| Linux | `UNKNOWN_NEEDS_RUNTIME_PROOF` | `UNKNOWN_NEEDS_RUNTIME_PROOF` | `UNKNOWN_NEEDS_RUNTIME_PROOF` (upstream claims a prebuilt NATTEN wheel path) | `UNKNOWN_NEEDS_RUNTIME_PROOF` |
| Android/iOS | `SOURCE_ONLY_INSPECTED` — no export path; DBN/particle-filter post-processing would need reimplementation | `SOURCE_ONLY_INSPECTED` — standard DETR/HF stack has plausible ONNX paths, not attempted | `SOURCE_ONLY_INSPECTED` — NATTEN custom kernels have no documented mobile export path | `SOURCE_ONLY_INSPECTED` — C++ core has historical native-mobile precedent, not verified this pass |

No platform beyond Windows x64 was actually tested this pass (only one
machine was available) — every non-Windows cell above is honestly
`UNKNOWN_NEEDS_RUNTIME_PROOF`, not inferred as passing.

## 13. Negative baseline results — condensed (also see §4)

| Baseline | FIX-B (phase offset) `COND_BEAT_OK` rate | FIX-H (variable tempo) `COND_BEAT_OK` rate | Downbeat/meter/cue/phrase/section output |
|---|---|---|---|
| scalar-BPM theoretical grid | 0.0 | 0.125 | None (all null by construction) |
| fixed-32-beat phrase proxy | N/A (phrase-only) | N/A | 2 spurious boundaries on FIX-F's 4-boundary ground truth |
| energy/onset heuristic | N/A (no beat model) | N/A | RMS-threshold cue candidates + coarse 3-level energy segmentation only |

## 14. Known limitations of this pass's own methodology (disclosed, not hidden)

1. `exact_bar_phase_accuracy` as implemented does not independently
   penalize a wrong *meter* — it only checks whether some predicted
   position-1 marker is near each true downbeat, which can look
   misleadingly good under a meter that's an even divisor of the truth
   (§6.2). `meter_correct` is the metric that actually catches this, and
   both are reported together specifically to avoid this trap.
2. `phrase_boundary_distance`/`section_boundary_distance` (ground-truth
   -> nearest-prediction) does not penalize spurious *extra* predicted
   boundaries (§4 item 2) — a real limitation for evaluating
   over-segmentation, disclosed rather than silently accepted as a clean
   result.
3. `energy_onset_heuristic`'s section-proxy label vocabulary
   (`low/mid/high_energy`) was not reconciled with FIX-F's
   named-section vocabulary (`intro/verse/chorus/outro`), so no
   section-boundary score was computed for it against FIX-F (§8) —
   scope gap, not a hidden failure.
4. `peak_memory_mb` uses Python-level `tracemalloc`, which does not
   capture PyTorch's C++-level tensor allocations — the reported
   28–186 MB figures materially understate true process memory use for
   both BeatNet and CUE-DETR. Flagged as a measurement-tooling
   limitation, not corrected this pass (would need an OS-level RSS
   sampler instead).
5. FIX-F's percussive "kick" layer does not accent beat 1 differently
   from other beats (unlike FIX-A/B/C/D/G), which likely contributed to
   its `exact_bar_phase_accuracy=0.0` result (§6.2) — a fixture design
   gap in this pass, disclosed as a caveat on that specific result rather
   than attributed purely to BeatNet.
6. Only one machine/platform (Windows x64) was available this pass — the
   entire macOS/Linux/mobile portability matrix (§12) is `INFERENCE`
   from upstream documentation, never independently verified.

## 15. Acceptance criteria matrix (Issue #5)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| AC1 | Pinned revisions respected or deviations justified | PASS | §2 table; all 4 candidates' code revisions match exactly; dependency-level deviations (numba, matplotlib) are explicit and evidenced (§5.3, §9) |
| AC2 | Code license and checkpoint/dataset license treated separately | PASS | `docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md`, every candidate has separate `Code license`/`Checkpoint license`/`Dataset license` rows |
| AC3 | No unlicensed checkpoint/data silently promoted to production | PASS | License matrix §1–4: every production-evaluation verdict is `UNKNOWN_NEEDS_LEGAL_REVIEW` or worse; nothing was marked `CLEAR_FOR_PRODUCTION_EVALUATION` |
| AC4 | At least one real analyzer candidate actually executed, not README-only | PASS | §6/§7 — BeatNet and CUE-DETR both actually executed, 16/16 real runs `OK`; raw JSON committed under `results/raw/` |
| AC5 | Negative BPM/fixed-phrase baselines actually executed | PASS | §4 — all 3 required baselines executed on all 8 fixtures, 24/24 `OK` |
| AC6 | Beat-awareness measured using explicit timestamps, not inferred from BPM only | PASS | §6.1 — `beat_timestamps_ms` compared directly against `SYNTHETIC_EXACT` ground-truth timestamps, per-fixture |
| AC7 | Downbeat/bar correctness evaluated separately from beat correctness | PASS | §6.2 — separate `meter_correct`/`exact_bar_phase_accuracy` metrics reported alongside, not merged with, §6.1's beat metrics; the metric-artifact caveat is itself evidence this separation was taken seriously |
| AC8 | Phrase/section/cue concepts not conflated | PASS | `common/schema.py` keeps 3 distinct fields; §8 states explicitly no field is reported as another |
| AC9 | Synthetic exact ground truth used for deterministic timing tests | PASS | `fixtures/manifest.json`, every fixture's `ground_truth` computed by closed-form construction (`generate_fixtures.py`), `provenance=SYNTHETIC` |
| AC10 | Runtime/platform constraints measured or explicitly blocked with evidence | PASS | §5/§12 — every candidate has either measured numbers or an evidenced blocker command+output |
| AC11 | Outputs normalized into a reproducible comparison format | PASS | `common/schema.py`'s `AnalyzerResult`, used identically by every baseline and candidate runner |
| AC12 | No protected/copyrighted audio, credentials, cookies, tokens committed | PASS | §11; `.gitignore` excludes all audio/checkpoints; verified via `git status`/`git diff --stat` before commit (§ handoff) |
| AC13 | No GPL/AGPL code copied into prospective production core | PASS | Nothing under `tools/p0m3/` is production core (P0 scope only); baselines are original implementations; Essentia (AGPL) was never installed |
| AC14 | Lane-specific decisions are evidence-backed | PASS | §9 table, each decision cites its evidence section |
| AC15 | Smallest-composite-stack recommendation produced | PASS | §9.1 |
| AC16 | P1 production engine not started | PASS | §11 |
| AC17 | Signalsmith/Rubber Band not started this pass | PASS | §11 |

## 16. Unknowns / risks

- BeatNet's and CUE-DETR's behavior on **real musical material** (as
  opposed to synthetic clicks/tones) is unverified — both candidates'
  results here are, honestly, floor-level smoke evidence for the
  pipeline mechanics plus one genuinely strong quantitative result
  (BeatNet's beat-phase robustness, §6.1). A follow-up pass needs at
  least one legally-clear (CC0/public-domain/owner-created) real-music
  fixture.
- All-In-One and Essentia remain fully unexecuted this pass; their real
  quality is still `SOURCE_ONLY_INSPECTED`-level knowledge only.
- Every candidate's training-audio provenance/rights chain is an
  unresolved `UNKNOWN_NEEDS_LEGAL_REVIEW` (license matrix §5) — this is
  a real, structural risk across the whole cue/structure candidate
  space, not specific to one candidate.
- macOS/Linux/mobile portability claims in §12 are entirely
  `INFERENCE` from upstream docs, never independently verified this pass.
- The `exact_bar_phase_accuracy` metric limitation (§14 item 1) means any
  future automated gate built on this pass's metrics.json must use
  `meter_correct`, not `exact_bar_phase_accuracy` alone, to judge
  downbeat/meter quality.

## 17. PM review request

Please independently verify:

1. `git log` on `research/p0-feasibility` shows this task's commit(s) as
   the new `HEAD`, and `git diff --stat` against the prior head
   (`d2601328ea2d4f3abc1e30b2791d728e1c31c33d`) touches only
   `docs/research/P0-M3-R1-*.md`, `tools/p0m3/analyzer_shootout/**`, and
   (if applicable) `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md` —
   no engine/production files.
2. `tools/p0m3/analyzer_shootout/results/all_raw.json` — spot-check that
   `run_state="OK"` entries for `beatnet` and `cue_detr` contain non-null
   `beat_timestamps_ms`/`cue_points_ms` respectively (real output, not
   stubs).
3. `docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` §1–§4 — confirm
   the `UNKNOWN_NEEDS_LEGAL_REVIEW` production verdicts are acceptable as
   the closing state for this pass (no candidate was upgraded to
   production-clear).
4. §6.2's downbeat/meter finding (systematic meter=2 misclassification
   on all 8 fixtures) — confirm this reads as an honest negative result
   requiring follow-up, not as a disguised failure to deliver AC7.
5. `tools/p0m3/analyzer_shootout/README.md`'s "What was NOT executed and
   why" section — confirm the All-In-One/Essentia blockers are
   acceptable evidence quality for this pass's `PARTIAL` result.
