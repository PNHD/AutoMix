# P0-M2-R1 — Benchmark Pair Catalog (Illustrative)

Status date: 2026-08-11 (PM REVIEW #5 — corrected a stale pair-count claim: this catalog actually contains **39** pairs, not 31. Every prior-pass reference to "31" was a miscount introduced in the original P0-M2-R1 pass and never independently re-verified in subsequent passes; it has now been counted programmatically — see "Programmatic pair count" below — and every downstream claim corrected. R18's native-tempo `FULL_DJ_BLEND` classification fix was re-verified against all 39 pairs; no per-pair policy changes required. Carries forward PM REVIEW #3's R13/R14 taxonomy propagation and R15 schema-fidelity fixes for `A-010`/`E-007`.)

## Programmatic pair count (R20)

Counted directly from this file's table rows via:

```bash
grep -oE '^\| `PAIR-SYN-[A-E]-[0-9]+` \|' docs/research/P0-M2-BENCHMARK-PAIR-CATALOG.md \
  | grep -oE 'PAIR-SYN-[A-E]-[0-9]+' | sort | uniq -c
```

| Lane | Count | IDs |
|---|---|---|
| A | 10 | `A-001`…`A-010` |
| B | 7 | `B-001`…`B-007` |
| C | 6 | `C-001`…`C-006` |
| D | 8 | `D-001`…`D-008` |
| E | 8 | `E-001`…`E-008` |
| **TOTAL** | **39** | |

No duplicate `pair_id` rows exist (independently checked via `sort | uniq -d` on the same extracted ID list, which returns empty). This matches the PM's independent count exactly.

Optional companion to `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` and `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`. Specifies representative pair definitions in the manifest schema's shape. No audio is included or implied to exist; corpus production is future work.

All example fixtures use `provenance: SYNTHETIC` for `SYNTHETIC_EXACT` ground truth (manifest schema §10, annotation source enum).

## What changed this pass (R18, read this first)

R18 revised the benchmark contract's classification decision procedure (contract §5.2/§5.3) so that a native-tempo `FULL_DJ_BLEND` no longer requires EQ automation, and now additionally requires measured cue/phrase structural evidence (not beat lock alone) — see the contract's §5.4 worked examples 1–5. This is a **runtime classification rule change only**: it changes how a benchmark runner computes `observed_class` from a transition render record. It does **not** change the shape or content of any pair's `transition_class_policy` in this catalog, because that policy is expressed in terms of the class labels themselves (`FULL_DJ_BLEND`, `SHORT_EQ_BLEND`, etc.) and Condition-Registry IDs, both of which are unaffected by how `observed_class` gets computed. All 39 pairs were re-audited against the revised classification procedure (see "Full policy-schema roundtrip audit" below) and required **zero** policy changes.

## What changed in the prior pass (R13–R16, retained for context)

- **R13/R14 taxonomy fixes propagated:** the classification decision procedure changed (contract §5.2), which makes `GAPLESS` unreachable for any pair with `is_continuous_work=false`, since `GAPLESS` now strictly requires both zero overlap, zero gap, *and* authored continuity. Two pairs' `accepted_unconditional` lists referenced `GAPLESS`/`CUT` in ways that no longer match the corrected procedure and are fixed below: `PAIR-SYN-A-007` (`GAPLESS` → `NO_SPECIAL_TRANSITION`, since it is not a continuous-work pair) and `PAIR-SYN-E-005` (`CUT` → `NO_SPECIAL_TRANSITION`, since its "cold stop" *is* each fixture's own natural/authored boundary, which the corrected procedure classifies `NO_SPECIAL_TRANSITION` when boundaries are natural, not `CUT`, which requires a *non-natural* boundary).
- **R15 schema-fidelity fixes:** `PAIR-SYN-A-010` now uses the array-valued `human_confirmations` + `human_all_required` fields (manifest schema §6) instead of a single-object placeholder. `PAIR-SYN-E-007` now uses the new `rejected_conditional` mechanism, keyed purely on the outcome condition `COND_VOCAL_OK` — the prior `requires_modifier: "stem_separation_applied"` gate is removed; any technique that achieves the required rendered outcome now qualifies.
- **R16:** no catalog changes required (R16 is a corpus-minimums/gate field, not a per-pair policy field), but the coverage summary below is updated to reference `lane_e_holdout_min`.

