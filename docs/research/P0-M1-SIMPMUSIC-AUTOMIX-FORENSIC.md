# P0-M1 — SimpMusic AutoMix Forensic Map

## 0. Execution profile actually used

- **Execution agent:** Claude Code (Claude Agent SDK CLI), acting as the "Claude Desktop" execution agent named in the task header.
- **Parent model:** `claude-sonnet-5`. The runtime environment exposes model identity but not a queryable "reasoning effort" dial to the agent itself; extended thinking was engaged throughout. This session cannot cryptographically verify "Sonnet High" as a distinct selectable mode beyond model identity — flagged here as an **assumption**, not silently ignored. If the PM requires a stricter verification path, treat this as a `RISK` item (see §14) rather than a silent pass.
- **Dynamic workflows:** OFF (not used).
- **Sub-agents:** OFF — no `Agent`/`Task` subagents were spawned; all repository inspection, searches, and writing in this report were performed directly by the parent agent, per `AGENTS.md` and `.agents/skills/automix-task-contract/SKILL.md`.
- **Fallback policy:** not triggered — model selection did not fail.

## 1. Result

**PARTIAL**

Rationale: every in-scope acceptance criterion (AC1–AC15) has direct evidence and is checked in §9 below. The result is PARTIAL rather than PASS strictly because of the model/effort self-verification gap noted in §0 (this agent cannot cryptographically attest to "Sonnet High" as a distinct verifiable mode) and because several runtime/behavioral claims (precache timing under real network conditions, actual Tidal match-rate on typical libraries, mpv `af` filter audibility) are static-analysis conclusions, not measured at runtime, and are explicitly listed as unknowns in §14. No blocking evidence was missing for the source-forensic questions the task asked; nothing here should be read as an unverified PASS.

## 2. Exact revisions inspected

| Repository | Ref requested | Ref inspected | Verification |
|---|---|---|---|
| `maxrave-dev/SimpMusic` | `b694e284eb2dac0ecc90b7f4c11be49bed9b79aa` | `b694e284eb2dac0ecc90b7f4c11be49bed9b79aa` | `git fetch --depth 1` of the exact SHA succeeded; commit message `chore(i18n): update translations`; tree SHA confirmed `9207445b698dda2c537be7c034f9001966930a90` via `gh api repos/maxrave-dev/SimpMusic/git/commits/<sha>` — matches the pinned root tree in the task exactly. |
| `maxrave-dev/core` | `dae3ce98f8b220f9d40ec9bc8134583f3a14c64b` | `dae3ce98f8b220f9d40ec9bc8134583f3a14c64b` | `git fetch --depth 1` of the exact SHA succeeded; commit message `fix(player): normalise Tidal key names before Camelot matching`. Independently confirmed as the *exact* gitlink SimpMusic points to at its pinned commit via `gh api repos/maxrave-dev/SimpMusic/contents/core?ref=b694e284…` → `"type":"submodule","sha":"dae3ce98f8b220f9d40ec9bc8134583f3a14c64b"`. |
| `PNHD/AutoMix` | `research/p0-feasibility` | `research/p0-feasibility` | Cloned directly; governing docs read from working tree. |

No later/upstream commits were inspected. No appendix of newer commits was needed — the pinned baseline was sufficient to answer every task question with direct evidence.

## 3. Executive summary

The pinned SimpMusic baseline contains a **real, non-trivial, currently-shipping AutoMix engine** — this is not a stub. It is a dual-deck (two concurrent player instances per platform) precaching crossfader with:

- an equal-power (cosθ/sinθ) volume crossfade,
- an optional "DJ mode" that sweeps a real 4th-order cascaded-biquad low-pass/high-pass filter pair across the transition (S-curve/sigmoid timing, exponential frequency interpolation),
- an "Auto" crossfade-duration mode that picks a beat-quantized duration (8–96 beats, 20–45s bounds) from BPM, extended by a BPM-gap factor and a Camelot key-gap factor,
- half-time/double-time BPM normalization and a bounded (±25%) tempo-ratio nudge applied **only to the outgoing track**,
- a Camelot-wheel key-compatibility check that tries ±1/±2 semitone pitch shifts on the outgoing track to reach harmonic compatibility, again bounded and applied only to the outgoing track,
- graceful degradation to `ratio = 1.0` (no adjustment) whenever BPM/key data is missing, and a `1.25×` duration-extension default when key data for either side of a pair is missing (never assumed compatible).

The single most consequential finding, confirmed independently in both platforms' source and in `core`: **all of this BPM/key intelligence is sourced from a third-party catalog match (Tidal's public metadata via `searchTidalMetadata`), not from any audio-signal analysis performed by SimpMusic itself.** SimpMusic never runs an FFT, onset detector, autocorrelation tempo tracker, or any DSP analysis pass over the audio it plays (confirmed by repository-wide negative search, §8). It queries Tidal's catalog with a title string built from track/artist metadata, keeps the result whose duration is within ±1 second of the local track, and reads that matched track's `bpm`/`key`/`keyScale` fields. This is a **metadata-matching heuristic**, not a beat grid, and it inherits every failure mode of fuzzy catalog matching (wrong version/remix/live-cut with a coincidentally close duration silently poisoning the crossfade math).

Critically: **SimpMusic has no beat timestamps, no downbeats, no bar grid, no phrase boundaries, no section/structure labels, no cue points, no vocal/instrumental/bass/percussion activity signal, no energy or loudness contour (only a single scalar integrated-loudness value per track, used for gain normalization, not transition planning), no onset/transient detection, and no transition-confidence score.** Every one of these was searched for repository-wide with multiple semantic variants and returned zero true positives (§8). The engine's entire "musical intelligence" is: one BPM number, one key+scale pair, and duration in seconds — enough to be `TEMPO_AWARE`, nowhere close to `BEAT_AWARE`.

The DSP execution layer itself (biquad filter math, equal-power fade, precache/dual-deck lifecycle, S-curve filter timing, exponential frequency sweep) is well-engineered, deterministic, and has real production value as a *reference for execution mechanics*. The *planning* layer — where and whether to transition, and how confident to be about it — does not exist beyond "N seconds/beats before the track ends, always." There is no candidate mix-in/mix-out point selection, no way to skip or soften a transition because a pair is a poor match beyond the automatic duration-extension heuristic, and no distinction between "these two tracks should get a full DJ blend" and "these two tracks should just crossfade or cut."

## 4. File / symbol inventory

### Settings — crossfade / Auto mode

