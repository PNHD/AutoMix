// Deterministic proof of P0-M6-R2 Phase B + repair-pass Blocker 2: queue
// truth must be an explicit tri-state value -- a real API error must
// NEVER be silently represented as "empty queue." No network.
import { buildGetQueueRequest } from "../src/adapters/spotify-api-requests.js";
import {
  QueueTruthState,
  deriveQueueTruth,
  unknownNotPolledQueueTruth,
  unknownApiErrorQueueTruth,
  isNextControlEnabled,
  canInjectToQueue,
  nextControlState,
  describePlayAtNaturalEnd,
  NO_QUEUED_NEXT_TRACK,
  NEXT_TRACK_QUEUED,
  QUEUE_STATE_UNKNOWN_NOT_POLLED,
  QUEUE_STATE_UNKNOWN_API_ERROR,
} from "../src/adapters/spotify-queue-truth.js";
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { SpotifyApiError } from "../src/adapters/spotify-api-response.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// --- Request shape (unchanged) ---
const req = buildGetQueueRequest();
check("GET /me/player/queue -- method is GET", req.method === "GET");
check("GET /me/player/queue -- path/url has no query string", req.path === "/me/player/queue" && req.url === "/me/player/queue");

// --- deriveQueueTruth (successful poll only) ---
{
  const empty = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [] });
  check("empty queue -> state KNOWN_EMPTY", empty.state === QueueTruthState.KNOWN_EMPTY);
  check("empty queue -> hasQueuedSuccessor false", empty.hasQueuedSuccessor === false);
  check("empty queue -> error is null", empty.error === null);

  const withQueue = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [{ id: "SUCC1" }, { id: "SUCC2" }] });
  check("populated queue -> state KNOWN_NONEMPTY", withQueue.state === QueueTruthState.KNOWN_NONEMPTY);
  check("populated queue -> hasQueuedSuccessor true", withQueue.hasQueuedSuccessor === true);
  check("populated queue -> queueSize 2", withQueue.queueSize === 2);
  check("populated queue -> nextToken is an opaque TRK_ token, not a raw id", withQueue.nextToken.startsWith("TRK_") && !withQueue.nextToken.includes("SUCC1"));
  check("populated queue -> all tokens sanitized", withQueue.tokens.every((t) => t.startsWith("TRK_")));

  const malformed = deriveQueueTruth(null);
  check("null response passed to deriveQueueTruth -> still KNOWN_EMPTY (caller decides whether that's trustworthy)", malformed.state === QueueTruthState.KNOWN_EMPTY);
}

// --- unknownNotPolledQueueTruth / unknownApiErrorQueueTruth ---
{
  const notPolled = unknownNotPolledQueueTruth();
  check("unknownNotPolledQueueTruth -> state UNKNOWN_NOT_POLLED", notPolled.state === QueueTruthState.UNKNOWN_NOT_POLLED);
  check("unknownNotPolledQueueTruth -> hasQueuedSuccessor false", notPolled.hasQueuedSuccessor === false);

  const apiError = unknownApiErrorQueueTruth({ path: "/me/player/queue", status: 500, bodyType: "EMPTY_ERROR", sanitizedMessage: "(empty error body)" });
  check("unknownApiErrorQueueTruth -> state UNKNOWN_API_ERROR", apiError.state === QueueTruthState.UNKNOWN_API_ERROR);
  check("unknownApiErrorQueueTruth -> hasQueuedSuccessor false (never treated as empty)", apiError.hasQueuedSuccessor === false);
  check("unknownApiErrorQueueTruth -> carries sanitized diagnostics", apiError.error.status === 500 && apiError.error.path === "/me/player/queue" && apiError.error.sanitizedMessage === "(empty error body)");
  check("unknownApiErrorQueueTruth -> diagnostics never carry a raw query string", !apiError.error.path.includes("?"));
}