## Reading the `Transition class policy` column

- **`U:`** — `accepted_unconditional`.
- **`C:`** — `accepted_conditional`, with Condition-Registry IDs (contract §7) and, where applicable, `human_confirmations`/`human_all_required` (contract §9.2).
- **`RC:`** — **new (R15)** `rejected_conditional`: rejected *unless* the stated condition(s) hold, with a mandatory `reason`. Outcome-grounded — never keyed on a specific implementation technology.
- **`R:`** — `rejected`, unconditionally, with a mandatory fixture-grounded `reason`.

Per manifest schema §6.1's structural constraint, a class appears in **at most one** of these four per pair.

## Lane A — Timing / structure

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | Transition class policy |
|---|---|---|---|---|
| `PAIR-SYN-A-001` | Same BPM, wrong beat phase | Two 128 BPM click-grid tracks, incoming's beat grid offset by half a beat (180°) | Exposes BPM-only compatibility assumptions | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_BEAT_OK & COND_DOWNBEAT_OK` · `R: GAPLESS (two independent tracks with a deliberate mismatch; a no-processing handoff leaves it fully audible)` |
| `PAIR-SYN-A-002` | Beat-aligned, wrong downbeat/bar phase | 120 BPM both, beats aligned, incoming's bar-1 lands on outgoing's beat-3 | Exposes beat-aware-but-not-downbeat-aware systems | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_DOWNBEAT_OK` · `R: GAPLESS (same reason)` |
| `PAIR-SYN-A-003` | Same BPM/key, incompatible phrase timing | 100 BPM both, 6-bar vs 8-bar phrases | Exposes beat-count-snapping instead of phrase-position awareness | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_PHRASE_OK & COND_CUE_OK` · `R: GAPLESS (same reason)` |
| `PAIR-SYN-A-004` | Clean intro/outro (positive control) | 8-bar low-density intro/outro, no vocal | Confirms use of good structure when available | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE` (no rejection) |
| `PAIR-SYN-A-005` | Chorus→verse boundary mismatch | Exit mid-chorus, entry mid-verse | Exposes lack of section-awareness | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_SECTION_OK & COND_CUE_OK` |
| `PAIR-SYN-A-006` | Pickup/anacrusis start | Incoming's first note precedes its beat 1 by a 16th note | Exposes "always start at file position 0" logic | `U: SIMPLE_CROSSFADE, SHORT_EQ_BLEND` · `C: FULL_DJ_BLEND if COND_BEAT_OK & COND_CUE_OK` |
| `PAIR-SYN-A-007` | Long silence / non-musical tail | Outgoing's musical content ends at a specific, fixture-annotated point followed by 6 s near-silence; `acceptable_exit_regions_ms` scoped to the pre-silence musical window only. `is_continuous_work=false` | A smart cue selector can transition using the real musical content, not the silence | `U: CUT, NO_SPECIAL_TRANSITION` (**changed this pass** — was `CUT, GAPLESS`; `GAPLESS` is unreachable here since `is_continuous_work=false`, per the corrected §5.2 procedure) · `C: SHORT_EQ_BLEND if COND_CUE_OK`; `FULL_DJ_BLEND if COND_CUE_OK & COND_BEAT_OK & COND_DOWNBEAT_OK` |
| `PAIR-SYN-A-008` | No clean intro/outro anywhere | Both fixtures' `acceptable_entry_regions_ms`/`acceptable_exit_regions_ms` authored as empty arrays | Forces recognition of "no good option" | `U: SIMPLE_CROSSFADE, CUT` · `C: SHORT_EQ_BLEND if COND_CUE_OK` (unreachable given the empty region arrays) · `R: FULL_DJ_BLEND (acceptable_entry_regions_ms and acceptable_exit_regions_ms are both authored as empty arrays — a fact fully known at corpus-design time, not a benchmark measurement gap)` |
| `PAIR-SYN-A-009` | Variable tempo | Outgoing ramps 90→110 BPM over final 30 s | Defeats scalar-BPM models | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_TEMPO_ENVELOPE_OK & COND_BEAT_OK` |
| `PAIR-SYN-A-010` | Non-4/4 meter | Outgoing 7/8, incoming 4/4 | Defeats a hardcoded `beats[::4]` bar-phase assumption | `U: SIMPLE_CROSSFADE, CUT` · `C: SHORT_EQ_BLEND if COND_BEAT_OK`; `FULL_DJ_BLEND if COND_CUE_OK, human_confirmations: [{"dimension":"beat_coherence","min_score":3},{"dimension":"downbeat_bar_coherence","min_score":3}], human_all_required: true` (**R15**: now a real array of two confirmations, both required — see §Serialization examples below for the literal JSON) |

## Lane B — Content collision

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | Transition class policy |
|---|---|---|---|---|
| `PAIR-SYN-B-001` | Vocal → vocal | Continuous vocal-band tone, outgoing final 15 s / incoming from 0 s | Exposes generic-EQ-but-no-detection systems; `COND_VOCAL_OK` measured on rendered/post-mix audio, so any effective mitigation technique qualifies | `U: SIMPLE_CROSSFADE` · `C: SHORT_EQ_BLEND if COND_VOCAL_OK`; `FULL_DJ_BLEND if COND_VOCAL_OK` |
| `PAIR-SYN-B-002` | Sustained vocal outro → vocal intro | Held single-note synthetic "vocal" tone | Tighter version of B-001 | `U: SIMPLE_CROSSFADE` · `C: SHORT_EQ_BLEND if COND_VOCAL_OK`; `FULL_DJ_BLEND if COND_VOCAL_OK` |
| `PAIR-SYN-B-003` | Dense bass → dense bass | Continuous low-band (20–150 Hz) energy | Exposes lack of bass-activity detection | `U: SIMPLE_CROSSFADE` · `C: SHORT_EQ_BLEND, FULL_DJ_BLEND if COND_BASS_OK` |
| `PAIR-SYN-B-004` | Percussion-heavy overlap | Dense transient hits, no rhythmic alignment | Tests whether beat-phase mismatch compounds with content collision | `U: SIMPLE_CROSSFADE, CUT` · `C: SHORT_EQ_BLEND if COND_BEAT_OK` |
| `PAIR-SYN-B-005` | Instrumental → vocal | No vocal band outgoing; incoming's vocal starts at 0 s | Easier positive-control-adjacent case | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND` (no rejection) |
| `PAIR-SYN-B-006` | Sparse → dense | Low-density exit, full-density entry | Tests density-aware entry-point choice | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_LOUDNESS_OK` |
| `PAIR-SYN-B-007` | Dense → sparse | Reverse of B-006 | Same, reverse direction | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_LOUDNESS_OK` |

