# P0-M4 — Final Feasibility Synthesis + P1 Gate

**Status date:** 2026-08-17  
**Binding task:** GitHub Issue #8  
**Starting HEAD:** `6a54790d220533eb6c336230fd6df23b98aed155`  
**Synthesis commit:** resolved after commit; see Issue #8 PM closeout / external handoff. A Git commit cannot contain its own final SHA without creating a different commit.  
**Execution:** ChatGPT PM synthesis in the owner-authorized chat session after the owner explicitly chose not to wait for Codex quota reset. Issue #8's original Codex/sub-agent execution profile is therefore superseded for execution only. No claim is made that independent sub-agents ran; instead the PM performed an evidence-audit pass and a separate skeptical decision pass over the same accepted source-of-truth set.  
**Final decision:** **`RESCOPE_BEFORE_P1`**

---

## 1. Final decision

**`RESCOPE_BEFORE_P1`**

AutoMix should **not stop**, because P0 established a credible preservation-first consumer planner, a provider-independent local architecture, a technically usable deterministic DSP direction, and a real technical gap above the pinned SimpMusic BPM/key-only baseline.

AutoMix should also **not enter the originally intended broad P1 production engine now**. Two load-bearing conditions remain unsatisfied:

1. the current evidence stack cannot reliably authorize a real `FULL_DJ_BLEND` on representative owner music under the accepted conservative R2 contract; and
2. most importantly, P0 never produced valid real-world listening evidence showing that the complete provider-independent pipeline is audibly/repeatably better than simple crossfade/BPM-key baselines on a representative set.

The correct next move is therefore to narrow the product/engineering claim to a **preservation-first local transition engine** whose first job is to choose *when to do less* and execute safe near-end transitions. `FULL_DJ_BLEND`, tempo/pitch manipulation, and beat/downbeat-synchronized complex mixing remain research-only until a future explicit evidence gate proves them.

This is a scope reduction, not a semantic relabeling of the current failed broad gate.

---

## 2. Starting / final HEAD

- Repository: `PNHD/AutoMix`
- Branch: `research/p0-feasibility`
- Verified starting HEAD: `6a54790d220533eb6c336230fd6df23b98aed155`
- `main` at synthesis start: `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`
- Final synthesis commit: see external PM handoff / Issue #8 closeout because the commit cannot self-contain its own hash.
- This task adds the synthesis report only. It does not modify production code or `docs/PROJECT_CHARTER.md`.

---

## 3. Source-of-truth hierarchy

When sources disagree, this synthesis uses the following precedence:

1. **Latest PM review/closeout comment** that explicitly accepts, rejects, or corrects evidence.
2. **Current committed accepted report + machine evidence** at the verified branch HEAD.
3. **Earlier accepted PM review comments** where not superseded.
4. **Historical task handoff prose** only where it is not contradicted by later PM review.
5. **Owner subjective observations** only as `OWNER_SUBJECTIVE_REFERENCE`, never as proof of a proprietary implementation.
6. Public product documentation as recorded in accepted P0-M0/R2 research; proprietary internals are never inferred.

Binding late correction for R3: final PM comment `5313966876` supersedes the final replay report's wording about beat/downbeat restrictiveness. Beat was relatively permissive; **downbeat remained a major blocker**. That same comment also narrows claims about the replay verifier's independence.

---

## 4. P0 evidence ledger

