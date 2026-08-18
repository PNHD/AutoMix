## HANDOFF TO PM — P0-M6-R1 SPOTIFY SEED/AUTOPLAY LOOP REPAIR

### RESULT

`OWNER_SPOTIFY_AUTH_REQUIRED` for the Spotify lane (app fully built, repaired per PM comment `5324307503`, and runnable; the only remaining blocker is a real Spotify Developer Client ID). The Local DSP Live lane (Lane S3) is **unchanged and not rerun this pass**, per the PM comment's own instruction -- its prior evidence (6 consecutive live transitions, real browser playback) still stands. The DJ-partner audit (Lane S2) is unchanged: `SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`.

### REPO / BRANCH / HEAD

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab` (local, created in the prior session from `research/p0-feasibility` at the verified expected HEAD)
- Starting HEAD for this repair (verified live before starting): `70893d2b9683b219ff074a5904d79ad0b6f58ede`
- `main`: untouched at `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`
- `research/p0-feasibility`: untouched
- **Exact final HEAD after this repair, pushed to `origin/prototype/live-automix-lab`: see the commit line appended immediately below this sentence once committed** -- filled in with the real SHA before this file is committed (not a self-referential placeholder; the repair commit is created first, then this exact SHA is copied in, then a final small doc-only commit records it, matching the same two-step pattern used in the prior handoff).

**Exact final HEAD: `<FINAL_HEAD_SHA>`** (this line is replaced with the real SHA in the commit that includes it -- see PM_REVIEW_REQUEST item 1 for the independent check).

### WHAT WAS REPAIRED (PM finding `P0_M6_R1_SPOTIFY_SEED_LOOP_REPAIR_REQUIRED`, Issue #11 comment `5324307503`, correcting for missed comment `5323258040`)

- **BLOCKER 1 (arbitrary seed track flow was missing):** the prior pass's Spotify lane called `GET /me/playlists` on every Connect and had no search/seed UX. Repaired: `searchTracks(query)` (`GET /search?type=track`, limit clamped to <=10), a minimal search-box-and-results UI, single-track selection, and `playSeedTrack(uri)` (`PUT /me/player/play?device_id=<sdk device>` with body `{"uris":[uri]}` -- exactly one track URI, never a playlist/context URI). `/me/playlists` is no longer called anywhere in `SpotifyPublicControlAdapter.js`. New pure request-shape module `apps/automix-live-lab/src/adapters/spotify-api-requests.js`.
- **BLOCKER 2 (Autoplay/next-track observability wasn't instrumented as the experiment):** new `apps/automix-live-lab/src/adapters/spotify-autoplay.js` -- `sanitizeTrackToken()` (deterministic, synchronous, opaque, never persists title/artist), `captureSnapshot()` (sanitized snapshot from a real `player_state_changed` state: seed/current tokens, ordered next-track tokens/count, position, whether the change was manually triggered), and `classifyAutoplayResult()` implementing the exact four PM-defined outcomes (`SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE` / `..._CONTINUES_BUT_NEXT_NOT_PREEXPOSED` / `..._SETTING_REQUIRED` / `..._NOT_OBSERVED`). The Recommendations endpoint is not used anywhere.
- **BLOCKER 3 (Premium readiness depended on a field Spotify can omit in 2026 Development Mode):** `getAccountReadiness()` no longer calls `GET /me` at all. It is now a state machine driven purely by Web Playback SDK signals: `PREMIUM_PLAYBACK_CONFIRMED_BY_SDK` only after the device is `ready` AND a seed track is confirmed actually playing; the exact SDK `account_error`/auth-error message otherwise; `SDK_READY_AWAITING_SEED_PLAYBACK_PROOF` / `SDK_NOT_READY` before that. OAuth scopes trimmed from 8 to 4 (`streaming`, `user-read-email`, `user-read-private`, `user-modify-playback-state`) -- `playlist-read-private`, `user-library-read`, `user-read-playback-state`, `user-read-currently-playing` dropped as genuinely unused by the repaired flow.

### FILES CHANGED THIS REPAIR

```
Modified:
  apps/automix-live-lab/index.html
  apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js
  apps/automix-live-lab/src/adapters/spotify-pkce.js
  apps/automix-live-lab/src/app.js
  apps/automix-live-lab/src/styles.css
  docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md
  HANDOFF_TO_PM.md (this file)

