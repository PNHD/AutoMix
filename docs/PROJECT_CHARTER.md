# AutoMix Project Charter

## Product goal

Create a cross-platform music application with a provider-independent AutoMix engine. The desired user experience combines a modern streaming-library UX with transitions that can approach or exceed high-quality commercial AutoMix systems where technically and legally possible.

## Product positioning after P0-M0 market gate

The project is **not** positioned as merely “Spotify + Apple Music + AutoMix”. Current products already cover substantial parts of that proposition:

- Offtrack is a consumer automatic mixer for Spotify/Apple Music on iOS and Spotify on Android;
- djay already combines Spotify + Apple Music + Automix on Windows and mobile;
- Spotify now has native mixed playlists, Auto transitions, BPM/key tools and Smart Reorder;
- rekordbox and other professional DJ products already have mature Automix/beat-grid infrastructure.

AutoMix must instead pursue a defensible wedge:

> **consumer-first listening UX + reproducibly better transition planning + provider-independent architecture**.

The product should feel like a premium everyday music player, not a second professional DJ workstation.

See `docs/research/P0-M0-MARKET-PRIOR-ART-LANDSCAPE.md` for the full market/prior-art gate and explicit stop conditions.

## Initial target

**Windows-first prototype**, then evaluate Android, iOS, and macOS.

The first quality prototype operates on local/DRM-free audio so the team has full control over analysis and DSP. Streaming providers are added only after the core is independently validated.

## Post-P0 scope decision (P0-M4) — binding

**Decision:** `RESCOPE_BEFORE_P1`, per `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md` and the bridge contract `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md`.

**Authorized first production scope:** `PRESERVATION_FIRST_LOCAL_AUTOMIX`.

This is the *only* product/engineering scope authorized to begin as "P1." It is:

- local / DRM-free audio only (no streaming-provider integration);
- preservation-first, consumer listening (not DJ/highlight playback);
- limited to three transition classes by default: `PLAY_THROUGH`/`NO_SPECIAL_TRANSITION`, `GAPLESS` at genuine natural/continuous-work boundaries, and `SIMPLE_CROSSFADE` at a preservation-safe near-end boundary;
- fail-closed: when evidence for a more complex transition is missing or low-confidence, the engine degrades to a simpler class rather than forcing a blend.

**Not authorized in the first production prototype:** `FULL_DJ_BLEND`, tempo/time-stretch automation, pitch/key shifting, beat/downbeat-synchronized overlap as a product promise, automatic song-shortening/highlight playback, and automatic non-natural `CUT` as default behavior. `SHORT_EQ_BLEND` is research-only, off by default, and does not become a production default merely because research code for it already exists.

**Why:** P0 established a real technical gap above the pinned SimpMusic baseline and a coherent preservation-first consumer policy (R2), but did not produce valid real-world listening evidence that the complete provider-independent pipeline is audibly/repeatably better than a simple crossfade baseline, and the final real-corpus replay (`docs/research/P0-M3-R3-FINAL-REAL-CORPUS-REPLAY.md`) recovered zero `FULL_DJ_BLEND` survivors under the unchanged, conservative R2 evaluator. The original broad, `FULL_DJ`-capable P1 hypothesis is therefore not authorized to start; the narrower, falsifiable preservation-first hypothesis is.

**Relationship to the long-term research target:** the broad, `FULL_DJ`-capable AutoMix engine described throughout this Charter (Architecture Boundaries §3–§5, Definition of success) remains this project's **long-term research target**. It is not currently authorized as a production scope and does **not** inherit authorization from the narrow `PRESERVATION_FIRST_LOCAL_AUTOMIX` P1 — re-authorizing it requires a separate, explicit, PM-approved evidence gate (see `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`'s NG1–NG8 narrow-scope appendix and the human gate it defines for re-expanding scope). Every mention of "P1" elsewhere in this Charter that predates this decision should be read as describing that long-term target, not the currently authorized first production scope, unless a section below states otherwise.

**Historical note (not retroactively erased):** before P0-M4, this Charter's "P1 — Local AutoMix Engine" phase (below) described a single, broad `FULL_DJ`-capable local engine as the immediate next phase. That description is preserved as the long-term research target; it is superseded, for *authorization* purposes, by this section and by the redefined "P1 — Local AutoMix Engine (authorized scope)" phase below.

## Architecture boundaries

**Scope note (P0-M4):** the subsections below (§1–§5) describe the project's full long-term target architecture, including the complete analysis schema and DSP capability set. They are not a checklist of mandatory shipping dependencies for the first authorized production prototype. The first P1 (`PRESERVATION_FIRST_LOCAL_AUTOMIX`) requires only the narrow subset marked **[P1-REQUIRED]** below; everything else is marked **[FUTURE / RESEARCH]** and remains a target capability, not a current shipping requirement. See `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md` for the full narrow-scope requirement list.

