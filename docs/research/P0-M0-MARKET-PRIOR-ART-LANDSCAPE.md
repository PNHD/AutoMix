# P0-M0 — Market, Competitor & Prior-Art Landscape Gate

**Research date:** 2026-08-11  
**Execution agent:** ChatGPT PM  
**Model / effort:** GPT-5.6 Sol / High  
**Dynamic workflows:** OFF  
**Sub-agents:** OFF  
**Result:** **PIVOT — CONTINUE P0, HOLD P1**

## 1. Executive decision

AutoMix should **not** be stopped, but its original positioning must change before implementation.

The broad proposition **“Spotify/Apple Music + automatic DJ-style transitions” is already solved in the market to a meaningful degree**:

- **Offtrack (formerly Mixonset)** is already a consumer-first automatic mixer that connects to Spotify Premium and Apple Music on iOS, selects mix points, shortens tracks to highlights, automatically transitions, and optimizes queue order.
- **Algoriddim djay** already integrates both Spotify and Apple Music on Windows, iOS, Android, and macOS and exposes a mature Automix engine.
- **Spotify itself** now offers mixed playlists, automatic transitions, BPM/key visibility, editable volume/EQ/effects curves, and Smart Reorder based on BPM/key.
- **rekordbox** now supports Spotify Automix and has mature beat-grid, track-analysis, cue, vocal-position, and professional DJ infrastructure.
- Apple Music AutoMix remains a strong consumer quality reference but is unavailable in Apple Music for Windows and Android.

Therefore **provider breadth alone is not a defensible product wedge**, and **Windows + Spotify + Apple Music alone is also not novel because djay already provides that combination**.

The project remains worth pursuing only if it targets a narrower gap:

> **A consumer-first, Spotify-like listening product with a provider-independent AutoMix core whose transition quality is explicitly benchmarked for cue-point selection, beat/downbeat alignment, phrase/section structure, vocal collision, energy/loudness continuity, and graceful fallback — without requiring a professional DJ workflow.**

The product must be demonstrably better or materially simpler than existing products on at least one major axis before P1 is allowed to start.

---

## 2. Direct competitor matrix

Legend:

- `CONFIRMED` = current first-party documentation inspected.
- `UNKNOWN` = not established from a trustworthy public source; do not infer closed-source internals.
- `PARTIAL` = capability exists but only on some platforms/providers or is not fully automatic.

| Product | Classification | Spotify | Apple Music | Windows | iOS | Android | Automatic transitions | Automatic cue/mix points | Queue optimization | Documented analysis / controls | PM disposition |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| **Offtrack** | `DIRECT_CONSUMER_COMPETITOR` | CONFIRMED | CONFIRMED on iOS | No Windows product found | Yes | Spotify + SoundCloud currently | Yes | Yes, claims best fade-in/fade-out points | Smart Mix | Track highlights 25–50%, automatic mixing, Smart Mix | **Primary consumer benchmark** |
| **djay** | `DIRECT_CONSUMER_COMPETITOR` + `PRO_DJ_COMPETITOR` | CONFIRMED | CONFIRMED | Yes | Yes | Yes | Yes, Automix | Automatic or manual start/end points | Suggestions / queue tools; exact ranking internals UNKNOWN | Intelligent beat matching, transition styles, duration, tempo behavior, full DJ engine | **Primary licensed-integration benchmark** |
| **Spotify Mixed Playlists** | `DIRECT_CONSUMER_COMPETITOR` | Native | N/A | Yes | Yes | Yes | Auto mode | Manual waveform/beat editing available; Auto internals UNKNOWN | Smart Reorder by BPM + key | BPM, key, waveform/beat data, volume/EQ/effect curves | **Primary in-provider UX benchmark** |
| **Apple Music AutoMix** | `DIRECT_CONSUMER_COMPETITOR` | N/A | Native | **No AutoMix in Windows app** | Yes | **No AutoMix** | Yes | Closed-source / UNKNOWN | UNKNOWN | Dynamically chooses transition type; may remove silence, crossfade, use complex transition, or skip transition | **Primary subjective quality benchmark** |
| **rekordbox** | `PRO_DJ_COMPETITOR` | Automix supported as of 7.2.16 | Supported | Yes | Mobile app | Mobile app | Yes | Mature cue/analysis infrastructure; exact Spotify Automix internals UNKNOWN | Not positioned as consumer smart shuffle | Beat/grid analysis, key/BPM, Smart Cue, AI vocal position; streaming restrictions apply | **Professional reference** |
| **VirtualDJ** | `PRO_DJ_COMPETITOR` | No current Spotify integration established here | Not established | Yes | Not primary | Not primary | Yes | Auto-generated Automix POIs + manual pair editor | No evidence of consumer smart reorder | Smart/Fade modes, optional BPM match, POI hierarchy, manual persistent pair transitions | **Mature automix UX/reference** |
| **DJ.Studio** | `OFFLINE_STUDIO_COMPETITOR` | Via supported source/import workflows, not assessed as live Spotify player here | Same caveat | Desktop/web workflow | Not target | Not target | Harmonize creates/order transitions in project | Default in/out mix settings; current docs still require fine-tuning | Yes by BPM/key | Beat grids, key/BPM, transition presets, stems; Harmonize explicitly does **not** use energy | **Offline optimization benchmark** |
| **Mixxx Auto DJ** | `OPEN_SOURCE_REFERENCE` | No official Spotify streaming path | No official Apple Music streaming path | Yes | No | No | Yes, simple Auto DJ | No sophisticated automatic cue planner in Auto DJ | No | Manual DJ engine has beat grids/sync, but Auto DJ explicitly ignores volume/frequency/rhythm | **Architecture/manual-DJ reference only** |

