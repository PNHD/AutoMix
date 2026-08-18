# P0-M6-R2 — Provider-Queue-Coexistence Repair

Status date: 2026-08-18

Binding finding: a REAL owner finding made during the live 3-track validation attempt (branch `prototype/live-automix-lab`, HEAD `503f36e` at the time). While guiding the owner through Connect/Authorize, the owner independently confirmed in the official Spotify client that opening any single arbitrary track causes Spotify itself to populate a "Next Up" queue -- there is no practical bulk-clear flow, only per-item removal. The live AutoMix app therefore observed `GET /me/player/queue` returning `KNOWN_NONEMPTY` with ~10 items immediately after a single seed play, even though the owner never manually queued anything. This invalidated the app's prior assumption that `KNOWN_NONEMPTY == owner/external queue conflict` -- exactly the assumption `EXTERNAL_QUEUE_OCCUPIED` was built on in the prior repair round.

## The repair

Spotify's public `POST /me/player/queue` endpoint is documented as "add an item to be played next in the user's current playback queue" -- i.e. play-next semantics, not append-at-the-end. A pre-existing (provider-generated) queue is therefore not something this app needs to avoid or clear; it only needs to place its own one chosen successor ahead of it and verify that placement.

- **`spotify-queue-truth.js`**: `canInjectToQueue(queueTruth)` now returns `true` for `KNOWN_EMPTY` OR `KNOWN_NONEMPTY` (previously `KNOWN_EMPTY` only) -- injection remains forbidden only for a genuinely unknown state (never polled, or the last poll errored).
- **`spotify-lookahead-queue.js`**: `confirmSuccessorFromTokens(tokens)` now requires the pending successor to occupy `tokens[0]` (the play-next/head position) rather than merely `tokens.includes(pendingToken)`. A successor visible only later in the queue (e.g. behind provider items, or appended at the end) is correctly treated as NOT YET confirmed, not falsely confirmed.
- **`SpotifyPublicControlAdapter.js`**: `runLookaheadCycle()` no longer short-circuits to a blocked `EXTERNAL_QUEUE_OCCUPIED` state on `KNOWN_NONEMPTY` -- it proceeds to select and inject exactly as it would on `KNOWN_EMPTY`. The pre-injection real-queue snapshot is captured as `_lastBaselineQueueTokens` (sanitized tokens only) purely for diagnostics; nothing is ever cleared or reordered. `getLookaheadStatus()` gained `providerQueueSize` (item count behind our own successor, or the whole queue if not yet confirmed), `pendingAutoMixSuccessor` (this app's own opaque token), and `successorIsPlayNext` (whether that token currently occupies the real queue's head position) -- all informational, never a blocker.
- **Terminology**: `EXTERNAL_QUEUE_OCCUPIED` (a blocking outcome) is gone from the live code path; a non-empty real queue is now reported truthfully as `providerQueueSize`, an informational count, never a reason a cycle was blocked.
- **UI (`index.html`/`app.js`)**: two new status rows -- "Successor is play-next" and "Provider queue size (Spotify's own)" -- so the owner can see, live, whether the real Spotify API actually places AutoMix's successor at the head of the queue during the retest.

## What this repair does NOT claim

The deterministic test suite (`verify_spotify_provider_queue_coexistence.mjs`, including a dedicated "provider-semantics probe") proves this app's OWN LOGIC correctly recognizes a play-next placement (`[X, A, B, C]`) as confirmed and an append-at-the-end placement (`[A, B, C, X]`) as NOT confirmed. It is deliberately synthetic/mocked -- it is NOT proof of what the real Spotify runtime actually does with `POST /me/player/queue` when a provider queue already exists. That can only be established by the real owner retest this repair hands back to. If that retest shows the real API does not place the successor at play-next, the correct terminal state is `SPOTIFY_ADD_QUEUE_NOT_PLAY_NEXT_IN_RUNTIME` -- a provider-API-behavior finding, not something to work around with further guessing in this pass.

## Test summary

26 verifier suites, 586/586 deterministic checks, 0 FAIL. One new suite this round: `verify_spotify_provider_queue_coexistence.mjs` (27/27 -- the deterministic provider-semantics probe plus the 12 required tests: nonempty baseline no longer blocks; baseline captured/preserved conceptually; one POST only; play-next confirms; later-in-queue does not confirm; no duplicate POST for a stable successor; exactly one refill on advance; provider queue remains allowed behind a second successor; `UNKNOWN_API_ERROR` still blocks mutation; AutoMix OFF still prevents POST; 20 ticks never grow app-controlled lookahead past 1; privacy stays opaque-token-only). Two existing suites updated for the intentional behavior change: `verify_spotify_queue_truth.mjs` (`canInjectToQueue` now true for `KNOWN_NONEMPTY`) and `verify_spotify_one_lookahead.mjs` (the old "external token blocks" test replaced with "provider queue does not block"). All other suites rerun unchanged and still pass. Local DSP Live untouched, 193s session not rerun.

## Unknowns / risks carried into the owner retest

- Whether Spotify's real `POST /me/player/queue` genuinely places an item at the immediate play-next position when a provider queue already exists is still `UNKNOWN_NEEDS_PROOF` -- this is exactly what the owner retest is for.
- All prior-round unknowns/risks remain unchanged and still open.