### 1. Provider adapters

Responsible for catalog/library identity, metadata, authorization, queue operations, and playback surfaces that the provider legally exposes.

Examples may include Spotify, Apple Music, YouTube Music, and local files.

Provider adapters must not own AutoMix planning logic.

### 2. Track identity layer

Normalizes provider-specific track identity and metadata without assuming that the same audio bytes are available from every provider.

### 3. Analysis engine

Target analysis schema (full long-term target; see per-item P1 markers):

- tempo/BPM with confidence — **[FUTURE / RESEARCH for P1]** (not required to choose among `PLAY_THROUGH`/`GAPLESS`/`SIMPLE_CROSSFADE`)
- beat timestamps — **[FUTURE / RESEARCH for P1]**
- downbeats and bar grid — **[FUTURE / RESEARCH for P1]**
- musical key/chroma with confidence — **[FUTURE / RESEARCH for P1]**
- phrase boundaries — **[FUTURE / RESEARCH for P1]**
- section boundaries or labels when reliable — **[FUTURE / RESEARCH for P1]**
- loudness curve and integrated loudness — **[P1-REQUIRED]**, as a level-continuity diagnostic only (not a semantic/ML analyzer)
- energy curve — **[FUTURE / RESEARCH for P1]** (diagnostic-only if used; never gating)
- vocal activity / instrumental activity where feasible — **[FUTURE / RESEARCH for P1]**
- bass/percussion activity where feasible — **[FUTURE / RESEARCH for P1]**
- deterministic track duration / sample-rate / channel handling — **[P1-REQUIRED]** (not itemized above; added by `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md`)
- natural playback boundaries and preservation accounting (`effective_content_end_ms`, `outgoing_content_preservation_ratio`, per `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` §4) — **[P1-REQUIRED]**

None of the ML/MIR lanes above (tempo, beat, downbeat, key, phrase, section, vocal/instrumental, bass/percussion activity) are required to ship the first authorized production prototype. They remain future/research capabilities, carried forward as research-only inputs per the P0-M4-R1 contract, and must never silently unlock a more complex transition class than the narrow scope authorizes.

### 4. Transition planner

Evaluates candidate exit/entry points and creates a deterministic transition plan.

Candidate scoring should eventually consider (full long-term target):

- beat/downbeat alignment — **[FUTURE / RESEARCH for P1]**
- phrase alignment — **[FUTURE / RESEARCH for P1]**
- tempo adjustment cost — **[FUTURE / RESEARCH for P1]**
- harmonic compatibility — **[FUTURE / RESEARCH for P1]**
- loudness continuity — **[P1-REQUIRED]**
- energy continuity — **[FUTURE / RESEARCH for P1]**
- vocal collision risk — **[FUTURE / RESEARCH for P1]** (not required when the only candidate classes are `PLAY_THROUGH`/`GAPLESS`/`SIMPLE_CROSSFADE`, none of which claim vocal-collision mitigation)
- transition length — **[P1-REQUIRED]**
- analysis confidence — **[FUTURE / RESEARCH for P1]** as a model-derived value; **[P1-REQUIRED]** only in the narrow sense of "fail closed to a simpler class when structural evidence is missing," which does not require a calibrated ML confidence score

Low-confidence cases must degrade gracefully to simpler transitions instead of forcing a DJ-style blend. For the first P1, this principle is satisfied by the R2 preservation-first planner (`docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md`), restricted to the narrow class set defined in `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md`.

### 5. DSP/playback engine

Expected capabilities for the local prototype (full long-term target):

- two-deck prebuffered playback — **[P1-REQUIRED]**
- sample-accurate or sufficiently deterministic scheduling — **[P1-REQUIRED]**
- equal-power fades — **[P1-REQUIRED]** (used by `SIMPLE_CROSSFADE` only)
- tempo/time-stretch — **[FUTURE / RESEARCH for P1]**, not authorized as default/automatic behavior in the first production prototype
- pitch/key adjustment where justified — **[FUTURE / RESEARCH for P1]**, not authorized as default/automatic behavior in the first production prototype
- EQ/filter automation — **[FUTURE / RESEARCH for P1]**; `SHORT_EQ_BLEND` remains research-only, off by default
- loudness compensation — **[P1-REQUIRED]** as level-continuity diagnostics/deterministic gain curves only, not dynamic-range compression/limiting
- beat/downbeat synchronized transition execution — **[FUTURE / RESEARCH for P1]**, not a product promise in the first production prototype

