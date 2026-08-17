# P0-M3-R3 — RM041 -> RM014 closest-pair evidence stability probe

Status date: 2026-08-17

Binding task: Issue #7 PM comment "PM REVIEW — ALL-IN-ONE REAL EVIDENCE
ACCEPTED; CLOSEST-PAIR STABILITY PROBE NEXT" (comment id `5279667313`).

Starting HEAD: `f0b212939979f5528a00f111b22ff92198e1c544`.

## Result

`PAIR_EVIDENCE_PARTIALLY_STABLE`

Raw evidence for the fixed pair `V2 RM041 -> RM014` is stable on several
independent lanes (BPM, functional-structure label at the accepted
boundary, the RM041/outgoing-exit downbeat grid and its harmonic estimate)
but genuinely unstable on others (the RM014/incoming-entry beat/downbeat
event count and boundary-local downbeat identity, and the RM014-side
harmonic key estimate below the 30-second window). This is not a quality
PASS, not `FULL_DJ_ELIGIBLE`, and not `OWNER_LISTENING_REQUIRED`. No render
was started. The accepted evidence
(`ALL_IN_ONE_REAL_PIPELINE_VALIDATED_RESIDUAL_BLOCKERS`, no quality PASS, no
render candidate) is unchanged; canonical R2 gates, `compatibility.py`,
`select_real_music_pairs.py`, and BeatNet beat ownership are all unchanged.

## Scope

Exactly two private tracks: `RM041`, `RM014`. No other RM id was analyzed.
No 19-track or 100-track corpus rerun. No render, Signalsmith, Rubber Band,
or owner listening pack.

## A1/A2 — All-In-One cross-seed stability

10 real `allin1.analyze` runs total: RM041 and RM014, each at seeds
`0,1,2,3,4`, each in its own process (so `AUTOMIX_DETERMINISTIC_SEED` is
genuinely varied) and its own fresh Demucs/spectrogram scratch directory.
All 10 PASSed on the first attempt — the task's one-diagnostic-retry
allowance was not needed.

### BPM

| Track | Per-seed | Mode | Min | Max |
|---|---|---:|---:|---:|
| RM041 | 103,103,103,103,103 | 103 | 103 | 103 |
| RM014 | 105,105,105,105,105 | 105 | 105 | 105 |

BPM is perfectly stable across every seed for both tracks.

### Beat/downbeat event counts per seed

| Track | seed0 | seed1 | seed2 | seed3 | seed4 |
|---|---:|---:|---:|---:|---:|
| RM041 beats | 317 | 317 | 317 | 317 | 317 |
| RM041 downbeats | 80 | 80 | 80 | 80 | 80 |
| RM014 beats | 356 | 356 | 369 | 368 | 372 |
| RM014 downbeats | 89 | 89 | 92 | 92 | 93 |

RM041's beat/downbeat COUNT is identical across all 5 seeds. RM014's is
NOT — seeds 2/3/4 detect 12-16 more beats and 3 more downbeats than seeds
0/1. This is a genuine, seed-dependent structural difference in the
detected grid, not merely small timing jitter.

### Beat grid — full pairwise (all 10 seed-pairs, bidirectional) and baseline (seed 0 vs. others)

| Track | Stat | Median ms | p90 ms | Max ms | Coverage <=25ms | <=50ms | <=100ms | n |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RM041 | all-pairs | 0.0 | 10.0 | 300.0 | 0.9653 | 0.9751 | 0.9785 | 6340 |
| RM041 | baseline(seed0)-vs-other | 0.0 | 10.0 | 300.0 | 0.9606 | 0.9685 | 0.9708 | 2536 |
| RM014 | all-pairs | 0.0 | 10.0 | 550.0 | 0.9503 | 0.9572 | 0.9668 | 7284 |
| RM014 | baseline(seed0)-vs-other | 0.0 | 10.0 | 500.0 | 0.9553 | 0.9602 | 0.9664 | 2889 |

### Downbeat grid — full pairwise and baseline