// --- isNextControlEnabled / canInjectToQueue / nextControlState: all four states ---
{
  const known_empty = deriveQueueTruth({ queue: [] });
  const known_nonempty = deriveQueueTruth({ queue: [{ id: "SUCC1" }] });
  const not_polled = unknownNotPolledQueueTruth();
  const api_error = unknownApiErrorQueueTruth({ path: "/me/player/queue", status: 500, bodyType: "EMPTY_ERROR" });

  check("isNextControlEnabled: true ONLY for KNOWN_NONEMPTY", isNextControlEnabled(known_nonempty) === true && isNextControlEnabled(known_empty) === false && isNextControlEnabled(not_polled) === false && isNextControlEnabled(api_error) === false);

  // Real owner finding (provider-queue coexistence repair): Spotify's
  // own client keeps a provider-generated queue (e.g. "Next Up")
  // populated after any track plays -- a KNOWN_NONEMPTY real queue is
  // normal, not an owner conflict, and must NOT block injection.
  // POST /me/player/queue is documented to add an item to be played
  // NEXT, so this app's successor is injected ahead of whatever
  // provider items already exist, which are left untouched. Injection
  // remains forbidden only when the real state is genuinely unknown.
  check("canInjectToQueue: true for KNOWN_EMPTY", canInjectToQueue(known_empty) === true);
  check("canInjectToQueue: true for KNOWN_NONEMPTY too (a provider queue is not a blocker)", canInjectToQueue(known_nonempty) === true);
  check("canInjectToQueue: false for UNKNOWN_NOT_POLLED (never inject on an unconfirmed state)", canInjectToQueue(not_polled) === false);
  check("canInjectToQueue: false for UNKNOWN_API_ERROR (queue injection forbidden on API error)", canInjectToQueue(api_error) === false);

  check("nextControlState: NEXT_TRACK_QUEUED for KNOWN_NONEMPTY", nextControlState(known_nonempty) === NEXT_TRACK_QUEUED);
  check("nextControlState: NO_QUEUED_NEXT_TRACK for KNOWN_EMPTY", nextControlState(known_empty) === NO_QUEUED_NEXT_TRACK);
  check("nextControlState: QUEUE_STATE_UNKNOWN_NOT_POLLED distinct from empty", nextControlState(not_polled) === QUEUE_STATE_UNKNOWN_NOT_POLLED);
  check("nextControlState: QUEUE_STATE_UNKNOWN_API_ERROR distinct from empty/not-polled -- owner UI must show the REAL blocker", nextControlState(api_error) === QUEUE_STATE_UNKNOWN_API_ERROR);
}

// --- describePlayAtNaturalEnd across all four states ---
{
  const known_empty = deriveQueueTruth({ queue: [] });
  const known_nonempty = deriveQueueTruth({ queue: [{ id: "SUCC1" }] });
  const api_error = unknownApiErrorQueueTruth({ path: "/me/player/queue", status: 500, bodyType: "EMPTY_ERROR" });

  check("Play description: KNOWN_EMPTY -> RESTART_SAME_SEED, truthful", describePlayAtNaturalEnd(known_empty).action === "RESTART_SAME_SEED");
  check("Play description: KNOWN_NONEMPTY -> RESUME_OR_ADVANCE", describePlayAtNaturalEnd(known_nonempty).action === "RESUME_OR_ADVANCE");
  check("Play description: UNKNOWN_API_ERROR -> UNKNOWN, never falsely claims restart OR advance", describePlayAtNaturalEnd(api_error).action === "UNKNOWN");
  check("Play description: UNKNOWN state message says so honestly", /unknown/i.test(describePlayAtNaturalEnd(api_error).message));
}