| Claim | Accepted source | Evidence class | Confidence | Decision pressure | Dimension |
|---|---|---|---|---|---|
| Pinned SimpMusic is a real dual-deck/DSP AutoMix implementation, but planning is scalar BPM/key driven and lacks explicit beat/downbeat/phrase/section/cue/content/confidence ownership | P0-M1 + Issue #1 PM closeout `5248459442` | `SOURCE_CODE` | HIGH | Supports continuing; exposes a real technical gap | Technical / differentiation |
| Broad “Spotify/Apple + automatic mixing” is already materially served by Offtrack, djay and native/provider products; provider breadth alone is not a wedge | P0-M0 | `PUBLIC_PRODUCT_DOC` + `PROJECT_INFERENCE` | HIGH | Argues against broad P1 positioning | Product differentiation |
| P0-M2 defines an executable, human-vetoed, holdout-aware benchmark and explicit G1–G8 P1 gate | P0-M2 + Issue #4 PM final closeout | `PROJECT_INFERENCE` / accepted specification | HIGH | Blocks P1 until quality evidence exists | Quality gate |
| BeatNet demonstrated strong explicit beat timestamps on deterministic synthetic fixtures, but downbeat/meter ownership was not reliable enough | P0-M3-R1 + Issue #5 closeout | `SYNTHETIC_BENCHMARK` | HIGH | Supports a beat research path; argues against broad production analyzer stack | Technical feasibility |
| All-In-One canonical legacy runtime can load its real checkpoint and run both synthetic and bounded real audio | All-In-One runtime + real-evidence reports | `SYNTHETIC_BENCHMARK` + bounded real analyzer evidence | HIGH | Supports technical feasibility but not production-quality ownership | Technical feasibility |
| All-In-One functional sections are real model outputs, but are not phrase boundaries and remain uncalibrated product evidence | All-In-One real evidence | bounded real analyzer evidence | HIGH | Re-scope | Technical / quality |
| RM041→RM014 evidence is only partially stable; RM014 entry downbeats and harmonic evidence are unstable/conflicting | pair-stability report | bounded real analyzer evidence | HIGH | Strongly argues against authorizing FULL_DJ from current evidence | Quality / analyzer reliability |
| R2 preservation-first planner rejects premature exits, ranks safe near-end candidates deterministically, keeps `PLAY_THROUGH`/`NO_SPECIAL_TRANSITION` first-class, and fail-closes complex mixing | P0-M3-R2 + Issue #6 PM acceptance | `SYNTHETIC_BENCHMARK` / policy prototype | HIGH | Supports a narrower production direction | Technical / product policy |
| Owner found Offtrack transitions poor/random/intrusive and observed at least one ~30 s premature exit | P0-M3-R2 owner reference | `OWNER_SUBJECTIVE` | MEDIUM | Supports preservation-first UX hypothesis only | Product differentiation |
| Owner's repaired synthetic R3 listening found synthetic methods insufficiently discriminative and a shared volume-drop problem; real vocal music was required | Issue #7 PM owner-listening direction update | `OWNER_SUBJECTIVE` + machine corroboration | HIGH for owner preference / MEDIUM for generality | Blocks quality PASS from synthetic listening | Quality |
| Early real-music listening packs were invalidated and explicitly marked `INVALID_DO_NOT_RATE`; no valid complete real-pipeline owner comparison was recovered later | Issue #7 PM reviews | `REAL_AUDIO_LISTENING` status | HIGH | Blocks P1 quality claim | Quality |
| Bounded analyzer recovery produced 0/20 strict-R2 eligible pairs, with unresolved/conflicting downbeat/harmonic/style/structure evidence and 17/20 measured incompatibility | analyzer-evidence recovery | `REAL_CORPUS_CACHED_ANALYSIS` + bounded analyzer evidence | HIGH | Re-scope | Analyzer / quality |
| Final cached 100-track replay produced 0 V1 and 0 V2 strict FULL_DJ survivors under unchanged conservative R2 gates | final real-corpus replay + final PM closeout `5313966876` | `REAL_CORPUS_CACHED_ANALYSIS` | HIGH | Re-scope; not universal impossibility | Quality / feasibility |
| Signalsmith Stretch remains a permissive MIT DSP production candidate; Rubber Band remains reference-only absent commercial-license choice | technical candidate inventory + R3 provenance | `LICENSE_PROVENANCE` + synthetic execution | HIGH | Supports local narrowed P1 path | Technical / legal |
| Local/DRM-free core work does not require provider circumvention; direct Spotify/Apple playback/mixing remains a later licensed/partner workstream | P0-M0 + Project Charter | `PUBLIC_PRODUCT_DOC` + `PROJECT_INFERENCE` | HIGH | Supports local P1 after re-scope; provider work deferred | Legal/provider |