## Reference implementations and benchmarks

SimpMusic is a research reference, not automatically the product base.

Pinned upstream research baseline at project start:

- Repository: `maxrave-dev/SimpMusic`
- Branch: `dev`
- Commit observed: `b694e284eb2dac0ecc90b7f4c11be49bed9b79aa`
- Core repository: `maxrave-dev/core`

Current known SimpMusic AutoMix behavior must be verified in P0-M1 rather than assumed from README or commit messages.

Commercial/consumer benchmark targets now also include:

- Apple Music AutoMix;
- Spotify Mixed Playlists `Auto`;
- Offtrack Smart Mix;
- djay Automix;
- rekordbox Automix where practical.

Open/research candidates include Echo Music, Mixxx, CUE-DETR/EDM-CUE, All-In-One, Signalsmith Stretch, DJtransGAN, BeatNet, and other candidates recorded in P0 research docs.

## Phase plan

### P0 — Feasibility, Market & Reference Baseline

- **P0-M0:** market, competitor and prior-art landscape gate — **PIVOT / complete**
- **P0-M1:** SimpMusic AutoMix forensic map
- **P0-M2:** competitive quality benchmark contract and test corpus design
- **P0-M3:** cross-platform music-analysis / cue-point / DSP technology evaluation

### P0 novelty gate

No main application implementation is allowed until all of these are true:

1. P0-M1 proves the exact SimpMusic baseline and its gaps.
2. P0-M2 defines a repeatable benchmark against relevant commercial and open-source references.
3. P0-M3 demonstrates a credible path to explicit beat/downbeat plus structure/cue information on the benchmark corpus.
4. A local planner prototype later demonstrates an audible/repeatable benefit over simple BPM/key/crossfade baselines.
5. The product specification retains at least one meaningful wedge against **both Offtrack and djay**.
6. No required product capability depends on DRM circumvention or an undocumented provider surface.

The project must stop or materially re-scope if commercial benchmarks already satisfy the intended consumer UX and transition quality with no meaningful unmet need, or if the only remaining differentiation requires unauthorized provider access.

**P0-M4 result:** condition 4 above was evaluated `FAIL` against the original broad, `FULL_DJ`-capable P1 hypothesis (no valid real-world listening evidence of an audible/repeatable benefit); conditions 3 and 5 were `PARTIAL`. Per `docs/research/P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md`, the project does not stop, but the broad P1 hypothesis this gate describes does not proceed as originally scoped — see "Post-P0 scope decision (P0-M4)" above and the redefined P1 phase immediately below.

### P1 — Local AutoMix Engine (authorized scope: `PRESERVATION_FIRST_LOCAL_AUTOMIX`)

**Authorized first production scope, per the P0-M4 rescope decision above:** build and validate a **preservation-first**, local/DRM-free transition engine limited to `PLAY_THROUGH`/`NO_SPECIAL_TRANSITION`, `GAPLESS` at genuine natural/continuous-work boundaries, and `SIMPLE_CROSSFADE` at a preservation-safe near-end boundary. Full requirements, exclusions, and entry conditions are defined in `docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md`. This phase may not start until that contract's preregistered real-music validation independently passes.

**P1-BROAD (long-term research target, not currently authorized):** the originally-described "build and validate the provider-independent analysis/planning/DSP core against local/DRM-free fixtures" — i.e. a `FULL_DJ`-capable engine using the full Architecture Boundaries §3–§5 analysis/DSP schema — remains the project's long-term research direction. It does not inherit authorization from the narrow P1 above and requires a separate, explicit, PM-approved evidence gate before any production implementation begins (see `docs/research/P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md`'s NG1–NG8 narrow-scope appendix for the human gate that governs re-expanding scope).

### P2 — First real provider adapter

Prefer a technically controllable source for an end-to-end prototype. Provider choice is evidence-driven and must pass policy/legal feasibility review.

### P3 — Unified library/player UX

Develop the product-facing library, queue, player, transition visualization, settings, and diagnostics.

### P4 — Spotify / Apple Music integration feasibility

Separate public API capabilities from licensed-partner capabilities. Do not bypass provider protections.

### P5 — Cross-platform hardening

Windows, Android, iOS, macOS as justified by the validated core and provider surfaces.

## Definition of success

The project is successful only if all of the following hold:

- its AutoMix quality is demonstrably better than fixed-duration crossfade;
- it materially improves on the current SimpMusic/Echo-class open-source references across a representative test set;
- it shows a meaningful product or quality advantage against the closest consumer benchmarks rather than reproducing existing functionality with a different UI;
- its core remains provider-independent and has a legal path to every playback surface it claims to support.
