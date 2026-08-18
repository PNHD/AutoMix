## HANDOFF TO PM — P0-M6-R3-PREOWNER COMPACT SCREENSHOT UX REPAIR

### RESULT

**PASS for the requested repair scope.** Both UI defects are fixed, deterministically tested, and verified in a real browser at 1280x900 and 375x812. Per the task's own instruction, this session does not run the owner listening/UI-approval pass -- it stops at the same terminal state as before, now with the compact-screenshot defects repaired.

### A NOTE ON THIS HANDOFF'S DESIGN

Continuing the non-self-referential design from prior rounds: this file describes the work and the implementation commit; the exact final pushed HEAD and verified `main`/`research/p0-feasibility` SHAs live in a fresh, **untracked** `PM_FINAL_STATE.md`, generated after the push and included in the ZIP. The ZIP's own SHA-256 is computed after building and reported in this session's final chat response, outside any file.

### REPO / BRANCH

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab`
- **Accepted implementation HEAD for this round:** `22d2d4392c432262a31e37fa90cf445ef0f7d3c7` (verified against `origin/prototype/live-automix-lab` before any work began).
- This commit is the implementation commit for the pre-owner UI repair -- source, tests, and docs together in one commit. See `PM_FINAL_STATE.md` in the ZIP for the exact resulting final pushed HEAD.

### WHAT THIS ROUND DID

**UI Defect 1 (Spotify credential setup):** `activateSpotify()`'s connect handler now hides `#spotify-setup` (Client ID input, Save, redirect URI hint) once `connect()` actually succeeds -- strictly after both early-return branches (reauth-required, not-authenticated) have already returned, so a failed/incomplete connect never hides it. Before authentication it still shows by default, unchanged. A new "Change Spotify setup" toggle inside the collapsed Advanced panel is the recovery path: it only ever toggles visibility, never clears the stored Client ID, and reauth (`beginLogin()`) is untouched.

**UI Defect 2 (search results):** two new helpers, `collapseSeedSearch()` and `restoreSeedSearch()`. The "Play as seed" button now calls `collapseSeedSearch()` only after `playSeedTrack()` actually succeeds -- it clears the results list, hides the search input/button/results container, and reveals a small "Change seed" button. "Change seed" calls only `restoreSeedSearch()`, which reveals the search controls again and does nothing else -- no auto-search, no change to the currently playing track. Now Playing (current track, progress, Jump to last 15s) is a sibling of the collapsible search subsection, not a child, so it's never affected.

Neither fix touches Spotify provider-next-up logic, the planner, the lookahead queue controller, Local DSP, `main`, or `research/p0-feasibility` -- confirmed via `git diff --stat` showing changes confined to `index.html`, `src/app.js`, and the extended test file.

### FILES CHANGED (this round)

```
Modified:
  apps/automix-live-lab/index.html                  (+14/-4  -- seed-search-controls wrapper + Change-seed button; Change-Spotify-setup button in Advanced)
  apps/automix-live-lab/src/app.js                   (+50    -- collapseSeedSearch()/restoreSeedSearch(), hide-setup-on-connect-success, Change-Spotify-setup toggle, els refs/wiring)
  apps/automix-live-lab/tools/verify_compact_ui.mjs  (+84    -- 28 new checks, 60 -> 88)

New:
  docs/research/P0-M6-R3-PREOWNER-UI-REPAIR.md
  HANDOFF_TO_PM.md (this file)
```

Not touched: everything under `src/adapters/`, `src/engine/`, `src/styles.css`, `src/data/`, `LocalDSPPlaybackAdapter.js`, `PlaybackAdapter.js`, `SpotifyDJPartnerPlaybackAdapter.js`, `main`, `research/p0-feasibility`, and every other verifier suite.

### TESTS PASSED (exact results)

```
verify_compact_ui.mjs -> 88/88 PASS (was 60/60; +28 new checks this round)

Full regression rerun (all 27 other suites, unmodified, all still passing):
verify_pkce.mjs 12/12, verify_schedule.mjs 22/22, verify_spotify_api_response.mjs 30/30,
verify_spotify_app_debug_privacy.mjs 11/11, verify_spotify_automix_toggle.mjs 17/17,
verify_spotify_autoplay.mjs 18/18, verify_spotify_bounded_retry.mjs 35/35,
verify_spotify_candidate_pool.mjs 22/22, verify_spotify_confirmation_race.mjs 30/30,
verify_spotify_lookahead_adapter_integration.mjs 26/26, verify_spotify_lookahead_queue.mjs 47/47,
verify_spotify_near_end_probe.mjs 22/22, verify_spotify_one_lookahead.mjs 12/12,
verify_spotify_planner.mjs 30/30, verify_spotify_play_seed.mjs 10/10,
verify_spotify_preauth_race.mjs 19/19, verify_spotify_privacy_diagnostics.mjs 19/19,
verify_spotify_provider_boundary.mjs 16/16, verify_spotify_provider_next_up.mjs 38/38,
verify_spotify_provider_queue_coexistence.mjs 27/27, verify_spotify_queue_truth.mjs 46/46,
verify_spotify_recent_history.mjs 16/16, verify_spotify_scope_migration.mjs 22/22,
verify_spotify_search.mjs 17/17, verify_spotify_seed_identity.mjs 24/24,
verify_spotify_seek.mjs 22/22, verify_spotify_transfer_playback.mjs 14/14
  (Local DSP engine untouched; its 193s live session was NOT rerun)
```

