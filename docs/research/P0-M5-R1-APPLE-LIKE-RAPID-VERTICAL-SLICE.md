# P0-M5-R1 — Apple-Like AutoMix Rapid Vertical Slice + Real-Music Owner Gate

Status date: 2026-08-18 (repaired twice)

Binding task: GitHub Issue #10, executed after Issue #9's `OWNER_NG4_GROUND_TRUTH_REQUIRED` hold (PM comment `5322015325`) reaffirmed the original Apple-Music-AutoMix-like product target and authorized this closed-loop technical-route-reset task in its place. Issue #9's artifacts (the P0-M4-R2 narrow-fallback evidence) are unchanged and preserved.

## R0. Repair pass — binding PM review and scope

This document was repaired once, in the same session/branch, in response to PM review result `P0_M5_R1_PRELISTEN_REPAIR_REQUIRED` (Issue #10 comment `5322363724`), starting from the previously pushed HEAD `06b0ccacf6938000cedaba86076fa0534eb853e9` (verified live before this repair — §2). **No owner listening had begun**, so the original 8-pair set and listening ZIP were invalidated and rebuilt rather than patched around. The original `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` is renamed `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.INVALID_DO_NOT_RATE.zip` locally and must not be rated.

Four blockers, each traceable to its own PM finding:

- **BLOCKER 1** — `pair_discovery.py`'s local tempo used `downbeats_s` (a bar/downbeat event rate), not track beat tempo, so the direct-ratio-only rule could not actually exclude half/double-time mismatches — concretely, `RM089->RM018` was admitted at a coincidental bar-rate match (~31.25) while the tracks' real beat tempi are ~125 and ~63.83 BPM. Repaired: local tempo now comes from `beats_s`; `downbeats_s` is used only for bar-phase/boundary snapping; a new octave/half-time ambiguity guard rejects a local estimate that plausibly misreads a track's own cached `median_beat_bpm`. Pair discovery was rerun from the existing Beat This cache only (not re-analyzed) and the 8-pair set was refrozen.
- **Stretch-coverage requirement** (new, not a numbered blocker but bundled into this repair) — the original run's soft-ranking legitimately produced an 8/8 zero-correction set that never exercised the Signalsmith stretch path at all. Repaired: discovery now requires exactly 2 deterministic stretch-cover pairs (2–6% correction) plus 6 best near-native pairs, with at least one stretch-cover pair forced into holdout.
- **BLOCKER 2** — the Signalsmith worker's `tailPadS` safety/latency padding was left in the retained M1 program, inflating M1's overlap length relative to M0's. Repaired: `finish()` now trims to exactly the expected rate-converted duration and asserts it within a documented tolerance.
- **BLOCKER 3** — M1 sent every tail through Signalsmith, including unity-rate pairs, introducing an avoidable raw-vs-processed seam. Repaired: Signalsmith is bypassed entirely when `abs(rate-1.0) <= 0.001`; the raw tail is used directly.
- **BLOCKER 4** — the windowed edge-discontinuity proxy was wired as a hard failure, so the delivered `VALIDATION_OUTPUT.txt` showed `RESULT: 9 SAFETY FAILURE(S)` while the report still called the pack ready — a genuine self-contradiction. Repaired: the windowed proxy is now diagnostic-only; a new exact-splice hard check (single-sample delta at the true seam, normalized against a local baseline that excludes the seam itself) is the real hard gate. Applying it surfaced a genuine, previously-undetected defect (see §7) that is fixed below, not merely reclassified.

## R1. Repair pass 2 — binding PM re-review and scope

This document was repaired a second time, in the same session/branch, in response to PM re-review result `P0_M5_R1_PRELISTEN_REPAIR_2_REQUIRED` (Issue #10 comment `5322996856`), starting from the previously pushed HEAD `eaa70a20854c10f2a2cc5d6fa41e8eb958d48ed6` (verified live before this repair — §2). PM's re-review provisionally **accepted** every finding from repair pass 1 (BLOCKER 1/2/3/4, stretch coverage) and found two NEW, narrower defects, one introduced by repair pass 1 itself and one exposed by re-review. **Again, no owner listening had begun**, so the repair-pass-1 owner ZIP (SHA-256 `f5e740...`) is also invalidated. It is renamed locally to `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.INVALID_DO_NOT_RATE.2.zip` (the original pass's ZIP remains `...INVALID_DO_NOT_RATE.zip`; neither must be rated).

- **BLOCKER A (introduced by repair 1's own micro-splice fix)** — `micro_splice_fade` blended `outgoing_pre`'s own already-emitted last ~10ms against the processed tail's first ~10ms. Since `render_m1` still emitted the FULL, unshortened `outgoing_pre` immediately before that blend, the same ~10ms source interval was audible twice — once raw, once blended — a real program-timeline rewind/duplication, even though the amplitude seam itself was smooth (equal-power gains hid a timeline defect, they did not fix one). Repaired: the blend now uses the window's OWN leading raw content (`out_audio[exit_smp : exit_smp + raw_lead_input_smp]`, i.e. the same forward-time interval the processed head represents), never a reused already-played sample. A new deterministic synthetic verifier (`verify_micro_splice.py`, 11/11 checks) proves no pre-seam interval is replayed and program chronology stays monotonic.
- **BLOCKER B (pre-existing, exposed by re-review)** — the outgoing exit downbeat snap allowed up to a 45-second forward-or-backward search, which could (and for `RM099->RM071` did) pull a complex-mix transition more than 15 seconds *earlier* than the cached R2 late/natural exit whenever Beat This had no later usable downbeat — violating the preservation-first "near the selected late/natural region" contract. Repaired: the snap is now bounded to `min(4 local bars, 10 seconds)`, computed from already-cached evidence; a pair with no downbeat inside that bounded neighborhood fails closed to `NO_USABLE_DOWNBEAT_NEAR_EXIT_CANDIDATE` instead of reaching further afield. Pair discovery was rerun from the existing Beat This cache only — `RM099->RM071` is no longer eligible (replaced by `RM089->RM020` in the refrozen 8).

## 0. Execution profile actually used

- **Execution surface:** Claude Desktop → Code.
- **Model:** `claude-sonnet-5`. **Reasoning effort:** High.
- **Extended thinking:** ON. **Dynamic workflows:** OFF. **Sub-agents:** OFF. **Fallback:** NONE.

## 1. Result

**`OWNER_APPLE_LIKE_LISTENING_REQUIRED`** (repaired twice) — Phases A–F are complete and the repaired pack genuinely passes all hard safety checks (verifier exit code 0, independently re-run), the micro-splice timeline defect is fixed and mechanically verified, and the exit-anchor snap is now bounded. A valid, machine-verified, local-only blinded owner listening pack (`P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip`, 8 scenarios x 2 methods = 16 real-music mixed WAV clips, a THIRD new blind seed) has been built. Owner ratings have **not** been collected. The Post-Rating Route Gate is **not** evaluated in this pass. P1 has not started.

## 2. Live-state verification

| Check | Value |
|---|---|
| Branch | `research/p0-feasibility` |
| HEAD at original-pass session start | `4c0cc7c6b1d3fa3c9b8174cbb966a876c0493234` — matched Issue #10's expected HEAD exactly |
| HEAD at repair-pass-1 session start | `06b0ccacf6938000cedaba86076fa0534eb853e9` — matched that repair task's expected HEAD exactly |
| HEAD at repair-pass-2 session start | `eaa70a20854c10f2a2cc5d6fa41e8eb958d48ed6` — matched this repair task's expected HEAD exactly |
| `main` | `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` — untouched (all three passes) |

Issue #9 hold comments `5322015325` (direction correction) and `5322071131` (supersession pointer to this issue) were fetched and read in full via `gh api` (original pass). Issue #10 PM review comments `5322363724` (`P0_M5_R1_PRELISTEN_REPAIR_REQUIRED`, repair 1) and `5322996856` (`P0_M5_R1_PRELISTEN_REPAIR_2_REQUIRED`, repair 2) were fetched and read in full.

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

## 5. Phase C — deterministic positive-pair discovery (repaired twice)

Scored all 9,900 ordered pairs from the 100-track corpus using only already-cached evidence (`corpus_analysis.local.json`'s Stage-B fields + the existing Beat This cache from the original pass — **not re-analyzed by either repair**). No manual song selection; no listening-outcome feedback.

- **Eligible pairs found: 247** (down from repair 1's 260, since BLOCKER B's bounded neighborhood is strictly stricter: 8,415 failed `EXIT_STRUCTURE_CONFIDENCE_BELOW_MEDIUM`, 1,028 failed `TEMPO_CORRECTION_EXCEEDS_6PCT`, 111 failed `LOCAL_TEMPO_OCTAVE_AMBIGUITY`, and **99 pairs were newly and correctly rejected by the new bounded exit-downbeat neighborhood** — direct, mechanical proof the BLOCKER B fix is live and doing real work).
- **Stretch-cover candidates found: 161** (correction in [2%, 6%]) — comfortably above the required minimum of 2.
- **Frozen exactly 8 pairs: 2 stretch-cover + 6 near-native, 6 dev / 2 holdout, 1 of the 2 stretch-cover pairs in holdout** — `RM055->RM052` (dev) and `RM055->RM047` (holdout), both at 3.12% tempo correction (unchanged from repair 1, still eligible under the bounded neighborhood); the 6 near-native pairs at 0.0% correction. **`RM099->RM071` (the pair PM cited as pulled 15.7s early) is gone**, replaced by `RM089->RM020`. Every remaining pair's exit-snap delta is now small and forward (0.4–4.5s), spot-checked directly against the frozen manifest.

The repair also **caught its own motivating examples**: `RM089->RM018` (repair 1's cited defect) remains ineligible, and `RM099->RM071` (repair 2's cited defect) is now also ineligible — both absent from the twice-refrozen 8.

## 6. Phase D — M0/M1 render (repaired twice)

For each of the 8 (twice-refrozen) pairs, rendered both methods from the **same** source pair and the **same** broad transition region:

- **M0** (baseline): equal-power crossfade at the pair's *raw, un-snapped* R2 candidate boundary — no beat/downbeat alignment, no stretch, no bass handoff. Unchanged by either repair.
- **M1** (`APPLE_LIKE_V1`): outgoing tail (an integer number of bars, sized from a genuine bar-period-in-seconds field, 8–16s window) stretched via the browser Signalsmith bridge to the pair's cached tempo ratio, starting exactly at a Beat-This-snapped outgoing downbeat (now bounded, BLOCKER B) — **only when the pair actually needs correction** (BLOCKER 3: Signalsmith is bypassed entirely at `|rate-1.0| <= 0.001`, using the raw tail directly); incoming overlap taken **unstretched** at its own snapped downbeat; equal-power gain **with** the existing accepted bass-handoff EQ swap; incoming continues at native tempo after the overlap; the internal raw-pre-roll/processed-tail seam is now blended (BLOCKER A, corrected, see §7).

**8/8 M0 and 8/8 M1 scenarios rendered successfully; the same 2/8 scenarios (S01/S02) actually exercised the Signalsmith stretch path** (`rate=0.9688`, a genuine 3.12% correction) — the remaining 6 correctly bypass Signalsmith. Clip durations 32.96–34.59s.

## 7. Phase E — machine safety/contract checks (repaired twice)

- **NaN/Inf: 0 across all 16 clips. Uncontrolled clipping: 0 across all 16 clips. Format (44100Hz/stereo): correct on all 16.**
- **BLOCKER 4 (repair 1) remains in effect:** the windowed edge proxy is diagnostic-only, contributing zero to the failure list (9 non-blocking warnings this run).
- **BLOCKER A (repair 2) — a real timeline defect introduced by repair 1's own micro-splice fix, now fixed:** `micro_splice_fade` previously blended `outgoing_pre`'s own already-emitted last ~10ms against the processed tail's first ~10ms, while `render_m1` still emitted the full unshortened `outgoing_pre` immediately before it — the same ~10ms interval played twice (once raw, once blended), a genuine chronology rewind the exact-splice amplitude check could not detect (a smooth amplitude seam does not imply correct timeline order). **Fixed:** the blend now uses the window's own leading RAW content (`out_audio[exit_smp : exit_smp + raw_lead_input_smp]`, the SAME forward-time interval the processed head represents) — never a reused already-played sample; `outgoing_pre` is untouched. As a direct side effect, the exact-splice z-scores at the two real stretch pairs' seam *improved further* (S01/S02 M1 edge1: `z≈1.42` in repair 1 → `z≈0.29` in repair 2), since the blend now genuinely matches the correct forward-time content instead of a mistimed one.
- **Final verifier run: genuinely exits 0** — `RESULT: ALL 16 CLIPS PASS SAFETY CHECKS (0 hard failures, 9 non-blocking diagnostic warnings)`, independently re-run and confirmed, not merely asserted in prose.

## 7.1 Regression / new-verifier note

- `verify_pair_discovery.py` (20/20 checks, extended this pass) proves both BLOCKER 1 (repair 1) and BLOCKER B (repair 2) mechanically against synthetic data: the PM-cited `125 vs 63.83 BPM` scenario is rejected; the octave-ambiguity guard fires/doesn't-fire correctly; the bounded exit-downbeat neighborhood reproduces the `RM099->RM071` shape (only a far backward downbeat available) and correctly fails closed instead of snapping ~15s backward; the 4-bar/10s cap is independently checked at both a fast and a slow synthetic tempo.
- `verify_micro_splice.py` (new this pass, 11/11 checks) proves BLOCKER A mechanically: using a synthetic forward-time-index ramp signal, it proves `raw_lead` is read from the window's own leading edge (never the already-emitted `outgoing_pre` tail), that the blend source continues monotonically forward from `outgoing_pre`'s last emitted sample, that both the raw and processed operands genuinely contribute to the blend (not silently ignoring one), and that post-fade content is untouched.

## 8. Phase F — blinded owner listening pack (rebuilt again, THIRD blind seed)

Both prior owner ZIPs are invalid and must not be rated: the original pass's `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` (renamed `...INVALID_DO_NOT_RATE.zip`) and repair 1's rebuild, SHA-256 `f5e740...` (renamed `...INVALID_DO_NOT_RATE.2.zip`).

New `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` (local-only, never committed), built from the twice-repaired render set:

- Exactly **8 scenarios x 2 blinded methods = 16 real-music mixed WAV clips**, named `S01-A.wav` .. `S08-B.wav` (blind tokens only).
- Which letter (A/B) is M0 vs M1 is randomized **independently per scenario** using a **THIRD, brand new** frozen 64-bit random seed (both prior seeds are discarded along with their invalid packs).
- `LISTENING_INSTRUCTIONS.md` and `OWNER_RATINGS_TEMPLATE.json` (8-scenario rows, all 9 fields per Issue #10 Phase F).
- Zero exposure of method names, opaque track IDs, dev/holdout labels, filenames/titles/artists, or the blind key — verified both structurally (`verify_owner_pack.py`, 20/20 checks) and via a direct regex scan of the built ZIP's filenames and text contents (zero hits).
- ZIP: 18 members (16 clips + 2 docs), SHA-256/size reported in the handoff.

## 9. Privacy audit

- All tracked source/evidence files (12 files under `tools/p0m5/apple_like_vertical_slice/`, excluding `work_local/`) scanned for path-like strings: zero hits.
- The owner-listening ZIP scanned for method names/opaque IDs/split labels/blind-key filename: zero hits.
- `id_map.local.json`, `corpus_analysis.local.json`, the Beat This checkpoint cache, decoded audio, all rendered clips, and the owner pack's blind key all live under gitignored `work_local/` trees (this task's own new `.gitignore`, plus the pre-existing repo-root `*.wav` rule).
- Vendored third-party repos (`beat_this`, `SongFormer`) live under `work_local/vendor/` — never committed.

## 10. Verifier / validation results

```
python tools/p0m5/apple_like_vertical_slice/verify_pair_discovery.py ...        -> 20/20 PASS (extended this pass, BLOCKER 1 + BLOCKER B)
python tools/p0m5/apple_like_vertical_slice/verify_micro_splice.py ...          -> 11/11 PASS (NEW this pass, BLOCKER A)
python tools/p0m5/apple_like_vertical_slice/pair_discovery.py ...               -> 247 eligible (99 newly rejected: bounded exit-downbeat neighborhood), 161 stretch-cover candidates, 8 FROZEN (6 dev/2 holdout, 2 stretch-cover/1 holdout) -- deterministic, byte-identical on rerun
python tools/p0m5/apple_like_vertical_slice/apple_like_render.py prepare/finish -> 8/8 M0 + 8/8 M1 SUCCESS, 2/8 with real Signalsmith stretch applied
python tools/p0m5/apple_like_vertical_slice/safety_checks.py ...                -> RESULT: ALL 16 CLIPS PASS SAFETY CHECKS (0 hard failures, 9 non-blocking diagnostic warnings) -- exit code 0, independently re-run
python tools/p0m5/apple_like_vertical_slice/verify_owner_pack.py ...            -> 20/20 PASS
```

## 11. Tracked deliverables (this task)

- `tools/p0m5/apple_like_vertical_slice/.gitignore` — private/local-only artifact exclusion.
- `beat_this_runtime.py` — isolated Beat This runtime wrapper (no vendored model code committed).
- `corpus_beat_analysis.py` — Phase B corpus analysis harness.
- `beat_analysis_aggregate_sanitized.json` — sanitized per-track Beat This summary (opaque IDs + counts/scalars only).
- `pair_discovery.py` — Phase C deterministic positive-pair discovery; **repaired twice** (repair 1: beat-tempo-based eligibility, octave-ambiguity guard, stretch-coverage selection; repair 2: bounded exit-downbeat neighborhood, BLOCKER B).
- `verify_pair_discovery.py` — synthetic unit checks; **extended this pass** to 20 checks (BLOCKER 1 + BLOCKER B).
- `pair_manifest_sanitized.json` — the frozen 8-pair manifest (opaque IDs, anchors, tempo/harmonic/energy evidence); **refrozen again this pass.**
- `apple_like_render.py` — Phase D M0/M1 renderer; **repaired twice** (repair 1: tail-pad trim + latency compensation + micro-splice-fade; repair 2: micro-splice-fade timeline fix, BLOCKER A).
- `verify_micro_splice.py` — **new this pass.** Synthetic timeline-chronology checks proving the BLOCKER A fix (11 checks).
- `render_evidence_sanitized.json` — sanitized per-scenario render evidence (overlap/tempo/safety numbers, opaque IDs); **regenerated this pass.**
- `safety_checks.py` — Phase E safety/click-proxy verifier; repaired in repair 1 (exact-splice hard check, windowed proxy demoted to diagnostic-only); unchanged logic this pass, rerun against the twice-repaired renders.
- `safety_checks_sanitized.json` — sanitized per-clip safety evidence; **regenerated this pass, genuinely 0 hard failures, exact-splice z-scores improved further.**
- `build_owner_pack.py` — Phase F blinded pack builder.
- `verify_owner_pack.py` — Phase F pack verifier.
- This report.

## 12. Local-only artifacts (never committed)

- `work_local/vendor/{beat_this,SongFormer}` — cloned pinned third-party repos.
- `work_local/pylibs`, `work_local/torch_cache` — isolated dependency/checkpoint caches.
- `work_local/decoded` — decoded canonical WAVs for the 100-track corpus.
- `work_local/beat_cache` — full per-track beat/downbeat timing arrays.
- `work_local/renders` — the 16 final M0/M1 WAV clips (source for the owner pack); **regenerated this pass.**
- `work_local/owner_pack` — the owner-pack staging directory including `blind_key.local.json` (THIRD new seed, this pass).
- `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` (repo root) — the twice-repaired owner-facing pack.
- `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.INVALID_DO_NOT_RATE.zip` (repo root) — the original pass's pack, invalidated, must not be rated.
- `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.INVALID_DO_NOT_RATE.2.zip` (repo root) — repair 1's rebuilt pack (SHA-256 `f5e740...`), also invalidated by repair 2, must not be rated.

## 13. What must happen next

1. **Owner checkpoint (this task's stop point):** the project owner listens to `P0-M5-R1-APPLE-LIKE-OWNER-LISTENING.zip` per its `LISTENING_INSTRUCTIONS.md` and fills in `OWNER_RATINGS_TEMPLATE.json`.
2. A future session continues the **same** task from the frozen 8-pair set and blind key (no regeneration unless PM finds a deterministic defect), evaluates the Post-Rating Route Gate exactly as Issue #10 defines it, and returns one of `APPLE_LIKE_ROUTE_RECOVERED` / `APPLE_LIKE_ROUTE_REPAIRABLE` (at most one repair iteration) / `APPLE_LIKE_ROUTE_REJECTED`.
3. P1 must not start inside this issue regardless of outcome.

---

P1 NOT STARTED. POST-RATING ROUTE GATE NOT EVALUATED. HANDOFF TO PM.
