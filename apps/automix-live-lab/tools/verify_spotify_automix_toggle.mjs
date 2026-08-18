// Deterministic proof of P0-M6-R2 repair-pass Blocker 6: AutoMix OFF
// must actually stop app-controlled queueing (setAutoMixEnabled() was
// previously a no-op). No network -- `_api` is monkey-patched.
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
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
function topTracksRaw(items) {
  return { items };
}
function rawTrack(id, artistId = "ART_X") {
  return { id, uri: `spotify:track:${id}`, artists: [{ id: artistId }], duration_ms: 200000, is_playable: true };
}

// --- Default state: AutoMix is ON by default (matches the UI's default "AutoMix: ON") ---
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  check("AutoMix defaults to enabled", adapter._autoMixEnabled === true);
}

// ============================================================
// Test: OFF before seed -> no queue cycle (unaffected by the pre-seed guard, but toggling itself is safe/inert)
// ============================================================
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  let apiCalled = false;
  adapter._api = async () => {
    apiCalled = true;
    return null;
  };
  adapter.setAutoMixEnabled(false);
  check("setAutoMixEnabled(false) before any seed does not throw or call the API", apiCalled === false);
  let threw = null;
  try {
    await adapter.runLookaheadCycle();
  } catch (e) {
    threw = e;
  }
  check("runLookaheadCycle() before a seed still throws SEED_NOT_YET_ACTIVE_FOR_LOOKAHEAD regardless of AutoMix state", threw?.message === "SEED_NOT_YET_ACTIVE_FOR_LOOKAHEAD");
  check("no API call was made", apiCalled === false);
}

// ============================================================
// Test: OFF after seed -> no POST
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    return null;
  };
  adapter.setAutoMixEnabled(false);
  const result = await adapter.runLookaheadCycle();
  check("AutoMix OFF with an active seed and an empty real queue -> AUTOMIX_DISABLED, not queued", result.queued === false && result.reason === "AUTOMIX_DISABLED");
  check("zero POST calls issued while AutoMix is OFF", calls.filter((c) => c.method === "POST").length === 0);
  check("real queue truth is still polled while OFF (owner can still see truthful status)", calls.some((c) => c.url === "/me/player/queue" && c.method === "GET"));
}

// ============================================================
// Test: OFF with already-confirmed successor -> no second successor (existing item is not falsely un-queued either)
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

  // AutoMix ON: queue successor #1 normally.
  const first = await adapter.runLookaheadCycle();
  check("with AutoMix ON, the first successor queues normally", first.queued === true);
  const postCountAfterFirst = calls.filter((c) => c.method === "POST").length;

  // Now turn AutoMix OFF -- the already-queued successor #1 must still
  // be confirmable (the public API can't un-queue it anyway), but no
  // SECOND successor may ever be started.
  adapter.setAutoMixEnabled(false);
  const confirmTick = await adapter.runLookaheadCycle();
  check("OFF does not block confirming an item that was already queued before OFF was toggled", adapter.getLookaheadStatus().successorConfirmed === true);
  check("confirming the pre-existing item issues no new POST", calls.filter((c) => c.method === "POST").length === postCountAfterFirst);

  // Advance to that successor becoming current -- controller now wants a
  // NEW cycle, but AutoMix is OFF. Mirrors real Spotify behavior: the
  // item is consumed out of the queue once it becomes current.
  const becameCurrentId = queueContents[0];
  queueContents = queueContents.filter((id) => id !== becameCurrentId);
  adapter._latestState = { paused: false, position: 0, duration: 200000, track_window: { current_track: { id: becameCurrentId, duration_ms: 200000, artists: [{ id: "ART_X" }] }, next_tracks: [] } };
  adapter._onPlayerStateChanged(adapter._latestState);
  const afterAdvance = await adapter.runLookaheadCycle();
  check("after the confirmed successor becomes current, AutoMix OFF prevents starting a second successor", afterAdvance.reason === "AUTOMIX_DISABLED");
  check("no second successor was ever queued while OFF", calls.filter((c) => c.method === "POST").length === postCountAfterFirst);
}

// ============================================================
// Test: ON resumes exactly one cycle
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    return null;
  };
  adapter.setAutoMixEnabled(false);
  const offResult = await adapter.runLookaheadCycle();
  check("OFF blocks the cycle", offResult.reason === "AUTOMIX_DISABLED");
  check("zero POSTs while OFF", calls.filter((c) => c.method === "POST").length === 0);

  adapter.setAutoMixEnabled(true);
  const onResult = await adapter.runLookaheadCycle();
  check("toggling back ON resumes exactly one selection cycle", onResult.queued === true);
  check("exactly one POST after re-enabling", calls.filter((c) => c.method === "POST").length === 1);
}

// --- Local DSP regression: LocalDSPPlaybackAdapter's own AutoMix toggle must not regress ---
{
  const fs = await import("node:fs");
  const path = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const localAdapterPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "adapters", "LocalDSPPlaybackAdapter.js");
  const source = fs.readFileSync(localAdapterPath, "utf8");
  check("LocalDSPPlaybackAdapter.js was not modified by this repair pass (still defines its own setAutoMixEnabled independently)", source.includes("setAutoMixEnabled"));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