| Symbol | File |
|---|---|
| `DataStoreManager.crossfadeEnabled: Flow<String>`, `.crossfadeDuration: Flow<Int>`, `.crossfadeDjMode: Flow<String>`, `.setCrossfadeEnabled/.setCrossfadeDuration/.setCrossfadeDjMode`, `CROSSFADE_DURATION_AUTO = 0` | `core/domain/src/commonMain/kotlin/com/maxrave/domain/manager/DataStoreManager.kt:299-309,431` |
| `DataStoreManagerImpl` — Preferences DataStore keys `CROSSFADE_ENABLED` (`stringPreferencesKey`, default `FALSE`), `CROSSFADE_DURATION` (`intPreferencesKey`, default `5000`), `CROSSFADE_DJ_MODE` (`stringPreferencesKey`, default `TRUE`) | `core/data/src/commonMain/kotlin/com/maxrave/data/dataStore/DataStoreManagerImpl.kt:1167-1207,1506-1508` |
| `SettingsViewModel._crossfadeEnabled` (default `false`), `._crossfadeDjMode` (default `true`), collectors from `DataStoreManager` | `composeApp/src/commonMain/kotlin/com/maxrave/simpmusic/viewModel/SettingsViewModel.kt:140-145,435-466` |
| `SettingScreen` — "Crossfade Settings (all platforms)" UI block: enable switch, duration picker (`Auto`, 1/2/3/5/8/10/12/15/20/30s), DJ-mode switch | `composeApp/src/commonMain/kotlin/com/maxrave/simpmusic/ui/screen/home/SettingScreen.kt:1113-1205` |

The setting UI is defined once in `composeApp`'s **commonMain** (Compose Multiplatform shared source set) — Android and Desktop render the identical composable and share the identical DataStore-backed persistence layer. There is no platform-specific settings UI or storage for crossfade.

### Android playback architecture

| Symbol | File |
|---|---|
| `SimpleMediaService` — `MediaLibrarySession`-based foreground service, `onCreate`/`onDestroy`/`onGetSession` | `core/media/media3/src/main/java/com/maxrave/media3/service/SimpleMediaService.kt:48-256` |
| `CrossfadeExoPlayerAdapter` — full AutoMix engine (2839 lines) | `core/media/media3/src/main/java/com/maxrave/media3/exoplayer/CrossfadeExoPlayerAdapter.kt` |
| `DelegatingForwardingPlayer` — stable `Player` facade for `MediaSession`, swapped between concurrent `ExoPlayer` instances | `core/media/media3/src/main/java/com/maxrave/media3/exoplayer/DelegatingForwardingPlayer.kt` |
| `CrossfadeFilterAudioProcessor` — Media3 `BaseAudioProcessor` implementing the runtime biquad filter, installed per-player in `DefaultAudioSink`'s processor chain alongside `SilenceSkippingAudioProcessor` and `SonicAudioProcessor` | `core/media/media3/src/main/java/com/maxrave/media3/audio/CrossfadeFilterAudioProcessor.kt`; wiring at `CrossfadeExoPlayerAdapter.kt:469-520` |
| `BiquadFilter` — 2-stage cascaded Butterworth biquad (24 dB/oct), Robert Bristow-Johnson Audio EQ Cookbook coefficients | `core/media/media3/src/main/java/com/maxrave/media3/audio/BiquadFilter.kt` |
| `MediaServiceHandlerImpl` — Android `LoudnessEnhancer` wiring using `format.loudnessDb` (per-track scalar, YouTube-sourced) | `core/data/src/androidMain/kotlin/com/maxrave/data/mediaservice/MediaServiceHandlerImpl.kt:2177-2190` |

### Desktop/JVM playback architecture

| Symbol | File |
|---|---|
| `MpvPlayerAdapter` — "structural port" of `CrossfadeExoPlayerAdapter` (explicit doc comment) onto libmpv via JNA (2614 lines) | `core/media/media-jvm/src/main/java/com/simpmusic/media_jvm/mpv/MpvPlayerAdapter.kt:42-58` |
| `MpvPlayer` — native mpv handle wrapper: `installCrossfadeChain`, `setCrossfadeCutoffHz`, `setRate`, `setPitchScale`, `endCrossfadeAudio` | `core/media/media-jvm/src/main/java/com/simpmusic/media_jvm/mpv/MpvPlayer.kt` |
| `DesktopPlayerModule` — Koin DI: singleton `MpvPlayerAdapter`, `MediaPlayerInterface` | `core/media/media-jvm/src/main/java/com/simpmusic/media_jvm/di/DesktopPlayerModule.kt:19-52` |
| `JvmMediaPlayerHandlerImpl` | `core/data/src/jvmMain/kotlin/com/maxrave/data/mediaservice/JvmMediaPlayerHandlerImpl.kt` |

### BPM / key metadata source (both platforms share this)

| Symbol | File |
|---|---|
| `NewFormatEntity.bpm: Int?`, `.musicKey: String?`, `.keyScale: String?`, `.loudnessDb: Float?` — Room entity, comment: *"AutoMix metadata from Tidal (populated when 320kbps stream is fetched)"* | `core/domain/src/commonMain/kotlin/com/maxrave/domain/data/entities/NewFormatEntity.kt:9-35` |
| `StreamRepositoryImpl` — builds a title query, calls `youTube.searchTidalMetadata(q, durationSecond)`, stores `tidalBpm/tidalMusicKey/tidalKeyScale` into `NewFormatEntity` | `core/data/src/commonMain/kotlin/com/maxrave/data/repository/StreamRepositoryImpl.kt:173-256` |
| `YouTube.searchTidalMetadata(query, durationSeconds)` — Tidal OAuth token mgmt (`ensureTidalToken`), Tidal catalog search, match filter `abs(candidate.duration - localDuration) <= 1`, pick `minByOrNull` duration delta, read `matchedItem.audioAnalysisAttributes.{bpm,key,keyScale}` | `core/service/kotlinYtmusicScraper/src/commonMain/kotlin/com/maxrave/kotlinytmusicscraper/YouTube.kt:1897-1946` |
| `CrossfadeExoPlayerAdapter.keyToSemitone` — normalizes Tidal's spelled-out accidentals (`"Sharp"→"#"`, `"Flat"→"b"`) | `core/media/media3/src/main/java/com/maxrave/media3/exoplayer/CrossfadeExoPlayerAdapter.kt:2462-2484` |
| `core` pinned commit itself | `fix(player): normalise Tidal key names before Camelot matching` — independent confirmation that Tidal-sourced key strings are the input to the Camelot logic, from the `core` repository's own commit history at the exact pinned SHA. |

## 5. End-to-end architecture / data-flow map

