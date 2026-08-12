# P0-M3-R3 -- Seamless DSP Render Shootout + Blinded Owner Listening

Status date: 2026-08-12

## 0. Execution profile actually used

- **Execution agent:** Claude Code runtime (Claude Desktop -> Code execution surface per `AGENTS.md`).
- **Parent model:** `claude-sonnet-5`. **Reasoning effort:** High.
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Cowork:** OFF. **Fallback:** NONE, not triggered.
- **Starting point:** HEAD `4e99fec5d34a34cc920d918dc166e452ccdd792a` (accepted P0-M3-R2 baseline).

## 1. Purpose

P0-M3-R2 decided WHEN/WHICH boundary to transition at. This pass answers:
given an accepted R2 boundary, can this project render a transition that is
genuinely seamless, natural, and not annoying -- the first P0-M3 pass where
audio is actually rendered and (about to be) listened to. This is a
disposable research harness (`tools/p0m3/audio_render_shootout/`), not the
P1 production engine, and no P1 work was started (verified: no changes
outside `tools/p0m3/audio_render_shootout/`, `docs/research/`, this repo's
root-level local-only ZIPs/HANDOFF file).

## 2. Binding inputs read

`AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_CHARTER.md`,
`docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`,
`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`,
`docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`,
`docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md`,
`docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md`,
`docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` (all 27 sections, incl.
PM REVIEW #2/#3 repairs), `docs/research/P0-M3-R2-OWNER-LISTENING-REFERENCE.md`,
the three `.agents/skills/` files.

The renderer **consumes** `tools/p0m3/transition_policy/policy/boundary.plan_transition_boundary()`
output directly -- every `PlannerDecision` used in this pass
(`tools/p0m3/audio_render_shootout/fixtures/planner_decisions/*.json`) is
the REAL output of that accepted function called on this pass's own
fixtures (`tools/p0m3/audio_render_shootout/fixtures/scenario_fixtures.py`),
never hand-fabricated. Reproducible: `python fixtures/generate_planner_decisions.py`.

## 3. DSP candidate provenance -- summary

Full audit: `docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md`. Headlines:

- **Signalsmith Stretch**, pinned `57b93f4e9206a089a45387eaa39bdc9f310d3308`
  (confirmed HEAD of `main` at task creation via `git ls-remote`), MIT
  license (verified verbatim). **Native C++ compilation is unavailable in
  this environment**: no `cl.exe`/`g++`/`clang`/`emcc` on `PATH`, and the
  one installed Visual Studio instance (`Visual Studio Professional 2026`)
  has no C++ compiler toolset installed (`VC/Tools/MSVC` does not exist).
  This is a documented, non-silent environment blocker, not a preference --
  per Issue #7, this pass therefore uses the **official, pinned, unmodified
  WASM/WebAudio release already shipped in the pinned commit**
  (`web/release/SignalsmithStretch.mjs`), run inside a real
  `OfflineAudioContext`/`AudioWorkletNode` (this session's Chromium-based
  Browser pane), driven by `tools/p0m3/audio_render_shootout/web/stretch_worker.html`.
  No Signalsmith source is reimplemented; the exact vendored file hashes are
  recorded in the provenance doc.
- **Rubber Band**, pinned `e4296ac80b1170018a110bc326fd0d45a0eb27d6`
  (confirmed HEAD of `default`), GPLv2+ (verified verbatim),
  `QUALITY_REFERENCE_ONLY`. Probe tier 1 (installed CLI) -- not found. Probe
  tier 2 (already-available FFmpeg Rubber Band filter) -- **found**: this
  machine's `ffmpeg 8.1.1-full_build` was built with
  `--enable-gpl --enable-version3 --enable-librubberband`, and its
  `rubberband` `AVOption` filter works. Tier 3 (local build) was not
  attempted -- unnecessary once tier 2 succeeded, and it would face the same
  missing-C++-toolchain blocker as Signalsmith's native path. The exact
  linked Rubber Band version/engine generation (R2/"Faster" vs R3/"Finer")
  could not be determined from the ffmpeg binary (no embedded version
  string; the filter's option set matches the classic R2 `Option` API) --
  recorded honestly as `UNKNOWN_NEEDS_RUNTIME_PROOF`, not assumed to be R3.
  M3 is invoked ONLY as an external `ffmpeg -af rubberband=...` subprocess;
  no Rubber Band source/binary is linked, vendored, or copied into any
  prospective shipping code (AC3).

## 4. Fixture scenarios

All four `PlannerDecision`s were produced by
`python fixtures/generate_planner_decisions.py` calling the REAL accepted
R2 `plan_transition_boundary()`. Full fixtures:
`tools/p0m3/audio_render_shootout/fixtures/scenario_fixtures.py`. Full
decisions: `tools/p0m3/audio_render_shootout/fixtures/planner_decisions/*.json`.

| Scenario | bpm_out / bpm_in | Tempo relation | `required_tempo_ratio` | `allowed_transition_class_set` | Exit / entry candidate |
|---|---|---|---|---|---|
| R3-A (no-stretch control) | 120 / 120 | DIRECT | `1.0` | `[FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE]` | `R3A-OUT-EXIT` (t=44000ms) / `R3A-IN-ANCHOR` (t=0ms) |
| R3-B (moderate stretch, ~5%) | 126 / 120 | DIRECT | `1.05` | `[FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE]` | `R3B-OUT-EXIT` (t=45000ms) / `R3B-IN-ANCHOR` (t=0ms) |
| R3-C (half/double + residual) | 120 / 61.8 | HALF_DOUBLE | `0.9709` | `[FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE]` | `R3C-OUT-EXIT` (t=44000ms) / `R3C-IN-ANCHOR` (t=0ms) |
| R3-D (incompatible pair) | 120 / 120 | DIRECT (irrelevant -- gated) | `None` | `[SIMPLE_CROSSFADE]` | `R3D-OUT-EXIT` (t=44000ms) / `R3D-IN-ANCHOR` (t=0ms) |
| E (pitch-shift stress) | -- | -- | -- | -- | `NOT_TESTED_NO_VALID_PLANNER_INPUT`, see `fixtures/pitch_shift_stress_conclusion.md` |

All four scenarios reach `outgoing_content_preservation_target = 1.0`
(a near-end exit whose remaining content is fully covered by the R2
overlap model, `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` §4) and
`beat_alignment_action = ALIGN_OUTGOING_BEAT_TARGET_TO_INCOMING_BEAT_TARGET`
/ `bar_alignment_action = ALIGN_OUTGOING_DOWNBEAT_TARGET_TO_INCOMING_DOWNBEAT_TARGET`
(both sides carry explicit `beat_downbeat_aligned` evidence).
`beat_phase_relation = NOT_MEASURED` in all four -- per R2's own R9 repair,
this is NOT treated as "already aligned"; the renderer performs the
declared alignment action itself (§7 below) rather than assuming phase 0.

**R3-D is the required incompatible-pair case**: `R3D-OUT-EXIT|R3D-IN-ANCHOR`
carries a boundary-level `vocal_collision_risk: HIGH` override
(`scenario_fixtures.SCENARIO_D["boundary_overrides"]`), which strips
`FULL_DJ_BLEND`/`SHORT_EQ_BLEND` from the allowed class set via the SAME
`policy/compatibility.downgrade_transition_class_set` gate P0-M3-R2 already
verified -- this pass adds no new gating logic. R3-D deliberately reuses
R3-A's exact audio (same bpm/duration/structure/seeds) so the DSP-fallback
behavior is isolated from any audio/cue confound (Issue #7 "do NOT let
different cue choices contaminate the DSP comparison").

Synthetic audio fixtures (`fixtures/synth.py`) are NOT click tracks: each
track has kick/snare/hat drums, a moving bass line, a chord pad, and a
melodic/vocal-like sustained lead, arranged into authored
intro/verse/chorus/outro sections with controlled energy variation, over an
exact beat/downbeat grid derived from the fixture's own bpm. A short
high-frequency "alignment marker" tick is embedded at each fixture's
authored alignment-target sample position for machine-verifiable ground
truth (§6). Audio is LOCAL ONLY, not committed (`.gitignore`); the
generator source and ground-truth metadata ARE committed.

## 5. Render methods

Full implementation: `tools/p0m3/audio_render_shootout/dsp/render_m{0,1,2,3}*.py`.
All four methods consume the exact SAME onset/content-end/entry timestamps
from the SAME `PlannerDecision` for a given scenario (`dsp/render_common.py`
is the one place that reads the decision and cuts audio segments) -- only
the time-stretch engine and gain/EQ policy differ between methods.

- **M0** (intentionally weak negative baseline): linear (non-equal-power)
  gain, no tempo correction even when the scenario requires one, no
  bass/EQ handoff, no beat alignment logic invoked.
- **M1** (planner-correct `SIMPLE_CROSSFADE` reference): equal-power gain,
  no tempo correction (by class definition -- AGENTS.md: "Crossfade: volume
  overlap only"), no bass/EQ handoff. Renders the SAME class regardless of
  whether `FULL_DJ_BLEND` was also allowed -- the stable "do less" reference.
- **M2** (Signalsmith candidate): when `FULL_DJ_BLEND` is allowed, applies
  the planner's exact `required_tempo_ratio`/pitch via the official pinned
  WASM release, applies the beat-alignment offset (§7), equal-power gain,
  and the bass/EQ handoff (§8). When `FULL_DJ_BLEND` is withheld (R3-D),
  renders the identical fallback M1 would -- never forces complex DSP
  (`dsp/render_m2_signalsmith.render_fallback`).
- **M3** (Rubber Band quality reference): identical boundary/gain/EQ policy
  to M2; only the stretch engine differs (`ffmpeg -af rubberband=tempo=<ratio>:pitch=<scale>`).

## 6. Alignment/tempo/pitch -- applied values + measured errors

Full contract: `tools/p0m3/audio_render_shootout/dsp/render_common.py`'s
`require_full_dj_alignment_fields` (fail-closed guard, §9) and
`compute_alignment_offset_ms` (general, not hardcoded-zero, computation).

| Scenario | Method | Applied tempo ratio | Planner required ratio | `stretch_ratio_error` | Applied pitch (semitones) | Applied alignment offset (ms) | `beat_alignment_error_ms` (synthetic ground truth) |
|---|---|---|---|---|---|---|---|
| R3-A | M0 | 1.0 | 1.0 | 0.0 | 0 | 0.0 | 0.0 |
| R3-A | M1 | 1.0 | 1.0 | 0.0 | 0 | 0.0 | 0.0 |
| R3-A | M2 | 1.0 | 1.0 | 0.0 | 0 | 0.0 | 0.0 |
| R3-A | M3 | 1.0 | 1.0 | 0.0 | 0 | 0.0 | 0.0 |
| R3-B | M0 | 1.0 | 1.05 | **0.05** (deliberate) | 0 | 0.0 | 0.0 |
| R3-B | M1 | 1.0 | 1.05 | **0.05** (deliberate) | 0 | 0.0 | 0.0 |
| R3-B | M2 | 1.05 | 1.05 | 0.0 | 0 | 0.0 | 0.0 |
| R3-B | M3 | 1.05 | 1.05 | 0.0 | 0 | 0.0 | 0.0 |
| R3-C | M0 | 1.0 | 0.9709 | **0.0291** (deliberate) | 0 | 0.0 | 0.0 |
| R3-C | M1 | 1.0 | 0.9709 | **0.0291** (deliberate) | 0 | 0.0 | 0.0 |
| R3-C | M2 | 0.9709 | 0.9709 | 0.0 | 0 | 0.0 | 0.0 |
| R3-C | M3 | 0.9709 | 0.9709 | 0.0 | 0 | 0.0 | 0.0 |
| R3-D | all 4 | 1.0 | `None` (FULL_DJ withheld) | `None` | 0 | 0.0 | 0.0 |

Full per-cell JSON: `tools/p0m3/audio_render_shootout/results/machine_metrics.json`.

`beat_alignment_error_ms` is measured, not asserted: a synthetic
high-frequency ("13kHz decaying blip) marker is embedded at each fixture's
exact authored beat-anchor sample at authoring time
(`fixtures/synth.py`/`fixtures/ground_truth/*.json`), then detected in the
FINAL rendered mix via matched-filter cross-correlation
(`dsp/safety_metrics.detect_marker`) and compared to its expected
post-render position; `beat_alignment_error_ms = detected_incoming_position
- detected_outgoing_position`. All 16 cells measure `0.0ms` -- both the
outgoing and incoming beat anchors in this pass's fixtures were
deliberately authored to fall exactly at the boundary onset/entry points
(so the correctly-computed alignment offset is honestly `0.0ms` for every
cell, not fabricated), and the marker-detection round-trip empirically
confirms the renderer actually places them there in the output samples,
not merely that the arithmetic says so.

`stretch_ratio_error = abs(planner_required_tempo_ratio - applied_tempo_ratio)`
directly shows M0/M1's deliberate (documented) tempo-correction skip on
B/C, and M2/M3's exact match.

## 7. Alignment implementation

`dsp/render_common.compute_alignment_offset_ms` computes, in general (not
hardcoded to zero): given `outgoing_beat_alignment_target_ms` and
`incoming_beat_alignment_target_ms` from the `PlannerDecision`, the ms
offset by which the (post-stretch) incoming clip must be shifted so both
targets coincide at the same output-timeline instant. In this pass's four
scenarios the offset resolves to `0.0ms` because both fixtures' beat
anchors were authored exactly at their respective onset/entry points --
this is a property of the fixtures, not a hardcoded renderer assumption;
the computation itself is exercised generally and would produce a nonzero
shift for a fixture whose anchors were offset from the boundary.

## 8. Signal safety / performance -- machine metrics only

Full data: `results/machine_metrics.json`. No subjective quality claim is
made from any of the following (AGENTS.md rule 2 / Issue #7 STAGE-A VERDICT
RULE).

- **NaN/Inf:** `0` across all 16 rendered cells.
- **Clipping:** `0` clipped samples across all 16 cells (headroom ceiling
  `-1.0 dBFS`, `dsp/mixing.apply_headroom_and_safety`).
- **Peak level:** `-1.41 dBFS` (R3-A/B, all methods), `-1.74 dBFS` (R3-C,
  all methods) -- consistent within a scenario across methods (same source
  material, same headroom policy).
- **Discontinuity/click proxy:** computed BOTH whole-clip (`dsp.safety_metrics.discontinuity_proxy`)
  and edge-scoped, i.e. only in a small window around the actual
  pre-roll/overlap and overlap/post-roll splice points
  (`discontinuity_proxy_at_transition_edges`), per Issue #7's own wording
  ("discontinuity/click proxy around transition edges"). **Honest
  limitation, stated plainly:** this proxy is a generic sample-to-sample
  jump statistic; this pass's synthetic drum hits (deliberately abrupt
  kick/snare attacks, by design in `fixtures/synth.py`) legitimately
  produce large sample-to-sample jumps that the proxy cannot distinguish
  from a genuine splice click. Its counts (`results/machine_metrics.json`,
  `signal_safety.discontinuity_proxy_at_transition_edges`) are recorded
  for completeness but are NOT used, here or anywhere in this report, to
  assert or deny audible click-freeness -- that determination requires
  human listening (§10-§11).
- **Loudness/energy:** `dsp.safety_metrics.rms_dbfs` /
  `loudness_jump_at_handoff_db` (RMS-based PROXY, explicitly NOT calibrated
  ITU-R BS.1770 LUFS) recorded per cell in `results/machine_metrics.json`'s
  `loudness` block.
- **Performance:** M0/M1 render in ~0.11-0.12s wall time for a ~40s output
  (`real_time_factor` ~0.0028, i.e. ~350x faster than real time -- pure
  Python/numpy, no external engine). M3 (ffmpeg subprocess) real-time
  factors ~0.016-0.031 (still ~30-60x faster than real time). M2's
  Signalsmith stretch itself runs in a separate browser process/tab; this
  harness only measures its own Python-side post-processing wall time
  (`render_wall_time_s_python_side`, ~tens of ms) and explicitly does NOT
  fabricate a wall-time number for the in-browser WASM stretch step itself
  -- recorded as a documented measurement gap, not a false `0`.
- **Peak memory:** not honestly measurable for the in-browser M2 stretch
  step from this Python-side harness (separate process); `psutil` is
  available in the venv for a future pass that wants to instrument the
  Python-side processes specifically, but no fabricated number is reported
  here for any method.

## 9. Fail-closed alignment contract (AC7)

None of this pass's four scenario fixtures happen to exercise the
missing-alignment-field path (their R2 boundaries are genuinely fully
evidenced). `dsp/render_common.require_full_dj_alignment_fields` is proven
real via `scripts/selftest_fail_closed.py`, which mutates a COPY of R3-B's
real accepted `PlannerDecision` to null out each of
`outgoing_beat_alignment_target_ms`, `incoming_beat_alignment_target_ms`,
`outgoing_downbeat_alignment_target_ms`, `incoming_downbeat_alignment_target_ms`,
`beat_alignment_action`, `bar_alignment_action`, and `required_tempo_ratio`
one at a time, asserting `PlannerContractError` is raised in every case
(and NOT raised on the untouched original). Reproducible:
`python scripts/selftest_fail_closed.py` -- `ALL SELF-TESTS PASS` (8/8:
1 positive + 7 negative mutations).

## 10. Blinded owner listening pack

`P0-M3-R3-OWNER-LISTENING.zip` (repo root, **LOCAL ONLY, not committed**).
11 clips (within the "approximately 9-12" target):

- S1 (R3-A) -- M1, M2, M3 (3 clips)
- S2 (R3-B) -- M1, M2, M3 (3 clips)
- S3 (R3-C) -- M1, M2, M3 (3 clips)
- S4 (R3-D) -- M0, M1 (2 clips -- M1/M2/M3 are byte-identical for R3-D,
  verified via matching SHA-256 during authoring, since `FULL_DJ_BLEND` is
  withheld and all three render the identical fallback; pairing M0 against
  M1 is the one real audible difference this scenario can demonstrate)

Each clip ~28s, centered on the transition (Issue #7 target: ~20-35s).
Opaque `S#-X.wav` names only. Rubric collects the required 1-5 ratings
(seamlessness/continuity, timing/rhythmic naturalness, stretch/pitch
naturalness, bass/low-end transition, momentum/excitement, overall
preference) plus the required yes/no questions
(noticeable-hard-discontinuity, annoying/fatiguing-artifact,
acceptable-for-normal-AutoMix) and an optional free-text note. The owner is
never asked to guess which method produced a clip.

Blind letter-to-method mapping is a deterministic, per-scenario seeded
shuffle (seed `20260812`, `scripts/build_listening_pack.py`), recorded ONLY
in `results/blind_key.json` (PM-only, included in the PM review ZIP, never
the owner ZIP).

## 11. Blinding verification (machine-checked)

`python scripts/verify_blinding.py` -- **ALL CHECKS PASS**. Verifies:
owner ZIP contains no `blind_key.json`; no method/class name (`signalsmith`,
`rubberband`, `baseline`, `crossfade`, `m0`-`m3`, `r3-a`..`r3-d`,
`full_dj_blend`, `short_eq_blend`, `simple_crossfade`) appears in the owner
ZIP's text files or WAV filenames; each blinded WAV's on-disk chunk
structure contains ONLY `fmt `/`data` (no `LIST`/`INFO`/id3 metadata chunk
for a name to hide in -- verified by direct RIFF-chunk parsing, not
assumed); every listening WAV's SHA-256 exists in `blind_key.json`'s
`clip_manifest` and matches byte-for-byte; the blind mapping reproduces
exactly by independently re-running the seeded shuffle; `OWNER_RATINGS_TEMPLATE.json`
uses only the opaque `S#-X` clip IDs as keys (nothing else). A first draft
of the binary WAV-content scan also checked 2-3 character terms
(`m0`/`m1`/`m2`/`m3`) against raw PCM bytes and correctly self-flagged as
producing spurious matches (any 2-byte ASCII sequence occurs by chance in
megabytes of audio); the binary scan was narrowed to only the long,
distinctive terms (>= 4 characters) where a chance collision is not
plausible, and the short terms are still checked against the (small,
human-authored) text files, where they are meaningful.

## 12. STAGE-A VERDICT RULE

Per Issue #7, this pass returns `OWNER_LISTENING_REQUIRED`, not `PASS`, for
overall render quality. Automated execution in this pass establishes only:
the renderer executed for all four scenarios and four methods; the R2
planner contract was obeyed (real `PlannerDecision`s consumed, never
fabricated); the fail-closed alignment guard is real; no objective safety
failure exists (zero NaN/Inf/clipping across 16 cells); the listening pack
is valid and passes every blinding-integrity check. **None of this
establishes that any rendered transition sounds seamless.** Human listening
has not yet occurred. Issue #7 remains OPEN until the owner listens to
`P0-M3-R3-OWNER-LISTENING.zip` and returns ratings.

## 13. Unknowns / risks

- The exact linked Rubber Band engine generation (R2 "Faster" vs R3
  "Finer") behind this machine's ffmpeg build is `UNKNOWN_NEEDS_RUNTIME_PROOF`
  (docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md sec.2.2) -- M3 remains
  labeled `QUALITY_REFERENCE_ONLY` regardless, per Issue #7, and this is not
  claimed to be R3/Finer.
- The discontinuity/click proxy (§8) is a generic statistical heuristic
  that cannot reliably distinguish a real splice click from this pass's
  own deliberately-abrupt synthetic drum transients -- explicitly not used
  to support any click-freeness claim.
- `loudness_proxy_dbfs`/`rms_dbfs` are RMS-based proxies, not calibrated
  ITU-R BS.1770 LUFS.
- M2's in-browser WASM stretch wall-time/peak-memory is not measured by
  this Python-side harness (a genuine instrumentation gap, not fabricated
  as zero) -- a future pass wanting real M2 performance numbers would need
  to instrument the browser process itself (e.g. via `performance.now()`
  inside `web/stretch_worker.html`, not attempted this pass).
- All fixtures are hand-authored synthetic audio (`SYNTHETIC_EXACT`); no
  real-music validation occurred this pass (Tier B / owner-private-music
  path exists in the harness design but was not exercised, per Issue #7
  "Do NOT require private tracks to complete Stage A").
- `NEAR_END_MAX_OVERLAP_MS`, preservation floors, and pair-compatibility
  thresholds are unchanged P0 placeholders inherited from P0-M3-R2 (not
  reopened this pass, per Issue #7's explicit scope boundary).

## 14. Files

- `docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md` (this document)
- `docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md`
- `tools/p0m3/audio_render_shootout/README.md`
- `tools/p0m3/audio_render_shootout/fixtures/scenario_fixtures.py`
- `tools/p0m3/audio_render_shootout/fixtures/generate_planner_decisions.py`
- `tools/p0m3/audio_render_shootout/fixtures/planner_decisions/*.json`
- `tools/p0m3/audio_render_shootout/fixtures/synth.py`
- `tools/p0m3/audio_render_shootout/fixtures/generate_audio.py`
- `tools/p0m3/audio_render_shootout/fixtures/ground_truth/*.json`
- `tools/p0m3/audio_render_shootout/fixtures/pitch_shift_stress_conclusion.md`
- `tools/p0m3/audio_render_shootout/dsp/*.py`
- `tools/p0m3/audio_render_shootout/web/stretch_worker.html`
- `tools/p0m3/audio_render_shootout/scripts/*.py`
- `tools/p0m3/audio_render_shootout/results/machine_metrics.json`
- `tools/p0m3/audio_render_shootout/.gitignore`, `requirements.txt`

## 15. PM review request

Please independently verify:

1. Run `python fixtures/generate_planner_decisions.py` (from
   `tools/p0m3/audio_render_shootout/`) and confirm the printed
   `allowed_transition_class_set`/`required_tempo_ratio` per scenario match
   §4's table exactly.
2. Open `results/machine_metrics.json` and confirm zero NaN/Inf/clipped
   samples across all 16 cells, and `stretch_ratio_error` is nonzero only
   for M0/M1 on R3-B/R3-C.
3. Run `python scripts/selftest_fail_closed.py` and confirm `ALL SELF-TESTS PASS`.
4. Run `python scripts/verify_blinding.py` and confirm `ALL CHECKS PASS`.
5. Confirm no `.wav`/other audio file is tracked by git anywhere under
   `tools/p0m3/audio_render_shootout/` (`git status`, `git ls-files`).
6. Confirm `dsp/mixing.py` and `dsp/*` contain no `rubberband`/`signalsmith`
   C++ source, and that Rubber Band is invoked only via an external
   `ffmpeg` subprocess call in `dsp/render_m3_rubberband.py`.
7. Instruct the owner to listen to `P0-M3-R3-OWNER-LISTENING.zip` FIRST and
   return `OWNER_RATINGS_TEMPLATE.json` before opening `results/blind_key.json`.

---

**Do not start P1. Result: `OWNER_LISTENING_REQUIRED`, not `PASS`.**
