## HANDOFF TO PM — P0-M6-R2 PRE-LIVE REPAIR

### RESULT

**PARTIAL — all 7 blockers repaired and deterministically tested; real owner 3-track validation intentionally NOT run.** Per the task's explicit stop condition ("Do NOT begin the real 3-track owner run yet" / stop at `OWNER_APP_CONTROLLED_CONTINUATION_VALIDATION_REQUIRED`), this session repaired every blocker the PM's independent review found (scope-aware reauth, tri-state queue truth, real one-lookahead gating, bounded cross-tick retry, real recent-history exclusion, AutoMix OFF enforcement, privacy-safe diagnostics) plus the stale-`HANDOFF_TO_PM.md` packaging defect, and stops here for PM re-review.

### REPO / BRANCH / HEAD

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab`
- Expected starting HEAD (per task): `faa4e4d` (prefix)
- **Verified live before starting:** local HEAD and `origin/prototype/live-automix-lab` both matched `faa4e4d99f75817df1218cf52163ce73c112f33f` exactly (`git fetch` + `git rev-parse` both sides) -- no drift. `main` at `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`, `research/p0-feasibility` at `5139411c8d94d7407e5d9c244b4e9275f30a8221` -- both confirmed untouched (matched their pre-session origin SHAs exactly; no commands run against either ref this session).
- Code commit (this session): `9b4660df2bdc95911831a4b8f2074bc16f600461`, directly on top of `faa4e4d`.
- **Exact final HEAD after push:** this HANDOFF_TO_PM.md commit itself, immediately on top of `9b4660d` -- `git log --oneline -3` on `prototype/live-automix-lab` is authoritative.

### FILES CHANGED

```
Modified:
  apps/automix-live-lab/index.html
  apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js
  apps/automix-live-lab/src/adapters/spotify-api-response.js
  apps/automix-live-lab/src/adapters/spotify-autoplay.js
  apps/automix-live-lab/src/adapters/spotify-candidate-pool.js
  apps/automix-live-lab/src/adapters/spotify-lookahead-queue.js
  apps/automix-live-lab/src/adapters/spotify-planner.js
  apps/automix-live-lab/src/adapters/spotify-queue-truth.js
  apps/automix-live-lab/src/app.js
  apps/automix-live-lab/tools/verify_spotify_lookahead_adapter_integration.mjs (rewritten for real-queue-truth gating)
  apps/automix-live-lab/tools/verify_spotify_queue_truth.mjs (rewritten for the tri-state model)

New source (one per blocker, where a new pure module was warranted):
  apps/automix-live-lab/src/adapters/spotify-scope.js              (Blocker 1)
  apps/automix-live-lab/src/adapters/spotify-privacy.js            (Blocker 7)
  apps/automix-live-lab/src/adapters/spotify-queue-error-policy.js (Blocker 4)

New tests (one dedicated suite per blocker):
  apps/automix-live-lab/tools/verify_spotify_scope_migration.mjs      (Blocker 1, 22/22)
  apps/automix-live-lab/tools/verify_spotify_one_lookahead.mjs        (Blocker 3, 13/13)
  apps/automix-live-lab/tools/verify_spotify_bounded_retry.mjs        (Blocker 4, 35/35)
  apps/automix-live-lab/tools/verify_spotify_recent_history.mjs       (Blocker 5, 16/16)
  apps/automix-live-lab/tools/verify_spotify_automix_toggle.mjs       (Blocker 6, 17/17)
  apps/automix-live-lab/tools/verify_spotify_privacy_diagnostics.mjs  (Blocker 7, 19/19)

New docs:
  docs/research/P0-M6-R2-PRELIVE-REPAIR.md
  HANDOFF_TO_PM.md (this file -- see "PACKAGING DEFECT FIX" below)