| Track | Stat | Median ms | p90 ms | Max ms | Coverage <=25ms | <=50ms | <=100ms | n |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RM041 | all-pairs | 0.0 | 10.0 | 290.0 | 0.9750 | 0.9850 | 0.9850 | 1600 |
| RM041 | baseline(seed0)-vs-other | 0.0 | 10.0 | 290.0 | 0.9750 | 0.9812 | 0.9812 | 640 |
| RM014 | all-pairs | 0.0 | 10.0 | 1770.0 | 0.9505 | 0.9571 | 0.9604 | 1820 |
| RM014 | baseline(seed0)-vs-other | 0.0 | 10.0 | 1770.0 | 0.9584 | 0.9640 | 0.9640 | 722 |

**A median near 0-10 ms does not hide the tail**, exactly as the task
anticipated checking for: max disagreement reaches 290-300 ms on RM041 and
500-1770 ms on RM014, and ~2-4% of events (up to ~5% for RM014 downbeats)
never agree within 100 ms across seeds. RM041's tail is materially
tighter than RM014's.

Full per-seed/per-pair numeric detail:
`tools/p0m3/all_in_one_runtime_probe/pair_stability/results/cross_seed_metrics.json`.

## A3 — Boundary-local downbeat consensus (exact accepted boundary)

Boundary reused verbatim from the accepted
`three_pair_replay_sanitized.json` V2 RM041->RM014 row: RM041 outgoing
exit target `186456.2 ms`, RM014 incoming entry target `0.0 ms`. Not
re-chosen.

### RM041 exit (186456.2 ms)

All 5 seeds agree EXACTLY: nearest beat/downbeat at signed distance
`-16.2 ms`, `position_in_bar=1` (a genuine downbeat), local downbeat
interval `2330.0 ms` on every seed. Comparison against the accepted
madmom benchmark grid (bidirectional): median `0.0 ms`, p90 `0.0 ms`, max
`0.0 ms`, 100% coverage at <=25/50/100 ms (n=10). All-In-One's downbeat
grid at this boundary is in EXACT agreement with the independent madmom
benchmark, on every seed.

### RM014 entry (0.0 ms)

Seeds split into two clusters: seeds 0/1 report nearest beat `+900 ms`,
nearest downbeat `+3580 ms`, local bar duration `3790 ms`; seeds 2/3/4
report nearest beat `+400 ms`, nearest downbeat `~1840-1850 ms`, local bar
duration `~1940-1950 ms`. `position_in_bar=2` is consistent across all 5
seeds (the bar PHASE is stable even though which downbeat is "nearest"
is not). Comparison against the accepted madmom benchmark grid
(bidirectional): median `2010.0 ms`, p90 `2020.0 ms`, max `2020.0 ms`, 0%
coverage at <=25/50/100 ms (n=10) — All-In-One's downbeat estimate at this
boundary disagrees substantially with the independent madmom benchmark on
every seed, consistent with RM014 downbeat evidence being flagged
`INSUFFICIENT`/`STILL_UNKNOWN` in the accepted prior passes.

Full detail: `cross_seed_metrics.json`'s `boundary_local_downbeat_evidence`.

## A4 — Functional structure stability

| Track | Role | Modal label | Label consensus | Same role all 5 seeds | Boundary displacement median/p90/max ms |
|---|---|---|---:|---|---:|
| RM041 | outgoing_exit | `chorus` | 1.0 (5/5) | yes | 4793.8 / 4793.8 / 4793.8 |
| RM014 | incoming_entry | `intro` | 1.0 (5/5) | yes | 0.0 / 0.0 / 0.0 |

Both boundaries land in the SAME functional label on every seed, matching
the accepted seed-0 evidence exactly (`chorus` / `intro`). All labels are
literal `AnalysisResult.segments` output; no phrase claim was made. Full
detail: `structure_consensus.json`.

## A5/A6/A7 — Harmonic window-sensitivity

Reused the existing bounded librosa CQT/Krumhansl methodology
(`wsl_bounded_audio_oracles.py::cqt_key_at`/`_profile_key`, unmodified) and
the existing unmodified `select_real_music_pairs.harmonic_relationship`.
Window lengths `{10, 15, 20, 30}` s x boundary perturbations
`{-1000, -500, 0, +500, +1000}` ms = 20 cells per side. Entry-side cells
whose window would start before the track (perturbations -1000/-500 ms at
a 0 ms accepted boundary) are honestly `OUT_OF_AVAILABLE_AUDIO_RANGE` and
excluded from aggregate stats (8 of 20 entry cells).