## Lane C — Energy / loudness

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | Transition class policy |
|---|---|---|---|---|
| `PAIR-SYN-C-001` | High → high | Constant high RMS energy | Positive control | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE` (no rejection) |
| `PAIR-SYN-C-002` | Low → high | Low energy exit, high energy entry | Tests energy-jump handling | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_LOUDNESS_OK` |
| `PAIR-SYN-C-003` | High → low | Reverse of C-002 | Same | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_LOUDNESS_OK` |
| `PAIR-SYN-C-004` | Gradual buildup/drop | Linear energy ramp then sudden drop | Tests energy-trajectory matching | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND` (no rejection) |
| `PAIR-SYN-C-005` | Large mastering-loudness gap | −14 vs −8 LUFS integrated | Exposes static-per-track-gain-only systems | `U: SHORT_EQ_BLEND` · `C: FULL_DJ_BLEND if COND_LOUDNESS_OK` |
| `PAIR-SYN-C-006` | Locally quiet transition region | High integrated loudness, quiet 10 s pocket at exit | Defeats whole-track-loudness-only systems | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_LOUDNESS_OK` |

## Lane D — Harmonic / tempo

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | Transition class policy |
|---|---|---|---|---|
| `PAIR-SYN-D-001` | Compatible key + close tempo | Camelot-adjacent, BPM gap ≤2% | Positive control | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE` (no rejection) |
| `PAIR-SYN-D-002` | Compatible key + large tempo gap | Camelot-adjacent, BPM gap ~40% | Tests tempo gap as the binding constraint | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE, CUT` · `C: FULL_DJ_BLEND if COND_TEMPO_ENVELOPE_OK` |
| `PAIR-SYN-D-003` | Incompatible key + close tempo | Camelot distance ≥4, BPM gap ≤2% | Tests key incompatibility as the binding constraint | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_PITCH_ENVELOPE_OK` |
| `PAIR-SYN-D-004` | Half/double-time | 84 vs 168 BPM | Tests half/double-time normalization | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND` (no rejection) |
| `PAIR-SYN-D-005` | Pitch shifting helps | Camelot distance 2, reachable via 1-semitone shift | Tests bounded, justified pitch correction | `U: SHORT_EQ_BLEND` · `C: FULL_DJ_BLEND if COND_PITCH_ENVELOPE_OK` |
| `PAIR-SYN-D-006` | Pitch shifting should be avoided | Camelot distance 2, but any in-bounds shift still sounds bad on this fixture's scripted content | Tests restraint despite objective feasibility | `U: SHORT_EQ_BLEND, SIMPLE_CROSSFADE` · `C: FULL_DJ_BLEND if COND_PITCH_ENVELOPE_OK` (bad-despite-in-bounds outcomes are caught by `C8`'s human clause, not the class-choice policy) |
| `PAIR-SYN-D-007` | Stretch within reasonable range | BPM gap ~8% | Positive control | `U: FULL_DJ_BLEND, SHORT_EQ_BLEND` (no rejection) |
| `PAIR-SYN-D-008` | Stretch outside reasonable range | BPM gap ~60%, no half/double-time relationship | Tests whether the system declines rather than forces a broken stretch | `U: SIMPLE_CROSSFADE, CUT, NO_SPECIAL_TRANSITION` · `C: SHORT_EQ_BLEND if COND_TEMPO_ENVELOPE_OK`; `FULL_DJ_BLEND if COND_TEMPO_ENVELOPE_OK` |

## Lane E — Confidence / fallback

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | Transition class policy |
|---|---|---|---|---|
| `PAIR-SYN-E-001` | Should be `FULL_DJ_BLEND` | Compatible key, close tempo, clean intro/outro, no collision | Positive control | `U: FULL_DJ_BLEND` (conservative fallbacks default-fall to the weak "not enumerated" reason, too weak to ground `C11`; tests preference optimality) |
| `PAIR-SYN-E-002` | Should be `SHORT_EQ_BLEND` | Moderate compatibility, some ambiguity, no severe collisions | Tests mid-confidence fallback | `U: SHORT_EQ_BLEND` · `C: FULL_DJ_BLEND if COND_BEAT_OK & COND_DOWNBEAT_OK & COND_PHRASE_OK` |
| `PAIR-SYN-E-003` | Should be `SIMPLE_CROSSFADE` | Incompatible key, no exploitable structure, no catastrophic collision | Tests low-confidence fallback short of a hard cut | `U: SIMPLE_CROSSFADE` · `C: SHORT_EQ_BLEND if COND_PITCH_ENVELOPE_OK` (no path to `FULL_DJ_BLEND` — no structure ground truth exists to condition on) |
| `PAIR-SYN-E-004` | Should be `GAPLESS` | Two fixtures scripted as one continuous piece; `is_continuous_work=true` | Tests recognition that no processing should be applied at all | `U: GAPLESS` · `R: FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE, CUT (pair is annotated is_continuous_work=true — an authored, corpus-design-time fact; any processing at all is an audible defect on a genuinely continuous work)` |
| `PAIR-SYN-E-005` | Should be `NO_SPECIAL_TRANSITION` | Outgoing ends cold, incoming starts cold; both fixtures' own `authored_exit_boundary_ms`/`authored_entry_boundary_ms` **are** the cold-stop point (i.e. the natural boundary itself is silent) and `energy_curve` confirms near-zero energy there. `is_continuous_work=false` | Tests recognition that forcing a crossfade over non-existent fade material is wrong, **and** that a natural-but-cold boundary is not the same as a deliberately truncated `CUT` | `U: NO_SPECIAL_TRANSITION` (**changed this pass** — was `CUT`; per the corrected §5.2 procedure, playing both fixtures to their own natural/authored boundary with zero overlap and zero gap classifies `NO_SPECIAL_TRANSITION`, not `CUT`, which specifically requires a *non-natural* boundary. `CUT` is not a meaningful alternative rendering here — truncating *before* the natural cold-stop point would discard real content for no benefit, since the natural point is already silent) · `R: FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE (both fixtures' own energy_curve shows a genuine cold, near-silent boundary at the natural edit point by construction; any fade class would only fade silence into silence)` |
| `PAIR-SYN-E-006` | Should be `NO_SPECIAL_TRANSITION` | Sequential album tracks per `docs/research/P0-M0-MARKET-PRIOR-ART-LANDSCAPE.md` §13; `sequencing_suppression_intended=true` | Directly tests the exact case P0-M1 §8 level 8 confirms SimpMusic cannot represent | `U: NO_SPECIAL_TRANSITION` · `R: FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE, CUT, GAPLESS (pair is annotated sequencing_suppression_intended=true — a product/authoring-intent fact known at corpus-design time)` |
| `PAIR-SYN-E-007` | Adversarial: strong-looking signals, should NOT full-blend unless the rendered outcome is clean | Compatible key, close tempo; a severe vocal collision is scripted to coincide with the pair's only structurally viable cue region under raw/unmitigated stems | The critical `C11_FORCED_WRONG_TRANSITION_STYLE` probe — **now outcome-grounded (R15), not technology-grounded** | `U: SIMPLE_CROSSFADE` · `C: SHORT_EQ_BLEND if COND_VOCAL_OK` · `RC: FULL_DJ_BLEND unless COND_VOCAL_OK (reason: "the scripted vocal collision coincides with the pair's only structurally viable cue region under the raw source audio; FULL_DJ_BLEND is acceptable if — and only if — the actual rendered output demonstrates COND_VOCAL_OK, by whatever technique achieves it: stem separation, dynamic vocal ducking, spectral separation, alternate cue-point handling, or any other valid method. stem_separation_applied is diagnostic metadata only and plays no role in this determination.")` (**changed this pass** — replaces the prior `rejected` + `requires_modifier`-gated `accepted_conditional` pair, which the schema could not represent without contradiction and which incorrectly named one specific mitigation technology; see §Serialization examples below) |
| `PAIR-SYN-E-008` | Adversarial: weak-looking signals, should still blend well | Incompatible key on paper, but musically inaudible given sparse/ambiguous harmonic content | Tests that conservatism is not *required* merely because metadata looks incompatible | `U: SHORT_EQ_BLEND` · `C: FULL_DJ_BLEND if COND_PITCH_ENVELOPE_OK` (no rejection — direct positive counterpart to E-007) |

## Serialization examples (R15 REQUIRED VALIDATION items 3/4)

### `PAIR-SYN-A-010` — proving both human confirmations are machine-readable

```json
{
  "pair_id": "PAIR-SYN-A-010",
  "benchmark_lane": "A_TIMING_STRUCTURE",
  "transition_class_policy": {
    "accepted_unconditional": ["SIMPLE_CROSSFADE", "CUT"],
    "accepted_conditional": [
      {
        "class": "SHORT_EQ_BLEND",
        "conditions": ["COND_BEAT_OK"],
        "all_required": true,
        "human_confirmations": [],
        "human_all_required": true
      },
      {
        "class": "FULL_DJ_BLEND",
        "conditions": ["COND_CUE_OK"],
        "all_required": true,
        "human_confirmations": [
          { "dimension": "beat_coherence", "min_score": 3 },
          { "dimension": "downbeat_bar_coherence", "min_score": 3 }
        ],
        "human_all_required": true
      }
    ],
    "rejected_conditional": [],
    "rejected": []
  }
}
```

`FULL_DJ_BLEND` is correct for this pair **iff** `COND_CUE_OK` is objectively satisfied **and** both listed rubric dimensions independently score ≥3 (`human_all_required: true` = AND). No prose-only boolean logic remains — the two-confirmation requirement is a literal JSON array, evaluated by the same scoring rule (contract §8) as every other pair.

### `PAIR-SYN-E-007` — proving no contradiction between conditional acceptance and conditional rejection

```json
{
  "pair_id": "PAIR-SYN-E-007",
  "benchmark_lane": "E_CONFIDENCE_FALLBACK",
  "transition_class_policy": {
    "accepted_unconditional": ["SIMPLE_CROSSFADE"],
    "accepted_conditional": [
      {
        "class": "SHORT_EQ_BLEND",
        "conditions": ["COND_VOCAL_OK"],
        "all_required": true,
        "human_confirmations": [],
        "human_all_required": true
      }
    ],
    "rejected_conditional": [
      {
        "class": "FULL_DJ_BLEND",
        "unless_conditions": ["COND_VOCAL_OK"],
        "all_required": true,
        "reason": "The scripted vocal collision coincides with the pair's only structurally viable cue region under the raw source audio. FULL_DJ_BLEND is acceptable only if the rendered output demonstrates COND_VOCAL_OK, achieved by any valid technique (stem separation, vocal ducking, spectral separation, alternate cue handling, or another method). stem_separation_applied is diagnostic metadata only."
      }
    ],
    "rejected": []
  }
}
```

`FULL_DJ_BLEND` appears in **exactly one** list (`rejected_conditional`), never simultaneously in `accepted_conditional` and `rejected` — resolving the prior contradiction structurally, not just by careful wording. Per the contract §8 scoring rule: if a render's `observed_class = FULL_DJ_BLEND` and the measured `COND_VOCAL_OK` is satisfied on that specific rendered output, the transition scores **correct** regardless of which technique (if any) was used to achieve it; if `COND_VOCAL_OK` is not satisfied, it scores a mismatch **and** is `C11`-eligible, grounded by the `reason` field — which itself never names a required technology, satisfying REQUIRED VALIDATION item 5.

## Full policy-schema roundtrip audit (R20 — every actual pair row, all 39)

Every pair listed above (39 total, per the programmatic count) was individually checked against the manifest schema §6 `transition_class_policy` object and §6.1 validation constraints for all five criteria below:

1. Every referenced Condition-Registry ID exists among the ten defined in contract §7 (`COND_BEAT_OK`, `COND_DOWNBEAT_OK`, `COND_CUE_OK`, `COND_PHRASE_OK`, `COND_SECTION_OK`, `COND_TEMPO_ENVELOPE_OK`, `COND_PITCH_ENVELOPE_OK`, `COND_VOCAL_OK`, `COND_BASS_OK`, `COND_LOUDNESS_OK`).
2. Every transition class named in the pair's policy cell appears in **at most one** of `accepted_unconditional` / `accepted_conditional` / `rejected_conditional` / `rejected` (schema §6.1 rule 1).
3. Every "&" combinator between condition IDs maps to `all_required: true` (the schema default); no pair in this catalog uses an OR combination, so `all_required: false` is present in the schema but unexercised by this illustrative catalog — noted, not a defect.
4. Where `human_confirmations` logic is used (`A-010` only), it is structurally represented as the array + `human_all_required` fields, not left as prose-only boolean logic.
5. No table cell contains an unmodeled prose operator ("without", "unless", "except when") controlling scoring without a structural equivalent — every occurrence of such words in a `reason` field is descriptive commentary about an already-structural policy entry (e.g. `E-007`'s `RC:` notation is backed by the literal `rejected_conditional.unless_conditions` field), never additional logic that exists only in prose. Every `rejected`/`rejected_conditional` `reason` was additionally checked against the grounding rule (schema §6, `rejected`/`rejected_conditional` field semantics): cites a fixture-authored fact (`is_continuous_work`, `sequencing_suppression_intended`, an empty region-annotation array, `energy_curve` evidence) or a technology-agnostic outcome condition — never a required named technology.

**Result by lane:**

| Lane | Pairs checked | Passed | Notes |
|---|---|---|---|
| A | 10 | **10/10** | `A-001`–`A-003` reject `GAPLESS` (fixture-grounded: not continuous-work pairs); `A-007` uses `CUT`/`NO_SPECIAL_TRANSITION` (post-R13/R14 fix); `A-008` rejects `FULL_DJ_BLEND` (empty region arrays); `A-010` uses the `human_confirmations` array (post-R15 fix) |
| B | 7 | **7/7** | `B-001`–`B-003`, `B-006`–`B-007` use `accepted_conditional` only, no rejections; `B-004`/`B-005` likewise |
| C | 6 | **6/6** | All six use `accepted_unconditional`/`accepted_conditional` only, no rejections anywhere in Lane C |
| D | 8 | **8/8** | `D-002`, `D-008` leave `FULL_DJ_BLEND` conditional (not rejected) per the R12 anti-circularity fix; `D-006` leaves the bad-despite-in-bounds case to `C8`'s catastrophic-layer human clause rather than the class-choice policy |
| E | 8 | **8/8** | `E-004`–`E-006` are the fixture/pair-annotation-grounded categorical rejections (`is_continuous_work`, `energy_curve`, `sequencing_suppression_intended`); `E-007` uses `rejected_conditional` (post-R15 fix), confirmed via the literal JSON serialization above to place `FULL_DJ_BLEND` in exactly one list |
| **TOTAL** | **39** | **39/39** | |

**Re-run after the R18 classification-procedure change (PM REVIEW #4):** R18 only alters how `observed_class` is computed at runtime (contract §5.2/§5.3); it does not alter the `transition_class_policy` schema shape or the meaning of any Condition-Registry ID. Every one of the 39 pairs' policies was re-checked and remains representable and correct without modification, since every catalog policy references classes only by name and by Condition-Registry IDs, never by the render-record automation flags (`has_eq_automation` etc.) that the classification procedure itself consumes. **39/39 pairs pass, zero policy changes required by R18.**

The two literal JSON examples above (`A-010`, `E-007`) are the two pairs the PM specifically flagged in PM REVIEW #3 as previously non-representable; both remain proven representable by direct serialization.

## Coverage summary against benchmark contract §4/§5/§11/§12

- Every case type named in the benchmark contract's Lane A–E tables has at least one concrete `pair_id`, scored via `observed_class` per the corrected taxonomy (contract §5.2), never via engine self-report.
- Two pairs required a taxonomy-consistency fix this pass (`A-007`, `E-005`, see "What changed this pass" above); two pairs required a schema-representability fix (`A-010`, `E-007`).
- `PAIR-SYN-E-007` remains the highest-priority pair for validating `C11` for a naive (non-mitigating) engine, now provably outcome-grounded rather than technology-grounded. `PAIR-SYN-E-006` remains the highest-priority pair for the "SimpMusic cannot represent suppressed transitions at all" gap.
- The Lane-E pairs collectively (23 minimum required at full corpus scale, per `manifest.json.corpus_minimums`) are what `G4`'s two holdout checks — the overall `lane_e_holdout_min` (7 pairs, ≥6 must match) and the adversarial subset's holdout (3 pairs, 0 confirmed `C11`) — are computed against once the corpus is built out beyond this illustrative 8-pair Lane-E sample.
- All entries remain `provenance: SYNTHETIC`; genre/style diversity, non-synthetic sourcing, and wiring into `manifest.json`/`tier1_fixtures.jsonl`/`tier1_pairs.jsonl` remain future corpus-production work, explicitly allowed under disposable P0-M3 benchmark-execution prototyping while the shipping production engine remains gated behind the P1 gate.