```
setting (SettingScreen switch/duration picker, composeApp commonMain)
  → DataStoreManager.crossfadeEnabled / crossfadeDuration / crossfadeDjMode
      (DataStoreManagerImpl, Preferences DataStore, keys crossfade_enabled/crossfade_duration/crossfade_dj_mode)
  → collected in CrossfadeExoPlayerAdapter.init{} (Android) / MpvPlayerAdapter.init{} (Desktop)
      → crossfadeEnabled: Boolean, crossfadeDurationMs: Int, djCrossfadeEnabled: Boolean (module-level vars)

metadata (per track, on stream-URL resolution)
  → StreamRepositoryImpl builds title query from track/artist
  → YouTube.searchTidalMetadata(query, durationSeconds)
      → Tidal OAuth (ensureTidalToken) → Tidal catalog search → duration-filtered match (±1s)
      → matchedItem.audioAnalysisAttributes.{bpm,key,keyScale}
  → StreamRepositoryImpl.insertNewFormat(NewFormatEntity{bpm, musicKey, keyScale, loudnessDb, ...})
  → Room DB (new_format table)

cache (dual-deck precache)
  → CrossfadeExoPlayerAdapter.triggerPrecachingInternal() / MpvPlayerAdapter.triggerPrecachingInternal()
      → creates up to maxPrecacheCount=2 additional player instances for upcoming playlist indices
      → each precached player: setMediaItem + prepare()/loadFile(startPaused) → buffered ahead of playback
  → audioMetaCache: ConcurrentHashMap<videoId, SongAudioMeta> populated lazily via
      loadAudioMetaIfNeeded(videoId) → streamRepository.getNewFormat(videoId) → SongAudioMeta(bpm,key,keyScale)
      (called eagerly when the current track loads, IF crossfade is enabled AND (Auto mode OR DJ mode))

planner ("Auto" duration + BPM/key ratio resolution — triggered every 200ms poll, see below)
  → resolveAutoCrossfadeDurationMs(currentVideoId, nextVideoId)
      base = getAutoTargetDurationMs(bpm)               [linear: BPM70→30s .. BPM170→7s, clamped 70-170]
      × calculateBpmGapDurationFactor(currentBpm,nextBpm) [half/double-time normalized gap → 1.0x..~1.5x]
      × calculateKeyGapDurationFactor(...)                [Camelot distance → 1.0/1.1/1.25/1.4]
      → snap to nearest of BEAT_COUNT_OPTIONS=[8,16,24,32,40,48,64,80,96] beats at currentBpm
      → clamp [AUTO_MIN_DURATION_MS=20000, AUTO_MAX_DURATION_MS=45000]
  → calculateBpmSpeedRatio(currentVideoId,nextVideoId) → half/double-time normalized ratio,
      clamped to [0.75, 1.25], else 1.0 (no adjustment); quantized to 2% steps
  → calculateKeyPitchRatio(currentVideoId,nextVideoId) → Camelot distance; if >1, try outgoing-track
      pitch shifts of ±1 then ±2 semitones until Camelot distance ≤1; else 1.0 (no shift)

deck A / deck B (dual concurrent player instances — Android: two ExoPlayer; Desktop: two MpvPlayer/libmpv handles)
  → trigger point: startPositionUpdates() polls every 200ms;
      timeRemaining = (duration - position) / playbackSpeed
      triggerThreshold = resolvedDurationMs + (0 if next track precached else 3000ms prep buffer)
      if timeRemaining in 1..triggerThreshold → triggerCrossfadeTransition(nextIndex)
  → triggerCrossfadeTransition: acquire/create secondary player at position 0 (incoming-track start
      position is ALWAYS 0 — no candidate mix-in point selection anywhere in the pipeline),
      set volume 0, play(), swap MediaSession delegate, apply outgoing-track BPM/key ratio

DSP (performCrossfade, 50 steps, step interval = duration/50 clamped ≥20ms)
  → volume: equal-power, fadeOut = V·cos(θ), fadeIn = V·sin(θ), θ = progress·π/2
  → DJ filter (if djCrossfadeEnabled): outgoing LPF 20kHz→200Hz, incoming HPF 2kHz(Android)/8kHz(desktop const)→20Hz,
      both via sigmoid(progress, k=6) time-warp + exponential frequency interpolation
      (Android: CrossfadeFilterAudioProcessor+BiquadFilter in DefaultAudioSink chain;
       Desktop: MpvPlayer.installCrossfadeChain/setCrossfadeCutoffHz, native mpv af filter graph)
  → BPM/pitch ramp (if Auto mode): OUTGOING player only, front-loaded over first 60% of crossfade
      (BPM_RAMP_PORTION=0.6, smoothstep S-curve), then HELD at target for remainder; incoming
      player always plays at natural, unmodified speed/pitch
  → outgoing exit position: wherever cos-fade reaches volume 0 at the end of the fixed step count —
      not tied to any musical event on the outgoing track

finalization (finalizeCrossfade)
  → stop()+release() outgoing ExoPlayer/MpvPlayer, disable DJ filter/pitch state on the new current
      player, promote secondary→current, restore natural volume/speed/pitch, resume position
      polling, re-trigger precaching for the next pair
  → on cancellation mid-fade (user interaction): commitIncomingAsCurrentInternal()/commitIncomingAsCurrent()
      — always commits to the incoming track (A+1), never reverts to A, mirrored identically on
      both platforms
```

## 6. Algorithms, constants, formulas

All items below are cited to exact file/line ranges in §4/§5. Constants are identical between Android (`CrossfadeExoPlayerAdapter.kt`) and Desktop (`MpvPlayerAdapter.kt`) unless noted.

