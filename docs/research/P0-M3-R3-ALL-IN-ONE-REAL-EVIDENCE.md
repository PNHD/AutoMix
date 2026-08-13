# P0-M3-R3 — bounded All-In-One real evidence

Status date: 2026-08-13

Starting branch/HEAD: `research/p0-feasibility` at
`64a78894166b873987de57437b2d74d4d057e97a`.

## Result

`ALL_IN_ONE_REAL_PIPELINE_VALIDATED_RESIDUAL_BLOCKERS`

The canonical All-In-One real public audio pipeline executed successfully on
exactly four owner-local opaque tracks. This is benchmark evidence, not a
quality PASS. No pair became FULL_DJ-eligible, and no render or listening pack
was created.

The accepted analyzer result remains
`ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY`.

## Frontier derivation

Before private audio access, `derive_frontier.py` inspected every one of the 20
accepted near-miss replays and retained only records whose measured texture
status was `COMPATIBLE` rather than `INCOMPATIBLE`.

- source pairs: 20;
- measured texture-incompatible exclusions: 17;
- retained pairs: 3;
- unique opaque tracks: 4;
- exact expected pair and track equality assertions: PASS.

Derived frontier:

| Lane | Pair |
|---|---|
| V1 | `RM014 -> RM010` |
| V2 | `RM014 -> RM081` |
| V2 | `RM041 -> RM014` |

Machine proof:
`tools/p0m3/all_in_one_runtime_probe/real_evidence/results/frontier_derivation_sanitized.json`.

## Canonical runtime and real public API

The isolated accepted P1 runtime was reused with these exact pins:

- All-In-One source: `18e78903c0365147a2c5d4e5e57ebf88cb7d800e`;
- Python: `3.10.18`;
- PyTorch: `2.0.0+cu118`;
- CUDA build: `11.8`;
- NATTEN: `0.14.6`;
- NATTEN source: `3b54c76185904f3cb59a49fff7bc044e4513d106`;
- checkpoint: `harmonix-fold0-0vra4ys2.pth` from `taejunkim/allinone`;
- loader-resolved checkpoint revision:
  `379e5fd010b3fdd0ee8381ff8cbcfa51d70b5c19`;
- loader-consumed checkpoint SHA-256:
  `0db596dfb0995f41d62f6267d76a9d54c046f1649bd35e1dbeca0c5f9a7b8acd`;
- checkpoint bytes: `1,400,571`.

The exact public call was:

```python
allin1.analyze(
    path,
    model="harmonix-fold0",
    device="cuda",
    include_activations=False,
    include_embeddings=False,
    keep_byproducts=False,
    overwrite=True,
    multiprocess=False,
)
```

The upstream symbol is `src/allin1/analyze.py::analyze`. It performs audio
loading, HTDemucs separation, four-stem spectrogram extraction, checkpoint
loading, inference, metrical postprocessing and functional-section
postprocessing. No manually constructed feature tensor or forward-only path
was used.

The normal loader still supplies no revision argument. The harness therefore
instrumented the loader return value without modifying upstream and recorded
the actual snapshot revision, resolved file hash and size above.

## Intervening failures retained

Failed environment/harness attempts were not accepted as analyzer evidence:

1. the isolated environment initially had no executable Linux `ffprobe`;
2. a discarded Windows-to-WSL FFmpeg bridge did not decode the mapped input;
3. offline mode could not see the prior probe's custom checkpoint cache;
4. the first provenance parser inspected the resolved blob path instead of the
   loader-returned snapshot path and rejected an otherwise completed run;
5. unseeded Demucs preprocessing was not repeatable: two full RM014 runs
   produced 372 vs. 357 beats and differing sections.

The accepted run uses a pinned isolated Linux FFmpeg archive from
`BtbN/FFmpeg-Builds` release `autobuild-2026-08-12-13-15`, archive SHA-256
`cf55934e9faa1969bff4c3fc1e1352707c9c9384e4d7986388830a8c8a726913`.
No system package or administrator setting changed.

For deterministic benchmark evidence, `deterministic_site/sitecustomize.py`
sets Python, NumPy and Torch RNG seed `0` in both the parent and Demucs
subprocess. No All-In-One or Demucs source was modified.

## RM014 real-pipeline smoke

RM014 ran first and twice, each time through fresh Demucs and spectrogram
directories.

| Run | Public API total | Inference | BPM | Beats | Downbeats | Segments |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 28.975612 s | 3.692557 s | 105 | 356 | 89 | 13 |
| 2 | 26.768241 s | 3.259567 s | 105 | 356 | 89 | 13 |

Exact equality: BPM, beat timestamps, downbeat timestamps, beat positions and
functional segments all PASS. Both outputs are schema-valid with zero NaN and
zero Inf. Evidence class:
`BENCHMARK_MODEL_OUTPUT_UNCALIBRATED`.

## Bounded four-track result

| Opaque ID | BPM | Beats | Downbeats | Segments | Inference wall time |
|---|---:|---:|---:|---:|---:|
| RM010 | 107 | 398 | 99 | 14 | 4.616143 s |
| RM014 | 105 | 356 | 89 | 13 | 3.692557 s (accepted first run) |
| RM041 | 103 | 317 | 80 | 12 | 2.389813 s |
| RM081 | 102 | 326 | 82 | 9 | 2.520331 s |

