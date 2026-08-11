# P0-M2-R1 — Corpus Manifest Schema

Status date: 2026-08-11

Companion to `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`. Defines the machine-readable fixture/pair manifest that every benchmark run is scored against.

**This document is normatively self-contained.** Every field below is defined completely at this revision — exact type, required/optional, nullable behavior, default, semantics, and annotation-source requirement — with no dependency on any earlier commit, PM review, or prior document revision to be implementable. A non-normative changelog appears at the very end (§13) for audit-trail purposes only; nothing in §1–§12 depends on reading it.

## 1. Format

**JSON Lines (`.jsonl`), one fixture or pair object per line**, plus a single top-level `manifest.json` index file, plus a separately-stored (not corpus-committed) transition render record stream.

```text
docs/research/corpus/manifest.json          # top-level index: schema version, tier definitions, split assignment, corpus minimums
docs/research/corpus/tier1_fixtures.jsonl   # one JSON object per Tier-1 audio fixture (track-level), shape in §3
docs/research/corpus/tier1_pairs.jsonl      # one JSON object per Tier-1 transition pair, shape in §4
docs/research/corpus/tier2_pairs.jsonl      # one JSON object per Tier-2 pair, shape in §5
```

A fifth, **transition render record** stream (§9) — one JSON object per rendered transition actually produced by a benchmark run — is defined by shape here but its storage location is left to the benchmark-execution task that produces it (a disposable P0-M3 prototype); it is never corpus ground truth and is never committed as corpus data.

No audio bytes are ever committed to this repository. Tier-1 fixtures reference owner-local audio via `local_path` (§3); Tier-2 pairs reference commercial tracks by metadata/provider ID only (§5).

## 2. Top-level `manifest.json`

```json
{
  "schema_version": "4.0.0",
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
    "note": "lane_e_should_not_full_blend_subset_holdout_min (3) is a subset of lane_e_holdout_min (7), not additive. Proportional ~30% holdout allocation across per_lane_min (A:7, B:2, C:2, D:4, E:7) sums to 22, matching tier1_holdout_pairs_min. A benchmark runner MUST reject (refuse to score) any corpus that does not meet every minimum in this block."
  }
}
```

### 2.1 `manifest.json` field reference

| Field | Type | Required | Default | Semantics |
|---|---|---|---|---|
| `schema_version` | string (semver) | yes | — | This document defines `4.0.0` |
| `tiers.tier1.fixtures_file` / `.pairs_file` | string | yes | — | Relative filenames of the Tier-1 fixture/pair JSONL files |
| `tiers.tier1.splits` | array of string | yes | — | Fixed at `["dev", "holdout"]` |
| `tiers.tier2.pairs_file` | string | yes | — | Relative filename of the Tier-2 pair JSONL file |
| `tiers.tier2.splits` | array of string | yes | — | Fixed at `["private_listening"]` |
| `split_assignment_policy.method` | string | yes | — | Fixed at `"fixed_at_creation"` |
| `split_assignment_policy.holdout_fraction_target` | float [0,1] | yes | — | Target holdout fraction (0.3); actual per-corpus counts are governed by `corpus_minimums`, not derived solely from this fraction |
| `corpus_minimums.*` | integers/floats | yes (every named sub-field) | — | Defined in §2 JSON block above; a benchmark runner MUST validate the actual corpus against every one of these before scoring and refuse to run if any minimum is unmet |

## 3. Fixture object (`tier1_fixtures.jsonl`, one JSON object per line)

Represents a single audio track used as one side of one or more Tier-1 transition pairs.

