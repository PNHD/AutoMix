# P0-M6-R1 — Spotify-First Live AutoMix Prototype + Competitive Baseline

Status date: 2026-08-18

Binding task: GitHub Issue #11, with Issue #11's Apple-first sections OVERRIDDEN by PM comments `5323227813` ("Spotify-first product correction") and `5323231023` ("Spotify Native Mix is now a required competitor baseline"), per the owner's direct routing of this session. Issue #11's original SwiftUI/Apple-first execution mode was not followed; per the owner's explicit instruction this session built a web prototype instead ("Prefer a web prototype first if it gets to runnable validation faster").

## R0. Repair pass -- binding PM review and scope

This document was repaired once, in the same session/branch, in response to PM review result `P0_M6_R1_SPOTIFY_SEED_LOOP_REPAIR_REQUIRED` (Issue #11 comment `5324307503`), which itself corrects the prior pass for missing the binding product comment `5323258040` ("PM PRODUCT TARGET CORRECTION -- SEED-ANY-SONG, NO PLAYLIST AUTHORING"). Starting HEAD for this repair: `70893d2b9683b219ff074a5904d79ad0b6f58ede` (this session's own prior commit, verified live before the repair).

The prior pass's Spotify lane centered `/me/playlists` and resuming existing playback. The actual product loop, per `5323258040` and reaffirmed by `5324307503`, is: **search ONE arbitrary track -> play that ONE track as a seed -> observe whether Spotify's own Autoplay supplies a continuation -> later feed those candidates to AutoMix once legitimate DJ-partner audio access exists.** No playlist creation or playlist-first workflow is the primary UX.

Three blockers, each traceable to its own PM finding, repaired in this pass:

- **BLOCKER 1 -- arbitrary seed track flow was missing.** Added `searchTracks(query)` (`GET /search?type=track`, Development Mode `limit` clamped to <=10), a minimal search/results UI, seed selection, and `playSeedTrack(uri)` (`PUT /me/player/play?device_id=...` with body `{"uris":[uri]}` -- exactly one track URI, never a playlist/context URI). `/me/playlists` is no longer called anywhere in the Spotify lane. New pure request-shape module `src/adapters/spotify-api-requests.js`, unit-tested in `tools/verify_spotify_search.mjs` (17/17) and `tools/verify_spotify_play_seed.mjs` (10/10).
- **BLOCKER 2 -- Autoplay/next-track observability was not instrumented as the experiment.** New `src/adapters/spotify-autoplay.js`: `sanitizeTrackToken()` (deterministic, synchronous, non-cryptographic opaque token, never persists title/artist), `captureSnapshot()` (sanitized snapshot from a real `player_state_changed` state object: seed/current tokens, ordered next-track tokens/count, position, whether continuation was manually triggered), and `classifyAutoplayResult()` implementing the exact four PM-defined outcomes. Unit-tested in `tools/verify_spotify_autoplay.mjs` (18/18), including a case proving a manually-triggered `next()` click is never misclassified as autoplay continuation, and a case proving next-track pre-exposure is detected even when the track later changes. The Recommendations endpoint is not used anywhere (BLOCKER 2 explicitly forbids it).
- **BLOCKER 3 -- Premium readiness relied on `GET /me` -> `product`, a field Spotify's Feb-2026 Development Mode migration can omit.** `getAccountReadiness()` no longer calls `/me` at all. Readiness is now a state machine driven purely by Web Playback SDK signals: `PREMIUM_PLAYBACK_CONFIRMED_BY_SDK` only after the device reaches `ready` AND a seed track is confirmed actually playing; the exact SDK `account_error`/`authentication_error` message otherwise; `SDK_READY_AWAITING_SEED_PLAYBACK_PROOF` once the device is registered but no seed is confirmed yet; `SDK_NOT_READY` before that. OAuth scopes were also trimmed from 8 to the 4 the repaired core flow actually needs (`streaming`, `user-read-email`, `user-read-private`, `user-modify-playback-state`) -- `playlist-read-private`, `user-library-read`, `user-read-playback-state`, and `user-read-currently-playing` were dropped as genuinely unused by the repaired flow, per the PM comment's explicit instruction not to broaden scopes.

The Local DSP Live lane (§6) was not modified in this repair pass and its 193-second live session was deliberately not rerun, per the PM comment's own instruction ("Local DSP does not need another 193s rerun unless changed"). `verify_schedule.mjs` was rerun as a regression check only (22/22, unchanged).

## R1. Repair pass 2 -- seed identity/manual-attribution repair

This document was repaired a second time, in the same session/branch, in response to PM review result `P0_M6_R1_SEED_IDENTITY_REPAIR_REQUIRED` (Issue #11 comment `5324583196`), starting from the previously pushed HEAD `85af4c91cd257969337a0560ff045d15586d31c9` (PM independently re-verified this exact SHA, plus the prior PM-review ZIP's SHA-256/size/member count, before filing this finding). Live branch/`main`/`research/p0-feasibility` state matched exactly; no live-state drift.

PM's re-review accepted repair pass 1's product-loop shape (search -> one-URI seed -> observe) but found the seed-identity bookkeeping internally inconsistent in a way that would have invalidated the runtime proof on a real account:

- **BLOCKER 1 (seed token hashed the URI while runtime snapshots hashed the bare track id):** `playSeedTrack(uri)` stored `sanitizeTrackToken(uri)` where `uri` is `spotify:track:<id>`, but `_onPlayerStateChanged`/`captureSnapshot` hashed `current_track.id`, which is just `<id>` -- two different input strings for the same song can never hash equal, so `_seedPlaybackConfirmed` could never become true and the seed's own first playback could be misread as a non-seed continuation. Repaired at the single source: `sanitizeTrackToken` (`spotify-autoplay.js`) now canonicalizes id-vs-uri via a new small pure helper, `canonicalTrackId`, before hashing -- `token(<id>) === token(spotify:track:<id>)` by construction, and every call site (seed selection, runtime state) automatically inherits the fix with zero duplicated parsing logic.
- **BLOCKER 2 (manual-next attribution cleared too early):** the prior pass's `_manualActionPending` boolean was cleared on the FIRST `player_state_changed` event after a manual `next()`/`seek()` call, even if that event still showed the same track (the SDK can fire more than one state event per user action). A later, still-manually-caused track-change event could then arrive with the flag already cleared and be misclassified as Spotify Autoplay. Repaired with a small state machine (`beginManualAction`/`resolveManualAttribution`, `spotify-autoplay.js`) that stays attributed across same-track intermediate events and resolves (clears) only when the current track actually changes, or after one fixed, bounded timeout (`MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS = 8000`, not pair/song-specific).

New deterministic INTEGRATION-level test file, `tools/verify_spotify_seed_identity.mjs` (24/24 PASS), driving the real `SpotifyPublicControlAdapter` class (not a reimplementation) with synthetic Web Playback SDK state objects through `_onPlayerStateChanged`/`next()`/`seek()`, proving: the core token-equality invariant; a URI-selected seed is recognized as `isSeedStillCurrent=true` and confirms playback when the SDK reports it by bare id, and is never misclassified as continuation; only a genuinely different track id becomes continuation evidence; the full manual-Next -> intermediate same-track event -> changed-track event sequence stays attributed throughout and does not classify as Autoplay; the bounded timeout is enforced; and sanitized snapshot privacy still holds (no raw id, uri scheme, or title/artist text leaks).

All previously-passing suites were rerun as regression checks (17/17 search, 10/10 play-seed, 18/18 autoplay, 12/12 PKCE, 22/22 schedule) -- all still pass unchanged. The Local DSP Live 193-second session was, again, deliberately NOT rerun, per this comment's own instruction.

## 0. Execution profile actually used

- **Execution surface:** Claude Desktop → Code.
- **Model:** `claude-sonnet-5`.
- **Sub-agents:** OFF (none spawned; AGENTS.md default, no task authorization to override it).
- **Dynamic workflows:** OFF.

## 1. Result

`OWNER_SPOTIFY_AUTH_REQUIRED` for Lane S1 (app is fully built, runs, and correctly gates at the one external blocker: a real Spotify Developer Client ID). Lane S3 (Local DSP Live) is **fully runnable and independently verified in this session**, not blocked. Lane S2 (DJ partner audit) is complete. Required product classification (§8): **`SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`**.

## 2. Live-state verification

| Check | Value |
|---|---|
| Branch | `prototype/live-automix-lab`, created from `research/p0-feasibility` |
| HEAD at session start | `5139411c8d94d7407e5d9c244b4e9275f30a8221` — matched Issue #11's expected HEAD exactly |
| `main` | `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa` — untouched |

Issue #11 was read in full via `gh issue view 11`. PM comments `5323227813` and `5323231023` were read in full via `gh api repos/PNHD/AutoMix/issues/comments/<id>`.

## 3. Provider abstraction (Lane 3 of the owner's routing message)

`apps/automix-live-lab/src/adapters/PlaybackAdapter.js` defines the single interface the UI and (in a future pass) the AutoMix planner are allowed to call: `connect`, `isConnected`, `getAccountReadiness`, `loadQueue`, `getQueue`, `getPlaybackState`, `play`, `pause`, `next`, `seek`, `getAutoMixPlan`, `setAutoMixEnabled`, `onStateChange`, plus a `capability` getter restricted to `LOCAL_DSP_FULL | PUBLIC_CONTROL_ONLY | PARTNER_ACCESS_REQUIRED`.

Three concrete adapters implement it:

- `LocalDSPPlaybackAdapter.js` -- `LOCAL_DSP_FULL`.
- `SpotifyPublicControlAdapter.js` -- `PUBLIC_CONTROL_ONLY`.
- `SpotifyDJPartnerPlaybackAdapter.js` -- `PARTNER_ACCESS_REQUIRED`, a documented stub (every method returns/throws `SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`), shaped so a future real implementation would not require touching the planner, the UI, or the other two adapters.

The AutoMix DSP/planner logic (the P0-M5-R1 frozen pair manifest, Beat This anchors, Signalsmith stretch usage) has zero import-time or runtime dependency on any Spotify module -- `LocalDSPPlaybackAdapter.js` and `deck-engine.js` never import anything under `adapters/Spotify*` (AGENTS.md rule 5).

## 4. Lane S1 -- Spotify public web prototype

**Built:** `apps/automix-live-lab/` (index.html + vanilla ES modules, no bundler/npm dependency -- "fastest runnable prototype"). Runs via `python apps/automix-live-lab/server/server.py 5500`, binds `127.0.0.1:5500` (loopback IP literal, not `localhost`, per Spotify's current redirect-URI policy).

**Implemented (`SpotifyPublicControlAdapter.js`, repaired this pass -- see R0):**
- Authorization Code with PKCE, fully client-side (`spotify-pkce.js`) -- no client secret is ever requested, stored, or transmitted. PKCE code-challenge generation was verified against the **official RFC 7636 Appendix B test vector** (not just "it runs") -- see §6. Scopes trimmed to the 4 the repaired flow actually needs (R0, BLOCKER 3).
- `searchTracks(query)` -- `GET /search?type=track`, limit clamped to <=10 (R0, BLOCKER 1).
- A minimal search box + results list; the owner picks exactly ONE arbitrary track as the seed.
- `playSeedTrack(uri)` -- `PUT /me/player/play?device_id=<sdk device>` with body `{"uris":[uri]}`, exactly one track URI, never a playlist/context URI (R0, BLOCKER 1). `/me/playlists` is not called anywhere in this file.
- Current/next track + playback state via the Web Playback SDK's `player_state_changed` event; every real event is also turned into a sanitized Autoplay-observability snapshot (R0, BLOCKER 2, `spotify-autoplay.js`).
- Play/pause/next/seek via the SDK (manual `next()`/`seek()` calls are flagged so a resulting track change is never misclassified as autoplay continuation).
- `capability` is hardcoded to `PUBLIC_CONTROL_ONLY` and cannot be upgraded by any runtime state.
- `getAccountReadiness()` no longer reads `GET /me` -> `product` at all (R0, BLOCKER 3) -- see R0 for the new SDK-signal-driven state machine.
- `getAutoMixPlan()` is explicitly advisory-only (`executesRealDsp: false`) and never claims tempo/key data it cannot obtain -- see §5's finding that Audio Features/Audio Analysis are unavailable to new apps. The Recommendations endpoint is never used.

**Runtime evidence (this session, via the Browser tool, no real Spotify credentials available):**
- App loads clean, no console errors. The Seed Track panel (search box + results + Autoplay-observability readout) renders correctly and defaults to `SPOTIFY_AUTOPLAY_NOT_OBSERVED` / `NO_SNAPSHOTS_CAPTURED` before any snapshot exists.
- Clicking Search before authenticating fails closed with `SPOTIFY_NOT_AUTHENTICATED` (caught, logged, no unhandled rejection) -- confirmed via the browser console this repair pass. No `/me/playlists` (or any `api.spotify.com`) request is observed on the network log before Connect is clicked -- confirmed via `read_network_requests`.
- `capability: PUBLIC_CONTROL_ONLY` renders correctly; `getAutoMixPlan()` correctly reports `NO_ACTIVE_SPOTIFY_PLAYBACK` / `executesRealDsp: no (advisory only)` before any playback exists.
- Clicking Connect with no Client ID configured correctly blocks client-side with `OWNER_SPOTIFY_AUTH_REQUIRED`-style messaging instead of throwing an unhandled error.
- **Bug found and fixed in an EARLIER pass** (not reintroduced): the adapter originally captured the Client ID once at construction time, so saving a Client ID in the UI *after* the adapter was created was silently ignored on the next Connect click. Fixed by making `_clientId` a live getter that reads `localStorage` on every call. Re-verified with the trimmed 4-scope authorize URL: saving a Client ID and clicking Connect still genuinely navigates the browser to `https://accounts.spotify.com` (Spotify's real login page rendered, confirmed via `tabs_context`). No further login was attempted; this session holds no real Spotify account credentials and none were entered anywhere.
- **Bug found and fixed in R1 (this repair pass):** `sanitizeTrackToken` was called with two differently-shaped inputs -- the full `spotify:track:<id>` URI at seed-selection time, and the bare `<id>` at every subsequent runtime state event -- so the seed's own token could never match its own later playback, silently breaking seed-playback confirmation and risking a false Autoplay-continuation classification on the seed's own first play event. Fixed at the single hashing entry point (`canonicalTrackId`, R1 §above); proven with 24 new integration-level checks driving the real adapter class, not just the pure hash function in isolation.

**Not testable without owner credentials (honest gap, not hidden):** actual token exchange, actual search results, actual seed playback, actual Premium-gated Web Playback SDK device registration, and therefore which of the four PM-defined Autoplay classifications a real session would produce:

- `SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE` -- `next_tracks` populated while the seed was still current.
- `SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED` -- continuation happens, but only becomes visible once it starts.
- `SPOTIFY_AUTOPLAY_SETTING_REQUIRED` -- no continuation, and the owner has separately confirmed Autoplay is off in account/device settings.
- `SPOTIFY_AUTOPLAY_NOT_OBSERVED` -- no continuation and the setting state is unknown (the mechanical default when nothing else applies).

These require a real Spotify Developer Client ID -- see §9 for exact owner setup steps. The request SHAPES for search and seed-playback, and the snapshot-capture/classification LOGIC for all four outcomes, are proven deterministically without credentials (R0; 45 new automated checks in `tools/verify_spotify_search.mjs`, `tools/verify_spotify_play_seed.mjs`, `tools/verify_spotify_autoplay.mjs`).

## 5. Lane S2 -- Spotify DJ partner route audit

Researched via official/current sources only (`developer.spotify.com`, `newsroom.spotify.com`, Algoriddim's own site), per `automix-forensic-research` skill's source-order rule.

| Question | Finding | Tag |
|---|---|---|
| Which DJ apps have Spotify catalog access today? | rekordbox, Serato (DJ Lite/Pro), djay (Algoriddim) | `FACT` -- [Spotify Newsroom, 2025-09-24](https://newsroom.spotify.com/2025-09-24/dj-software-integration-premium/) |
| Platforms/timeline | Desktop from 2025-09-24; rekordbox + djay expanded to iOS/Android 2025-12-11 | `FACT` -- same source + [Newsroom DJ-integration tag](https://newsroom.spotify.com/tag/dj-software-integration) |
| Markets | 51 markets at launch (region-limited, not global) | `FACT` -- same source |
| Account requirement | Spotify Premium | `FACT` -- same source |
| What can these apps do? | "mix songs from Spotify using supported DJ software" / "track-to-track transitions"; Algoriddim states djay's Automix does real-time, beat-matched, continuous mixing of Spotify tracks via its own Fluid Beatgrid engine | `FACT` for the newsroom wording; `FACT` (vendor claim) for [Algoriddim's Spotify page](https://www.algoriddim.com/spotify) -- not independently reproduced by this session (no partner access) |
| Personal/non-commercial limit | Confirmed by secondary reporting (DJ TechTools, ClubDJ Pro) that Spotify content via these integrations is licensed for personal, non-commercial use only | `INFERENCE` from secondary sources, not the primary Newsroom post itself |
| Is there a public developer SDK/API for this DJ-audio entitlement? | **No public application process, SDK, or documentation was found** on `developer.spotify.com` for the DJ-partner audio-mixing entitlement. The commercial-hardware partner program page exists and is organization-only/application-gated, but nothing analogous is documented for DJ software. | `NOT_FOUND_IN_PINNED... ` -- more precisely `UNKNOWN_NEEDS_PROOF` (absence of public evidence is not proof no private application channel exists) |
| Does the public policy forbid this for ordinary apps? | Yes, explicitly: "Do not permit any device or system to segue, mix, re-mix, or overlap any Spotify Content with any other audio content" (Section III.7) | `FACT` -- [developer.spotify.com/policy](https://developer.spotify.com/policy) |

**Conclusion:** `SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`. The three named apps hold a licensed partner entitlement distinct from, and not obtainable through, the ordinary public Client ID / Web API / Web Playback SDK. AGENTS.md rule 6 was followed: no attempt was made to infer or approximate this access. `SpotifyDJPartnerPlaybackAdapter.js` (§3) documents this boundary instead of working around it.

## 6. Lane S3 -- Local DSP Live AutoMix (mandatory, fully proven)

**Design:** reuses the frozen, already-accepted P0-M5-R1 8-pair manifest (`tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json`) verbatim -- no Beat This re-run, no pair re-discovery. The 6 dev-split pairs form a 6-item live queue (>=5 transitions required by the task; 6 delivered):

- 5 of 6 pairs (tempo_ratio=1.0, no correction needed) are played as genuine **live two-deck Web Audio** transitions: `deck-engine.js` schedules both AudioBufferSourceNodes against a single shared `AudioContext` clock, with equal-power gain crossfade (`setValueCurveAtTime`, the same constant-power law as `dsp/mixing.py`'s `equal_power_gains`, independently implemented for the Web Audio AudioParam API) and a live bass/EQ handoff (`BiquadFilterNode` low-shelf automation at 150 Hz, `BASS_HANDOFF_SPEED=2.2` -- both constants reused verbatim from `dsp/mixing.py`) computed and applied **at runtime**, not pre-rendered.
- The 1 remaining pair (`S01`, `RM055->RM052`, tempo_ratio=0.9688, a genuine 3.12% correction) reuses the exact, already safety-checked, already accepted `S01_M1.wav` offline render **verbatim** as one scheduled queue item. This is disclosed, not hidden: a real-time AudioWorklet port of Signalsmith was out of scope for this pass (see §10 unknowns). The engine still schedules it gaplessly against its live neighbors.
- Beat/downbeat anchors, exit/entry timestamps, and tempo ratios are read verbatim from the frozen manifest (`beat_downbeat_sync: true` on every item) -- never recomputed.
- Incoming tracks are never rate/pitch-shifted -- "incoming continues at native tempo" is true by construction (`inSrc.playbackRate` is never touched).

**Mathematical proof (no browser needed):** `apps/automix-live-lab/tools/verify_schedule.mjs` runs the exact same `computeQueueSchedule()` function the browser engine uses and proves, from the real prepared queue manifest:

```
[PASS] queue has exactly 6 items
[PASS] transitionCount >= 5 (task requirement)
[PASS] schedule is gapless end-to-end (zero-gap, zero-overlap chaining)
... (22 checks total)
RESULT: 22/22 PASS
Schedule summary: 6 transitions, total session 193.44s
```

**PKCE correctness proof (no browser needed):** `apps/automix-live-lab/tools/verify_pkce.mjs` proves `generateCodeChallenge()` against the **official RFC 7636 Appendix B test vector** and the authorize-URL shape against Spotify's documented PKCE parameters:

```
[PASS] S256 code_challenge matches RFC 7636 Appendix B test vector
... (12 checks total)
RESULT: 12/12 PASS
```

**Real-browser runtime proof (this session, via the Browser tool, `http://127.0.0.1:5500/`):**

All 11 prepared audio files (`GET /work_local/queue_audio/*.wav`) loaded `200 OK`. `connect()` created a live `AudioContext`; `loadQueue()` scheduled the exact same 6-item timeline computed offline. The session was then observed **live, in real wall-clock time**, through all 6 transitions:

| Transition boundary | Wall-clock observed |
|---|---|
| S01 -> S04 | 03:46:01.270 -> 03:46:01.429 |
| S04 -> S05 | 03:46:32.910 -> 03:46:32.932 |
| S05 -> S06 | 03:47:04.550 -> 03:47:04.686 |
| S06 -> S07 | 03:47:37.150 -> 03:47:37.181 |
| S07 -> S08 | 03:48:08.350 -> 03:48:08.437 |
| S08 ends | 03:48:39.869 |

Total elapsed from first `now_playing` (03:45:26.685) to final `item_ended` (03:48:39.869) = **193.18s real time**, against a mathematically scheduled **193.44s** -- a 0.26s difference, fully explained by this session's 250ms UI-polling interval (i.e. our *observation* granularity, not an actual audio gap: the Web Audio nodes themselves are scheduled against one sample-accurate `AudioContext` clock via `.start(exactTime)`/`setValueCurveAtTime(...,exactTime,...)`, not polled). **6 consecutive transitions, continuous playback, zero manual intervention between them -- satisfies "prove at least 5 consecutive transitions."**

## 7. Competitor baseline (required by PM comment `5323231023`)

| Baseline | Capability (as publicly documented) | Access for this project |
|---|---|---|
| `SPOTIFY_NATIVE_MIX_AUTO` | Premium "Mix" feature: user taps Mix -> Auto on a playlist; Spotify applies "volume/EQ/effect curves" between tracks; Smart Reorder (launched 2026-02-25) reorders a mixed playlist by BPM/key first. Per-playlist editing workflow, not literally a from-scratch continuous live DJ session -- `INFERENCE` from [Spotify Newsroom, 2026-02-25](https://newsroom.spotify.com/2026-02-25/smart-reorder-playlist-mixing/); exact audio-DSP mechanism (crossfade only vs. tempo-stretched beatmatching) is not documented publicly -- `UNKNOWN_NEEDS_PROOF`. 220M+ hours streamed since 2025 launch (Spotify's own figure). | Native first-party feature; not something this project can access or extend via public API (Audio Features/Analysis are deprecated for new apps -- §5-adjacent finding, `FACT`, [Spotify Community](https://community.spotify.com/t5/Spotify-for-Developers/Depending-on-deprecated-Audio-Features-API-for-my-Thesis-Help/td-p/6741862) / multiple 2026 developer blog posts, deprecation dated 2024-11-27). |
| `DJAY_SPOTIFY_AUTOMIX` | Algoriddim states djay's Automix does continuous, real-time, beat-matched mixing of Spotify tracks via its own "Fluid Beatgrid" engine -- `FACT` (vendor claim), not independently reproduced here (`SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`, §5). | Blocked -- licensed partner entitlement, not public API. |
| `AUTOMIX_LOCAL_ENGINE` | This session's Lane S3 build: genuine live two-deck Web Audio scheduling, Beat-This-anchored exit/entry, <=6% Signalsmith-stretch-covered tempo correction (1/6 items), live bass/EQ handoff, 6 consecutive gapless transitions, independently verified both mathematically (34 total automated checks, §6) and in real browser playback. | Fully in this project's control; the part of the roadmap actually validated end-to-end this session. |

**Required differentiation assessment (PM comment `5323231023`):** our engine's plausible material advantage over `SPOTIFY_NATIVE_MIX_AUTO` is genuine bar-accurate, beat/downbeat-anchored, pitch-preserving tempo correction (Beat This anchors + Signalsmith stretch) executed as part of continuous live playback with zero per-transition manual authoring, versus Spotify's documented "volume/EQ/effect curves" + BPM/key-based *reordering* (a scheduling optimization, not stated to include audible tempo-stretch/beatmatch of the audio itself). **This is `INFERENCE`, not `FACT`** -- Spotify has not published its transition DSP mechanism, and this project does not have hands-on access to Spotify Mix Auto's actual audio output to A/B against our engine. Flagged `UNKNOWN_NEEDS_PROOF`: a future task should capture a real Spotify Mix Auto transition (screen-record with owner's own Premium account, personal listening only, no redistribution) and compare it directly against this session's local-engine output.

## 8. Required product classification

**`SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`**

- Ordinary public Spotify Client ID access (`SPOTIFY_PUBLIC_API_SUFFICIENT`) is proven insufficient for real AutoMix DSP: policy explicitly forbids mixing Spotify Content (§5), and Audio Features/Audio Analysis are unavailable to new apps regardless.
- The local engine is demonstrably NOT the blocker (`LOCAL_ENGINE_REPAIR_REQUIRED` does not apply) -- §6 is fully proven, working, independently verified evidence from this same session.
- A legitimate route to Spotify-catalog live mixing does exist in the market (djay/rekordbox/Serato, §5) -- so `SPOTIFY_ROUTE_NOT_VIABLE` is too strong; the accurate classification is that the route exists but requires the same licensed partner access those three vendors hold, which this project does not have and, per AGENTS.md, must not attempt to obtain by inference or bypass.

## 9. `OWNER_SPOTIFY_AUTH_REQUIRED` -- exact setup steps

1. Go to https://developer.spotify.com/dashboard and log in with a Spotify account. (As of Feb 2026, Spotify requires the developer account itself to hold an active Premium subscription to create an app.)
2. Create an app. Any name/description; no "website" required.
3. In app settings, add exactly this Redirect URI: `http://127.0.0.1:5500/` (must match byte-for-byte what `apps/automix-live-lab/index.html` displays under "Redirect URI to register" -- it is computed from `window.location.origin + pathname` at runtime, so keep the server on port 5500 or update both sides together).
4. Copy the app's **Client ID** (no client secret is needed or used -- this app uses PKCE only).
5. Run `python apps/automix-live-lab/server/server.py 5500`, open `http://127.0.0.1:5500/`, switch to "Spotify Live", paste the Client ID into the setup box, click Save, click "Connect / Authorize".
6. Log in with a **Premium** Spotify account when redirected (Web Playback SDK requires Premium; a Free account will authenticate but `getAccountReadiness()` will correctly report `ready: false`).
7. In the "Seed track" panel, type any search term, click Search, then click "Play as seed" next to exactly one result.
8. Watch the "Autoplay observability" readout: once the seed is confirmed playing (`PREMIUM_PLAYBACK_CONFIRMED_BY_SDK` should also appear under Account readiness), let it play through toward its end without clicking anything else, and note which of the four classifications (§4) the app settles on. If Spotify's Autoplay setting is off for that account/device, enable it under the Spotify app's Playback settings and retry.

## 10. Unknowns / risks

- `UNKNOWN_NEEDS_PROOF`: real Spotify token exchange, real search results, real seed playback, and real Web Playback SDK device registration were never exercised (no owner credentials available this session). The PKCE math and the authorize redirect are proven (§6); the token-exchange HTTP call itself was not. Which of the four Autoplay classifications (§4) a real account/session produces is therefore also `UNKNOWN_NEEDS_PROOF` until the owner completes §9.
- `UNKNOWN_NEEDS_PROOF`: whether Spotify's actual DJ-partner application process exists privately (only its absence from public documentation is established, not its non-existence).
- `SPOTIFY_AUTOPLAY_SETTING_REQUIRED` cannot be detected automatically -- Spotify does not expose the Autoplay toggle state through any public API this session found. The classifier accepts an out-of-band `autoplayConfirmedDisabled` flag the owner sets after checking their own account/device settings (R0, `spotify-autoplay.js`); without it, "no continuation observed" always resolves to `SPOTIFY_AUTOPLAY_NOT_OBSERVED`.
- Disclosed scope gap: 1 of 6 live-queue transitions reuses a pre-rendered stretch (§6) rather than a real-time Signalsmith AudioWorklet; a genuinely live per-sample pitch-preserving stretch was out of scope for "fastest runnable prototype" this pass.
- The live bass/EQ handoff uses a standard Web Audio `BiquadFilterNode` low-shelf, which approximates but is not byte-identical to `dsp/mixing.py`'s offline `lfilter`-based EQ swap -- conceptually the same accepted technique (150 Hz cutoff, 2.2x handoff speed reused verbatim), not a byte-identical port.
- `owner_music_input/` source tracks and all decoded/rendered audio remain local-only, gitignored, never committed -- consistent with every prior P0 milestone's practice and AGENTS.md rule 4.

## 11. Validation results

**Prior pass (unchanged, Local DSP Live not rerun this pass per PM instruction):**
```
node apps/automix-live-lab/tools/verify_schedule.mjs   -> 22/22 PASS (rerun this pass as a regression check only)
python apps/automix-live-lab/tools/prepare_queue_audio.py -> 6/6 queue items prepared (not rerun -- unchanged)
Real-browser session (prior pass): Local DSP Live -- 6/6 queue items scheduled and
  played through in real time, 6 consecutive transitions observed live,
  193.18s actual vs 193.44s computed. Not rerun this pass (engine unchanged).
```

**This repair pass (R0, new):**
```
node apps/automix-live-lab/tools/verify_pkce.mjs            -> 12/12 PASS (rerun, unaffected by scope trim)
node apps/automix-live-lab/tools/verify_spotify_search.mjs  -> 17/17 PASS (NEW -- BLOCKER 1)
node apps/automix-live-lab/tools/verify_spotify_play_seed.mjs -> 10/10 PASS (NEW -- BLOCKER 1)
node apps/automix-live-lab/tools/verify_spotify_autoplay.mjs  -> 18/18 PASS (NEW -- BLOCKER 2)

Real-browser session (Browser tool, http://127.0.0.1:5500/, this repair pass):
  - Spotify Live: Seed Track panel renders (search box, results, Autoplay-
    observability readout defaulting to SPOTIFY_AUTOPLAY_NOT_OBSERVED /
    NO_SNAPSHOTS_CAPTURED); clicking Search before auth fails closed with
    SPOTIFY_NOT_AUTHENTICATED (caught, logged, no unhandled rejection);
    network log confirms zero api.spotify.com requests fire before Connect
    (specifically zero /me/playlists calls, BLOCKER 1); PKCE redirect to
    https://accounts.spotify.com reconfirmed live with the trimmed 4-scope
    authorize URL (BLOCKER 3); switching back to Local DSP Live still loads
    cleanly (not exercised further, per the no-rerun instruction).
```

**Repair pass 2 (R1, new -- seed identity/manual attribution):**
```
node apps/automix-live-lab/tools/verify_spotify_seed_identity.mjs -> 24/24 PASS (NEW -- BLOCKER 1 + BLOCKER 2,
  integration-level, drives the real SpotifyPublicControlAdapter class)

Full regression rerun of every previously-passing suite (all unchanged):
node apps/automix-live-lab/tools/verify_spotify_search.mjs      -> 17/17 PASS
node apps/automix-live-lab/tools/verify_spotify_play_seed.mjs   -> 10/10 PASS
node apps/automix-live-lab/tools/verify_spotify_autoplay.mjs    -> 18/18 PASS
node apps/automix-live-lab/tools/verify_pkce.mjs                -> 12/12 PASS
node apps/automix-live-lab/tools/verify_schedule.mjs            -> 22/22 PASS (Local DSP engine untouched, 193s session NOT rerun)

Real-browser smoke check (Browser tool, http://127.0.0.1:5500/, this pass):
  app loads cleanly with zero console errors after the repair; Local DSP
  Live's Connect button was NOT clicked (193s session correctly not rerun).
```

Combined this pass: 24 new PASS + 79 regression-rerun PASS = 103/103, 0 FAIL.

Combined this pass: 45 new automated PASS checks (17 + 10 + 18), plus 12 PKCE + 22 schedule rerun as regression checks (both still passing), 0 FAIL, plus real-browser runtime evidence for the repaired Spotify flow.