### Non-double-count rule

`analysis_confidence = min(structure_strength, genre_strength, harmonic_strength)` remains a **composite**, not a fourth independent analyzer measurement. It is useful as a conservative gate result, but is not counted again as independent evidence of analyzer quality.

Likewise, the final 100-track replay is downstream of cached analysis and R2 gate semantics. It is not an independent listening experiment.

---

## 5. Six-condition Project Charter novelty-gate audit

| # | Charter condition | Result | Accepted evidence | Consequence |
|---:|---|---|---|---|
| 1 | P0-M1 proves the exact SimpMusic baseline and its gaps | **PASS** | Issue #1 PM accepted the pinned source-forensic conclusion: real BPM/key-aware dual-deck DSP, but no explicit temporal beat/downbeat/phrase/section/cue/content/confidence planner | A concrete open baseline and gap are known |
| 2 | P0-M2 defines a repeatable benchmark against relevant commercial/open references | **PASS** | P0-M2 final accepted contract defines class taxonomy, objective/proxy/human evidence, catastrophic failures, holdout and G1–G8 | The quality decision framework is adequate |
| 3 | P0-M3 demonstrates a credible path to explicit beat/downbeat plus structure/cue information on the benchmark corpus | **PARTIAL** | Explicit beat path is credible; All-In-One real functional sections run; CUE-DETR/other cues are benchmark evidence. Downbeat/meter reliability, phrase ownership, calibrated confidence, portability and production/legal status remain incomplete | Broad FULL_DJ analyzer stack is not production-ready |
| 4 | Local planner prototype demonstrates an **audible/repeatable benefit** over simple BPM/key/crossfade baselines | **FAIL** | R2 proves policy behavior, not audible superiority. Synthetic owner listening was insufficient and exposed loudness defects; real owner packs were invalidated; final real-corpus path recovered no render candidate | This is the load-bearing reason broad P1 cannot start |
| 5 | Product specification retains at least one meaningful wedge against both Offtrack and djay | **PARTIAL** | Preservation-first, consumer-not-DJ policy and provider-independent architecture remain plausible; however transition-quality superiority was not demonstrated and provider breadth alone was already rejected as a wedge by M0 | Keep the UX/policy hypothesis, remove unproven quality claims |
| 6 | No required product capability depends on DRM circumvention or an undocumented provider surface | **PASS for local core; provider integration deferred** | Local/DRM-free P1 architecture is explicit. M0 shows licensed products can integrate providers, while ordinary public API equivalence is not assumed | A local engine can proceed after re-scope without prohibited access; streaming is not a P1 prerequisite |

### Gate conclusion

The charter novelty gate is **not substantially satisfied for the original broad P1** because condition 4 is a direct FAIL and conditions 3/5 are only PARTIAL. `GO_TO_P1` would therefore require ignoring the project's own gate.

---

## 6. Quality-feasibility synthesis

| Question | Answer | Evidence boundary |
|---|---|---|
| Can AutoMix choose safer transition timing than naive/early-exit systems? | **`YES_PROVEN`** | R2 metadata/synthetic planner fixtures prove premature-exit rejection, preservation floors, ranking, play-through and compatibility fail-closed behavior. This is policy correctness, not audible quality superiority. |
| Can the current evidence stack reliably identify when `FULL_DJ_BLEND` is safe? | **`NO`** | No real V1/V2 survivor; downbeat remains a major blocker; pair stability found seed/window-dependent evidence and unresolved harmonic/downbeat conflict. The stack is good at withholding, not yet proven at finding true positives. |
| Can the current DSP path render a technically valid complex transition? | **`YES_PROVEN` on controlled synthetic fixtures only** | Repaired R3 harness executed planner-boundary transitions and Signalsmith/Rubber Band reference paths with fail-closed technical validation. This says nothing about representative real-music preference. |
| Has valid real-world owner listening demonstrated the complete provider-independent pipeline is better than simple crossfade on representative music? | **`NO`** | Synthetic listening was explicitly insufficient; real packs that existed were invalidated; final real-corpus replay had no legitimate render candidate. |
| Has the project met the P0-M2 P1 gate? | **`NO`** | G1–G8 were not passed on their required corpus/holdout/listening sample sizes. In particular there is no valid G1/G2 human-preference result for the full pipeline. |