| Field | Type | Required | Nullable | Default | Semantics |
|---|---|---|---|---|---|
| `fixture_id` | string | yes | no | — | Stable unique ID, e.g. `SYN-A-001` (see §8 ID convention) |
| `local_path` | string | yes | no | — | Path to the audio file on owner-local storage; not resolvable from a public checkout without the owner's local fixture set; never committed audio |
| `checksum` | object `{"algo": string, "value": string}` | yes | no | — | Integrity check against `local_path`, e.g. `{"algo":"sha256","value":"..."}` |
| `provenance` | enum: `SYNTHETIC` \| `OWNER_CREATED` \| `PUBLIC_DOMAIN` \| `CC0` \| `PERMISSIVE_OTHER` | yes | no | — | Source category; commercial/copyrighted audio is never a valid value here |
| `license` | string | yes | no | — | Exact license name/version/URL, e.g. `CC0-1.0`, `Public Domain (pre-1928 US)` |
| `license_source_url` | string | conditional | yes | `null` | Required (non-null) unless `provenance` is `SYNTHETIC` or `OWNER_CREATED` |
| `duration_ms` | integer | yes | no | — | Full track duration |
| `authored_exit_boundary_ms` | integer | no | yes | `duration_ms` | The track's own authored/musically-natural end point, if different from `duration_ms` (e.g. a pre-edited fixture whose musical content stops before the raw file ends) |
| `authored_entry_boundary_ms` | integer | no | yes | `0` | The track's own authored/musically-natural start point, if different from `0` |
| `genre_style_tags` | array of string | yes | no (array itself required; may be empty only if truly untagged, discouraged) | — | e.g. `["pop"]`, `["hip-hop","dynamic-tempo"]`; drives the anti-overfitting coverage audit |
| `meter` | object `{"numerator": integer, "denominator": integer, "confidence": float [0,1]}` | yes | yes (whole object) | `null` | `null` only for intentionally ambiguous-meter fixtures |
| `bpm` | object `{"value": float, "confidence": float [0,1]}` | yes | yes (whole object) | `null` | `null` only when `tempo_curve` is present instead (variable-tempo fixtures) |
| `tempo_curve` | array of `{"t_ms": integer, "bpm": float}` | no | yes | `null` | Present only for variable-tempo fixtures; overrides `bpm` when present |
| `beat_timestamps_ms` | array of integer | conditional | yes | `null` | Required (non-null) whenever `annotation_sources.beat_timestamps` is `SYNTHETIC_EXACT` or `MANUAL` |
| `downbeat_indices` | array of integer | conditional | yes | `null` | Indices into `beat_timestamps_ms` marking bar starts; required whenever `annotation_sources.downbeats` is `SYNTHETIC_EXACT`/`MANUAL` |
| `key` | object `{"root": string, "scale": "major"\|"minor", "camelot": string, "confidence": float [0,1]}` | yes | yes (whole object) | `null` | e.g. `{"root":"A","scale":"minor","camelot":"8A","confidence":1.0}` |
| `phrase_boundaries_ms` | array of integer | no | yes | `null` | |
| `section_boundaries` | array of `{"t_start_ms": integer, "t_end_ms": integer, "label": string}` | no | yes | `null` | `label` should use a controlled vocabulary: `intro`, `verse`, `chorus`, `bridge`, `buildup`, `drop`, `outro`, `instrumental_break`, `other` |
| `acceptable_entry_regions_ms` | array of `{"t_start_ms": integer, "t_end_ms": integer}` | no | no (array itself; use `[]`, not `null`, when no regions exist) | `[]` if annotated as such | An **empty array with a real `annotation_sources` entry** is a meaningful, authored "no acceptable entry region exists anywhere in this fixture" statement, distinct from an *unannotated* field (which has no `annotation_sources` entry at all and must not be treated as "empty on purpose") |
| `acceptable_exit_regions_ms` | array of `{"t_start_ms": integer, "t_end_ms": integer}` | no | no | `[]` if annotated as such | Same empty-array-is-meaningful convention as above |
| `vocal_intervals_ms` | array of `{"t_start_ms": integer, "t_end_ms": integer}` | no | yes | `null` | **Source**-level vocal activity in this fixture's own unmodified audio. Never used directly as the pass/fail ground truth for the vocal-overlap objective metric (contract §8), which is computed on rendered/post-mix output; this field is the input used to construct fixtures and expected renderings, not the runtime scoring signal itself |
| `bass_intervals_ms` | array of `{"t_start_ms": integer, "t_end_ms": integer}` | no | yes | `null` | |
| `percussion_intervals_ms` | array of `{"t_start_ms": integer, "t_end_ms": integer}` | no | yes | `null` | |
| `loudness` | object `{"integrated_lufs": float, "momentary_curve": [{"t_ms": integer, "lufs": float}], "short_term_curve": [{"t_ms": integer, "lufs": float}]}` | no | yes (whole object) | `null` | `integrated_lufs` is a single programme-level value (ITU-R BS.1770-5 gated integrated measurement). `momentary_curve` samples use a 400 ms integration window stepped at a 100 ms hop (EBU Tech 3341 momentary-metering convention layered on BS.1770-5 K-weighting). `short_term_curve` samples use a 3 s integration window. A 400 ms value must never be labeled "short-term" and a 3 s value must never be labeled "momentary" anywhere a benchmark report references this field |
| `energy_curve` | array of `{"t_ms": integer, "rms_db": float}` | no | yes | `null` | Also usable to verify a fixture's own boundary is a genuine "cold stop" (near-zero energy at the edge) without a dedicated boundary-type field |
| `annotation_sources` | object, keys are field names from this table, values from the enum in §6 | yes | no | — | One entry per annotated field above that carries ground truth, e.g. `{"beat_timestamps":"SYNTHETIC_EXACT","key":"MANUAL","vocal_intervals":"MODEL_ESTIMATE","loudness_momentary":"SYNTHETIC_EXACT","loudness_short_term":"SYNTHETIC_EXACT","loudness_integrated":"SYNTHETIC_EXACT","acceptable_entry_regions":"SYNTHETIC_EXACT","acceptable_exit_regions":"SYNTHETIC_EXACT"}`. Any field with no entry here is treated as `UNKNOWN` and **must not** be used as ground truth by a benchmark runner |
| `notes` | string | no | yes | `null` | Free text |

