# P0-M3-R3 STAGE B — Owner Real-Music Validation (REAL-EVIDENCE REPAIR + EVIDENCE AUDIT)

**This is the SECOND repair pass.** The first real-evidence repair (§0-§2
below) fixed fabricated genre/structure/bass/texture evidence. A
follow-up PM audit ("PM STAGE-B REAL-EVIDENCE REPAIR REVIEW — NARROW
REPAIR REQUIRED") then found the V3 selector still bypassed the stated
ranking contract (sorted by beat-confidence + opaque ID only, ignoring
preservation/structure/texture/vocal/bass/energy/harmonic), and that the
handoff's ~95%/~93% bottleneck claims were unsupported prose rather than
machine-verified counts. §3 below (rewritten) documents that second
repair's exact machine evidence. This pass is a NARROW selector/evidence/
audit repair only — it reuses the existing cached 100-track analysis,
never re-decodes audio, never renders, and never rebuilds the owner pack.

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

## 3. Pair selection outcome (honest, post-repair, PM STAGE-B EVIDENCE AUDIT)

Exhaustive search over ~9,900 ordered pairs using the SAME
`evaluate_pair_compatibility` the accepted R2 planner uses, with the
additional constraint that a candidate's outgoing exit must itself be
RENDERABLE (structure confidence ≥ MEDIUM — otherwise the real planner's
own `policy/eligibility.py` Guard 2 rejects it as `NO_SAFE_OUTGOING_EXIT`,
independent of transition class).

**B1 repair**: V3 selection previously bypassed the ranking contract
entirely (sorted only by `beat_confidence==HIGH` on both sides, then
opaque ID) -- it now uses the EXACT SAME `rank_key()` as V1/V2 (pool
membership alone guarantees the negative-control property; ranking WITHIN
the pool now follows preservation → entry → structure → texture → vocal →
bass → energy continuity → harmonic → smallest-excess-tempo-burden →
opaque ID last). This changed the selected V3 pair.

### Exact gate decomposition (`real_music/work_local/pair_gate_calibration_sanitized.json`, machine-computed from the cached 100-track analysis, no re-decode)

| Gate | V1 PASS | V1 INCOMPATIBLE | V1 UNKNOWN | V1 fail% | V2 PASS | V2 INCOMPATIBLE | V2 UNKNOWN | V2 fail% |
|---|---|---|---|---|---|---|---|---|
| genre | 32 | 34 | 554 | 94.8% | 54 | 61 | 910 | 94.7% |
| tempo | 620 | 0 | 0 | 0.0% | 1025 | 0 | 0 | 0.0% |
| beat | 472 | 0 | 148 | 23.9% | 819 | 0 | 206 | 20.1% |
| downbeat | 44 | 0 | 576 | 92.9% | 72 | 0 | 953 | 93.0% |
| harmonic | 151 | 205 | 264 | 75.6% | 227 | 384 | 414 | 77.9% |
| structure | 90 | 0 | 530 | 85.5% | 133 | 0 | 892 | 87.0% |
| texture | 31 | 589 | 0 | 95.0% | 51 | 974 | 0 | 95.0% |
| vocal | 304 | 316 | 0 | 51.0% | 481 | 544 | 0 | 53.1% |
| bass | 620 | 0 | 0 | 0.0% | 1023 | 2 | 0 | 0.2% |
| analysis_confidence | 0 | — | 620 | 100.0% | 1 | — | 1024 | 99.9% |
| **intersection (FULL_DJ-eligible)** | **0 / 620** | | | | **0 / 1025** | | | |

`INCOMPATIBLE` = a real measurement was taken and genuinely failed.
`UNKNOWN` = the gate failed for lack of trustworthy evidence, NOT proven
incompatibility (see §3.2). Structure/downbeat/analysis_confidence are
**100% UNKNOWN when they fail** (these gates have no "measured
incompatible" state in this design at all); genre is **94% UNKNOWN** vs
6% measured-incompatible; texture and vocal, by contrast, are dominated by
genuine measurement (95% / 51-53% MEASURED_INCOMPATIBLE respectively).

### 3.1 Threshold sensitivity (B3, diagnostic only — production thresholds unchanged)

Texture thresholds evaluated at 0.75×/1×/1.25×/1.5× current, energy at
comparable variants (see the calibration JSON's `sensitivity_matrix` per
universe). **Result: 0 surviving candidates at every multiplier tested,
for both V1 and V2.** The zero-result is **stable, not threshold-sensitive**
— the dominant failing gate at every variant is `analysis_confidence`
(itself an aggregate of structure/genre/harmonic evidence strength, never
texture/energy), meaning loosening the texture/energy calibration alone
would not unlock V1 or V2 in this corpus.

### 3.2 Threshold calibration provenance (B2)

`THRESHOLD_CALIBRATION_NOT_PREVIOUSLY_PROVEN.` The 5 hardcoded texture/
energy thresholds were originally set from ad-hoc interactive percentile
calculations against a small 20-track sample during the prior session --
never saved as a runnable script, not reproducible from any committed
artifact, and not computed against the full 100-track corpus or the real
V1/V2 tempo-eligible universes. They are honestly labeled PROJECT
HEURISTIC values pending real validation. This pass's calibration JSON
provides reproducible full-corpus percentile distributions
(min/p05/p10/p20/p25/p50/p75/p80/p90/p95/max for
centroid/flatness/onset-density/loudness-gap/bass-gap/combined-energy-gap)
as a basis for a FUTURE, properly-documented calibration -- the existing
thresholds were NOT changed by this audit.

### 3.3 Near-miss forensics (B4)

Top-10 nearest-miss pairs per universe (ranked by fewest independently
failed gates, then preservation/energy quality) are in
`real_music/work_local/selection_trace.local.json`. The closest V1/V2
near-misses fail on **3 gates simultaneously** (never fewer) -- e.g.
`{structure, texture, analysis_confidence}` or
`{harmonic, texture, analysis_confidence}` -- confirming this is a
genuine multi-dimensional evidence gap, not a single narrowly-missed
threshold.

- **V1 (close_tempo_minimal_stretch): `PARTIAL_EVIDENCE_INSUFFICIENT_V1`.**
  Pool size after the honest hard-gate filter: **0 / 620**.
- **V2 (conditional_tempo_correction): `PARTIAL_EVIDENCE_INSUFFICIENT_V2`.**
  Pool size: **0 / 1025**.
- **V3 (incompatible_downgrade): SELECTED (repaired ranking).** Pool size
  1,057. Newly-selected pair (opaque IDs) has `structure_compatibility=
  COMPATIBLE` (genuine bar-synchronous novelty-peak evidence),
  `intro_outro_texture_compatible=true`, `bass_percussion_collision_risk=
  LOW`, 16.67% required tempo deviation (smaller excess beyond the 12%
  ceiling than the pre-repair selection's 20.83%), harmonic `UNKNOWN`
  (insufficient key confidence, not measured-incompatible this time) --
  `FULL_DJ_BLEND` is still correctly withheld
  (`TEMPO_EXCESSIVE_STRETCH_REQUIRED` + `DOWNBEAT_CONFIDENCE_INSUFFICIENT`
  + `HARMONIC_UNKNOWN_DOWNGRADED` + `ANALYSIS_CONFIDENCE_LOW_PAIR`).
  Pre-render projected combined energy gap ≈34dB (`WEAK` — down from the
  pre-repair selection's ≈40dB, reflecting the now-active
  energy-continuity ranking dimension).

**No gate was weakened to produce a V1 or V2 pair.** See §3.2/§3.3: the
zero-result is real, but a meaningful share of it (genre, downbeat,
structure, analysis_confidence) reflects UNKNOWN evidence, not proven
incompatibility -- this corpus cannot be honestly described as "proven
incompatible for V1/V2," only as "insufficiently evidenced," alongside
some genuinely measured blockers (texture, vocal).

## 4. Planner + render outcome

**The newly re-ranked V3 pair (§3.3) has NOT been re-rendered this pass**
(explicitly out of scope for this narrow selector/evidence audit -- no
audio decode, no Signalsmith, no rendering). The render/loudness figures
below are from the PRIOR pass's now-superseded V3 selection and are kept
here only as historical record of that earlier run; they do not describe
the pair currently in `real_music/manifest.local.json`.

- **Prior selection's V3** (pre-B1-repair): `decision_type=TRANSITION`,
  `allowed_transition_class_set=[SIMPLE_CROSSFADE]`, `tempo_mode=
  NATIVE_TEMPO`. Rendered A (equal-power) / B (late-outgoing-hold).
  Post-render `loudness_max_dip_db` ≈16.0dB for both.

A future pass should render the §3.3 pair once PM accepts this audit, and
report its own (not the superseded pair's) post-render diagnostics.

## 5. Verifier + mutation-test evidence

`scripts/verify_real_music_stage_b.py` (post-commit, run against the
pushed HEAD with a locally-supplied `--private-sentinel`) -- see
`HANDOFF_TO_PM.md` for the exact command and pass/fail result.

`scripts/mutation_test_real_music_stage_b.py` -- **ALL REQUIRED MUTATIONS
PASS** (11 from the prior repair pass + 12 new from this evidence audit --
see `HANDOFF_TO_PM.md`'s VALIDATION section for the full list), each
proving a specific guarantee against a crafted adversarial input (never
real owner data): genre never fabricated; structure/`musical_unit_complete`
never derived from beat/downbeat alone; bass/percussion collision is
measured; texture requires real timbral/rhythmic evidence; incoming entry
is never forced to 0ms; FULL_DJ withheld on any single independent gate
failure; V3 now uses the real compatibility/energy ranking (not
beat+ID); V3 remains FULL_DJ-ineligible; V3 ID order cannot beat
materially safer energy continuity; the calibration artifact is
deterministic from the cached analysis; gate counts sum correctly;
UNKNOWN and INCOMPATIBLE are kept distinct; cumulative intersections
reproduce; sensitivity testing never mutates production thresholds;
near-miss ranking runs before final hard-gate filtering; no privacy leak;
and all prior regressions stay green.

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

`PARTIAL` (`PARTIAL_EVIDENCE_INSUFFICIENT_V1` + `PARTIAL_EVIDENCE_INSUFFICIENT_V2`,
`V3` re-selected under the repaired ranking but NOT re-rendered this pass).
No quality PASS is claimed. No owner pack was rebuilt this pass. P1 has
not started.
