# P0-M6-R3 — Compact Live UX + Seed-Conditioned Next

Status date: 2026-08-18

Binding task: `P0-M6-R3 — COMPACT LIVE UX + SEED-CONDITIONED NEXT`, issued directly by the project owner on top of the accepted `P0-M6-R2` HEAD `e40eabc807b5c97f9097d3bb2d7ea2716443d817`.

## Binding result carried forward

`OWNER_APP_CONTROLLED_CONTINUATION_PASS` from R2 stands: the real owner run confirmed app-controlled play-next continuation works against Spotify's own provider queue (one seed, two confirmed app-controlled successors, `refillCount=2`, `consecutiveAutomaticTracks=3`). Continuation infrastructure itself was not reopened. This round addresses R2's product-quality findings: an unrelated Jay Chou -> K-pop transition selected by `DURATION_CONTINUITY`, no beat/downbeat DSP on the Spotify lane (expected/by design), a too-verbose primary UI, and a stale `SDK_NOT_READY` readiness display.

## Part B — provider Next Up as the primary continuation signal

Root cause of the bad transition: `runLookaheadCycle()` polled the real queue (`GET /me/player/queue`) only to decide whether injection was *allowed*, then always ran the account-affinity planner (top tracks / recently played / search) to pick a successor -- it never considered the polled queue's own head item as a candidate, even though Spotify's client had already placed a contextually-relevant "Next Up" track there.

Repaired:

- `deriveQueueTruth` (`spotify-queue-truth.js`) now also derives `headCandidate` -- the real queue's head item, in planner-candidate shape (`id`/`uri`/`primaryArtistId`/`durationMs`/`explicit`/`isPlayable`), tagged `SPOTIFY_PROVIDER_NEXT_UP`. A head item missing a real track `uri` (e.g. malformed) safely yields `headCandidate: null` rather than a broken candidate.
- `evaluateProviderHeadExclusion` (`spotify-planner.js`) applies the same hard exclusions as the account-affinity planner (malformed/unplayable, is-current-track, already-played-this-session, immediate-same-artist-repetition) **except** the recent-repeat-history window, which stays a soft guard only -- per the task, real recently-played history must never veto an otherwise-valid provider Next Up.
- `LookaheadQueueController.adoptProviderNextUp()` (`spotify-lookahead-queue.js`) adopts an eligible head directly: `SELECTING_SUCCESSOR -> SUCCESSOR_CONFIRMED`, skipping `SUCCESSOR_QUEUE_REQUESTED` entirely (there is nothing to confirm-by-polling -- occupying the head position already IS the confirmation) and, critically, **never calls `queueTrackFn`** -- no duplicate `POST /me/player/queue` to "claim ownership" of an item Spotify already queued.
- `runLookaheadCycle()` (`SpotifyPublicControlAdapter.js`) checks the provider head's eligibility BEFORE fetching the account candidate pool at all. When eligible, it adopts and returns immediately -- the account-affinity planner (and its two API calls) is never even consulted. Only when the provider head is absent or ineligible does the pre-existing account-affinity path run, now tagged `selectionSource: ACCOUNT_AFFINITY_FALLBACK`.
- `SELECTION_SOURCE` (`spotify-planner.js`) exposes exactly the two required values, `SPOTIFY_PROVIDER_NEXT_UP` / `ACCOUNT_AFFINITY_FALLBACK`, surfaced on `getLookaheadStatus().selectionSource`.

Because the provider-head branch returns early, `DURATION_CONTINUITY` (or any other account-affinity reason) can structurally never override a valid provider Next Up -- the planner that produces it is not invoked in that case. No BPM/key/genre/audio-similarity claim is made anywhere in this path (verified by a dedicated no-claim regex test, matching the existing Phase D convention). No deprecated Spotify field is read.

All 26 pre-existing suites (586/586) pass unmodified -- the R2 `provider_queue_coexistence` test fixtures use minimal `{id}`-only mock queue items (no `uri`), which correctly and safely continue to produce `headCandidate: null` and exercise the unchanged account-affinity fallback path, exactly as before this round.

## Part A — compact responsive live UI + readiness truth

`index.html`/`styles.css`/`app.js` reorganized into the mandated primary sections -- Header (title, live readiness badge, AutoMix ON/OFF), Now Playing (search, current track, progress, Jump to last 15s), Next (successor/source/ready-state), AutoMix Session (consecutive tracks, refill count, provider queue size), Transition Capability (the two mandated truthful lines for Spotify: "Playback continuity only." / "No custom beat-matched DSP on Spotify Public API.") -- with everything else (candidate pool size, lookahead state machine internals, selection reason/source, provider/capability identifiers, Autoplay observability, queue-truth diagnostics, debug log) moved into a single collapsed `<details id="panel-advanced">`, closed by default. `.grid-primary` is a 2-column CSS grid on desktop (`max-width: 1040px`, centered), collapsing to 1 column at `<=900px` and staying 1 column with wrapping controls at `<=600px` (verified live in-browser at 1280px/900px/375px: zero horizontal overflow, correct column count, `flex-wrap: wrap` on the controls row, zero console errors in either Spotify Live or Local DSP Live mode).

Readiness-truth bug: `getAccountReadiness()` was correct, but `app.js` called it exactly once at Connect time and cached the result on `adapter._lastReadiness` forever after; `device_ready` and confirmed seed playback both arrive asynchronously from the Web Playback SDK, often after that single snapshot. Fixed by making `startStatusLoop()`'s recurring tick call `adapter.getAccountReadiness()` live every 500ms (cheap -- no network I/O, pure state checks) instead of ever trusting a stale cached value; the header badge and Advanced's raw readiness field both now reflect the real state within one tick of `device_ready`/seed-playback confirmation.

Local DSP Live is unaffected: its own capability statement ("real beat-matched crossfade DSP ... in this browser tab") is shown separately and truthfully, and none of its files (`LocalDSPPlaybackAdapter.js`, `src/engine/*`, `work_local/`) were touched.

## Part C — no fake DSP

Unchanged and reaffirmed: `SpotifyPublicControlAdapter.getAutoMixPlan()` always returns `executesRealDsp: false` with an explicitly advisory reason string, regardless of playback state (directly tested). The primary Spotify UI never renders the advisory exit/entry/tempo/EQ/beat-sync fields at all now (they moved to Advanced, clearly labeled "advisory only -- never executed"); the only primary Spotify-mode capability text is the two mandated truthful lines. No beat matching, BPM correction, EQ handoff, crossfade, time stretch, or pitch correction is implemented or implied for the Spotify lane.

## Test summary

28 verifier suites, 684/684 deterministic checks, 0 FAIL. New suites this round: `verify_spotify_provider_next_up.mjs` (38 -- Part B: provider-head eligibility/exclusions incl. the soft recent-repeat guard, `deriveQueueTruth` head-candidate shape, provider-head-wins-over-duration-match, zero-POST adoption, already-played-provider-head rejection + fallback, provider-absent fallback, refill-after-adoption, a 2-provider-head 3-track simulation, AutoMix-OFF blocking adoption too, and a privacy/no-claim leak check on the new path) and `verify_compact_ui.mjs` (60 -- Part A: unique ids / no duplicated status blocks, every primary section present outside the Advanced block, every advanced diagnostic still present inside it, the mandated Spotify capability wording plus `executesRealDsp:false` truth, the readiness-truth fix proven both statically (live tick) and dynamically (state-transition), and privacy of the new UI text). All 26 pre-existing suites rerun unchanged, still 586/586. Local DSP's 193s live session was not rerun (its files were not touched).