## 4. Tier-1 pair object (`tier1_pairs.jsonl`, one JSON object per line)

Represents one ordered (outgoing → incoming) transition test case between two Tier-1 fixtures.

| Field | Type | Required | Nullable | Default | Semantics |
|---|---|---|---|---|---|
| `pair_id` | string | yes | no | — | Stable unique ID, e.g. `PAIR-SYN-A-001` |
| `outgoing_fixture_id` | string | yes | no | — | References a `fixture_id` in `tier1_fixtures.jsonl` |
| `incoming_fixture_id` | string | yes | no | — | References a `fixture_id` in `tier1_fixtures.jsonl` |
| `benchmark_lane` | enum: `A_TIMING_STRUCTURE` \| `B_CONTENT_COLLISION` \| `C_ENERGY_LOUDNESS` \| `D_HARMONIC_TEMPO` \| `E_CONFIDENCE_FALLBACK` | yes | no | — | Primary lane; exactly one |
| `secondary_lanes` | array of the same enum | no | no | `[]` | Additional lanes this pair is also relevant to |
| `case_tags` | array of string | yes | no | — | Drawn from the case vocabulary in the benchmark contract's per-lane tables, e.g. `["same_bpm_wrong_beat_phase"]` |
| `transition_class_policy` | object, full shape in §6 | yes | no | — | The outcome-aware acceptance structure |
| `is_continuous_work` | boolean | no | no | `false` | `true` only when the pair's two fixtures are authored as a single continuous musical work split at an edit point. Drives `GAPLESS` eligibility (§9) |
| `sequencing_suppression_intended` | boolean | no | no | `false` | `true` only when the pair models an intentional "apply no AutoMix processing at all" authoring intent, without claiming the fixtures are one continuous work |
| `manipulation_constraints` | object, full shape in §7 | no | yes | `null` (global defaults from §7 apply) | Per-pair overrides of the default DSP-manipulation bounds |
| `known_trap_purpose` | string | yes | no | — | One-sentence statement of what failure mode this pair is designed to expose |
| `annotation_sources` | object | yes | no | — | Same source-enum pattern as the fixture object, scoped to pair-level annotations: `transition_class_policy`, `is_continuous_work`, `sequencing_suppression_intended`, and any `manipulation_constraints` overrides |
| `evaluation_exclusions` | array of string | no | no | `[]` | Named metrics/dimensions this pair is explicitly excluded from scoring on, with a reason recorded in `notes`; every entry must reference a specific metric/dimension name from the benchmark contract §8/§9, never a blanket exclusion |
| `split` | enum: `dev` \| `holdout` | yes | no | — | See §2 `split_assignment_policy` |
| `created_at` | string (ISO-8601 date) | yes | no | — | |
| `notes` | string | no | yes | `null` | Free text |

## 5. Tier-2 pair object (`tier2_pairs.jsonl`, one JSON object per line)

Represents one commercial-track transition pair used for private, real-world listening comparisons against baseline systems (benchmark contract §6). **Never contains audio, `local_path`, or `checksum` fields.**

| Field | Type | Required | Nullable | Default | Semantics |
|---|---|---|---|---|---|
| `pair_id` | string | yes | no | — | |
| `outgoing_ref` | object `{"title": string, "artist": string, "provider_ids": {"spotify": string\|null, "apple_music": string\|null, "isrc": string\|null}}` | yes | no | — | Metadata/IDs only, never audio |
| `incoming_ref` | object, same shape as `outgoing_ref` | yes | no | — | |
| `benchmark_lane` | same enum as §4 | no | yes | `null` | Optional for Tier-2; commercial pairs are not always designed against a specific lane |
| `case_tags` | array of string | no | no | `[]` | |
| `reference_system` | string | yes | no | — | Which baseline system this session observed, e.g. `"Apple Music AutoMix"`, `"djay Automix"` (benchmark contract §6.2) |
| `observed_transition_timestamp_ms` | integer | no | yes | `null` | When the reference system executed its transition, as observed during the listening session |
| `observed_settings` | string | no | yes | `null` | Free text — whatever transition-relevant settings were visible/knowable for the reference system, e.g. `"Spotify Auto mode, default crossfade"` |
| `listening_scores` | object, an embedded human-rubric result (benchmark contract §9) | no | yes | `null` | Its `preference_outcome` field (rubric dimension 16) must be one of `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE` — never a bare 1–5 score, so Tier-2 sessions are structurally compatible with the same statistical-gate machinery as Tier-1, even though Tier-2 results never count toward a Tier-1 quantitative gate (benchmark contract §6.3) |
| `created_at` | string (ISO-8601 date) | yes | no | — | |
| `notes` | string | no | yes | `null` | |

