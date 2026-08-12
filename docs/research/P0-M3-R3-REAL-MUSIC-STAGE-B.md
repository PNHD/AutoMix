# P0-M3-R3 STAGE B — Owner Real-Music Validation (REAL-EVIDENCE REPAIR)

Executes the newest Issue #7 PM comment, "PM STAGE B REVIEW — CURRENT
OWNER PACK INVALID / REAL-EVIDENCE REPAIR REQUIRED", against the
owner-authorized local-only corpus (~100 tracks; root path deliberately
withheld from this document per the PM comment's own privacy boundary).
This document contains **only sanitized, aggregate, and opaque-ID
evidence** — no filenames, paths, hashes, or per-track private identity.

## 0. Why this revision exists

The prior Stage B owner pack (SHA-256 beginning `84ad398e...`) is
**permanently invalid** — PM review found the selector's genre, structure,
bass/percussion, and texture evidence were fabricated or non-independent
(derived from beat/downbeat confidence alone, or hardcoded constants), the
incoming entry was force-set to 0ms even when a real nonzero entry was
detected, and the resulting owner-facing renders carried catastrophic
projected loudness holes (~32.8dB / ~37.6dB) that were never screened
pre-render. This document describes the REPAIRED evidence model and its
honest result — not a re-run with weakened gates.

## 1. Repairs applied (`scripts/analyze_owner_corpus.py`, `scripts/select_real_music_pairs.py`)

- **Genre (R1)**: real owner-local embedded-tag evidence only
  (`genre`/`comment`/`description`/`synopsis` ffprobe tag fields,
  deliberately excluding `title` to avoid incidental-wordplay false
  positives — e.g. a track titled "...Rock Paper Scissors..." must never
  be misread as the "rock" genre). Matched against a small documented
  keyword→family sanitizer vocabulary; raw tag text is never written to
  committed evidence. No match → `UNKNOWN` (empty list), which the
  existing, UNCHANGED R2 `genre_ok` gate already treats as incompatible
  (empty-set family intersection) — no weakening of `compatibility.py` was
  needed or made.
- **Structure (R2)**: `structure_compatibility`/`musical_unit_complete`
  now require INDEPENDENT structural evidence — either a detected
  sustained instrumental tail (vocal-density-based), or a genuine
  bar-synchronous "novelty" (self-similarity change-point) peak within ±1
  bar of the candidate, computed from RMS + chroma + spectral centroid +
  spectral flatness (never from beat/downbeat confidence, which only
  supplies the bar period/phase the novelty detector needs to know where
  bars fall). No qualifying evidence → honestly `LOW`/`UNKNOWN`.
- **Bass/percussion + texture (R3)**: `bass_percussion_collision_risk` is
  now a MEASURED, percentile-bucketed 30–150Hz band-energy + onset-density
  read at both boundary regions (never a hardcoded `LOW`).
  `intro_outro_texture_compatible` now requires boundary-local spectral
  centroid, spectral flatness, AND onset-density gaps all below
  corpus-calibrated thresholds (not RMS+vocal-risk alone).
  `analysis_confidence` reflects the MEASURED STRENGTH of the
  structure/genre/harmonic evidence specifically (not beat/downbeat, which
  already has its own independent gate — avoiding double-counting the same
  evidence against the same bar twice).
- **Incoming entry (R4)**: `real_music_pipeline.py::build_tx_fixture()` now
  wires `leading_silence_is_authored_non_musical` /
  `leading_silence_ms` through to
  `policy.boundary.incoming_effective_content_start_ms`, so a genuinely
  detected nonzero entry (an authored-silence-skip or instrumental-lead
  end) is actually ACCEPTED by the real planner instead of being silently
  forced back to 0ms.
- **Pre-render loudness/energy (R5)**: every candidate now carries
  SOURCE-level (pre-render) projected loudness-gap and bass-gap
  diagnostics, computed directly from the analyzer's boundary-region
  measurements — used for ranking, never for post-render cherry-picking.
- **Ranking (R6)**: hard safety gates → near-whole-song preservation →
  clean entry → structure/texture/vocal/bass safety → source
  loudness/energy continuity → harmonic → tempo-correction burden →
  deterministic opaque-ID tie-break **last**. A STRONG-energy candidate
  now provably outranks an otherwise-equal WEAK-energy one regardless of
  ID ordering (see the mutation-test evidence, §5).
- **Verifier (R7)**: the private authorized-root marker is no longer
  hardcoded anywhere in tracked source (not even as a regression-test
  comparison literal, which would recreate the same self-invalidation bug)
  — it is supplied only via `--private-sentinel` / an env var at run time.
  The tracked-file privacy scan reads content via `git show <ref>:<path>`
  so it validates the actual committed/pushed blob, not just the working
  tree.

## 2. Sanitized aggregate corpus statistics (repaired analyzer, full 100-track run)

```
tracks analyzed:              100 / 100 (0 failures)
tempo (BPM):                  min 69.8, median 112.3, max 172.3
beat confidence:               HIGH 89, MEDIUM 11
downbeat confidence:           HIGH 28, MEDIUM 36, LOW 19, NONE 17
key confidence (whole-track):  HIGH 35, MEDIUM 16, LOW 21, NONE 28
exit structural evidence:      INSTRUMENTAL_TAIL 5, NOVELTY_PEAK 10, NONE 85
tracks with known genre evidence: 33 / 100 (67 UNKNOWN — real embedded
                                   metadata is mostly generic YouTube
                                   video categories, not music genre)
```

## 3. Pair selection outcome (honest, post-repair)

Exhaustive search over ~9,900 ordered pairs using the SAME
`evaluate_pair_compatibility` the accepted R2 planner uses, with the
additional constraint that a candidate's outgoing exit must itself be
RENDERABLE (structure confidence ≥ MEDIUM — otherwise the real planner's
own `policy/eligibility.py` Guard 2 rejects it as `NO_SAFE_OUTGOING_EXIT`,
independent of transition class).

- **V1 (close_tempo_minimal_stretch): `PARTIAL_NO_VALID_V1`.** Pool size
  after the honest hard-gate filter: **0**. Dominant independent
  bottlenecks among the 620 tempo-eligible candidates: genre evidence
  incompatible/unknown (≈95%), texture gap above the corpus-calibrated
  threshold (≈95%), downbeat confidence insufficient on at least one side
  (≈93%) — these compound multiplicatively; zero candidates satisfied all
  simultaneously in this specific 100-track corpus.
- **V2 (conditional_tempo_correction): `PARTIAL_NO_VALID_V2`.** Pool size:
  **0** (same compounding bottlenecks among the 1,025 tempo-eligible
  candidates).
- **V3 (incompatible_downgrade): SELECTED.** Pool size 1,057 (after the
  renderability filter). Selected pair: 20.83% required tempo deviation
  (genuine `EXCESSIVE_STRETCH`, unrelated to the two BPM values used in
  the now-invalidated pack), `HARMONIC_INCOMPATIBLE`,
  `GENRE_INCOMPATIBLE`, downbeat-confidence-insufficient on the incoming
  side — several independent, honestly-measured reasons `FULL_DJ_BLEND` is
  correctly withheld. Structure evidence: a genuine detected instrumental
  tail on the outgoing side. Pre-render projected combined energy gap:
  ~40dB (flagged `WEAK` by the new ranking — expected and appropriate for
  a deliberately-mismatched negative control, not a defect).

**No gate was weakened to manufacture a V1 or V2 pair.** This is the
project's first fully evidence-honest pair-selection pass on this corpus;
the previous (invalid) pack's V1/V2 existed only because structure,
texture, and bass/percussion evidence were fabricated from proxies that
had no real independent basis.

## 4. Planner + render outcome

- **V3**: `decision_type=TRANSITION`, `allowed_transition_class_set=
  [SIMPLE_CROSSFADE]` (FULL_DJ_BLEND correctly withheld),
  `tempo_mode=NATIVE_TEMPO`. Rendered candidates A (equal-power) and B
  (late-outgoing-hold) — no C (no tempo correction is ever attempted for a
  planner-withheld FULL_DJ pair). Post-render `loudness_max_dip_db` ≈
  16.0dB for both A and B — a substantial improvement over the invalidated
  pack's ~37.6dB for the same category, attributable to the pre-render
  energy-gap-aware ranking (R5/R6), even though V3 is not expected to be a
  "clean" transition by design.

## 5. Verifier + mutation-test evidence

`scripts/verify_real_music_stage_b.py` (post-commit, run against the
pushed HEAD with a locally-supplied `--private-sentinel`) — see
`HANDOFF_TO_PM.md` for the exact command and pass/fail result.

`scripts/mutation_test_real_music_stage_b.py` — **ALL 11 REQUIRED
MUTATIONS PASS**, each proving the specific repaired guarantee holds
against a crafted adversarial input (never real owner data):
genre never fabricated, structure/`musical_unit_complete` never derived
from beat/downbeat alone, bass/percussion collision is measured (not a
constant), texture requires real timbral/rhythmic evidence, incoming entry
is never forced to 0ms when a real nonzero entry was detected, FULL_DJ is
withheld when ANY one independent gate is UNKNOWN/unsafe, ranking prefers
STRONG energy over WEAK regardless of opaque-ID order, a catastrophic
projected loudness hole ranks below a safer alternative, the verifier
itself never hardcodes/defaults its private sentinel, and all prior
fail-closed/beat-grid/cross-method regressions still pass.

## 6. Privacy + blinding

- No source audio, derived listening WAV, filename, path, hash, tag, or
  fingerprint from the private corpus was committed.
- Owner listening clips (local only) are 30s excerpts, PCM16, 44.1kHz
  stereo, RIFF `fmt `/`data`-only (no metadata chunk), opaque filenames
  (`V3-A.wav`, `V3-B.wav`). Only 2 clips this pass (V1/V2 absent for the
  honest reasons in §3).
- A NEW blind seed (`AUTOMIX_R3_REAL_MUSIC_BLIND_SEED`) maps blind letters
  to internal candidates; the seed and full mapping are LOCAL ONLY and
  gitignored, never in the owner ZIP, never printed in the final handoff.
  Unrelated to both the synthetic pack's seed AND the previously-generated
  (now-invalid) real-music seed.
- The invalidated owner ZIP hash (`84ad398e...`) is asserted absent from
  the current build by the verifier (Check 12) and remains invalid
  forever regardless of future rebuilds.

## Result

`PARTIAL` (`PARTIAL_NO_VALID_V1` + `PARTIAL_NO_VALID_V2`, `V3` selected and
rendered). No quality PASS is claimed. P1 has not started.