Every output schema is valid and finite. No fifth track was read or analyzed.
Full sanitized beats, downbeats, beat positions and functional segments are in
`results/all_in_one_real_evidence_sanitized.json`.

## Functional and downbeat evidence

Exact All-In-One terminology is preserved below. `intro`, `outro`, `chorus`
and `start` appear only because the model returned those labels.

| Track/role | Target ms | Functional interval ms | Label | Prev / next | Nearest boundary ms | Distance ms / beats / bars |
|---|---:|---|---|---|---:|---|
| RM014 exit | 194256.0 | 192350.0–208250.0 | `outro` | `chorus` / `end` | 192350.0 | 1906.0 / 3.344 / 0.836 |
| RM010 entry | 0.0 | 0.0–20.0 | `start` | none / `chorus` | 0.0 | 0.0 / 0.0 / 0.0 |
| RM081 entry | 0.0 | 0.0–20.0 | `start` | none / `intro` | 0.0 | 0.0 / 0.0 / 0.0 |
| RM041 exit | 186456.2 | 171290.0–191250.0 | `chorus` | `inst` / `end` | 191250.0 | 4793.8 / 8.265 / 2.066 |
| RM014 entry | 0.0 | 0.0–10.0 | `intro` | none / `intro` | 0.0 | 0.0 / 0.0 / 0.0 |

These are functional-section outputs, not phrase evidence. No phrase claim was
made, and no late boundary was renamed `outro` by the harness.

All four All-In-One downbeat grids have a 10.0 ms median nearest-event error
against the prior madmom benchmark grid. That is `AGREEMENT_DIAGNOSTIC`, not a
calibrated confidence upgrade. Prior madmom/current-heuristic status was
`RESOLVED_CONFLICT` for RM010/RM014/RM081 and `STILL_UNKNOWN` for RM041.
Because no accepted rule allows uncalibrated All-In-One output to replace
product ownership, every strict downbeat status remains unchanged.

## Three-pair replay

| Pair | Pre-All-In-One failed gates | New functional evidence | Strict R2 | Diagnostic | Residual blockers |
|---|---|---|---|---|---|
| V1 RM014 -> RM010 | genre, downbeat, harmonic, analysis_confidence | `outro -> start` | `FULL_DJ_WITHHELD` | `WITHHELD_DIAGNOSTIC` | genre, downbeat, harmonic, analysis_confidence |
| V2 RM014 -> RM081 | genre, downbeat, harmonic, analysis_confidence | `outro -> start` | `FULL_DJ_WITHHELD` | `WITHHELD_DIAGNOSTIC` | genre, downbeat, harmonic, analysis_confidence |
| V2 RM041 -> RM014 | downbeat, harmonic, structure, analysis_confidence | `chorus -> intro` | `FULL_DJ_WITHHELD` | `WITHHELD_DIAGNOSTIC` | downbeat, harmonic, structure, analysis_confidence |

For all three pairs:

- harmonic evidence: UNCHANGED;
- genre/style evidence: UNCHANGED;
- texture evidence: UNCHANGED;
- canonical `analysis_confidence`: UNCHANGED;
- BeatNet beat ownership: UNCHANGED;
- existing R2 evaluator and hard gates: UNCHANGED.

All three retain a harmonic failed gate. No
`REAL_RENDER_CANDIDATE_RECOVERED_EXISTING_R2` condition exists.

## Confidence and ownership

All-In-One exposes semantic outputs but no accepted calibrated product
confidence mapping. The evidence is therefore
`BENCHMARK_MODEL_OUTPUT_UNCALIBRATED`; it is never promoted to `HIGH`.
All-In-One beat timestamps are diagnostic only. BeatNet remains the accepted
beat-timestamp owner.

## License boundary

Unchanged:

- All-In-One code: MIT;
- checkpoint repository metadata: `SELF_DECLARED_MIT`;
- benchmark: `CLEAR_FOR_BENCHMARK`;
- production evaluation: `UNKNOWN_NEEDS_LEGAL_REVIEW`.

Technical real-audio success does not resolve training-audio provenance.

## Privacy, scope and non-actions

- approved pre-existing opaque mapping only;
- exactly four opaque tracks, no fifth track;
- committed evidence contains RM IDs only—no source filename, basename,
  mapped path, artist, title, album, raw tag, audio hash or audio bytes;
- no whole 19-track or 100-track rerun;
- no Signalsmith, Rubber Band, transition render or owner listening pack;
- no R2 gate changes, P1 work or `main` merge.

Machine evidence and verifier output live under
`tools/p0m3/all_in_one_runtime_probe/real_evidence/`.

## Validation

- bounded real-evidence verifier: 18/18 pre-commit assertions PASS (the
  post-commit mode adds remote/scope assertions);
- accepted runtime-probe verifier: 39/39 PASS;
- analyzer-recovery self-test: 11/11 PASS;
- analyzer-recovery verifier: 19/19 PASS with the local private sentinel;
- Stage-B mutation suite: all 23 mutations PASS;
- legacy Stage-B verifier: ALL CHECKS PASS with its two required local-only
  inputs.

The first legacy-regression invocation intentionally demonstrated fail-closed
behavior when those local-only inputs were absent; the authoritative rerun
above supplied them from gitignored local state without printing or tracking
their values.
