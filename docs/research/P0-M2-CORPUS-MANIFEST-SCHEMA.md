# P0-M2-R1 — Corpus Manifest Schema

Status date: 2026-08-11

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
docs/research/corpus/manifest.json          # top-level index: schema version, tier definitions, split assignment
docs/research/corpus/tier1_fixtures.jsonl   # one JSON object per Tier-1 audio fixture (track-level)
docs/research/corpus/tier1_pairs.jsonl      # one JSON object per Tier-1 transition pair (references two fixture_id)
docs/research/corpus/tier2_pairs.jsonl      # one JSON object per Tier-2 pair (metadata/provider-ID references only, no audio)
```

No audio bytes are ever committed alongside these files; `tier1_fixtures.jsonl` stores a `local_path` field that resolves to owner-local storage outside Git (see §6), plus a `checksum` for integrity verification of whatever file exists at that path.

These four files are **schema definitions and directory conventions specified by this document**; populating them with real fixtures/pairs is corpus-production work, not part of this specification deliverable (per Issue #4's "No audio files" / "This is a RESEARCH + SPECIFICATION task" constraints).

## 2. Top-level `manifest.json`

```json
{
  "schema_version": "1.0.0",
  "generated_by": "P0-M2-R1",
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
  }
}
```

`split_assignment_policy` exists specifically to make the anti-overfitting rule in the benchmark contract (§10 "Holdout pairs/categories may not be hand-tuned") auditable: any manifest diff that moves a pair between `dev` and `holdout` after benchmark results exist for it is a process violation and must be called out in the run's report, not silently applied.

## 3. Fixture object (`tier1_fixtures.jsonl`, one per line)

Represents a single audio track used as one side of one or more transition pairs.

| Field | Type | Required | Description |
|---|---|---|---|
| `fixture_id` | string | yes | Stable unique ID, e.g. `SYN-A-001` (prefix indicates lane/category, see §7 ID convention) |
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
| `loudness` | object `{integrated_lufs, short_term_curve}`, nullable | no | `short_term_curve` is an array of `{t_ms, lufs}` sampled per BS.1770 short-term (3 s) window |
| `energy_curve` | array of `{t_ms, rms_db}`, nullable | no | |
| `annotation_sources` | object, yes | yes | One entry per annotated field above, each valued with the source enum (§5) — e.g. `{"beat_timestamps":"SYNTHETIC_EXACT","key":"MANUAL","vocal_intervals":"MODEL_ESTIMATE"}`. Any annotated field with no entry here is treated as `UNKNOWN` and **must not** be used as ground truth by a benchmark runner. |
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
| `case_tags` | array of string | yes | Free-form but drawn from the case vocabulary in the benchmark contract's per-lane tables (§4.1–§4.5), e.g. `["same_bpm_wrong_beat_phase"]`, `["vocal_to_vocal"]`, `["large_tempo_gap"]` |
| `expected_transition_class_set` | array from enum: `FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, `SIMPLE_CROSSFADE`, `GAPLESS`, `CUT`, `NO_SPECIAL_TRANSITION` | yes | The `acceptable_transition_classes` ground truth used by the transition-class-correctness metric (benchmark contract §7) |
| `known_trap_purpose` | string | yes | One-sentence statement of what failure mode this pair is designed to expose, e.g. `"Same BPM, 180-degree beat-phase offset — exposes systems with no downbeat model."` This field is what makes the corpus's adversarial intent auditable rather than incidental. |
| `annotation_sources` | object | yes | Same source-enum pattern as the fixture object, scoped to pair-level annotations (`expected_transition_class_set`, `acceptable_entry_regions`/`acceptable_exit_regions` overrides if pair-specific) |
| `evaluation_exclusions` | array of string, nullable | no | Named metrics/dimensions this pair is explicitly excluded from scoring on, with a reason — e.g. a fixture with `meter: null` is excluded from `downbeat_phase_error` scoring by design, not by omission. Every exclusion must reference a specific metric/dimension name from the benchmark contract §7/§8, not a blanket exclusion. |
| `split` | enum: `dev`, `holdout` (Tier-1) or `private_listening` (Tier-2) | yes | See §2 `split_assignment_policy` |
| `created_at` | ISO-8601 date | yes | |
| `notes` | string, nullable | no | |

