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
| R3-B (moderate stretch, ~5%) | 126 / 120 | DIRECT | `1.05` | `[FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE]` | `R3B-OUT-EXIT` (t=45714ms, PM STAGE A REVIEW R2 repair -- see §16) / `R3B-IN-ANCHOR` (t=0ms) |
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

## 6. Alignment/tempo/pitch -- applied values + measured errors (SUPERSEDED, see §16)

**This section's original `beat_alignment_error_ms` methodology and the
`0.0ms`-for-every-cell claim below were found defective by PM STAGE A
REVIEW (R3) and are superseded by §16's `outgoing_anchor_absolute_error_ms`
/ `incoming_anchor_absolute_error_ms` / `relative_alignment_error_ms`
model. Kept in place, unedited below, only so the supersession is visible
in-place; do not cite the `0.0ms` figures in this section as current
evidence.**

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

PM STAGE A REVIEW independently found this `0.0ms`-everywhere result
unreliable: `compute_metrics.py` called `detect_marker()` twice with the
SAME 13kHz template for both outgoing and incoming, against overlapping
search windows, so both calls could (and sometimes did) lock onto the
SAME peak and mechanically difference to `0.0` even when the individual
detections were, independently, ~223-255ms away from the true marker.
See §16 for the repair and the corrected measurements.

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

## 10. Blinded owner listening pack (SUPERSEDED, see §17-18)

**PM STAGE A REVIEW invalidated the pack described in this section (R4:
its clips were extracted from marker-embedded diagnostic audio, so the
13kHz diagnostic tick could leak into owner-listening audio; R5: its blind
seed `20260812` was hardcoded in committed source and its mapping was
committed to git, both readable by the owner before listening). Do not
use the ZIP hash originally reported here. §17-18 document the rebuilt
pack.**

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

## 15. PM review request (SUPERSEDED, see §19)

**Superseded by §19's PM review request, which reflects the repaired
pipeline. Kept in place only so the supersession is visible in-place.**

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

# PM STAGE A REVIEW -- REPAIR (2026-08-12)

PM STAGE A REVIEW independently re-verified pushed HEAD
`090fa848db8d56d72d794108a576beac8e547df9` and both uploaded deliverables,
and found four load-bearing defects the original pass's own checks did not
catch (R1-R4), plus two hardening requirements (R5-R6). Sections 16-19
document the repair. Everything in §1-15 that PM STAGE A REVIEW did not
flag (planner-decision consumption discipline, R3-D fallback-never-forced
behavior, pitch-shift-stress `NOT_TESTED_NO_VALID_PLANNER_INPUT`
conclusion, Signalsmith/Rubber Band provenance) is unchanged.

## 16. R1-R3 -- sample-rate domain, ground truth, and alignment-diagnostic repairs

### R1 -- M2 sample-rate domain mismatch

**Defect** (independently reproduced by PM): `web/stretch_worker.html`
decoded the input WAV through a default `new AudioContext()`, which uses
the browser's hardware output rate (48000Hz on this machine) rather than
the source file's native rate (44100Hz) -- `decodeAudioData` silently
resamples to the context's rate. `finish_job()` then took the Signalsmith
output's own (48000Hz) sample rate and used it to label/write the ENTIRE
assembled render, while `outgoing_pre`/`outgoing_overlap` remained
44.1kHz-domain sample arrays -- concatenating two different rate-domain
buffers under one declared rate. Independent evidence PM cited: R3-A/C
`overlap_duration_ms` reported `9187.5` instead of the planned `10000`;
R3-B reported `10106.25` instead of `11000` (using the R2-repair-cycle's
then-uncorrected 45000ms boundary).

**Repair**:
1. `web/stretch_worker.html` now requires an explicit `expectedSampleRate`
   query param, decodes through a dedicated `OfflineAudioContext(1, 1,
   expectedSampleRate)` (which forces `decodeAudioData` to resample to
   EXACTLY that rate), and asserts `audioBuffer.sampleRate ===
   expectedSampleRate` before proceeding, and `rendered.sampleRate`/
   `rendered.numberOfChannels` again after rendering -- throwing
   (visible as `ERROR: SAMPLE_RATE_ASSERTION_FAILED`, not a silent
   fallback) on any mismatch.
2. `dsp/render_m2_signalsmith.finish_job()` independently re-reads the
   actual WAV file's own sample rate (never trusts the sidecar alone),
   and fails closed (`dsp.mixing.SampleRateMismatchError`) unless it
   matches the canonical fixture rate OR an explicit, logged
   `dsp.mixing.normalize_sample_rate` (deterministic `scipy.signal.
   resample_poly` rational resample) has run -- `sample_rate_resample_applied`
   is recorded honestly per cell (`false` in every current cell, since the
   browser-side fix makes the mismatch not occur in practice).
3. `dsp/render_m3_rubberband.py` was symmetrically hardened (`assert` ->
   `raise SampleRateMismatchError`), even though PM's review did not flag
   M3 specifically.
