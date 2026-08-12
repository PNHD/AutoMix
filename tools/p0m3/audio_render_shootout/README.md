# P0-M3-R3 -- Audio Render Shootout

Disposable research harness for GitHub Issue #7 (`P0-M3-R3 -- Seamless DSP
render shootout + blinded owner listening`). Renders the accepted R2
transition-policy boundary (`tools/p0m3/transition_policy/`) as actual WAV
audio using four methods (M0-M3) so a human can blind-listen to them.

**This is a P0 research harness, not the P1 production engine.** See
`AGENTS.md` / `docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md` (incl.
its "PM STAGE A REVIEW -- REPAIR" sections 16-19) for the full report,
repair history, and stop conditions.

## Audio is LOCAL ONLY

Per `AGENTS.md` rule 4 and Issue #7: no `.wav` file anywhere under this
directory is committed (`.gitignore` enforces `*.wav`, `audio_local/`,
`serve_tmp/`, `premix_diag/`). `results/blind_key.json` is ALSO gitignored
(PM STAGE A REVIEW R5 repair -- it must never be readable from repository
history). Only generator source, fixture metadata, planner-decision JSON,
machine-metrics JSON, ground-truth JSON, and documentation are committed.

## Layout

```
fixtures/
  scenario_fixtures.py         -- R2 planner input fixtures (source of truth) for scenarios A-D
  generate_planner_decisions.py -- calls the REAL R2 planner, writes fixtures/planner_decisions/*.json (committed)
  synth.py                     -- deterministic synthetic music generator; embed_markers=False for clean (owner) audio
  generate_audio.py            -- writes audio_local/*.wav + *_clean.wav (gitignored) + fixtures/ground_truth/*.json (committed)
  pitch_shift_stress_conclusion.md -- scenario E conclusion (NOT_TESTED_NO_VALID_PLANNER_INPUT)
dsp/
  wav_io.py                    -- float32/pcm16 WAV read/write (stdlib only)
  markers.py                   -- distinct outgoing/incoming diagnostic marker signatures (R3 repair)
  mixing.py                    -- equal-power gain, bass/EQ handoff, headroom/clip-safety, sample-rate normalization (R1 repair)
  safety_metrics.py            -- diagnostic-only signal-safety/loudness/alignment metrics (prominence-based marker confidence)
  render_common.py             -- shared planner-decision consumption, fail-closed alignment guard, clean/diagnostic variant loading, premix diagnostic snapshots
  render_m0.py / render_m1.py  -- pure-Python baseline/reference renderers
  render_m2_signalsmith.py     -- Signalsmith Stretch candidate (browser-WASM bridge)
  render_m3_rubberband.py      -- Rubber Band quality reference (ffmpeg subprocess)
web/
  stretch_worker.html          -- drives the OFFICIAL pinned SignalsmithStretch.mjs at an explicit, asserted sample rate; records stretch.latency() + scheduling sidecar (R1/R6 repair)
vendor/                        -- gitignored, re-fetchable pinned Signalsmith web release (see provenance doc)
scripts/
  serve.py                     -- local static+upload server for the M2 browser bridge
  render_all.py                -- writes M0/M1 diagnostic + clean renders to results/
  compute_metrics.py           -- aggregates results/machine_metrics.json (premix-buffer marker detection, R3 repair)
  verify_cross_method_consistency.py -- R1 repair verifier: sr/channels/overlap-duration parity across M0-M3
  verify_beat_grid_membership.py     -- R2 repair verifier: FULL_DJ alignment targets are on the real beat/downbeat grid
  build_listening_pack.py      -- extracts + blinds the 11 owner-listening clips from CLEAN renders only; requires AUTOMIX_R3_BLIND_SEED (R4/R5 repair)
  build_owner_pack.py          -- assembles P0-M3-R3-OWNER-LISTENING.zip (repo root, local only)
  build_pm_pack.py             -- assembles P0-M3-R3-PM-REVIEW.zip (repo root, local only)
  verify_blinding.py           -- Issue #7's "BLINDING VERIFICATION" checks + R5 format-parity/seed-provenance checks
  selftest_fail_closed.py      -- AC7 proof that missing FULL_DJ alignment fields raise, not guess
  real_music_pipeline.py       -- Tier-B real-music harness (LOCAL-ONLY manifest -> A/B/C same-boundary comparator, see docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md §26)
  selftest_pre_real_music_repair.py -- PM REVIEW "PRE-REAL-MUSIC REPAIR REQUIRED" R1-R4 regression proof + prior-result non-regression checks
results/                       -- gitignored audio + blind_key.json; committed: machine_metrics.json, render_meta*/*.json
```

## Setup

```bash
python3 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # numpy, scipy, psutil
```

Requires (already present in this environment; see
`docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md` for the full audit):
- `ffmpeg` built with `--enable-librubberband` (for M3)
- A Chromium-based browser pane (`mcp__Claude_Browser` in this session) for M2's WASM bridge -- native C++ compilation is unavailable in this environment (no `cl.exe`/`g++`/`emcc` on `PATH`), so M2 uses the pinned commit's OWN official prebuilt `web/release/SignalsmithStretch.mjs`, run unmodified inside a real `OfflineAudioContext`/`AudioWorkletNode`, at an explicitly requested and asserted canonical sample rate (R1 repair).

## Reproduction commands (exact order used, post-repair)

```bash
# 1. Planner decisions (calls the REAL accepted R2 planner)
python fixtures/generate_planner_decisions.py

