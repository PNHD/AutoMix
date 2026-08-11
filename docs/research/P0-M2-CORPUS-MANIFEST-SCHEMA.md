# P0-M2-R1 — Corpus Manifest Schema

Status date: 2026-08-11 (repair pass — see `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §0 for the PM repair-request this revision addresses: R1 loudness terminology, R2 outcome-aware transition-class policy, R4 executable catastrophic-gate constants, R5 preference-outcome data model, R7 annotation-grounded C11)

Companion to `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`. Defines the machine-readable fixture/pair manifest that every benchmark run (baseline or candidate AutoMix engine) is scored against.

## 1. Format decision

**JSON Lines (`.jsonl`), one fixture or pair object per line**, plus a single top-level `manifest.json` index file.

Justification:

- **Line-addressable diffs**: `.jsonl` fixture/pair files diff cleanly in Git — adding, removing, or amending one fixture touches one line, keeping PR review of corpus changes tractable (relevant because this repository is public and every corpus change should be independently reviewable, per `AGENTS.md`'s evidence-first culture).
- **Streamable**: a benchmark runner can process the corpus without loading the entire manifest into memory, relevant once the corpus grows beyond the initial synthetic seed set.
- **No schema-migration lock-in**: unlike a relational/SQL corpus store, adding new optional fields (e.g., a new annotation source type, a new case tag) does not require a migration step — it requires only that consumers tolerate unknown fields, which is standard JSON practice.
- **YAML was considered and rejected** for the per-fixture/per-pair records specifically because YAML's whitespace sensitivity makes large hand-edited corpora more error-prone during manual annotation review; a single top-level `manifest.json` (small, human-edited far less often) is acceptable in plain JSON without that risk.

Three files per corpus tier:

```text
docs/research/corpus/manifest.json          # top-level index: schema version, tier definitions, split assignment, corpus minimums
docs/research/corpus/tier1_fixtures.jsonl   # one JSON object per Tier-1 audio fixture (track-level)
docs/research/corpus/tier1_pairs.jsonl      # one JSON object per Tier-1 transition pair (references two fixture_id)
docs/research/corpus/tier2_pairs.jsonl      # one JSON object per Tier-2 pair (metadata/provider-ID references only, no audio)
```

No audio bytes are ever committed alongside these files; `tier1_fixtures.jsonl` stores a `local_path` field that resolves to owner-local storage outside Git (see §7), plus a `checksum` for integrity verification of whatever file exists at that path.

These four files are **schema definitions and directory conventions specified by this document**; populating them with real fixtures/pairs is corpus-production work, not part of this specification deliverable (per Issue #4's "No audio files" / "This is a RESEARCH + SPECIFICATION task" constraints). Per Issue #4's repair-pass instruction (R8/R9), disposable benchmark-execution prototypes that populate and run against this schema are in scope for a future P0-M3 task; the shipping production engine is not.

## 2. Top-level `manifest.json`

```json
{
  "schema_version": "2.0.0",
  "generated_by": "P0-M2-R1 (repair pass)",
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
    "tier1_total_pairs_min": 60,
    "tier1_holdout_pairs_min": 18,
    "tier1_dev_pairs_min": 42,
    "per_lane_min": {
      "A_TIMING_STRUCTURE": 16,
      "B_CONTENT_COLLISION": 8,
      "C_ENERGY_LOUDNESS": 8,
      "D_HARMONIC_TEMPO": 12,
      "E_CONFIDENCE_FALLBACK": 16
    },
    "lane_a_clean_structure_subset_min": 10,
    "lane_e_should_not_full_blend_subset_min": 8,
    "g2_simpmusic_comparison_subset_min": 30,
    "g2_simpmusic_comparison_subset_holdout_min": 9,
    "note": "Derivation and gate-by-gate justification for every number above is in the benchmark contract's P0->P1 gate section (contract doc, 'Minimum corpus / gate sample-size plan'). This file's corpus_minimums block is the single source of truth a benchmark runner reads at execution time; the contract prose must not drift from these numbers without a corresponding schema_version bump."
  }
}
```

`split_assignment_policy` exists specifically to make the anti-overfitting rule in the benchmark contract ("Holdout pairs/categories may not be hand-tuned") auditable: any manifest diff that moves a pair between `dev` and `holdout` after benchmark results exist for it is a process violation and must be called out in the run's report, not silently applied.

`corpus_minimums` exists so the P0→P1 gate (contract §11) is mathematically executable rather than aspirational: every gate below references one of these named minimums directly, and a benchmark runner can validate "is the corpus large enough to even attempt this gate" before running any measurement.

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
| `genre_style_tags` | array of string | yes | e.g. `["pop"]`, `["hip-hop","dynamic-tempo"]` — drives the anti-overfitting coverage audit (benchmark contract §10) |
| `meter` | object `{numerator, denominator, confidence}`, nullable | yes (nullable) | e.g. `{"numerator":4,"denominator":4,"confidence":1.0}`; `null` for ambiguous-meter fixtures (an intentional Lane A case) |
| `bpm` | object `{value, confidence}`, nullable | yes (nullable) | Ground-truth or estimated tempo; `null` for variable-tempo fixtures (see `tempo_curve`) |
| `tempo_curve` | array of `{t_ms, bpm}`, nullable | no | Only present for variable-tempo fixtures; overrides `bpm` when present |
| `beat_timestamps_ms` | array of integer, nullable | conditional | Required whenever `annotation_sources.beat_timestamps` is `SYNTHETIC_EXACT` or `MANUAL` |
| `downbeat_indices` | array of integer, nullable | conditional | Indices into `beat_timestamps_ms` marking bar starts; required whenever `annotation_sources.downbeats` is `SYNTHETIC_EXACT`/`MANUAL` |
| `key` | object `{root, scale, camelot, confidence}`, nullable | yes (nullable) | e.g. `{"root":"A","scale":"minor","camelot":"8A","confidence":1.0}` |
| `phrase_boundaries_ms` | array of integer, nullable | no | |
| `section_boundaries` | array of `{t_start_ms, t_end_ms, label}`, nullable | no | `label` is free text but should use a small controlled vocabulary (`intro`, `verse`, `chorus`, `bridge`, `buildup`, `drop`, `outro`, `instrumental_break`, `other`) |
| `acceptable_entry_regions_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | Candidate regions where this track may serve as the **incoming** track's entry point |
| `acceptable_exit_regions_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | Candidate regions where this track may serve as the **outgoing** track's exit point |
| `vocal_intervals_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | |
| `bass_intervals_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | |
| `percussion_intervals_ms` | array of `{t_start_ms, t_end_ms}`, nullable | no | |
| `loudness` | object, nullable | no | `{"integrated_lufs": number, "momentary_curve": [{"t_ms":int,"lufs":number}, ...], "short_term_curve": [{"t_ms":int,"lufs":number}, ...]}`. **Terminology is binding** (per benchmark contract R1 repair): `integrated_lufs` is a single programme-level value (BS.1770-5 gated integrated measurement, whole-track or a defined start/stop range); `momentary_curve` samples use a 400 ms integration window stepped at a 100 ms hop (EBU Tech 3341 momentary-metering convention layered on the BS.1770-5 K-weighted measurement); `short_term_curve` samples use a 3 s integration window. Never call a 400 ms value "short-term" or a 3 s value "momentary" anywhere a benchmark report references this field. |
| `energy_curve` | array of `{t_ms, rms_db}`, nullable | no | |
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
| `transition_class_policy` | object — **replaces the prior `expected_transition_class_set` field (schema v1.0.0)** | yes | See §5 below. This is the outcome-aware acceptance structure that fixes the R2 circularity problem: a pair records what is *always* acceptable, what is acceptable *conditional on measured execution quality*, and what is *never* acceptable — instead of a single fixed set that penalized a smarter engine for correcting an adversarial input. |
| `manipulation_constraints` | object, nullable | no | `{"tempo_ratio_max_deviation": number, "max_pitch_shift_semitones": number, "low_band_coactivity_threshold_db": number, "low_band_coactivity_min_duration_ms": integer, "low_band_coactivity_ratio_ceiling": number}`. When omitted, a benchmark runner MUST use the global defaults defined in the benchmark contract's Condition Registry (`tempo_ratio_max_deviation=0.12`, `max_pitch_shift_semitones=3`, `low_band_coactivity_threshold_db=-12`, `low_band_coactivity_min_duration_ms=500`, `low_band_coactivity_ratio_ceiling=0.5`). A pair overriding any field must record why in `notes` and add the field to `annotation_sources` (e.g. `"manipulation_constraints.tempo_ratio_max_deviation":"MANUAL"`) so a widened/narrowed tolerance is never silently applied. This field exists specifically to make catastrophic codes `C5`/`C7`/`C8` reference defined, non-magic constants (benchmark contract R4 repair). |
| `known_trap_purpose` | string | yes | One-sentence statement of what failure mode this pair is designed to expose, e.g. `"Same BPM, 180-degree beat-phase offset — exposes systems with no downbeat model."` This field is what makes the corpus's adversarial intent auditable rather than incidental. |
| `annotation_sources` | object | yes | Same source-enum pattern as the fixture object, scoped to pair-level annotations (`transition_class_policy`, `manipulation_constraints` overrides, `acceptable_entry_regions`/`acceptable_exit_regions` overrides if pair-specific) |
| `evaluation_exclusions` | array of string, nullable | no | Named metrics/dimensions this pair is explicitly excluded from scoring on, with a reason — e.g. a fixture with `meter: null` is excluded from `downbeat_phase_error` scoring by design, not by omission. Every exclusion must reference a specific metric/dimension name from the benchmark contract §7/§8, not a blanket exclusion. |
| `split` | enum: `dev`, `holdout` (Tier-1) or `private_listening` (Tier-2) | yes | See §2 `split_assignment_policy` |
| `created_at` | ISO-8601 date | yes | |
| `notes` | string, nullable | no | |

## 5. `transition_class_policy` object

Replaces the v1.0.0 `expected_transition_class_set` field. Structure:

```json
{
  "accepted_unconditional": ["SHORT_EQ_BLEND", "SIMPLE_CROSSFADE"],
  "accepted_conditional": [
    {
      "class": "FULL_DJ_BLEND",
      "conditions": ["COND_BEAT_OK", "COND_DOWNBEAT_OK"],
      "all_required": true
    }
  ],
  "rejected": [
    {
      "class": "GAPLESS",
      "reason": "Tracks are two independent works with a deliberate beat-phase mismatch; a seamless no-processing handoff would leave the mismatch fully audible with no corrective mechanism applied at all."
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `accepted_unconditional` | Transition classes that are a correct *choice* for this pair regardless of how well the engine executes them. Choosing one of these never triggers a transition-class mismatch or `C11`. Execution quality is still scored by the normal objective/human metrics — this only governs whether the *class choice itself* was appropriate. |
| `accepted_conditional` | Transition classes that are correct **only if** the engine's actual measured execution satisfies the listed condition IDs (§ Condition Registry, defined in the benchmark contract §7). `all_required: true` means every listed condition must hold (AND); `all_required: false` means any one condition is sufficient (OR) — default `true` when omitted. If the class was chosen but the condition(s) were not met, the pair is scored as a transition-class **mismatch** (a `PROXY`-classified metric miss, per contract §7) — this is a quality failure, not automatically a `C11` catastrophic event, unless the same class also appears in `rejected` for this pair (it must not appear in both). |
| `rejected` | Transition classes that are **never** a correct choice for this pair, regardless of execution quality, each with a mandatory `reason`. Choosing a `rejected` class is the annotation-grounding condition for `C11_FORCED_WRONG_TRANSITION_STYLE` (benchmark contract §9) — `C11` additionally requires objective-metric or human corroboration before it is confirmed (see contract §9's `C11` definition); the `rejected` list alone identifies *which* pairs are eligible for a `C11` finding, not that one automatically occurred. |

**Closed-world default**: any transition class not listed in `accepted_unconditional` or `accepted_conditional` for a pair is treated as `rejected` by default (reason: `"not enumerated as acceptable for this pair"`) even if it is not explicitly written into the `rejected` array. Authors should still explicitly populate `rejected` with a real `reason` for any class whose wrongness is the specific point of the fixture (this is what makes `C11` findings meaningful rather than incidental).

## 6. Annotation source enum

Every annotated field, on both fixture and pair objects, must declare its source as exactly one of:

| Value | Meaning |
|---|---|
| `SYNTHETIC_EXACT` | Fixture was generated with this value as an exact input parameter (e.g., a script-generated click track with beats placed at exactly `60000/BPM` intervals) — zero measurement error by construction |
| `MANUAL` | A human annotator directly marked this value by inspection/listening |
| `DATASET` | Sourced from an existing published dataset's own annotations (e.g., EDM-CUE's expert cue points, per `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) — provenance of that dataset's own annotation method must be recorded in `notes` |
| `MODEL_ESTIMATE` | Produced by an automated analyzer/model (e.g., a beat-tracking model's output) — inherently uncertain, must carry a `confidence` value where the schema supports one |
| `PROVIDER_METADATA` | Sourced from a third-party catalog/provider metadata field (e.g., a Tidal-matched BPM/key) — carries the same category of risk P0-M1 §10 documents for SimpMusic; never treated as ground truth for `OBJECTIVE`-classified metrics in the benchmark contract |
| `UNKNOWN` | Source not established; the value must not be used as ground truth for any objective metric or catastrophic-failure detection until reclassified |

**Binding rule**: no benchmark report may present a `MODEL_ESTIMATE`, `PROVIDER_METADATA`, or `UNKNOWN`-sourced annotation as ground truth. Metrics computed against such annotations must be reported with their `PROXY` classification carried through (benchmark contract §7), and any catastrophic-failure code (benchmark contract §9) that depends on comparison against ground truth must only fire using `SYNTHETIC_EXACT` or `MANUAL` sourced values, except where the contract explicitly says otherwise (`C9`'s human-corroboration path, which is deliberately independent of annotation source — see contract §9).

## 7. Tier-2 privacy and non-redistribution

Tier-2 pair objects (`tier2_pairs.jsonl`) never contain audio, `local_path`, or `checksum` fields — only `outgoing_ref`/`incoming_ref` metadata objects (title/artist/provider IDs), plus:

- `observed_transition_timestamp_ms` (when the reference system executed its transition, as observed during a live listening session)
- `observed_settings` (free text — whatever transition-relevant settings were visible/knowable for the reference system, e.g. "Spotify Auto mode, default crossfade")
- `listening_scores` — an embedded human-rubric result object per benchmark contract §8, tied to this specific pair + reference system + session. Its `preference_outcome` field (dimension 16) must be one of `CANDIDATE_PREFERRED` / `BASELINE_PREFERRED` / `TIE` (contract §8.2) — never a bare 1–5 score, so Tier-2 sessions are structurally compatible with the same statistical-gate machinery as Tier-1, even though Tier-2 results are never counted toward a Tier-1 quantitative gate (contract §11 `SimpMusic baseline path`).

This keeps Tier-2 fully within `AGENTS.md` non-negotiable rules 3/4 — no protected audio, no DRM bypass, no redistribution risk — while still making commercial-benchmark sessions reproducible as *procedure* (same pair, same provider IDs, repeatable listening protocol) even though the underlying audio bytes are never in this repository.

## 8. Fixture/pair ID convention

`{PREFIX}-{LANE}-{SEQ}`, where:

- `PREFIX` is `SYN` (synthetic), `OWN` (owner-created), `PD` (public domain), or `CC0`.
- `LANE` is the single-letter primary lane code (`A`–`E`) for pairs, or a category letter for standalone fixtures reused across lanes (`X` = general-purpose fixture not tied to one lane).
- `SEQ` is a zero-padded sequence number, unique within `PREFIX-LANE`.

Example: `SYN-A-001` (first synthetic Lane-A fixture), `PAIR-SYN-A-001` (a pair whose ID additionally carries the `PAIR-` prefix to disambiguate from fixture IDs in tooling/search). This convention is a recommendation for corpus-production work, not a hard schema constraint — the schema only requires `fixture_id`/`pair_id` to be a stable, unique string.

## 9. Versioning and change discipline

- `manifest.json.schema_version` follows semver. A breaking field change (rename, type change, required→field removal) bumps the major version; additive optional fields bump the minor version. **This revision bumps `1.0.0` → `2.0.0`** because `expected_transition_class_set` (a required field in v1.0.0) was removed and replaced by the non-interchangeable `transition_class_policy` object, and the fixture `loudness` field's sub-keys were renamed (`short_term_curve`'s old 3 s-labeled-as-generic usage split into explicit `momentary_curve`/`short_term_curve`) — both are breaking changes for any v1.0.0 consumer.
- Every corpus-affecting Git commit must be reviewable as a normal diff (per §1's format justification) and must not silently move a pair between `dev`/`holdout` after that pair has benchmark results recorded against it (§2).
- This schema document itself, once corpus production begins, should be updated only via a task that records the schema version bump and the reason, consistent with `AGENTS.md`'s evidence-first, no-silent-change culture.