### Product sources

- Apple AutoMix current support: https://support.apple.com/vi-vn/105067
- Apple AutoMix behavior on Mac: https://support.apple.com/guide/music/transition-songs-muse5e9ec085/1.6/mac/26
- Spotify playlist mixing launch/update: https://newsroom.spotify.com/2025-08-19/mix-your-favorite-playlists-seamlessly-by-adding-your-own-transitions/
- Spotify Smart Reorder: https://newsroom.spotify.com/2026-02-25/smart-reorder-playlist-mixing/
- djay streaming services: https://help.algoriddim.com/topic/music-streaming/streaming-services
- djay Windows Automix: https://help.algoriddim.com/user-manual/djay-pro-windows/mixing-basics/using-automix
- djay Windows product page: https://www.algoriddim.com/djay-pro-windows
- Offtrack: https://www.offtrack.com/
- Offtrack Apple Music: https://www.offtrack.com/applemusic/
- Offtrack Spotify: https://www.offtrack.com/spotify/
- rekordbox release notes 7.2.16: https://rekordbox.com/en/support/releasenote/
- rekordbox streaming restrictions: https://rekordbox.com/en/support/faq/streaming-7/
- VirtualDJ Automix: https://virtualdj.com/manuals/virtualdj/interface/browser/sideview/automix.html
- VirtualDJ POI Editor: https://virtualdj.com/manuals/virtualdj/editors/poieditor.html
- VirtualDJ Automix Editor: https://virtualdj.com/manuals/virtualdj/editors/automixeditor.html
- DJ.Studio Harmonize: https://help.dj.studio/en/articles/7878402-harmonize-previously-automix
- Mixxx Auto DJ: https://manual.mixxx.org/2.4/en/chapters/djing_with_mixxx.html

---

## 3. The closest threat to novelty: Offtrack

Offtrack is the most important discovery for product positioning because it is not primarily a professional DJ deck application. Its current first-party material describes almost exactly the consumer job-to-be-done originally envisioned for AutoMix:

- sync Spotify and Apple Music playlists;
- find suitable transition moments automatically;
- shorten songs to highlights (roughly 25–50% in its marketing);
- seamlessly transition tracks;
- Smart Mix the queue instead of ordinary shuffle;
- target driving, parties, workouts, and everyday listening rather than a manual DJ performance workflow.

Current platform asymmetry still leaves room:

- Offtrack markets **iOS + Android**, not Windows.
- iOS currently lists Spotify Premium, Apple Music, SoundCloud Free, TIDAL, local files, and CarPlay.
- Android currently lists Spotify Premium and SoundCloud Free, with more integrations promised.