# 2. Synthetic source audio: diagnostic (marker-embedded) + clean (marker-free), LOCAL ONLY
python fixtures/generate_audio.py

# 3. M0/M1 (pure Python, no external engine) -- diagnostic for all 4 scenarios, clean for the cells the owner pack needs
python scripts/render_all.py

# 4. M2 (Signalsmith, browser-WASM bridge) -- diagnostic AND clean variants, A/B/C (6 browser round-trips)
python scripts/serve.py 8765 &
python dsp/render_m2_signalsmith.py prepare R3-A diagnostic   # prints a URL; open it in a real browser, wait for title "DONE ..."
python dsp/render_m2_signalsmith.py finish  R3-A diagnostic
python dsp/render_m2_signalsmith.py prepare R3-A clean
python dsp/render_m2_signalsmith.py finish  R3-A clean
# ... repeat for R3-B, R3-C ...
python dsp/render_m2_signalsmith.py fallback R3-D diagnostic   # FULL_DJ_BLEND withheld -- no browser job needed
python dsp/render_m2_signalsmith.py fallback R3-D clean

# 5. M3 (Rubber Band via ffmpeg, synchronous) -- diagnostic AND clean for A/B/C, diagnostic only for D
python dsp/render_m3_rubberband.py R3-A diagnostic
python dsp/render_m3_rubberband.py R3-A clean
# ... repeat for R3-B, R3-C ...
python dsp/render_m3_rubberband.py R3-D diagnostic

# 6. Repair verifiers + machine metrics
python scripts/verify_cross_method_consistency.py   # R1
python scripts/verify_beat_grid_membership.py        # R2
python scripts/compute_metrics.py                    # R3 (premix-buffer marker detection)

# 7. AC7 fail-closed self-test
python scripts/selftest_fail_closed.py

