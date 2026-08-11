# P0-M2-R1 — Benchmark Pair Catalog (Illustrative)

Status date: 2026-08-11

Optional companion to `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` and `docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md`. This document specifies **representative pair definitions** in the manifest schema's shape, demonstrating that every required adversarial case type (benchmark contract §4) is concretely constructible. No audio is included or implied to exist yet — every entry below is a specification for a fixture/pair that corpus-production work must still generate, source, and annotate. Fixture generation itself is out of scope for P0-M2-R1 (research/specification only).

All example fixtures use `provenance: SYNTHETIC` because synthetic material is the only way to guarantee `SYNTHETIC_EXACT` ground truth (manifest schema §5), which is required to make these specific adversarial claims falsifiable rather than merely plausible. Real-world (public-domain/CC0/owner-created) material should supplement this catalog once corpus production begins, per the benchmark contract's anti-overfitting requirement (§10) — synthetic-only coverage would itself be a form of overfitting to clean, idealized structure.

## Lane A — Timing / structure

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | `expected_transition_class_set` |
|---|---|---|---|---|
| `PAIR-SYN-A-001` | Same BPM, wrong beat phase | Two 128 BPM click-grid synthetic tracks, incoming track's beat grid offset by exactly half a beat (180°) relative to outgoing | Exposes any system that treats matched BPM as sufficient for a beat-synced blend | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` (not `FULL_DJ_BLEND` — beat phase must be corrected or the blend avoided) |
| `PAIR-SYN-A-002` | Beat-aligned, wrong downbeat/bar phase | Both tracks 120 BPM, beats aligned, but incoming track's bar-1 lands on outgoing track's beat-3 | Exposes systems with beat-awareness but no downbeat/bar model — SimpMusic's exact gap per P0-M1 §8 level 3 | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-A-003` | Same BPM/key, incompatible phrase timing | Both 100 BPM, compatible Camelot key, but outgoing track's phrase boundaries fall at odd bar counts (e.g. 6-bar phrases) vs. incoming's standard 8-bar phrases | Exposes systems that snap to a beat *count* instead of a phrase *position* (P0-M1 §10's specific critique of `resolveAutoCrossfadeDurationMs`) | `{SHORT_EQ_BLEND}` |
| `PAIR-SYN-A-004` | Clean intro/outro opportunity (positive control) | Both tracks have an 8-bar low-density intro/outro with no vocal | Confirms a system *uses* good structure when available, not just avoids bad structure | `{FULL_DJ_BLEND}` |
| `PAIR-SYN-A-005` | Chorus→verse boundary mismatch | Outgoing track's designated exit point is mid-chorus; incoming track's entry is mid-verse | Exposes lack of section-awareness | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-A-006` | Pickup/anacrusis start | Incoming track's first audible note precedes its own beat 1 by a 16th note | Exposes "always start incoming track at file position 0 == beat 1" logic (P0-M1 §5/§8 level 7's exact description of SimpMusic) | `{SIMPLE_CROSSFADE}` |
| `PAIR-SYN-A-007` | Long silence / non-musical tail | Outgoing track ends with 6 s of near-silence after its last musical content | Exposes beat-alignment logic applied to a region with no real beat content | `{CUT, GAPLESS}` |
| `PAIR-SYN-A-008` | No clean intro/outro | Both tracks start/end mid-phrase with no low-density boundary region | Forces a deliberate non-boundary choice or fallback; tests whether the system recognizes "no good option" rather than forcing a boundary-seeking algorithm onto a distribution with none | `{SIMPLE_CROSSFADE, CUT}` |
| `PAIR-SYN-A-009` | Variable tempo | Outgoing track ramps 90→110 BPM linearly over its final 30 s | Defeats a single-scalar-BPM model entirely; requires `tempo_curve` field, not `bpm` | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-A-010` | Non-4/4 meter | Outgoing track in 7/8, incoming in 4/4 | Defeats a hardcoded `beats[::4]` bar-phase assumption (P0-M0 §7.2's documented `AI-DJ-Mixing-System` failure mode); `meter` field populated with `numerator:7` | `{SIMPLE_CROSSFADE, CUT}` |

## Lane B — Content collision

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | `expected_transition_class_set` |
|---|---|---|---|---|
| `PAIR-SYN-B-001` | Vocal → vocal | Outgoing track has a continuous synthetic vocal-band tone through its final 15 s; incoming track has one starting at 0 s | Exposes systems with a generic DJ-filter EQ sweep but no actual vocal-activity detection (P0-M1 §8 level 6/§10) | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-B-002` | Sustained vocal outro → vocal intro | Same as B-001 but with a held single-note synthetic "vocal" tone specifically (harder collision, no rhythmic gaps to hide in) | Tighter version of B-001 | `{SHORT_EQ_BLEND, CUT}` |
| `PAIR-SYN-B-003` | Dense bass → dense bass | Both tracks have continuous low-band (20–150 Hz) synthetic energy through the transition window | Exposes lack of bass-activity detection | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-B-004` | Percussion-heavy overlap | Both tracks have dense synthetic transient/percussion hits with no rhythmic alignment | Tests whether beat-phase mismatch (Lane A) compounds with content collision | `{SIMPLE_CROSSFADE, CUT}` |
| `PAIR-SYN-B-005` | Instrumental → vocal | Outgoing track has no vocal band; incoming track's vocal starts immediately at 0 s | Positive-control-adjacent: this should be an *easier* case than B-001/B-002 — a system that scores this poorly has a more general defect | `{FULL_DJ_BLEND, SHORT_EQ_BLEND}` |
| `PAIR-SYN-B-006` | Sparse → dense | Outgoing track's exit region is low-density (few active bands); incoming's entry region is full-density | Tests energy/density-aware entry-point choice | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-B-007` | Dense → sparse | Reverse of B-006 | Same purpose, reverse direction | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |

## Lane C — Energy / loudness

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | `expected_transition_class_set` |
|---|---|---|---|---|
| `PAIR-SYN-C-001` | High → high | Both tracks near-constant high RMS energy through the transition | Positive control | `{FULL_DJ_BLEND}` |
| `PAIR-SYN-C-002` | Low → high | Outgoing track low energy, incoming track enters at high energy with no buildup | Tests energy-jump handling | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-C-003` | High → low | Reverse of C-002 | Same purpose, reverse direction | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-C-004` | Gradual buildup/drop | Outgoing track's final 20 s is a scripted linear energy ramp (buildup); incoming track opens with a sudden "drop" energy level | Tests whether energy-trajectory matching is used, not just endpoint energy | `{FULL_DJ_BLEND, SHORT_EQ_BLEND}` |
| `PAIR-SYN-C-005` | Large mastering-loudness gap | Outgoing track mastered at −14 LUFS integrated, incoming at −8 LUFS integrated, both otherwise structurally clean | Exposes systems using only a static per-track gain (P0-M1 §9/§10's exact critique of SimpMusic's `loudnessDb` handling) rather than transition-window loudness matching | `{FULL_DJ_BLEND, SHORT_EQ_BLEND}` (should sound clean *if* loudness is matched at the transition boundary) |
| `PAIR-SYN-C-006` | Locally quiet transition region despite high integrated loudness | Outgoing track has high integrated loudness overall but a deliberately quiet 10 s pocket exactly at its designated exit region | Defeats any system relying only on whole-track integrated loudness rather than the transition-window's local loudness | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |

## Lane D — Harmonic / tempo

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | `expected_transition_class_set` |
|---|---|---|---|---|
| `PAIR-SYN-D-001` | Compatible key + close tempo | Camelot-adjacent keys, BPM gap ≤ 2% | Positive control | `{FULL_DJ_BLEND}` |
| `PAIR-SYN-D-002` | Compatible key + large tempo gap | Camelot-adjacent keys, BPM gap ~40% (outside any safe stretch envelope) | Tests whether a system recognizes tempo gap as the binding constraint even when key looks fine | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE, CUT}` |
| `PAIR-SYN-D-003` | Incompatible key + close tempo | Camelot distance ≥ 4, BPM gap ≤ 2% | Tests whether key incompatibility alone is enough to avoid a full blend even when tempo is trivially matched | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-D-004` | Half/double-time | Outgoing 84 BPM, incoming 168 BPM (exact double-time relationship) | Tests half/double-time normalization (P0-M1 §11 documents this as a correct SimpMusic pattern worth carrying forward) — a naive system should NOT treat this as a large tempo gap | `{FULL_DJ_BLEND, SHORT_EQ_BLEND}` |
| `PAIR-SYN-D-005` | Pitch shifting helps | Camelot distance = 2, reachable to distance ≤ 1 via a 1-semitone shift on the outgoing track | Tests whether a bounded, justified pitch correction is applied | `{FULL_DJ_BLEND}` |
| `PAIR-SYN-D-006` | Pitch shifting should be avoided | Camelot distance = 2, but the fixture is scripted so any pitch shift attempt introduces an audible artifact signature (deliberately extreme timbral content) — tests restraint, not just capability | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` |
| `PAIR-SYN-D-007` | Stretch within reasonable range | BPM gap ~8%, within a conservative stretch envelope | Positive control for tempo correction | `{FULL_DJ_BLEND}` |
| `PAIR-SYN-D-008` | Stretch outside reasonable range | BPM gap ~60%, no half/double-time relationship | Tests whether the system declines correction rather than forcing an obviously broken stretch (mirrors P0-M1 §10's point about SimpMusic's own ±25% bound) | `{SIMPLE_CROSSFADE, CUT, NO_SPECIAL_TRANSITION}` |

## Lane E — Confidence / fallback

| `pair_id` | Case | Fixture sketch | `known_trap_purpose` | `expected_transition_class_set` |
|---|---|---|---|---|
| `PAIR-SYN-E-001` | Should be `FULL_DJ_BLEND` | Compatible key, close tempo, clean 8-bar intro/outro, no vocal collision, high energy both sides | Positive control | `{FULL_DJ_BLEND}` |
| `PAIR-SYN-E-002` | Should be `SHORT_EQ_BLEND` | Moderate key/tempo compatibility, some structural ambiguity, no severe collisions | Tests mid-confidence fallback | `{SHORT_EQ_BLEND}` |
| `PAIR-SYN-E-003` | Should be `SIMPLE_CROSSFADE` | Incompatible key, no exploitable structure, but no catastrophic collision either | Tests low-confidence fallback that still isn't a hard cut | `{SIMPLE_CROSSFADE}` |
| `PAIR-SYN-E-004` | Should be `GAPLESS` | Two fixtures scripted as sequential parts of one continuous piece (e.g. a scripted "Part 1"/"Part 2" pair with matching edges) | Tests recognition that no transition processing should be applied at all — a `FULL_DJ_BLEND` here is a defect, not a bonus | `{GAPLESS}` |
| `PAIR-SYN-E-005` | Should be `CUT` | Outgoing track ends cold (hard stop, no fade-out content); incoming track starts cold | Tests recognition that forcing a crossfade over non-existent fade material is wrong | `{CUT}` |
| `PAIR-SYN-E-006` | Should be `NO_SPECIAL_TRANSITION` | Fixture pair scripted to represent "sequential album tracks" per `docs/research/P0-M0-MARKET-PRIOR-ART-LANDSCAPE.md` §13 — intentionally suppressed transition | Directly tests the exact case P0-M0 names and P0-M1 §8 level 8 confirms SimpMusic cannot represent at all | `{NO_SPECIAL_TRANSITION}` |
| `PAIR-SYN-E-007` | Adversarial: strong-looking signals, should NOT full-blend | Compatible key, close tempo (so a naive BPM/key-only system would choose `FULL_DJ_BLEND`), but scripted severe vocal collision (Lane B-style) at the exit/entry region | The critical `C11_FORCED_WRONG_TRANSITION_STYLE` (benchmark contract §9) probe — this is the case where "looks compatible on paper" must lose to "sounds bad in practice" | `{SHORT_EQ_BLEND, SIMPLE_CROSSFADE}` (explicitly excludes `FULL_DJ_BLEND`) |
| `PAIR-SYN-E-008` | Adversarial: weak-looking signals, should still blend well | Incompatible key on paper (Camelot distance ≥ 4) but scripted so the actual audio content (e.g. sparse/ambiguous harmonic content in both tracks) makes the "incompatibility" musically inaudible | Tests over-conservative systems that decline to blend based on metadata alone without checking whether the mismatch is actually audible | `{FULL_DJ_BLEND, SHORT_EQ_BLEND}` |

## Coverage summary against benchmark contract §4/§10

- Every case type named in the benchmark contract's Lane A–E tables (§4.1–§4.5) has at least one concrete `pair_id` above.
- `PAIR-SYN-E-007` and `PAIR-SYN-E-006` are the two highest-priority pairs for validating the confidence/fallback lane specifically, since they are the direct adversarial tests of `C11_FORCED_WRONG_TRANSITION_STYLE` and of the exact "static global setting, no per-pair fallback" gap P0-M1 documents for SimpMusic.
- All 31 entries above are `provenance: SYNTHETIC` by design (§ preamble); genre/style tag diversity (pop, hip-hop, rock, etc., per benchmark contract §10) and non-synthetic sourcing are **not yet represented** — this is flagged explicitly as required future corpus-production work, not claimed as already satisfied by this illustrative catalog.
- None of these entries are wired into `manifest.json`/`tier1_fixtures.jsonl`/`tier1_pairs.jsonl` yet (`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` §1) — that wiring, plus actual audio generation and annotation, is corpus-production work for a future task.