## 6. `transition_class_policy` object (v3) — full shape and validation constraints

```json
{
  "accepted_unconditional": ["SIMPLE_CROSSFADE"],
  "accepted_conditional": [
    {
      "class": "SHORT_EQ_BLEND",
      "conditions": ["COND_BEAT_OK", "COND_DOWNBEAT_OK"],
      "all_required": true,
      "human_confirmations": [
        { "dimension": "beat_coherence", "min_score": 3 }
      ],
      "human_all_required": true
    }
  ],
  "rejected_conditional": [
    {
      "class": "FULL_DJ_BLEND",
      "unless_conditions": ["COND_VOCAL_OK"],
      "all_required": true,
      "reason": "Illustrative only: acceptable if and only if the rendered output demonstrates COND_VOCAL_OK, by any technique."
    }
  ],
  "rejected": [
    { "class": "GAPLESS", "reason": "Illustrative only: this pair's fixtures are not authored as a continuous work (is_continuous_work=false), so a seamless no-processing join would misrepresent two independent tracks as one." }
  ]
}
```

**This example is itself valid under §6.1's constraints** — see the worked mutual-exclusivity check immediately below the field table (after §6.1). No class value is repeated across `accepted_unconditional`, `accepted_conditional[].class`, `rejected_conditional[].class`, and `rejected[].class`: `SIMPLE_CROSSFADE`, `SHORT_EQ_BLEND`, `FULL_DJ_BLEND`, and `GAPLESS` each appear exactly once, in exactly one list. `CUT` and `NO_SPECIAL_TRANSITION` appear in none of the four lists, which is valid and simply means both default to the closed-world rejection (§6.1 rule 2) for this illustrative pair.

| Field | Type | Required | Nullable | Default | Semantics |
|---|---|---|---|---|---|
| `accepted_unconditional` | array of class enum (`FULL_DJ_BLEND` \| `SHORT_EQ_BLEND` \| `SIMPLE_CROSSFADE` \| `GAPLESS` \| `CUT` \| `NO_SPECIAL_TRANSITION`) | yes | no | `[]` | Classes always a correct *choice* for this pair; execution quality is still scored separately by the objective/human metrics |
| `accepted_conditional` | array of objects (shape below) | yes | no | `[]` | |
| `accepted_conditional[].class` | class enum | yes | no | — | |
| `accepted_conditional[].conditions` | array of Condition-Registry ID strings (benchmark contract §7: `COND_BEAT_OK`, `COND_DOWNBEAT_OK`, `COND_CUE_OK`, `COND_PHRASE_OK`, `COND_SECTION_OK`, `COND_TEMPO_ENVELOPE_OK`, `COND_PITCH_ENVELOPE_OK`, `COND_VOCAL_OK`, `COND_BASS_OK`, `COND_LOUDNESS_OK`) | no | no | `[]` | Objective conditions that must be measured-satisfied for this class to be scored correct |
| `accepted_conditional[].all_required` | boolean | no | no | `true` | `true` = every listed `conditions` entry must hold (AND); `false` = at least one (OR) |
| `accepted_conditional[].human_confirmations` | array of `{"dimension": string (one of the 15 human-rubric dimension names, benchmark contract §9.2), "min_score": integer [1,5]}` | no | no | `[]` | Additional human-rubric requirements, used when the objective Condition Registry does not cleanly cover the pair's specific structural situation (e.g. cross-meter downbeat compatibility) |
| `accepted_conditional[].human_all_required` | boolean | no | no | `true` | AND/OR semantics for `human_confirmations`, same convention as `all_required` |
| `rejected_conditional` | array of objects (shape below) | yes | no | `[]` | Classes rejected **unless** a stated outcome condition holds |
| `rejected_conditional[].class` | class enum | yes | no | — | |
| `rejected_conditional[].unless_conditions` | array of Condition-Registry ID strings | yes | no | — | Must be non-empty — a `rejected_conditional` entry with no `unless_conditions` is invalid (use `rejected` instead) |
| `rejected_conditional[].all_required` | boolean | no | no | `true` | AND/OR semantics, same convention |
| `rejected_conditional[].reason` | string | yes | no | — | **Mandatory.** Must describe an outcome/structural fact, never name a specific implementation technology as the *only* valid path — e.g. valid: "acceptable only if the rendered output demonstrates `COND_VOCAL_OK`, by any technique"; invalid: "acceptable only if stem separation is applied" |
| `rejected` | array of objects `{"class": class enum, "reason": string}` | yes | no | `[]` | Classes **never** correct regardless of any condition. `reason` is mandatory and must cite a fixture-authored, corpus-design-time-known fact (e.g. `is_continuous_work`, `sequencing_suppression_intended`, an empty region-annotation array, or `energy_curve` evidence) — never "the benchmark cannot currently measure this," which must instead be expressed via `accepted_conditional.human_confirmations` |

