// Deterministic proof of P0-M6-R2 repair-pass Blocker 4: a failing
// queue-write must never be retried every ~2s orchestration tick
// forever. No network -- `_api`/`Date.now` are monkey-patched.
import { classifyQueueFailure, isBlockerActive, QueueBlockerType, DEFAULT_TRANSIENT_COOLDOWN_MS, DEFAULT_RATE_LIMIT_COOLDOWN_MS } from "../src/adapters/spotify-queue-error-policy.js";
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

// --- Pure classification ---
{
  check("401 -> TERMINAL_AUTH", classifyQueueFailure(401).type === QueueBlockerType.TERMINAL_AUTH);
  check("403 -> TERMINAL_AUTH", classifyQueueFailure(403).type === QueueBlockerType.TERMINAL_AUTH);
  check("429 with Retry-After -> COOLDOWN honoring the exact value", classifyQueueFailure(429, 12).cooldownMs === 12000);
  check("429 without Retry-After -> COOLDOWN with the default bound", classifyQueueFailure(429, null).cooldownMs === DEFAULT_RATE_LIMIT_COOLDOWN_MS);
  check("404 -> CANDIDATE_FAILED (candidate-specific, not systemic)", classifyQueueFailure(404).type === QueueBlockerType.CANDIDATE_FAILED);
  check("500 -> COOLDOWN with the default transient bound", classifyQueueFailure(500).type === QueueBlockerType.COOLDOWN && classifyQueueFailure(500).cooldownMs === DEFAULT_TRANSIENT_COOLDOWN_MS);
  check("network failure (no status) -> COOLDOWN, treated as transient/systemic", classifyQueueFailure(null).type === QueueBlockerType.COOLDOWN);

  check("isBlockerActive: null blocker is never active", isBlockerActive(null, Date.now()) === false);
  check("isBlockerActive: TERMINAL_AUTH never auto-clears", isBlockerActive({ type: QueueBlockerType.TERMINAL_AUTH }, Date.now() + 999999999) === true);
  const cooldown = { type: QueueBlockerType.COOLDOWN, untilMs: 1000 };
  check("isBlockerActive: COOLDOWN active before untilMs", isBlockerActive(cooldown, 500) === true);
  check("isBlockerActive: COOLDOWN expired after untilMs", isBlockerActive(cooldown, 1500) === false);
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

// ============================================================
// Test: candidate-specific permanent failure (404) -- exclude just that candidate, try another next tick, no cooldown
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const postAttempts = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("BAD"), rawTrack("GOOD")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) {
      const uri = new URLSearchParams(url.split("?")[1]).get("uri");
      postAttempts.push(uri);
      if (uri.includes("BAD")) throw new SpotifyApiError({ method: "POST", path: "/me/player/queue", status: 404, body: { error: { status: 404, message: "Not found" } }, bodyType: "JSON_ERROR" });
      return null; // GOOD succeeds
    }
    return null;
  };
  // "BAD" wins the deterministic tie-break first (both TOP_TRACK_AFFINITY) -- whichever it is, the point is: after it fails with 404, it must never be retried, and a DIFFERENT candidate must succeed on the very next tick, with NO cooldown delay.
  const first = await adapter.runLookaheadCycle();
  check("first tick attempted the failing candidate and failed", first.queued === false);
  check("the failed candidate is now excluded from future selection", adapter.getLookaheadStatus().failedCandidateCount === 1);
  check("no systemic blocker/cooldown was set for a candidate-specific 404", adapter.getLookaheadStatus().queueBlocker === null);

  const second = await adapter.runLookaheadCycle();
  check("the VERY NEXT tick (no cooldown) succeeds with the OTHER candidate", second.queued === true);
  // The controller's own bounded retry (MAX_QUEUE_REQUEST_ATTEMPTS = 3)
  // legitimately retries the SAME candidate up to 3 times WITHIN that
  // one failed selection cycle -- the Blocker 4 guarantee is that it is
  // never attempted again in any LATER cycle, not that it's attempted
  // only once ever.
  check("the failed candidate was attempted 3 times within its one bounded cycle, then never again", postAttempts.filter((u) => u.includes("BAD")).length === 3);
}