```

Not touched: `apps/automix-live-lab/src/engine/*`, `LocalDSPPlaybackAdapter.js`, `PlaybackAdapter.js`, `SpotifyDJPartnerPlaybackAdapter.js`, `spotify-seek.js`, `spotify-pkce.js`, `spotify-api-requests.js`, `queue_manifest.json`, `styles.css`. No files under `tools/p0m3/`, `tools/p0m5/`, or any existing `docs/research/P0-M5*`/`P0-M6-R1*`/`P0-M6-R2-APP-CONTROLLED-CONTINUATION-QUEUE.md` content touched.

### PACKAGING DEFECT FIX

The PM found the previous `P0-M6-R2-PM-REVIEW.zip` shipped the OLD `P0-M6-R1` `HANDOFF_TO_PM.md`. Root cause: the ZIP was built (and its hash computed) BEFORE `HANDOFF_TO_PM.md` was rewritten for that round -- the file the ZIP grabbed off disk was still last round's content. Fixed this round by reordering the build: this exact `HANDOFF_TO_PM.md` was written and finalized FIRST, THEN the ZIP was built from the resulting working tree (so the ZIP's copy and this file are identical), and only THEN was this file committed. There is no reason for those two to diverge this time.

### SCOPES (unchanged from prior round, now correctly migrated)

Still the same 7 scopes added in the original R2 pass -- `streaming`, `user-read-email`, `user-read-private`, `user-modify-playback-state`, `user-read-playback-state`, `user-top-read`, `user-read-recently-played`. What changed THIS round is enforcement: a token that predates these scopes (or is missing even one) is now automatically detected and discarded on `connect()`, routing the owner back through PKCE with zero manual steps (Blocker 1). If the owner already went through the R2 reauthorization once, no further action should be needed -- `connect()` will simply confirm the stored token's scope set still covers everything and proceed normally.

### TESTS PASSED (exact results)

```
New this round (one dedicated suite per blocker):
node apps/automix-live-lab/tools/verify_spotify_scope_migration.mjs      -> 22/22 PASS (Blocker 1)
node apps/automix-live-lab/tools/verify_spotify_one_lookahead.mjs       -> 13/13 PASS (Blocker 3)
node apps/automix-live-lab/tools/verify_spotify_bounded_retry.mjs       -> 35/35 PASS (Blocker 4)
node apps/automix-live-lab/tools/verify_spotify_recent_history.mjs      -> 16/16 PASS (Blocker 5)
node apps/automix-live-lab/tools/verify_spotify_automix_toggle.mjs      -> 17/17 PASS (Blocker 6)
node apps/automix-live-lab/tools/verify_spotify_privacy_diagnostics.mjs -> 19/19 PASS (Blocker 7)

Rewritten in place (Blocker 2 + the real-queue-truth-gated orchestration, Blocker 3):
node apps/automix-live-lab/tools/verify_spotify_queue_truth.mjs               -> 46/46 PASS
node apps/automix-live-lab/tools/verify_spotify_lookahead_adapter_integration.mjs -> 26/26 PASS

Full regression rerun (all previously-passing suites, all unchanged):
node apps/automix-live-lab/tools/verify_pkce.mjs                  -> 12/12 PASS
node apps/automix-live-lab/tools/verify_schedule.mjs              -> 22/22 PASS
node apps/automix-live-lab/tools/verify_spotify_api_response.mjs  -> 30/30 PASS
node apps/automix-live-lab/tools/verify_spotify_autoplay.mjs      -> 18/18 PASS
node apps/automix-live-lab/tools/verify_spotify_candidate_pool.mjs -> 22/22 PASS
node apps/automix-live-lab/tools/verify_spotify_lookahead_queue.mjs -> 47/47 PASS
node apps/automix-live-lab/tools/verify_spotify_near_end_probe.mjs -> 22/22 PASS
node apps/automix-live-lab/tools/verify_spotify_planner.mjs       -> 30/30 PASS
node apps/automix-live-lab/tools/verify_spotify_play_seed.mjs     -> 10/10 PASS
node apps/automix-live-lab/tools/verify_spotify_preauth_race.mjs  -> 19/19 PASS
node apps/automix-live-lab/tools/verify_spotify_provider_boundary.mjs -> 16/16 PASS
node apps/automix-live-lab/tools/verify_spotify_search.mjs        -> 17/17 PASS
node apps/automix-live-lab/tools/verify_spotify_seed_identity.mjs -> 24/24 PASS
node apps/automix-live-lab/tools/verify_spotify_seek.mjs          -> 22/22 PASS
node apps/automix-live-lab/tools/verify_spotify_transfer_playback.mjs -> 14/14 PASS
  (Local DSP engine untouched; its 193s live session was NOT rerun, per task instruction)
```

**Combined: 23 suites, 519/519 PASS, 0 FAIL.** Full raw output captured in `VALIDATION_ALL.txt` inside the PM review ZIP.

Real-browser smoke check (Browser tool, against the owner's already-running dev server at `http://127.0.0.1:5500/`): the new "Queue blocker" / "AutoMix queueing" status rows render (`none` / `ON` at rest), the Next control correctly starts disabled showing the new `QUEUE_STATE_UNKNOWN_NOT_POLLED` label (not a flat "empty"), and switching Spotify Live <-> Local DSP Live in both directions produces zero console errors. Static/no-login smoke check only -- no real Spotify account touched.

### SCOPE MIGRATION PROOF (Blocker 1)

`verify_spotify_scope_migration.mjs`, driving the REAL adapter with a minimal in-memory `localStorage` shim (not a reimplementation): a legacy token with no `scope` field at all -> `SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES`, token discarded from storage; a token missing exactly one required scope -> same result; a token with the complete (or superset) scope set -> `AUTHENTICATED`, token untouched; a refresh response omitting `scope` preserves the previously-known set, one that includes `scope` overwrites it; the Client ID survives a token-invalidating reauth in both the storage layer and the `_clientId` getter; `app.js`'s Connect handler is statically confirmed to recognize the new reason string and re-trigger `beginLogin()`; `connect()`'s result object never contains the access token.

### ONE-LOOKAHEAD PROOF (Blocker 3)

`verify_spotify_one_lookahead.mjs` (13/13) plus `verify_spotify_lookahead_adapter_integration.mjs` (26/26, real adapter, stateful mock queue): a `KNOWN_EMPTY` real queue queues exactly one successor; a second tick with our own pending token now visible in the real queue confirms it and issues zero additional POSTs; an external (not-ours) token in the real queue yields `EXTERNAL_QUEUE_OCCUPIED` with zero POSTs and never even fetches the candidate pool; a real queue-truth API error yields `QUEUE_STATE_UNKNOWN_CANNOT_INJECT` with zero POSTs; 10 duplicate orchestration ticks in a row produce exactly one POST total.

### BOUNDED RETRY PROOF (Blocker 4)

`verify_spotify_bounded_retry.mjs` (35/35): a 404 excludes only that one candidate (no cooldown) and a different candidate succeeds on the very next tick; a 403 sets a terminal auth blocker that stays active across 10+ further ticks with zero additional POSTs; a 429 honors a real `Retry-After: 5` header, blocks all attempts until (simulated, `Date.now()`-controlled) 5 seconds elapse, then resumes automatically; a 500 exhausts its 3 bounded in-cycle attempts then sets a cooldown rather than retrying a 4th time immediately; a 20-orchestration-tick simulation against a permanently-failing endpoint produces exactly 3 total POSTs (one bounded cycle), not the 60 an unbounded retry loop would have produced.

### REAL RECENT-HISTORY PROOF (Blocker 5)

`verify_spotify_recent_history.mjs` (16/16): a track present in BOTH Top Tracks and Recently Played keeps its `TOP_TRACK_AFFINITY` tag AND its `recentPlayRank` (previously silently dropped by the pool dedup); a track inside the real recent-repeat window is hard-excluded as `RECENT_REPEAT_EXCLUDED`, genuinely distinct from `ALREADY_PLAYED_THIS_SESSION` (a track played only THIS session vs. one only in real account history each get their own distinct exclusion reason in the same selection call); an older eligible top track wins ranking over a just-played top track; the adapter-level integration test confirms `runLookaheadCycle()` sources `recentRepeatWindowIds` from real `GET /me/player/recently-played` history (`_lastRecentlyPlayedIds`), not from `_sessionPlayedIds`.

### AUTOMIX OFF PROOF (Blocker 6)

`verify_spotify_automix_toggle.mjs` (17/17): AutoMix defaults ON; toggling OFF before a seed is inert (no API calls); OFF after an active seed with an empty real queue returns `AUTOMIX_DISABLED` with zero POSTs (queue truth is still polled so the owner sees truthful status); OFF does not block confirming a successor that was already queued before the toggle, and does not start a second successor once that one becomes current; toggling back ON resumes exactly one selection cycle; `LocalDSPPlaybackAdapter.js` (separate class) is confirmed untouched.

### AC CHECK

| Requirement | Status | Evidence |
|---|---|---|
| Verify live local/origin HEAD before editing, don't assume the abbreviated SHA | PASS | `git fetch` + `git rev-parse` both sides confirmed `faa4e4d` before any edit |
| main / research/p0-feasibility untouched | PASS | both confirmed at their pre-session SHAs |
| Preserve accepted R2 implementation except where blockers require change | PASS | `spotify-pkce.js`, `spotify-api-requests.js`, Phase D/E core algorithms unchanged; only the specifically-flagged gaps repaired |
| Blocker 1: scope storage/comparison/discard/reauth routing | PASS | see "SCOPE MIGRATION PROOF" above |
| Blocker 2: tri-state queue truth, sanitized error diagnostics, Next disabled for EMPTY/UNKNOWN, injection only on KNOWN_EMPTY, confirmation never converts an error into NOT_YET_VISIBLE | PASS | `verify_spotify_queue_truth.mjs` 46/46 |
| Blocker 3: one-track lookahead gated on real queue truth | PASS | see "ONE-LOOKAHEAD PROOF" above |
| Blocker 4: bounded retry across ticks, per-failure-type classification, 20-tick simulation | PASS | see "BOUNDED RETRY PROOF" above |
| Blocker 5: real recent-history exclusion, dedup no longer drops recentPlayRank | PASS | see "REAL RECENT-HISTORY PROOF" above |
| Blocker 6: AutoMix OFF stops new queueing, doesn't falsely claim un-queueing, Local DSP unaffected | PASS | see "AUTOMIX OFF PROOF" above |
| Blocker 7: no raw URI/ID/device ID in errors/debug output | PASS | `verify_spotify_privacy_diagnostics.mjs` 19/19 -- query-string stripped from `SpotifyApiError.path`, device tokens opaque |
| HANDOFF_TO_PM.md packaging defect fixed, ZIP contains the correct final version | PASS | see "PACKAGING DEFECT FIX" above |
| No Recommendations/Audio Features/Audio Analysis/deprecated endpoints; no playlist creation; no connector-token dependency | PASS | unchanged from prior round; `verify_spotify_provider_boundary.mjs` still 16/16 |
| Run every existing verifier plus all new tests | PASS | 23 suites, 519/519, 0 FAIL |
| Do not rerun 193s Local DSP session (engine untouched) | PASS | no engine files modified |
| Do not start production P1 | PASS | no P1 work performed |
| Push only `prototype/live-automix-lab` | PASS | see PM REVIEW REQUEST |
| Stop before the real three-track owner run | PASS | this handoff stops here |

### UNKNOWNS / RISKS

- Still nothing in this repair (or the original R2 pass) has been exercised against the real Spotify API by a human -- every test above is deterministic/synthetic, by design (the task explicitly stops before the real owner run). In particular, the exact real response shapes for `POST /me/player/queue` failures (401/403/429/404/5xx bodies) are `UNKNOWN_NEEDS_PROOF`; the classification logic in `spotify-queue-error-policy.js` is written against Spotify's documented status codes, not an observed real error.
- `RECENT_REPEAT_WINDOW_SIZE` (20), `MAX_QUEUE_REQUEST_ATTEMPTS` (3), and the default cooldown durations (30s) remain judgment calls, not owner-specified constants -- flagged for PM/owner review, not hidden.
- All P0-M6-R1 and prior-round P0-M6-R2 unknowns/risks (manual-action attribution timeout, DJ-partner-access boundary, one-account/one-seed sample size for the original Autoplay-not-observed finding, the Phase C bounded-search-fallback heuristic) remain unchanged and still open.

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -10` on `prototype/live-automix-lab` (both locally and on `origin/prototype/live-automix-lab` after push) shows this session's commit(s) directly on top of `faa4e4d`.
2. Re-run all 23 suites (`node apps/automix-live-lab/tools/verify_*.mjs`) and confirm 519/519.
3. Confirm `git grep -in "client_secret"` under `apps/automix-live-lab/` returns nothing (real code, not prose lines in this file).
4. Confirm `main`/`research/p0-feasibility` untouched via `git rev-parse`.
5. Confirm the push: `gh api repos/PNHD/AutoMix/branches/prototype/live-automix-lab --jq '.commit.sha'` matches local `HEAD`.
6. Independently re-derive the ZIP's SHA-256 and compare to the value recorded below, and confirm `HANDOFF_TO_PM.md` inside the ZIP is byte-identical to this file (the packaging-defect fix).

---

`OWNER_APP_CONTROLLED_CONTINUATION_VALIDATION_REQUIRED`

Next step for the owner, pending PM sign-off on this repair (server already running at `http://127.0.0.1:5500/`, per the owner's own instruction to keep it up):

1. Reload the page, reconnect (Connect/Authorize) -- if this is the owner's first connect since the original R2 scope additions, `connect()` will now automatically detect the insufficient stored token and redirect through PKCE with the new scopes; if already reauthorized once, it should connect immediately.
2. Search and play ONE arbitrary seed. Do not click Search/Add/Next/any playlist action again after this.
3. Watch the new "App-controlled continuation queue" panel (state, candidate pool size, selection reason, refill count, consecutive-automatic-track count) AND the new "Queue blocker" / "AutoMix queueing" status rows -- any real failure should now show a genuine, specific blocker (e.g. `TERMINAL_AUTH_BLOCKER`, `COOLDOWN -- retrying in ~Ns`, `EXTERNAL_QUEUE_OCCUPIED`) instead of silently doing nothing.
4. Use "Jump to last 15s" (existing near-end probe) to reach the seed's natural end quickly.
5. Confirm Spotify itself advances to the queued successor (refill count 1, consecutive-automatic-track count 2).
6. Confirm a second successor is automatically selected and queued, jump to its last 15s, confirm Spotify advances to it too (refill count 2, consecutive-automatic-track count >= 3).
7. Report the exact panel/status values at each step, or the exact endpoint/HTTP status/sanitized body of whichever call first fails, per the task's terminal-state contract.