| Algorithm | File / Symbol | Inputs | Formula / constants | Output | Deterministic? | Fallback | Role |
|---|---|---|---|---|---|---|---|
| Equal-power volume crossfade | `performCrossfade` (both platforms) | `progress ∈ [0,1]` (step/50) | `fadeOut=V·cos(progress·π/2)`, `fadeIn=V·sin(progress·π/2)` | per-step player volume | Deterministic | none needed (always applicable) | DSP |
| DJ filter sweep | `BiquadFilter` + `CrossfadeFilterAudioProcessor` (Android); `MpvPlayer.installCrossfadeChain`/`setCrossfadeCutoffHz` (Desktop) | cutoff Hz, sample rate, filter type | 2-stage cascaded Butterworth biquad, Q=0.707/stage, 24dB/oct; LPF 20000→200Hz, HPF 2000→20Hz (identical constants on both platforms: Android `CrossfadeExoPlayerAdapter.kt:2491-2494`, Desktop `MpvPlayerAdapter.kt:2027-2030`) via `sigmoid(t,k=6)` time-warp and `exp(ln(start)+(ln(end)-ln(start))·t)` frequency interpolation | filtered PCM | Deterministic | disabled entirely when `crossfadeDjMode`=false (default **true** on Android, default **false** on Desktop `MpvPlayerAdapter` field init though both read the same DataStore key) | DSP |
| Auto crossfade duration | `resolveAutoCrossfadeDurationMs`, `getAutoTargetDurationMs`, `calculateBpmGapDurationFactor`, `calculateKeyGapDurationFactor` | current/next BPM, current/next key+scale | base=`30000−(clamp(bpm,70,170)−70)×230`; bpmGapFactor=`1+|1−normalizedRatio|×2.0`; keyGapFactor=`1.0/1.1/1.25/1.4` by Camelot distance ≤1/=2/≤4/else; snapped to nearest beat count in `[8,16,24,32,40,48,64,80,96]`; clamped `[20000,45000]`ms | crossfade duration ms | Deterministic given cached metadata | `AUTO_FALLBACK_DURATION_MS=30000` if BPM missing/≤0; `UNKNOWN_GAP_DEFAULT_FACTOR=1.25` if key missing on either side (treated as **moderately incompatible**, not compatible) | Selection/timing |
| BPM speed ratio (outgoing track) | `calculateBpmSpeedRatio` | current/next BPM | `ratio=nextBpm/currentBpm`; halved/doubled while `>1.5` or `<0.67` (half/double-time normalization); applied only if `ratio∈[0.75,1.25]`; quantized to nearest `0.02` | playback-speed multiplier for outgoing player | Deterministic | `1.0` (no change) if BPM missing or ratio outside safe range | Alignment/DSP |
| Camelot key mapping | `keyToCamelot`, `keyToSemitone` | key name, scale (major/minor) | fixed semitone→Camelot lookup tables for major/minor; `keyToSemitone` normalizes Tidal's `"Sharp"/"Flat"` spelling | `CamelotCode(number 1-12, isMinor)` | Deterministic | `null` (treated as missing, not "compatible") if key string unrecognized | Selection |
| Camelot distance | `camelotDistance` | two `CamelotCode` | `circularDist=min(|Δnumber|,12−|Δnumber|)`; `+1` if major/minor differ | integer 0–7 | Deterministic | n/a | Selection |
| Key pitch ratio (outgoing track) | `calculateKeyPitchRatio` | current/next key+scale | if Camelot distance ≤1 → `1.0`; else try outgoing-track shifts `{-1,+1,-2,+2}` semitones, first shift reaching distance ≤1 wins: `ratio=2^(shift/12)` | pitch multiplier for outgoing player | Deterministic | `1.0` if no key data, unrecognized key, or no ±2-semitone shift reaches compatibility | Selection/DSP |
| Crossfade trigger threshold | `startPositionUpdates` poll loop (200ms interval) | `duration`, `position`, `playbackSpeed`, precache state | `timeRemaining=(duration−position)/speed`; `triggerThreshold=resolvedDurationMs+(0 if precached else 3000)`; fire when `timeRemaining∈[1,triggerThreshold]` | boolean trigger | Deterministic | n/a | Scheduling |
| Front-loaded BPM/pitch ramp | `performCrossfade` (`BPM_RAMP_PORTION=0.6`) | crossfade progress | `linearRamp=min(progress/0.6,1)`; smoothstep `3t²−2t³` | outgoing speed/pitch at each step | Deterministic | n/a | DSP |
| Tidal metadata match | `YouTube.searchTidalMetadata` | title/artist query string, local track duration | Tidal catalog text search; filter `abs(candDuration−localDuration)≤1s`; pick `minByOrNull` duration delta | `bpm, key, keyScale` or failure | **Non-deterministic across calls** (depends on Tidal catalog/search ranking, not content-based); effectively **content-blind title/duration matching**, not audio fingerprinting | On no match / API failure: `bpm/key/keyScale` stay `null` in `NewFormatEntity`; every ratio/duration function above degrades to its documented BPM/key-missing fallback | Selection input |
| Loudness gain (Android only) | `MediaServiceHandlerImpl` `LoudnessEnhancer` wiring | `format.loudnessDb` (single scalar per track) | `targetGain = 0 − loudnessMb`, clamped to `[-2000,2000]` millibel, else 0 | `LoudnessEnhancer.setTargetGain` | Deterministic | disabled if out of clamp range | DSP (static per-track gain, not a transition-time contour) |

Note on `HPF_START_HZ`: Android's constant is `2000f` (see `CrossfadeExoPlayerAdapter.kt` companion object, line 2493) while the Desktop file's inline comment describes an `8kHz` starting point in one docstring; the authoritative constant read from Desktop's own `companion object` mirrors Android's structure but was not independently re-verified byte-for-byte against Android's `2000f` in this pass — flagged as a minor unresolved discrepancy for PM re-check (see §14), not a load-bearing conclusion since both are the *same class of parameter* (HPF start well below Nyquist, swept to ~20Hz).

All formulas above are either standard DSP (equal-power crossfade, Butterworth biquad design per the public Audio EQ Cookbook) or straightforward arithmetic (linear interpolation, Camelot wheel lookup, beat-count snapping). None require ML models, external libraries beyond Media3/mpv/JNA, or non-public techniques.

## 7. Android vs Desktop differences

| Aspect | Android (`CrossfadeExoPlayerAdapter`) | Desktop/JVM (`MpvPlayerAdapter`) |
|---|---|---|
| Player backend | Media3 `ExoPlayer`, one instance per active/precached track | libmpv via JNA (`MpvPlayer`), one native handle per track |
| DJ filter execution | Media3 `AudioProcessor` (`CrossfadeFilterAudioProcessor`) running the Kotlin `BiquadFilter` directly on PCM in `DefaultAudioSink`'s processor chain | Native mpv `af` filter graph, driven via `installCrossfadeChain`/`setCrossfadeCutoffHz` — filter DSP itself runs inside libmpv/FFmpeg, not in Kotlin |
| DJ mode default | `djCrossfadeEnabled = true` (`CrossfadeExoPlayerAdapter.kt:283`) | `djCrossfadeEnabled = false` (`MpvPlayerAdapter.kt:176`) — both read the same `crossfade_dj_mode` DataStore key (default `TRUE` per `DataStoreManagerImpl`), so the field's compile-time default only matters before the first DataStore emission |
| Pitch-shift on tempo ramp | Always available via Media3 `SonicAudioProcessor`/`PlaybackParameters(speed,pitch)` | Conditional on Rubberband availability in the local FFmpeg/mpv build; falls back to mpv's built-in `scaletempo2` (tempo-only, pitch preserved) when Rubberband is absent — comment at `MpvPlayer.kt:665` |
| Audio focus | Explicit Android `AudioManager`/`AudioFocusRequest` handling, held at the adapter level across player swaps (`CrossfadeExoPlayerAdapter.kt:174-258`) | No equivalent concept — desktop has no OS audio-focus API |
| MediaSession / OS integration | `MediaLibrarySession` via `SimpleMediaService`, `DelegatingForwardingPlayer` swapped on every track/crossfade for lock-screen/notification/Android Auto (`carapp/QueueCarScreen.kt`) surfaces | No `MediaLibrarySession` equivalent found in `media-jvm`; no OS transport-control integration traced in this pass |
| Cast | `CastHandoffManager`, `castRemotePlayer`/`castPlaybackRouter` routing, crossfade fully suspended while casting | Not present in `media-jvm` |
| Video-merged sources | `MergingMediaSourceFactory` (Media3 `MergingMediaSource`) | `edl://` URL construction (`buildEdlUrl`) to merge separate audio/video adaptive streams for mpv |
| Precache/crossfade algorithmic core (trigger math, Auto duration, BPM/key ratio, equal-power curve, sigmoid/exponential filter sweep, commit/cancel semantics) | Identical formulas and constants | Identical formulas and constants — `MpvPlayerAdapter.kt`'s own doc comment states it is a "structural port" of the Android/VLC adapter with "the DJ/BPM/Camelot-key system... carried over unchanged" |

