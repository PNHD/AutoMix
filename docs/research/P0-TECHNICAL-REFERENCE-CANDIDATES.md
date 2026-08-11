# P0 Technical Reference Candidates

Status date: 2026-08-11

This is a candidate inventory for P0 research. Inclusion here does **not** mean a library has been approved as a production dependency. P0-M3 must benchmark capabilities, runtime cost, portability, model size, maintenance, license obligations, and output quality before selecting components.

## Selection categories

- `BENCHMARK_NOW`: high-value candidate for P0 experiments.
- `PRODUCTION_CANDIDATE`: license/architecture appear compatible enough to evaluate for shipping, subject to technical validation.
- `REFERENCE_ONLY`: useful architecture/algorithm source, but current license/stack makes direct embedding undesirable.
- `DEFER`: potentially useful later, not needed for current gate.

## Music structure / beat analysis

### All-In-One Music Structure Analyzer

Repository: https://github.com/mir-aidj/all-in-one

Pinned revision: `18e78903c0365147a2c5d4e5e57ebf88cb7d800e`

License: MIT.

Outputs documented by upstream include:

- BPM;
- explicit beat timestamps;
- downbeat timestamps;
- beat positions within bars;
- functional segment boundaries;
- functional labels such as intro, verse, chorus, bridge and outro;
- optional frame-level beat/downbeat/segment/label activations;
- optional embeddings at 100 FPS, with stem dimension ordered bass/drums/other/vocals.

Why it matters to AutoMix:

This is currently the closest single open research package found to the temporal/structural metadata AutoMix needs for phrase/section-aware transition candidate generation. It can directly test the hypothesis left by SimpMusic's BPM/key-centric approach.

Caveats:

- Python/PyTorch research stack, not automatically a mobile/runtime choice;
- upstream main has not moved since 2023, so maintenance/runtime compatibility must be tested;
- Windows install currently involves NATTEN build requirements;
- functional segments are not identical to musical phrase boundaries; P0-M3 must evaluate boundary quality and derive phrase candidates rather than falsely equating the two.

Decision: `BENCHMARK_NOW`, `PRODUCTION_CANDIDATE_ONLY_AFTER_PORTABILITY_STUDY`.

### BeatNet

Repository: https://github.com/mjhydri/BeatNet

Pinned revision: `81cedd4beeb7235262db80969a0c9ce9a48a0ed4`

License in repository: Creative Commons Attribution 4.0 International (CC BY 4.0).

Capabilities documented upstream:

- streaming, real-time, online and offline modes;
- joint beat/downbeat tracking;
- tempo and meter tracking;
- causal CRNN + particle-filtering path for online/real-time inference;
- offline DBN path;
- official training pipeline now present in v1.2.0.

Why it matters:

Useful benchmark for causal beat/downbeat tracking if AutoMix later needs analysis before a complete track has been analyzed, or if we want to compare offline structure quality against a realtime-capable tracker.

Decision: `BENCHMARK_NOW`, `REFERENCE_ONLY_UNTIL_LICENSE_REVIEW`.

Reason: CC BY 4.0 is not a conventional software license. Do not embed code/model artifacts into the shipping engine without a dedicated legal/license decision.

### Essentia

Repository: https://github.com/MTG/essentia

Pinned revision: `b9fa6cb674ca43dfb94d28d293aeda441c6745db`

License: AGPLv3 for the open-source library distribution.

Capabilities:

Broad C++/Python MIR/DSP toolbox with tempo/beat, onset, key/chroma, loudness, spectral/tonal descriptors, segmentation and deep-learning model support.

Why it matters:

Excellent baseline/oracle for evaluating individual analysis dimensions and creating offline benchmark labels/features.

Decision: `REFERENCE_ONLY` for now.

Reason: AGPL obligations are a poor default fit for a future store-distributed multi-platform app unless the project deliberately adopts that licensing model or obtains other licensing terms. Do not make the core depend on Essentia during P0.

## Time-stretch / pitch-shift DSP

### Signalsmith Stretch

Repository: https://github.com/Signalsmith-Audio/signalsmith-stretch

Pinned revision: `57b93f4e9206a089a45387eaa39bdc9f310d3308`

License: MIT.

Capabilities:

- C++11 polyphonic pitch shifting and time stretching;
- upstream notes that time stretching sounds best in the more modest ~0.75x–1.5x range;
- tested with MSVC and AppleClang;
- preset/configuration APIs and split/chunked computation support;
- Web Audio/WASM version also exists upstream.

Why it matters:

AutoMix normally needs modest tempo correction around a track's native BPM, exactly the range this library targets. MIT + C++ also makes it a strong candidate for a provider-independent native DSP core across Windows/macOS/iOS/Android.

Decision: `BENCHMARK_NOW`, `PRODUCTION_CANDIDATE`.

Required tests:

- latency and reset/seek behavior;
- artifact quality on percussion, vocals and dense mixes;
- dynamic ratio changes during a transition;
- CPU cost on Windows x64, Android arm64 and iOS arm64;
- allocation/threading behavior in the chosen real-time wrapper.

### Rubber Band Library

Official project/license: https://breakfastquay.com/rubberband/

Capabilities:

Mature time-stretch/pitch-shift library with real-time use cases.

Licensing:

Open-source distribution is GPL v2 or later; proprietary/commercial licenses are available separately. The vendor explicitly notes App Store implications for GPL distribution.

Decision: `BENCHMARK_NOW`, `REFERENCE_ONLY_WITHOUT_COMMERCIAL_LICENSE`.

Reason: technically valuable quality reference, but Signalsmith Stretch is a simpler permissive candidate for an initial shipping architecture. Benchmark both before a DSP decision.

## DJ engine / playback architecture

### Mixxx

Repository: https://github.com/mixxxdj/mixxx

Pinned revision: `ab848eb75621d42d940ead767cc1cf4e619259ab`

License: GPL v2 or later.

Relevant architecture discovered at this revision includes:

- `src/track/beats.*` and beat factory/data model;
- serialized beat structures (`src/proto/beats.proto`);
- sync engine (`src/engine/sync/enginesync.h`);
- quantization controls;
- beat-grid import/support paths;
- mature multi-deck real-time DJ engine behavior.

Why it matters:

Mixxx is a high-value architecture reference for how a mature desktop DJ engine separates beat models, sync/quantization, decks, engine scheduling, controls and analysis. It can also reveal practical edge cases absent from small AutoMix demos.

Decision: `REFERENCE_ONLY`.

Reason: GPL application license and a large Qt/C++ architecture make copying/embedding it a poor default. Study concepts and independently implement only what our product needs.

## Reference metadata target: Apple Music Understanding

Not a cross-platform production dependency.

Use Apple's 2026 Music Understanding framework as a **metadata capability reference** for what a high-quality analyzer may expose:

- key;
- rhythm with beat timestamps, bars and BPM;
- structure with sections/segments/phrases represented as time ranges;
- pace;
- instrument activity;
- loudness.

Important boundary: availability of these analysis concepts does not grant access to protected Apple Music/Spotify PCM and does not override provider licensing/DRM.

Decision: `REFERENCE_ONLY`, plus possible native Apple analyzer experiment for owner-provided/local files later.

## Recommended P0-M3 benchmark lanes

P0-M3 should not ask “which one library wins?” as a single score. Test lanes separately:

1. **Beat/downbeat lane**
   - All-In-One
   - BeatNet
   - Essentia baseline(s)
2. **Structure lane**
   - All-In-One functional boundaries/labels
   - additional structure/novelty methods if needed
3. **Harmonic lane**
   - key/chroma algorithms and confidence
4. **Activity lane**
   - vocal/bass/percussion activity or proxies
5. **Loudness/energy lane**
   - integrated + short-term/local curves
6. **Stretch/pitch lane**
   - Signalsmith Stretch
   - Rubber Band reference
7. **Engine architecture lane**
   - SimpMusic pinned baseline
   - Mixxx reference patterns

The likely production architecture may combine several specialized components rather than adopt one large MIR framework.

## Dependency gate

No candidate becomes a production dependency until a task records:

- exact version/commit;
- license decision;
- supported target platforms;
- binary/model size;
- cold/warm analysis time;
- CPU/GPU/NPU requirements;
- memory peak;
- deterministic test corpus results;
- real-time suitability where applicable;
- failure/fallback behavior;
- maintenance/community risk;
- reproducible integration prototype.
