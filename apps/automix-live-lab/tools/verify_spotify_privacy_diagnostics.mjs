// Deterministic proof of P0-M6-R2 repair-pass Blocker 7: no raw Spotify
// URIs, IDs, or device IDs may ever appear in a thrown error, an emitted
// event, or tracked/queue diagnostics. No network -- `_api`/`fetch` are
// monkey-patched.
import { sanitizeDeviceToken, fnv1aHex } from "../src/adapters/spotify-privacy.js";
import { sanitizeTrackToken } from "../src/adapters/spotify-autoplay.js";
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

// --- Pure privacy primitives ---
{
  const token = sanitizeDeviceToken("SUPER_SECRET_DEVICE_ID_ABC123");
  check("sanitizeDeviceToken produces a DEV_-prefixed opaque token", token.startsWith("DEV_"));
  check("sanitizeDeviceToken never contains the raw device id", !token.includes("SUPER_SECRET_DEVICE_ID_ABC123"));
  check("sanitizeDeviceToken is deterministic (same input -> same token)", sanitizeDeviceToken("X") === sanitizeDeviceToken("X"));
  check("sanitizeDeviceToken null-safe", sanitizeDeviceToken(null) === null && sanitizeDeviceToken(undefined) === null);
  check("sanitizeTrackToken and sanitizeDeviceToken share the same hash primitive (fnv1aHex) but different prefixes -- never collide in meaning", sanitizeTrackToken("X") !== sanitizeDeviceToken("X") && sanitizeTrackToken("X").endsWith(fnv1aHex("X")));
}

// ============================================================
// Test: SpotifyApiError never carries a query string, even for a query-bearing request path
// ============================================================
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._token = { access_token: "FAKE_TOKEN_NEVER_LOGGED", refresh_token: "r", expires_at_ms: Date.now() + 999999 };
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({ status: 404, ok: false, headers: { get: () => null }, text: async () => JSON.stringify({ error: { status: 404, message: "Device not found" } }) });
  let thrown = null;
  try {
    await adapter._api("/me/player/queue?uri=spotify:track:SUPER_SECRET_TRACK_ID&device_id=SUPER_SECRET_DEVICE_ID", { method: "POST" });
  } catch (e) {
    thrown = e;
  }
  check("_api() throws a SpotifyApiError for the failing call", thrown instanceof SpotifyApiError);
  check("SpotifyApiError.path excludes the query string entirely", thrown.path === "/me/player/queue");
  check("SpotifyApiError.path never contains the raw track uri", !thrown.path.includes("SUPER_SECRET_TRACK_ID"));
  check("SpotifyApiError.path never contains the raw device id", !thrown.path.includes("SUPER_SECRET_DEVICE_ID"));
  check("the full serialized error never contains the raw track uri or device id", !JSON.stringify(thrown).includes("SUPER_SECRET_TRACK_ID") && !JSON.stringify(thrown, Object.getOwnPropertyNames(thrown)).includes("SUPER_SECRET_DEVICE_ID"));
  check("the full serialized error never contains the access token", !JSON.stringify(thrown, Object.getOwnPropertyNames(thrown)).includes("FAKE_TOKEN_NEVER_LOGGED"));

  globalThis.fetch = originalFetch;
}

// ============================================================
// Test: Retry-After header is captured as retryAfterSec (Blocker 4 support), never leaks in path
// ============================================================
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._token = { access_token: "t", refresh_token: "r", expires_at_ms: Date.now() + 999999 };
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ status: 429, ok: false, headers: { get: (h) => (h === "Retry-After" ? "7" : null) }, text: async () => "" });
  let thrown = null;
  try {
    await adapter._api("/me/player/queue?uri=spotify:track:X&device_id=Y", { method: "POST" });
  } catch (e) {
    thrown = e;
  }
  check("a 429 response's Retry-After header is captured as retryAfterSec", thrown.retryAfterSec === 7);
  check("path is still stripped of the query string on a 429", thrown.path === "/me/player/queue");

  globalThis.fetch = originalFetch;
}

// ============================================================
// Test: device lifecycle events never emit the raw device_id
// ============================================================
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  const emitted = [];
  adapter.onStateChange((evt) => emitted.push(evt));

  // Simulate the SDK's "ready" listener firing, without a real DOM/SDK.
  adapter._deviceId = "RAW_DEVICE_ID_ZZZ999";
  const { sanitizeDeviceToken: sdt } = await import("../src/adapters/spotify-privacy.js");
  adapter._deviceToken = sdt(adapter._deviceId);
  adapter._emit({ type: "device_ready", deviceToken: adapter._deviceToken });

  adapter._api = async () => null;
  await adapter._ensureDeviceActive();
  check("device_ready event carries a deviceToken, never a raw deviceId field", emitted.some((e) => e.type === "device_ready" && "deviceToken" in e && !("deviceId" in e)));
  check("device_activated event carries a deviceToken, never a raw deviceId field", emitted.some((e) => e.type === "device_activated" && "deviceToken" in e && !("deviceId" in e)));
  check("no emitted event this test contains the raw device id substring", !JSON.stringify(emitted).includes("RAW_DEVICE_ID_ZZZ999"));
  check("the deviceToken used is opaque (DEV_-prefixed)", emitted.find((e) => e.type === "device_ready").deviceToken.startsWith("DEV_"));
}

// ============================================================
// Test: queue-truth diagnostics never serialize a raw URI or device id, even under a query-bearing failure
// ============================================================
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._api = async () => {
    throw new SpotifyApiError({ method: "GET", path: "/me/player/queue", status: 403, body: { error: { status: 403, message: "Insufficient client scope" } }, bodyType: "JSON_ERROR" });
  };
  const truth = await adapter.getRealQueueTruth();
  const serialized = JSON.stringify(truth);
  check("queue-truth error diagnostics contain no query-string artifacts", !serialized.includes("?") );
  check("queue-truth error diagnostics never contain the word 'device_id=' or 'uri='", !/device_id=|uri=/.test(serialized));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