### 6.1 Validation constraints (binding on every pair)

1. **Mutual exclusivity:** a given class value must appear in **at most one** of `accepted_unconditional`, `accepted_conditional[].class`, `rejected_conditional[].class`, `rejected[].class` for a single pair. A pair violating this is invalid and must be rejected by a manifest linter/benchmark runner before scoring.
2. **Closed-world default:** a class not listed in any of the four lists defaults to rejected with the fixed generic reason `"not enumerated as acceptable for this pair"`. This default reason is deliberately weak and **must not**, by itself, ground a `C11` finding (benchmark contract §10) — only an explicit `rejected` or `rejected_conditional` entry (each carrying a specific, mandatory reason) may ground `C11`.
3. **Scoring rule** (also stated in the benchmark contract §8), given a rendered transition's `observed_class` (§9):
   - `observed_class ∈ accepted_unconditional` → correct.
   - `observed_class` has an `accepted_conditional` entry → correct iff its `conditions` (per `all_required`) and `human_confirmations` (per `human_all_required`) are satisfied; else mismatch (not automatically `C11`-eligible).
   - `observed_class` has a `rejected_conditional` entry → correct iff its `unless_conditions` (per `all_required`) **are** satisfied; if not, mismatch **and** `C11`-eligible, grounded by that entry's `reason`.
   - `observed_class` has a `rejected` entry → always mismatch and `C11`-eligible.
   - Otherwise → mismatch per the closed-world default (rule 2 above), not `C11`-eligible.
4. `rejected_conditional[].reason` and `rejected[].reason` must never name a specific implementation technology (e.g. a named DSP technique or modifier flag) as the sole qualifying mechanism — acceptance/rejection must be defined in terms of Condition-Registry IDs (i.e., measured outcomes), which are technology-agnostic by construction.
5. **Worked mutual-exclusivity check for the §6 example above:**

   | Class | `accepted_unconditional` | `accepted_conditional[].class` | `rejected_conditional[].class` | `rejected[].class` | Appears in |
   |---|---|---|---|---|---|
   | `SIMPLE_CROSSFADE` | ✓ | — | — | — | exactly 1 list |
   | `SHORT_EQ_BLEND` | — | ✓ | — | — | exactly 1 list |
   | `FULL_DJ_BLEND` | — | — | ✓ | — | exactly 1 list |
   | `GAPLESS` | — | — | — | ✓ | exactly 1 list |
   | `CUT` | — | — | — | — | 0 lists (closed-world default applies) |
   | `NO_SPECIAL_TRANSITION` | — | — | — | — | 0 lists (closed-world default applies) |

   Reading across each row: every class appears in at most one column with a ✓, so the intersection of any two of the four lists is the empty set for this example. Rule 1 (mutual exclusivity) is satisfied.

## 7. `manipulation_constraints` object — full shape

| Field | Type | Required | Nullable | Default (applied when the whole object, or this specific field, is absent) | Semantics |
|---|---|---|---|---|---|
| `tempo_ratio_max_deviation` | float (0,1) | no | no | `0.12` | Maximum allowed deviation of applied tempo ratio from 1.0 for `COND_TEMPO_ENVELOPE_OK`/`C7` to treat the correction as safe. Default derived relative to SimpMusic's own shipped ±25% ceiling (P0-M1 §6), intentionally tighter |
| `max_pitch_shift_semitones` | float > 0 | no | no | `3` | Maximum allowed pitch-shift magnitude for `COND_PITCH_ENVELOPE_OK`/`C8` |
| `low_band_coactivity_threshold_db` | float ≤ 0 | no | no | `-12` | Low-band (20–150 Hz) RMS threshold, relative to each track's own low-band peak RMS, above which both tracks are considered simultaneously "active" for `COND_BASS_OK`/`C5` co-activity purposes |
| `low_band_coactivity_min_duration_ms` | integer > 0 | no | no | `500` | Minimum sustained duration of simultaneous low-band activity (above the threshold) required before it counts toward co-activity |
| `low_band_coactivity_ratio_ceiling` | float [0,1] | no | no | `0.5` | Maximum fraction of the transition window that may show low-band co-activity before `COND_BASS_OK` fails (and, combined with a short window, before `C5` fires) |