---

## 7. Analyzer / evidence lane matrix

“Sufficient for P1” below means sufficient for the **original broad FULL_DJ-capable P1**, not merely useful as an optional diagnostic in the narrowed scope.

| Lane | Strongest accepted evidence | Legal / production status | Reliability | Runtime / portability | Sufficient for broad P1? |
|---|---|---|---|---|---|
| Beat timestamps | BeatNet explicit timestamps; strong synthetic results | Benchmark clear; production still requires deliberate CC BY / dependency decision | Strong synthetic beat lane; real ownership not comprehensively calibrated | Python/research stack; warm-reuse behavior required special handling | **PARTIAL / NO as shipping dependency** |
| Downbeats / bar phase | BeatNet benchmark + All-In-One real diagnostics + madmom benchmark | No accepted shipping owner; madmom benchmark-only; All-In-One legal review unresolved | Major blocker; conflicts/unknowns; RM014 boundary disagreement ~2 s vs madmom | All-In-One recovered only on legacy CUDA/NATTEN matrix | **NO** |
| Structure / sections | All-In-One functional segment labels on real bounded tracks | Benchmark clear; production evaluation `UNKNOWN_NEEDS_LEGAL_REVIEW` | Functional labels can be stable on a pair, but not calibrated globally | Legacy GPU stack; portability unresolved | **NO** |
| Phrase evidence | No accepted true phrase analyzer ownership | — | Functional sections are explicitly not phrases; fixed-N proxy rejected | — | **NO** |
| Cue points | CUE-DETR smoke/benchmark | MIT code but checkpoint/training rights need legal review | EDM-domain-specific, invalid raw predictions observed, confidence uncalibrated | Large research model | **NO** |
| Harmonic | Cached estimator + bounded librosa CQT oracle | Small clean-room/librosa research path; not accepted production confidence | Conflicts/UNKNOWN dominate; RM014 window sensitivity materially changes result | Offline feasible | **NO** |
| Style / genre | sparse local tags; Essentia oracle unavailable in accepted bounded path | Essentia AGPL/model licensing unsuitable without commercial route | Sparse/UNKNOWN evidence; fabricated genre was explicitly rejected | Production path unresolved | **NO** |
| Texture / content | bounded spectral/energy proxies | clean-room diagnostics possible | Useful as conservative evidence; not a calibrated semantic classifier | Offline feasible | **PARTIAL, blocker-only** |
| Confidence ownership | underlying-lane ledger + conservative aggregate | no calibrated production confidence owner | `analysis_confidence` is composite; no independent calibrated confidence | depends on constituent lanes | **NO** |
| Vocal activity | project vocal-band / activity proxies in bounded research | clean-room heuristic possible | Not a validated vocal-separation/activity truth lane | Offline feasible | **NO for positive FULL_DJ authorization** |
| Bass/percussion activity | project low-band / percussive proxies | clean-room heuristic possible | Useful diagnostic; not calibrated positive authorization | Offline feasible | **PARTIAL, blocker/diagnostic** |
| Loudness / energy | deterministic RMS / loudness diagnostics and continuity metrics | clean-room implementation feasible | Technically measurable; prior listening exposed a real continuity defect and no product-default curve won on valid real listening | Cross-platform implementation plausible | **YES for diagnostics; quality policy still unproven** |