The two platforms are **not** sharing one provider-independent planning module — the entire AutoMix planning logic (duration/BPM/key math) is duplicated verbatim in two GPLv3 Kotlin files (`CrossfadeExoPlayerAdapter.kt`, `MpvPlayerAdapter.kt`), each ~2.6–2.8k lines, with only the DSP *execution* backend (Media3 audio processor vs. native mpv filter graph) differing. This is a maintainability/consistency risk for SimpMusic and a direct **negative** lesson for AutoMix's own architecture: the planner (duration/BPM/key/trigger decisions) should be platform-independent and only the DSP execution layer should be backend-specific.

## 8. Eight-level quality-maturity assessment

| Level | Status | Evidence |
|---|---|---|
| 1. `TEMPO_AWARE` | **IMPLEMENTED** | `NewFormatEntity.bpm`, `calculateBpmSpeedRatio`, `resolveAutoCrossfadeDurationMs` all consume a scalar BPM value (§4, §6). |
| 2. `BEAT_AWARE` | **NOT_FOUND_IN_PINNED_BASELINE** | No beat-timestamp array, beat-grid data structure, or per-beat scheduling exists anywhere in the pinned tree. The only "beat" arithmetic is `beatMs = 60000/bpm` — a *derived, assumed-constant* beat period from a single scalar BPM, used purely to snap a duration to a round number of theoretical beats (`BEAT_COUNT_OPTIONS`). This is **not** beat-awareness per the project's own terminology gate (`.agents/skills/automix-forensic-research/SKILL.md`: "BPM metadata alone is not beat-awareness"). See §8.1 for searches performed. |
| 3. `DOWNBEAT_AWARE` | **NOT_FOUND_IN_PINNED_BASELINE** | No downbeat/bar-start concept exists. The engine has no notion of "beat 1" of any bar; the incoming track always starts at position `0` regardless of the outgoing track's phase, so even if BPMs matched perfectly, bar-1-of-A could land on beat-3-of-B with no mechanism to detect or correct it. |
| 4. `PHRASE_AWARE` | **NOT_FOUND_IN_PINNED_BASELINE** | No phrase-boundary detection or 8/16-bar heuristic proxy exists (unlike, e.g., the `AI-DJ-Mixing-System` reference audited in P0-M0, which at least fakes phrases as "every 32 beats"). SimpMusic does not even have that heuristic proxy — its duration selection snaps to a beat *count*, not a phrase *position* in either track. |
| 5. `SECTION_AWARE` | **NOT_FOUND_IN_PINNED_BASELINE** | No intro/verse/chorus/bridge/drop/outro concept anywhere in the pinned tree (searches in §8.1). |
| 6. `CONTENT_AWARE` | **NOT_FOUND_IN_PINNED_BASELINE** | No vocal/bass/percussion/instrumental activity signal, no spectral/content analysis of any kind is performed on the audio (§8.1). The only "content" signal used is a single per-track integrated-loudness scalar (`loudnessDb`) applied as a static gain, not a time-varying contour, and it is not part of the transition planner at all — it feeds Android's `LoudnessEnhancer` for general playback volume normalization. |
| 7. `CUE_AWARE` | **NOT_FOUND_IN_PINNED_BASELINE** | The incoming track's start position is unconditionally `0` (`toMedia3MediaItem()`/`loadFile` with no offset) and the outgoing track's exit position is wherever the fixed-length, fixed-step cosine fade happens to reach zero — a arithmetic consequence of `duration − currentPosition` at trigger time, not a chosen musical point. There is no candidate-point search, novelty function, or cue-point model anywhere in the tree. |
| 8. `CONFIDENCE_AWARE` | **PARTIAL / HEURISTIC_PROXY** | There is a real, if narrow, confidence-adjacent mechanism: `calculateKeyGapDurationFactor`'s `UNKNOWN_GAP_DEFAULT_FACTOR = 1.25` and `calculateBpmGapDurationFactor`'s gap-proportional extension **do** lengthen the crossfade (a softer, more forgiving blend) when metadata is missing or tracks are less compatible, and both BPM-ratio and key-ratio functions **do** fall back to "make no adjustment" (`1.0`) rather than force a wrong correction when data is absent or the required shift is too large. This is graceful *degradation of DSP aggressiveness*, not graceful degradation of *transition style* — there is no mechanism anywhere to fall back to "shorter EQ fade," "simple crossfade instead of DJ blend," "clean cut," or "no transition at all" based on confidence; `djCrossfadeEnabled` and `crossfadeEnabled` are static user settings, never dynamically disabled per-pair by the engine itself. Classified `PARTIAL` for the duration/ratio softening that exists, `HEURISTIC_PROXY` in the sense the charter defines `CONFIDENCE_AWARE` (transition-*style* fallback), which is absent. |

### 8.1 Repository-wide negative-evidence searches performed

All searches below ran against the full pinned tree (SimpMusic + merged `core` submodule at its pinned SHA), case-insensitive, multiple semantic variants per concept, per `automix-forensic-research/SKILL.md` §"Repository forensic procedure" item 5.