A pair's `manipulation_constraints` object, when present, may override any subset of these fields; unlisted fields fall back to their default. A pair overriding any field must record why in its `notes` field and add the specific field path (e.g. `"manipulation_constraints.tempo_ratio_max_deviation"`) to its `annotation_sources`, so a widened/narrowed tolerance is never silently applied.

## 8. Fixture/pair ID convention

`{PREFIX}-{LANE}-{SEQ}`: `PREFIX` is `SYN` (synthetic), `OWN` (owner-created), `PD` (public domain), or `CC0`; `LANE` is the single-letter primary lane code (`A`–`E`), or `X` for a general-purpose fixture not tied to one lane; `SEQ` is a zero-padded sequence number unique within `PREFIX-LANE`. Pairs additionally carry a `PAIR-` prefix (e.g. `PAIR-SYN-A-001`) to disambiguate from fixture IDs in tooling. This is a recommendation for corpus-production consistency, not a hard schema constraint — the schema only requires `fixture_id`/`pair_id` to be a stable, unique string.

## 9. Transition render record — full shape

**Not corpus ground truth.** The shape of a per-rendered-transition measurement record a benchmark runner produces when it executes a system under test against a pair (Tier-1 or Tier-2). Storage location is left to the benchmark-execution task that produces it; it is never committed as corpus data alongside §3–§5's files.

| Field | Type | Required | Nullable | Semantics |
|---|---|---|---|---|
| `pair_id` | string | yes | no | References the scored pair |
| `system_under_test` | string | yes | no | e.g. `"AutoMix candidate v0.1"`, `"fixed_equal_power_crossfade"`, `"SIMPMUSIC_CLASS_REFERENCE"` |
| `run_timestamp` | string (ISO-8601 datetime) | yes | no | |
| `overlap_ms` | integer ≥0 | yes | no | Measured duration where both tracks' audio is simultaneously present above a noise floor in the rendered output |
| `inter_track_gap_ms` | integer ≥0 | conditional | yes | **Mandatory (non-null) whenever `overlap_ms` is at or below the measurement epsilon (default 20 ms).** Measured silence between the end of the outgoing track's rendered audio and the start of the incoming track's rendered audio. A `null` value in that situation is itself meaningful — it forces `observed_class = UNCLASSIFIED_ANOMALY` (§9.1) rather than being treated as 0 |
| `has_volume_automation` | boolean | yes | no | A volume/gain curve during the overlap deviating from static/native gain by more than a measurement-noise epsilon |
| `has_eq_automation` | boolean | yes | no | A detectable spectral/band-gain change over time during the overlap beyond native equalization |
| `has_tempo_pitch_automation` | boolean | yes | no | Playback rate or pitch deviates from native by more than a measurement epsilon at any point in the overlap |
| `sustained_beat_lock_ratio` | float [0,1] | no | yes | Fraction of beat-grid instants within the overlap window where, using each track's own beat timestamps mapped through its actually-applied playback-rate curve (native if `has_tempo_pitch_automation=false`), instantaneous beat-alignment error ≤1/16 beat **and** downbeat-phase error =0 simultaneously, relative to a shared beat/bar grid. `null` when reliable beat ground truth (`SYNTHETIC_EXACT`/`MANUAL`) is unavailable for either track — never imputed |
| `has_sustained_beat_lock` | boolean | no | yes | `true` iff `sustained_beat_lock_ratio ≥0.8` **and** `overlap_ms ≥ 4×local_bar_period_ms`; `null` when `sustained_beat_lock_ratio` is `null` |
| `cue_placement_ok` | boolean | yes (when `overlap_ms > epsilon`; otherwise irrelevant) | no | `true` if, for each side (outgoing exit / incoming entry) whose `acceptable_exit_regions_ms`/`acceptable_entry_regions_ms` carries reliable (`SYNTHETIC_EXACT`/`MANUAL`) ground truth, the actual rendered entry/exit point lands inside that fixture's annotated region (cue-region error =0, i.e. `COND_CUE_OK` satisfied for that side); when neither side has reliable region ground truth, defaults `true` (nothing to check — permissive, not a free pass to grant the label, since `has_sustained_beat_lock` is independently required); `false` whenever reliable ground truth exists for a side and that side's rendered point falls outside it |
| `phrase_section_alignment_ok` | boolean | yes (when `overlap_ms > epsilon`) | no | `true` if, for whichever of `phrase_boundaries_ms`/`section_boundaries` carries reliable ground truth for the relevant track(s), the actual rendered entry/exit point satisfies the corresponding contract §7 condition (`COND_PHRASE_OK` and/or `COND_SECTION_OK`); when neither is reliably annotated, defaults `true` (nothing to check); `false` whenever reliably annotated and the corresponding condition is not satisfied |
| `has_native_tempo_structural_evidence` | boolean | yes (when `overlap_ms > epsilon`) | no | `has_sustained_beat_lock AND cue_placement_ok AND phrase_section_alignment_ok`, where a `null` `has_sustained_beat_lock` (missing beat ground truth) resolves this composite to `false` — the native-tempo/no-correction `FULL_DJ_BLEND` branch (§9.1 rule 3d — distinct from rule 3c, which is the tempo/pitch-automation path) is never granted on missing evidence |
| `outgoing_used_natural_full_duration` | boolean | yes | no | Outgoing track played to its own `authored_exit_boundary_ms` (or `duration_ms` if that field was null), not truncated |
| `incoming_used_natural_start` | boolean | yes | no | Incoming track began at its own `authored_entry_boundary_ms` (or `0` if null) |
| `stem_separation_applied` | boolean | yes | no | **Diagnostic metadata only — never referenced by any `transition_class_policy` entry or classification rule.** Whether the system under test applied stem/source-separation or targeted vocal/instrument attenuation during the overlap |
| `engine_reported_class` | class enum | no | yes | The system under test's own self-reported/logged class label, if any. **Diagnostic only, never authoritative** |
| `observed_class` | enum: `FULL_DJ_BLEND` \| `SHORT_EQ_BLEND` \| `SIMPLE_CROSSFADE` \| `GAPLESS` \| `CUT` \| `NO_SPECIAL_TRANSITION` \| `UNCLASSIFIED_ANOMALY` | yes | no | Computed **only** from the fields above plus the pair's `is_continuous_work`/`sequencing_suppression_intended` annotations, via the deterministic decision procedure in §9.1. The sole scoring input for `transition_class_policy` matching, `C11`, and `G4` |
| `class_label_mismatch` | boolean | yes | no | `engine_reported_class != observed_class`. Diagnostic signal about engine self-assessment honesty; no direct gate consequence on its own |