// --- Adapter integration: getRealQueueTruth() tri-state, sanitized diagnostics, next() gating ---
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  check("adapter starts with UNKNOWN_NOT_POLLED queue truth (never null)", adapter._lastQueueTruth.state === QueueTruthState.UNKNOWN_NOT_POLLED);
  check("Next is NOT enabled before any poll (no false claim of availability)", adapter.isNextControlEnabled() === false);

  // -- Successful poll, empty queue --
  adapter._api = async () => ({ currently_playing: { id: "SEED123" }, queue: [] });
  const truth1 = await adapter.getRealQueueTruth();
  check("getRealQueueTruth() successful poll -> KNOWN_EMPTY", truth1.state === QueueTruthState.KNOWN_EMPTY);
  check("_lastQueueTruth updated to KNOWN_EMPTY", adapter._lastQueueTruth.state === QueueTruthState.KNOWN_EMPTY);
  check("getNextControlState() reflects NO_QUEUED_NEXT_TRACK", adapter.getNextControlState() === NO_QUEUED_NEXT_TRACK);

  // -- next() refuses when queue is confirmed empty --
  let sdkNextCalled = false;
  adapter._player = { nextTrack: async () => { sdkNextCalled = true; } };
  const nextResult = await adapter.next();
  check("next() refuses when queue is confirmed KNOWN_EMPTY", sdkNextCalled === false && nextResult.ok === false && nextResult.reason === NO_QUEUED_NEXT_TRACK);
  check("next() does NOT create manual-action attribution when it refuses to act", adapter._manualAction.pendingSinceMs === null);

  // -- API error poll: must become UNKNOWN_API_ERROR, never KNOWN_EMPTY (the actual reported defect) --
  adapter._api = async () => {
    throw new SpotifyApiError({ method: "GET", path: "/me/player/queue", status: 500, body: null, bodyType: "EMPTY_ERROR" });
  };
  const truth2 = await adapter.getRealQueueTruth();
  check("getRealQueueTruth() on a real API error -> UNKNOWN_API_ERROR, never KNOWN_EMPTY", truth2.state === QueueTruthState.UNKNOWN_API_ERROR);
  check("UNKNOWN_API_ERROR carries sanitized diagnostics (status/path/bodyType)", truth2.error.status === 500 && truth2.error.path === "/me/player/queue" && truth2.error.bodyType === "EMPTY_ERROR");
  check("getNextControlState() shows the REAL blocker (QUEUE_STATE_UNKNOWN_API_ERROR), not a false empty", adapter.getNextControlState() === QUEUE_STATE_UNKNOWN_API_ERROR);

  sdkNextCalled = false;
  const nextResult2 = await adapter.next();
  check("next() also refuses on UNKNOWN_API_ERROR (disabled for EMPTY OR UNKNOWN)", sdkNextCalled === false && nextResult2.ok === false);

  // -- Diagnostics must never leak a query string / raw identifier, even for a query-bearing failing call --
  adapter._api = async () => {
    throw new SpotifyApiError({ method: "GET", path: "/me/player/queue", status: 403, body: { error: { status: 403, message: "Insufficient client scope" } }, bodyType: "JSON_ERROR" });
  };
  const truth3 = await adapter.getRealQueueTruth();
  check("UNKNOWN_API_ERROR extracts Spotify's sanitized error message (403 scope error)", truth3.error.sanitizedMessage === "Insufficient client scope");
  check("sanitized diagnostics never contain a raw access token substring", !JSON.stringify(truth3).toLowerCase().includes("bearer"));

  // -- Once a real successor IS confirmed queued, next() behaves normally (regression) --
  adapter._api = async () => ({ currently_playing: { id: "SEED123" }, queue: [{ id: "SUCC1" }] });
  await adapter.getRealQueueTruth();
  check("getNextControlState() flips to NEXT_TRACK_QUEUED once a real successor exists", adapter.getNextControlState() === NEXT_TRACK_QUEUED);
  sdkNextCalled = false;
  await adapter.next();
  check("next() calls the SDK once a real successor is confirmed queued", sdkNextCalled === true);
  check("next() still begins manual-action attribution in the normal case (regression)", adapter._manualAction.pendingSinceMs !== null);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