# 8. Blinded owner listening pack (clean-only) + PM pack + verification
#    AUTOMIX_R3_BLIND_SEED is a NEW secret integer, supplied at run time only
#    (never committed, never hardcoded) -- R5 repair.
AUTOMIX_R3_BLIND_SEED=<secret> python scripts/build_listening_pack.py
python scripts/build_owner_pack.py
AUTOMIX_R3_BLIND_SEED=<same secret> python scripts/verify_blinding.py
python scripts/build_pm_pack.py
```

## Scenarios

| ID | Purpose | bpm_out / bpm_in | required_tempo_ratio |
|---|---|---|---|
| R3-A | no-stretch control | 120 / 120 | 1.0 (DIRECT) |
| R3-B | moderate direct stretch (~5%) | 126 / 120 | 1.05 (DIRECT) -- outgoing exit at `t=45714ms`, corrected onto the real beat/downbeat grid (PM STAGE A REVIEW R2 repair; was `45000ms`, a non-beat half-beat offset) |
| R3-C | half/double + residual | 120 / 61.8 | 0.9709 (HALF_DOUBLE) |
| R3-D | incompatible pair (forced fallback) | 120 / 120, pair-level HIGH vocal-collision override | N/A -- FULL_DJ_BLEND withheld |
| E | pitch-shift stress | -- | `NOT_TESTED_NO_VALID_PLANNER_INPUT`, see `fixtures/pitch_shift_stress_conclusion.md` |

All four PlannerDecisions are produced by directly calling
`tools/p0m3/transition_policy/policy/boundary.plan_transition_boundary()` --
never hand-fabricated.

## Methods

- **M0** -- intentionally weak baseline: linear (non-equal-power) gain, no
  tempo correction even when required, no bass/EQ handoff, no alignment.
- **M1** -- planner-correct `SIMPLE_CROSSFADE` reference: equal-power gain
  only, no tempo correction (by class definition), no bass/EQ handoff.
- **M2** -- Signalsmith Stretch candidate: equal-power gain, bass/EQ
  handoff, beat/downbeat-anchored alignment offset, applies
  `required_tempo_ratio`/pitch from the PlannerDecision via the official
  pinned WASM release, at an explicitly requested and asserted canonical
  sample rate. Falls back to the SAME class M1 would render when
  `FULL_DJ_BLEND` is withheld (R3-D) -- never forces complex DSP.
- **M3** -- Rubber Band quality reference (`ffmpeg -af rubberband=...`),
  same boundary/gain/EQ policy as M2, isolated as an external subprocess
  only (`QUALITY_REFERENCE_ONLY`, no code linked/copied).

## Clean vs. diagnostic audio (PM STAGE A REVIEW R4 repair)

Every scenario has TWO source-audio variants:
- **diagnostic** -- embeds distinct outgoing/incoming alignment markers
  (`dsp/markers.py`); used for the full DSP pipeline, machine alignment
  metrics, and PM forensic review. Never used for owner listening.
- **clean** -- byte-identical musical content, zero diagnostic markers;
  used ONLY for the owner-listening pack.

## Machine metrics summary

See `results/machine_metrics.json` for the full 16-cell (4 scenarios x 4
methods) machine evidence. Headline facts (all reproduced by the commands
above):

- Zero NaN/Inf samples, zero clipped samples, across all 16 renders.
- M2/M3 apply `required_tempo_ratio` exactly (`stretch_ratio_error = 0.0`
  in every FULL_DJ_BLEND cell); M0/M1 deliberately do not
  (`stretch_ratio_error = 0.05` for R3-B, `0.0291` for R3-C), the
  documented weak/reference behavior.
- `outgoing_anchor_absolute_error_ms` = `0.0` (HIGH confidence) in all 16
  cells. `incoming_anchor_absolute_error_ms` = `0.0` (HIGH confidence) for
  M0/M1/D (no real time-stretch applied); `None`/`UNKNOWN_LOW_CONFIDENCE`
  for M2/M3 on A/B/C -- an honest, non-fabricated result reflecting that a
  short synthetic transient marker is measurably reshaped by phase-vocoder
  time-stretch, not a fabricated `0.0` and not a false large error. See
  the research report §16 for the full account.
- `overlap_duration_ms` is invariant across all 4 methods within each
  scenario (machine-verified, `scripts/verify_cross_method_consistency.py`).
- R3-D: all four methods render only `SIMPLE_CROSSFADE` -- `FULL_DJ_BLEND`
  is never forced.

**Metrics are diagnostic only** (Issue #7 / AGENTS.md rule 2) -- none of the
above is a subjective-seamlessness claim; see the STAGE-A verdict rule in
`docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md`.

## Blind listening pack

`P0-M3-R3-OWNER-LISTENING.zip` (repo root, LOCAL ONLY, never committed):
11 opaquely-named clips (`S1-A.wav` ... `S4-B.wav`, sourced exclusively
from clean renders), `LISTENING_INSTRUCTIONS.md`, `OWNER_RATINGS_TEMPLATE.json`.
No method name appears anywhere in it (machine-verified by
`scripts/verify_blinding.py`, including sample-rate/channel/bit-depth/
duration format-parity checks). The letter-to-method mapping is a
deterministic seeded shuffle from a NEW secret seed supplied via
`AUTOMIX_R3_BLIND_SEED` at build time (never hardcoded in source, never
committed); the mapping is recorded ONLY in `results/blind_key.json`
(gitignored, PM-zip-only, never in the owner ZIP).
