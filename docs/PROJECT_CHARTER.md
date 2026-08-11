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

## Architecture boundaries

### 1. Provider adapters

Responsible for catalog/library identity, metadata, authorization, queue operations, and playback surfaces that the provider legally exposes.

Examples may include Spotify, Apple Music, YouTube Music, and local files.

Provider adapters must not own AutoMix planning logic.

### 2. Track identity layer

Normalizes provider-specific track identity and metadata without assuming that the same audio bytes are available from every provider.

### 3. Analysis engine

Target analysis schema:

- tempo/BPM with confidence
- beat timestamps
- downbeats and bar grid
- musical key/chroma with confidence
- phrase boundaries
- section boundaries or labels when reliable
- loudness curve and integrated loudness
- energy curve
- vocal activity / instrumental activity where feasible
- bass/percussion activity where feasible

### 4. Transition planner

Evaluates candidate exit/entry points and creates a deterministic transition plan.

Candidate scoring should eventually consider:

- beat/downbeat alignment
- phrase alignment
- tempo adjustment cost
- harmonic compatibility
- loudness continuity
- energy continuity
- vocal collision risk
- transition length
- analysis confidence

Low-confidence cases must degrade gracefully to simpler transitions instead of forcing a DJ-style blend.

### 5. DSP/playback engine

Expected capabilities for the local prototype:

- two-deck prebuffered playback
- sample-accurate or sufficiently deterministic scheduling
- equal-power fades
- tempo/time-stretch
- pitch/key adjustment where justified
- EQ/filter automation
- loudness compensation
- beat/downbeat synchronized transition execution

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

### P1 — Local AutoMix Engine

Build and validate the provider-independent analysis/planning/DSP core against local/DRM-free fixtures.

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