## 5. Annotation source enum

Every annotated field, on both fixture and pair objects, must declare its source as exactly one of:

| Value | Meaning |
|---|---|
| `SYNTHETIC_EXACT` | Fixture was generated with this value as an exact input parameter (e.g., a script-generated click track with beats placed at exactly `60000/BPM` intervals) — zero measurement error by construction |
| `MANUAL` | A human annotator directly marked this value by inspection/listening |
| `DATASET` | Sourced from an existing published dataset's own annotations (e.g., EDM-CUE's expert cue points, per `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) — provenance of that dataset's own annotation method must be recorded in `notes` |
| `MODEL_ESTIMATE` | Produced by an automated analyzer/model (e.g., a beat-tracking model's output) — inherently uncertain, must carry a `confidence` value where the schema supports one |
| `PROVIDER_METADATA` | Sourced from a third-party catalog/provider metadata field (e.g., a Tidal-matched BPM/key) — carries the same category of risk P0-M1 §10 documents for SimpMusic; never treated as ground truth for `OBJECTIVE`-classified metrics in the benchmark contract |
| `UNKNOWN` | Source not established; the value must not be used as ground truth for any objective metric or catastrophic-failure detection until reclassified |

**Binding rule**: no benchmark report may present a `MODEL_ESTIMATE`, `PROVIDER_METADATA`, or `UNKNOWN`-sourced annotation as ground truth. Metrics computed against such annotations must be reported with their `PROXY` classification carried through (benchmark contract §7), and any catastrophic-failure code (benchmark contract §9) that depends on comparison against ground truth must only fire using `SYNTHETIC_EXACT` or `MANUAL` sourced values, except where the contract explicitly says otherwise (none currently do).

## 6. Tier-2 privacy and non-redistribution

Tier-2 pair objects (`tier2_pairs.jsonl`) never contain audio, `local_path`, or `checksum` fields — only `outgoing_ref`/`incoming_ref` metadata objects (title/artist/provider IDs), plus:

- `observed_transition_timestamp_ms` (when the reference system executed its transition, as observed during a live listening session)
- `observed_settings` (free text — whatever transition-relevant settings were visible/knowable for the reference system, e.g. "Spotify Auto mode, default crossfade")
- `listening_scores` (an embedded human-rubric result object per benchmark contract §8, tied to this specific pair + reference system + session)

This keeps Tier-2 fully within `AGENTS.md` non-negotiable rules 3/4 — no protected audio, no DRM bypass, no redistribution risk — while still making commercial-benchmark sessions reproducible as *procedure* (same pair, same provider IDs, repeatable listening protocol) even though the underlying audio bytes are never in this repository.

## 7. Fixture/pair ID convention

`{PREFIX}-{LANE}-{SEQ}`, where:

- `PREFIX` is `SYN` (synthetic), `OWN` (owner-created), `PD` (public domain), or `CC0`.
- `LANE` is the single-letter primary lane code (`A`–`E`) for pairs, or a category letter for standalone fixtures reused across lanes (`X` = general-purpose fixture not tied to one lane).
- `SEQ` is a zero-padded sequence number, unique within `PREFIX-LANE`.

Example: `SYN-A-001` (first synthetic Lane-A fixture), `PAIR-SYN-A-001` (a pair whose ID additionally carries the `PAIR-` prefix to disambiguate from fixture IDs in tooling/search). This convention is a recommendation for corpus-production work, not a hard schema constraint — the schema only requires `fixture_id`/`pair_id` to be a stable, unique string.

## 8. Versioning and change discipline

- `manifest.json.schema_version` follows semver. A breaking field change (rename, type change, required→field removal) bumps the major version; additive optional fields bump the minor version.
- Every corpus-affecting Git commit must be reviewable as a normal diff (per §1's format justification) and must not silently move a pair between `dev`/`holdout` after that pair has benchmark results recorded against it (§2).
- This schema document itself, once corpus production begins, should be updated only via a task that records the schema version bump and the reason, consistent with `AGENTS.md`'s evidence-first, no-silent-change culture.
