// Deterministic proof of P0-M6-R2 Phase B: queue-aware controls must be
// truthful about whether a real Spotify-queued successor exists, using
// only GET /me/player/queue -- never implying Next creates a
// recommendation, and never claiming Play will advance when nothing is
// actually queued. No network.
import { buildGetQueueRequest } from "../src/adapters/spotify-api-requests.js";
import {
  deriveQueueTruth,
  isNextControlEnabled,
  nextControlState,
  describePlayAtNaturalEnd,
  NO_QUEUED_NEXT_TRACK,
  NEXT_TRACK_QUEUED,
} from "../src/adapters/spotify-queue-truth.js";
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// --- Request shape ---
const req = buildGetQueueRequest();
check("GET /me/player/queue -- method is GET", req.method === "GET");
check("GET /me/player/queue -- path/url has no query string", req.path === "/me/player/queue" && req.url === "/me/player/queue");

// --- deriveQueueTruth ---
{
  const empty = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [] });
  check("empty queue -> hasQueuedSuccessor false", empty.hasQueuedSuccessor === false);
  check("empty queue -> queueSize 0", empty.queueSize === 0);
  check("empty queue -> nextToken null", empty.nextToken === null);

  const withQueue = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [{ id: "SUCC1" }, { id: "SUCC2" }] });
  check("populated queue -> hasQueuedSuccessor true", withQueue.hasQueuedSuccessor === true);
  check("populated queue -> queueSize 2", withQueue.queueSize === 2);
  check("populated queue -> nextToken is an opaque TRK_ token, not a raw id", withQueue.nextToken.startsWith("TRK_") && !withQueue.nextToken.includes("SUCC1"));
  check("populated queue -> all tokens sanitized", withQueue.tokens.every((t) => t.startsWith("TRK_")));
  check("populated queue -> currentToken sanitized too", withQueue.currentToken.startsWith("TRK_"));

  const malformed1 = deriveQueueTruth(null);
  check("null response -> treated as empty, no throw", malformed1.hasQueuedSuccessor === false && malformed1.queueSize === 0);

  const malformed2 = deriveQueueTruth({ queue: "not-an-array" });
  check("non-array queue field -> treated as empty, no throw", malformed2.hasQueuedSuccessor === false);

  const malformed3 = deriveQueueTruth({ queue: [null, {}, { id: "" }, { id: "REAL" }] });
  check("malformed queue items are skipped, only well-formed items counted", malformed3.queueSize === 1 && malformed3.tokens.length === 1);
}

// --- isNextControlEnabled / nextControlState ---
{
  const empty = deriveQueueTruth({ queue: [] });
  const populated = deriveQueueTruth({ queue: [{ id: "SUCC1" }] });
  check("isNextControlEnabled false for empty queue", isNextControlEnabled(empty) === false);
  check("isNextControlEnabled true for populated queue", isNextControlEnabled(populated) === true);
  check("nextControlState reports NO_QUEUED_NEXT_TRACK for empty queue", nextControlState(empty) === NO_QUEUED_NEXT_TRACK);
  check("nextControlState reports NEXT_TRACK_QUEUED for populated queue", nextControlState(populated) === NEXT_TRACK_QUEUED);
  check("isNextControlEnabled false for null/unknown truth", isNextControlEnabled(null) === false && isNextControlEnabled(undefined) === false);
}

// --- describePlayAtNaturalEnd (Test 17: empty-queue Next truthfulness) ---
{
  const empty = deriveQueueTruth({ queue: [] });
  const desc = describePlayAtNaturalEnd(empty);
  check("empty queue -> Play is described as restarting the SAME seed, never as advancing", desc.action === "RESTART_SAME_SEED");
  check("empty queue -> message never claims a new track", !/new track|advance/i.test(desc.message) || /not advance/i.test(desc.message));

  const populated = deriveQueueTruth({ queue: [{ id: "SUCC1" }] });
  const desc2 = describePlayAtNaturalEnd(populated);
  check("populated queue -> Play is truthfully described as able to advance", desc2.action === "RESUME_OR_ADVANCE");
}

// --- Adapter integration: getRealQueueTruth() populates _lastQueueTruth; next() gates on it ---
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  check("adapter starts with unknown (null) queue truth", adapter._lastQueueTruth === null);
  check("Next is NOT enabled before any poll (no false claim of availability)", adapter.isNextControlEnabled() === false);

  adapter._api = async () => ({ currently_playing: { id: "SEED123" }, queue: [] });
  const truth = await adapter.getRealQueueTruth();
  check("getRealQueueTruth() calls GET /me/player/queue and derives truth", truth.hasQueuedSuccessor === false);
  check("_lastQueueTruth is populated after the poll", adapter._lastQueueTruth !== null && adapter._lastQueueTruth.queueSize === 0);
  check("getNextControlState() reflects NO_QUEUED_NEXT_TRACK", adapter.getNextControlState() === NO_QUEUED_NEXT_TRACK);

  // next() must refuse to call the SDK at all when the queue is truthfully empty.
  let sdkNextCalled = false;
  adapter._player = { nextTrack: async () => { sdkNextCalled = true; } };
  const nextResult = await adapter.next();
  check("next() refuses (does not call SDK nextTrack) when queue is truthfully empty", sdkNextCalled === false);
  check("next() returns NO_QUEUED_NEXT_TRACK instead of silently no-op'ing", nextResult.ok === false && nextResult.reason === NO_QUEUED_NEXT_TRACK);
  check("next() does NOT create manual-action attribution when it refuses to act", adapter._manualAction.pendingSinceMs === null);

  // Once a real successor IS queued, next() must behave exactly as before (regression).
  adapter._api = async () => ({ currently_playing: { id: "SEED123" }, queue: [{ id: "SUCC1" }] });
  await adapter.getRealQueueTruth();
  check("getNextControlState() flips to NEXT_TRACK_QUEUED once a real successor exists", adapter.getNextControlState() === NEXT_TRACK_QUEUED);
  sdkNextCalled = false;
  await adapter.next();
  check("next() calls the SDK once a real successor is confirmed queued", sdkNextCalled === true);
  check("next() still begins manual-action attribution in the normal case (regression)", adapter._manualAction.pendingSinceMs !== null);

  // A poll failure (network error) must never crash, and must be treated as no-successor (fail safe, not fail open).
  const adapter2 = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter2._api = async () => {
    throw new Error("SPOTIFY_API_ERROR: GET /me/player/queue -> 500");
  };
  const truthAfterFailure = await adapter2.getRealQueueTruth();
  check("a poll failure resolves to no-successor (fail safe), does not throw out of getRealQueueTruth()", truthAfterFailure.hasQueuedSuccessor === false);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