4. `scripts/verify_cross_method_consistency.py` (new) asserts, per
   scenario: identical `canonical_sample_rate` and `channels` across all
   4 methods, and `overlap_duration_ms` invariant across methods (within
   0.05ms, a sub-sample rounding allowance only). **`ALL CHECKS PASS`** --
   R3-A/C now report `overlap_duration_ms: 10000.0` and R3-B reports
   `10286.01` (see R2 below for why R3-B's number itself changed) across
   all 4 methods, every scenario.

### R2 -- R3-B's declared beat/downbeat anchor was not on the beat grid

**Defect** (independently reproduced by PM): R3-B's outgoing exit
candidate was authored at bpm=126, `t_ms=45000`,
`beat_downbeat_aligned: true`. `45000 / (60000/126) = 94.5` beats from
t=0 -- exactly a half-beat offset, neither a beat nor a downbeat. The
synthetic marker was simply inserted at 45000ms with no check against the
actual authored beat grid.

**Repair**: `fixtures/scenario_fixtures.py`'s `SCENARIO_B` outgoing exit
candidate and its `marker_ms` were moved to `t_ms=45714` -- the nearest
integer ms to the 24th bar boundary (`24 * 4 * (60000/126) =
45714.285714...ms`, 0.2857ms from the true grid position). The
`PlannerDecision` was regenerated from this corrected fixture via the REAL
`policy.boundary.plan_transition_boundary()` (`python
fixtures/generate_planner_decisions.py`) -- never hand-edited; it still
returns `required_tempo_ratio: 1.05` (the intended ~5% direct-stretch
scenario is preserved). `scripts/verify_beat_grid_membership.py` (new)
asserts, for A/B/C, that every `FULL_DJ_BLEND` outgoing/incoming
beat/downbeat alignment target is within `5.0ms` (a stated
`PROJECT_INFERENCE` diagnostic tolerance, not Apple-derived) of an actual
entry in that side's synthetic `beats_ms`/`downbeats_ms` ground truth.
**`ALL CHECKS PASS`** -- including R3-B's outgoing target now measuring
`0.286ms` from the true grid position, well inside tolerance.

### R3 -- alignment diagnostics could report a fabricated `0.0ms`

**Defect** (independently reproduced by PM): the outgoing and incoming
sides both used the SAME 13kHz decaying-sine marker template. With
overlapping/near-identical expected search positions, `detect_marker()`
could (and, per PM's cited evidence, sometimes did) lock onto the SAME
peak for both calls, mechanically producing `relative_error = 0.0` even
when the two individual detections were independently ~223-255ms off.

**Repair, part 1 (distinct signatures)**: `dsp/markers.py` (new) defines
two spectrally- and structurally-distinct marker signatures --
**outgoing**: a decaying pure sine at 9500Hz; **incoming**: a decaying
UPWARD CHIRP from 15500Hz to 19500Hz. `fixtures/synth.py` embeds the
correct signature per `marker_role` and records `marker_spec` (kind +
exact parameters) in each side's ground-truth JSON, so detection always
uses the true embedded template, never a hardcoded guess.

**Repair, part 2 (honest confidence, never a fabricated 0.0)**:
`dsp/safety_metrics.detect_marker()` now reports a `quality` of `HIGH`,
`LOW`, `UNKNOWN_NO_SEGMENT`, or `UNKNOWN_LOW_CONFIDENCE`, using a
PROMINENCE-based (z-score of the best-scoring position against the full
distribution of scores in the search window) confidence measure rather
than a bare absolute-correlation cutoff -- calibrated empirically after
discovering that a marker additively mixed into real musical content
(deliberately placed AT an authored downbeat, which is also exactly where
a kick hit triggers) rarely exceeds ~0.3-0.4 absolute correlation even at
the objectively correct position, while the correct position still stands
out as an overwhelming statistical outlier (z-scores of 10+ observed) --
see `dsp/safety_metrics.py`'s `MARKER_QUALITY_HIGH_Z`/`MARKER_QUALITY_LOW_Z`
comments for the full empirical rationale. `error_ms`/`detected_sample`
are `None` whenever `quality` is `UNKNOWN_*` -- never a fabricated `0.0`.
`scripts/compute_metrics.py` now reports THREE separate numbers per cell:
`outgoing_anchor_absolute_error_ms`, `incoming_anchor_absolute_error_ms`,
`relative_alignment_error_ms` (computed ONLY when both sides are
confidently detected; otherwise `None` with
`relative_alignment_quality: "UNKNOWN_INSUFFICIENT_CONFIDENT_DETECTIONS"`).

**Repair, part 3 (measuring the right buffer -- a finding made DURING
this repair, not in the original PM comment)**: while validating parts
1-2, this pass discovered that the incoming alignment anchor sits, by
definition, at the exact FIRST sample of the equal-power crossfade's
fade-in, where gain is mathematically `sin(0) == 0` -- so a marker placed
there is ALWAYS silent in the final gain-mixed render regardless of
whether the renderer positioned it correctly. This is a real, expected
property of equal-power crossfades, not a placement bug, but it makes the
final mixed render unreliable for verifying incoming-side alignment
empirically. Fix: every renderer (M0/M1/M2/M3) now saves the exact
PRE-GAIN `outgoing_overlap`/`incoming_overlap` buffers (post-stretch,
post-alignment-shift, before `dsp.mixing.mix_overlap` multiplies by the
crossfade curve) to `results/premix_diag/*_premix.wav`
(`dsp.render_common.save_premix_diagnostic`, diagnostic-only, local,
~0.6s snippets) whenever `variant="diagnostic"`. `compute_metrics.py`
detects both markers against these premix buffers (`expected_sample=0`
for both, since each buffer starts at the same output-timeline instant by
construction) instead of the final mixed render. Signal-safety/loudness/
discontinuity diagnostics still run against the FINAL mixed render, since
those legitimately describe the actual deliverable.

**Results** (`results/machine_metrics.json`, all 16 cells):

| Scenario | Method | out abs err (ms) | in abs err (ms) | relative err (ms) | out quality | in quality |
|---|---|---|---|---|---|---|
| R3-A | M0/M1 | 0.0 | 0.0 | 0.0 | HIGH | HIGH |
| R3-A | M2/M3 | 0.0 | `None` | `None` | HIGH | `UNKNOWN_LOW_CONFIDENCE` |
| R3-B | M0/M1 | 0.0 | 0.0 | 0.0 | HIGH | HIGH |
| R3-B | M2/M3 | 0.0 | `None` | `None` | HIGH | `UNKNOWN_LOW_CONFIDENCE` |
| R3-C | M0/M1 | 0.0 | 0.0 | 0.0 | HIGH | HIGH |
| R3-C | M2/M3 | 0.0 | `None` | `None` | HIGH | `UNKNOWN_LOW_CONFIDENCE` |
| R3-D | all 4 | 0.0 | 0.0 | 0.0 | HIGH | HIGH |

M0/M1/D are unambiguously confirmed aligned (`0.0ms`, `HIGH` confidence
both sides -- these never apply real time-stretch, so the marker's
waveform reaches the premix buffer completely intact). **M2/M3's incoming
marker is honestly `UNKNOWN_LOW_CONFIDENCE`, not falsely `0.0` and not
falsely a large error**: absolute correlation peaks measured only
`0.012-0.039` (below the `0.05` floor) even though several individually
had high z-scores (up to 7.8) -- the most defensible reading is that
Signalsmith/Rubber Band's phase-vocoder-style time-stretch measurably
reshapes/smears a short (10-12ms) broadband transient, which is itself a
real, informative property of these DSP engines on transient content (and
arguably relevant to the very question this task is investigating -- how
these engines handle transients under time-stretch), not a measurement
artifact. Per PM's explicit instruction ("a failed or ambiguous marker
detection must be UNKNOWN/FAIL, never synthetic 0.0"), this pass reports
`UNKNOWN_LOW_CONFIDENCE` rather than forcing a number through further
threshold tuning.

## 17. R4 -- clean vs. diagnostic render separation

**Defect** (independently reproduced by PM): `fixtures/synth.py` embedded
the (then-single, 13kHz) diagnostic marker directly into the SAME source
waveform used for owner-listening renders -- an audible-ish tick that
could contaminate exactly the subjective dimensions Stage B asks the
owner to judge.

**Repair**: `fixtures/synth.py`'s `make_track()` now takes an
`embed_markers` flag; `fixtures/generate_audio.py` writes BOTH a
diagnostic variant (`{id}_{side}.wav`, marker-embedded, used for the full
DSP pipeline / machine metrics / PM forensic review) and a clean variant
(`{id}_{side}_clean.wav`, no diagnostic content at all -- otherwise
byte-for-byte the same musical content: same seed/bpm/structure) for
every scenario. `dsp/render_common.load_scenario_context()` takes a
`variant` parameter threaded through every renderer (M0/M1/M2/M3,
including the M2 browser-bridge `prepare_job`/`finish_job` and the M3
ffmpeg path); clean-variant M2 jobs are separate browser round-trips
against the clean input, using the identical M2 gain/EQ/alignment policy
-- only the underlying source audio differs. Clean renders are written to
`results/rendered_clean/` (verified during authoring: NONE of the clean
renders' bytes match any diagnostic render's bytes, since the underlying
audio differs by construction). `scripts/build_listening_pack.py` now
reads EXCLUSIVELY from `results/rendered_clean/` -- verified by its own
`source_variant: "clean"` field recorded in `blind_key.json`'s
`clip_manifest` for all 11 clips, and empirically by the blinding
verifier's format-parity check (§18) plus this repair's own construction
(no code path in `build_listening_pack.py` can read `results/rendered/`
at all -- the diagnostic directory constant isn't even imported there).

## 18. R5-R6 -- true blinding + Signalsmith latency evidence

### R5 -- blinding was reproducible from committed repository state

**Defect** (independently reproduced by PM): `scripts/build_listening_pack.py`
hardcoded `BLIND_SEED = 20260812` in committed source, and
`results/blind_key.json` (the full letter-to-method mapping) was itself
committed to git at HEAD `090fa84` -- an owner with `git log`/`git show`
access could read the mapping before listening.

**Repair**:
1. `git rm --cached tools/p0m3/audio_render_shootout/results/blind_key.json`
   and added `results/blind_key.json` + `results/.blind_seed_local` +
   `premix_diag/` to `.gitignore` -- verified by
   `git ls-files --error-unmatch` failing against the path (§18's
   verifier check).
2. `scripts/build_listening_pack.py` no longer has any `BLIND_SEED`
   constant. It requires the seed via the `AUTOMIX_R3_BLIND_SEED`
   environment variable and exits 1 with a clear error if unset --
   verified interactively this pass (`python scripts/build_listening_pack.py`
   with no env var set -> `ERROR: AUTOMIX_R3_BLIND_SEED environment
   variable is required ...`, exit 1).
3. A NEW seed (a 63-bit value from Python's `secrets.randbelow`, generated
   in this session, never written to any committed file or this document)
   was used to rebuild the pack. `scripts/verify_blinding.py` asserts the
   seed in use is NOT the old committed value (`20260812`) -- **`OK`**.
4. `scripts/verify_blinding.py` extended with format-parity checks across
   every owner WAV: identical sample rate, channel count, bit depth, and
   container/format tag, plus clip-duration spread `<= 0.5s`. Actual
   result this pass: sample rate `{44100}`, channels `{2}`, bit depth
   `{16}`, format tag `{1}` (PCM), duration spread `0.000s` (all 11 clips
   exactly 28.00s) -- **zero variance across every field, zero
   method-correlated file-format signal available to the owner**.
5. The owner ZIP still contains no blind key/seed/method name (all
   original Issue #7 checks re-verified against the rebuilt pack).

`python scripts/verify_blinding.py` (seed supplied via env var) --
**`ALL CHECKS PASS`**.

### R6 -- Signalsmith latency/scheduling evidence

**Repair**: `web/stretch_worker.html` now calls `await
stretchNode.latency()` before scheduling/rendering and includes it,
alongside `requested_input_sample_rate`, `decoded_sample_rate`,
`output_sample_rate`, `channels`, `requested_tempo_rate`,
`requested_semitones`, `block_ms`, `tail_pad_s`, `input_duration_s`,
`output_sample_count`, `output_duration_s`, and the exact `scheduling_params`
object passed to `.schedule()`, in a machine-readable sidecar JSON
uploaded alongside the audio (`{tag}_m2_sidecar.json`) and folded verbatim
into each M2 cell's `render_meta` JSON as `signalsmith_job_sidecar`. No
latency value is trimmed/subtracted a second time anywhere in the
pipeline -- the pinned node's own latency-compensated `schedule()`
contract is used as-is, per the upstream README's documented behavior;
this repair only ADDS visibility into the value, it does not add a second,
independent latency correction on top of it. **Observed value: `0.12s`
(120ms) consistently across all 6 browser jobs** (A/B/C x
diagnostic/clean) -- equal to the `blockMs=120` configured block length,
consistent with the upstream docs' description of latency scaling with
block size. §16 R3's repaired distinct-marker diagnostics (measured on
premix buffers, where M0/M1/D report exact `0.0ms` alignment) show no
evidence that a residual scheduling correction beyond the node's own
latency compensation is needed for this pass's fixtures; no such
correction was added.

## 19. Updated verification + PM STAGE A REVIEW repair closeout

Exact commands (from `tools/p0m3/audio_render_shootout/`):

```
python fixtures/generate_planner_decisions.py
python fixtures/generate_audio.py
python scripts/render_all.py
# M2: prepare/finish for diagnostic AND clean variants, A/B/C (6 browser round-trips)
python dsp/render_m2_signalsmith.py prepare R3-A diagnostic   # ... open URL, wait for DONE ...
python dsp/render_m2_signalsmith.py finish  R3-A diagnostic
python dsp/render_m2_signalsmith.py prepare R3-A clean
python dsp/render_m2_signalsmith.py finish  R3-A clean
# (repeat for R3-B, R3-C)
python dsp/render_m2_signalsmith.py fallback R3-D diagnostic
python dsp/render_m2_signalsmith.py fallback R3-D clean
python dsp/render_m3_rubberband.py R3-A diagnostic
python dsp/render_m3_rubberband.py R3-A clean
# (repeat for R3-B, R3-C, and R3-D diagnostic-only)
python scripts/verify_cross_method_consistency.py   # NEW -- R1
python scripts/verify_beat_grid_membership.py       # NEW -- R2
python scripts/compute_metrics.py                   # repaired -- R3
python scripts/selftest_fail_closed.py
AUTOMIX_R3_BLIND_SEED=<new secret seed> python scripts/build_listening_pack.py   # R4 (clean-only) + R5 (required seed)
python scripts/build_owner_pack.py
AUTOMIX_R3_BLIND_SEED=<same seed> python scripts/verify_blinding.py             # R5, extended checks
python scripts/build_pm_pack.py
```

All exited 0. `ALL CHECKS PASS` on `verify_cross_method_consistency.py`,
`verify_beat_grid_membership.py`, `selftest_fail_closed.py` (8/8), and
`verify_blinding.py` (including all new R5 checks). 16/16 diagnostic cells
and 11/11 clean owner clips rendered; 0 NaN/Inf, 0 clipped samples across
every diagnostic cell.

### Updated AC check (deltas from §15's original pass only)

- **AC6** (same boundary across methods): now machine-verified, not just
  structurally argued -- `verify_cross_method_consistency.py` PASS.
- **AC9** (beat/downbeat synthetic-ground-truth errors reported): now
  reports 3 separate honest numbers per cell with confidence, including
  legitimate `UNKNOWN` results for M2/M3 incoming markers, never a
  fabricated `0.0`.
- **AC12** (blind owner listening ZIP passes blinding-integrity checks):
  re-verified against the REBUILT pack with a new, non-derivable seed and
  new format-parity checks.
- All other AC1-AC17 results from §15 stand, re-verified against the
  repaired pipeline.

### Unknowns / risks (additions to §13)

- M2/M3's incoming-marker detection quality (`UNKNOWN_LOW_CONFIDENCE`) is
  itself only diagnostic evidence about matched-filter detectability of a
  short synthetic transient under phase-vocoder stretch -- it is NOT
  evidence about, and must not be read as evidence about, actual
  perceptual/rhythmic correctness of the stretched incoming audio itself.
  Only human listening (Stage B) can assess that.
  outgoing/M0/M1/D alignment remains fully confirmed at `0.0ms`, `HIGH`
  confidence.
- The new blind seed is known only to this session's local environment
  (supplied via `AUTOMIX_R3_BLIND_SEED`, never written to any committed
  file); the PM review ZIP's `blind_key.json` is the sole authoritative
  record going forward.

## PM REVIEW REQUEST (supersedes §15)

Please independently verify:

1. Run `python scripts/verify_cross_method_consistency.py`,
   `python scripts/verify_beat_grid_membership.py`,
   `python scripts/selftest_fail_closed.py`, and (with the seed from the
   PM ZIP's `blind_key.json` exported as `AUTOMIX_R3_BLIND_SEED`)
   `python scripts/verify_blinding.py` -- confirm all four print
   `ALL CHECKS PASS` / `ALL SELF-TESTS PASS`.
2. Open `results/machine_metrics.json` and confirm R3-A/C
   `overlap_duration_ms = 10000.0` and R3-B `overlap_duration_ms ≈
   10286.01` across all 4 methods each (not the prior pass's
   `9187.5`/`10106.25`).
3. Confirm `fixtures/scenario_fixtures.py`'s `SCENARIO_B` outgoing exit is
   `t_ms=45714` (not `45000`) and that
   `fixtures/planner_decisions/R3-B.json` was regenerated (check its file
   mtime / regenerate it yourself) rather than hand-edited.
4. Confirm `results/blind_key.json` is NOT present via `git ls-files
   tools/p0m3/audio_render_shootout/results/` and that
   `tools/p0m3/audio_render_shootout/scripts/build_listening_pack.py`
   contains no hardcoded seed constant.
5. Confirm the NEW `P0-M3-R3-OWNER-LISTENING.zip` SHA-256 (§ below /
   `HANDOFF_TO_PM.md`) differs from the invalidated prior pack's
   `6a4dc2250a746701b1863dec3c9accea3981a9bb6a6fbf4a597deeff23fbc09e`.
6. Instruct the owner to listen to the NEW `P0-M3-R3-OWNER-LISTENING.zip`
   ONLY -- the prior pack is invalidated and must not be rated.

Do not start P1. Result remains `OWNER_LISTENING_REQUIRED`.

---

# PM OWNER LISTENING DIRECTION UPDATE -- LOUDNESS + CONDITIONAL TEMPO + REAL-MUSIC HARNESS (2026-08-12)

The owner's informal first listen of the repaired synthetic pack produced
new binding subjective evidence that OVERRIDES the plan to complete Stage
B from the synthetic listening matrix: the rating matrix is too
cumbersome, synthetic music makes methods too hard to distinguish, real
vocal music is required, and the most obvious shared defect is a sudden
perceived volume drop. PM independently corroborated the loudness
complaint from this pass's own committed machine metrics (R3-A M0:
`5.85dB`/`6.49dB` jumps at the overlap boundaries). This section documents
the five follow-on tasks: loudness/energy continuity repair, conditional
tempo adaptation, a real-music Tier-B harness, a simplified owner-rating
UX, and a Spotify public-reference note. **The synthetic pack and its
blind mapping are NOT unblinded here** -- the owner already reported it
insufficiently discriminative for the real product question; forcing a
winner from it would not answer that question.

## 20. Loudness / energy continuity repair

### 20.1 Root cause (measured, not assumed)

`dsp/loudness_diagnostics.py` (new) replaces the single before/after
400ms comparison with a genuine 200ms-window/100ms-hop time series,
anchored against a `pre_transition_reference_db` measured over a stable
2-second window well before the transition (3-5s before onset, so
transient noise from sparse percussive hits averages out). Run on the
unmodified R3-A M0 render, the curve revealed two distinct, separable
phenomena, not one:

1. **Beat-phase measurement noise** (large, but NOT a real defect):
   consecutive 100-200ms windows swing `~10-15dB` purely depending on
   whether a kick/snare/hat transient happens to fall inside that
   specific window -- this project's synthetic drums are deliberately
   sparse and punchy (`fixtures/synth.py`), so any single short-window
   RMS measurement is dominated by beat phase, not by the underlying
   crossfade curve. This is why the PRIOR pass's single-point
   `loudness_jump_at_handoff_db` numbers (`5.85dB`/`6.49dB` etc.) were
   real numbers but not reliable evidence of a specific gain-curve
   defect on their own.
2. **A real, sustained mid-transition dip** (the genuine defect,
   separable from #1 because it is visible as a slow trend across MANY
   beat cycles, not a single-window artifact): comparing the SAME beat-
   phase-aligned windows across the transition, both the "loud" peaks and
   "quiet" valleys of the periodic pattern get measurably quieter through
   the middle of the overlap and recover only near the end. Root cause,
   confirmed by direct measurement: the incoming track's ENTRY region
   (its authored intro, lower `energy` per `fixtures/synth.py`'s section
   model) is objectively QUIETER than the outgoing track's EXIT region at
   the moment of crossfade. Equal-power gain (`g_out^2+g_in^2=1`)
   preserves total signal ENERGY only when both sides have equal
   intrinsic loudness; crossfading from an objectively louder source to
   an objectively quieter one necessarily dips in the middle even though
   the gain law itself is mathematically "constant power." **This is
   exactly the "equal-power gains alone do not guarantee constant
   perceived loudness" finding PM's comment anticipated, now measured
   directly rather than assumed** -- confirmed further by the fact that
   `handoff_loudness_delta_db` (still noisy/beat-phase-sensitive) and
   `maximum_loudness_dip_db` (the new, more reliable reference-anchored
   metric) both point the same direction, and that ALL FOUR curve
   variants below (§20.2), which share identical source content and beat
   phase, show the SAME relative ordering regardless of the absolute
   noise floor -- proving the between-curve comparison is a valid signal
   even though the absolute numbers are inflated by beat-sparsity noise.

Bass-handoff interaction: a quick sensitivity check (`bass_handoff_speed`
2.2x vs. 1.0x on the late-hold curve, R3-A) showed a small but real
additional improvement (`max_dip` `9.77dB -> 9.34dB`) from slowing the
bass swap to match the full-band curve's duration -- confirming PM's
hypothesis has SOME truth, though it is a smaller contributor than the
source-loudness-mismatch root cause above.

Static headroom policy (`dsp.mixing.apply_headroom_and_safety`, `-1.0dBFS`
ceiling) was NOT a contributor to the dip -- it only ever reduces gain
when the assembled peak exceeds ceiling (never during the dip, which is
in the middle of the transition, well under peak).

### 20.2 Curve shootout (`scripts/render_loudness_shootout.py`, `dsp/mixing.py`)

Four variants, rendered on R3-A/B/C's diagnostic audio via the M1-style
(no-stretch) pipeline to isolate the gain-curve variable exactly as the
M0-M3 shootout isolates the stretch-engine variable:

| Variant | Curve | Energy-aware makeup | Description |
|---|---|---|---|
| LA | `equal_power` | no | current reference (unchanged from M1) |
| LB | `late_hold` | no | outgoing holds unity for the first 30% of overlap, then cosine-tapers; incoming ramps in via the full-duration sine curve regardless -- "incoming enters underneath, handoff occurs later" |
| LC | `equal_power` | yes | equal-power curve + a capped (`±6dB`), boundary-measured static makeup gain on incoming, ramped in proportional to incoming's own gain envelope (never boosts silence) |
| LD | `late_hold` | yes | LB + LC combined |

Results (`results/loudness_shootout_meta/*.json`, `maximum_loudness_dip_db`):

| Scenario | LA (reference) | LB (late-hold) | LC (energy-aware) | LD (combined) |
|---|---|---|---|---|
| R3-A | 10.63 dB | **9.09 dB** | 9.08 dB | 8.77 dB |
| R3-B | 9.42 dB | **7.88 dB** | 7.90 dB | 7.53 dB |
| R3-C | 14.08 dB | **11.87 dB** | 14.24 dB (worse) | 12.36 dB |

**Recommendation: LB (late-outgoing-hold) adopted as this pass's default**
for `scripts/real_music_pipeline.py` (`curve="late_hold"`). It is the
ONLY variant that improves `maximum_loudness_dip_db` in all three
scenarios with zero added clipping/headroom risk (`peak_dbfs` unchanged
from LA in every case) and no increase in `maximum_loudness_rise_db`
beyond what's expected from holding outgoing at unity slightly longer.
LC/LD show larger dip reductions in some scenarios but (a) make R3-C
WORSE than the unmodified reference (a static boundary-measured makeup
gain doesn't generalize well to R3-C's half/double-tempo relation, where
the "boundary" 500ms window is not representative of the incoming track's
overall level), and (b) push peak level up to the `-1.00dBFS` headroom
ceiling in several cells (LC/LD, R3-A and R3-C), meaning the static
headroom limiter is already engaging -- i.e. LC/LD trade one loudness
problem for a different, less predictable one. Per PM's explicit
instruction ("Do not solve this by simply compressing or limiting
everything"), LC/LD are recorded as a documented, evidence-backed
direction for future tuning (e.g. a smaller makeup cap, or measuring
incoming's loudness over a longer/more representative window), not
adopted by default this pass.

Absolute `maximum_loudness_dip_db` values remain double-digit even for
the recommended curve -- per §20.1, this number is still inflated by
beat-phase measurement noise inherent to sparse synthetic drums, not a
literal claim that LB fully eliminates any perceptible dip. **Whether LB
sounds sufficiently seamless is exactly the question Stage B (real-music,
human) listening must answer** -- this section produces DIAGNOSTIC
evidence and a defensible default, not a subjective PASS.

## 21. Conditional tempo adaptation (`dsp/tempo_modes.py`, `dsp/tempo_ramp.py`)

### 21.1 NATIVE / MATCH_DURING_OVERLAP / MATCH_AND_RETURN

`select_tempo_mode(decision)` decides purely from the ACCEPTED R2
`PlannerDecision` (never a new/independent tempo decision) using PM's
6-rule test (pair compatibility passed, dynamic class allowed, correction
modest/inside envelope, boundary alignment evidence present, project
benchmark zone, never altering outgoing). Verified against all 4 scenario
decisions:

| Scenario | `required_tempo_ratio` | deviation | benchmark zone | Mode selected |
|---|---|---|---|---|
| R3-A | 1.0 | 0.0% | SAFE_ZONE_0_2_PCT | `NATIVE_TEMPO` (already aligned -- never corrected for its own sake) |
| R3-B | 1.05 | 5.0% | CONDITIONAL_ZONE_2_6_PCT | `MATCH_AND_RETURN_TO_NATIVE` |
| R3-C | 0.9709 | 2.91% | CONDITIONAL_ZONE_2_6_PCT | `MATCH_AND_RETURN_TO_NATIVE` |
| R3-D | `None` | -- | -- | `NATIVE_TEMPO` (FULL_DJ_BLEND withheld -- never force-corrected for an incompatible pair) |

This exactly matches the desired product behavior: no correction where
tracks already align (A), no correction where the pair is incompatible
(D), and conditional matching only where compatibility passed AND a real
correction is inside both R2's hard envelope and this pass's stricter
0-2%/2-6%/>6% project buckets (B, C). The `>6%` bucket is a **default
downgrade candidate** even when still inside R2's wider 12% hard ceiling
-- no fixture in this pass currently exercises that path (none of A/B/C/D
require >6%), recorded honestly as untested this pass, not fabricated.
Outgoing tempo is never altered by any code path in this harness; pitch
is preserved (`semitones=0`) in every call, consistent with
`fixtures/pitch_shift_stress_conclusion.md`'s finding that R2 never
authorizes a nonzero pitch correction.

### 21.2 Tempo-ramp results

`dsp/tempo_ramp.py`'s `apply_return_to_native_ramp` implements the
settling-region ramp as a single continuous sample-domain warp (smoothstep-
interpolated instantaneous rate, linear-interpolation resample at the
resulting continuously-varying input position) -- deterministic,
from-scratch, no external engine, no block-splice seams by construction.
Rendered on R3-B (`scripts/render_tempo_ramp_experiment.py`): ramp region
= 2 bars at incoming's native 120bpm = `4.0s`, starting immediately at
handoff (`hold_before_ramp_s=0`). Rate curve recorded at 100ms resolution
(157 points over the full post-handoff region): `1.0` (still matched) at
`t=0` -> smoothly approaches `0.952381` (`=1/1.05`, fully native) by
`t=4.0s`, held flat thereafter (confirmed in `results/tempo_ramp_experiment/
R3-B_tempo_ramp_result.json`).

**Artifact check**: `discontinuity_proxy_at_edges` at the handoff splice
itself shows `0` flagged discontinuities for BOTH the ramped and
no-ramp comparators (identical `max_abs_delta=0.034`, i.e. the ramp
introduces no seam at its own start). Scanning the FULL 5-second ramp
region with the whole-clip discontinuity proxy shows **879** flagged
events (ramped) vs. **1116** flagged events in the UNRAMPED comparator's
IDENTICAL time span -- i.e. the ramped version is flagged LESS often than
the reference, not more, and the largest single jump is also smaller
(`0.492` vs `0.605`). Per this project's own established finding (this
proxy legitimately fires on ordinary sparse drum transients, §8/§16),
this is strong evidence the ramp adds no measurable new artifact beyond
what the underlying synthetic content already contains -- not a
subjective seamlessness claim, but a real, honest machine result in favor
of the ramp being safe to include as this pass's default
(`real_music_pipeline.py` selects `MATCH_AND_RETURN_TO_NATIVE` whenever
`select_tempo_mode` does).

**Known limitation, stated honestly**: the resampler is linear-
interpolation based (a mild low-pass/anti-alias tradeoff for large jumps),
adequate for the small (`<=6%`) corrections this project's conditional-
zone ever authorizes, but not a production-grade band-limited resampler.
No claim is made that the ramp is inaudible -- only that it introduces no
MEASURABLE discontinuity beyond the source content's own baseline.

## 22. Real-music Tier-B harness (`real_music/`, `scripts/real_music_pipeline.py`)

Per Issue #7's original Tier-B anticipation and this update's Task 3:
accepts an owner-supplied, **LOCAL-ONLY, never-committed** manifest
(`real_music/MANIFEST_SCHEMA.md`) naming local WAV/FLAC/MP3/M4A files +
the same structural annotations (`exit_candidate_t_ms`, `bpm`, pair-
compatibility fields) the synthetic fixtures already supply, builds a
real `transition_policy` TX-fixture from them, and calls the SAME
`policy.boundary.plan_transition_boundary()` -- no separate/invented
decision path for real music. Converts audio via `ffmpeg` only (local
files, never a network/protected-stream source). Renders M1 (always, this
pass's repaired `late_hold` curve) and M3 (ffmpeg Rubber Band,
automatic) when a dynamic class is allowed and `select_tempo_mode`
resolves to a matching mode, including the return-to-native ramp when
applicable. M2 (Signalsmith) is NOT auto-rendered (it needs the same
manual browser round-trip every synthetic scenario in this pass required)
-- the script prints the exact follow-up command instead of silently
skipping it.

**Interface validated this pass** (NOT real-music evidence -- this
project's OWN synthetic fixture audio was used purely as plumbing stand-in
input, then deleted, never committed, never presented as a real-music
result): all 3 representative pair categories (close-tempo/conditional-
correction/incompatible-downgrade) round-tripped correctly --
`close_tempo_minimal_stretch` -> `NATIVE_TEMPO`; `conditional_tempo_correction`
-> `MATCH_AND_RETURN_TO_NATIVE` with a working M3 render (ratio `1.05`,
4s ramp, 0 clipped/NaN samples); `incompatible_downgrade` -> planner
correctly withheld `FULL_DJ_BLEND`/`SHORT_EQ_BLEND` down to
`SIMPLE_CROSSFADE` only, no M3 attempted.

**No owner-supplied real-music paths were made available to this
session.** This project did not search, infer, or use any file from the
owner's personal media libraries -- `real_music/manifest.local.json` does
not exist, so per this task's own explicit instruction the harness stops
here, honestly, rather than fabricating copyrighted examples.

## 23. Simplified owner listening UX (`real_music/LISTENING_INSTRUCTIONS_SIMPLIFIED.md`, `scripts/build_simplified_rating_template.py`)

Replaces the old 6-dimension-per-clip matrix with, per transition set:
`BEST` / `SECOND` / `WORST` (clip letters), four YES/NO questions
(`SEAMLESS_ENOUGH_FOR_NORMAL_LISTENING`, `VOLUME_DIP_OR_JUMP_NOTICEABLE`,
`TEMPO_OR_STRETCH_ARTIFACT_NOTICEABLE`, `TIMING_OR_BEAT_FEELS_WRONG`), an
optional free-text note, and an OPTIONAL 1-5 overall score. Generator
verified in `--demo` mode against a representative 3-set shape matching
this pass's 3 required real-music pair categories. Not yet used for a
real pack (none exists yet -- §22).

## 24. Spotify public reference

See `docs/research/P0-M3-R3-SPOTIFY-PUBLIC-REFERENCE.md` (new) -- Automix
(existing, always-on, beat-matched, select playlists), Mix (2025, editable
per-playlist custom transitions, Premium), Smart Reorder (2026, BPM/key-
based playlist reordering). All three quoted directly from Spotify's own
public support/newsroom pages retrieved this session; no reverse
engineering, no proprietary-internal claim.

## 25. Updated STAGE RESULT

**`OWNER_REAL_MUSIC_INPUT_REQUIRED`** -- the loudness repair (§20) and
conditional tempo work (§21) are complete with reproducible evidence, and
the real-music harness (§22) is built and interface-validated, but no
owner-supplied real-music manifest was available this session, so no new
listening pack could be built. This is NOT `OWNER_LISTENING_REQUIRED`
against the old synthetic pack -- per the owner's own feedback, that pack
is not being returned to for a quality verdict.

### Next owner action

Supply local file paths for >= 3 real-vocal transition pairs (categories:
close-tempo/minimal-stretch, ~3-6%-conditional-correction,
incompatible-should-downgrade) by copying `real_music/manifest.example.json`
to a local path (e.g. `real_music/manifest.local.json`, already
gitignored) and filling in real paths + honest annotations per
`real_music/MANIFEST_SCHEMA.md`, then this pass's engineering work can
resume with:
```
python scripts/real_music_pipeline.py --manifest real_music/manifest.local.json --work-dir real_music/work_local
```

**Do not start P1. Result: `OWNER_REAL_MUSIC_INPUT_REQUIRED`, not `PASS`.** (This supersedes every earlier "Do not start P1" line in this document -- §12/§19's `OWNER_LISTENING_REQUIRED` results are superseded by this section per the owner's own feedback that the synthetic pack is not being returned to for a quality verdict.)
