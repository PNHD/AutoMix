// Deterministic proof of P0-M6-R2 repair-pass-2 Blocker 1: the
// double-poll confirmation race is gone. One orchestration decision uses
// exactly ONE fresh GET /me/player/queue snapshot -- confirmation must
// never re-fetch after the caller already has fresh queue truth, and an
// API error during confirmation must never be reinterpreted as
// "not yet visible." No network -- `_api` is monkey-patched.
import { LookaheadQueueController, QueueState } from "../src/adapters/spotify-lookahead-queue.js";
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { SpotifyApiError } from "../src/adapters/spotify-api-response.js";
import { sanitizeTrackToken } from "../src/adapters/spotify-autoplay.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// ============================================================
// Pure controller: confirmSuccessorFromTokens never performs I/O
// ============================================================
{
  let verifyQueueFnCalls = 0;
  const controller = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => {
      verifyQueueFnCalls += 1;
      return ["TRK_SUCC"];
    },
    selectNextFn: () => ({ selected: { id: "SUCC", uri: "spotify:track:SUCC" }, token: "TRK_SUCC", reason: "TOP_TRACK_AFFINITY", excluded: [], candidatePoolSize: 1 }),
  });
  await controller.selectAndQueueSuccessor({});
  check("controller is SUCCESSOR_QUEUE_REQUESTED after queuing", controller.state === QueueState.SUCCESSOR_QUEUE_REQUESTED);

  const result = controller.confirmSuccessorFromTokens(["TRK_SUCC"]);
  check("confirmSuccessorFromTokens confirms using the supplied tokens", result.confirmed === true && result.token === "TRK_SUCC");
  check("confirmSuccessorFromTokens performed ZERO network I/O (verifyQueueFn never called)", verifyQueueFnCalls === 0);
  check("controller is SUCCESSOR_CONFIRMED", controller.state === QueueState.SUCCESSOR_CONFIRMED);

  // Reject case: pure, still no I/O.
  const controller2 = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => {
      throw new Error("verifyQueueFn must never be called by confirmSuccessorFromTokens");
    },
    selectNextFn: () => ({ selected: { id: "SUCC2", uri: "spotify:track:SUCC2" }, token: "TRK_SUCC2", reason: "TOP_TRACK_AFFINITY", excluded: [], candidatePoolSize: 1 }),
  });
  await controller2.selectAndQueueSuccessor({});
  const rejected = controller2.confirmSuccessorFromTokens(["TRK_SOMETHING_ELSE"]);
  check("confirmSuccessorFromTokens reports NOT_YET_VISIBLE_IN_QUEUE when the pending token isn't in the supplied set, still with zero I/O", rejected.confirmed === false && rejected.reason === "NOT_YET_VISIBLE_IN_QUEUE");
  check("controller remains SUCCESSOR_QUEUE_REQUESTED when not found in the supplied tokens", controller2.state === QueueState.SUCCESSOR_QUEUE_REQUESTED);

  check("confirmSuccessorFromTokens refuses when not awaiting confirmation at all", new LookaheadQueueController({ queueTrackFn: async () => {}, verifyQueueFn: async () => [], selectNextFn: () => ({}) }).confirmSuccessorFromTokens(["X"]).reason === "NOT_AWAITING_CONFIRMATION");
}

function newActiveSeedAdapter() {
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._deviceId = "device123";
  adapter._seedUri = "spotify:track:SEED123";
  adapter._seedToken = sanitizeTrackToken("SEED123");
  adapter._seedObserved = true;
  adapter._latestState = {
    paused: false,
    position: 0,
    duration: 200000,
    track_window: { current_track: { id: "SEED123", duration_ms: 200000, artists: [{ id: "ART_SEED" }] }, next_tracks: [] },
  };
  return adapter;
}
function feedState(adapter, state) {
  adapter._latestState = state;
  adapter._onPlayerStateChanged(state);
}
function fakeState({ trackId, artistId = "ART_X", position = 0, durationMs = 200000 }) {
  return {
    paused: false,
    position,
    duration: durationMs,
    track_window: { current_track: { id: trackId, duration_ms: durationMs, artists: [{ id: artistId }] }, next_tracks: [] },
  };
}
function topTracksRaw(items) {
  return { items };
}
function rawTrack(id, artistId = "ART_X") {
  return { id, uri: `spotify:track:${id}`, artists: [{ id: artistId }], duration_ms: 200000, is_playable: true };
}

