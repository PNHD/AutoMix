## HANDOFF TO PM — P0-M3-R3 REAL-MUSIC STAGE B PACK

### RESULT
`OWNER_REAL_MUSIC_LISTENING_REQUIRED`

All three required real-vocal validation categories (V1/V2/V3) were
transparently selected from the full 100-track authorized corpus and
rendered successfully. **This is NOT a quality PASS** — owner blinded
listening is required before any quality verdict. P1 has not started.

### REPO / BRANCH / HEAD
`PNHD/AutoMix`, branch `research/p0-feasibility`.
Starting accepted baseline: `ac9b2acf6571241e5810f29280c021cf8fcb3b9c` (unchanged going into this pass).
HEAD after this pass: **see commit created immediately after this handoff is pushed** (`git log -1` on `origin/research/p0-feasibility`). `main` untouched.

### FILES CREATED
- `tools/p0m3/audio_render_shootout/scripts/analyze_owner_corpus.py` — from-scratch numpy/scipy corpus analyzer (tempo/beat/downbeat/key/loudness/vocal-density-proxy/intro-outro).
- `tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py` — transparent V1/V2/V3 pair selection using the real R2 `evaluate_pair_compatibility`.
- `tools/p0m3/audio_render_shootout/scripts/real_music_signalsmith.py` — owner-facing Signalsmith Stretch prepare/finish adapter for real-music pairs (browser round-trip, mirrors `dsp/render_m2_signalsmith.py`).
- `tools/p0m3/audio_render_shootout/scripts/build_real_music_owner_pack.py` — blinded owner listening pack builder (new seed, opaque filenames).
- `tools/p0m3/audio_render_shootout/scripts/build_real_music_pm_pack.py` — sanitized PM evidence pack builder (no audio).
- `tools/p0m3/audio_render_shootout/scripts/verify_real_music_stage_b.py` — consolidated validation.
- `docs/research/P0-M3-R3-REAL-MUSIC-STAGE-B.md` — sanitized methodology + aggregate results.
- `P0-M3-R3-REAL-MUSIC-OWNER-LISTENING.zip` (LOCAL ONLY, not committed).
- `P0-M3-R3-REAL-MUSIC-PM-REVIEW.zip` (LOCAL ONLY, not committed).

No source audio, derived listening WAVs, filenames, paths, hashes, or tags from the private corpus were committed anywhere.

### CORPUS AGGREGATE INVENTORY (sanitized — no filenames)
```
tracks analyzed:             100 / 100 (0 failures)
tempo (BPM):                 min 69.8, median 112.3, max 172.3
beat confidence:              HIGH 89, MEDIUM 11
downbeat confidence:          HIGH 28, MEDIUM 36, LOW 19, NONE 17
key confidence (whole-track): HIGH 35, MEDIUM 16, LOW 21, NONE 28
detected instrumental outro tail: 5 / 100
detected leading-silence skip:    24 / 100
```
Full methodology in `docs/research/P0-M3-R3-REAL-MUSIC-STAGE-B.md` §2 (every estimator explicitly labeled with its confidence-derivation method; vocal-density is HEURISTIC_PROXY — no source-separation model was available in this environment).

### ANALYZER AVAILABILITY / CONFIDENCE
No trained ML beat/vocal/key model was available in this environment (consistent with `docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md`). All estimators are from-scratch numpy/scipy DSP (spectral-flux onset + autocorrelation tempo, comb-filter beat phase, z-scored dual-band-ensemble downbeat phase, Krumhansl-Schmuckler key correlation with whole-track/boundary-local corroboration, percentile-based vocal-density-proxy risk). Confidence thresholds were calibrated against this corpus's own observed statistic distributions before selection (not tuned per-pair afterward) — see doc §2 for the specific recalibration reasoning (e.g. the naive first-pass downbeat detector using kick-band energy alone showed near-zero group separation on this corpus's four-on-the-floor material; the accepted estimator combines two independent onset signals).

### V1/V2/V3 SELECTION RATIONALE (opaque IDs only)
Exhaustive search over ~9,900 ordered pairs using the REAL, unmodified `evaluate_pair_compatibility` (`tools/p0m3/transition_policy/policy/compatibility.py`) — no separately-invented rule, no cherry-picking after rendering.