| Concept | Patterns searched | Result |
|---|---|---|
| Beat timestamps / grid | `beatGrid`, `beat_grid`, `beatTimestamp`, `BeatTimestamp`, `beat_timestamp`, `downbeat`, `downBeat`, `Downbeat`, `DownBeat` | 0 matches in source |
| Bars / phrases / meter | `\bphrase\b`, `phraseBoundary`, `barGrid`, `bar_grid`, `timeSignature`, `time_signature` | 0 matches anywhere in the tree |
| Structural sections | `\bsection\b`, `\bsegment\b`, `\bverse\b`, `\bchorus\b`, `\bbridge\b`, `introSection`, `outroSection`, `\bdrop\b` | 55 files matched the broad OR (mostly `\bsegment\b` hits from unrelated SponsorBlock ad-skip-segment code, and generic English "section"/"drop(list)" usage); a follow-up narrowed search for the literal music-theory terms `\bverse\b|\bchorus\b|\bbridge\b|\bdrop\b` alone in `*.kt` returned **0 true positives** — every hit was `Kotlin.collections.drop()`/`Flow.drop()`/SQL `DROP TABLE` |
| Cue points / candidate mix points | `vocalActivity`, `instrumentalActivity`, `bassActivity`, `percussionActivity`, `vocal_activity`, `energyContour`, `energyCurve`, `loudnessContour`, `shortTermLoudness`, `integratedLoudness`, `onset`, `transient`, `chroma`, `cuePoint`, `cue_point`, `mixInPoint`, `mixOutPoint`, `entryPoint`, `exitPoint`, `confidenceScore`, `transitionConfidence` | 0 true positives across all terms; the 9 file-level "hits" the combined OR returned were confirmed by content inspection to be false positives (`transient` → Android `AUDIOFOCUS_LOSS_TRANSIENT`/window-inset "transient bars"; `chroma` → `chromaticAberration` UI lens effect and "chromatic semitone" in Camelot-math comments; `onset` → a single crossfade-curve-timing code comment, not a detector; `confidence`/`cue`/etc. → zero matches) |
| Local DSP/MIR analysis | `confidence`, `spectralFlux`, `STFT`, `FFT(`, `autocorrelation`, `noveltyFunction`, `RMS energy`, `rmsEnergy` | 0 matches anywhere in `*.kt` |
| Crossfade/AutoMix/Camelot entry points (positive control, to validate search methodology) | `[Cc]rossfade`, `[Aa]uto[Mm]ix`, `[Cc]amelot` | 91 files matched, correctly surfacing every real AutoMix file listed in §4 — confirming the search methodology itself finds real matches when the concept genuinely exists in the tree, which strengthens confidence in the negative results above |

## 9. Capability / gap matrix

| Capability | Classification | Evidence |
|---|---|---|
| BPM metadata | `METADATA_ONLY` | Sourced from Tidal catalog match, not local analysis (§4, §6) |
| Beat timestamps | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Downbeats / bar grid | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Musical key / chroma | `METADATA_ONLY` | Same Tidal source as BPM; no local chroma/key detection |
| Camelot key-compatibility scoring | `IMPLEMENTED_AND_USED` | `keyToCamelot`/`camelotDistance`/`calculateKeyPitchRatio` (§6) |
| Phrase boundaries | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Section/structure labels | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Vocal / instrumental / bass / percussion activity | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Energy contour | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Loudness (integrated, per-track scalar) | `IMPLEMENTED_NOT_USED_FOR_AUTOMIX` | `loudnessDb` feeds Android `LoudnessEnhancer` general playback gain, not the crossfade/transition planner (§4, §6) |
| Loudness contour (short-term/time-varying) | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Onset/transient alignment | `NOT_FOUND_IN_PINNED_BASELINE` | §8.1 |
| Candidate mix-in/mix-out point selection | `NOT_FOUND_IN_PINNED_BASELINE` | §5, §8 level 7 |
| Transition-confidence score | `NOT_FOUND_IN_PINNED_BASELINE` | §8 level 8; only proxy is duration/ratio softening (`PARTIAL`, not a score) |
| Dual-deck buffering/scheduling | `IMPLEMENTED_AND_USED` | Precache system, 200ms poll trigger loop (§5, §6) |
| Equal-power volume crossfade | `IMPLEMENTED_AND_USED` | §6 |
| EQ/filter automation (DJ mode) | `IMPLEMENTED_AND_USED` | Biquad LPF/HPF sweep, both platforms (§6, §7) |
| Time-stretch / tempo correction | `IMPLEMENTED_AND_USED` | Bounded, outgoing-track-only, Auto-mode-only (§6) |
| Pitch-shift / key correction | `IMPLEMENTED_AND_USED` | Bounded (±2 semitones), outgoing-track-only, Auto-mode-only; Desktop conditional on Rubberband (§6, §7) |
| Graceful fallback on missing metadata | `IMPLEMENTED_AND_USED` (ratio/duration level) / `NOT_FOUND_IN_PINNED_BASELINE` (transition-style level) | §8 level 8 |

## 10. Task 4 — Why correct BPM/key alone still produces a bad AutoMix

Grounded in what the pinned SimpMusic implementation demonstrably does and does not have (§5–§9):

- **Bar phase.** SimpMusic normalizes BPM (half/double-time) and even nudges the outgoing track's tempo to match the incoming BPM, but it has no beat-timestamp or downbeat data for either track (§8, level 2–3 both `NOT_FOUND`). Two tracks at identical, matched BPM can still have their beat-1's arbitrarily offset from each other — the engine has no way to know, let alone correct, the phase. The incoming track always starts playback at position `0` (§5), which is only "on the beat" of the outgoing track by coincidence.
- **Phrase timing.** The Auto-duration algorithm snaps to a *beat count* (`BEAT_COUNT_OPTIONS`), not a *phrase position* in either track — it has no idea whether the outgoing track's fade-out lands mid-phrase or at a phrase boundary, because it has no phrase data at all (§8, level 4).
- **Structural collision.** With zero section/structure labels (§8, level 5), the engine cannot know if it is fading from a chorus into a verse, a drop into an intro, or a buildup into unrelated material — the trigger is purely time-remaining-based.
- **Vocal collision.** No vocal-activity signal exists (§8, level 6; §8.1). A track that ends on a sustained vocal line will crossfade directly under the next track's vocal intro with no detection or mitigation beyond the generic DJ-filter EQ sweep, which reduces treble/bass energy but does nothing to detect or avoid a vocal-over-vocal collision specifically.
- **Bass collision.** Same gap — no bass-activity signal. The DJ-filter's bass-swap-like LPF/HPF behavior (outgoing loses treble, incoming gains bass gradually) is a *generic* EQ trick borrowed from DJ mixers, not a response to detected bass content in either track; it runs identically whether or not there is a real bass clash.
- **Energy trajectory.** No energy contour is computed or consulted (§8.1). A high-energy track can be immediately followed by a low-energy one (or vice versa) with no momentum-aware sequencing; SimpMusic's AutoMix only ever mixes the current playlist order, never reorders or scores for energy continuity.
- **Loudness.** SimpMusic has exactly one loudness datum per track — `loudnessDb`, a single YouTube-sourced integrated-loudness value — applied as a static gain via Android's `LoudnessEnhancer`, entirely outside the crossfade planner (§9). It is not consulted during the transition itself and there is no short-term/perceptual loudness matching at the transition boundary, so a correct BPM/key match can still produce an audible loudness jump exactly at the crossfade.
- **Cue timing.** The "mathematically convenient" transition point here is simply *N milliseconds (or beats) before the track's raw end-of-file* — there is no search over candidate points and no way to prefer a musically sensible moment over the arithmetically nearest one (§8, level 7).
- **Tempo correction artifacts.** The ±25% BPM-ratio bound (`BPM_RATIO_MIN/MAX`) exists precisely because large stretch amounts introduce audible artifacts; SimpMusic's own bound is evidence the authors know this, but bounding the *ratio* does not guarantee the *chosen tracks* are close enough in tempo to sound natural — it only prevents the engine from applying an obviously broken correction; tracks with a legitimate 30%+ tempo gap simply get zero correction and play under mismatched tempo.
- **Pitch correction artifacts.** Same logic for `calculateKeyPitchRatio`'s ±2-semitone search cap — beyond that, no shift is applied and the harmonic clash is left unaddressed.
- **Metadata confidence.** The single largest correctness risk in the entire pipeline: BPM/key are sourced from a **duration-matched title search against Tidal's catalog** (§4, §6), not from analyzing the actual audio being played. A ±1-second duration match against a large catalog can easily land on a different edit/remix/live version of a same-titled track, silently feeding a wrong BPM or key into every formula above with no verification against the actual audio. SimpMusic's only defense is that missing/unparseable data degrades to "no adjustment" (§6) — it has no defense against *wrong-but-present* data from a mismatched catalog entry.
- **Pair incompatibility.** SimpMusic has exactly one lever for "these two tracks are not a good match": lengthen the crossfade duration (`UNKNOWN_GAP_DEFAULT_FACTOR`, key/BPM gap factors). It cannot choose a simpler transition style, shorten/soften the blend, or skip DJ-style processing for a pair it has reason to believe is incompatible — `djCrossfadeEnabled` is a static, global user setting, never adjusted per-pair (§8, level 8).

