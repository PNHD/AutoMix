// Proves the Phase C/D/E wiring actually runs end-to-end through the
// REAL SpotifyPublicControlAdapter class (not just the pure modules in
// isolation) -- candidate pool -> planner -> lookahead queue controller
// -> real player_state_changed-driven advancement, exactly the path the
// live app.js UI (Phase F) will drive. No network -- `_api` is
// monkey-patched, same convention as verify_spotify_transfer_playback.mjs.
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { QueueState } from "../src/adapters/spotify-lookahead-queue.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

function newAdapter() {
  return new SpotifyPublicControlAdapter({ clientId: "test-client-id", redirectUri: "http://127.0.0.1:5500/" });
}

function feedState(adapter, state) {
  adapter._latestState = state;
  adapter._onPlayerStateChanged(state);
}

function fakeState({ trackId, artistId = "ART_UNSET", paused = false, position = 0, durationMs = 200000 }) {
  return {
    paused,
    position,
    duration: durationMs,
    track_window: {
      current_track: { id: trackId, name: "irrelevant", duration_ms: durationMs, artists: [{ id: artistId, name: "irrelevant" }] },
      next_tracks: [],
    },
  };
}

function topTracksRaw(items) {
  return { items };
}
function rawTrack(id, artistId) {
  return { id, uri: `spotify:track:${id}`, artists: [{ id: artistId, name: "irrelevant" }], duration_ms: 200000, is_playable: true };
}

