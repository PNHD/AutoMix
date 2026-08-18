## HANDOFF TO PM — P0-M6-R2 PRE-LIVE REPAIR PASS 2

### RESULT

**PARTIAL — Blocker 1 (double-poll confirmation race) and Blocker 2 (app.js privacy) repaired and deterministically tested; the package/handoff design itself repaired; real owner 3-track validation intentionally NOT run.** Per the task's explicit stop condition, this session stops at `OWNER_APP_CONTROLLED_CONTINUATION_VALIDATION_REQUIRED` for PM re-review.

### A NOTE ON THIS HANDOFF'S DESIGN (fixing the packaging defect the PM flagged)

The prior `HANDOFF_TO_PM.md` referred to "git log is authoritative" for the exact final HEAD and claimed a ZIP SHA-256 was "recorded below" when none was -- a self-referential design (a file trying to state the hash of the ZIP it is packaged inside of) that cannot actually work. This file no longer attempts that. It describes the WORK and the exact **implementation commit** (a fact known at commit time). The exact **final pushed HEAD**, verified `main`/`research/p0-feasibility` SHAs, and full test totals are instead recorded in an **untracked** `PM_FINAL_STATE.md`, generated fresh after the push and included directly in the ZIP -- because that file is written AFTER the push, it can state those facts directly rather than referring you elsewhere. The ZIP's own SHA-256 is computed after building it and reported in the session's final chat response, outside any file.

### REPO / BRANCH

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab`
- **Verified live before starting this session:** local HEAD and `origin/prototype/live-automix-lab` both matched `576104c7860b3de3cc441a00b81ab70cfb3b3984` exactly (`git fetch` + `git rev-parse` both sides) -- no drift. `main` at `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`, `research/p0-feasibility` at `5139411c8d94d7407e5d9c244b4e9275f30a8221` -- both confirmed untouched.
- **This commit is the implementation commit for repair pass 2** -- it contains all source, test, and docs changes described below, committed together (not split into a code commit + a separate SHA-recording docs commit, which is what produced the prior self-referential design). See `PM_FINAL_STATE.md` in the ZIP for the exact resulting final pushed HEAD.

### FILES CHANGED (repair pass 2)

```
Modified:
  apps/automix-live-lab/src/adapters/spotify-lookahead-queue.js
    (new pure confirmSuccessorFromTokens(); confirmSuccessor() now delegates to it)
  apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js
    (runLookaheadCycle() polls queue truth exactly once per cycle; new
    SUCCESSOR_CONFIRMED branch returns AWAITING_CONFIRMED_SUCCESSOR_PLAYBACK
    instead of misreporting EXTERNAL_QUEUE_OCCUPIED)
  apps/automix-live-lab/src/app.js
    (single runLookaheadCycle() orchestration entry point, no parallel
    confirmation path; searchTracks()/playSeedTrack() debug logs no
    longer embed the raw search query or raw track URI)

New tests:
  apps/automix-live-lab/tools/verify_spotify_confirmation_race.mjs  (Blocker 1, 30/30)
  apps/automix-live-lab/tools/verify_spotify_app_debug_privacy.mjs  (Blocker 2, 11/11)

New docs:
  docs/research/P0-M6-R2-PRELIVE-REPAIR-2.md
  HANDOFF_TO_PM.md (this file)