// ============================================================
// Test: 401/403 -- terminal auth/scope blocker, no automatic retry loop
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let postCount = 0;
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCount += 1;
      throw new SpotifyApiError({ method: "POST", path: "/me/player/queue", status: 403, body: { error: { status: 403, message: "Insufficient client scope" } }, bodyType: "JSON_ERROR" });
    }
    return null;
  };
  const first = await adapter.runLookaheadCycle();
  check("a 403 failure sets a terminal auth blocker", adapter.getLookaheadStatus().queueBlocker?.type === "TERMINAL_AUTH_BLOCKER");
  const postCountAfterFirst = postCount;

  // Ten more ticks -- a terminal auth blocker never auto-clears, so none of these may attempt a new POST.
  for (let i = 0; i < 10; i += 1) {
    const r = await adapter.runLookaheadCycle();
    check(`tick ${i + 2} after a terminal auth blocker reports TERMINAL_AUTH_BLOCKER, not a fresh attempt`, r.reason === "TERMINAL_AUTH_BLOCKER");
  }
  check("zero additional POST attempts across 10 more ticks after a terminal auth blocker", postCount === postCountAfterFirst);
}

// ============================================================
// Test: 429 -- honors Retry-After, enters a visible cooldown, clears after it elapses
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let postCount = 0;
  const originalNow = Date.now;
  let fakeNow = 1_000_000;
  Date.now = () => fakeNow;

  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCount += 1;
      if (postCount <= 3) throw new SpotifyApiError({ method: "POST", path: "/me/player/queue", status: 429, body: null, bodyType: "EMPTY_ERROR", retryAfterSec: 5 });
      return null;
    }
    return null;
  };

  const first = await adapter.runLookaheadCycle();
  check("a 429 failure enters a COOLDOWN blocker honoring Retry-After (5s)", adapter.getLookaheadStatus().queueBlocker?.type === "COOLDOWN" && adapter.getLookaheadStatus().queueBlocker?.untilMs === fakeNow + 5000);
  const postCountAfterFirst = postCount;

  fakeNow += 1000; // 1s later -- still within the 5s cooldown
  const stillCoolingDown = await adapter.runLookaheadCycle();
  check("still within the cooldown window -> no new POST attempt", stillCoolingDown.reason === "IN_COOLDOWN" && postCount === postCountAfterFirst);

  fakeNow += 5000; // now past the 5s cooldown
  const afterCooldown = await adapter.runLookaheadCycle();
  check("after the cooldown elapses, a new attempt is made automatically", postCount === postCountAfterFirst + 1);

  Date.now = originalNow;
}

// ============================================================
// Test: transient 5xx/network -- bounded attempts (within one cycle) then a bounded cooldown, not an immediate retry
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let postCount = 0;
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCount += 1;
      throw new SpotifyApiError({ method: "POST", path: "/me/player/queue", status: 500, body: null, bodyType: "EMPTY_ERROR" });
    }
    return null;
  };
  await adapter.runLookaheadCycle();
  check("the LookaheadQueueController's own bounded retry attempted exactly 3 times within the one cycle", postCount === 3);
  check("after those 3 attempts fail, a COOLDOWN blocker is set (not an immediate 4th attempt)", adapter.getLookaheadStatus().queueBlocker?.type === "COOLDOWN");
}

// ============================================================
// Test: 20-tick simulation -- unbounded POST requests are impossible
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let postCount = 0;
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([rawTrack("A")]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCount += 1;
      throw new SpotifyApiError({ method: "POST", path: "/me/player/queue", status: 500, body: null, bodyType: "EMPTY_ERROR" });
    }
    return null;
  };
  for (let i = 0; i < 20; i += 1) {
    await adapter.runLookaheadCycle();
  }
  // Without the cooldown, 20 ticks x 3 bounded-retry attempts each = 60
  // POSTs. With the repair, only the FIRST tick's bounded cycle (3
  // attempts) ever fires -- every subsequent tick is blocked by the
  // still-active cooldown (Date.now() was never advanced in this test).
  check("20 orchestration ticks against a permanently-failing endpoint produce far fewer than 60 POSTs", postCount < 10);
  check("in fact exactly 3 (one bounded cycle, then cooldown-blocked for the rest)", postCount === 3);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
