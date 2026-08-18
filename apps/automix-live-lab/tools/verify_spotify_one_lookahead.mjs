// Deterministic proof of P0-M6-R2 repair-pass Blocker 3: exactly
// one-track lookahead, gated on REAL queue truth -- an external item in
// the real Spotify queue must block injection entirely, an API error
// must never be silently treated as safe to inject into, and duplicate
// orchestration ticks can never produce more than one POST for one
// selection cycle. No network -- `_api` is monkey-patched.
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { QueueState } from "../src/adapters/spotify-lookahead-queue.js";
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
  adapter._seedObserved = true; // SEED_ACTIVE, without a real player_state_changed event
  adapter._latestState = {
    paused: false,
    position: 0,
    duration: 200000,
    track_window: { current_track: { id: "SEED123", duration_ms: 200000, artists: [{ id: "ART_SEED" }] }, next_tracks: [] },
  };
  return adapter;
}

function topTracksRaw(items) {
  return { items };
}
function rawTrack(id, artistId = "ART_X") {
  return { id, uri: `spotify:track:${id}`, artists: [{ id: artistId }], duration_ms: 200000, is_playable: true };
}

// ============================================================
// Test: empty queue -> queue one successor
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] }; // KNOWN_EMPTY
    if (url.startsWith("/me/player/queue?")) return null;
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("empty (KNOWN_EMPTY) real queue -> one successor queued", result.queued === true);
  check("exactly one POST issued", calls.filter((c) => c.method === "POST").length === 1);
}

// ============================================================
// Test: own pending token visible -> confirm, no duplicate POST
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let queueContents = [];
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) queueContents.push(uri.replace("spotify:track:", ""));
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: queueContents.map((id) => ({ id })) };
    return null;
  };
  const first = await adapter.runLookaheadCycle(); // queues "A"
  check("first cycle queues successor A", first.queued === true && queueContents.includes("A"));
  const postCountAfterFirst = calls.filter((c) => c.method === "POST").length;

  // Second tick: our own token IS visible in the real queue -- must confirm, not re-select/enqueue.
  const second = await adapter.runLookaheadCycle();
  check("second tick with our own pending token visible does not select again", second.queued === false);
  check("second tick issues zero additional POSTs", calls.filter((c) => c.method === "POST").length === postCountAfterFirst);
  check("adapter status shows the successor confirmed", adapter.getLookaheadStatus().successorConfirmed === true);
}

// ============================================================
// Test: a pre-existing provider-generated queue (e.g. Spotify's own
// "Next Up") does NOT block selection -- see
// verify_spotify_provider_queue_coexistence.mjs for the full repair
// this behavior change is part of (real owner finding: a non-empty
// real queue after any track plays is normal, not an owner conflict).
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [{ id: "PROVIDER_NEXT_UP_ITEM" }] }; // KNOWN_NONEMPTY, provider-generated, not ours
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("a pre-existing provider-generated queue item does not block selection", result.queued === true);
  check("exactly one POST is issued despite the provider queue already having an item", calls.filter((c) => c.method === "POST").length === 1);
}

// ============================================================
// Test: queue API error -> zero POST
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url === "/me/player/queue") throw new (await import("../src/adapters/spotify-api-response.js")).SpotifyApiError({ method: "GET", path: "/me/player/queue", status: 500, body: null, bodyType: "EMPTY_ERROR" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("a real queue-truth API error -> QUEUE_STATE_UNKNOWN_CANNOT_INJECT", result.reason === "QUEUE_STATE_UNKNOWN_CANNOT_INJECT");
  check("zero POSTs issued when the queue state is unknown due to an API error", calls.filter((c) => c.method === "POST").length === 0);
}

// ============================================================
// Test: duplicate orchestration ticks -> one POST total
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let queueContents = [];
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A"), rawTrack("B")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      if (uri) queueContents.push(uri.replace("spotify:track:", ""));
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: queueContents.map((id) => ({ id })) };
    return null;
  };

  // Ten rapid-fire orchestration ticks, none of which advance playback --
  // simulates the poll loop firing repeatedly while nothing changes.
  for (let i = 0; i < 10; i += 1) {
    await adapter.runLookaheadCycle();
  }
  check("10 duplicate orchestration ticks produce exactly ONE POST total", calls.filter((c) => c.method === "POST").length === 1);
  check("state settled at SUCCESSOR_QUEUE_REQUESTED or SUCCESSOR_CONFIRMED (never re-selected)", [QueueState.SUCCESSOR_QUEUE_REQUESTED, QueueState.SUCCESSOR_CONFIRMED].includes(adapter.getLookaheadStatus().state));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