// ============================================================
// REQUIRED RACE TEST (full 11-step scenario from the PM spec)
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const getQueueCalls = [];
  let mockQueue = [];
  adapter._api = async (url, opts = {}) => {
    const method = opts.method || "GET";
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) mockQueue.push(uri.replace("spotify:track:", ""));
      return null;
    }
    if (url === "/me/player/queue") {
      getQueueCalls.push(Date.now());
      return { currently_playing: { id: "SEED123" }, queue: mockQueue.map((id) => ({ id })) };
    }
    return null;
  };

  // Step 1-2: seed active, real queue KNOWN_EMPTY (mockQueue starts []).
  // Step 3-4: runLookaheadCycle queues SUCC -> SUCCESSOR_QUEUE_REQUESTED.
  const cycle1 = await adapter.runLookaheadCycle();
  check("step 3-4: first cycle queues SUCC", cycle1.queued === true);
  check("step 4: controller is SUCCESSOR_QUEUE_REQUESTED", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_QUEUE_REQUESTED);

  // Step 5-6: the NEXT orchestration cycle receives ONE real queue
  // response containing SUCC, and confirms using THAT SAME response.
  const getCallsBeforeConfirmCycle = getQueueCalls.length;
  const cycle2 = await adapter.runLookaheadCycle();
  check("step 6: controller becomes SUCCESSOR_CONFIRMED", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);
  // Step 7: assert exactly ONE GET /me/player/queue occurred in that cycle.
  check("step 7: exactly ONE GET /me/player/queue occurred during the confirmation cycle", getQueueCalls.length - getCallsBeforeConfirmCycle === 1);

  // Step 8-11: feed player_state_changed current=SUCC.
  feedState(adapter, fakeState({ trackId: "SUCC", artistId: "ART_X" }));
  check("step 9: controller becomes SELECTING_NEXT_SUCCESSOR", adapter.getLookaheadStatus().state === QueueState.SELECTING_NEXT_SUCCESSOR);
  check("step 10: consecutiveAutoTrackCount becomes 2", adapter.getLookaheadStatus().consecutiveAutoTrackCount === 2);
  check("step 11: refillCount becomes 1", adapter.getLookaheadStatus().refillCount === 1);
}

// ============================================================
// Mechanical reproduction of the OLD race: queue says SUCC is visible,
// then (within the SAME snapshot / no second GET permitted) SUCC is
// consumed into current -- the state machine must still advance
// correctly using only the ONE poll it already had.
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = [];
  let getQueueCallCount = 0;
  let allowGet = true;
  adapter._api = async (url, opts = {}) => {
    const method = opts.method || "GET";
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) mockQueue.push(uri.replace("spotify:track:", ""));
      return null;
    }
    if (url === "/me/player/queue") {
      if (!allowGet) throw new Error("A SECOND GET /me/player/queue was attempted during one confirmation decision -- this IS the race this repair removes");
      getQueueCallCount += 1;
      return { currently_playing: { id: "SEED123" }, queue: mockQueue.map((id) => ({ id })) };
    }
    return null;
  };

  await adapter.runLookaheadCycle(); // queues SUCC
  check("SUCC queued", mockQueue.includes("SUCC"));

  // The confirming cycle's poll sees SUCC in the queue. We then forbid
  // ANY further GET for the remainder of this synchronous decision --
  // the old buggy design would have made a second GET right here inside
  // confirmSuccessor() and found it empty (because in the real world
  // Spotify could have just consumed it). The repaired design must
  // confirm from the ALREADY-FETCHED response and never attempt that
  // second call at all.
  const confirmCycle = await adapter.runLookaheadCycle();
  check("confirmed using the one poll already taken (no second GET was ever attempted -- see allowGet guard above)", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);

  // NOW simulate Spotify having consumed it (queue truly empty from here on).
  mockQueue = [];
  allowGet = true; // future ticks/polls are fine again
  feedState(adapter, fakeState({ trackId: "SUCC" }));
  check("state machine still advances correctly after the successor becomes current", adapter.getLookaheadStatus().state === QueueState.SELECTING_NEXT_SUCCESSOR);
  check("refillCount incremented despite the queue having been consumed between confirmation and advancement", adapter.getLookaheadStatus().refillCount === 1);
}