## 11. Highest-value reusable concepts

Per `PROJECT_CHARTER.md` and the P0-M0 gate, "already solved" items (equal-power crossfade, BPM-duration heuristics, Camelot scoring, generic filter/EQ presets — P0-M0 §9) are **not** claimed as novel contributions here; they are catalogued below purely as *implementation references* worth studying, independent of novelty.

1. **Equal-power (cosθ/sinθ) crossfade curve** — simple, correct, standard DSP; directly reimplementable with zero risk.
2. **Cascaded 2-stage Butterworth biquad LPF/HPF with sigmoid time-warp + exponential frequency sweep** — a genuinely nice piece of engineering: the S-curve keeps both tracks near full spectrum at the fade's start/end (mimicking a real DJ mixer crossfader) and the exponential frequency interpolation respects logarithmic pitch perception. Worth reproducing independently; formulas are public DSP (Audio EQ Cookbook), not novel IP.
3. **Half-time/double-time BPM normalization before ratio computation** (`while (ratio>1.5) ratio/=2; while (ratio<0.67) ratio*=2`) — a small, correct, easily-missed detail (BPM 80 vs 160 should read as compatible, not a 2x mismatch) worth carrying forward as a pattern, independent of SimpMusic's code.
4. **Front-loaded ramp with hold** (BPM/pitch reach target within the first 60% of the crossfade, then hold) — a sound engineering idea: it ensures the bulk of the audible overlap plays at matched tempo instead of the correction "catching up" only as the outgoing track becomes inaudible. Directly applicable to AutoMix's own DSP layer.
5. **Camelot-wheel distance + bounded pitch-shift search (±1, then ±2 semitones)** — standard DJ-tool technique (harmonic mixing), well-implemented here as a small bounded search rather than an unconditional shift.
6. **Graceful numeric fallback pattern** — every ratio function returns "no adjustment" rather than guessing when data is missing, and duration factors treat missing data as moderately (not fully) incompatible. This general *pattern* (fail toward inaction, not toward false confidence) is worth adopting explicitly in AutoMix's own confidence-aware design, even though SimpMusic only applies it at the ratio/duration level, not the transition-style level (§10).
7. **Precache-ahead dual-deck lifecycle with graceful commit/cancel semantics** (`commitIncomingAsCurrentInternal`, always resolving mid-fade interruptions toward the incoming track) — a clean state-machine pattern for playback engines with concurrent deck instances, independent of the specific ExoPlayer/mpv APIs used.

None of the above require SimpMusic's specific implementation to reuse — they are documented ideas/formulas that can be re-derived from public DSP references and re-implemented cleanly.

## 12. Reuse / license disposition

SimpMusic and `core` are GPLv3 (`LICENSE` at repo root, confirmed at the pinned commit). Per `AGENTS.md` non-negotiable rule 4/`PROJECT_CHARTER.md` §12 ("Do not fork SimpMusic as the product foundation"), **no SimpMusic/`core` source is copied into this report beyond short illustrative excerpts already quoted above for evidentiary purposes**, and none should ever be pasted into AutoMix production code.

