# P0-M3-R3 bounded analyzer-evidence recovery

Date: 2026-08-13

Issue: [PNHD/AutoMix #7](https://github.com/PNHD/AutoMix/issues/7)

Binding PM comment: [5270363930](https://github.com/PNHD/AutoMix/issues/7#issuecomment-5270363930)
Accepted starting HEAD: `7ccb5c72461e4237d85b621946be7cc4443f0350`

## Result

`ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY`

No V1/V2 near miss became FULL_DJ-eligible under the existing R2 evaluator.
No render was started. This is not a quality PASS and does not prove that the
private 100-track corpus lacks musically compatible pairs.

## Bounded work set

The worker independently derived the exact union of tracks appearing in the
cached top-10 V1 and top-10 V2 near misses:

- V1 pairs: 10
- V2 pairs: 10
- unique opaque tracks: 19
- analyzed tracks outside this union: 0

The exact opaque IDs and pair membership are in
`results/analyzer_evidence_recovery_subset.json`. Private source paths existed
only in a gitignored local job file. No source basename, path, audio hash, raw
tag, or audible derivative is in committed evidence.

## A1 — confidence ownership

Canonical R2 behavior is unchanged. `analysis_confidence` remains the existing
minimum of structure, genre and harmonic strength solely so the accepted
baseline can be compared byte-for-behavior.

The research path now emits an explicit ledger for:

- `beat_confidence_source`
- `downbeat_confidence_source`
- `structure_confidence_source`
- `genre_style_confidence_source`
- `harmonic_confidence_source`
- `vocal_proxy_confidence_source`
- `texture_measurement_confidence_source`
- `bass_measurement_confidence_source`

The diagnostic gate order requires every underlying R2 lane but does not count
the aggregate `analysis_confidence` as a second independent measurement. This
diagnostic produced 0/20 eligible pairs and cannot create an honest render
candidate. A future R2 contract change remains PM-owned.

## A2 — downbeat/bar evidence

All-In-One remained blocked after the required bounded environment probe:

- canonical source stayed at `18e78903c0365147a2c5d4e5e57ebf88cb7d800e`;
- the installed isolated WSL environment had PyTorch `2.13.0+cu126` and NATTEN
  `0.21.7+torch2130cu126` with CUDA available;
- canonical import failed because legacy `natten1dav`/`natten1dqkrpb` symbols
  are absent;
- public PR #37 at `5c2b2ce571c04054a0b54ceba365c0b8c1188099`
  was inspected in full and tested from a gitignored detached checkout;
- that patch also failed against NATTEN 0.21.7 because `na1d_qk`/`na1d_av`
  symbols are absent from the observed official 0.21 API.

No unreviewed attention rewrite, admin install, or system-wide dependency
change was used to force execution.

The fallback was the already-isolated madmom RNN downbeat model plus DBN,
tagged `BENCHMARK_ONLY`. It ran on exactly 19 tracks. Against the cached
homegrown bar-phase grid:

- `RESOLVED_HIGH`: 0 tracks
- `RESOLVED_CONFLICT`: 9 tracks
- `STILL_UNKNOWN`: 10 tracks

The `PROJECT_DIAGNOSTIC` resolution rule required at least 8 decoded
downbeats, median raw downbeat activation >=0.20, interval CV <=0.12 and
median agreement error <=100 ms for `RESOLVED_HIGH`; error >250 ms with at
least 8 events produced `RESOLVED_CONFLICT`. These thresholds are not
calibrated product confidence and did not alter R2.

Conflicts were downgraded to insufficient evidence during replay; the cached
heuristic was not cherry-picked. Beat ownership remains unchanged: the madmom
run is not promoted to product beat truth.

## A3 — section evidence

Because All-In-One did not run, no functional `intro/outro/bridge/verse/chorus`
labels were available. The bounded fallback measured independent audio change
points from beat-synchronous CQT, MFCC and spectral-contrast features using
librosa `0.11.0`.

All 19 tracks produced boundary candidates, but they remain
`STILL_UNKNOWN_BOUNDARY_ONLY_NO_FUNCTIONAL_LABELS`. The evidence reports the
section interval containing each exit/entry, the nearest boundary and distance
in ms/beats/bars. It never calls a boundary a phrase or outro without a real
functional label.

Boundary candidates used adjacent beat-synchronous feature novelty >=1.5
robust-z with at least 8 beats of spacing. This is a project diagnostic, not a
functional-section confidence calibration.

## A4 — harmonic evidence

The independent oracle used librosa CQT chroma and Krumhansl-Schmuckler key
profiles on the actual cached exit/entry windows.

Independent key confidence was `HIGH` at a top-two profile-score margin >=0.08,
`MEDIUM` at >=0.04, otherwise `LOW`; this is a project diagnostic and not a
calibrated product confidence.

Track-window comparison against the cached STFT-chroma estimator:

- exit: 2 agreements, 7 conflicts, 10 still unknown;
- entry: 3 agreements, 6 conflicts, 10 still unknown.

Across the 20 near-miss pairs:

- `RESOLVED_COMPATIBLE`: 0
- `RESOLVED_INCOMPATIBLE`: 2
- `RESOLVED_CONFLICT`: 4
- `STILL_UNKNOWN`: 14

Only one formerly UNKNOWN harmonic gate became PASS through exact
cross-estimator agreement (`RM042 -> RM015`). The pair still failed texture and
canonical aggregate confidence, so it is not a render candidate.

## A5 — genre/style evidence

Essentia Discogs-EffNet was probed but not run. No Essentia/TensorFlow runtime
was installed in the isolated WSL environment, and `pip index versions
essentia` returned no matching distribution for Python 3.12. No broad install,
Docker bring-up, web search of track identities, or improvised filename-based
classification was attempted.

Result: `GENRE_STYLE_ORACLE_UNAVAILABLE`. Existing generic owner-local tag
evidence existed for 8/19 tracks; all other style evidence stayed UNKNOWN.

## A6 — targeted replay

| Category | Pair | Original failed gates | Recovered strict-R2 failed gates | Newly resolved |
|---|---|---|---|---|
| V1 | RM092 -> RM070 | structure, texture, aggregate | downbeat, structure, texture, aggregate | none |
| V1 | RM075 -> RM043 | downbeat, texture, aggregate | downbeat, texture, aggregate | none |
| V1 | RM075 -> RM003 | downbeat, texture, aggregate | downbeat, texture, aggregate | none |
| V1 | RM042 -> RM083 | genre, harmonic, texture, aggregate | genre, harmonic, texture, aggregate | none |
| V1 | RM042 -> RM051 | genre, downbeat, texture, aggregate | genre, downbeat, texture, aggregate | none |
| V1 | RM042 -> RM002 | genre, downbeat, texture, aggregate | genre, downbeat, texture, aggregate | none |
| V1 | RM042 -> RM015 | genre, harmonic, texture, aggregate | genre, texture, aggregate | harmonic |
| V1 | RM082 -> RM092 | genre, harmonic, texture, aggregate | genre, downbeat, harmonic, texture, aggregate | none |
| V1 | RM082 -> RM070 | genre, harmonic, texture, aggregate | genre, downbeat, harmonic, texture, aggregate | none |
| V1 | RM014 -> RM010 | genre, downbeat, harmonic, aggregate | genre, downbeat, harmonic, aggregate | none |
| V2 | RM014 -> RM041 | harmonic, texture, aggregate | downbeat, harmonic, texture, aggregate | none |
| V2 | RM014 -> RM081 | genre, harmonic, aggregate | genre, downbeat, harmonic, aggregate | none |
| V2 | RM014 -> RM070 | harmonic, texture, aggregate | downbeat, harmonic, texture, aggregate | none |
| V2 | RM014 -> RM071 | genre, texture, aggregate | genre, downbeat, texture, aggregate | none |
| V2 | RM014 -> RM092 | harmonic, texture, aggregate | downbeat, harmonic, texture, aggregate | none |
| V2 | RM041 -> RM014 | harmonic, structure, aggregate | downbeat, harmonic, structure, aggregate | none |
| V2 | RM075 -> RM092 | downbeat, harmonic, texture | downbeat, harmonic, texture, aggregate | none |
| V2 | RM042 -> RM026 | genre, harmonic, texture, aggregate | genre, harmonic, texture, aggregate | none |
| V2 | RM042 -> RM001 | genre, downbeat, texture, aggregate | genre, downbeat, texture, aggregate | none |
| V2 | RM042 -> RM017 | genre, harmonic, texture, aggregate | genre, harmonic, texture, aggregate | none |

`aggregate` in this table means the unchanged canonical
`analysis_confidence`; the machine artifact uses the exact field name.

Aggregate replay result:

- strict existing-R2 eligible: 0/20
- confidence-ledger diagnostic eligible: 0/20
- pairs with remaining UNKNOWN evidence: 20/20
- pairs with measured incompatibility: 17/20
- measured texture incompatibility: 17/20

## Validation and non-actions

- bounded-recovery self-test: 11/11 assertions PASS;
- bounded artifact/privacy verifier: 19/19 assertions PASS before commit;
- exact prior Stage-B mutation and verifier suites are rerun during closeout;
- owner/private audio analyzed: only the 19-track deduplicated subset;
- whole-corpus rerun: no;
- owner audio render: no;
- Signalsmith/Rubber Band: no;
- owner listening ZIP: not created or rebuilt;
- P1: not started.

Full per-track downbeats, inferred meter, confidence/stability evidence,
section-boundary distances, independent keys, pair-ledger verdicts and strict
reason codes are in
`tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json`.
