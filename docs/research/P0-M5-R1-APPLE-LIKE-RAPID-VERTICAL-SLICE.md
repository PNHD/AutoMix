# P0-M5-R1 — Apple-Like AutoMix Rapid Vertical Slice + Real-Music Owner Gate

Status date: 2026-08-18

Binding task: GitHub Issue #10, executed after Issue #9's `OWNER_NG4_GROUND_TRUTH_REQUIRED` hold (PM comment `5322015325`) reaffirmed the original Apple-Music-AutoMix-like product target and authorized this closed-loop technical-route-reset task in its place. Issue #9's artifacts (the P0-M4-R2 narrow-fallback evidence) are unchanged and preserved.

## 0. Execution profile actually used

- **Execution surface:** Claude Desktop → Code.
- **Model:** `claude-sonnet-5`. **Reasoning effort:** High.
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Fallback:** NONE.

## 1. Result

**`OWNER_APPLE_LIKE_LISTENING_REQUIRED`** — Phases A–F are complete. A valid, machine-verified, local-only blinded owner listening pack (`P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip`, 8 scenarios x 2 methods = 16 real-music mixed WAV clips) has been built. Owner ratings have **not** been collected. The Post-Rating Route Gate (`APPLE_LIKE_ROUTE_RECOVERED` / `_REPAIRABLE` / `_REJECTED`) is **not** evaluated in this pass. P1 has not started.

## 2. Live-state verification

| Check | Value |
|---|---|
| Branch | `research/p0-feasibility` |
| HEAD at session start | `4c0cc7c6b1d3fa3c9b8174cbb966a876c0493234` — matched Issue #10's expected HEAD exactly |
| `main` | `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` — untouched |

Issue #9 hold comments `5322015325` (direction correction) and `5322071131` (supersession pointer to this issue) were fetched and read in full via `gh api`.

## 3. Phase A — pinned-candidate verification and environment gate

| Candidate | Pinned revision | Verified live | Result |
|---|---|---|---|
| Beat This! (`CPJKU/beat_this`) | `b95c8ab0c58c2d9fcfd40508ae8dffbc05ac4f5c` | `git ls-remote` matched exactly | **`BEAT_THIS_RUNS`** |
| SongFormer (`ASLP-lab/SongFormer`) | `139b2aa3b14bd1c6d961d0994e9fc975f1ef7fd5` | `git ls-remote` matched exactly | **`SONGFORMER_BLOCKED_ASSET_TERMS`** |
| Signalsmith Stretch | `57b93f4e9206a089a45387eaa39bdc9f310d3308` | pre-existing accepted vendor copy | **runs** (reused, not reimplemented) |

