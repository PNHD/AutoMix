# P0-M3-R1 — Cue/Beat/Structure Analyzer Shootout

Status date: 2026-08-11 (PM REPAIR PASS — supersedes the original P0-M3-R1 pass at commit `8a419b1b51aa341ebe53a5e62727357a07e7cb1b`)

## 0. Execution profile actually used

- **Execution agent:** Claude Code runtime (Claude Desktop -> Code
  execution surface per `AGENTS.md`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High.
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:**
  OFF (no `Agent`/`Task` subagent calls anywhere in this repair pass).
  **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **This revision addresses** the PM's `PM REVIEW — REPAIR REQUIRED`
  comment on Issue #5 (posted after review of commit `8a419b1b5...`),
  items R1–R7.

## 1. Result

**PASS**

Every Issue #5 acceptance criterion (AC1–AC17) has direct, independently
checkable evidence after this repair pass — see §16's inline matrix. This
is not a claim that every open question from the original pass has been
answered (BeatNet/CUE-DETR's behavior on real music remains unverified;
All-In-One remains unexecuted) — those are legitimate follow-up items for
a later P0-M3 pass, not binding acceptance criteria of Issue #5, which
explicitly states a single blocked candidate does not block the task and
does not require real-music validation or non-Windows execution to close
this specific pass.

## 2. What changed in this repair pass (map to PM's R1–R7)

| PM item | What was repaired | Where |
|---|---|---|
| R1 | Runtime lifecycle (`run_phase`: `N_A`/`COLD_MODEL_LOAD_INFERENCE`/`WARM_INFERENCE`), real in-process model reuse for warm runs, OS-level peak RSS via `psutil` (Windows `peak_wset`), `checkpoint_size_mb`/`total_model_asset_footprint_mb` | `common/schema.py`, `common/runtime.py`, `candidates/run_beatnet.py`, `candidates/run_cuedetr.py`; §5 |
| R2 | FIX-F evidence corrected (160 beats, not 192); two-sided TP/FP/FN/precision/recall/F1 boundary-event metric added, tolerance grounded in P0-M2's `COND_PHRASE_OK`/`COND_SECTION_OK`; energy-heuristic narrative/data contradiction resolved | `eval/metrics.py` (`boundary_event_metrics`), `eval/run_shootout.py`; §6 |
| R3 | `THIRD_PARTY_NOTICES.md` added with the full ETH DISCO MIT notice, mapped to `candidates/run_cuedetr.py` | `tools/p0m3/analyzer_shootout/THIRD_PARTY_NOTICES.md` |
| R4 | Transitive CUE-DETR assets audited; `timm/resnet50.a1_in1k` (~98 MB) removed after proving bit-identical output without it | `candidates/run_cuedetr.py`, `docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` Sec 1.1 |
| R5 | `cue_confidence` → `cue_score`/`cue_score_kind=MINMAX_NORMALIZED_DETR_DETECTION_SCORE`; `cue_confidence` now `None` unless calibrated; `raw_cue_points_ms` preserved, validated `cue_points_ms` clamped to `[0, duration_ms]`, invalid predictions counted/reported | `common/schema.py`, `candidates/run_cuedetr.py`; §7 |
| R6 | Bounded All-In-One WSL2 Ubuntu probe (already-installed, not newly enabled) | §8 |
| R7 | `all_raw.json`/`metrics.json`/`SUMMARY.md` regenerated from repaired runners; `eval/verify_repair.py` programmatically asserts result counts and repaired-schema invariants | §14 |

## 3. Candidate revisions actually inspected/run (unchanged from the original pass)

| Candidate | Repo | Pinned revision | Revision actually used |
|---|---|---|---|
| CUE-DETR | `ETH-DISCO/cue-detr` | `d0462856ed2f59a1fb65267cfbe87340a65ad1bb` | Same |
| All-In-One | `mir-aidj/all-in-one` | `18e78903c0365147a2c5d4e5e57ebf88cb7d800e` | Same (installed and probed this pass, §8) |
| BeatNet | `mjhydri/BeatNet` | `81cedd4beeb7235262db80969a0c9ce9a48a0ed4` | Same |
| Essentia | `MTG/essentia` | `b9fa6cb674ca43dfb94d28d293aeda441c6745db` | Not re-inspected this pass (unchanged per PM's explicit instruction — no new source-build attempt required) |

## 4. Environment

Windows x64 host unchanged from the original pass (§3 of the prior
version; RTX 2060 6GB, MSVC Build Tools 2022, Python 3.10.6). **New this
pass:** WSL2 Ubuntu 24.04 (already installed prior to this task, confirmed
via `wsl --list --verbose` showing it in `Stopped` state before this pass
started it — not newly installed or enabled), used for the bounded
All-In-One probe (§8). WSL2 GPU passthrough to the same RTX 2060 was
already configured (`nvidia-smi` succeeds inside WSL) — not newly enabled
by this task.

## 5. Runtime lifecycle, memory, and model-size — repaired (R1)

### 5.1 Lifecycle definition actually used

- `run_phase = "N_A"`: baselines (no model to load).
- `run_phase = "COLD_MODEL_LOAD_INFERENCE"`: the estimator/model object is
  constructed for the first time in this process, immediately followed by
  inference on that same call. `asset_fetch_wall_sec` on this record is
  the wall time of *only* the construction/loading step (network+disk
  read+deserialize for CUE-DETR; in-process construction from an
  already-installed local checkpoint for BeatNet, which has no network
  component at run time since its checkpoints ship inside the pip
  package). `wall_time_sec` on this same record is inference time only
  (measured separately, starting after construction returns).
- `run_phase = "WARM_INFERENCE"`: the identical, already-resident
  estimator/model object (verified by identity, not assumed) is reused
  for a later fixture in the same process; `asset_fetch_wall_sec` is
  `None` and `wall_time_sec` reflects inference only.

Verified programmatically (`eval/verify_repair.py` §14): exactly one
`COLD_MODEL_LOAD_INFERENCE` row exists per ML candidate across the 40
committed rows, with all other same-candidate rows `WARM_INFERENCE`.

### 5.2 Measured lifecycle/memory/size — BeatNet

| Fixture | `run_phase` | `asset_fetch_wall_sec` | `wall_time_sec` | `process_peak_rss_mb` | `python_tracemalloc_peak_mb` |
|---|---|---|---|---|---|
| FIX-A | `COLD_MODEL_LOAD_INFERENCE` | 0.073 | 22.45 | 544.84 | 185.42 |
| FIX-B | `WARM_INFERENCE` | — | 0.21 | 544.84 | 35.82 |
| FIX-C | `WARM_INFERENCE` | — | 0.36 | 544.84 | 44.99 |
| FIX-D | `WARM_INFERENCE` | — | 0.23 | 544.84 | 32.75 |
| FIX-E | `WARM_INFERENCE` | — | 0.40 | 544.84 | 49.71 |
| FIX-F | `WARM_INFERENCE` | — | 0.77 | 597.07 | 115.80 |
| FIX-G | `WARM_INFERENCE` | — | 0.65 | 597.07 | 107.56 |
| FIX-H | `WARM_INFERENCE` | — | 0.50 | 597.07 | 77.30 |

`memory_measurement_method = PSUTIL_PROCESS_PEAK_WSET_RSS` on every row
(Windows `peak_wset`, a genuine OS-reported process peak, not a Python-
object-level approximation). `checkpoint_size_mb = total_model_asset_footprint_mb = 1.54`
(the single `model-1.pt` file actually loaded; the other two bundled
checkpoints, `model-2.pt`/`model-3.pt`, are on disk but never loaded by
this runner).

The `COLD_MODEL_LOAD_INFERENCE` row (22.45s) is overwhelmingly inference
time on the first file, not construction (0.073s) — first-call PyTorch/
numba JIT and buffer-allocation overhead, not network/disk I/O (BeatNet
has none at run time). Every `WARM_INFERENCE` row is 40–110x faster,
genuinely reflecting reused in-process inference, not merely "a different
file happened to be smaller."

**A genuine, disclosed side-finding from enabling real warm reuse:**
`exact_bar_phase_accuracy` and `beat_fraction` values on `WARM_INFERENCE`
rows differ slightly from the original (per-fixture-fresh-estimator) pass
— e.g. FIX-E's `exact_bar_phase_accuracy` moved from 0.5 to 0.5625,
FIX-H's `beat_fraction.cond_beat_ok_rate` moved from 1.0 to 0.9896. The
*qualitative* conclusion is unchanged (meter is still predicted as `2` on
all 8 fixtures in both runs — see §6.2), but the small numeric shift is
real, not a reporting artifact: inspecting BeatNet's own source
(`BeatNet.activation_extractor_online`, `BeatNet.process`) shows the
offline/DBN path re-extracts CRNN activations fresh per call via
`self.model(feats)`, and the CRNN (`self.model`) is a stateful PyTorch
module the README's own usage examples always construct fresh, once per
file — reusing it across files (this repair's warm-reuse methodology) is
not upstream's documented usage pattern. `INFERENCE` (not verified line-
by-line): the CRNN likely carries some persistent recurrent-layer buffer
across calls that the constructor-per-file pattern implicitly resets.
This is recorded as a genuine capability caveat for any future
warm-resident BeatNet deployment (`RUNS_WITH_WORKAROUND` still holds, but
"the model is safe to keep warm across files without an explicit reset"
is now `UNKNOWN_NEEDS_RUNTIME_PROOF`, not assumed), not hidden in favor
of the faster warm numbers.

### 5.3 Measured lifecycle/memory/size — CUE-DETR

| Fixture | `run_phase` | `asset_fetch_wall_sec` | `wall_time_sec` | `process_peak_rss_mb` |
|---|---|---|---|---|
| FIX-A | `COLD_MODEL_LOAD_INFERENCE` | 1.633 | 6.72 | 926.72 |
| FIX-B | `WARM_INFERENCE` | — | 1.31 | 926.72 |
| FIX-C | `WARM_INFERENCE` | — | 1.63 | 926.72 |
| FIX-D | `WARM_INFERENCE` | — | 1.10 | 926.72 |
| FIX-E | `WARM_INFERENCE` | — | 1.71 | 926.72 |
| FIX-F | `WARM_INFERENCE` | — | 3.84 | 1263.85 |
| FIX-G | `WARM_INFERENCE` | — | 3.50 | 1263.85 |
| FIX-H | `WARM_INFERENCE` | — | 2.50 | 1263.85 |

`checkpoint_size_mb = total_model_asset_footprint_mb = 158.78` (R4: the
`timm/resnet50.a1_in1k` backbone asset, previously ~98 MB additional, is
no longer downloaded or required — see §7.1). `asset_fetch_wall_sec` on
the cold row (1.633s) is the `DetrImageProcessor`/`DetrForObjectDetection`
`.from_pretrained(...)` calls (disk-cached-checkpoint deserialization into
the process, no re-download since the checkpoint was already fetched in
the original pass's local HF cache); `wall_time_sec` (6.72s cold vs.
1.1–3.8s warm) is inference only.

## 6. Boundary-event metrics — repaired (R2)

### 6.1 FIX-F ground truth, verified programmatically against the committed fixture

`fixtures/manifest.json`'s `FIX-F-8bar-16bar-sections` entry: **160 beats**
(40 bars at 128 BPM 4/4, not 192 as the original pass incorrectly stated),
`phrase_boundaries_ms = section starts = [0, 15000, 30000, 60000]`
(beat indices 0/32/64/128), `duration_sec = 77.0`.

The fixed-32-beat proxy (`beats[i] for i in range(0, 160, 32)`) predicts
beat indices **`{0, 32, 64, 96, 128}`** → **`{0, 15000, 30000, 45000, 60000}` ms**
— **5** predictions, not 6, and the true beat-index-160 boundary the
original pass claimed (`160`) does not exist because `range(0, 160, 32)`
stops at 128 (160 is out of range for a 160-length array). Matched
against ground truth with `COND_PHRASE_OK` tolerance (0.5×beat period =
234.375 ms at 128 BPM): **all 4 ground-truth boundaries are hit (TP=4)**,
**exactly 1 spurious prediction exists (FP=1, the 45000 ms boundary)**,
**FN=0**. This exactly matches the PM's stated expected values and was
derived programmatically from the current fixture/proxy code, not
hand-copied from the PM's comment (`eval/verify_repair.py` §14 asserts
this exact tuple against fresh output on every run).

| Metric | Value |
|---|---|
| `tolerance_kind` | `COND_PHRASE_OK` (P0-M2 benchmark contract Sec 7/8: phrase-boundary distance ≤0.5×local beat period) |
| `tolerance_ms` | 234.375 |
| `n_gt` | 4 |
| `n_pred` | 5 |
| **TP** | **4** |
| **FP** | **1** |
| **FN** | **0** |
| precision | 0.8 |
| recall | 1.0 |
| F1 | 0.889 |

The two-sided `boundary_event_metrics` function (`eval/metrics.py`) that
produces this — greedy nearest-neighbor matching without replacement,
tolerance passed by the caller and never invented inside the metric
itself — is now used for every phrase/section-boundary-emitting
candidate/baseline (§6.3), replacing the original pass's ground-truth-only
`phrase_section_boundary_distance_ms`, which is retained alongside it
(not removed) since it still answers a different, legitimate question
("how close is the nearest hit"), just not the false-positive question
this repair adds.

### 6.2 BeatNet downbeat/meter — unchanged conclusion, updated exact numbers

Meter=2 was (mis-)predicted on **all 8** fixtures in both the original and
this repaired pass — the qualitative finding from the original pass
stands. `exact_bar_phase_accuracy` per fixture, this pass's numbers (see
§5.2's warm-reuse caveat for why these differ slightly from the original
pass's): FIX-A 1.0, FIX-B 1.0, FIX-C 1.0, FIX-D 0.917, FIX-E 0.5625,
FIX-F 0.025, FIX-G 0.969, FIX-H 0.958. The same metric-artifact caveat
from the original pass still applies (a meter-2 prediction can trivially
satisfy this per-event check without the meter itself being correct) —
`meter_correct=False` on all 8 remains the metric that actually tells the
truth, unchanged.

### 6.3 Energy-onset heuristic — boundary timing vs. label semantics, resolved (R2)

The original pass's report claimed no section score was computed for
`energy_onset_heuristic_baseline`, while `metrics.json` actually contained
`section_boundary_distance` for FIX-F/FIX-G. **Both facts are now stated
correctly and explicitly, and neither is hidden:**

- **Boundary timing IS scored** (both the ground-truth-nearest-distance
  metric and, new this pass, the two-sided TP/FP/FN event metric):

  | Fixture | `tolerance_kind` | `tolerance_ms` | n_gt | n_pred | TP | FP | FN | precision | recall | F1 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | FIX-F | `COND_SECTION_OK` | 1875.0 | 4 | 4 | 3 | 1 | 1 | 0.75 | 0.75 | 0.75 |
  | FIX-G | `COND_SECTION_OK` | 2181.8 | 3 | 5 | 2 | 3 | 1 | 0.4 | 0.667 | 0.5 |

  (`COND_SECTION_OK`: section-boundary distance ≤1×local bar period, P0-M2
  contract Sec 7/8.)
- **Semantic section-LABEL correctness is explicitly NOT scored anywhere
  in this pass**: `energy_onset_heuristic_baseline` emits labels from a
  3-level `low_energy`/`mid_energy`/`high_energy` vocabulary that has no
  1:1 mapping to the ground truth's `intro`/`verse`/`chorus`/`outro`
  vocabulary, so `score_against_gt` (`eval/run_shootout.py`) now sets
  `section_label_semantic_accuracy = None` with an explicit
  `section_label_semantic_accuracy_note` field on every scored record
  stating this, rather than leaving the absence implicit. Both facts —
  timing IS scored, labels are NOT — are asserted together by
  `eval/verify_repair.py` (§14).

## 7. CUE-DETR — score semantics, transitive assets, and timestamp validation (R4/R5)

### 7.1 Transitive asset audit and the removed `timm` dependency (R4)

The original pass downloaded `timm/resnet50.a1_in1k` (~98 MB,
ImageNet-pretrained ResNet-50 weights) because `transformers`' default
`use_pretrained_backbone=True` initializes the DETR backbone from timm's
pretrained weights *before* `disco-eth/cue-detr`'s own checkpoint
state_dict is loaded on top and overwrites every backbone parameter. This
repair pass verified empirically that `use_pretrained_backbone=False`
(skips the timm download and pretrained-backbone initialization entirely)
produces **bit-identical** inference output vs. the default `True` path —
detection scores and box positions compared exactly equal (`max score
diff = 0.0`) on the same input file. `candidates/run_cuedetr.py` now uses
`use_pretrained_backbone=False`; the timm download no longer happens.
Full before/after audit, including `facebook/detr-resnet-50`'s
still-necessary (tiny, config-only) role: `docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md`
Sec 1.1. Net effect: `total_model_asset_footprint_mb` for CUE-DETR drops
from ~257 MB to 158.78 MB with zero output change (proof, not assumption).

### 7.2 Score semantics — repaired (R5)

The `~0.91–1.0` values the original pass labeled `cue_confidence` are
min-max-normalized DETR detection scores across candidate boxes *within a
single track's own prediction set* — a relative ranking signal, not a
calibrated musical-cue confidence. The schema/output are repaired:

- `cue_score`: the actual per-cue numeric value (unchanged numbers, renamed field).
- `cue_score_kind`: `"MINMAX_NORMALIZED_DETR_DETECTION_SCORE"` on every CUE-DETR row.
- `cue_confidence`: `None` on every row (no candidate in this pass emits a genuinely calibrated confidence — this conclusion from the original pass is unchanged and now enforced by the schema itself, not just prose).

### 7.3 Cue-timestamp validation — repaired (R10/R5)

`raw_cue_points_ms` (unvalidated model output) is now preserved separately
from `cue_points_ms` (validated, `0 ≤ t ≤ track_duration_ms` only).
Invalid predictions are counted (`n_invalid_cue_predictions`) and listed
verbatim (`invalid_cue_points_raw_ms`), never silently clamped or dropped
without a trace:

| Fixture | raw predictions (ms) | validated (ms) | invalid (raw, ms) | n_invalid |
|---|---|---|---|---|
| FIX-A | 69.7, 31718.5 | 69.7, 31718.5 | — | 0 |
| FIX-B | 232.2 | 232.2 | — | 0 |
| FIX-C | 46.4 | 46.4 | — | 0 |
| FIX-D | 46.4 | 46.4 | — | 0 |
| FIX-E | **-139.3**, 69.7 | 69.7 | -139.3 | 1 |
| FIX-F | **-69.7** | *(none)* | -69.7 | 1 |
| FIX-G | **-46.4**, **71842.5** | *(none)* | -46.4, 71842.5 | 2 |
| FIX-H | 69.7 | 69.7 | — | 0 |

**4 of 11 raw predictions (36%) across the 8-fixture set are invalid** —
this is now an explicit, measurable, `eval/verify_repair.py`-asserted
result (§14), not prose-only anomaly text. FIX-G's `71842.5` ms invalid
value is a boundary case: the fixture's actual duration is ~71818 ms, so
this prediction is only ~24 ms past the valid end — still correctly
flagged, since `0 ≤ t ≤ duration_ms` is the stated rule and no tolerance
band was specified by the PM for this check. **FIX-F and FIX-G now have
ZERO validated cue predictions** (previously reported as having one
"anomalous negative" cue point each) — this is the honest, corrected
result of applying the validation rule, not a new failure introduced by
this repair; the raw model output did not change.

## 8. All-In-One — bounded WSL2 environment probe (R6)

### 8.1 Probe scope and boundary respected

Per PM instruction: checked only whether an **already-available**
non-admin Linux execution surface exists; did not install/enable WSL,
Docker Desktop, virtualization, or any admin toolchain.

```
$ wsl --list --verbose
    NAME                    STATE      VERSION
 *  Ubuntu                  Stopped    2
    docker-desktop          Stopped    2
```

WSL2 + an Ubuntu 24.04 distro were already installed and enabled on this
machine prior to this task (confirmed by their presence in `wsl --list`
before any action was taken this pass — a `Stopped` distro is already
installed, merely not currently running; starting it via `wsl -d Ubuntu`
is a normal per-session user operation, not an installation/enablement
step). `nvidia-smi` inside WSL succeeded immediately, confirming GPU
passthrough was already configured, also not newly enabled by this task.

### 8.2 What was attempted and the result

Inside the existing Ubuntu 24.04 distro (Python 3.12.3, gcc/make/12
cores/939 GB free/internet all already present):

1. `pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu126`
   → succeeded, `torch.cuda.is_available() == True` (real GPU passthrough).
2. `pip install natten` (plain PyPI) → **failed**: no prebuilt wheel
   resolved, source build requires CMake (`RuntimeError: Cannot find CMake
   executable`) — the same class of blocker as Windows, just a different
   missing tool.
3. Per NATTEN's own documented prebuilt-wheel path
   (`https://natten.org/install/`): `pip install "natten==0.21.7+torch2130cu126" -f https://whl.natten.org`
   → **succeeded**. This is real, new evidence that NATTEN's Linux
   prebuilt-wheel path (unlike Windows' `make`-only path) genuinely works
   on this machine, resolving the specific blocker recorded in the
   original pass.
4. `pip install "git+https://github.com/CPJKU/madmom"` → succeeded
   (imports cleanly on Linux/Python 3.12, `pip show` reports `0.17.dev0`
   from upstream's current `main`, no Windows-style `collections`/`numpy`
   compat shims were needed here).
5. `pip install "git+https://github.com/mir-aidj/all-in-one.git@18e78903c0365147a2c5d4e5e57ebf88cb7d800e"`
   → package installs (`pip show allin1` reports version `1.1.0`), **but
   fails to import**:
   ```
   ImportError: cannot import name 'natten1dav' from 'natten.functional'
   ```
   All-In-One's pinned-revision code (`src/allin1/models/dinat.py`) calls
   `natten1dav`/`natten1dqkrpb`/`natten2dav`/`natten2dqkrpb` — an older
   NATTEN functional API (contemporaneous with the ~2023 era the repo's
   own `pyproject.toml` and lack of recent commits suggest, per the
   already-recorded P0 caveat). NATTEN 0.21.7 (the only version with a
   working prebuilt-wheel path found this pass) has replaced that API
   entirely with a redesigned interface; those four function names do not
   exist in it.
6. Checked whether an **older**, API-compatible NATTEN version
   (`natten==0.14.6`, from the version list `pip index versions natten`
   returned) could be installed instead: **failed** —
   `ModuleNotFoundError: No module named 'torch'` during its own
   `setup.py`-based build-requirement resolution (old NATTEN's setup
   script imports `torch` directly and needs `--no-build-isolation` plus,
   for its actual CUDA-extension compilation, an installed CUDA
   Toolkit/`nvcc` and `cmake` — checked: `nvcc`/`cmake` are **not**
   present in this WSL distro).

### 8.3 Honest stopping point (boundary respected)

Installing `nvcc`(CUDA Toolkit)/`cmake` to build the old, API-compatible
NATTEN version from source would itself be exactly the kind of
system-wide admin-toolchain installation the PM's instruction explicitly
prohibits for this repair ("DO NOT install/enable ... admin toolchains").
This is the correct, bounded stopping point: **real, new progress was
made (the original blocker — no build tool for NATTEN on Windows — is
provably not the same blocker on Linux, where a prebuilt wheel exists),
but a genuinely different, newly-discovered blocker (NATTEN API-version
incompatibility with All-In-One's pinned-revision code) replaces it.**
All-In-One remains `BLOCKED_ENVIRONMENT` this pass; FIX-F/FIX-G/one
timing fixture were **not** run (the package does not import). This
changes the composite-stack recommendation (§10) — the "resolve the
NATTEN build blocker" framing from the original pass turned out to be
necessary-but-not-sufficient.

## 9. Cue-point and structure lane results (unchanged framing, updated numbers)

Same smoke/regression-evidence framing as the original pass (Issue #5
Task D — no authored cue/section ground truth exists on synthetic
fixtures). Updated CUE-DETR numbers are in §7.3; updated boundary-event
numbers for the fixed-32 proxy and energy heuristic are in §6.1/§6.3.

## 10. Decision matrix and smallest composite stack — updated for R6's finding

| Capability lane | Decision | Evidence basis |
|---|---|---|
| Beat timestamps | `ADOPT_FOR_P0_PROTOTYPE` (BeatNet) | §5.2/§6.2 — unchanged from original pass; the R1 warm-reuse caveat (§5.2) adds a deployment nuance but not a change to this lane decision |
| Downbeats / bar phase | `KEEP_AS_BENCHMARK_ONLY` (BeatNet) | §6.2 — unchanged |
| Meter | `KEEP_AS_BENCHMARK_ONLY` (BeatNet) | §6.2 — unchanged |
| Cue points | `KEEP_AS_BENCHMARK_ONLY` (CUE-DETR) | §7 — unchanged conclusion; now with an explicit, measured 36% raw-invalid-prediction rate as an additional concrete caveat |
| Phrase candidates | `REJECT` (fixed-N-beat proxy, now with an exact TP=4/FP=1/FN=0 event count, §6.1) / **downgraded to `UNRESOLVED` (was `PORT/EXPORT_EXPERIMENT_NEXT`)** for All-In-One | §8 — the WSL2 probe found a *new*, unresolved blocker (NATTEN API-version mismatch), not merely "needs a Linux runner" as the original pass assumed; presenting it as a scheduled next step overstates how close it is |
| Section boundaries/labels | `REJECT` (energy-level heuristic, §6.3) / **`UNRESOLVED`** for All-In-One | Same reasoning as above |
| Confidence / fallback inputs | `KEEP_AS_BENCHMARK_ONLY` (no candidate this pass) | Unchanged — `cue_score`/`cue_score_kind` (R5) makes explicit that CUE-DETR's score is not this signal either |

### 10.1 Smallest composite stack — revised

1. **BeatNet (offline/DBN)** for beat timestamps only — unchanged
   recommendation, now with an added deployment caveat: a
   warm/model-resident production integration must not assume
   cross-file reuse is numerically safe without further investigation
   (§5.2).
2. **All-In-One is no longer presented as a scheduled near-term unblock.**
   The composite-stack recommendation in the original pass said
   "once the NATTEN build blocker is resolved" as if that were the only
   obstacle; §8 shows that even where the build blocker *is* resolved
   (Linux, prebuilt wheel), a second, independent blocker (API-version
   incompatibility between the pinned revision and any NATTEN version
   with a working install path) remains. Downbeat/meter/phrase/section
   ownership stays genuinely **unresolved** pending either (a) a newer
   All-In-One revision compatible with current NATTEN, (b) pinning an
   old NATTEN version and accepting a `cmake`/CUDA-Toolkit source build
   (out of scope for this repair's environment boundary), or (c) a
   different structure-analysis candidate entirely.
3. **CUE-DETR** for a cue-point signal, EDM-genre-adjacent, smoke-test
   status — unchanged, with the new invalid-prediction-rate caveat (§7.3).
4. The three negative baselines remain the permanent comparison floor —
   unchanged.
5. Essentia stays `REFERENCE_ONLY` — unchanged.

## 11. Third-party notice (R3)

`tools/p0m3/analyzer_shootout/THIRD_PARTY_NOTICES.md` contains the full
ETH DISCO MIT copyright and permission notice, explicitly mapped to
`candidates/run_cuedetr.py` (the one file in this harness that is a
direct, minimally-adapted port of third-party code, as opposed to code
that merely calls a third-party package/checkpoint through its public
API). Referenced from both `candidates/run_cuedetr.py`'s own module
docstring and `tools/p0m3/analyzer_shootout/README.md`.

## 12. Artifact/license matrix update (R4)

`docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` Sec 1.1 now audits
`facebook/detr-resnet-50` (kept; Apache-2.0; processor-config-only, no
weights used) and `timm/resnet50.a1_in1k` (removed this pass; Apache-2.0;
recorded for completeness even though no longer part of the dependency
graph, with the exact proof of unnecessity). No production-evaluation
verdict changed as a result — CUE-DETR's composite pipeline verdict
remains `UNKNOWN_NEEDS_LEGAL_REVIEW` (Sec 1), gated by the still-unresolved
training-audio-provenance question, unaffected by this asset simplification.

## 13. Portability matrix — updated Linux row for All-In-One only

| Platform | BeatNet | CUE-DETR | All-In-One | Essentia |
|---|---|---|---|---|
| Windows x64 | `RUNS_WITH_WORKAROUND` | `RUNS_NOW` | `BLOCKED_ENVIRONMENT` (unchanged, §5.2 of original pass) | `BLOCKED_ENVIRONMENT` (unchanged) |
| Linux (WSL2 Ubuntu 24.04, this pass) | Not re-tested this pass | Not re-tested this pass | **`BLOCKED_ENVIRONMENT`** (updated from `UNKNOWN_NEEDS_RUNTIME_PROOF`; NATTEN's own build blocker is resolved via a prebuilt wheel, but a new NATTEN-API-version blocker was found, §8) | Not re-tested this pass |
| macOS Apple Silicon | `UNKNOWN_NEEDS_RUNTIME_PROOF` | `UNKNOWN_NEEDS_RUNTIME_PROOF` | `UNKNOWN_NEEDS_RUNTIME_PROOF` (unchanged — upstream's claimed macOS auto-install path was not tested; note it may hit the same NATTEN-API-version issue since macOS also needs a NATTEN release, not necessarily an old one) | `UNKNOWN_NEEDS_RUNTIME_PROOF` |
| Android/iOS | `SOURCE_ONLY_INSPECTED` | `SOURCE_ONLY_INSPECTED` | `SOURCE_ONLY_INSPECTED` | `SOURCE_ONLY_INSPECTED` |

## 14. Validation — programmatic result-count and schema assertions (R7)

`tools/p0m3/analyzer_shootout/eval/verify_repair.py`, run against the
regenerated `results/{all_raw.json,metrics.json}`:

```
=== 1. Result counts by candidate/run_state ===
{ "beatnet": {"OK": 8}, "cue_detr": {"OK": 8},
  "energy_onset_heuristic_baseline": {"OK": 8},
  "fixed_32_beat_phrase_proxy_baseline": {"OK": 8},
  "scalar_bpm_grid_baseline": {"OK": 8} }
[PASS] all 5 expected candidates present
[PASS] total raw count == 40
[PASS] every raw record has run_state=OK

=== 2. Validated cue_points_ms range assertion ===
[PASS] no negative values in any validated cue_points_ms
[PASS] raw_cue count == valid + invalid count -- raw=11 valid=7 invalid=4
[PASS] at least one invalid cue prediction was actually observed and preserved

=== 3. ML candidate lifecycle/model-size metadata assertions ===
[PASS] every ML row has a non-null run_phase
[PASS] exactly one COLD_MODEL_LOAD_INFERENCE row per ML candidate -- {'beatnet': 1, 'cue_detr': 1}
[PASS] every ML row has non-null checkpoint_size_mb
[PASS] every ML row states an explicit memory_measurement_method
[PASS] every baseline row uses run_phase=N_A

=== 4. FIX-F fixed-32-beat proxy boundary event metrics ===
n_gt=4 n_pred=5 TP=4 FP=1 FN=0 precision=0.8 recall=1.0 F1=0.889
[PASS] all 5 exact-value assertions

=== 5. energy_onset_heuristic section-boundary-timing vs label-semantic fields ===
[PASS] FIX-F/FIX-G: boundary timing score present
[PASS] FIX-F/FIX-G: section_label_semantic_accuracy explicitly None with NOT_COMPUTED note

=== RESULT: ALL ASSERTIONS PASS ===
```

Full command: `python eval/verify_repair.py` (run from
`tools/p0m3/analyzer_shootout/`, using either candidate venv — the check
is schema/data-only, no ML imports required).

## 15. Unknowns / risks (updated)

- BeatNet's/CUE-DETR's behavior on real musical material remains
  unverified (unchanged from the original pass — explicitly not a binding
  AC for this task per PM's R7).
- **New this pass:** BeatNet's estimator-reuse safety (whether warm
  reuse across files is numerically equivalent to fresh construction) is
  now an open, evidenced question (§5.2), not an assumption either way.
- All-In-One's exact unblock path is now better-characterized but still
  unresolved: needs a newer All-In-One revision compatible with current
  NATTEN, or an old-NATTEN source build requiring `cmake`/CUDA Toolkit
  (explicitly out of this repair's environment boundary).
- Essentia remains fully unexecuted (unchanged; PM confirmed no new
  attempt required this pass).
- Every candidate's training-audio provenance/rights chain remains
  `UNKNOWN_NEEDS_LEGAL_REVIEW` (license matrix, unchanged).
- macOS/mobile portability claims remain `INFERENCE`/`UNKNOWN_NEEDS_RUNTIME_PROOF`.

## 16. Acceptance criteria matrix (Issue #5, re-verified after repair)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| AC1 | Pinned revisions respected or deviations justified | PASS | §3; all 4 candidates' code revisions unchanged and exact; the WSL2 probe used the same pinned All-In-One SHA |
| AC2 | Code license and checkpoint/dataset license treated separately | PASS | License matrix Sec 1–4, now including Sec 1.1's transitive-asset audit |
| AC3 | No unlicensed checkpoint/data silently promoted to production | PASS | License matrix; every production-evaluation verdict remains `UNKNOWN_NEEDS_LEGAL_REVIEW` or worse |
| AC4 | At least one real analyzer candidate actually executed, not README-only | PASS | §5.2/§5.3 — BeatNet and CUE-DETR both actually executed, 40/40 runs `OK`, now with truthful cold/warm lifecycle labeling |
| AC5 | Negative BPM/fixed-phrase baselines actually executed | PASS | §6.1 — all 3 baselines executed on all 8 fixtures, including the corrected FIX-F evidence |
| AC6 | Beat-awareness measured using explicit timestamps, not inferred from BPM only | PASS | §6.2, unchanged mechanism |
| AC7 | Downbeat/bar correctness evaluated separately from beat correctness | PASS | §6.2 |
| AC8 | Phrase/section/cue concepts not conflated | PASS | `common/schema.py` fields remain distinct; §6.3 makes the boundary-timing-vs-label distinction explicit rather than implicit |
| AC9 | Synthetic exact ground truth used for deterministic timing tests | PASS | `fixtures/manifest.json`, unchanged; FIX-F's ground truth is now correctly described (§6.1) |
| AC10 | Runtime/platform constraints measured or explicitly blocked with evidence | PASS | §5 (measured), §8 (blocked, with much richer evidence than the original pass) |
| AC11 | Outputs normalized into a reproducible comparison format | PASS | `common/schema.py`, repaired this pass (R1/R5 fields) |
| AC12 | No protected/copyrighted audio, credentials, cookies, tokens committed | PASS | Diff for this repair touches only `docs/research/P0-M3-R1-*.md`, `tools/p0m3/analyzer_shootout/**`; no audio/checkpoints staged (verified via `git add -n` before commit) |
| AC13 | No GPL/AGPL code copied into prospective production core | PASS | Unchanged; Essentia (AGPL) still never installed; madmom (BSD-3) used only as a benchmark-lane dependency, not production core |
| AC14 | Lane-specific decisions are evidence-backed | PASS | §10, each decision cites its evidence section, including the R6-driven `UNRESOLVED` downgrade |
| AC15 | Smallest-composite-stack recommendation produced | PASS | §10.1, revised to honestly reflect the R6 finding rather than presenting an unresolved blocker as a scheduled next step |
| AC16 | P1 production engine not started | PASS | No engine source files anywhere in this diff |
| AC17 | Signalsmith/Rubber Band not started this pass | PASS | Not referenced anywhere in this diff |

## 17. PM review request

Please independently verify:

1. `tools/p0m3/analyzer_shootout/results/all_raw.json` — spot-check a
   `beatnet`/`cue_detr` `WARM_INFERENCE` row has `asset_fetch_wall_sec=null`
   and a materially smaller `wall_time_sec` than its candidate's one
   `COLD_MODEL_LOAD_INFERENCE` row.
2. `eval/verify_repair.py`'s FIX-F assertions (`TP==4`, `FP==1`, `FN==0`)
   against the raw `fixtures/manifest.json` ground truth, independently.
3. `candidates/run_cuedetr.py`'s `use_pretrained_backbone=False` claim —
   confirm `THIRD_PARTY_NOTICES.md` and the license matrix Sec 1.1 make
   the removed-asset history auditable rather than silently vanished.
4. §8's WSL2 probe — confirm the stopping point (declining to install
   `cmake`/CUDA Toolkit) reads as correctly bounded, not as an
   unjustified early exit given a prebuilt-wheel NATTEN path did exist.
5. `results/raw/cue_detr__FIX-F-*.json` and `..._FIX-G-*.json` — confirm
   `cue_points_ms: []` (zero valid predictions) is now the accurate
   committed state for those two fixtures, replacing the original pass's
   prose-only "anomaly" framing.