### Narrow-scope implication

The first production prototype should therefore **avoid making ML/MIR uncertainty a prerequisite for ordinary playback**. A preservation-first simple transition engine can be useful without pretending that the unresolved analyzer lanes are solved.

---

## 8. Product-wedge assessment

Overall classification: **`ERODED_REQUIRES_RESCOPE`**.

### UX / product-policy wedge — plausible and materially evidenced

R2 established a coherent consumer policy that differs from highlight-first behavior: preserve essentially the whole track, prefer a natural near-end handoff, rank rather than take the first technical opportunity, and explicitly allow `PLAY_THROUGH` / `NO_SPECIAL_TRANSITION`. The owner's Offtrack experience supports the problem hypothesis, but remains subjective.

This is the strongest surviving wedge.

### Transition-quality wedge — unproven

P0 did not demonstrate representative real-audio preference over fixed crossfade or SimpMusic-class behavior. Therefore AutoMix must not claim Apple-like quality, superior DJ transitions, or “better than Offtrack/djay” transition quality yet.

### Provider-independence wedge — architecturally useful, not sufficient alone

The provider-independent core is a sound engineering choice and preserves future optionality. But M0 already established that provider breadth/Windows coverage alone is not enough differentiation. It supports the product; it is not by itself proof of market novelty.

---

## 9. Legal / provider-feasibility assessment

Classification for the immediate engineering path: **`LEGAL_PATH_CLEAR_ENOUGH_FOR_LOCAL_P1`**.

Streaming provider status: **`PROVIDER_INTEGRATION_DEFERRED`**.

### Safe-enough local path

A future narrowed P1 can operate on owner/local/DRM-free files and use:

- project-owned deterministic planning/mixing logic;
- normal platform audio APIs;
- simple gain/loudness/EQ DSP written in-house;
- permissive dependencies such as Signalsmith Stretch only if/when tempo processing re-enters scope and its integration gate is separately satisfied.

GPL/AGPL/NC research references stay outside a prospective proprietary shipping core unless the licensing strategy deliberately changes.

### Deferred provider path

P0-M0 established that licensed products can provide Spotify/Apple integrations, but did **not** establish that the same playback/mixing surfaces are available to this project via ordinary public APIs. AutoMix must not rely on protected-stream extraction, session interception, undocumented APIs, or DRM circumvention.

Therefore provider work remains a later licensing/partner feasibility stream and is not a blocker for proving a local engine.

---

## 10. What P0 proved

1. SimpMusic's pinned baseline has real DSP execution but its planning intelligence is materially below AutoMix's target.
2. A benchmark can distinguish tempo awareness from beat/downbeat/structure/cue/content/confidence awareness and can fail bad blends rather than rewarding complexity.
3. Preservation-first transition timing can be represented, ranked deterministically, and fail closed.
4. Audible entry and beat/downbeat alignment anchors are separate concepts and can be represented independently without discarding meaningful intro content.
5. Signalsmith provides a permissive technically runnable time-stretch direction for controlled research.
6. All-In-One's legacy runtime can execute its real pipeline and produce functional sections/downbeats on bounded real audio.
7. The current broad analyzer stack contains real instability/conflict; refusing FULL_DJ under uncertainty is justified.
8. Local/DRM-free architecture can continue without provider circumvention.
9. The market/product thesis must be consumer-policy/quality differentiated; provider aggregation alone is insufficient.

---

## 11. What P0 did NOT prove

1. It did not prove that the complete real-music pipeline is better than fixed crossfade.
2. It did not pass P0-M2 G1–G8.
3. It did not recover an accepted real V1/V2 `FULL_DJ_BLEND` candidate under current gates.
4. It did not establish reliable production ownership for downbeat/bar phase, phrases, cue confidence, style/genre, harmonic confidence, or global structure confidence.
5. It did not validate a product-default loudness/EQ curve on a valid real listening pack.
6. It did not prove mobile/macOS portability of the research MIR stack.
7. It did not resolve training-audio provenance for All-In-One/CUE-DETR-like checkpoints.
8. It did not prove direct Spotify/Apple provider integration is available to this project through normal public APIs.
9. It did not prove a transition-quality advantage over Offtrack or djay.
10. Zero final FULL_DJ survivors do **not** prove that complex AutoMix is impossible; they prove that the current evidence/gate combination does not honestly authorize one in the tested corpus.