### RM041 exit

**100% root/mode agreement: every one of 20/20 cells resolves to `D
minor`.** Confidence grows monotonically with window length: `MEDIUM` (4
of 5 cells) at 10 s, mostly `MEDIUM`/1 `LOW` at 15 s, `HIGH` (5/5) at both
20 s and 30 s. Perturbation (+-1000 ms) never changes the root/mode at any
window length. This lane is `HARMONIC_EVIDENCE_STABLE_DIAGNOSTIC`
in isolation.

### RM014 entry

**Unstable below the 30 s window.** Root/mode by window length: 10 s ->
`D# major` (3/3 measured cells); 15 s -> `F# major` (1) / `D# major` (2);
20 s -> `F# major` / `G minor` / `C minor` (all three perturbations
disagree with each other); 30 s -> `G minor` (3/3, `HIGH` confidence,
matching the accepted independent-oracle 30 s-window result exactly).
Confidence is `LOW`/`MEDIUM` below 30 s and only reaches `HIGH` at 30 s.

### Pair relation (matched window-length/perturbation cells, `harmonic_relationship()` unmodified)

Of 12 valid (in-range) cells: **3 `COMPATIBLE`** (all three at the 30 s
window), **3 `INCOMPATIBLE`** (10 s@+500/+1000 ms, 20 s@0 ms), **6
`UNKNOWN`** (10 s@0 ms, all of 15 s, 20 s@+500/+1000 ms). The pair relation
is window-length dependent, not stable — it only converges to the
accepted independent-oracle `COMPATIBLE` result at the single window
length (30 s) that matches the original accepted methodology's fixed
window.

### A7 verdict

`HARMONIC_EVIDENCE_UNSTABLE` (driven entirely by the RM014/entry side;
the RM041/exit side alone is stable). The cached-local-estimator conflict
(`F major -> G minor INCOMPATIBLE` vs. independent-oracle
`D minor -> G minor COMPATIBLE`) is **not resolved** by this sensitivity
test in a threshold-agnostic way — it is reproduced at the one window
length (30 s) matching the original methodology, but 3 of 4 tested window
lengths disagree with each other and with that result. Full detail:
`tools/p0m3/all_in_one_runtime_probe/pair_stability/results/harmonic_sensitivity.json`.

### A8

`THIRD_HARMONIC_ORACLE_MAY_BE_JUSTIFIED` — the conflict remains genuinely
unresolved after sensitivity testing. No new analyzer, library, or model
was installed or evaluated this pass; this is a PM-owned decision.

## A9 — analysis_confidence counterfactual matrix

Read-only, against the UNMODIFIED `compatibility.py` /
`select_real_music_pairs.py` semantics
(`tools/p0m3/all_in_one_runtime_probe/pair_stability/build_counterfactual_matrix.py`).
`CASE_0`'s reconstructed input was verified (by the script itself, at run
time) to reproduce the accepted `strict_reason_codes_unchanged` list for
RM041->RM014 byte-for-byte before any counterfactual case was computed.

| Case | harmonic HIGH? | structure HIGH? | analysis_confidence | Remaining hard gates | Strict FULL_DJ eligible |
|---|---|---|---|---|---|
| CASE_0 (current) | no | no | LOW | downbeat, structure, analysis_confidence, harmonic | False |
| CASE_1 (only harmonic) | yes | no | LOW | downbeat, structure, analysis_confidence | False |
| CASE_2 (only structure) | no | yes | LOW | downbeat, analysis_confidence, harmonic | False |
| CASE_3 (both) | yes | yes | **HIGH** | **downbeat (only)** | **False** |

Even in the most favorable hypothetical (both harmonic AND structure
legitimately resolved to HIGH), `downbeat` remains the sole blocking
gate — and `downbeat` (specifically the RM014/entry side) is exactly the
lane this probe found least stable (A3). This is a counterfactual
diagnostic only; it does not mutate canonical evidence, `compatibility.py`,
or `select_real_music_pairs.py`, and it declares no render candidate.
Full detail: `results/counterfactual_matrix.json`.

