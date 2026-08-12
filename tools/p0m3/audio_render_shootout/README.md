# P0-M3-R3 -- Audio Render Shootout

Disposable research harness for GitHub Issue #7 (`P0-M3-R3 -- Seamless DSP
render shootout + blinded owner listening`). Renders the accepted R2
transition-policy boundary (`tools/p0m3/transition_policy/`) as actual WAV
audio using four methods (M0-M3) so a human can blind-listen to them.

**This is a P0 research harness, not the P1 production engine.** See
`AGENTS.md` / `docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md` for the
full report and stop conditions.

## Audio is LOCAL ONLY

Per `AGENTS.md` rule 4 and Issue #7: no `.wav` file anywhere under this
directory is committed (`.gitignore` enforces `*.wav`, `audio_local/`,
`serve_tmp/`). Only generator source, fixture metadata, planner-decision
JSON, machine-metrics JSON, and documentation are committed.

## Layout

```
fixtures/
  scenario_fixtures.py         -- R2 planner input fixtures (source of truth) for scenarios A-D
  generate_planner_decisions.py -- calls the REAL R2 planner, writes fixtures/planner_decisions/*.json (committed)
  synth.py                     -- deterministic synthetic music generator
  generate_audio.py            -- writes audio_local/*.wav (gitignored) + fixtures/ground_truth/*.json (committed)
  pitch_shift_stress_conclusion.md -- scenario E conclusion (NOT_TESTED_NO_VALID_PLANNER_INPUT)
dsp/
  wav_io.py                    -- float32/pcm16 WAV read/write (stdlib only)
  mixing.py                    -- equal-power gain, bass/EQ handoff, headroom/clip-safety
  safety_metrics.py            -- diagnostic-only signal-safety/loudness/alignment metrics
  render_common.py             -- shared planner-decision consumption + fail-closed alignment guard
  render_m0.py / render_m1.py  -- pure-Python baseline/reference renderers
  render_m2_signalsmith.py     -- Signalsmith Stretch candidate (browser-WASM bridge)
  render_m3_rubberband.py      -- Rubber Band quality reference (ffmpeg subprocess)
web/
  stretch_worker.html          -- drives the OFFICIAL pinned SignalsmithStretch.mjs in a real browser AudioWorklet/OfflineAudioContext
vendor/                        -- gitignored, re-fetchable pinned Signalsmith web release (see provenance doc)
scripts/
  serve.py                     -- local static+upload server for the M2 browser bridge
  render_all.py                -- writes M0/M1 renders to results/
  compute_metrics.py           -- aggregates results/machine_metrics.json
  build_listening_pack.py      -- extracts + blinds the 11 owner-listening clips, writes results/blind_key.json
  build_owner_pack.py          -- assembles P0-M3-R3-OWNER-LISTENING.zip (repo root, local only)
  verify_blinding.py           -- Issue #7's "BLINDING VERIFICATION" checks
  selftest_fail_closed.py      -- AC7 proof that missing FULL_DJ alignment fields raise, not guess
results/                       -- gitignored audio; committed: machine_metrics.json, blind_key.json* (*PM-only, see below)
```

## Setup

```bash
python3 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # numpy, scipy, psutil
```

Requires (already present in this environment; see
`docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md` for the full audit):
- `ffmpeg` built with `--enable-librubberband` (for M3)
- A Chromium-based browser pane (`mcp__Claude_Browser` in this session) for M2's WASM bridge -- native C++ compilation is unavailable in this environment (no `cl.exe`/`g++`/`emcc` on `PATH`), so M2 uses the pinned commit's OWN official prebuilt `web/release/SignalsmithStretch.mjs`, run unmodified inside a real `OfflineAudioContext`/`AudioWorkletNode`.

## Reproduction commands (exact order used)

```bash
# 1. Planner decisions (calls the REAL accepted R2 planner)
python fixtures/generate_planner_decisions.py

# 2. Synthetic source audio (LOCAL ONLY)
python fixtures/generate_audio.py

# 3. M0/M1 (pure Python, no external engine)
python scripts/render_all.py

# 4. M2 (Signalsmith, browser-WASM bridge) -- one job per FULL_DJ_BLEND scenario (A/B/C)
python scripts/serve.py 8765 &
python dsp/render_m2_signalsmith.py prepare R3-A   # prints a URL; open it in a real browser, wait for title "DONE ..."
python dsp/render_m2_signalsmith.py finish R3-A
python dsp/render_m2_signalsmith.py prepare R3-B
python dsp/render_m2_signalsmith.py finish R3-B
python dsp/render_m2_signalsmith.py prepare R3-C
python dsp/render_m2_signalsmith.py finish R3-C
python dsp/render_m2_signalsmith.py fallback R3-D   # FULL_DJ_BLEND withheld -- no browser job needed

# 5. M3 (Rubber Band via ffmpeg, synchronous)
python dsp/render_m3_rubberband.py R3-A
python dsp/render_m3_rubberband.py R3-B
python dsp/render_m3_rubberband.py R3-C
python dsp/render_m3_rubberband.py R3-D

# 6. Machine metrics
python scripts/compute_metrics.py

# 7. Blinded owner listening pack + verification
python scripts/build_listening_pack.py
python scripts/build_owner_pack.py
python scripts/verify_blinding.py

# 8. AC7 fail-closed self-test
python scripts/selftest_fail_closed.py
```

## Scenarios

| ID | Purpose | bpm_out / bpm_in | required_tempo_ratio |
|---|---|---|---|
| R3-A | no-stretch control | 120 / 120 | 1.0 (DIRECT) |
| R3-B | moderate direct stretch (~5%) | 126 / 120 | 1.05 (DIRECT) |
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
  pinned WASM release. Falls back to the SAME class M1 would render when
  `FULL_DJ_BLEND` is withheld (R3-D) -- never forces complex DSP.
- **M3** -- Rubber Band quality reference (`ffmpeg -af rubberband=...`),
  same boundary/gain/EQ policy as M2, isolated as an external subprocess
  only (`QUALITY_REFERENCE_ONLY`, no code linked/copied).

## Machine metrics summary

See `results/machine_metrics.json` for the full 16-cell (4 scenarios x 4
methods) machine evidence. Headline facts (all reproduced by the commands
above):

- Zero NaN/Inf samples, zero clipped samples, across all 16 renders.
- M2/M3 apply `required_tempo_ratio` exactly (`stretch_ratio_error = 0.0`
  in every FULL_DJ_BLEND cell); M0/M1 deliberately do not (`stretch_ratio_error`
  = `0.05` for R3-B, `0.0291` for R3-C), the documented weak/reference
  behavior.
- Synthetic-ground-truth `beat_alignment_error_ms = 0.0` in all 16 cells
  (matched-filter marker detection against the authored beat grid).
- R3-D: all four methods render only `SIMPLE_CROSSFADE` -- `FULL_DJ_BLEND`
  is never forced.

**Metrics are diagnostic only** (Issue #7 / AGENTS.md rule 2) -- none of the
above is a subjective-seamlessness claim; see the STAGE-A verdict rule in
`docs/research/P0-M3-R3-SEAMLESS-RENDER-SHOOTOUT.md`.

## Blind listening pack

`P0-M3-R3-OWNER-LISTENING.zip` (repo root, LOCAL ONLY, never committed):
11 opaquely-named clips (`S1-A.wav` ... `S4-B.wav`), `LISTENING_INSTRUCTIONS.md`,
`OWNER_RATINGS_TEMPLATE.json`. No method name appears anywhere in it
(machine-verified by `scripts/verify_blinding.py`). The letter-to-method
mapping is a deterministic seeded shuffle (`results/blind_key.json`,
PM-only, never in the owner ZIP).
