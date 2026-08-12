# P0-M3-R3 STAGE B — Owner Real-Music Validation

Executes the newest Issue #7 PM comment, "PM STAGE B — OWNER REAL-MUSIC
VALIDATION AUTHORIZED", against the owner-authorized local-only corpus
(~100 tracks; root path deliberately withheld from this document per the
PM comment's own privacy boundary). This document contains **only
sanitized, aggregate, and opaque-ID evidence** — no filenames, paths,
hashes, or per-track private identity.

## 1. Corpus inventory

100 supported audio files were found under the authorized root (recursive,
no sibling/parent directories touched). Each was assigned a stable opaque
ID (`RM001`–`RM100`, sorted by filename) and analyzed locally. The
ID↔real-path mapping is stored LOCAL ONLY and gitignored
(`tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json`)
and was never included in any committed file, this document, or the
model's own responses.

All 100 tracks decoded and analyzed successfully (0 failures).

## 2. Analysis methodology (`scripts/analyze_owner_corpus.py`)

No trained ML beat/vocal/key model was available in this environment (see
`docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md` for the prior ML-analyzer
feasibility pass). Every estimator below is a from-scratch numpy/scipy
implementation of a standard, textbook DSP technique, computed at a
22.05kHz mono analysis rate:

- **Tempo/BPM**: spectral-flux onset envelope → autocorrelation peak in the
  70–190 BPM range. Confidence = autocorrelation peak prominence (σ above
  the mean across candidate lags).
- **Beat phase**: comb-filter search over the onset envelope for the phase
  offset that maximizes onset energy at that periodicity. Confidence
  thresholds were calibrated against this corpus's own observed margin
  distribution (a sample showed margins clustering 1.3–2.0σ for genuinely
  strong beat locks — not the naive first-guess threshold of 2.2σ, which
  called every track only "MEDIUM").
- **Downbeat/bar phase**: initial attempts using low-band (kick-only)
  onset energy showed near-zero group separation on this corpus (many
  tracks carry kick on every beat, not only the downbeat — an honest
  four-on-the-floor property of the material, not an estimator bug). The
  accepted estimator instead sums z-scored low-band AND broadband onset
  envelopes (a standard weak-evidence ensemble) before grouping by phase;
  this measurably improved discrimination on tracks with a real periodic
  bar-level accent while correctly staying low-confidence where no such
  accent exists.
- **Key**: 12-bin chroma (log-frequency-binned FFT magnitude) correlated
  against Krumhansl–Schmuckler major/minor profiles for all 12 roots.
  Computed BOTH as a whole-track average AND as boundary-localized windows
  (~30s around each candidate exit/entry point, since a track's key at its
  actual transition point can differ from its nominal whole-track key).
  Whole-track/boundary-local agreement on the identical (root, mode) is
  treated as corroborating evidence (confidence raised, never invented
  from nothing).
- **Loudness**: short-window RMS-dBFS, consistent with the render
  pipeline's own `dsp/loudness_diagnostics.py` methodology.
- **Vocal-density proxy (HEURISTIC_PROXY — no source separation
  available)**: 300–3400Hz band-energy ratio × tonal salience
  (1 − spectral flatness) in that band, smoothed ~1s, bucketed into
  LOW/MEDIUM/HIGH per-track by percentile (not a fixed absolute threshold,
  since dense-vocal tracks must be judged against their own distribution).
  A genuine vocal "collision" is modeled as requiring concurrent
  vocal-density on BOTH sides of a boundary — one vocal-light side means no
  collision is possible regardless of the other side's density.
- **Intro/outro structure**: instrumental-tail/lead detection (sustained
  low-vocal-density, above-silence-floor runs) plus explicit
  leading-authored-silence detection (distinct from an audible instrumental
  intro) so a candidate boundary is never silently placed inside true
  digital silence.

## 3. Sanitized aggregate corpus statistics

```
tracks analyzed:            100 / 100 (0 failures)
tempo (BPM):                min 69.8, median 112.3, max 172.3
beat confidence:             HIGH 89, MEDIUM 11
downbeat confidence:         HIGH 28, MEDIUM 36, LOW 19, NONE 17
key confidence (whole-track): HIGH 35, MEDIUM 16, LOW 21, NONE 28
detected instrumental outro tail: 5 / 100
detected leading-silence skip:    24 / 100
```

## 4. Pair selection (`scripts/select_real_music_pairs.py`)

Exhaustive search over all ordered pairs (~9,900) using the SAME
compatibility model the accepted R2 planner uses
(`tools/p0m3/transition_policy/policy/compatibility.py`
`evaluate_pair_compatibility`), never a separately-invented rule. No
manual/cherry-picked selection — deterministic scoring + lexicographic
tie-break.

- **V1 (close_tempo_minimal_stretch)**: pool of 620 candidate pairs with
  ≤2% tempo deviation; selected pair has 0.0% deviation (near-identical
  BPM), `HARMONIC_COMPATIBLE`, beat confidence HIGH on both sides.
- **V2 (conditional_tempo_correction)**: pool of exactly 2 candidate pairs
  clearing every FULL_DJ_BLEND hard gate (genre/tempo/beat/downbeat/
  structure/texture/vocal-safety/harmonic/analysis-confidence) AND landing
  in the 3–6% conditional zone. Selected pair: 4.17% required tempo
  deviation, both sides beat+downbeat confidence HIGH,
  `HARMONIC_COMPATIBLE` (perfect-fourth key relation, corroborated across
  independent whole-track/boundary-local windows).
- **V3 (incompatible_downgrade)**: pool of 6,801 candidate pairs with an
  `EXCESSIVE_STRETCH` tempo relation (>12% deviation even after
  half/double-time folding). Selected pair: 15.79% required deviation
  (genuinely measured BPM mismatch, not fabricated), also
  `HARMONIC_INCOMPATIBLE` and downbeat-confidence-insufficient on the
  outgoing side — multiple independent, honestly-measured reasons
  `FULL_DJ_BLEND` is correctly withheld.

Full per-pair rationale (opaque IDs, confidence values, reason codes) is in
`real_music/work_local/selection_rationale_sanitized.json` (PM ZIP).

## 5. Planner + render pipeline

Every selected pair was converted to the same TX-fixture shape every
synthetic scenario in this pass uses and passed to the REAL, unmodified
`policy.boundary.plan_transition_boundary` — no hand-edited
`PlannerDecision` JSON. Confirmed outcomes:

- **V1**: `decision_type=TRANSITION`, `allowed_transition_class_set=
  [SHORT_EQ_BLEND, SIMPLE_CROSSFADE]`, `tempo_mode=NATIVE_TEMPO` (no
  stretch, as intended).
- **V2**: `allowed_transition_class_set=[FULL_DJ_BLEND, SHORT_EQ_BLEND,
  SIMPLE_CROSSFADE]`, `tempo_mode=MATCH_INCOMING_DURING_OVERLAP` (the
  planner's own `MATCH_AND_RETURN_TO_NATIVE` preference was correctly
  downgraded — `ramp_is_safe` measured −70.92 cents drift, outside the
  ±5-cent tolerance — matching this pass's explicit PM direction never to
  force the unvalidated return-to-native ramp).
- **V3**: `allowed_transition_class_set=[SIMPLE_CROSSFADE]` —
  `FULL_DJ_BLEND` correctly withheld, `tempo_mode=NATIVE_TEMPO` (no forced
  correction for an incompatible pair).

A/B/C render policy (same shared boundary per pair, `dsp/mixing.py`):

- **A** — equal-power reference, no tempo correction.
- **B** — late-outgoing-hold loudness candidate, no tempo correction.
- **C** (only when FULL_DJ_BLEND is allowed and a real correction is
  warranted, V2 only) — **owner-facing C is the official pinned
  Signalsmith Stretch WASM/WebAudio engine** (`web/stretch_worker.html`,
  manual browser round-trip, same mechanism `dsp/render_m2_signalsmith.py`
  uses for synthetic scenarios), `MATCH_INCOMING_DURING_OVERLAP`, pitch
  preserved (0 semitones), never the unsafe return-to-native ramp. A
  SEPARATE ffmpeg-Rubber-Band C candidate was also rendered but is
  PM/reference-only and is never included in the owner pack.

## 6. Privacy + blinding

- No source audio, derived listening WAV, filename, path, hash, tag, or
  fingerprint from the private corpus was committed.
- Owner listening clips (`real_music/work_local/owner_listening_clips/`,
  local only) are 30s excerpts, PCM16, 44.1kHz stereo, RIFF/fmt /data only
  (no metadata chunk for anything to hide in), opaque filenames
  (`V1-A.wav`, `V2-C.wav`, …).
- A NEW blind seed (`AUTOMIX_R3_REAL_MUSIC_BLIND_SEED`, distinct
  mechanism/env-var from the synthetic pack's `AUTOMIX_R3_BLIND_SEED`) maps
  blind letters to internal candidates; the seed and full mapping are
  LOCAL ONLY and gitignored, never in the owner ZIP, never printed in the
  final handoff.
- `scripts/verify_real_music_stage_b.py` — **ALL CHECKS PASS** (privacy,
  format parity, V2 zone/engine/pitch-preservation, V3 no-forced-FULL_DJ,
  shared-boundary, new-seed-not-reused).

## 7. Regression status

`selftest_fail_closed.py` (8/8), `verify_beat_grid_membership.py`,
`verify_cross_method_consistency.py`, and
`selftest_pre_real_music_repair.py` all still **PASS** — no prior
sample-rate/beat-grid/fail-closed/loudness/privacy repair regressed.

## Result

`OWNER_REAL_MUSIC_LISTENING_REQUIRED`. No quality PASS is claimed. P1 has
not started.
