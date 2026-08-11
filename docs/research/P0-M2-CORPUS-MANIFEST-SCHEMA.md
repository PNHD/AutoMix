# P0-M2-R1 — Corpus Manifest Schema

Status date: 2026-08-11 (PM REVIEW #3 — R13/R14 classification-evidence fields, R15 `human_confirmations`/`rejected_conditional`, R16 Lane-E holdout field)

Companion to `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`. Defines the machine-readable fixture/pair manifest that every benchmark run is scored against.

## 1. Format decision

**JSON Lines (`.jsonl`), one fixture or pair object per line**, plus a single top-level `manifest.json` index file. (Rationale unchanged from prior revisions: line-addressable diffs, streamability, no schema-migration lock-in versus a relational store, YAML rejected for whitespace-sensitivity risk in hand-edited corpora.)

```text
docs/research/corpus/manifest.json          # top-level index: schema version, tier definitions, split assignment, corpus minimums
docs/research/corpus/tier1_fixtures.jsonl   # one JSON object per Tier-1 audio fixture (track-level)
docs/research/corpus/tier1_pairs.jsonl      # one JSON object per Tier-1 transition pair
docs/research/corpus/tier2_pairs.jsonl      # one JSON object per Tier-2 pair (metadata/provider-ID references only, no audio)
```

A fifth, **result-record** stream (§10) — one JSON object per rendered transition actually produced by a benchmark run — is defined by shape here but its storage location is left to the future benchmark-execution task that produces it (a disposable P0-M3 prototype); it is not corpus ground truth and is never committed as corpus data.

## 2. Top-level `manifest.json`

```json
{
  "schema_version": "3.0.0",
  "generated_by": "P0-M2-R1 (PM REVIEW #3 repair pass)",
  "tiers": {
    "tier1": { "fixtures_file": "tier1_fixtures.jsonl", "pairs_file": "tier1_pairs.jsonl", "splits": ["dev", "holdout"] },
    "tier2": { "pairs_file": "tier2_pairs.jsonl", "splits": ["private_listening"] }
  },
  "split_assignment_policy": {
    "method": "fixed_at_creation",
    "rule": "A pair's split is assigned once, at manifest-entry creation time, before any benchmark run against it, and is never reassigned based on how a system performs on it.",
    "holdout_fraction_target": 0.3
  },
  "corpus_minimums": {
    "tier1_total_pairs_min": 74,
    "tier1_dev_pairs_min": 52,
    "tier1_holdout_pairs_min": 22,
    "tier1_holdout_tie_rate_ceiling": 0.20,
    "tier1_holdout_decisive_min": 18,
    "tier1_holdout_decisive_min_derivation": "22 - floor(0.20*22) = 22-4 = 18: 22 is the smallest holdout pool for which the maximum tie count still compliant with the 20% inconclusive ceiling (4 ties, 18.2%) still leaves 18 decisive G1 trials.",
    "per_lane_min": {
      "A_TIMING_STRUCTURE": 23,
      "B_CONTENT_COLLISION": 8,
      "C_ENERGY_LOUDNESS": 8,
      "D_HARMONIC_TEMPO": 12,
      "E_CONFIDENCE_FALLBACK": 23
    },
    "lane_a_clean_structure_subset_min": 10,
    "lane_a_clean_structure_subset_holdout_min": 3,
    "lane_e_holdout_min": 7,
    "lane_e_should_not_full_blend_subset_min": 8,
    "lane_e_should_not_full_blend_subset_holdout_min": 3,
    "g2_simpmusic_comparison_subset_min": 30,
    "g2_simpmusic_comparison_subset_holdout_min": 9,
    "note": "R16 fix: lane_e_holdout_min (7) is NEW and is the machine-readable minimum for G4's Lane-E OVERALL transition-class match-rate holdout check (contract G4), distinct from lane_e_should_not_full_blend_subset_holdout_min (3), which is G4's separate C11 zero-tolerance holdout check on the adversarial subset specifically. lane_e_should_not_full_blend_subset_holdout_min's 3 pairs are a SUBSET of lane_e_holdout_min's 7 pairs (at least 3 of Lane E's 7 required holdout pairs must be drawn from the adversarial subset), not additive. Cross-check: proportional ~30% holdout allocation across per_lane_min (A:23*0.3=6.9->7, B:8*0.3=2.4->2, C:8*0.3=2.4->2, D:12*0.3=3.6->4, E:23*0.3=6.9->7) sums to 7+2+2+4+7=22, exactly matching tier1_holdout_pairs_min -- the named per-lane/per-subset minimums are achievable simultaneously via a single natural proportional split, not competing allocations. A benchmark runner MUST reject (refuse to score) any corpus that does not meet every minimum in this block."
  }
}
```

## 3. Fixture object (`tier1_fixtures.jsonl`)

Unchanged from the PM REVIEW #2 revision except where noted. Key fields relevant to this revision:

| Field | Type | Description |
|---|---|---|
| `fixture_id` | string | Stable unique ID |
| `local_path`, `checksum`, `provenance`, `license`, `license_source_url` | — | Provenance/integrity (unchanged) |
| `duration_ms` | integer | Full track duration |
| `authored_exit_boundary_ms` | integer, nullable | The track's own authored/natural end (defaults to `duration_ms`) |
| `authored_entry_boundary_ms` | integer, nullable | The track's own authored/natural start (defaults to `0`) |
| `beat_timestamps_ms`, `downbeat_indices`, `meter`, `bpm`/`tempo_curve`, `key` | — | Structural/harmonic ground truth (unchanged); **also the input to the R13 `sustained_beat_lock_ratio` measurement (§10)** |
| `acceptable_entry_regions_ms`, `acceptable_exit_regions_ms` | array, may be empty | An empty array is a meaningful, authored "no region exists" statement (unchanged) |
| `vocal_intervals_ms`, `bass_intervals_ms`, `percussion_intervals_ms`, `loudness`, `energy_curve` | — | Content/loudness ground truth (unchanged; vocal/bass metrics are computed on rendered output per contract §8, not naively on these source intervals) |
| `annotation_sources` | object | One entry per annotated field, per the source enum (§6) |

## 4. Pair object (`tier1_pairs.jsonl` / `tier2_pairs.jsonl`)

| Field | Type | Required | Description |
|---|---|---|---|
| `pair_id` | string | yes | |
| `outgoing_fixture_id` / `outgoing_ref`, `incoming_fixture_id` / `incoming_ref` | — | yes | |
| `benchmark_lane`, `secondary_lanes`, `case_tags` | — | yes/no | |
| `transition_class_policy` | object | yes | See §5 — **revised this pass** (R15): `human_confirmation` → `human_confirmations` (array) + `human_all_required`; new `rejected_conditional` list; `requires_modifier` **removed** (§5's "What was removed" note explains why) |
| `is_continuous_work` | boolean, default `false` | no | Authored fact: the pair's two fixtures are one continuous work split at an edit point. Drives `GAPLESS` eligibility (§10) |
| `sequencing_suppression_intended` | boolean, default `false` | no | Authored fact: no AutoMix processing should occur, without claiming the fixtures are one continuous work |
| `manipulation_constraints` | object, nullable | no | `tempo_ratio_max_deviation` (default 0.12), `max_pitch_shift_semitones` (default 3), `low_band_coactivity_threshold_db` (default −12), `low_band_coactivity_min_duration_ms` (default 500), `low_band_coactivity_ratio_ceiling` (default 0.5) |
| `known_trap_purpose` | string | yes | |
| `annotation_sources`, `evaluation_exclusions`, `split`, `created_at`, `notes` | — | — | Unchanged |

## 5. `transition_class_policy` object (revised — R15)

```json
{
  "accepted_unconditional": ["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"],
  "accepted_conditional": [
    {
      "class": "FULL_DJ_BLEND",
      "conditions": ["COND_BEAT_OK", "COND_DOWNBEAT_OK"],
      "all_required": true,
      "human_confirmations": [],
      "human_all_required": true
    }
  ],
  "rejected_conditional": [],
  "rejected": [
    { "class": "GAPLESS", "reason": "..." }
  ]
}
```

| Field | Meaning |
|---|---|
| `accepted_unconditional` | Classes always a correct *choice*, execution quality scored separately. |
| `accepted_conditional[].class` / `.conditions` / `.all_required` | Unchanged: named Condition-Registry IDs (contract §7), AND (`all_required:true`, default) or OR (`false`). |
| `accepted_conditional[].human_confirmations` | **Changed (R15) from a single nullable `human_confirmation` object to an array** of `{"dimension": "...", "min_score": N}`, each referencing a human-rubric dimension (contract §9.2). Empty array (`[]`) or omitted = no human confirmation required. |
| `accepted_conditional[].human_all_required` | Boolean, default `true`. `true` = every entry in `human_confirmations` must independently meet its `min_score` (AND). `false` = at least one must (OR). Together with the array, this makes a multi-dimension requirement like `PAIR-SYN-A-010`'s `downbeat_bar_coherence >= 3 AND beat_coherence >= 3` fully machine-readable — see `docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md`'s "Serialization examples" section for the literal serialized JSON. |
| `rejected_conditional[].class` / `.unless_conditions` / `.all_required` / `.reason` | **New (R15).** The class is rejected **unless** the listed Condition-Registry IDs are measured-satisfied (per `all_required`'s AND/OR semantics, same convention as `accepted_conditional`). `reason` is **mandatory** and is strong, annotation-grounded evidence for a `C11` finding when the unless-condition(s) are not met — unlike the weak, generic closed-world default reason (§ below). This is the fix for the logical contradiction the PM identified in `PAIR-SYN-E-007`'s prior encoding (a class cannot simultaneously be an unconditional `rejected` entry and a `requires_modifier`-gated `accepted_conditional` entry) and, critically, is defined purely in terms of **outcome conditions** (e.g. `COND_VOCAL_OK`, which is measured on the rendered/post-mix audio regardless of which technique produced it), never a named implementation technology. |
| `rejected` | Classes **never** correct regardless of any condition. Reason must cite a fixture-authored, corpus-design-time-known fact (unchanged from the R12 repair pass). |

**New structural constraint (R15):** a class must appear in **at most one** of `accepted_unconditional` / `accepted_conditional` / `rejected_conditional` / `rejected` for a given pair — never two, which would be an ambiguous or contradictory representation. A benchmark runner (and a manifest linter) MUST reject a pair whose `transition_class_policy` violates this.

**Closed-world default (unchanged):** a class not listed anywhere in the four lists defaults to rejected with the generic "not enumerated as acceptable for this pair" reason, which remains deliberately too weak to ground a `C11` finding by itself — only an explicit `rejected` or `rejected_conditional` entry (each carrying a specific, mandatory, fixture/outcome-grounded `reason`) can ground `C11`.

**Scoring rule** (also stated in the benchmark contract §8): given a rendered transition's `observed_class` (§10, §ClassificationTaxonomy in the contract),
1. `observed_class ∈ accepted_unconditional` → correct.
2. `observed_class` has an `accepted_conditional` entry → correct iff its `conditions`/`human_confirmations` are satisfied; else mismatch (not automatically `C11`-eligible).
3. `observed_class` has a `rejected_conditional` entry → correct iff its `unless_conditions` **are** satisfied; if not satisfied → mismatch **and** `C11`-eligible, grounded by that entry's `reason`.
4. `observed_class` has a `rejected` entry → always mismatch and `C11`-eligible.
5. Otherwise (not enumerated anywhere) → mismatch, weak reason, **not** `C11`-eligible.

**What was removed (R15):** the PM REVIEW #2 revision's `accepted_conditional[].requires_modifier` field (gating acceptance on a single named technology flag such as `stem_separation_applied`) is **removed**. It encoded exactly the anti-pattern the PM's R15 review flagged: correctness tied to *which technique* was used rather than the *rendered outcome*. `stem_separation_applied` (and any future technique-identifying flag) remains available on the transition render record (§10) purely as **diagnostic metadata** — it is never referenced by any `transition_class_policy` entry after this revision.

## 6. Annotation source enum

Unchanged: `SYNTHETIC_EXACT`, `MANUAL`, `DATASET`, `MODEL_ESTIMATE`, `PROVIDER_METADATA`, `UNKNOWN`. No `MODEL_ESTIMATE`/`PROVIDER_METADATA`/`UNKNOWN`-sourced annotation may be presented as ground truth; catastrophic codes require `SYNTHETIC_EXACT`/`MANUAL` sourcing except `C9`'s human-corroboration path.

## 7. Tier-2 privacy and non-redistribution

Unchanged. `listening_scores.preference_outcome` remains `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE`. No audio, `local_path`, or `checksum` fields on Tier-2 pairs.

## 8. Fixture/pair ID convention

Unchanged: `{PREFIX}-{LANE}-{SEQ}`.

## 9. Versioning and change discipline

**This revision bumps `2.1.0` → `3.0.0` (breaking):**
- `accepted_conditional[].human_confirmation` (singular nullable object) is renamed/restructured to `.human_confirmations` (array) + `.human_all_required` — a v2.1.0 consumer reading the old field name would silently miss data.
- `accepted_conditional[].requires_modifier` is removed outright — a v2.1.0 consumer relying on it would break.
- `rejected_conditional` is a new list with scoring-rule implications for any consumer implementing the transition-class-correctness metric.
- Two new transition-render-record fields (`inter_track_gap_ms`, `sustained_beat_lock_ratio`/`has_sustained_beat_lock`) are required inputs to the revised `GAPLESS`/`FULL_DJ_BLEND` classification rules (§10, contract §5) — a runner built against the prior classification procedure would misclassify.

Every corpus-affecting Git commit must remain reviewable as a normal diff and must not silently move a pair between `dev`/`holdout` after results exist for it.

## 10. Transition render record (revised — R13/R14)

**Not corpus ground truth** — the shape of a per-rendered-transition measurement record a benchmark runner produces (storage location left to the future benchmark-execution task).

| Field | Type | Description |
|---|---|---|
| `pair_id` | string | |
| `system_under_test` | string | |
| `run_timestamp` | ISO-8601 | |
| `overlap_ms` | integer | Measured duration where both tracks' audio is simultaneously present above a noise floor |
| `inter_track_gap_ms` | integer, nullable | **New (R14).** Only meaningful when `overlap_ms` ≤ the measurement epsilon (default 20 ms, treated as zero overlap). Measured silence duration between the end of the outgoing track's rendered audio and the start of the incoming track's rendered audio. `0` (or ≤ epsilon) means a sample-contiguous join; a value above epsilon means a real, measurable, audible gap exists. **`overlap_ms ≤ epsilon` alone never implies zero gap** — this field is mandatory whenever `overlap_ms` is at or below the epsilon, and the classification procedure (contract §5) treats a missing value in that situation as `UNCLASSIFIED_ANOMALY`, never defaults it to zero. |
| `has_volume_automation` | boolean | Volume/gain curve during the overlap deviating from static/native gain beyond a measurement-noise epsilon |
| `has_eq_automation` | boolean | Detectable spectral/band-gain change over time during the overlap beyond native equalization |
| `has_tempo_pitch_automation` | boolean | Playback rate or pitch deviates from native by more than a measurement epsilon at any point in the overlap |
| `sustained_beat_lock_ratio` | float [0,1], nullable | **New (R13).** Fraction of beat-grid instants within the overlap window where, using each track's own beat timestamps mapped through its actually-applied playback-rate curve (native if `has_tempo_pitch_automation=false`), instantaneous beat-alignment error ≤ 1/16 beat **and** downbeat-phase error = 0, simultaneously, relative to a shared beat/bar grid. `null` when reliable beat ground truth (`SYNTHETIC_EXACT`/`MANUAL`) is unavailable for either track — never imputed as 0 or 1. |
| `has_sustained_beat_lock` | boolean, nullable | **New (R13).** `true` iff `sustained_beat_lock_ratio ≥ 0.8` **and** `overlap_ms ≥ 4 × local_bar_period_ms` (the duration floor excludes a single lucky beat-aligned instant from counting as "sustained" — see contract §5.4 for the full derivation). `null` when `sustained_beat_lock_ratio` is `null`. |
| `outgoing_used_natural_full_duration` | boolean | Outgoing track played to its own `authored_exit_boundary_ms` (or `duration_ms` if null), not truncated |
| `incoming_used_natural_start` | boolean | Incoming track began at its own `authored_entry_boundary_ms` (or `0` if null) |
| `stem_separation_applied` | boolean | **Diagnostic metadata only (R15) — never referenced by any `transition_class_policy` entry or classification rule.** Whether the system under test applied stem/source-separation or targeted vocal/instrument attenuation during the overlap. |
| `engine_reported_class` | enum or `null` | Diagnostic only, never authoritative |
| `observed_class` | enum: `FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, `SIMPLE_CROSSFADE`, `GAPLESS`, `CUT`, `NO_SPECIAL_TRANSITION`, `UNCLASSIFIED_ANOMALY` | Computed via the contract §5 deterministic decision procedure from the fields above plus `is_continuous_work`/`sequencing_suppression_intended`. The sole scoring input for `transition_class_policy` matching, `C11`, and `G4`. |
| `class_label_mismatch` | boolean | `engine_reported_class != observed_class`, diagnostic only |

This table is the concrete field list the R13 (`FULL_DJ_BLEND` evidence) and R14 (`GAPLESS` gap-awareness) fixes are computed against.