## A10 — Calibration-readiness verdict

**`PAIR_EVIDENCE_PARTIALLY_STABLE`**

Rationale: BPM, the RM041/exit-side downbeat grid (exact agreement with
the independent madmom benchmark on every seed), the functional-structure
label at both boundaries (100% consensus), and the RM041/exit-side
harmonic estimate (100% root/mode agreement across all 20 window x
perturbation cells) are all genuinely stable and would support a future
calibration rule. The RM014/entry-side downbeat grid (seed-dependent
event-count drift, a two-cluster split in "nearest downbeat" at the exact
boundary, poor agreement with the independent benchmark) and the
RM014/entry-side harmonic estimate (window-length-dependent root/mode
below 30 s) are not. A future calibration/resolution-policy task would
need to (a) treat outgoing-exit and incoming-entry evidence asymmetrically
rather than with one shared confidence rule, (b) use a tail-aware
statistic (not a bare median) for downbeat agreement given the observed
gap between p90 (~10 ms) and max (up to 1770 ms), and (c) pin a specific
harmonic window length rather than trusting a single fixed-window
estimate, since window choice measurably changes the RM014-side harmonic
conclusion. This task does not define that rule.

## Validation

`tools/p0m3/all_in_one_runtime_probe/pair_stability/verify_pair_stability.py`:
**209/209 PASS.** Covers: exactly the 10 expected raw-run files (no more,
no less); all 10 runs PASS; both tracks' seed sets are exactly
`{0,1,2,3,4}`; canonical source/NATTEN commit and checkpoint SHA-256
pinned in every run; cross-seed metrics include median/p90/max/coverage
for every grid; the accepted boundary (186456.2 / 0.0 ms) is preserved
everywhere it is used; structure labels are literal model output with no
phrase claim; the harmonic sensitivity grid covers exactly the declared
window lengths and perturbations and uses the unmodified pairwise
function; the counterfactual matrix never treats downbeat as resolved; no
audio-render output file and no Signalsmith/Rubber Band reference exist
under `pair_stability/`; no privacy-pattern (path, filename, audio
extension) or disallowed RM id appears in any committed evidence file.

Additional git-level checks (run directly, not re-implemented in the
verifier): `compatibility.py` and `select_real_music_pairs.py` are
byte-identical to the starting HEAD; the working branch is
`research/p0-feasibility`; no other tracked file was modified.

## Privacy / scope

- Only the pre-existing approved local opaque mapping was read.
- Exactly RM041 and RM014 were analyzed; no other track.
- Committed evidence contains RM ids and numeric measurements only — no
  source filename, basename, path, artist, title, album, raw tag, audio
  hash, or audio bytes.
- All raw `allin1.analyze` console output (which can print the private
  source filename via progress-bar labels) was redirected to a local,
  gitignored log directory and never printed to a terminal/transcript for
  any of the 10 driver-invoked runs.
- No whole 19-track or 100-track rerun.
- No Signalsmith, Rubber Band, transition render, or owner listening pack.
- No R2 gate change, no `compatibility.py`/`select_real_music_pairs.py`
  edit, no P1 work, no `main` merge.

**Disclosure note**: during interactive setup of this task (a single
manual dry-run invocation before the driver script existed), one console
line containing the private track's on-disk filename/title/artist was
inadvertently displayed in the operator's tool output before output
redirection was added to the process. It was not written to any committed
file, any result JSON, or this document, and the corresponding artifact
was deleted before the real 10-run driver executed. Flagged here for
transparency per the task's evidence-honesty requirement; all 10 real
runs used in this report's evidence were produced only after output
redirection was in place.

## Files

- `tools/p0m3/all_in_one_runtime_probe/pair_stability/run_cross_seed_stability.py`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/driver_run_all_seeds.sh`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_downbeat_consensus.py`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_structure_consensus.py`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_harmonic_sensitivity.py`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/build_counterfactual_matrix.py`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/verify_pair_stability.py`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/EXACT_COMMANDS.md`
- `tools/p0m3/all_in_one_runtime_probe/pair_stability/results/*.json`