- **V1** (`close_tempo_minimal_stretch`): pool=620 candidates (≤2% tempo deviation). Selected: 0.0% deviation, `HARMONIC_COMPATIBLE`, beat confidence HIGH both sides.
- **V2** (`conditional_tempo_correction`): pool=**2** candidates clearing every FULL_DJ_BLEND hard gate AND in the 3–6% zone. Selected: 4.17% required deviation, beat+downbeat confidence HIGH both sides, `HARMONIC_COMPATIBLE` (perfect-fourth relation, corroborated across independent measurement windows).
- **V3** (`incompatible_downgrade`): pool=6,801 candidates with a genuine `EXCESSIVE_STRETCH` tempo relation (>12% even after half/double-time folding). Selected: 15.79% required deviation (real measured BPM mismatch), also `HARMONIC_INCOMPATIBLE` and downbeat-insufficient on the outgoing side — multiple independent honest reasons `FULL_DJ_BLEND` is correctly withheld.

Full rationale with confidence values and reason codes (opaque `RM###` IDs only): `real_music/work_local/selection_rationale_sanitized.json` (in PM ZIP).

### PLANNERDECISION EVIDENCE (real R2 planner, no hand-edited JSON)
| Pair | decision_type | allowed_transition_class_set | required_tempo_ratio | tempo_mode |
|---|---|---|---|---|
| V1 | TRANSITION | SHORT_EQ_BLEND, SIMPLE_CROSSFADE | 1.0 | NATIVE_TEMPO |
| V2 | TRANSITION | FULL_DJ_BLEND, SHORT_EQ_BLEND, SIMPLE_CROSSFADE | 1.0417 | MATCH_INCOMING_DURING_OVERLAP |
| V3 | TRANSITION | SIMPLE_CROSSFADE | 1.1579 | NATIVE_TEMPO |

V2's `MATCH_AND_RETURN_TO_NATIVE` preference was correctly downgraded: `ramp_is_safe` measured **−70.92 cents** drift (outside the ±5-cent tolerance) for this pair's own 1.0417 ratio, so the harness fell back to `MATCH_INCOMING_DURING_OVERLAP` per your explicit direction never to force the unvalidated return-to-native ramp.

### A/B/C RENDER POLICY
Same shared boundary per pair (onset/content_end/entry identical across A/B/C by construction — `dsp/render_common.compute_segments` called once per pair):
- **A** — equal-power reference, no tempo correction (all 3 pairs).
- **B** — late-outgoing-hold loudness candidate, no tempo correction (all 3 pairs).
- **C** — only V2 (FULL_DJ_BLEND allowed + real correction warranted). **Owner-facing C is the official pinned Signalsmith Stretch WASM/WebAudio engine** (manual browser round-trip via `web/stretch_worker.html`, same mechanism as the synthetic M2 pass), `MATCH_INCOMING_DURING_OVERLAP`, 0 semitones pitch shift (preserved), sample-rate parity asserted (44100Hz both sides), 0 NaN/Inf/clipped samples. A separate ffmpeg-Rubber-Band C was also rendered but is **PM/reference-only** and is excluded from the owner ZIP.
- V3 never rendered a C candidate (FULL_DJ withheld by the planner, not by this script).

### PRIVACY VALIDATION
`scripts/verify_real_music_stage_b.py` — **ALL CHECKS PASS**:
- no git-tracked file, sanitized summary, or per-pair result/decision JSON contains `owner_music_input`, any source extension marker, or an absolute-path pattern;
- V2 tempo deviation (4.17%) within the ~3–6% conditional zone and the R2 12% hard envelope;
- V2 owner C is the pinned Signalsmith engine, 0 semitones, never `MATCH_AND_RETURN_TO_NATIVE`;
- V3 `allowed_transition_class_set` excludes `FULL_DJ_BLEND`, no C rendered, `NATIVE_TEMPO`;
- A/B/C (and Signalsmith C) share the identical onset/content_end/entry boundary per pair;
- owner ZIP WAVs: identical sample rate/channels/bit-depth/container, duration spread 0.000s, RIFF `fmt `/`data`-only chunks (no metadata chunk), no internal method-name term (`signalsmith`/`equal_power`/`full_dj`/etc.) anywhere in filenames or text contents;
- new blind seed (`AUTOMIX_R3_REAL_MUSIC_BLIND_SEED`) is not the old synthetic seed (`20260812`), not reused from `AUTOMIX_R3_BLIND_SEED`, and the local-only blind-key file is not git-tracked.