---

## 12. Decision rationale

### Why not `GO_TO_P1`

`GO_TO_P1` would contradict both the charter and P0-M2. The load-bearing audible-benefit condition failed, the broad analyzer stack is incomplete, and the accepted final R3 result recovered no legitimate real complex-mix candidate.

### Why not `STOP`

The project still has a buildable, legally clean local direction that does not depend on the failed FULL_DJ hypothesis: preservation-first transition timing, conservative fallback, local files, simple deterministic DSP, and a consumer UX that explicitly avoids premature highlight-style exits. The R2 planner result is useful independent of complex beatmatching.

### Why `RESCOPE_BEFORE_P1`

The surviving evidence supports a smaller hypothesis:

> **Can a consumer-first local player make ordinary song-to-song playback feel more intentional by preserving songs, choosing safer near-end handoffs, and preferring simple/no-special transitions when complex evidence is weak?**

That hypothesis is technically implementable and falsifiable without pretending the unsolved FULL_DJ/analyzer problem is already solved.

---

## 13. Exact rescope

### Working scope name

`PRESERVATION_FIRST_LOCAL_AUTOMIX`

This is an engineering scope label, not final UI copy.

### First production-prototype transition classes

**Default-enabled:**

- `PLAY_THROUGH` / `NO_SPECIAL_TRANSITION`
- `GAPLESS` only at genuine natural/continuous-work boundaries
- `SIMPLE_CROSSFADE` at a preservation-safe near-end boundary

**Excluded from the first production prototype:**

- `FULL_DJ_BLEND`
- tempo/time-stretch automation
- pitch/key shifting
- beat/downbeat-synchronized overlap as a product promise
- automatic highlight/song-shortening mode
- automatic non-natural `CUT` as a default behavior

**Research-only / off by default:**

- `SHORT_EQ_BLEND`; it may remain in the research harness but must not become a product default until same-boundary real listening proves it improves over simple equal-power crossfade without introducing loudness holes or fatigue.

### Required analysis in the narrow prototype

Required:

- deterministic track duration / sample-rate / channel handling;
- natural playback boundaries;
- preservation accounting;
- deterministic gain curves;
- loudness / level-continuity diagnostics sufficient to avoid obvious holes/jumps;
- fail-closed fallback to play-through/simple transition.

Not required for first-product authorization:

- ML genre/style;
- harmonic key compatibility;
- phrase classifier;
- semantic section classifier;
- downbeat/bar classifier;
- ML cue-point model;
- model-derived `analysis_confidence`.

Beat/structure/harmonic outputs may remain **diagnostic research inputs only** until separately calibrated. They cannot silently unlock a more complex transition class.

### Local-file constraint

First production prototype is **local / DRM-free audio only**. No Spotify/Apple/YouTube protected-stream integration is part of this scope.

### Human gate before expanding scope

Before `SHORT_EQ_BLEND`, `FULL_DJ_BLEND`, tempo/pitch manipulation, or a “better transition quality than existing products” claim is enabled, a preregistered real-music blinded comparison must pass a PM-approved benchmark contract.

P0-M4 does **not** silently weaken P0-M2's existing G1–G8 thresholds. Until a dedicated rescope contract explicitly replaces an inapplicable FULL_DJ-specific gate with an equally explicit class-specific gate, the existing P0-M2 thresholds remain the source of truth.

At minimum, any revised narrow gate must retain:

- blinded preference against fixed-duration equal-power crossfade;
- a SimpMusic-class comparison path;
- unseen holdout data;
- zero safety-critical holdout failures;
- zero holdout human vetoes;
- deterministic/reproducible objective planning;
- no per-pair holdout tuning.

### Claims removed until proven

Do not market or specify as established capability:

- “Apple Music AutoMix quality”;
- “AI DJ-quality beatmatched transitions”;
- “phrase-aware mixing” as a production feature;
- “better than Offtrack/djay transition quality”;
- “Spotify + Apple Music unified AutoMix” as an immediately available provider feature;
- reliable automatic key/genre/downbeat/structure understanding across arbitrary music.

### Research artifacts carried forward vs. frozen

Carry forward:

- R2 preservation/boundary planner semantics;
- P0-M2 benchmark taxonomy and human-veto principles;
- simple deterministic DSP utilities that survive narrow-scope review;
- local privacy/provenance discipline;
- alignment-anchor contract as future-facing architecture, not active default behavior.

Freeze as research-only:

- current FULL_DJ gate/evaluator outcomes;
- All-In-One/CUE-DETR/madmom/Essentia oracle evidence;
- Signalsmith tempo path until complex mixing is re-authorized;
- harmonic/style/downbeat calibration experiments;
- R3 real-corpus candidate search.

No new analyzer/oracle loop is authorized merely because this rescope exists.

---

## 14. P1 entry contract / next step

Because the decision is `RESCOPE_BEFORE_P1`, **P1 remains blocked now**.

The next task is exactly one bounded specification bridge:

### `P0-M4-R1 — PRESERVATION-FIRST RESCOPE CONTRACT`

Purpose: change specification/benchmark contracts only so the repository has one unambiguous definition of the narrower product before production code begins.

Required outputs:

1. Update `docs/PROJECT_CHARTER.md` to record `PRESERVATION_FIRST_LOCAL_AUTOMIX` as the only authorized first production scope.
2. Add a narrow-scope P1 entry appendix/revision to the P0-M2 benchmark contract rather than silently waiving G1–G8.
3. Define which existing gates remain unchanged, which FULL_DJ-specific gates are out of scope, and what class-specific evidence replaces them.
4. Define one bounded real-music **P0 validation** using the existing research renderer for preservation-aware simple transitions only; no new analyzer/oracle work.
5. Define a hard finish rule: that validation produces either `NARROW_P1_ENTRY_ALLOWED` or `STOP_OR_REDESIGN`; no recursive analyzer loop.
6. Keep provider integration deferred and FULL_DJ research-only.

### P1 entry condition after that bridge

P1 may start **only after**:

- the revised charter/benchmark is accepted by PM; and
- the bounded real-music preservation-first validation passes its preregistered blinded preference, holdout, safety, veto and reproducibility criteria.

If that simple preservation-aware engine cannot beat the simple baseline under valid real listening, the project should **STOP or materially redesign the product**, not react by reopening the R3 analyzer search.

---

## 15. Frozen assumptions and prohibited claims

Frozen until new PM-authorized evidence:

- R3 final result is `R3_FINAL_PARTIAL_NO_VALID_V1_V2`.
- V1/V2 final survivor counts remain zero under the unchanged R2 evaluator.
- Downbeat is a major blocker in the final corpus; do not repeat the superseded wording grouping it with relatively permissive beat evidence.
- `analysis_confidence` is composite, not independent evidence.
- All-In-One functional labels are not phrase boundaries.
- Diagnostic/oracle agreement cannot silently promote a lane to `HIGH`.
- Invalidated owner packs remain `INVALID_DO_NOT_RATE` and are not retrospective quality evidence.
- Provider-protected audio must not be extracted to make local DSP possible.

Prohibited claims until an explicit later gate passes:

- broad P1 is “validated”;
- real FULL_DJ quality has passed;
- current analyzer stack is production-ready;
- commercial transition superiority has been demonstrated;
- checkpoint metadata alone resolves training-audio legal provenance.

---