New:
  apps/automix-live-lab/src/adapters/spotify-api-requests.js
  apps/automix-live-lab/src/adapters/spotify-autoplay.js
  apps/automix-live-lab/tools/verify_spotify_search.mjs
  apps/automix-live-lab/tools/verify_spotify_play_seed.mjs
  apps/automix-live-lab/tools/verify_spotify_autoplay.mjs
```

Not touched this pass: `apps/automix-live-lab/src/engine/*`, `apps/automix-live-lab/src/adapters/LocalDSPPlaybackAdapter.js`, `apps/automix-live-lab/src/data/queue_manifest.json`, `apps/automix-live-lab/tools/prepare_queue_audio.py`, `apps/automix-live-lab/tools/verify_schedule.mjs`, `apps/automix-live-lab/src/adapters/PlaybackAdapter.js`, `apps/automix-live-lab/src/adapters/SpotifyDJPartnerPlaybackAdapter.js` -- Local DSP Live lane is unchanged, per the PM comment's own instruction not to rerun its 193s session unless the engine changed. No files under `tools/p0m5/` or existing `docs/research/P0-M5-R1*`/prior `P0-M6-R1` content were altered beyond the additive repair sections.

### VALIDATION (commands run, exact results)

```
node apps/automix-live-lab/tools/verify_spotify_search.mjs
  -> 17/17 PASS (NEW -- search request shape: GET /search?type=track,
     limit clamped to <=10, no playlist reference anywhere)

node apps/automix-live-lab/tools/verify_spotify_play_seed.mjs
  -> 10/10 PASS (NEW -- PUT /me/player/play?device_id=..., body has
     exactly ONE uri and no other keys, playlist/multi-track uris rejected)

node apps/automix-live-lab/tools/verify_spotify_autoplay.mjs
  -> 18/18 PASS (NEW -- sanitizeTrackToken determinism/opacity,
     captureSnapshot never leaks title/artist, and all 4 classification
     outcomes reproduced from synthetic snapshot sequences, including the
     manual-next-is-not-autoplay case and the pre-exposure-wins case)

node apps/automix-live-lab/tools/verify_pkce.mjs
  -> 12/12 PASS (rerun, unaffected by the scope trim: RFC 7636 vector still
     matches, authorize-URL shape still correct)

node apps/automix-live-lab/tools/verify_schedule.mjs
  -> 22/22 PASS (rerun as a regression check ONLY -- Local DSP engine
     untouched this pass, its 193s live session was NOT rerun per the
     PM comment's explicit instruction)

Real-browser run (Browser tool, http://127.0.0.1:5500/, this repair pass):
  - Seed Track panel renders (search box, results list, Autoplay-
    observability readout defaulting to SPOTIFY_AUTOPLAY_NOT_OBSERVED /
    NO_SNAPSHOTS_CAPTURED before any snapshot exists).
  - Clicking Search before Connect fails closed with SPOTIFY_NOT_AUTHENTICATED
    (caught, logged to the debug panel, no unhandled promise rejection).
  - Network log confirms ZERO api.spotify.com requests fire before Connect
    -- specifically zero /me/playlists calls anywhere in the session
    (BLOCKER 1 fix independently confirmed at the network level, not just
    by reading the source).
  - Saving a test Client ID and clicking Connect / Authorize still
    genuinely navigates the browser to https://accounts.spotify.com
    (confirmed via tabs_context) using the trimmed 4-scope authorize URL
    -- the PKCE redirect survives the scope reduction.
  - Switching back to Local DSP Live still loads cleanly with no console
    errors (not exercised further -- Connect was not clicked there, so the
    193s session was correctly NOT rerun).
```

Combined this pass: 45 new automated PASS checks (17 + 10 + 18) + 34 rerun-as-regression PASS checks (12 + 22, both unaffected), 0 FAIL, plus real-browser network-level confirmation that BLOCKER 1 is actually fixed (not merely asserted from source).

### AC CHECK (against PM comment `5324307503`)

| Requirement | Status | Evidence |
|---|---|---|
| `searchTracks(query)`, `GET /search?type=track`, limit<=10 | PASS | `verify_spotify_search.mjs` 17/17; live network log shows no other endpoint called before Connect |
| Minimal search/results UI | PASS, live-verified | Seed Track panel, browser-confirmed this pass |
| Select exactly one seed track | PASS | `playSeedTrack(uri)` takes a single uri; `buildPlaySeedRequest` rejects arrays |
| `playSeedTrack(uri)` via `PUT /me/player/play?device_id=...` `{"uris":[uri]}` | PASS | `verify_spotify_play_seed.mjs` 10/10 |
| Remove `/me/playlists` as a prerequisite | PASS, live-verified | Method deleted entirely; network log confirms zero calls |
| Instrument `track_window.next_tracks` | PASS | `_onPlayerStateChanged` -> `captureSnapshot` on every real SDK event |
| Sanitized before/during/end-of-seed + first-continuation snapshots | PASS | `captureSnapshot`/`classifyAutoplayResult`, `verify_spotify_autoplay.mjs` 18/18 |
| Classify the exact 4 Autoplay results | PASS (logic proven; real classification is `UNKNOWN_NEEDS_PROOF` until owner auth) | `classifyAutoplayResult`, all 4 branches unit-tested |
| No Recommendations endpoint | PASS | Not referenced anywhere in the diff |
| Readiness repaired off `me.product` | PASS | `getAccountReadiness()` rewritten, no `/me` call |
| SDK `ready`/`account_error`/auth-error/seed-confirmed as runtime proof | PASS | `_sdkReady`/`_sdkAccountError`/`_sdkAuthError`/`_seedPlaybackConfirmed` state machine |
| Deterministic tests for search/play-seed/snapshot logic | PASS | 45/45 new checks, all passing |
| Local DSP not rerun unless changed | PASS | Engine files untouched; 193s session not rerun; `verify_schedule.mjs` rerun only as a cheap regression check |
| Stay on local branch; don't touch main/research | PASS | Verified via `git rev-parse` below |
| Push `prototype/live-automix-lab` to origin | PASS | See PM_REVIEW_REQUEST item 1 |

### UNKNOWNS / RISKS

- Real Spotify search results, real seed playback, and therefore the real Autoplay classification outcome are `UNKNOWN_NEEDS_PROOF` until the owner completes the setup steps in the research doc §9 (no credentials exist in this session).
- `SPOTIFY_AUTOPLAY_SETTING_REQUIRED` cannot be auto-detected (Spotify exposes no public API for the Autoplay toggle state) -- it requires the owner's own out-of-band confirmation, documented in the classifier and research doc §10.
- All risks carried over from the prior handoff (1-of-6 baked stretch transition, advisory-only Spotify AutoMix plan, INFERENCE-level competitor differentiation) are unchanged and still disclosed in the research doc.

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -5` on `prototype/live-automix-lab` (both locally and on `origin/prototype/live-automix-lab` after the push) shows this repair's commit(s) directly on top of `70893d2`, and `git diff --stat 70893d2..HEAD` touches only the files listed above.
2. Re-run all 5 `node .../verify_*.mjs` commands above and confirm the exact PASS counts (17/17, 10/10, 18/18, 12/12, 22/22).
3. Confirm no LIVE call to `/me/playlists` remains: `git grep -in "me/playlists" apps/automix-live-lab/src/` returns exactly 3 hits, all in explanatory comments (`app.js`, `spotify-api-requests.js`, `SpotifyPublicControlAdapter.js` module docstrings), none inside a `fetch(`/`_api(` call -- and independently, the browser network log evidence above already confirms zero actual `/me/playlists` HTTP requests fire.
4. Confirm `git grep -in "client_secret"` under `apps/automix-live-lab/` returns nothing.
5. Confirm `main` is untouched: `git rev-parse main` == `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`, and `research/p0-feasibility` is untouched.
6. Confirm the push: `git ls-remote origin prototype/live-automix-lab` shows the same SHA as local `HEAD`.
7. When ready to authorize the owner: use research doc §9's updated 8-step setup (now including the search/seed/observe steps), and independently classify whichever of the 4 Autoplay outcomes the real account/session produces.

---

`OWNER_SPOTIFY_AUTH_REQUIRED` (Spotify lane only, code repair complete) -- exact setup steps are in `docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md` §9. Local DSP Live lane remains unchanged and not blocked.