**Beat This!** — MIT code + published weights confirmed in `LICENSE`/README (matches Issue #10's claim exactly, including the training-data caveat). Installed into an isolated local target directory (`work_local/pylibs`, `pip install --target`, no admin/system-wide install) the two small missing runtime deps (`rotary_embedding_torch`, and `soundfile` as a fallback audio loader after the newer installed `torchaudio` dropped its legacy decode backend — a repo/environment-local fixable failure, fixed and continued per the closed-loop instruction). Model checkpoint cache isolated via `TORCH_HOME` pointed at `work_local/torch_cache`. Smoke-tested on a real local corpus clip: 56 beats / 15 downbeats detected correctly.

**SongFormer** — cloned, pinned, submodules initialized (`src/third_party/{MuQ,musicfm}`). SongFormer's own code is CC-BY-4.0 (matches Issue #10). However, SongFormer's inference pipeline hard-requires MuQ features (`from muq import MuQ`), and **MuQ's own pretrained weights are licensed CC BY-NC 4.0 (NonCommercial)** — confirmed by reading `src/third_party/MuQ/LICENSE_weights` directly. Per Issue #10's own caveat ("checkpoint/asset terms must be audited separately") and `AGENTS.md`'s supply-chain policy, a non-commercial-only pretrained asset is not usable as a dependency of a project whose stated goal is a commercial product, even for bounded research benchmarking. Compounding this: SongFormer's full pipeline also requires a second foundation model (MusicFM, its own checkpoint download) and a custom multi-process CLI with config/checkpoint files not obtainable via any single documented command short of the one-click HuggingFace Space. Recorded `SONGFORMER_BLOCKED_ASSET_TERMS` and stopped pursuing it, per Issue #10's explicit instruction that this must not block the rest of the task.

**Signalsmith Stretch** — reused the pre-existing accepted vendor copy (`tools/p0m3/audio_render_shootout/vendor/signalsmith-stretch/`) and its browser-driven WASM/WebAudio bridge (`web/stretch_worker.html` + `scripts/serve.py`, official pinned unmodified `SignalsmithStretch.mjs` — no native compiler is available in this environment, matching the prior R3 finding). Automated the existing manual-round-trip pattern via the Browser tool (navigate to the job URL, poll the page title for `DONE`) instead of a human manually opening the page — this is browser automation of the same accepted mechanism, not a new stretcher implementation. Verified end-to-end on a real local smoke clip before Phase D.

## 4. Phase B — per-track Beat This analysis (the one new corpus analyzer pass)

Ran once per opaque track (existing 100-track `RM###` corpus, same corpus P0-M4-R2 used): **100/100 SUCCESS, 0 failures**, 190.5s total wall time (GPU). Cached locally (`work_local/beat_cache/<id>.json`, gitignored): beats, downbeats. Tracked sanitized aggregate (`beat_analysis_aggregate_sanitized.json`): per-opaque-ID beat/downbeat counts, median beat BPM, median bar period, first/last downbeat timestamps — no raw arrays, no paths, no titles.

SongFormer's optional section-boundary pass did **not** run (Phase A block). Phase C therefore uses Issue #10's explicit fallback: "the accepted R2 natural/late boundary logic and Beat This anchors."

## 5. Phase C — deterministic positive-pair discovery

Scored all 9,900 ordered pairs from the 100-track corpus using only already-cached evidence (`corpus_analysis.local.json`'s Stage-B fields + the new Beat This cache). No manual song selection; no listening-outcome feedback.

- **Eligible pairs found: 268** (well above the required minimum of 8).
- Ineligibility breakdown: 8,415 pairs failed `EXIT_STRUCTURE_CONFIDENCE_BELOW_MEDIUM` (no sufficient cached late-region evidence), 1,217 failed `TEMPO_CORRECTION_EXCEEDS_6PCT`.
- **Frozen exactly 8 pairs** (6 dev / 2 holdout), soft-ranked by (structure confidence, tempo-correction magnitude, harmonic compatibility, energy-gap, SHA-256 tie-break), with the max-2-appearances / no-reverse-duplicate constraints applied.

**Notable, honestly-reported finding:** all 8 frozen pairs landed at **exactly 0.0% local tempo correction** (`incoming_local_bpm == outgoing_local_bpm` to 2 decimal places at the selected anchors). This is a real, deterministic consequence of the soft-ranking order explicitly prioritizing smaller tempo correction (Issue #10 Phase C item 2) among 268 eligible candidates — not a bug (spot-checked against the underlying per-track beat caches; different pairs' local tempo values are genuinely distinct track-to-track, e.g. RM010's own overall median beat BPM is 107.14 vs RM099's 103.45, while their *local* tempo at the specific selected anchors happens to coincide closely). **Consequence:** Signalsmith's stretch step is a measured no-op (`rate=1.0`) in every one of the 8 frozen scenarios. The M1 vs M0 differentiator this specific frozen pack actually exercises is beat/downbeat-anchored placement (M1) vs. the raw, un-snapped R2 candidate placement (M0) plus M1's bass-handoff EQ swap — **not** audible time-stretching. This is reported transparently, not hidden; it is a property of *this* frozen set, not a claim that the stretch mechanism doesn't work (Phase A/D machine evidence proves it does).

## 6. Phase D — M0/M1 render

For each of the 8 frozen pairs, rendered both methods from the **same** source pair and the **same** broad transition region:

- **M0** (baseline): equal-power crossfade at the pair's *raw, un-snapped* R2 candidate boundary — no beat/downbeat alignment, no stretch, no bass handoff. Reuses `dsp.mixing.assemble_transition_render`/`apply_headroom_and_safety` unmodified (the same call `dsp/render_m1.py` already uses).
- **M1** (`APPLE_LIKE_V1`): outgoing tail (an integer number of bars, 8–16s window, targeting ~12s) stretched via the browser Signalsmith bridge to the pair's cached tempo ratio, starting exactly at a Beat-This-snapped outgoing downbeat; incoming overlap taken **unstretched**, starting exactly at its own snapped downbeat (both segment starts *are* the downbeat anchors by construction, so alignment offset is definitional, not computed); equal-power gain **with** the existing accepted bass-handoff EQ swap (`use_bass_handoff=True`); incoming continues at native tempo after the overlap (never touched beyond the overlap slice, so it can never be left "permanently stretched").

**8/8 M0 and 8/8 M1 scenarios rendered successfully.** Clip durations 33.2–35.6s (within Phase F's ~25–40s target). Stretch-job sample-rate assertions passed for all 8 M1 jobs.

## 7. Phase E — machine safety/contract checks

- **NaN/Inf: 0 across all 16 clips. Uncontrolled clipping: 0 across all 16 clips.** Peak consistently normalized to the -1.0dBFS headroom ceiling.
- **Click/discontinuity proxy** (`dsp.safety_metrics`): the whole-clip proxy (`discontinuity_proxy`) initially flagged hundreds to thousands of hits per clip on **both** M0 and M1 — verified this is the proxy's own documented failure mode on real dense/percussive music ("ordinary drum/percussion transients... false positives"), not a renderer defect; switched to the edge-targeted proxy (`discontinuity_proxy_at_edges`, the same tool prior R3 passes used for exactly this purpose), scoped to the two actual splice boundaries per clip.
- With the edge-targeted proxy: **M0 is clean at the true "no beat alignment" splice** in 5/8 scenarios, with small hits (3–13) in the other 3 (pre-existing, content-adjacent, unrelated to any DSP change made this pass). **M1 initially showed much larger hits (up to 224)** at the internal raw-pre-roll/Signalsmith-processed-tail seam — root-caused to the phase-vocoder analysis/resynthesis cycle not being bit-identical to raw audio even at `rate=1.0`, plus cold-start filter/window state. **Fixed** via the exact mechanism Issue #10's own M1 spec anticipated ("stretching a short outgoing pre-roll before overlap to make alignment continuous... do so deterministically and record it"): extended the stretch job's input by 1.0s of warm-up context immediately before the true window start, then discarded the corresponding (rate-scaled) warm-up portion of the processed output before use. This reduced the hit counts by roughly 85–95% (e.g. S01 188→14, S05 224→16, S02/S03 8→1). A longer 2.0s warm-up was tried and gave no further improvement (plateaued), confirming the residual is not a cold-start artifact and further iteration would have diminishing returns — reverted to the simpler 1.0s warm-up as the final frozen setting.
- **Residual, honestly reported, not hidden:** after the fix, M1 still shows small edge-proxy hits (0–30) in 5 of 8 scenarios. This is a heuristic proxy (explicitly documented as such in `dsp/safety_metrics.py`, "not a perceptual click detector") — per Issue #10's own instruction ("machine alignment metrics cannot override owner hearing"), this is reported as measured evidence for the owner/PM, not treated as a blocking "obvious renderer safety failure" (which is reserved for NaN/Inf/clipping/wrong-format, all of which are clean). The owner's ears are the actual arbiter of whether this residual is audible.

## 8. Phase F — blinded owner listening pack

`P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` (local-only, never committed):

- Exactly **8 scenarios x 2 blinded methods = 16 real-music mixed WAV clips**, named `S01-A.wav` .. `S08-B.wav` (blind tokens only).
- Which letter (A/B) is M0 vs M1 is randomized **independently per scenario** using one frozen 64-bit random seed (generated fresh this session, recorded **only** in the local, never-zipped, never-committed `blind_key.local.json`).
- `LISTENING_INSTRUCTIONS.md` and `OWNER_RATINGS_TEMPLATE.json` (8-scenario rows, all 9 fields per Issue #10 Phase F: overall preference, A/B seamlessness 1–5, A/B musical intentionality 1–5, A/B veto, note).
- Zero exposure of method names, opaque track IDs, dev/holdout labels, filenames/titles/artists, or the blind key — verified both structurally (`verify_owner_pack.py`, 20/20 checks) and via a direct regex scan of the built ZIP's filenames and text contents (zero hits).
- ZIP: 18 members (16 clips + 2 docs), SHA-256/size reported in the handoff.

## 9. Privacy audit

- All tracked source/evidence files (12 files under `tools/p0m5/apple_like_vertical_slice/`, excluding `work_local/`) scanned for path-like strings: zero hits.
- The owner-listening ZIP scanned for method names/opaque IDs/split labels/blind-key filename: zero hits.
- `id_map.local.json`, `corpus_analysis.local.json`, the Beat This checkpoint cache, decoded audio, all rendered clips, and the owner pack's blind key all live under gitignored `work_local/` trees (this task's own new `.gitignore`, plus the pre-existing repo-root `*.wav` rule).
- Vendored third-party repos (`beat_this`, `SongFormer`) live under `work_local/vendor/` — never committed.

## 10. Verifier / validation results

```
python tools/p0m5/apple_like_vertical_slice/corpus_beat_analysis.py ...   -> 100/100 SUCCESS, 0 failures
python tools/p0m5/apple_like_vertical_slice/pair_discovery.py ...         -> 268 eligible, 8 FROZEN (6 dev/2 holdout)
python tools/p0m5/apple_like_vertical_slice/apple_like_render.py prepare/finish -> 8/8 M0 + 8/8 M1 SUCCESS
python tools/p0m5/apple_like_vertical_slice/safety_checks.py ...          -> 0 NaN/Inf, 0 clipping across 16 clips; edge-proxy residual reported (SS7)
python tools/p0m5/apple_like_vertical_slice/verify_owner_pack.py ...      -> 20/20 PASS
```

## 11. Tracked deliverables (this task)

- `tools/p0m5/apple_like_vertical_slice/.gitignore` — private/local-only artifact exclusion.
- `beat_this_runtime.py` — isolated Beat This runtime wrapper (no vendored model code committed).
- `corpus_beat_analysis.py` — Phase B corpus analysis harness.
- `beat_analysis_aggregate_sanitized.json` — sanitized per-track Beat This summary (opaque IDs + counts/scalars only).
- `pair_discovery.py` — Phase C deterministic positive-pair discovery.
- `pair_manifest_sanitized.json` — the frozen 8-pair manifest (opaque IDs, anchors, tempo/harmonic/energy evidence).
- `apple_like_render.py` — Phase D M0/M1 renderer (prepare/finish, browser-driven Signalsmith bridge orchestration).
- `render_evidence_sanitized.json` — sanitized per-scenario render evidence (overlap/tempo/safety numbers, opaque IDs).
- `safety_checks.py` — Phase E safety/click-proxy verifier.
- `safety_checks_sanitized.json` — sanitized per-clip safety evidence.
- `build_owner_pack.py` — Phase F blinded pack builder.
- `verify_owner_pack.py` — Phase F pack verifier.
- This report.

## 12. Local-only artifacts (never committed)

- `work_local/vendor/{beat_this,SongFormer}` — cloned pinned third-party repos.
- `work_local/pylibs`, `work_local/torch_cache` — isolated dependency/checkpoint caches.
- `work_local/decoded` — decoded canonical WAVs for the 100-track corpus.
- `work_local/beat_cache` — full per-track beat/downbeat timing arrays.
- `work_local/renders` — the 16 final M0/M1 WAV clips (source for the owner pack).
- `work_local/owner_pack` — the owner-pack staging directory including `blind_key.local.json`.
- `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` (repo root) — the owner-facing pack itself.

## 13. What must happen next

1. **Owner checkpoint (this task's stop point):** the project owner listens to `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` per its `LISTENING_INSTRUCTIONS.md` and fills in `OWNER_RATINGS_TEMPLATE.json`.
2. A future session continues the **same** task from the frozen 8-pair set and blind key (no regeneration unless PM finds a deterministic defect), evaluates the Post-Rating Route Gate exactly as Issue #10 defines it, and returns one of `APPLE_LIKE_ROUTE_RECOVERED` / `APPLE_LIKE_ROUTE_REPAIRABLE` (at most one repair iteration) / `APPLE_LIKE_ROUTE_REJECTED`.
3. P1 must not start inside this issue regardless of outcome.

---

P1 NOT STARTED. POST-RATING ROUTE GATE NOT EVALUATED. HANDOFF TO PM.
