## HANDOFF TO PM — P0-M6-R2 PROVIDER-QUEUE-COEXISTENCE REPAIR

### RESULT

**PARTIAL — bounded provider-semantics repair complete and deterministically tested; real owner 3-track validation resumed but not yet completed (stopped mid-guide by this real-world finding).** This session was actively guiding the owner through the accepted `503f36e` build's real 3-track validation when the owner discovered, in the official Spotify client itself, that Spotify keeps its own "Next Up" queue populated after any track plays -- invalidating the app's `KNOWN_NONEMPTY == owner conflict` assumption. Per instruction, this session made ONE bounded repair of that exact defect and stops here for the owner to resume validation.

### A NOTE ON THIS HANDOFF'S DESIGN

Continuing the non-self-referential design from the prior repair pass: this file describes the work and the implementation commit; the exact final pushed HEAD, verified `main`/`research/p0-feasibility` SHAs, and full test totals live in a fresh, **untracked** `PM_FINAL_STATE.md`, generated after the push and included in the ZIP. The ZIP's own SHA-256 is computed after building and reported in this session's final chat response, outside any file.

### REPO / BRANCH

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab`
- **Accepted starting point for this round:** `503f36ebb46cfbad7d10168525936625f0fba77d` (the PM-accepted, gate-cleared HEAD this session began the real owner run against).
- **This commit is the implementation commit for the provider-queue-coexistence repair** -- source, tests, and docs together in one commit. See `PM_FINAL_STATE.md` in the ZIP for the exact resulting final pushed HEAD.

### THE FINDING (verbatim substance)

The owner, mid-live-test, opened the official Spotify client and confirmed visually that playing any single arbitrary track causes Spotify itself to populate a "Next Up" queue -- with no practical bulk-clear flow (only per-item removal). The live AutoMix app's `GET /me/player/queue` therefore returned `KNOWN_NONEMPTY` (~10 items) immediately after a single seed play, even though the owner never manually queued anything. The app's prior logic (from the previous repair round) treated ANY `KNOWN_NONEMPTY` real queue as `EXTERNAL_QUEUE_OCCUPIED` and refused to make AutoMix progress -- a false blocker.

### THE REPAIR

Spotify's public `POST /me/player/queue` is documented as "add an item to be played next" -- play-next semantics, not append. The repair replaces the empty-queue prerequisite with a play-next policy:

1. `canInjectToQueue` (`spotify-queue-truth.js`) now allows injection for `KNOWN_EMPTY` OR `KNOWN_NONEMPTY` -- forbidden only for a genuinely unknown queue state (never polled, or the last poll errored).
2. `confirmSuccessorFromTokens` (`spotify-lookahead-queue.js`) now requires the pending successor to occupy `tokens[0]` (the play-next/head position), not merely `tokens.includes(pendingToken)` -- a successor visible only later in the queue (behind provider items, or appended at the end) is correctly NOT confirmed.
3. `runLookaheadCycle()` (`SpotifyPublicControlAdapter.js`) no longer blocks on a non-empty queue; it captures the pre-injection snapshot as `_lastBaselineQueueTokens` (diagnostics only, never cleared/reordered) and proceeds to select + inject exactly as on an empty queue.
4. `getLookaheadStatus()` gained `providerQueueSize`, `pendingAutoMixSuccessor`, `successorIsPlayNext` -- all informational, sanitized (opaque tokens / counts only), never a blocker.
5. Two new UI status rows ("Successor is play-next", "Provider queue size") so the owner can see, live, whether the real API actually places the successor at the head during the retest.

### FILES CHANGED (this round)

```
Modified:
  apps/automix-live-lab/index.html                                    (2 new status rows)
  apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js   (runLookaheadCycle policy change, getLookaheadStatus new fields)
  apps/automix-live-lab/src/adapters/spotify-lookahead-queue.js       (confirmSuccessorFromTokens play-next check)
  apps/automix-live-lab/src/adapters/spotify-queue-truth.js           (canInjectToQueue allows KNOWN_NONEMPTY)
  apps/automix-live-lab/src/app.js                                    (renders the 2 new status rows)
  apps/automix-live-lab/tools/verify_spotify_one_lookahead.mjs        (obsolete "external queue blocks" test replaced)
  apps/automix-live-lab/tools/verify_spotify_queue_truth.mjs          (canInjectToQueue assertion updated for the new policy)

New:
  apps/automix-live-lab/tools/verify_spotify_provider_queue_coexistence.mjs  (27/27 -- probe + 12 required tests)
  docs/research/P0-M6-R2-PROVIDER-QUEUE-COEXISTENCE.md
  HANDOFF_TO_PM.md (this file)
