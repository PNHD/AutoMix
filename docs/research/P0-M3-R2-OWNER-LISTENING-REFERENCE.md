# P0-M3-R2 -- Owner Listening Reference (Offtrack)

Status date: 2026-08-11

## Label

**`OWNER_SUBJECTIVE_REFERENCE`**

This document records a single subjective listening impression reported by the project owner/PM. It is **not**:

- an objective benchmark result,
- a reconstruction or claim about Offtrack's actual internal logic, thresholds, or algorithms,
- a claim about a specific track, artist, or provider setting (none were supplied by the owner and none are invented here, per `AGENTS.md` rule 1 and the forensic-research skill's evidence-source ordering),
- reverse engineering of Offtrack in any form.

Per Issue #6, this observation exists only to explain **why** this task's fixture set (`tools/p0m3/transition_policy/fixtures/fixtures.json`, specifically `TP-01`) includes a synthetic "technically-compatible-but-musically-premature exit around 30 seconds into a normal track" adversarial case. No numeric threshold in `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` was tuned to reproduce this specific figure; the sensitivity analysis in that document's §6/§7 explicitly demonstrates the guard is not dependent on any single elapsed-time number.

## Observation record

| Field | Value |
|---|---|
| Product | Offtrack |
| Date observed | 2026-08-11 |
| Reporter | Project owner/PM |
| Subjective transition quality | Poor / annoying / felt musically random |
| Subjective automatic-mixing impression | Intrusive |
| Observed premature song exit | Approximately 30 seconds into playback, in at least one tested case |
| Exact track identity | Not supplied by owner -- **not invented, not requested from any external source** |
| Exact Offtrack settings/mode active | Not supplied by owner -- **not invented, not requested from any external source** |
| Provider/platform used | Not supplied by owner |
| Method by which this record was obtained | Owner's own manual listening session, reported directly to the executing agent as task context (Issue #6 body) -- not independently observed, tested, or reproduced by this agent |
| Corroborating technical evidence | None. No Offtrack binary, API, network traffic, or source was inspected, accessed, or reverse engineered by this task |

## How this observation was used

1. It motivated the **shape** of `tools/p0m3/transition_policy/fixtures/fixtures.json`'s `TP-01` fixture: a track with a technically plausible early mix point and no legitimate musical exit at that point, and a genuine late exit elsewhere. `TP-01`'s exact fixture is fully synthetic and metadata-only (`docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` §6).
2. It motivated treating "premature exit" as a first-class benchmark failure mode (`premature_exit_rate` in `tools/p0m3/transition_policy/results/metrics.json`) alongside the pre-existing "forced full DJ blend" failure mode from `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`.
3. It did **not** set, tune, or justify any specific numeric guard value (fraction floors, confidence thresholds, etc.) in this task's eligibility model -- those are stated explicitly as P0 placeholders in `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` §12 and sensitivity-tested independently of this observation.
4. It did **not** change this task's binding stop conditions: DRM circumvention, protected-stream extraction, credential/session interception, and reverse engineering of proprietary Offtrack internals remain forbidden and were not attempted.

## Standing limitation

Because no track, timestamp precision, or settings detail was supplied, this record cannot be used as ground truth for any quantitative benchmark gate (contrast with `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md` §6.1's `SUBJECTIVE_REFERENCE_ONLY` comparability class, which this observation would fall under if Offtrack were ever added as a Tier-2 baseline system). If the owner later supplies the exact track and settings, this document should be updated with that detail under the same `OWNER_SUBJECTIVE_REFERENCE` label, and the fixture set may be extended (not retroactively "corrected") with a new case reflecting the additional detail.
