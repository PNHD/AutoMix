// Deterministic proof of the provider-queue-coexistence repair (real
// owner finding, P0-M6-R2): Spotify's own client keeps a
// provider-generated "Next Up" queue populated after any track starts
// playing -- a non-empty real queue is normal, not an owner conflict,
// and must never block AutoMix's own one-successor lookahead. Per
// Spotify's documented `POST /me/player/queue` semantics ("add an item
// to be played next"), confirmation requires the pending successor to
// occupy the PLAY-NEXT (head, index 0) position of the real queue, not
// merely appear anywhere in it. No network -- `_api` is monkey-patched.
//
// IMPORTANT: the "deterministic provider-semantics probe" below proves
// this app's OWN LOGIC correctly recognizes a play-next placement as
// confirmed and an append-at-the-end placement as NOT confirmed. It is
// NOT proof of what the real Spotify runtime actually does -- that can
// only be established by the real owner retest this repair pass hands
// off to (see HANDOFF_TO_PM.md / the terminal state this session
// reports). If that retest shows the real API does NOT place our
// successor at play-next, the terminal state is
// SPOTIFY_ADD_QUEUE_NOT_PLAY_NEXT_IN_RUNTIME, not a further workaround
// in this pass.
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { QueueState } from "../src/adapters/spotify-lookahead-queue.js";
import { LookaheadQueueController } from "../src/adapters/spotify-lookahead-queue.js";
import { canInjectToQueue, deriveQueueTruth } from "../src/adapters/spotify-queue-truth.js";
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
function fakeState({ trackId, artistId = "ART_X" }) {
  return {
    paused: false,
    position: 0,
    duration: 200000,
    track_window: { current_track: { id: trackId, duration_ms: 200000, artists: [{ id: artistId }] }, next_tracks: [] },
  };
}
function topTracksRaw(items) {
  return { items };
}
function rawTrack(id, artistId = "ART_X") {
  return { id, uri: `spotify:track:${id}`, artists: [{ id: artistId }], duration_ms: 200000, is_playable: true };
}

// ============================================================
// DETERMINISTIC PROVIDER-SEMANTICS PROBE
// baseline [A, B, C] + POST X -> confirmation snapshot [X, A, B, C]
// must confirm; [A, B, C, X] (appended, not play-next) must NOT confirm.
// ============================================================
{
  const playNextConfirm = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => [],
    selectNextFn: () => ({ selected: { id: "X", uri: "spotify:track:X" }, token: "TRK_X", reason: "TOP_TRACK_AFFINITY", excluded: [], candidatePoolSize: 1 }),
  });
  await playNextConfirm.selectAndQueueSuccessor({});
  const playNextSnapshot = ["TRK_X", "TRK_A", "TRK_B", "TRK_C"]; // baseline [A,B,C], X placed at the head
  const playNextResult = playNextConfirm.confirmSuccessorFromTokens(playNextSnapshot);
  check("probe: X at queue[0] (documented play-next placement) -> CONFIRMED", playNextResult.confirmed === true);

  const appendedConfirm = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => [],
    selectNextFn: () => ({ selected: { id: "X", uri: "spotify:track:X" }, token: "TRK_X", reason: "TOP_TRACK_AFFINITY", excluded: [], candidatePoolSize: 1 }),
  });
  await appendedConfirm.selectAndQueueSuccessor({});
  const appendedSnapshot = ["TRK_A", "TRK_B", "TRK_C", "TRK_X"]; // baseline [A,B,C], X appended at the END, not play-next
  const appendedResult = appendedConfirm.confirmSuccessorFromTokens(appendedSnapshot);
  check("probe: X present but only at the END (not play-next) -> NOT confirmed (this is exactly the shape that would trigger SPOTIFY_ADD_QUEUE_NOT_PLAY_NEXT_IN_RUNTIME on a real retest)", appendedResult.confirmed === false && appendedResult.reason === "NOT_YET_VISIBLE_IN_QUEUE");
  check("probe: controller remains SUCCESSOR_QUEUE_REQUESTED when X is only appended, not stuck in a false-confirmed state", appendedConfirm.state === QueueState.SUCCESSOR_QUEUE_REQUESTED);
}

// ============================================================
// Test 1: nonempty baseline queue no longer blocks selection
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [{ id: "PROVIDER_A" }, { id: "PROVIDER_B" }, { id: "PROVIDER_C" }] };
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("test 1: a nonempty (provider) baseline queue does not block selection", result.queued === true);
}