```

Not touched: everything else from prior rounds (scope-aware reauth, tri-state error diagnostics beyond the KNOWN_NONEMPTY policy change, bounded retry, real recent-history exclusion, AutoMix OFF gating, the confirmation-race single-poll fix, app.js debug-log privacy). `spotify-pkce.js`, `spotify-api-requests.js`, `spotify-api-response.js`, `spotify-planner.js`, `spotify-candidate-pool.js`, `spotify-scope.js`, `spotify-privacy.js`, `spotify-queue-error-policy.js`, `spotify-autoplay.js`, `spotify-seek.js`, `styles.css`, `queue_manifest.json`, everything under `src/engine/`, `LocalDSPPlaybackAdapter.js`, `PlaybackAdapter.js`, `SpotifyDJPartnerPlaybackAdapter.js` -- none touched.

### DETERMINISTIC PROVIDER-SEMANTICS PROBE (before/after logic proof)

`verify_spotify_provider_queue_coexistence.mjs`'s probe: given a baseline queue `[A, B, C]` and a POST for candidate `X`, a confirmation snapshot of `[X, A, B, C]` (play-next placement) is recognized as CONFIRMED; a snapshot of `[A, B, C, X]` (appended, not play-next) is recognized as NOT confirmed and the controller correctly stays `SUCCESSOR_QUEUE_REQUESTED` rather than false-confirming. **This proves the app's decision logic is correct for both shapes -- it is NOT proof of which shape the real Spotify API actually returns.** That determination is exactly what the resumed owner retest is for.

### TESTS PASSED (exact results)

```
New this round:
node apps/automix-live-lab/tools/verify_spotify_provider_queue_coexistence.mjs -> 27/27 PASS

Full regression rerun (all 25 previously-passing suites, 2 updated for the intentional policy change, all passing):
verify_pkce.mjs 12/12, verify_schedule.mjs 22/22, verify_spotify_api_response.mjs 30/30,
verify_spotify_app_debug_privacy.mjs 11/11, verify_spotify_automix_toggle.mjs 17/17,
verify_spotify_autoplay.mjs 18/18, verify_spotify_bounded_retry.mjs 35/35,
verify_spotify_candidate_pool.mjs 22/22, verify_spotify_confirmation_race.mjs 30/30,
verify_spotify_lookahead_adapter_integration.mjs 26/26, verify_spotify_lookahead_queue.mjs 47/47,
verify_spotify_near_end_probe.mjs 22/22, verify_spotify_one_lookahead.mjs 12/12,
verify_spotify_planner.mjs 30/30, verify_spotify_play_seed.mjs 10/10,
verify_spotify_preauth_race.mjs 19/19, verify_spotify_privacy_diagnostics.mjs 19/19,
verify_spotify_provider_boundary.mjs 16/16, verify_spotify_queue_truth.mjs 46/46,
verify_spotify_recent_history.mjs 16/16, verify_spotify_scope_migration.mjs 22/22,
verify_spotify_search.mjs 17/17, verify_spotify_seed_identity.mjs 24/24,
verify_spotify_seek.mjs 22/22, verify_spotify_transfer_playback.mjs 14/14
  (Local DSP engine untouched; its 193s live session was NOT rerun)
```

**Combined: 26 suites, 586/586 PASS, 0 FAIL.** Full raw output in `VALIDATION_ALL.txt` inside the ZIP.

Real-browser smoke check (Browser tool): the two new status rows render correctly (`--` / `0` at rest before any seed), switching Spotify Live <-> Local DSP Live produces zero console errors.

### AC CHECK

| Requirement | Status | Evidence |
|---|---|---|
| Do not touch Local DSP, main, research/p0-feasibility, or P1 | PASS | none touched; verified `main`/`research` SHAs unchanged |
| Replace empty-queue prerequisite with play-next policy | PASS | `canInjectToQueue` now allows KNOWN_NONEMPTY |
| Confirm via queue.tokens[0] === pendingSuccessorToken, not "exists somewhere" | PASS | `confirmSuccessorFromTokens` rewritten; probe test proves both shapes |
| Existing provider queue items behind the successor remain untouched | PASS | no delete/reorder call exists; test 8 proves provider items persist across two successor cycles |
| Exactly one app-controlled lookahead still applies | PASS | test 11 (20-tick simulation), unchanged idempotency mechanism |
| Truthful terminology: PROVIDER_QUEUE_PRESENT / providerQueueSize, not EXTERNAL_QUEUE_OCCUPIED | PASS | old reason/branch removed; new informational fields added |
| No raw IDs/titles/artists in tracked diagnostics | PASS | test 12 |
| Deterministic provider-semantics probe added before broadening logic | PASS | see "DETERMINISTIC PROVIDER-SEMANTICS PROBE" above |
| All 12 required tests | PASS | `verify_spotify_provider_queue_coexistence.mjs`, 27/27 |
| Run all existing suites plus new tests | PASS | 26 suites, 586/586, 0 FAIL |
| Keep server running, stop for owner retest after tests pass | PASS | server left running; this handoff stops here |

### UNKNOWNS / RISKS

- Whether the real Spotify API actually places an app-queued item at the immediate play-next position when a provider queue already exists is `UNKNOWN_NEEDS_PROOF` -- exactly what the resumed owner retest will establish. If it does NOT, the correct terminal state is `SPOTIFY_ADD_QUEUE_NOT_PLAY_NEXT_IN_RUNTIME`, not a further workaround in this pass.
- All prior-round unknowns/risks remain unchanged and still open.

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -10` on `prototype/live-automix-lab` shows this session's commit directly on top of `503f36e`.
2. Re-run all 26 suites and confirm 586/586.
3. Confirm `git grep -in "client_secret"` under `apps/automix-live-lab/` returns nothing.
4. Confirm `main`/`research/p0-feasibility` untouched via `git rev-parse`.
5. Open `PM_FINAL_STATE.md` inside the ZIP and cross-check its stated final HEAD against `git rev-parse HEAD`, and independently re-derive the ZIP's SHA-256 against the value in this session's final chat message.

---

`OWNER_PROVIDER_QUEUE_COEXISTENCE_RETEST_REQUIRED`

The server remains running at `http://127.0.0.1:5500/`. Next step: resume the owner's live 3-track validation from where it paused for this repair.