### 9.1 `observed_class` decision procedure (deterministic, runner-applied)

1. Measure `overlap_ms`; if at or below the epsilon (default 20 ms), measure `inter_track_gap_ms` (mandatory in that branch).
2. **If `overlap_ms ≤ epsilon`:**
   - `inter_track_gap_ms` missing/`null` → `UNCLASSIFIED_ANOMALY`.
   - `inter_track_gap_ms ≤ epsilon` (sample-contiguous): if `outgoing_used_natural_full_duration` and `incoming_used_natural_start` are both `true` and `is_continuous_work=true` → `GAPLESS`; if both `true` and `is_continuous_work=false` → `NO_SPECIAL_TRANSITION`; otherwise → `CUT`.
   - `inter_track_gap_ms > epsilon` (a real, measurable, audible gap): `GAPLESS` is never assigned in this branch. Both boundaries natural → `NO_SPECIAL_TRANSITION`; otherwise → `CUT`.
3. **If `overlap_ms > epsilon`:**
   - `has_volume_automation=false` → `UNCLASSIFIED_ANOMALY`.
   - `has_eq_automation=false` and `has_tempo_pitch_automation=false` and `has_native_tempo_structural_evidence=false` → `SIMPLE_CROSSFADE`.
   - `has_tempo_pitch_automation=true` → `FULL_DJ_BLEND` (sufficient on its own, independent of EQ or structural-evidence values; execution quality scored separately via `COND_TEMPO_ENVELOPE_OK`/`COND_PITCH_ENVELOPE_OK`/`C7`/`C8`).
   - `has_tempo_pitch_automation=false` and `has_native_tempo_structural_evidence=true` → `FULL_DJ_BLEND` (the no-correction/native-tempo path; **EQ automation is not required** for this path).
   - `has_tempo_pitch_automation=false` and `has_native_tempo_structural_evidence=false` and `has_eq_automation=true` → `SHORT_EQ_BLEND`.
4. `class_label_mismatch = (engine_reported_class != observed_class)`.