// ============================================================
// Test 2: baseline queue preserved conceptually (captured, never mutated/cleared)
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [{ id: "PROVIDER_A" }, { id: "PROVIDER_B" }] };
    return null;
  };
  await adapter.runLookaheadCycle();
  check("test 2: the pre-injection baseline queue snapshot is captured (2 provider tokens)", adapter._lastBaselineQueueTokens.length === 2);
  check("test 2: captured baseline tokens are sanitized opaque tokens, never raw ids", adapter._lastBaselineQueueTokens.every((t) => t.startsWith("TRK_")));
}

// ============================================================
// Test 3: one POST only (for a single selection cycle, even with a provider queue present)
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [{ id: "PROVIDER_A" }] };
    return null;
  };
  await adapter.runLookaheadCycle();
  check("test 3: exactly one POST for one selection cycle", postCalls.length === 1);
}

// ============================================================
// Test 4 & 5: X at queue[0] confirms; X present only later does NOT confirm
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = ["PROVIDER_A", "PROVIDER_B"]; // pre-existing provider queue
  let placeAtHead = true;
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      const id = uri.replace("spotify:track:", "");
      mockQueue = placeAtHead ? [id, ...mockQueue] : [...mockQueue, id];
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: mockQueue.map((id) => ({ id })) };
    return null;
  };
  await adapter.runLookaheadCycle(); // queues SUCC at head (mock places it there)
  const confirmTick = await adapter.runLookaheadCycle();
  check("test 4: X placed at queue[0] (head/play-next) confirms", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);
  check("test 4: successorIsPlayNext true once confirmed at the head", adapter.getLookaheadStatus().successorIsPlayNext === true);

  // Separate adapter: successor gets appended behind the provider queue instead.
  const adapter2 = newActiveSeedAdapter();
  let mockQueue2 = ["PROVIDER_A", "PROVIDER_B"];
  adapter2._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC2")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      mockQueue2 = [...mockQueue2, uri.replace("spotify:track:", "")]; // appended at the end -- not play-next
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: mockQueue2.map((id) => ({ id })) };
    return null;
  };
  await adapter2.runLookaheadCycle();
  const confirmTick2 = await adapter2.runLookaheadCycle();
  check("test 5: X present only LATER in the queue (behind provider items) does NOT confirm", adapter2.getLookaheadStatus().state === QueueState.SUCCESSOR_QUEUE_REQUESTED);
  check("test 5: successorIsPlayNext false when not at the head", adapter2.getLookaheadStatus().successorIsPlayNext === false);
}

// ============================================================
// Test 6: duplicate X does not cause duplicate POST
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = [];
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      mockQueue = [uri.replace("spotify:track:", ""), ...mockQueue];
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: mockQueue.map((id) => ({ id })) };
    return null;
  };
  for (let i = 0; i < 8; i += 1) await adapter.runLookaheadCycle();
  check("test 6: 8 ticks against a stable (confirmed) successor -> exactly one POST, no duplicates", postCalls.length === 1);
}

// ============================================================
// Test 7: confirmed X becoming current triggers exactly one refill
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      mockQueue = [uri.replace("spotify:track:", ""), ...mockQueue];
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: mockQueue.map((id) => ({ id })) };
    return null;
  };
  await adapter.runLookaheadCycle();
  await adapter.runLookaheadCycle(); // confirms
  check("test 7 setup: confirmed before advance", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);
  feedState(adapter, fakeState({ trackId: "SUCC" }));
  check("test 7: exactly one refill on advance", adapter.getLookaheadStatus().refillCount === 1);
}