However, **“Offtrack has no Windows version” is not enough reason to build AutoMix**. djay already covers Windows with Spotify + Apple Music + Automix. AutoMix must combine the consumer simplicity of Offtrack with a measurable technical or UX advantage that djay does not target.

No official public Offtrack source repository was located in the GitHub searches performed for `Mixonset` / `Offtrack AI DJ`. This should be treated as **closed-source from our current evidence**, not proof that no source exists anywhere.

---

## 4. djay: strongest proof that provider integration is technically/licensably possible

djay materially changes the feasibility landscape:

- Spotify and Apple Music are both integrated into djay on Windows.
- Spotify is supported on iOS, macOS, Windows, and Android.
- Apple Music is supported on iOS, macOS, visionOS, Android, and Windows.
- Spotify can feed djay Automix.
- djay exposes automatic/manual transition start/end points and a mature automatic DJ workflow.
- Streaming-service restrictions still disable Neural Mix for Spotify/Apple Music, and recording is disabled for most streamed tracks.

This proves that **a licensed partner can build the user experience**, but does **not** prove that the same capabilities are available through ordinary public Spotify/Apple developer APIs.

Strategic conclusion:

- Do not spend P0 trying to bypass provider restrictions.
- Build and benchmark the provider-independent engine on legal local/DRM-free audio.
- Keep provider adapters isolated.
- Treat direct Spotify/Apple Music playback/mixing as a future partner/licensing workstream, not a prerequisite for proving the core.

---

## 5. Native Spotify has consumed part of the product opportunity

Spotify Premium now supports playlist mixing with:

- an `Auto` blend mode;
- user-editable transition presets;
- volume, EQ, and effect curves;
- waveform and beat data for transition editing;
- visible BPM and key;
- Smart Reorder based on BPM and key.

This means a product that merely adds crossfade, BPM/key matching, or queue sorting around Spotify is no longer differentiated.

AutoMix must go beyond native Spotify at the **automatic planner** layer and/or offer a superior cross-platform listening experience.

---

## 6. Professional products are already mature but solve a different UX problem

### rekordbox

Current rekordbox 7.2.16 adds Spotify Automix, Spotify Collection/library features, and makes AI vocal-position detection available on all plans. rekordbox is a strong reference for track analysis, beat-grid correction, cue management, vocal-awareness tooling, and professional reliability.

It is **not** evidence that we should build a second professional DJ workstation. AutoMix should deliberately avoid competing on decks, DVS, controller mapping, USB export, sampler, performance mode, etc.

### VirtualDJ

VirtualDJ has a mature Automix model with:

- Smart mode selecting mix points based on outro/intro;
- Fade variants;
- optionally beatmatching when tempos are close;
- automatically generated POIs such as `Mix Tempo`, `Mix Cut`, `Mix Fade`, and `Mix Full`;
- a pair-specific Automix Editor whose adjustments are saved for future occurrences of the same ordered track pair.

This is an excellent UX reference for **explainable/fallback mix-point hierarchy**, even if its product surface is too DJ-centric for AutoMix.

### DJ.Studio

DJ.Studio is useful as an offline/studio reference, but its current documentation is unusually candid:

- Harmonize optimizes playlist order mainly from BPM + key.
- Harmonize explicitly says it **does not use energy** as an ordering parameter.
- Automatic transitions use user/default settings and still require listening/fine-tuning.
- Earlier v3 documentation explicitly clarified that Harmonize did not actually determine best mix-in points and that phrase detection was under development.

Therefore DJ.Studio should not be treated as proof that fully automatic high-quality cue/phrase selection is solved.

---

## 7. Open-source/source-code landscape

