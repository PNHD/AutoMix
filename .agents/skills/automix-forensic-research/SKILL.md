---
name: automix-forensic-research
description: Evidence-first repository/API/DSP research for AutoMix, with pinned revisions, repository-wide negative proof, audio-analysis terminology, and DRM/licensing boundaries.
---

# AutoMix Forensic Research

Use for source-code archaeology, API capability research, DSP feasibility work, provider-policy research, and comparisons against reference players/mixers.

## Scope discipline

- Research is read-only unless the task explicitly authorizes a disposable experiment or report commit.
- Never bypass DRM, capture protected provider PCM, steal credentials, hook/inject processes, or infer private APIs from prohibited techniques.
- Separate public API capability from partner-only/licensed capability.

## Source order

Prefer evidence in this order:

1. Pinned source repository revision and exact code paths/symbols.
2. Official vendor/platform documentation.
3. Primary research papers or official library documentation.
4. Reputable secondary sources only when primary evidence is unavailable.

For changing external systems, record retrieval date/version/ref.

## Repository forensic procedure

1. Pin the exact root commit/ref before searching.
2. Resolve and pin submodules/gitlinks independently.
3. Build a symbol/file inventory before drawing architecture conclusions.
4. Trace data/control flow end-to-end; do not stop at the first matching symbol.
5. For an absence claim, search the full pinned revision using multiple semantic variants before returning `NOT_FOUND_IN_PINNED_BASELINE`.
6. Record exact searches used for negative proof.
7. Separate later/upstream changes into an appendix; do not contaminate the pinned baseline.

## AutoMix terminology gate

Never collapse these concepts:

- `tempo/BPM`: scalar or estimated tempo.
- `beat-aware`: explicit beat timestamps/grid are used.
- `downbeat-aware`: bar starts/downbeats are identified and used.
- `phrase-aware`: transition entry/exit uses phrase boundaries.
- `section-aware`: intro/verse/chorus/outro or equivalent structural sections are identified and used.

BPM metadata alone is not beat-awareness. Beat timestamps alone are not downbeat-awareness. Downbeats alone are not phrase-awareness.

## Capability classification

Classify each requested capability as exactly one of:

- `IMPLEMENTED_AND_USED`
- `IMPLEMENTED_NOT_USED_FOR_AUTOMIX`
- `METADATA_ONLY`
- `HEURISTIC_PROXY`
- `NOT_FOUND_IN_PINNED_BASELINE`
- `UNKNOWN_NEEDS_RUNTIME_PROOF`

## Audio-analysis evidence checklist

When relevant, inspect separately for:

- BPM/tempo
- beat timestamps
- downbeats / bar grid / meter
- phrase boundaries
- section/segment labels or ranges
- key/chroma/harmonic compatibility
- pitch-shift/time-stretch behavior
- vocal activity
- bass/percussion/instrument activity
- energy/pace contour
- loudness/integrated loudness/short-term loudness
- onset/transient timing
- entry/exit candidate scoring
- confidence/fallback logic
- dual-deck buffering/scheduling
- volume/EQ/filter curves

## Reporting

Every conclusion must be tagged mentally as `FACT`, `INFERENCE`, or `UNKNOWN`. In the written report, make inferences explicit and list runtime-proof requirements for unknowns.

Finish with the handoff required by `automix-task-contract`.