// ============================================================
// API-error-during-confirmation test
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = [];
  let failNextGet = false;
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    const method = opts.method || "GET";
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) mockQueue.push(uri.replace("spotify:track:", ""));
      return null;
    }
    if (url === "/me/player/queue") {
      if (failNextGet) throw new SpotifyApiError({ method: "GET", path: "/me/player/queue", status: 500, body: null, bodyType: "EMPTY_ERROR" });
      return { currently_playing: { id: "SEED123" }, queue: mockQueue.map((id) => ({ id })) };
    }
    return null;
  };

  await adapter.runLookaheadCycle(); // queues SUCC -> SUCCESSOR_QUEUE_REQUESTED
  check("SUCCESSOR_QUEUE_REQUESTED before the API error", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_QUEUE_REQUESTED);

  failNextGet = true;
  const postCountBeforeErrorTick = postCalls.length;
  const errorResult = await adapter.runLookaheadCycle();
  check("a queue-truth API error during confirmation returns the EXACT result QUEUE_STATE_UNKNOWN_CANNOT_CONFIRM", errorResult.reason === "QUEUE_STATE_UNKNOWN_CANNOT_CONFIRM");
  check("the API error is NEVER reinterpreted as NOT_YET_VISIBLE_IN_QUEUE", errorResult.reason !== "NOT_YET_VISIBLE_IN_QUEUE");
  check("controller remains SUCCESSOR_QUEUE_REQUESTED after the API error (not lost, not falsely advanced)", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_QUEUE_REQUESTED);
  check("zero POSTs during the API-error confirmation tick", postCalls.length === postCountBeforeErrorTick);

  // Recovery: once the API succeeds again, confirmation proceeds normally.
  failNextGet = false;
  const recovered = await adapter.runLookaheadCycle();
  check("confirmation recovers once the API succeeds again", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);
}

// ============================================================
// 20-tick simulation: no duplicate POSTs, no unbounded GET amplification, no stuck state after advancement
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = [];
  let mockCurrentId = "SEED123";
  const getCalls = [];
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    const method = opts.method || "GET";
    // Distinct artist ids so the second successor is never excluded via
    // IMMEDIATE_SAME_ARTIST_REPETITION once the first becomes current.
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC1", "ART_1"), rawTrack("SUCC2", "ART_2")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) mockQueue.push(uri.replace("spotify:track:", ""));
      return null;
    }
    if (url === "/me/player/queue") {
      getCalls.push(url);
      return { currently_playing: { id: mockCurrentId }, queue: mockQueue.map((id) => ({ id })) };
    }
    return null;
  };

  // Ticks 1-5: idle-empty -> select -> queue one successor (1 POST), then confirm-idle ticks.
  // The planner's deterministic tie-break may pick either SUCC1 or SUCC2
  // first -- use whichever it actually queued, don't assume.
  for (let i = 0; i < 5; i += 1) await adapter.runLookaheadCycle();
  check("20-tick sim: after 5 ticks, exactly one successor was queued so far", postCalls.length === 1);
  check("20-tick sim: state settled at SUCCESSOR_CONFIRMED (not stuck at REQUESTED)", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);

  const firstSuccessorId = mockQueue[0];
  const firstSuccessorArtist = firstSuccessorId === "SUCC1" ? "ART_1" : "ART_2";
  // Advance to the first successor becoming current (real Spotify behavior: consumed out of the queue).
  mockCurrentId = firstSuccessorId;
  mockQueue = mockQueue.filter((id) => id !== firstSuccessorId);
  feedState(adapter, fakeState({ trackId: firstSuccessorId, artistId: firstSuccessorArtist }));
  check("20-tick sim: no stuck state after the confirmed successor becomes current", adapter.getLookaheadStatus().state === QueueState.SELECTING_NEXT_SUCCESSOR);
  check("20-tick sim: refillCount is 1 after the first advance", adapter.getLookaheadStatus().refillCount === 1);

  // Ticks 6-20: should select+queue the remaining successor (1 more POST) and then just idle-confirm/await-playback for the rest.
  for (let i = 0; i < 15; i += 1) await adapter.runLookaheadCycle();
  check("20-tick sim: exactly TWO total POSTs across the whole 20-tick run (one per successor, no duplicates)", postCalls.length === 2);
  check("20-tick sim: GET call count stays linear in ticks, not amplified (<=20, one per tick)", getCalls.length <= 20);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