| Project | Classification | License | What it actually provides | Source-level reality check | Disposition |
|---|---|---|---|---|---|
| **SimpMusic** | `OPEN_SOURCE_REFERENCE` | GPLv3 | YouTube Music playback + DJ-style crossfade/AutoMix | Existing inspection shows BPM/key-driven duration, equal-power fade, filters, tempo/pitch heuristics; P0-M1 will formally prove whether temporal beat/downbeat/phrase grids are absent | `REFERENCE_ONLY_LICENSE` + benchmark |
| **Echo Music** | `OPEN_SOURCE_REFERENCE` | GPLv3 | Active Android music player with AutoMix beta | `BeatAnalyzer.kt` uses classical DSP: STFT/spectral flux -> tempo autocorrelation -> periodic beat phase. Dynamic mix-in/out are RMS-energy heuristics. Not evidence of semantic phrase/section detection | `REFERENCE_ONLY_LICENSE` |
| **Mixxx** | `OPEN_SOURCE_REFERENCE` | GPLv2+ | Mature DJ engine, beat grids, sync, quantization | Auto DJ itself explicitly ignores volume, frequency content, and rhythms | `REFERENCE_ONLY_LICENSE` + architecture reference |
| **AI-DJ-Mixing-System** | `OPEN_SOURCE_REFERENCE` | MIT | Experimental Python DJ planning/mixing pipeline | README wording is stronger than implementation: “phrase boundaries” are every 32 detected beats; “bar/downbeat” boundaries are `beats[::4]`; energy is RMS heuristics. Uses librosa time-stretch, not a production realtime DSP engine | `REUSE_CANDIDATE` only for small ideas; never quality oracle |
| **DJtransGAN** | `RESEARCH_REFERENCE` | MIT | Learned EQ + fader transition generation from real DJ mixes | Inference takes explicit previous/next cue points. It learns **how to execute** a transition, not end-to-end cue selection/queue planning | `REUSE_CANDIDATE` research component |
| **CUE-DETR / EDM-CUE** | `RESEARCH_REFERENCE` | MIT code; dataset/checkpoint terms need separate audit | Automatic expert-style cue-point prediction; code, checkpoints, and metadata dataset published | Strong candidate for cue-point planner benchmark. Dataset has almost 5k EDM tracks and cue metadata from 4 DJs; no copyrighted audio is shipped in repo | **High-priority `REUSE_CANDIDATE` for P0-M3** |
| **All-In-One Music Structure Analyzer** | `RESEARCH_REFERENCE` | MIT code | BPM, beat/downbeat and functional music structure/segments | Strong candidate for true structure metadata rather than fixed-N-beat proxy | **High-priority P0-M3 benchmark** |
| **Signalsmith Stretch** | `OPEN_SOURCE_REFERENCE` | MIT | C++ time-stretch / pitch-shift | Appropriate production DSP candidate; benchmark required vs alternatives | **High-priority `REUSE_CANDIDATE`** |
| **BeatNet** | `RESEARCH_REFERENCE` | CC BY 4.0 repo | Realtime/offline joint beat/downbeat/tempo/meter tracking | Good analysis oracle/candidate; production licensing/dependency implications need dedicated review | `DEFER` for production, benchmark in P0-M3 |
| **Essentia** | `RESEARCH_REFERENCE` | AGPLv3 | Broad MIR algorithms/models | Excellent benchmark/oracle, restrictive for a permissive/proprietary core | `REFERENCE_ONLY_LICENSE` by default |
| **Rubber Band** | `OPEN_SOURCE_REFERENCE` | GPL/commercial dual path | High-quality time-stretch/pitch-shift | Benchmark quality, but commercial licensing needed for proprietary distribution outside GPL path | `REFERENCE_ONLY` unless commercial license chosen |

### 7.1 Echo Music reality check

Pinned source inspected:

- Repository: `EchoMusicApp/Echo-Music`
- Ref: `3764023b3e6ca573576e5ee414501467c94a2c96`
- File: `app/src/main/kotlin/com/music/echo/playback/audio/BeatAnalyzer.kt`

The code explicitly documents:

```text
decode -> mono PCM -> STFT -> spectral flux onset envelope ->
autocorrelation tempo estimate -> comb-filter phase for beat offset
```

It constructs a periodic grid from `firstBeatOffsetMs + k * (60000 / bpm)`, analyzes an 18-second middle window, and derives mix-in/out from short RMS-energy scans. This is useful engineering prior art, but it is still far below the semantic structure target defined for AutoMix.

### 7.2 AI-DJ-Mixing-System reality check

Pinned current source inspected:

- Repository: `kckDeepak/AI-DJ-Mixing-System`
- Ref: `d56bd28c772f713ae39fc9ac33d0b555b98e1ce4`
- `structure_detector.py`

Important implementation details:

- beat extraction uses `librosa.beat.beat_track`;
- “phrase boundaries” are generated as **every 32 beats** (`8 bars × 4 beats`), not detected semantic phrases;
- “bar/downbeat” locations are derived as `beats[::4]`, which assumes the first detected beat is the bar start and the meter is 4/4;
- energy uses 2-second RMS blocks + derivative thresholds;
- mixing engine searches show `librosa.effects.time_stretch`.

This is exactly why AutoMix requires source verification instead of trusting README/marketing labels such as “phrase-aware” or “downbeat-aware”.

### 7.3 DJtransGAN reality check

Repository: `ChenPaulYu/DJtransGAN`  
License: MIT.

The project contains differentiable fader/EQ DSP, GAN training/inference, and pretrained weights. Its inference interface takes `prev_cue` and `next_cue`, so it does not solve the key planner question: **where should the transition start/end and which tracks should follow each other?**

It is useful for learning transition-control curves from human mixes after our planner is working.

### 7.4 CUE-DETR is a high-value new candidate

Repository: `ETH-DISCO/cue-detr`  
Code license: MIT.

The published EDM-CUE metadata includes nearly 5k tracks from four DJs with:

- BPM / beat-grid start;
- initial beat count;
- time signature;
- expert cue points.

The accompanying 2024 paper reports a dataset of roughly 21k expert cue points and improved cue-point precision with strong phrasing adherence.

This is likely more valuable for AutoMix P0-M3 than inventing a cue-point detector from scratch. **Do not adopt checkpoints/data into production until their separate Hugging Face terms and training-data provenance are audited.**

### Source repositories

- SimpMusic: https://github.com/maxrave-dev/SimpMusic
- Echo Music: https://github.com/EchoMusicApp/Echo-Music
- Mixxx: https://github.com/mixxxdj/mixxx
- AI-DJ-Mixing-System: https://github.com/kckDeepak/AI-DJ-Mixing-System
- DJtransGAN: https://github.com/ChenPaulYu/DJtransGAN
- CUE-DETR: https://github.com/ETH-DISCO/cue-detr
- All-In-One: https://github.com/mir-aidj/all-in-one
- Signalsmith Stretch: https://github.com/Signalsmith-Audio/signalsmith-stretch
- BeatNet: https://github.com/mjhydri/BeatNet
- Essentia: https://github.com/MTG/essentia

---

## 8. Academic prior art we should not reinvent

### Automatic Detection of Cue Points for DJ Mixing

Zehren, Alunno, and Bientinesi model professional-DJ rules using feature extraction + novelty analysis. Their published work reports that about **96% of generated switch points were rated good for use in a DJ mix** in their evaluation.

Paper: https://arxiv.org/abs/2007.08411

### CUE-DETR / Cue Point Estimation using Object Detection

Argüello, Lanzendörfer, and Wattenhofer (2024) recast cue-point estimation as object detection and publish code/model/data metadata. The paper reports around **21k expert-annotated cue points across nearly 5k tracks**, with high phrasing adherence.

Paper: https://arxiv.org/abs/2407.06823  
Code: https://github.com/ETH-DISCO/cue-detr

### A Computational Analysis of Real-World DJ Mixes

Kim et al. analyzed **1,557 DJ mixes, 13,728 tracks, and 20,765 transitions**, extracting cue points and transition lengths from real-world mixes. Their public summary shows transition-length peaks at phrase-scale intervals and provides a data-backed reference for human DJ behavior.

Paper: https://arxiv.org/abs/2008.10267  
Project: https://mir-aidj.github.io/djmix-analysis/

### DJtransGAN

Sony/Academia Sinica's work trains differentiable EQ/fader controls from real DJ mixes and reports listening-test results competitive with baselines. This demonstrates that learned transition **execution** is viable once cue points are known.

Sony publication: https://www.sony.com/en/SonyInfo/technology/publications/automatic-dj-transitions-with-differentiable-audio-effects-and-generative-adversarial-networks/

---

## 9. What is already solved

Do **not** spend project time trying to claim novelty in these areas:

1. Basic crossfade / equal-power crossfade.
2. BPM-based transition-duration heuristics.
3. Key/Camelot compatibility scoring.
4. Basic beatmatching and tempo correction.
5. Generic filter/EQ transition presets.
6. Spotify-native mixed playlists.
7. Spotify + Apple Music access inside a Windows DJ application — djay already does this.
8. Consumer automatic Spotify + Apple Music mixing on iOS — Offtrack already does this.
9. Automatic song shortening/highlights as a product concept — Offtrack already markets it.
10. Basic automatic intro/outro energy heuristics — open-source examples already implement them.
11. Fixed “every N beats” pseudo-phrase rules — trivial prior art and not sufficient quality.
12. Expert-style cue-point ML as a research concept — CUE-DETR already demonstrates it.
13. Learned EQ/fader transition execution — DJtransGAN already demonstrates it.

---

## 10. What is not solved, or not publicly verifiably solved

Closed-source competitors may internally solve some of these. The statement here is **not** that nobody has them; it is that there is no sufficiently verified open, provider-independent implementation/product combination found in this research.

1. A **consumer-first** Windows/mobile player with Spotify-like daily-listening UX rather than DJ decks while exposing high-quality AutoMix.
2. A **provider-independent open core** with explicit contracts for analysis -> transition planning -> DSP -> fallback.
3. Open-source AutoMix whose planner is demonstrably:
   - beat-timestamp aware;
   - actual downbeat/meter aware;
   - semantic phrase/section aware rather than fixed 32-beat proxy;
   - vocal-collision aware;
   - energy/loudness-contour aware;
   - confidence-aware with graceful fallback.
4. A reproducible benchmark showing why one automatic transition is better than another rather than relying on “sounds smooth”.
5. A transition planner trained/calibrated from real DJ cue-point behavior while remaining deterministic and explainable at runtime.
6. Cross-platform parity with the same planner/DSP behavior and regression corpus.
7. A credible public route to arbitrary cross-provider streamed audio mixing without partner licensing. This remains primarily a business/licensing problem, not an engineering gap.

---

## 11. Defensible AutoMix wedge

### Product wedge

**Do not build another DJ workstation.**

AutoMix should feel like a normal premium music player:

- Spotify-like library/search/queue model;
- one-tap AutoMix;
- optional smart reorder;
- optional `Full track` vs `Highlights` behavior;
- simple transition confidence/explanation rather than waveforms/decks by default;
- advanced controls hidden behind an expert surface;
- desktop Windows as a first-class experience, not a degraded port;
- mobile parity later.

### Technical wedge

The engine should optimize a transition pair over explicit candidate entry/exit points with a score such as:

```text
score =
  downbeat_alignment
+ phrase_or_section_compatibility
+ harmonic_compatibility
+ energy_continuity
+ loudness_continuity
- tempo_stretch_cost
- vocal_overlap_penalty
- transient_collision_penalty
- uncertainty_penalty
```

Then execute the chosen plan using deterministic DSP:

- dual-deck prebuffer;
- phase/beat alignment;
- conservative time-stretch/pitch shift;
- equal-power volume curves;
- bass/EQ exchange where appropriate;
- filter/echo only when the selected transition style supports it;
- fallback to shorter EQ fade / crossfade / clean cut / no transition when confidence is low.

The model/ML layer may analyze structure or rank cue points, but it should not be allowed to generate unstable real-time audio-control decisions without deterministic constraints.

---

## 12. Build vs fork vs integrate

### Do not fork SimpMusic as the product foundation

Reasons:

- GPLv3 constrains future product licensing choices.
- its audio/provider architecture is centered around its existing YouTube/Tidal-related stack rather than a provider-independent core;
- its current AutoMix quality target is below the phrase/downbeat/cue-point planner we want to benchmark.

Use it as a behavioral/code reference only.

### Do not fork Echo Music as the product foundation

Reasons:

- GPLv3;
- Android-first/player-specific architecture;
- current AutoMix analysis is classical BPM/grid + RMS intro/outro heuristic, not semantic cue planning.

### Do not clone Offtrack/djay