**Combined: 28 suites, 712/712 PASS, 0 FAIL.** Full raw output in `VALIDATION_ALL.txt` inside the ZIP.

**Real-browser smoke check** (Browser tool, `http://127.0.0.1:5500/`):
- Pre-auth (real DOM state, no simulation): setup visible, search controls visible, "Change seed" hidden -- confirmed.
- Post-auth + post-seed screenshot state (class transitions applied match exactly what the tested code paths set) at **1280x900**: `document.body.innerText` contains none of "Spotify Client ID" / "Redirect URI to register" / "Play as seed" / "Debug log" / "Lookahead state"; `scrollWidth === innerWidth` (no overflow); zero console errors.
- Same check at **375x812**: identical result -- no leaked fields, `scrollWidth === innerWidth`, single-column grid (`gridTemplateColumns: "355.2px"`).
- Toggle round-trips verified live: `Change seed` restores search controls without altering `#queue-current`'s text; `Change Spotify setup` clicked twice reveals then re-hides the form with correct label text both ways; the Client ID input's computed `display` is confirmed `"none"` even with a value already typed into it.

### AC CHECK

| Requirement | Status | Evidence |
|---|---|---|
| Do not change recommendation/planner/queue behavior | PASS | `git diff --stat` shows zero changes under `src/adapters/`; `verify_spotify_provider_next_up.mjs`/`verify_spotify_planner.mjs`/`verify_spotify_lookahead_queue.mjs` unchanged, still 38/38, 30/30, 47/47 |
| Do not run the owner listening review | PASS | not run; terminal state below |
| Do not touch Local DSP, `main`, `research/p0-feasibility` | PASS | none touched, verified |
| Defect 1: setup hidden after connect() succeeds | PASS | `verify_compact_ui.mjs` tests 1/2 + live-browser check |
| Defect 1: setup recoverable, Client ID never cleared, reauth works | PASS | `verify_compact_ui.mjs` test 2 + live toggle round-trip |
| Defect 2: search results collapse after seed confirmed | PASS | `verify_compact_ui.mjs` test 3 + live-browser check |
| Defect 2: "Change seed" restores flow without auto-search/track-change | PASS | `verify_compact_ui.mjs` test 4 + live toggle round-trip (queue-current unchanged) |
| Screenshot target: no Client ID / redirect URI / results / debug / diagnostics | PASS | `verify_compact_ui.mjs` tests 5/6 + live-browser `body.innerText` check at both widths |
| <=600px: one column, no horizontal overflow | PASS | live-browser check at 375x812 |
| No pixel-perfect tests | PASS | all new checks are structural/behavioral (id presence, function-body shape, text-content absence, `scrollWidth`/overflow), never exact pixel values |
| Run all existing tests plus new tests | PASS | 28 suites, 712/712, 0 FAIL |

### UNKNOWNS / RISKS

- All prior-round unknowns/risks not addressed by this task remain open and unchanged, including whether Spotify's real "Next Up" head is consistently stylistically coherent -- still exactly what the pending owner UI review is for.

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -5` on `prototype/live-automix-lab` shows this session's commit directly on top of `22d2d4392c432262a31e37fa90cf445ef0f7d3c7`.
2. Re-run all 28 suites and confirm 712/712.
3. Confirm `git diff --stat 22d2d43..HEAD -- apps/automix-live-lab/src/adapters/ apps/automix-live-lab/src/engine/` is empty.
4. Confirm `main`/`research/p0-feasibility` untouched via `git rev-parse`.
5. Open `PM_FINAL_STATE.md` inside the ZIP and cross-check its stated final HEAD against `git rev-parse HEAD`, and independently re-derive the ZIP's SHA-256 against the value in this session's final chat message.
6. When ready, run the owner listening/UI-review pass below.

---

`OWNER_R3_RECOMMENDATION_UI_REVIEW_REQUIRED`

Owner check (not tester-style QA): pick one arbitrary artist with a clear stylistic identity, play it as the seed, and confirm (a) the next selection feels contextually plausible, (b) no obvious abrupt genre/language jump unless Spotify itself supplied it, (c) continuation remains functional, (d) a screenshot of the primary UI is compact/readable without opening Advanced, and now also (e) the screenshot shows no Client ID field, no redirect URI, and no leftover search-results list.