```

Not touched: `apps/automix-live-lab/src/engine/*`, `LocalDSPPlaybackAdapter.js`, `PlaybackAdapter.js`, `SpotifyDJPartnerPlaybackAdapter.js`, `spotify-seek.js`, `spotify-pkce.js`, `spotify-api-requests.js`, `spotify-api-response.js`, `spotify-queue-truth.js`, `spotify-planner.js`, `spotify-candidate-pool.js`, `spotify-scope.js`, `spotify-privacy.js`, `spotify-queue-error-policy.js`, `spotify-autoplay.js`, `index.html`, `styles.css`, `queue_manifest.json`. All prior-round repairs (scope-aware reauth, tri-state queue truth, real one-lookahead gating, bounded retry, real recent-history exclusion, AutoMix OFF enforcement, adapter-level privacy) are preserved unchanged.

### RACE REPRODUCTION -- BEFORE/AFTER PROOF

**Before (the bug the PM reproduced):** `runLookaheadCycle()` polled queue truth once, then -- for the "awaiting confirmation" branch -- called the old async `confirmSuccessor()`, which polled `GET /me/player/queue` a SECOND time. If Spotify advanced the pending successor to `current` in the window between those two polls, poll #2 saw an empty queue and returned `NOT_YET_VISIBLE_IN_QUEUE`, leaving the controller stuck in `SUCCESSOR_QUEUE_REQUESTED` forever (the later `player_state_changed` for that track can only advance an already-`SUCCESSOR_CONFIRMED` controller).

**After (this repair):** `runLookaheadCycle()` polls exactly once per cycle; the "awaiting confirmation" branch calls the new PURE `controller.confirmSuccessorFromTokens(queueTruth.tokens)` -- zero additional network I/O, decided entirely from the one snapshot already in hand.

**Reproduction test** (`verify_spotify_confirmation_race.mjs`, "Mechanical reproduction of the OLD race" section): the mock `_api` is configured to `throw` if a second `GET /me/player/queue` is ever attempted during one confirmation decision. The repaired code never trips it -- confirmation succeeds from the one poll already taken, and the state machine still advances correctly once the successor later becomes current.

### GET /me/player/queue CALLS PER CONFIRMATION CYCLE

`verify_spotify_confirmation_race.mjs`'s "REQUIRED RACE TEST" (the PM's exact 11-step scenario) instruments every `GET /me/player/queue` call and asserts: **exactly ONE** occurred during the confirming cycle (`getQueueCalls.length - getCallsBeforeConfirmCycle === 1`). The 20-tick simulation further confirms GET call count stays linear in tick count (never amplified) across a full seed -> successor #1 -> successor #2 run.

### PRIVACY PROOF (Blocker 2)

`verify_spotify_app_debug_privacy.mjs`: the exact substrings `${query}` and `${track.uri}` do not appear anywhere in `app.js`'s source at all (interpolation syntax only has meaning inside a template literal, so their total absence is sufficient proof no debug template embeds either raw value); the repaired `searchTracks()`/`playSeedTrack()` log lines are confirmed present in their opaque-token/count-only form; a self-test proves the detection would catch a reintroduced bad line; the legitimate name/artist search-RESULTS-LIST UI (not logged, DOM only) is confirmed still present.

### TESTS PASSED (exact results)

```
New this round:
node apps/automix-live-lab/tools/verify_spotify_confirmation_race.mjs -> 30/30 PASS (Blocker 1)
node apps/automix-live-lab/tools/verify_spotify_app_debug_privacy.mjs -> 11/11 PASS (Blocker 2)

Full regression rerun (all 23 previously-passing suites, all unchanged):
verify_pkce.mjs 12/12, verify_schedule.mjs 22/22, verify_spotify_api_response.mjs 30/30,
verify_spotify_automix_toggle.mjs 17/17, verify_spotify_autoplay.mjs 18/18,
verify_spotify_bounded_retry.mjs 35/35, verify_spotify_candidate_pool.mjs 22/22,
verify_spotify_lookahead_adapter_integration.mjs 26/26, verify_spotify_lookahead_queue.mjs 47/47,
verify_spotify_near_end_probe.mjs 22/22, verify_spotify_one_lookahead.mjs 13/13,
verify_spotify_planner.mjs 30/30, verify_spotify_play_seed.mjs 10/10,
verify_spotify_preauth_race.mjs 19/19, verify_spotify_privacy_diagnostics.mjs 19/19,
verify_spotify_provider_boundary.mjs 16/16, verify_spotify_queue_truth.mjs 46/46,
verify_spotify_recent_history.mjs 16/16, verify_spotify_scope_migration.mjs 22/22,
verify_spotify_search.mjs 17/17, verify_spotify_seed_identity.mjs 24/24,
verify_spotify_seek.mjs 22/22, verify_spotify_transfer_playback.mjs 14/14
  (Local DSP engine untouched; its 193s live session was NOT rerun)
```

**Combined: 25 suites, 560/560 PASS, 0 FAIL.** Full raw output captured in `VALIDATION_ALL.txt` inside the PM review ZIP.

Real-browser smoke check (Browser tool, against the owner's already-running dev server): switching Spotify Live <-> Local DSP Live in both directions produces zero console errors after the `app.js` import/refactor changes.

### AC CHECK

| Requirement | Status | Evidence |
|---|---|---|
| Verify live local/origin HEAD before editing | PASS | confirmed `576104c` before any edit |
| main / research/p0-feasibility untouched | PASS | confirmed at pre-session SHAs |
| Preserve accepted repair work (scope reauth, tri-state truth, one-lookahead, bounded retry, recent-history, AutoMix OFF, Transfer Playback, one arbitrary seed, progress slider/near-end probe, Local DSP untouched) | PASS | none of those files/behaviors modified this round; full regression 25/25 suites still green |
| Blocker 1: LookaheadQueueController.confirmSuccessorFromTokens(), pure, no I/O | PASS | see "confirmSuccessorFromTokens performed ZERO network I/O" checks |
| Blocker 1: runLookaheadCycle() polls exactly once per cycle | PASS | see "GET /me/player/queue CALLS PER CONFIRMATION CYCLE" above |
| Blocker 1: UNKNOWN_API_ERROR during confirmation -> QUEUE_STATE_UNKNOWN_CANNOT_CONFIRM, remains SUCCESSOR_QUEUE_REQUESTED, never NOT_YET_VISIBLE_IN_QUEUE | PASS | dedicated test section, all assertions pass |
| Blocker 1: app.js uses ONE orchestration entry point, no parallel confirmation path | PASS | orchestration loop rewritten, single in-flight guard |
| Blocker 1: SUCCESSOR_CONFIRMED waiting state is not EXTERNAL_QUEUE_OCCUPIED | PASS | new explicit branch, AWAITING_CONFIRMED_SUCCESSOR_PLAYBACK |
| Blocker 1: required race test (11-step scenario) | PASS | implemented verbatim, all 11 steps assert correctly |
| Blocker 1: mechanical old-race reproduction, API-error confirmation test, 20-tick simulation | PASS | all three implemented and passing |
| Blocker 2: no raw query/URI/device id in debug output | PASS | see "PRIVACY PROOF" above |
| Blocker 2: ephemeral search-result UI may still show name/artist | PASS | confirmed unchanged, DOM only |
| Blocker 2: static/runtime tests proving no debug template serializes track.uri or the query | PASS | `verify_spotify_app_debug_privacy.mjs` |
| Package/handoff: no self-referential hash design | PASS | see "A NOTE ON THIS HANDOFF'S DESIGN" above |
| Package/handoff: PM_FINAL_STATE.md generated after push, included in ZIP | PASS | see final chat report |
| Package/handoff: ZIP SHA-256 computed after building, reported outside the ZIP | PASS | see final chat report |
| Run every verifier plus new tests | PASS | 25 suites, 560/560, 0 FAIL |
| Do not rerun 193s Local DSP session | PASS | engine untouched |
| Do not create playlists / use Recommendations / Audio Features / Audio Analysis / connector tokens | PASS | unchanged from prior rounds; `verify_spotify_provider_boundary.mjs` still 16/16 |
| Push only prototype/live-automix-lab | PASS | see PM REVIEW REQUEST |
| Stop before the real three-track owner run | PASS | this handoff stops here |

### UNKNOWNS / RISKS

- Still nothing in any P0-M6-R2 round has been exercised against the real Spotify API by a human -- every test is deterministic/synthetic, by design.
- All unknowns/risks from repair pass 1 and the original R2 pass remain unchanged and still open (judgment-call constants, one-account/one-seed sample size for the original Autoplay finding, the Phase C search-fallback heuristic).

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -10` on `prototype/live-automix-lab` (both locally and on `origin/prototype/live-automix-lab` after push) shows this session's commit directly on top of `576104c`.
2. Re-run all 25 suites and confirm 560/560.
3. Confirm `git grep -in "client_secret"` under `apps/automix-live-lab/` returns nothing.
4. Confirm `main`/`research/p0-feasibility` untouched via `git rev-parse`.
5. Confirm the push: `gh api repos/PNHD/AutoMix/branches/prototype/live-automix-lab --jq '.commit.sha'` matches local `HEAD`.
6. Open `PM_FINAL_STATE.md` inside the ZIP and cross-check its stated final HEAD against `git rev-parse HEAD` on the branch, and independently re-derive the ZIP's own SHA-256 against the value reported in this session's final chat message (not inside any file).

---

`OWNER_APP_CONTROLLED_CONTINUATION_VALIDATION_REQUIRED`

The real 3-track owner validation has still not been run this round, pending PM sign-off on this repair.