Their provider access is likely tied to commercial relationships and platform agreements that cannot be inferred from public APIs. Product behavior is benchmarkable; access rights are not reusable source code.

### Build a clean core, reuse permissive components selectively

High-priority candidates for P0 evaluation:

- CUE-DETR — cue-point prediction research baseline;
- All-In-One — structure/beat/downbeat baseline;
- Signalsmith Stretch — production DSP candidate;
- DJtransGAN — learned transition-control research reference;
- existing simple deterministic baseline we implement ourselves for apples-to-apples testing.

Each dependency/model/data asset still requires its own license/provenance audit before production adoption.

---

## 13. Mandatory competitive benchmark before P1

P1 production implementation is **HOLD** until we complete a hands-on benchmark.

### Required products

At minimum:

1. Apple Music AutoMix
2. Spotify `Mix -> Auto`
3. djay Automix
4. Offtrack Smart Mix
5. rekordbox Automix where practical
6. SimpMusic AutoMix
7. Echo Music AutoMix
8. AutoMix local baseline/prototype when available

### Fixed benchmark playlist

Use a controlled set covering:

- same-genre / close BPM / compatible key;
- same-genre / far BPM;
- compatible BPM but incompatible key;
- vocal outro -> vocal intro collision;
- sparse intro/outro;
- abrupt cold ending;
- halftime/double-time ambiguity;
- variable intro length;
- genre jump;
- tracks with non-4/4 or weak beat where possible;
- sequential album tracks where transition may intentionally be suppressed.

For commercial streaming services, do not record or extract protected audio if the product/provider forbids it. Score transitions live and record only metadata, timestamps, observations, and settings.

### Score each pair

0–5 on:

- entry-point musicality;
- exit-point musicality;
- beat alignment;
- bar/downbeat alignment;
- phrase coherence;
- vocal collision;
- harmonic clash;
- energy continuity;
- loudness continuity;
- tempo artifacts;
- transition-style appropriateness;
- overall preference.

Also record:

- transition duration;
- track truncation amount;
- whether the engine declined/fell back;
- whether the queue was reordered;
- whether the result is reproducible.

---

## 14. P0 novelty gate

AutoMix may advance to P1 only if **all** of the following are true:

1. P0-M1 proves the exact SimpMusic baseline and its gaps.
2. P0-M2 establishes a repeatable listening/metadata benchmark.
3. P0-M3 demonstrates at least one analysis stack that can reliably produce actual beat/downbeat plus structure/cue information on the test corpus.
4. A local AutoMix planner prototype beats simple BPM/key/crossfade baselines on the benchmark.
5. The product specification has at least one meaningful wedge against **both** Offtrack and djay.
6. No required P1 feature depends on DRM circumvention or an undocumented provider capability.

### STOP / re-scope conditions

Stop or materially re-scope the project if any of these happen:

- hands-on testing shows Offtrack or djay already delivers the desired consumer UX **and** comparable/better transition quality on Windows/mobile with no meaningful unmet need;
- our phrase/downbeat/cue-aware planner fails to show an audible/repeatable benefit over simpler existing Automix approaches;
- the only remaining differentiation requires unauthorized Spotify/Apple Music audio access;
- cross-platform DSP cannot meet quality/latency targets without a licensing/dependency path we are unwilling to accept;
- the product wedge collapses to cosmetic UI differences around functionality already offered natively by Spotify.

---

## 15. PM conclusion

**RESULT: PIVOT.**

Continue Phase 0. Do not start production app code.

The market is not empty; in fact, Offtrack and djay are close enough that they must become explicit benchmark targets. However, open-source AutoMix quality remains visibly fragmented, and the strongest research pieces are components rather than a polished consumer system.

The project is justified only as:

> **consumer-first UX + reproducibly better transition planning + provider-independent architecture**, with provider streaming integrations treated separately from the core technical proof.

### PM next task

Keep **P0-M1 — SimpMusic AutoMix forensic map** as the active execution task. Do not run P0-M2/P0-M3 in parallel yet.

When P0-M1 hands off, PM must review its evidence against this market report, then issue P0-M2 as a fixed competitive benchmark specification. P0-M3 should explicitly add **CUE-DETR** to the candidate analyzer/cue-planner evaluation.
