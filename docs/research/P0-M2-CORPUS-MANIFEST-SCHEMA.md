# P0-M2-R1 — Corpus Manifest Schema

Status date: 2026-08-11 (PM REVIEW #2 narrow repair pass — R10 holdout/sample-size fields, R11 transition-render-record shape, R12-driven `is_continuous_work`/`sequencing_suppression_intended` annotation fields)

Companion to `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`. Defines the machine-readable fixture/pair manifest that every benchmark run (baseline or candidate AutoMix engine) is scored against.

## 1. Format decision

**JSON Lines (`.jsonl`), one fixture or pair object per line**, plus a single top-level `manifest.json` index file.

Justification:

- **Line-addressable diffs**: `.jsonl` fixture/pair files diff cleanly in Git — adding, removing, or amending one fixture touches one line, keeping PR review of corpus changes tractable (relevant because this repository is public and every corpus change should be independently reviewable, per `AGENTS.md`'s evidence-first culture).
- **Streamable**: a benchmark runner can process the corpus without loading the entire manifest into memory, relevant once the corpus grows beyond the initial synthetic seed set.
- **No schema-migration lock-in**: unlike a relational/SQL corpus store, adding new optional fields (e.g., a new annotation source type, a new case tag) does not require a migration step — it requires only that consumers tolerate unknown fields, which is standard JSON practice.
- **YAML was considered and rejected** for the per-fixture/per-pair records specifically because YAML's whitespace sensitivity makes large hand-edited corpora more error-prone during manual annotation review; a single top-level `manifest.json` (small, human-edited far less often) is acceptable in plain JSON without that risk.

Four files (a fourth added by this revision — R11):

```text
docs/research/corpus/manifest.json          # top-level index: schema version, tier definitions, split assignment, corpus minimums
docs/research/corpus/tier1_fixtures.jsonl   # one JSON object per Tier-1 audio fixture (track-level)
docs/research/corpus/tier1_pairs.jsonl      # one JSON object per Tier-1 transition pair (references two fixture_id)
docs/research/corpus/tier2_pairs.jsonl      # one JSON object per Tier-2 pair (metadata/provider-ID references only, no audio)
```

A fifth, **result-record** stream (§10, new) — one JSON object per rendered transition actually produced by a benchmark run — is defined by shape in this document but its storage location/filename is intentionally left to the future benchmark-execution task that produces it (a disposable P0-M3 prototype per the benchmark contract §2's R8 clarification); it is not corpus ground truth and is not committed alongside the four files above.

No audio bytes are ever committed alongside these files; `tier1_fixtures.jsonl` stores a `local_path` field that resolves to owner-local storage outside Git (see §7), plus a `checksum` for integrity verification of whatever file exists at that path.

These files are **schema definitions and directory conventions specified by this document**; populating them with real fixtures/pairs is corpus-production work, not part of this specification deliverable (per Issue #4's "No audio files" / "This is a RESEARCH + SPECIFICATION task" constraints). Per the benchmark contract's R8 clarification, disposable benchmark-execution prototypes that populate and run against this schema are in scope for a future P0-M3 task; the shipping production engine is not.

## 2. Top-level `manifest.json`

```json
{
  "schema_version": "2.1.0",
  "generated_by": "P0-M2-R1 (PM REVIEW #2 repair pass)",
  "tiers": {
    "tier1": {
      "fixtures_file": "tier1_fixtures.jsonl",
      "pairs_file": "tier1_pairs.jsonl",
      "splits": ["dev", "holdout"]
    },
    "tier2": {
      "pairs_file": "tier2_pairs.jsonl",
      "splits": ["private_listening"]
    }
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
    "tier1_holdout_decisive_min_derivation": "R10 fix: G1 excludes TIE outcomes from its binomial n, so a holdout pool that is merely >=18 total pairs can fall below 18 DECISIVE trials the moment even one tie occurs. 22 is the smallest pool size for which the maximum tie count still compliant with the 20% inconclusive ceiling (floor(0.20*22)=4 ties, i.e. an 18.2% tie rate) still leaves 22-4=18 decisive trials. This is a worst-case guarantee, not an average-case hope: any holdout tie rate up to and including 20% at n=22 is proven, by this arithmetic, not to starve G1 below its required 18 decisive trials.",
    "per_lane_min": {
      "A_TIMING_STRUCTURE": 23,
      "B_CONTENT_COLLISION": 8,
      "C_ENERGY_LOUDNESS": 8,
      "D_HARMONIC_TEMPO": 12,
      "E_CONFIDENCE_FALLBACK": 23
    },
    "lane_a_clean_structure_subset_min": 10,
    "lane_a_clean_structure_subset_holdout_min": 3,
    "lane_e_should_not_full_blend_subset_min": 8,
    "lane_e_should_not_full_blend_subset_holdout_min": 3,
    "g2_simpmusic_comparison_subset_min": 30,
    "g2_simpmusic_comparison_subset_holdout_min": 9,
    "note": "R10 fix: every G1-G4 subset used by the G5 'must hold independently on holdout' requirement now has an explicit *_holdout_min field, not just a total. lane_a_clean_structure_subset_holdout_min=3 and lane_e_should_not_full_blend_subset_holdout_min=3 are each close to but not below the ~30% holdout_fraction_target applied to their respective subset totals (ceil(0.3*10)=3, ceil(0.3*8)=2.4 rounded up to 3 for the same reason G1's holdout was rounded up rather than down: a fractional holdout count that rounds down risks an execution where the stated fractional threshold has no valid integer interpretation). A benchmark runner MUST reject (refuse to score) any corpus that does not meet every minimum in this block, rather than silently scoring against an undersized holdout. Full derivation and gate-by-gate justification is in the benchmark contract's P0->P1 gate section; this file's corpus_minimums block is the single source of truth a benchmark runner reads at execution time."
  }
}
```

`split_assignment_policy` exists specifically to make the anti-overfitting rule in the benchmark contract ("Holdout pairs/categories may not be hand-tuned") auditable: any manifest diff that moves a pair between `dev` and `holdout` after benchmark results exist for it is a process violation and must be called out in the run's report, not silently applied.

`corpus_minimums` exists so the P0→P1 gate (contract §12) is mathematically executable rather than aspirational: every gate references one of these named minimums directly, and a benchmark runner can validate "is the corpus large enough to even attempt this gate, including its holdout-only re-check" before running any measurement.

## 3. Fixture object (`tier1_fixtures.jsonl`, one per line)

Represents a single audio track used as one side of one or more transition pairs.

| Field | Type | Required | Description |
|---|---|---|---|
| `fixture_id` | string | yes | Stable unique ID, e.g. `SYN-A-001` (prefix indicates lane/category, see §8 ID convention) |
| `local_path` | string | yes | Path to the audio file on owner-local storage; **not** resolvable from a public checkout without the owner's local fixture set |
| `checksum` | object `{algo, value}` | yes | e.g. `{"algo":"sha256","value":"..."}` — integrity check against `local_path`, and the canonical way to detect a fixture was silently swapped |
| `provenance` | enum: `SYNTHETIC`, `OWNER_CREATED`, `PUBLIC_DOMAIN`, `CC0`, `PERMISSIVE_OTHER` | yes | Source category; must be one of these five for any Tier-1 fixture — commercial/copyrighted audio is never valid here |
| `license` | string | yes | Exact license name/version/URL (e.g. `CC0-1.0`, `Public Domain (pre-1928 US)`, or a specific permissive-license grant text/URL for `PERMISSIVE_OTHER`) |
| `license_source_url` | string, nullable | conditional | Required unless `provenance` is `SYNTHETIC` or `OWNER_CREATED` |
| `duration_ms` | integer | yes | Full track duration |
| `authored_exit_boundary_ms` | integer, nullable | no | **New (R12).** The track's own authored/musically-natural end point, if different from `duration_ms` (e.g. a pre-edited "Part 1" fixture whose musical content stops before the raw file ends). Defaults to `duration_ms` when `null`. Used by the transition-render classification procedure (§10) to determine whether an outgoing track was played to its natural end (informs `GAPLESS`/`NO_SPECIAL_TRANSITION` vs `CUT` classification) — an observable, fixture-grounded fact, not a benchmark-runner inference. |
| `authored_entry_boundary_ms` | integer, nullable | no | **New (R12).** The track's own authored/musically-natural start point, if different from `0`. Defaults to `0` when `null`. Same purpose as `authored_exit_boundary_ms`, for the incoming side. |
| `genre_style_tags` | array of string | yes | e.g. `["pop"]`, `["hip-hop","dynamic-tempo"]` — drives the anti-overfitting coverage audit (benchmark contract §11) |
| `meter` | object `{numerator, denominator, confidence}`, nullable | yes (nullable) | e.g. `{"numerator":4,"denominator":4,"confidence":1.0}`; `null` for ambiguous-meter fixtures (an intentional Lane A case) |
| `bpm` | object `{value, confidence}`, nullable | yes (nullable) | Ground-truth or estimated tempo; `null` for variable-tempo fixtures (see `tempo_curve`) |
| `tempo_curve` | array of `{t_ms, bpm}`, nullable | no | Only present for variable-tempo fixtures; overrides `bpm` when present |
| `beat_timestamps_ms` | array of integer, nullable | conditional | Required whenever `annotation_sources.beat_timestamps` is `SYNTHETIC_EXACT` or `MANUAL` |
| `downbeat_indices` | array of integer, nullable | conditional | Indices into `beat_timestamps_ms` marking bar starts; required whenever `annotation_sources.downbeats` is `SYNTHETIC_EXACT`/`MANUAL` |
| `key` | object `{root, scale, camelot, confidence}`, nullable | yes (nullable) | e.g. `{"root":"A","scale":"minor","camelot":"8A","confidence":1.0}` |
| `phrase_boundaries_ms` | array of integer, nullable | no | |
| `section_boundaries` | array of `{t_start_ms, t_end_ms, label}`, nullable | no | `label` is free text but should use a small controlled vocabulary (`intro`, `verse`, `chorus`, `bridge`, `buildup`, `drop`, `outro`, `instrumental_break`, `other`) |
| `acceptable_entry_regions_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | Candidate regions where this track may serve as the **incoming** track's entry point. An **empty array** (not `null`) is a meaningful, authored statement that no acceptable entry region exists anywhere in this fixture — this is the exact mechanism `PAIR-SYN-A-008` (benchmark contract, catalog) relies on for its `FULL_DJ_BLEND` rejection, and it is a fact about the fixture's own authoring, not a benchmark measurement gap (R12 distinction). |
| `acceptable_exit_regions_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | Candidate regions where this track may serve as the **outgoing** track's exit point. Same empty-array-is-meaningful convention as above. For a fixture like `SYN-A-007` (musical content ends before a long silent tail), this field must be annotated to cover the pre-silence musical-content window specifically — **not** the silent tail — so `COND_CUE_OK` (contract §7) is well-defined and achievable by a competent engine (R12 fix; previously this field's intended scoping for that fixture was left implicit). |
| `vocal_intervals_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | **Source**-level vocal activity — where vocal content exists in this fixture's own, unmodified audio. Per the R12/contract §8 fix, this is **not** used directly as the ground truth for the vocal-overlap objective metric; that metric is computed against the *rendered* transition output (§10), which may differ from source-level overlap if the system under test applies stem/vocal attenuation. This field remains the input used to construct that rendered measurement and to design fixtures, but is not itself the pass/fail signal. |
| `bass_intervals_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | |
| `percussion_intervals_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | |
| `loudness` | object, nullable | no | `{"integrated_lufs": number, "momentary_curve": [{"t_ms":int,"lufs":number}, ...], "short_term_curve": [{"t_ms":int,"lufs":number}, ...]}`. Terminology is binding: `integrated_lufs` is a single programme-level value (BS.1770-5 gated integrated measurement); `momentary_curve` samples use a 400 ms integration window stepped at a 100 ms hop (EBU Tech 3341 momentary-metering convention layered on the BS.1770-5 K-weighted measurement); `short_term_curve` samples use a 3 s integration window. Never call a 400 ms value "short-term" or a 3 s value "momentary" anywhere a benchmark report references this field. |
| `energy_curve` | array of `{t_ms, rms_db}`, nullable | no | Also usable to verify a fixture's own boundary is a genuine "cold stop" (near-zero energy at the very edge) for cases like `PAIR-SYN-E-005`, without needing a dedicated boundary-type field. |
| `annotation_sources` | object, yes | yes | One entry per annotated field above, each valued with the source enum (§6) — e.g. `{"beat_timestamps":"SYNTHETIC_EXACT","key":"MANUAL","vocal_intervals":"MODEL_ESTIMATE","loudness_momentary":"SYNTHETIC_EXACT","loudness_short_term":"SYNTHETIC_EXACT","loudness_integrated":"SYNTHETIC_EXACT"}`. Any annotated field with no entry here is treated as `UNKNOWN` and **must not** be used as ground truth by a benchmark runner. |
| `notes` | string, nullable | no | Free text |

## 4. Pair object (`tier1_pairs.jsonl` / `tier2_pairs.jsonl`, one per line)

Represents one ordered (outgoing → incoming) transition test case.

| Field | Type | Required | Description |
|---|---|---|---|
| `pair_id` | string | yes | Stable unique ID, e.g. `PAIR-A-001` |
| `outgoing_fixture_id` | string (Tier-1) or `outgoing_ref` object (Tier-2) | yes | Tier-1: references `tier1_fixtures.jsonl`. Tier-2: `{"title":..., "artist":..., "provider_ids":{"spotify":"...", "apple_music":"...", "isrc":"..."}}` — metadata/IDs only, never audio |
| `incoming_fixture_id` / `incoming_ref` | same shape as above | yes | |
| `benchmark_lane` | enum: `A_TIMING_STRUCTURE`, `B_CONTENT_COLLISION`, `C_ENERGY_LOUDNESS`, `D_HARMONIC_TEMPO`, `E_CONFIDENCE_FALLBACK` | yes | Primary lane (benchmark contract §4). A pair may be tagged with more than one lane via `secondary_lanes` if genuinely multi-purpose, but must declare exactly one primary lane for reporting |
| `secondary_lanes` | array of the same enum | no | |
| `case_tags` | array of string | yes | Free-form but drawn from the case vocabulary in the benchmark contract's per-lane tables, e.g. `["same_bpm_wrong_beat_phase"]`, `["vocal_to_vocal"]`, `["large_tempo_gap"]` |
| `transition_class_policy` | object | yes | See §5 below. The outcome-aware acceptance structure (R2, extended by this revision — R12 — with two additional narrow escape/gate mechanisms: `human_confirmation` and `requires_modifier`, see §5). |
| `is_continuous_work` | boolean, default `false` | no | **New (R12).** `true` only when the pair's two fixtures are authored as a single continuous musical work split at an edit point (e.g. a scripted "Part 1"/"Part 2" pair with matching audio at the seam) — an authored, fixture-level fact fully known to the corpus creator, not a runtime inference. Drives `GAPLESS` classification in the transition-render decision procedure (§10) and is the explicit grounding for `PAIR-SYN-E-004`'s categorical rejection of every processed class. |
| `sequencing_suppression_intended` | boolean, default `false` | no | **New (R12).** `true` only when the pair models an intentional "do not apply special transition handling at all" product/authoring intent (e.g. `docs/research/P0-M0-MARKET-PRIOR-ART-LANDSCAPE.md` §13's "sequential album tracks" case). Distinguished from `is_continuous_work`: this pair is **not** claiming the two fixtures are one work, only that no AutoMix-specific processing should occur. Explicit grounding for `PAIR-SYN-E-006`'s categorical rejection. |
| `manipulation_constraints` | object, nullable | no | `{"tempo_ratio_max_deviation": number, "max_pitch_shift_semitones": number, "low_band_coactivity_threshold_db": number, "low_band_coactivity_min_duration_ms": integer, "low_band_coactivity_ratio_ceiling": number}`. When omitted, a benchmark runner MUST use the global defaults defined in the benchmark contract's Condition Registry (`tempo_ratio_max_deviation=0.12`, `max_pitch_shift_semitones=3`, `low_band_coactivity_threshold_db=-12`, `low_band_coactivity_min_duration_ms=500`, `low_band_coactivity_ratio_ceiling=0.5`). A pair overriding any field must record why in `notes` and add the field to `annotation_sources`. |
| `known_trap_purpose` | string | yes | One-sentence statement of what failure mode this pair is designed to expose |
| `annotation_sources` | object | yes | Same source-enum pattern as the fixture object, scoped to pair-level annotations (`transition_class_policy`, `is_continuous_work`, `sequencing_suppression_intended`, `manipulation_constraints` overrides, `acceptable_entry_regions`/`acceptable_exit_regions` overrides if pair-specific) |
| `evaluation_exclusions` | array of string, nullable | no | Named metrics/dimensions this pair is explicitly excluded from scoring on, with a reason |
| `split` | enum: `dev`, `holdout` (Tier-1) or `private_listening` (Tier-2) | yes | See §2 `split_assignment_policy` |
| `created_at` | ISO-8601 date | yes | |
| `notes` | string, nullable | no | |

## 5. `transition_class_policy` object

```json
{
  "accepted_unconditional": ["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"],
  "accepted_conditional": [
    {
      "class": "FULL_DJ_BLEND",
      "conditions": ["COND_BEAT_OK", "COND_DOWNBEAT_OK"],
      "all_required": true,
      "human_confirmation": null,
      "requires_modifier": null
    }
  ],
  "rejected": [
    {
      "class": "GAPLESS",
      "reason": "..."
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `accepted_unconditional` | Transition classes that are a correct *choice* for this pair regardless of how well the engine executes them. |
| `accepted_conditional[].class` | The class in question (e.g. `FULL_DJ_BLEND`). |
| `accepted_conditional[].conditions` | Condition-Registry IDs (contract §7) that must be measured-satisfied, per `all_required`. |
| `accepted_conditional[].all_required` | `true` (default) = AND; `false` = OR. |
| `accepted_conditional[].human_confirmation` | **New (R12).** Nullable object `{"dimension": "beat_coherence", "min_score": 3}`. Used only where the standard objective Condition Registry does not cleanly apply to the pair's specific structural situation (the canonical example: `PAIR-SYN-A-010`'s cross-meter 7/8-vs-4/4 pairing, where no objective downbeat-compatibility condition is currently defined). When present, the class is accepted **in addition to** any listed `conditions` only if the stated human-rubric dimension (contract §9) also meets `min_score` from a blinded listener. This directly implements the PM's R12 instruction to route a benchmark's own measurement-capability gap to human evaluation rather than to a categorical rejection that would incorrectly imply musical impossibility. |
| `accepted_conditional[].requires_modifier` | **New (R12).** Nullable string naming a boolean field from the transition render record (§10, e.g. `"stem_separation_applied"`). When present, the class is accepted only if that modifier is `true` **and** the listed `conditions` are satisfied. Used for cases where a class should remain generally rejected for the realistic near-term case but must not categorically block a specific, more advanced, named technique — see `PAIR-SYN-E-007` in the pair catalog, which keeps `FULL_DJ_BLEND` rejected *without* `stem_separation_applied=true`, but accepts it conditionally *with* that modifier plus `COND_VOCAL_OK`. |
| `rejected` | Transition classes that are **never** a correct choice for this pair, regardless of execution quality or any modifier, each with a mandatory `reason`. Per the R12 re-audit (benchmark contract §6), a `reason` is only valid grounding if it cites a **fixture-authored, fully-known-at-corpus-design-time fact** (e.g. `is_continuous_work`, `sequencing_suppression_intended`, an empty `acceptable_entry_regions_ms`/`acceptable_exit_regions_ms` array, or a fixture's own `energy_curve` showing a genuine cold boundary) — **never** "the benchmark currently has no way to measure whether this succeeds," which is an evaluation-capability limitation, not evidence of musical impossibility, and must instead be expressed as `accepted_conditional` with `human_confirmation`. |

**Closed-world default**: any transition class not listed in `accepted_unconditional` or `accepted_conditional` for a pair is treated as `rejected` by default (reason: `"not enumerated as acceptable for this pair"`) even if it is not explicitly written into the `rejected` array. This default-strength reason is deliberately weak and is **not**, by itself, sufficient grounding for a `C11` finding (contract §10) — only an explicitly authored `rejected` entry with a specific, fixture-grounded reason is.

## 6. Annotation source enum

Every annotated field, on both fixture and pair objects, must declare its source as exactly one of:

| Value | Meaning |
|---|---|
| `SYNTHETIC_EXACT` | Fixture was generated with this value as an exact input parameter — zero measurement error by construction |
| `MANUAL` | A human annotator directly marked this value by inspection/listening |
| `DATASET` | Sourced from an existing published dataset's own annotations (e.g., EDM-CUE's expert cue points) |
| `MODEL_ESTIMATE` | Produced by an automated analyzer/model — inherently uncertain, must carry a `confidence` value where the schema supports one |
| `PROVIDER_METADATA` | Sourced from a third-party catalog/provider metadata field — never treated as ground truth for `OBJECTIVE`-classified metrics |
| `UNKNOWN` | Source not established; must not be used as ground truth until reclassified |

**Binding rule**: no benchmark report may present a `MODEL_ESTIMATE`, `PROVIDER_METADATA`, or `UNKNOWN`-sourced annotation as ground truth. Metrics computed against such annotations must be reported with their `PROXY` classification carried through, and any catastrophic-failure code that depends on comparison against ground truth must only fire using `SYNTHETIC_EXACT` or `MANUAL` sourced values, except `C9`'s human-corroboration path, which is deliberately independent of annotation source.

## 7. Tier-2 privacy and non-redistribution

Tier-2 pair objects (`tier2_pairs.jsonl`) never contain audio, `local_path`, or `checksum` fields — only `outgoing_ref`/`incoming_ref` metadata objects (title/artist/provider IDs), plus:

- `observed_transition_timestamp_ms`
- `observed_settings`
- `listening_scores` — an embedded human-rubric result object per benchmark contract §9, whose `preference_outcome` field (dimension 16) must be one of `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE`

This keeps Tier-2 fully within `AGENTS.md` non-negotiable rules 3/4 — no protected audio, no DRM bypass, no redistribution risk.

## 8. Fixture/pair ID convention

`{PREFIX}-{LANE}-{SEQ}`, where `PREFIX` is `SYN`/`OWN`/`PD`/`CC0`, `LANE` is the single-letter primary lane code (`A`–`E`, or `X` for general-purpose), and `SEQ` is a zero-padded sequence number unique within `PREFIX-LANE`. A recommendation for corpus-production work, not a hard schema constraint.

## 9. Versioning and change discipline

- `manifest.json.schema_version` follows semver. **This revision bumps `2.0.0` → `2.1.0`** (additive, non-breaking): `authored_exit_boundary_ms`/`authored_entry_boundary_ms` (fixture), `is_continuous_work`/`sequencing_suppression_intended` (pair), and `accepted_conditional[].human_confirmation`/`.requires_modifier` (transition_class_policy) are all new optional fields with safe defaults; existing v2.0.0 consumers that ignore unknown fields remain compatible, and no existing required field or enum value was removed or renamed.
- Every corpus-affecting Git commit must be reviewable as a normal diff and must not silently move a pair between `dev`/`holdout` after that pair has benchmark results recorded against it.
- This schema document itself, once corpus production begins, should be updated only via a task that records the schema version bump and the reason.

## 10. Transition render record (new — R11)

**Not corpus ground truth.** This is the shape of a per-rendered-transition measurement record a benchmark runner produces when it actually executes a system under test against a pair (Tier-1 or Tier-2). It exists in this document so the benchmark contract's transition-class taxonomy and classification decision procedure (contract §5) are binding against a concrete, named field list rather than prose alone — but the file/store this record lives in is intentionally left to the future benchmark-execution task (a disposable P0-M3 prototype) that produces it; it is not part of `tier1_pairs.jsonl`/`tier1_fixtures.jsonl` and is never committed as corpus data.

| Field | Type | Description |
|---|---|---|
| `pair_id` | string | References the scored pair |
| `system_under_test` | string | e.g. `"AutoMix candidate v0.1"`, `"fixed_equal_power_crossfade"`, `"SIMPMUSIC_CLASS_REFERENCE"` |
| `run_timestamp` | ISO-8601 datetime | |
| `overlap_ms` | integer | Measured duration where both tracks' audio is simultaneously present above a noise floor in the rendered output |
| `has_volume_automation` | boolean | A volume/gain curve during the overlap deviating from static/native gain by more than a measurement-noise epsilon |
| `has_eq_automation` | boolean | A detectable spectral/band-gain change over time during the overlap beyond native equalization |
| `has_tempo_pitch_automation` | boolean | Playback rate or pitch deviates from native by more than a measurement epsilon at any point in the overlap |
| `outgoing_used_natural_full_duration` | boolean | Outgoing track played to its own `authored_exit_boundary_ms` (or `duration_ms` if null), not truncated |
| `incoming_used_natural_start` | boolean | Incoming track began at its own `authored_entry_boundary_ms` (or `0` if null) |
| `stem_separation_applied` | boolean | Whether the system under test applied stem/source-separation or targeted vocal/instrument attenuation during the overlap — a modifier, never a primary class (contract §5) |
| `engine_reported_class` | enum or `null` | The system under test's own self-reported/logged class label, if any — **diagnostic only, never authoritative** |
| `observed_class` | enum: `FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, `SIMPLE_CROSSFADE`, `GAPLESS`, `CUT`, `NO_SPECIAL_TRANSITION`, `UNCLASSIFIED_ANOMALY` | Computed **only** from the fields above plus the pair's `is_continuous_work`/`sequencing_suppression_intended` annotations, via the deterministic decision procedure in the benchmark contract §5. This is the field used for every `transition_class_policy` match, `C11` evaluation, and `G4` scoring — `engine_reported_class` is never substituted for it. |
| `class_label_mismatch` | boolean | `true` when `engine_reported_class != observed_class`; logged as a diagnostic signal about the engine's own self-assessment quality, with no direct gate consequence on its own |

This table is the concrete answer to the benchmark contract's R11 requirement that "the benchmark, not the candidate engine, must own class assignment for gate purposes": `observed_class` is a pure function of measured signals plus static, pre-authored corpus annotations, and `engine_reported_class` never enters that function.