`engine_reported_class` is never consulted in steps 1–3.

## 10. Annotation source enum

Every annotated field, on fixture, Tier-1 pair, and Tier-2 pair objects, must declare its source as exactly one of:

| Value | Meaning |
|---|---|
| `SYNTHETIC_EXACT` | Fixture/pair was generated with this value as an exact input parameter — zero measurement error by construction |
| `MANUAL` | A human annotator directly marked this value by inspection/listening |
| `DATASET` | Sourced from an existing published dataset's own annotations (provenance of that dataset's own annotation method recorded in `notes`) |
| `MODEL_ESTIMATE` | Produced by an automated analyzer/model — inherently uncertain, must carry a `confidence` value where the schema supports one |
| `PROVIDER_METADATA` | Sourced from a third-party catalog/provider metadata field — never treated as ground truth for `OBJECTIVE`-classified metrics |
| `UNKNOWN` | Source not established; must not be used as ground truth for any objective metric or catastrophic-failure detection until reclassified |

**Binding rules:**
1. No benchmark report may present a `MODEL_ESTIMATE`, `PROVIDER_METADATA`, or `UNKNOWN`-sourced annotation as ground truth.
2. Metrics computed against such annotations must be reported with their `PROXY` classification carried through (benchmark contract §8).
3. Any catastrophic-failure code that depends on comparison against ground truth must only fire using `SYNTHETIC_EXACT` or `MANUAL` sourced values, **except** `C9`'s human-corroboration path (benchmark contract §10), which is deliberately independent of annotation source.
4. A field with no `annotation_sources` entry is treated identically to one explicitly marked `UNKNOWN`.

## 11. Corpus-level validation rules a benchmark runner MUST enforce before scoring

1. Every `corpus_minimums` field in `manifest.json` (§2) is met by the actual corpus (fixture/pair counts, per-lane counts, per-subset counts, holdout counts).
2. Every Tier-1 fixture's `annotation_sources` accounts for every non-null field that carries ground truth; no field is used as `OBJECTIVE` evidence without a corresponding `SYNTHETIC_EXACT`/`MANUAL` entry.
3. Every Tier-1/Tier-2 pair's `transition_class_policy` satisfies the §6.1 validation constraints (mutual exclusivity, mandatory `reason` fields, no technology-named `rejected`/`rejected_conditional` reasons).
4. No Tier-2 pair object contains `local_path`, `checksum`, or any other audio-bearing field.
5. No pair's `split` value changes between benchmark runs once results exist for that pair (per §2 `split_assignment_policy`).
6. Every fixture referenced by a pair (`outgoing_fixture_id`/`incoming_fixture_id`) exists in `tier1_fixtures.jsonl`.

A corpus or pair set failing any of the above must be rejected by the runner before any scoring is attempted, not silently worked around.

## 12. Versioning and change discipline

`manifest.json.schema_version` follows semver: a breaking field change (rename, type change, required-field removal, or a changed validation constraint that would silently alter scoring) bumps the major version; additive optional fields bump the minor version. Every corpus-affecting Git commit must remain reviewable as a normal diff and must not silently move a pair between `dev`/`holdout` after results exist for it (§11 rule 5).

## 13. Changelog (non-normative — historical context only; §1–§12 above are the complete current definition and require nothing below to implement)

- **4.0.0** (this revision): full self-contained rewrite (no field's definition depends on reading an earlier revision); added `cue_placement_ok`, `phrase_section_alignment_ok`, `has_native_tempo_structural_evidence` to the transition render record and to the `observed_class` decision procedure, so a native-tempo `FULL_DJ_BLEND` no longer requires EQ automation and no longer qualifies on beat-lock alone without demonstrated cue/phrase placement evidence; added §11's explicit runner-enforced validation-rule list; formalized the Tier-2 pair object as its own complete table (§5) rather than prose.
- **3.0.0**: introduced `rejected_conditional`; replaced `accepted_conditional[].human_confirmation` (singular) with `.human_confirmations` (array) + `.human_all_required`; removed `accepted_conditional[].requires_modifier`; added `sustained_beat_lock_ratio`/`has_sustained_beat_lock`/`inter_track_gap_ms` to the transition render record; added `lane_e_holdout_min` to `corpus_minimums`.
- **2.1.0**: added `authored_exit_boundary_ms`/`authored_entry_boundary_ms` (fixture), `is_continuous_work`/`sequencing_suppression_intended` (pair).
- **2.0.0**: replaced `expected_transition_class_set` with `transition_class_policy` (`accepted_unconditional`/`accepted_conditional`/`rejected`).
- **1.0.0**: initial schema.