// ============================================================
// Test 8: provider queue remains allowed behind the NEW successor too (second cycle)
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = ["PROVIDER_A", "PROVIDER_B", "PROVIDER_C"]; // provider queue present from the start
  let mockCurrentId = "SEED123";
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC1", "ART_1"), rawTrack("SUCC2", "ART_2")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      mockQueue = [uri.replace("spotify:track:", ""), ...mockQueue]; // play-next
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: mockCurrentId }, queue: mockQueue.map((id) => ({ id })) };
    return null;
  };
  await adapter.runLookaheadCycle(); // select+queue successor #1 ahead of the 3 provider items
  await adapter.runLookaheadCycle(); // confirm
  const firstId = mockQueue[0];
  check("test 8 setup: successor #1 confirmed at play-next, 3 provider items still behind it", adapter.getLookaheadStatus().successorIsPlayNext === true && adapter.getLookaheadStatus().providerQueueSize === 3);

  mockCurrentId = firstId;
  mockQueue = mockQueue.filter((id) => id !== firstId); // consumed, provider items remain
  feedState(adapter, fakeState({ trackId: firstId, artistId: firstId === "SUCC1" ? "ART_1" : "ART_2" }));
  await adapter.runLookaheadCycle(); // select+queue successor #2, again ahead of the still-present provider items
  await adapter.runLookaheadCycle(); // confirm
  check("test 8: successor #2 is also confirmed at play-next, provider items from before are still present and untouched", adapter.getLookaheadStatus().successorIsPlayNext === true && adapter.getLookaheadStatus().providerQueueSize === 3);
  check("test 8: two total POSTs (one per successor), provider items never posted/removed by this app", postCalls.length === 2);
}

// ============================================================
// Test 9: UNKNOWN_API_ERROR still blocks mutation
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      return null;
    }
    if (url === "/me/player/queue") throw new SpotifyApiError({ method: "GET", path: "/me/player/queue", status: 500, body: null, bodyType: "EMPTY_ERROR" });
    return { items: [] };
  };
  const result = await adapter.runLookaheadCycle();
  check("test 9: UNKNOWN_API_ERROR -> QUEUE_STATE_UNKNOWN_CANNOT_INJECT, still blocks mutation", result.reason === "QUEUE_STATE_UNKNOWN_CANNOT_INJECT");
  check("test 9: zero POSTs on API error", postCalls.length === 0);
}

// ============================================================
// Test 10: AutoMix OFF still prevents POST (even with a provider queue present)
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [{ id: "PROVIDER_A" }] };
    return null;
  };
  adapter.setAutoMixEnabled(false);
  const result = await adapter.runLookaheadCycle();
  check("test 10: AutoMix OFF -> AUTOMIX_DISABLED even with a provider queue present", result.reason === "AUTOMIX_DISABLED");
  check("test 10: zero POSTs while OFF", postCalls.length === 0);
}

// ============================================================
// Test 11: 20 orchestration ticks do not grow app-controlled lookahead > 1
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockQueue = ["PROVIDER_A", "PROVIDER_B"];
  let mockCurrentId = "SEED123";
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC1", "ART_1"), rawTrack("SUCC2", "ART_2")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      mockQueue = [uri.replace("spotify:track:", ""), ...mockQueue];
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: mockCurrentId }, queue: mockQueue.map((id) => ({ id })) };
    return null;
  };
  for (let i = 0; i < 10; i += 1) await adapter.runLookaheadCycle();
  check("test 11: after 10 ticks, exactly ONE AutoMix-controlled successor was ever queued (never more than one pending/confirmed at a time)", postCalls.length === 1);
  const firstId = mockQueue[0];
  mockCurrentId = firstId;
  mockQueue = mockQueue.filter((id) => id !== firstId);
  feedState(adapter, fakeState({ trackId: firstId, artistId: firstId === "SUCC1" ? "ART_1" : "ART_2" }));
  for (let i = 0; i < 10; i += 1) await adapter.runLookaheadCycle();
  check("test 11: after 20 total ticks and one advance, exactly TWO total successors ever queued (still never more than one outstanding at once)", postCalls.length === 2);
}

// ============================================================
// Test 12: privacy remains opaque-token-only
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("SUCC_RAW_ID_SHOULD_NOT_LEAK")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [{ id: "PROVIDER_RAW_ID_SHOULD_NOT_LEAK" }] };
    return null;
  };
  await adapter.runLookaheadCycle();
  const status = adapter.getLookaheadStatus();
  const serialized = JSON.stringify(status);
  check("test 12: getLookaheadStatus() never leaks the raw candidate id", !serialized.includes("SUCC_RAW_ID_SHOULD_NOT_LEAK"));
  check("test 12: getLookaheadStatus() never leaks the raw provider queue item id", !serialized.includes("PROVIDER_RAW_ID_SHOULD_NOT_LEAK"));
  check("test 12: pendingAutoMixSuccessor is an opaque TRK_ token", status.pendingAutoMixSuccessor === null || status.pendingAutoMixSuccessor.startsWith("TRK_"));
  check("test 12: providerQueueSize is a plain number, not raw items", typeof status.providerQueueSize === "number");
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