| Item | Disposition | Reason | Upstream file/symbol |
|---|---|---|---|
| Equal-power crossfade curve | `REIMPLEMENT_CLEAN_ROOM` | Standard DSP identity (`cos²+sin²=1`); no creative expression to license | `CrossfadeExoPlayerAdapter.kt` `performCrossfade` |
| Cascaded biquad LPF/HPF design | `REIMPLEMENT_CLEAN_ROOM` | Coefficients follow the public Audio EQ Cookbook (explicitly cited in SimpMusic's own doc comment); implementing the same public formulas independently carries no GPL taint | `BiquadFilter.kt` |
| Sigmoid time-warp + exponential frequency interpolation for filter sweep | `REIMPLEMENT_CLEAN_ROOM` | Documented general technique, small enough to be non-copyrightable as an idea; reimplement from the description, not the Kotlin | `CrossfadeExoPlayerAdapter.kt` `sigmoid`/`exponentialInterpolate` |
| Half/double-time BPM normalization pattern | `REIMPLEMENT_CLEAN_ROOM` | Simple loop-based normalization; standard DJ-tool technique | `calculateBpmSpeedRatio` |
| Camelot wheel lookup tables + distance function | `REIMPLEMENT_CLEAN_ROOM` | Camelot wheel is a published, standard DJ notation (not SimpMusic's invention); the lookup tables are a direct, non-creative encoding of that public system | `keyToCamelot`/`camelotDistance` |
| Front-loaded ramp-then-hold envelope shape | `REIMPLEMENT_CLEAN_ROOM` | General envelope-shaping idea, reproducible from the description in §11 | `performCrossfade` `BPM_RAMP_PORTION` logic |
| Dual-deck precache/commit/cancel state machine *pattern* | `REIMPLEMENT_CLEAN_ROOM` | Architectural pattern, not copyrightable code; AutoMix's own implementation will differ by construction (different player backend, different language/framework choices) | `CrossfadeExoPlayerAdapter.kt`/`MpvPlayerAdapter.kt` overall structure |
| Any literal Kotlin source (adapter classes, filter classes, DataStore wiring, UI composables) | `DO_NOT_REUSE` | GPLv3; `PROJECT_CHARTER.md` explicitly rules out forking SimpMusic as a foundation | All files in §4 |
| Tidal-metadata-matching approach as a *strategy* (borrow BPM/key from a third-party catalog by title+duration match) | `DO_NOT_REUSE` | Not a licensing issue — a correctness issue: §10 identifies this as the single largest metadata-confidence risk in the pipeline; AutoMix's own charter (Analysis engine target schema) calls for tempo/key *with confidence* derived from the audio itself, not a blind catalog match. Carrying this specific strategy forward would import SimpMusic's worst-verified weakness. | `YouTube.searchTidalMetadata` |
| Any Tidal API integration specifics (endpoints, OAuth flow, response shape) | `NEEDS_LICENSE_REVIEW` | Independent of GPL — Tidal's own API terms of service govern reuse of this integration approach and were not in scope for this task; flag for separate legal/API-policy review before AutoMix considers any third-party-catalog metadata source | `YouTube.kt` Tidal OAuth/search methods |

## 13. Parts that should not be carried forward

- **The Tidal-catalog-match strategy for BPM/key** (§10, §12) — the single highest-risk element of the whole pipeline; wrong-but-plausible data can poison every downstream formula silently, and AutoMix's own charter calls for confidence-scored, audio-derived analysis instead.
- **Static, per-user, global `djCrossfadeEnabled`/`crossfadeEnabled` settings as the only confidence lever** — AutoMix's charter explicitly requires low-confidence pairs to degrade gracefully to simpler transitions; SimpMusic has no per-pair mechanism to do this at all (§8 level 8, §10).
- **Fixed "N seconds/beats before file end" triggering with an always-position-0 incoming start** — this is precisely the "mathematically convenient but musically arbitrary" cue-timing failure mode the charter's Analysis Engine / Transition Planner sections are designed to avoid (§8 level 7, §10).
- **Duplicating the entire planner (duration/BPM/key math) verbatim across platforms** (§7) — an architecture smell worth explicitly avoiding: AutoMix's planner should be a single provider/platform-independent module, with only DSP execution split by backend.

## 14. Runtime unknowns / risks requiring further proof

- **Model/effort self-verification gap** (§0/§1): this agent could not cryptographically confirm "Sonnet High" as a distinct verifiable state beyond model identity (`claude-sonnet-5`) and its own engaged extended-thinking behavior. Recommend the PM independently confirm the harness's effort setting through whatever out-of-band mechanism the PM's tooling provides.
- **Tidal match-rate in practice**: what fraction of a typical SimpMusic user's library actually receives a Tidal BPM/key match at all, and at what error rate (wrong version/remix matched within the ±1s window)? Static analysis proves the *mechanism* and its risk profile; it cannot measure the real-world hit/error rate without running the app against a real library and real Tidal responses.
- **Audibility of the mpv-side DJ filter sweep**: `installCrossfadeChain`/`setCrossfadeCutoffHz` route through mpv's native `af` filter graph; this report confirms the Kotlin-side call sequence and constants are structurally parallel to Android's biquad implementation, but did not execute the app to audibly A/B the two platforms' filter sweeps.
- **Precache timing under real network conditions**: the 3-second "not precached" prep buffer and the 100ms stagger between precache loads are read from source; their sufficiency under real mobile/network latency was not measured at runtime.
- **Behavior when Cast is active** and other edge cases (video-content skip rules, retry/backoff on stream-URL expiry) were traced structurally (§5, §7) but not exercised at runtime.

## 15. P0-M2 benchmark implications

- SimpMusic AutoMix should be benchmarked in the **fixed playlist required by `PROJECT_CHARTER.md`/`P0-M0` §13** using its "Auto" duration mode with DJ mode on (its most feature-complete configuration), specifically targeting the failure modes this report predicts from source: bar-phase misalignment (even at matched BPM), vocal-outro-into-vocal-intro pairs, sequential-album-track suppression (SimpMusic has no such suppression — it will always crossfade if enabled, even for songs that should play gapless/uninterrupted), and pairs with plausible-but-wrong Tidal metadata (hard to construct deliberately, but worth including a pair where one track's Tidal-matched title is ambiguous, e.g. multiple versions with near-identical duration).
- Because SimpMusic's incoming-track start position is always `0` and its outgoing exit position is purely duration-arithmetic (§8 level 7, §10), P0-M2's "entry-point musicality" and "exit-point musicality" scoring dimensions should reliably show SimpMusic scoring at or near the low end **structurally**, not incidentally — this is a predictable, source-grounded expectation the benchmark should confirm rather than assume.
- P0-M2 should score SimpMusic separately with DJ mode **off** (plain equal-power crossfade only) vs **on** (biquad EQ sweep + bounded tempo/pitch correction), since these are meaningfully different transition qualities behind one on/off setting.

## 16. P0-M3 analyzer/cue/DSP implications

- This report gives P0-M3 a concrete, falsifiable floor to beat: any candidate analyzer stack (All-In-One, BeatNet, CUE-DETR, etc., per `P0-TECHNICAL-REFERENCE-CANDIDATES.md`) should be evaluated first on whether it can supply the exact capabilities SimpMusic lacks — beat timestamps, downbeats, phrase boundaries, section labels, candidate cue points, and a genuine confidence score — since §8/§9 confirm SimpMusic supplies none of them.
- The DSP execution layer (§6, §11) is a lower-priority P0-M3 concern than the analysis/planning gap: SimpMusic's crossfade/filter/tempo-ratio *execution* mechanics are reasonable engineering and provide a credible baseline to match or exceed with Signalsmith Stretch/Rubber Band once real cue points exist; the harder, higher-value problem P0-M3 must solve is upstream of DSP — *deciding where and whether to transition at all*, which SimpMusic does not do beyond arithmetic time-remaining.
- P0-M3 should specifically test candidate analyzers against SimpMusic's demonstrated failure mode: **metadata-confidence-blind matching**. Any analyzer whose only signal is "estimated BPM/key with no verification against actual audio content" reproduces SimpMusic's single largest weakness; P0-M3's evaluation criteria should require candidates to expose their own confidence and be tested for silent-wrong-match risk, not just headline accuracy.
