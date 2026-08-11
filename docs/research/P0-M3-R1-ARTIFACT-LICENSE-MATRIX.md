# P0-M3-R1 — Artifact / License Gate

Status date: 2026-08-11 (PM REVIEW #2 FINAL CLOSEOUT PASS — Sec 1.1 addendum per R12; no verdicts changed; supersedes commit `8df67b16ab2cdc5044f80fa1c0470bd9b6f32b09`)

Companion to `docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md`. Produced for
GitHub Issue #5 Task A. Per `.agents/skills/automix-forensic-research`,
every conclusion below is tagged `FACT` (directly observed/cited),
`INFERENCE` (reasoned from FACTs), or `UNKNOWN_NEEDS_LEGAL_REVIEW`.

**Binding rule applied throughout (AGENTS.md rule 4 / Issue #5):** a
repository's code license is never treated as covering a checkpoint or
dataset hosted elsewhere, even when the same organization publishes both.
A Hugging Face repository's `license:` metadata tag is treated as a
**self-declared uploader claim**, not an independently audited legal
determination — it is the best available evidence in every case below,
but it is recorded as such, not overstated.

Verdict enum used (Issue #5 Task A): `CLEAR_FOR_BENCHMARK` /
`CLEAR_FOR_PRODUCTION_EVALUATION` / `BENCHMARK_ONLY` /
`BLOCKED_ASSET_LICENSE` / `UNKNOWN_NEEDS_LEGAL_REVIEW`.

---

## 1. CUE-DETR / EDM-CUE

| Field | Value | Tag |
|---|---|---|
| Code repository | `ETH-DISCO/cue-detr` | — |
| Code revision inspected | `d0462856ed2f59a1fb65267cfbe87340a65ad1bb` | FACT |
| Code license | MIT (`LICENSE` file at pinned revision) | FACT |
| Checkpoint source | `https://huggingface.co/disco-eth/cue-detr` (`hf_hub_download`-style load via `DetrForObjectDetection.from_pretrained('disco-eth/cue-detr')`, confirmed by actually loading it — see main report Task D) | FACT |
| Checkpoint license | HF repository metadata tag: `license: mit`. **No separate `LICENSE` file or license text exists in the checkpoint repo itself — the README is empty.** The metadata tag is the sole textual evidence. | FACT (tag exists) / INFERENCE (tag is uploader-declared, not an audited grant) |
| Checkpoint size | 41.6M parameters, F32 safetensors (~166 MB at 4 bytes/param) | FACT (HF model card) |
| Dataset source | `https://huggingface.co/datasets/disco-eth/edm-cue` (EDM-CUE) | FACT |
| Dataset license | HF metadata tag: `license: mit` | FACT (tag) |
| Dataset content | Metadata only — track title/artist/duration/genre/key, beat-grid (BPM/start/time-sig), and ~21k manually-annotated expert cue-point timestamps for ~5k EDM tracks sourced from 4 DJs, referenced by Deezer catalog ID. **No audio bytes are included or redistributed.** | FACT (HF dataset card + `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`, already recorded) |
| Is copyrighted training/source audio redistributed? | No — dataset repo contains references (Deezer IDs) only, not audio. | FACT |
| Training-audio provenance/rights | The underlying EDM audio used to *derive* the cue-point annotations and to train the checkpoint's weights came from "4 different DJs" (README) — ETH-DISCO's own rights to use that (evidently commercial, copyrighted) audio for model training, and whether that training relationship imposes any restriction on redistributing the *resulting weights*, is **not documented anywhere in the repository or dataset card**. | UNKNOWN_NEEDS_LEGAL_REVIEW |
| Attribution required? | Yes under MIT (retain license/copyright notice) for both code and checkpoint, per the respective MIT terms. | FACT |
| Commercial use permitted? | MIT permits it for the tagged artifacts themselves; the unresolved training-provenance question above is a separate, un-mitigated risk that a permissive *tag* on the output weights does not resolve. | INFERENCE |
| **Benchmark verdict** | **`CLEAR_FOR_BENCHMARK`** — code MIT (audited: LICENSE file read directly), checkpoint/dataset MIT-tagged, no audio was downloaded or redistributed by this task, and the checkpoint was used only for local, non-redistributed inference (see main report; not committed to this repository). | — |
| **Production-evaluation verdict** | **`UNKNOWN_NEEDS_LEGAL_REVIEW`** — before any production embedding, resolve (a) whether the HF `mit` tag is an authoritative grant from ETH-DISCO (the actual rights holder) and (b) ETH-DISCO's own training-audio provenance/rights, per AGENTS.md rule 6 (do not infer permissive rights from a convenient tag alone). | — |

### 1.1 Transitive model/config assets actually downloaded/required (PM REPAIR R4)

The original P0-M3-R1 pass omitted these from the matrix even though they
were actually downloaded/required by `candidates/run_cuedetr.py`. Every
asset the runner touches at inference time is now audited here, not
assumed to be covered by CUE-DETR's own MIT tag.

| Asset | Source | Purpose | License | Kept in current runner? | Benchmark verdict | Production verdict |
|---|---|---|---|---|---|---|
| `facebook/detr-resnet-50` processor config | `https://huggingface.co/facebook/detr-resnet-50`, `DetrImageProcessor.from_pretrained(...)` | Image-preprocessing config only (resize/normalize parameters) — **no model weights** from this repo are loaded or used | `apache-2.0` (HF metadata tag, confirmed FACT via direct repository fetch; official Meta AI repo, trained on COCO 2017) | **Yes** — required; the pinned CUE-DETR code itself specifies this exact call | `CLEAR_FOR_BENCHMARK` | `CLEAR_FOR_PRODUCTION_EVALUATION` for the config artifact itself (Apache-2.0, no training-audio provenance question since it carries no audio-domain weights) — still gated by CUE-DETR's own overall `UNKNOWN_NEEDS_LEGAL_REVIEW` verdict (Sec 1) for the composite pipeline |
| `timm/resnet50.a1_in1k` pretrained backbone weights | `https://huggingface.co/timm/resnet50.a1_in1k` | ImageNet-1k-pretrained ResNet-50 weights, auto-downloaded by `transformers`' default `use_pretrained_backbone=True` behavior to initialize the DETR backbone **before** `disco-eth/cue-detr`'s own checkpoint state_dict is loaded on top and overwrites every backbone parameter | `apache-2.0` (HF metadata tag, confirmed FACT) | **No — removed this repair pass.** Empirically verified (this repair pass): `DetrForObjectDetection.from_pretrained('disco-eth/cue-detr', use_pretrained_backbone=False)` vs. the upstream-default `use_pretrained_backbone=True` produce **bit-identical** inference output (detection scores and box positions compared exactly equal, max score diff = 0.0) on the same input file, proving the checkpoint's own state_dict fully supplies the backbone and the timm download changes nothing about the result. `candidates/run_cuedetr.py` now passes `use_pretrained_backbone=False`. | `N/A` — no longer part of the dependency graph | `N/A` |

Recorded even though removed, per R4's instruction not to silently drop an
asset from the audit trail — this is what *was* downloaded in the original
pass and *why* it is no longer necessary, not a claim it was ever
license-blocked (Apache-2.0 was never the problem; it was simply
unnecessary weight).

**PM REVIEW #2 R12 addendum:** the bit-identical claim above previously
had no committed machine-readable evidence backing the prose. It is now
recorded in `tools/p0m3/analyzer_shootout/results/cuedetr_backbone_equivalence.json`
(`verdict: "BIT_IDENTICAL"`, `max_score_diff: 0.0`, exact dependency
versions and compared fixture/fields), generated by
`generate_backbone_equivalence_evidence()` in `candidates/run_cuedetr.py`
and asserted present by `eval/verify_repair.py`. No verdict in this
section changed as a result — this only strengthens the existing
evidence from prose-only to machine-checkable.

## 2. All-In-One Music Structure Analyzer

| Field | Value | Tag |
|---|---|---|
| Code repository | `mir-aidj/all-in-one` | — |
| Code revision inspected | `18e78903c0365147a2c5d4e5e57ebf88cb7d800e` | FACT |
| Code license | MIT (`pyproject.toml`: `license = "MIT"`, `LICENSE` file present) | FACT |
| Checkpoint source | `taejunkim/allinone` on Hugging Face, loaded via `hf_hub_download(repo_id='taejunkim/allinone', filename=...)` in `src/allin1/models/loaders.py` (inspected directly, not run — see Task E) | FACT |
| Checkpoint license | HF repository metadata tag: `license: mit` | FACT (tag) |
| Dataset (training) | Harmonix Set (`urinieto/harmonixset`) — 912 Western pop tracks with beat/downbeat/functional-segment annotations | FACT (checkpoint filenames are literally `harmonix-fold{0-7}-*.pth`, confirming the training-fold source) |
| Dataset license | Harmonix Set **annotations** are CC BY 4.0; the dataset explicitly does **not** redistribute the underlying copyrighted pop-track audio (only Mel-spectrograms, MusicBrainz IDs, and annotations are shared) — the same "annotations/metadata are open, audio itself is not" pattern as EDM-CUE. | FACT (Harmonix Set README/Zenodo record, ISMIR 2019 paper) |
| Is copyrighted training/source audio redistributed? | No — by the dataset's own design. | FACT |
| Training-audio provenance/rights | All-In-One's checkpoint weights were derived from training on Harmonix's underlying copyrighted commercial pop-track audio (obtained by the Harmonix/paper authors, not by `taejunkim`), under conditions not documented in the `taejunkim/allinone` HF repo. Same category of gap as CUE-DETR §1. | UNKNOWN_NEEDS_LEGAL_REVIEW |
| Runtime dependency license (NATTEN) | MIT (`SHI-Labs/NATTEN`, confirmed via GitHub `LICENSE`) | FACT |
| Runtime dependency license (madmom, optional per All-In-One's own README) | BSD-3-Clause per upstream `CPJKU/madmom`; not independently re-verified this pass beyond the version already used for BeatNet (PyPI `madmom==0.16.1`) | INFERENCE (carried from BeatNet's use of the same package, §3) |
| **Benchmark verdict** | **`CLEAR_FOR_BENCHMARK`** — same reasoning as CUE-DETR (code + checkpoint tag both MIT, NATTEN MIT). Actual execution was `BLOCKED_ENVIRONMENT` this pass (see main report Task E), not `BLOCKED_ASSET_LICENSE`. | — |
| **Production-evaluation verdict** | **`UNKNOWN_NEEDS_LEGAL_REVIEW`** — identical training-provenance gap to CUE-DETR. | — |

## 3. BeatNet

| Field | Value | Tag |
|---|---|---|
| Code repository | `mjhydri/BeatNet` | — |
| Code revision inspected AND executed | `81cedd4beeb7235262db80969a0c9ce9a48a0ed4` | FACT (see main report Task D — real end-to-end run) |
| Code license | Creative Commons Attribution 4.0 International (CC BY 4.0), full `LICENSE` file read directly | FACT |
| Checkpoint source | Bundled directly in the repository at the pinned revision: `src/BeatNet/models/model-1.pt`, `model-2.pt`, `model-3.pt` | FACT (`git` tree listing at the pinned SHA) |
| Checkpoint license | Same CC BY 4.0 as the repository — no separate license file exists for the `.pt` files, and none is needed since they are first-party artifacts of this same repository. | FACT |
| Dataset (training) | Per the ISMIR 2021 paper (BeatNet), trained/evaluated on Ballroom, Hainsworth, SMC, GTZAN, Rock corpus and similar public MIR beat-tracking corpora. Individual dataset licenses for this list were **not independently re-audited** this pass (out of scope: we consume the shipped checkpoint, not the training pipeline). | INFERENCE (paper citation) / UNKNOWN (full per-dataset license chain not re-verified) |
| Is copyrighted training/source audio redistributed by this repo? | No — only trained weights (`.pt`), no audio. | FACT |
| Attribution required? | Yes — CC BY 4.0 requires attribution for any use, including commercial, of the code and the bundled checkpoints. | FACT |
| Commercial use permitted? | Yes, under CC BY 4.0, subject to attribution. CC BY 4.0 is a content license, not a conventional software license (no patent grant, no explicit "software" framing) — this is an atypical, non-default choice for shipping compiled/embedded model weights in an app-store binary and needs a deliberate attribution-surface decision (e.g., an in-app credits screen), not a purely technical integration decision. | INFERENCE |
| **Benchmark verdict** | **`CLEAR_FOR_BENCHMARK`** — actually executed this pass under CC BY 4.0 terms; benchmark-only local execution against synthetic fixtures, no redistribution, output not committed as an asset. | — |
| **Production-evaluation verdict** | **`BENCHMARK_ONLY`** (unchanged from `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`'s prior `REFERENCE_ONLY_UNTIL_LICENSE_REVIEW`) — CC BY 4.0's attribution mechanism for a compiled/shipped model has not been decided; this pass's successful *execution* is new evidence of technical viability, not of a completed legal review, and does not by itself upgrade the production verdict. | — |

## 4. Essentia

| Field | Value | Tag |
|---|---|---|
| Code repository | `MTG/essentia` | — |
| Code revision recorded | `b9fa6cb674ca43dfb94d28d293aeda441c6745db` (not re-inspected beyond the prior P0 record; not executed this pass) | FACT (carried from `docs/research/P0-TECHNICAL-REFERENCE-CANDIDATES.md`) |
| Code license | AGPLv3 (open-source distribution); a separate proprietary/commercial license is also sold by the maintainers (per the project's own site) | FACT |
| Pretrained TensorFlow model zoo (separate from the AGPL C++/Python library) | Distributed by MTG/UPF under **CC BY-NC-ND 4.0** (Attribution, NonCommercial, NoDerivatives) for the open license track, with a proprietary license available on request | FACT (`https://essentia.upf.edu/licensing_information.html`) |
| Is copyrighted training/source audio redistributed? | Not evaluated this pass — no Essentia model was downloaded or run. | N/A this pass |
| **Benchmark verdict** | **`BENCHMARK_ONLY`** at best if ever executed (AGPLv3 code; any deep-learning model additionally under CC BY-NC-ND 4.0, which forbids production commercial use and forbids derivatives entirely) — consistent with the existing P0 decision. | — |
| **Production-evaluation verdict** | **`BLOCKED_ASSET_LICENSE`** for the pretrained TensorFlow models specifically (CC BY-NC-ND 4.0 categorically excludes commercial use and derivatives) **and** `BLOCKED_ASSET_LICENSE`-equivalent for the core library under AGPLv3 absent a purchased commercial license, unchanged from the standing P0 decision. | — |
| Execution status this pass | `SOURCE_ONLY_INSPECTED` for code/license research; **no install was attempted** — `pip index versions essentia` returned `ERROR: No matching distribution found for essentia` on this Windows x64 / Python 3.10 environment (no PyPI wheel), and a from-source build (custom `waf` build system, many native dependencies) was out of scope for this pass's time budget, consistent with the project's standing `REFERENCE_ONLY` decision for Essentia. | FACT (command + output) |

## 5. Cross-candidate pattern (worth flagging explicitly)

Both ML checkpoints actually evaluated for cue/structure-adjacent
capability whose upstream is fully inspectable (CUE-DETR, All-In-One)
share the **exact same license-gap shape**: a permissive (`MIT`) tag on
the *output weights*, trained on copyrighted commercial audio the
uploading organization does not itself redistribute and whose training-use
rights are not documented in either the code repo or the HF model/dataset
card. BeatNet sidesteps part of this by shipping under CC BY 4.0 end to
end (code and checkpoint under one license, at least), but still leaves
the specific training-corpus rights chain unaudited. **No candidate in
this pass has a checkpoint whose training-audio provenance is fully,
affirmatively documented as rights-cleared for commercial redistribution
of the resulting weights.** This is recorded as a standing
`UNKNOWN_NEEDS_LEGAL_REVIEW` item for any future production-adoption
decision (AGENTS.md rule 6: do not infer permissive rights from a
convenient tag).