### FORMAT / BLINDING VALIDATION
7 owner clips (`V1-A/B`, `V2-A/B/C`, `V3-A/B`), all 30.00s, 44.1kHz stereo PCM16, RIFF/fmt /data-only, opaque filenames. Blind mapping is a NEW seed/mechanism, never reusing the synthetic pack's seed; the seed and full mapping stay LOCAL ONLY (gitignored) and are never revealed in this handoff or any committed file.

### REAL-MUSIC OWNER ZIP
Path: `P0-M3-R3-REAL-MUSIC-OWNER-LISTENING.zip` (repo root, LOCAL ONLY)
SHA-256: `84ad398e00267f9ac5308c38440ad728fdf6fd7dbe28c8b07d67a8313dfc3465`
Size: `32842522` bytes
Contents (7 wav + instructions + rating template = 9 entries): `LISTENING_INSTRUCTIONS.md`, `OWNER_RATINGS_TEMPLATE.json`, `V1-A.wav`, `V1-B.wav`, `V2-A.wav`, `V2-B.wav`, `V2-C.wav`, `V3-A.wav`, `V3-B.wav`.

### PM ZIP
Path: `P0-M3-R3-REAL-MUSIC-PM-REVIEW.zip` (repo root, LOCAL ONLY)
SHA-256 of the build immediately prior to this final handoff text: `9b87cbe9799d76271dd140db532d91f2bbca41a86bb2b0304858640aba4aabb0`, size `63519` bytes, 23 entries. Because this ZIP embeds `HANDOFF_TO_PM.md` itself, the SHA of the copy containing THIS exact sentence will differ trivially (a few bytes) from the value above — as with the prior accepted PM review cycle's same self-reference limitation, please compute the authoritative SHA-256 independently against the file actually delivered rather than relying on a value quoted inside it.
Contents: this pass's added code (allowlist, no data), sanitized aggregate corpus summary, sanitized selection rationale/trace, per-pair `planner_decision.json`/`result.json` (path-free by construction, independently grepped clean), the Signalsmith owner-render result metadata, the real-music blind key (opaque clip IDs + internal candidate letters only — never the RM###→real-path mapping), the validation report, this `HANDOFF_TO_PM.md`. **No source tracks or derived audible real-music clips are in the PM ZIP** (owner has not authorized that).

### UNKNOWNS / RISKS
- The from-scratch DSP analyzers (beat/downbeat/key/vocal-density) are heuristic, not ML-grade — confidence labels are HONEST but the underlying estimators can still be wrong on individual tracks; owner listening is exactly the check this pass is deferring to for that reason.
- V2's candidate pool under the strict 3–6% + all-hard-gates intersection was only 2 pairs out of ~9,900 — a genuinely narrow slice of this specific 100-track corpus, not a general claim about how often such pairs exist in a larger catalog.
- Vocal-density is an explicitly-labeled HEURISTIC_PROXY (band-energy-ratio × tonal-salience) — not a real vocal-activity detector; a future pass with a trained model could revise V1/V2/V3 selection.
- Only 5/100 tracks showed a detected sustained instrumental outro tail; most near-end candidates rely on the beat/downbeat-grid-confidence fallback rather than a directly-observed vocal-free outro.

### PM CLOSEOUT REQUEST
Please independently verify:
1. Re-run `scripts/verify_real_music_stage_b.py` (needs `AUTOMIX_R3_REAL_MUSIC_BLIND_SEED` — supplied to you out-of-band, never in this document) and confirm ALL CHECKS PASS.
2. Re-run `scripts/selftest_fail_closed.py`, `scripts/verify_beat_grid_membership.py`, `scripts/verify_cross_method_consistency.py`, `scripts/selftest_pre_real_music_repair.py` — confirm no regression.
3. Independently inspect `real_music/work_local/renders/REAL-V2/planner_decision.json` and `C_signalsmith_owner_result.json` for the MATCH_INCOMING_DURING_OVERLAP / pitch-preservation / ramp-safety evidence claimed above.
4. Confirm the PM ZIP contains no private-media identifiers (independent grep for the authorized root path / extensions).
5. When ready, deliver `P0-M3-R3-REAL-MUSIC-OWNER-LISTENING.zip` to the owner for blinded listening per the simplified rubric.

Do not reveal the DSP-method mapping to the owner. Do not start P1.