// --- Wire an adapter through: seed -> observed -> runLookaheadCycle -> confirm -> advance -> second cycle ---
{
  const adapter = newAdapter();
  adapter._deviceId = "device123";

  const apiCalls = [];
  // P0-M6-R2 repair pass: runLookaheadCycle() now ALWAYS polls real
  // queue truth (GET /me/player/queue) first (Blocker 3), so this mock
  // must behave like a real stateful queue -- an item leaves `mockQueue`
  // once it becomes `mockCurrentId` (feedState() below updates both) --
  // otherwise the mock would falsely report an already-played former
  // successor as still queued (EXTERNAL_QUEUE_OCCUPIED).
  let mockQueue = [];
  let mockCurrentId = "SEED123";
  // The planner's deterministic opaque-ID tie-break means either SUCC1
  // or SUCC2 could legitimately be chosen first -- assertions below use
  // whichever the adapter actually enqueued, rather than assuming one.
  adapter._api = async (url, opts = {}) => {
    apiCalls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC1", "ART_1"), rawTrack("SUCC2", "ART_2")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) mockQueue.push(uri.replace("spotify:track:", ""));
      return null; // POST enqueue, 204-equivalent
    }
    if (url === "/me/player/queue") {
      return { currently_playing: { id: mockCurrentId }, queue: mockQueue.map((id) => ({ id })) };
    }
    return null;
  };
  // Mirrors real Spotify behavior: once a track becomes current, it is
  // consumed out of the queue array. Wraps feedState() for this block
  // only so every player_state_changed in this test keeps the mock
  // queue realistic.
  function advanceMock(adapter, { trackId, artistId }) {
    mockCurrentId = trackId;
    mockQueue = mockQueue.filter((id) => id !== trackId);
    feedState(adapter, fakeState({ trackId, artistId }));
  }

  // Mirrors what playSeedTrack() sets, without a real network call.
  adapter._seedUri = "spotify:track:SEED123";
  adapter._seedToken = (await import("../src/adapters/spotify-autoplay.js")).sanitizeTrackToken("SEED123");
  adapter._sessionPlayedIds = [];
  adapter._usedArtistIds = [];

  let threwBeforeSeedObserved = false;
  try {
    await adapter.runLookaheadCycle();
  } catch (e) {
    threwBeforeSeedObserved = e.message === "SEED_NOT_YET_ACTIVE_FOR_LOOKAHEAD";
  }
  check("runLookaheadCycle refuses to run before the seed is SEED_ACTIVE", threwBeforeSeedObserved);

  advanceMock(adapter, { trackId: "SEED123", artistId: "ART_SEED" });
  check("adapter is now SEED_ACTIVE (seed observed)", adapter._seedObserved === true);
  check("session history captured the seed's own track id", adapter._sessionPlayedIds.includes("SEED123"));
  check("session history captured the seed's own primary artist id", adapter._usedArtistIds.includes("ART_SEED"));

  const cycle1 = await adapter.runLookaheadCycle();
  check("runLookaheadCycle polls real queue truth first (Blocker 3)", apiCalls.some((c) => c.url === "/me/player/queue" && c.method === "GET"));
  check("runLookaheadCycle builds a candidate pool via top-tracks + recently-played", apiCalls.some((c) => c.url.startsWith("/me/top/tracks")) && apiCalls.some((c) => c.url.startsWith("/me/player/recently-played")));
  check("runLookaheadCycle selects and queues successor #1 (POST /me/player/queue)", cycle1.queued === true && apiCalls.some((c) => c.method === "POST" && c.url.startsWith("/me/player/queue?")));
  check("adapter status reflects the queued selection", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_QUEUE_REQUESTED);
  check("candidate pool size is visible on adapter status (Phase F)", adapter.getLookaheadStatus().candidatePoolSize === 2);
  check("selection reason is visible on adapter status (Phase F)", typeof adapter.getLookaheadStatus().selectionReason === "string");

  const firstSuccessorId = mockQueue[0]; // "SUCC1" or "SUCC2" -- whichever the planner actually chose
  const firstSuccessorArtist = firstSuccessorId === "SUCC1" ? "ART_1" : "ART_2";

  // A duplicate orchestration tick BEFORE confirmation must not start a
  // second selection cycle or issue a second POST (Blocker 3).
  const postCountBeforeDuplicateTick = apiCalls.filter((c) => c.method === "POST").length;
  const duplicateTick = await adapter.runLookaheadCycle();
  check("a duplicate tick while awaiting confirmation never starts a new selection cycle", duplicateTick.queued === false);
  check("a duplicate tick while awaiting confirmation issues zero additional POSTs", apiCalls.filter((c) => c.method === "POST").length === postCountBeforeDuplicateTick);
  check("adapter status shows successorConfirmed true after the duplicate tick's confirm attempt", adapter.getLookaheadStatus().successorConfirmed === true);

  // Spotify itself now advances to the confirmed successor -- this must
  // arrive as an ordinary player_state_changed event, exactly like any
  // other track change, and drive the state machine forward.
  advanceMock(adapter, { trackId: firstSuccessorId, artistId: firstSuccessorArtist });
  check("a real player_state_changed event for the confirmed successor advances the lookahead machine", adapter.getLookaheadStatus().state === QueueState.SELECTING_NEXT_SUCCESSOR);
  check("refillCount is now 1 after the first automatic advance", adapter.getLookaheadStatus().refillCount === 1);
  check("consecutiveAutoTrackCount is now 2", adapter.getLookaheadStatus().consecutiveAutoTrackCount === 2);
  check("session history now includes successor #1's id (never re-selectable)", adapter._sessionPlayedIds.includes(firstSuccessorId));

  // A duplicate player_state_changed for the SAME now-current track must not double-count (idempotency, wired through the real adapter).
  const refillBeforeDuplicate = adapter.getLookaheadStatus().refillCount;
  feedState(adapter, fakeState({ trackId: firstSuccessorId, artistId: firstSuccessorArtist, position: 5000 })); // e.g. a position-update duplicate
  check("a duplicate state event for the same current track does not double-count the refill", adapter.getLookaheadStatus().refillCount === refillBeforeDuplicate);

  // --- Second lookahead cycle for the remaining successor ---
  const cycle2 = await adapter.runLookaheadCycle();
  const secondSuccessorId = mockQueue[0];
  check("a second lookahead cycle selects a DIFFERENT successor, never re-offering the first one", cycle2.queued === true && secondSuccessorId !== firstSuccessorId);
  await adapter.runLookaheadCycle(); // next orchestration tick -- confirms the just-queued second successor
  check("adapter status shows successorConfirmed true for the second successor", adapter.getLookaheadStatus().successorConfirmed === true);
  advanceMock(adapter, { trackId: secondSuccessorId, artistId: secondSuccessorId === "SUCC1" ? "ART_1" : "ART_2" });
  check("at least 3 consecutive automatic tracks played from one owner-selected seed (integration)", adapter.getLookaheadStatus().consecutiveAutoTrackCount >= 3);
  check("refillCount is 2 after two automatic advances (integration)", adapter.getLookaheadStatus().refillCount === 2);
}

// --- A fresh seed resets all Phase C/D/E session state (never leaks across seeds) ---
{
  const adapter = newAdapter();
  adapter._deviceId = "device123";
  adapter._api = async (url) => {
    if (url.startsWith("/me/top/tracks")) return { items: [] };
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    return null;
  };
  adapter._sessionPlayedIds = ["OLD_TRACK_FROM_PRIOR_SEED"];
  adapter._usedArtistIds = ["OLD_ARTIST"];
  adapter._lastCandidatePoolSize = 42;
  adapter._lookaheadController = { state: "SOME_STALE_STATE" };

  await adapter.playSeedTrack("spotify:track:NEWSEED");
  check("playSeedTrack() clears session-played history for the new seed", adapter._sessionPlayedIds.length === 0);
  check("playSeedTrack() clears used-artist history for the new seed", adapter._usedArtistIds.length === 0);
  check("playSeedTrack() clears the candidate pool size", adapter._lastCandidatePoolSize === 0);
  check("playSeedTrack() discards the prior seed's lookahead controller", adapter._lookaheadController === null);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