## 16. Risks / unknowns

1. A preservation-first simple engine may still fail to produce a noticeable enough quality advantage over native/provider crossfade to justify a standalone product.
2. The product-policy wedge may be reproducible by competitors with little effort; market differentiation remains weaker than the architecture differentiation.
3. Loudness continuity must be solved with real listening, not only RMS/proxy metrics.
4. Local-file success does not guarantee streaming-provider access or identical DSP freedom later.
5. If future scope reintroduces FULL_DJ, downbeat, harmonic, style and structure confidence still require new calibration evidence and legal/runtime decisions.
6. Signalsmith is technically promising but its product value is irrelevant until tempo manipulation itself is re-authorized.
7. P0-M2's original 74-pair broad benchmark may be more expensive than needed for the narrower class set, but any revision must be explicit and must not lower the evidence bar merely for convenience.

No accepted-evidence contradiction prevents a decision, so `BLOCKED_EVIDENCE_INCONSISTENT` is not warranted.

---

## 17. PM review checklist

- [x] Live `research/p0-feasibility` HEAD verified before synthesis.
- [x] `main` verified untouched before synthesis.
- [x] P0-M1 PM accepted source-forensic baseline used rather than report execution-status wording.
- [x] P0-M2 final accepted G1–G8 contract treated as binding.
- [x] P0-M3-R1 analyzer results and license boundaries kept separate.
- [x] R2 planner success not substituted for audible quality proof.
- [x] Synthetic owner listening explicitly not treated as final real-world quality evidence.
- [x] Invalid real-music owner packs not counted as listening evidence.
- [x] Final R3 zero-survivor result interpreted narrowly, not as impossibility.
- [x] Final PM correction that downbeat remains a major blocker applied.
- [x] `analysis_confidence` not double-counted.
- [x] UX, quality and provider-independence wedge assessed separately.
- [x] Local legal path separated from deferred provider integration.
- [x] Exactly one final decision emitted: `RESCOPE_BEFORE_P1`.
- [x] Rescope is concrete and excludes unsupported FULL_DJ promises.
- [x] No audio, analyzer, oracle, render or provider experiment performed.
- [x] No P1 production code started.
- [x] No `docs/PROJECT_CHARTER.md` change in P0-M4 itself.

## Acceptance check — Issue #8 AC1–AC16

- **AC1 PASS** — live branch/HEAD verified first.
- **AC2 PASS** — accepted M0–M3 evidence is represented using late PM supersession rules.
- **AC3 PASS** — all six charter conditions audited individually.
- **AC4 PASS** — audible quality is separated from policy/synthetic evidence.
- **AC5 PASS** — zero-survivor outcome interpreted only under current evidence/gates.
- **AC6 PASS** — composite `analysis_confidence` not double-counted.
- **AC7 PASS** — UX, quality and provider-independent wedges separated.
- **AC8 PASS** — local P1 legal path distinguished from later streaming integration.
- **AC9 PASS** — one final decision: `RESCOPE_BEFORE_P1`.
- **AC10 PASS** — no GO based on optimism or sunk cost.
- **AC11 PASS** — exact bounded rescope defined above.
- **AC12 N/A / PASS** — STOP not selected; rationale explains why evidence does not justify STOP.
- **AC13 PASS** — no new audio/analyzer/render/provider experiment.
- **AC14 PASS** — no production P1 code.
- **AC15 PASS pending external pack construction** — PM ZIP is created locally after the commit, not tracked in GitHub, with no private audio/mapping/model/cache data.
- **AC16 PASS** — unresolved analyzer, quality, market and provider risks are exposed explicitly.

---

# Final verdict

**`RESCOPE_BEFORE_P1`**

P0 has enough evidence to preserve the project, but not enough evidence to authorize its original broad AutoMix engine. The first production direction must be a **local, preservation-first, simple-transition engine**. Complex FULL_DJ behavior remains research-only until a later, bounded and preregistered real-listening gate proves it.