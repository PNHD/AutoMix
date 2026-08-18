// Deterministic proof of the P0-M6-R2 Phase A repair: the shared Spotify
// API response parser must never crash on Player write endpoints' real
// response shapes (204, empty 200, plain-text 200), must preserve status
// + body for every error shape, and must never leak a bearer token. No
// network -- fake Response-like objects only.
import { parseSpotifyApiResponse, sanitizeErrorText, SpotifyApiError } from "../src/adapters/spotify-api-response.js";
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

function fakeRes({ status, ok, text }) {
  return { status, ok: ok ?? (status >= 200 && status < 300), text: async () => text };
}

// --- Test 1: 200 JSON API response ---
{
  const res = fakeRes({ status: 200, text: JSON.stringify({ tracks: { items: [1, 2, 3] } }) });
  const parsed = await parseSpotifyApiResponse(res);
  check("200 JSON -> ok true", parsed.ok === true);
  check("200 JSON -> bodyType JSON", parsed.bodyType === "JSON");
  check("200 JSON -> body parsed correctly", parsed.body.tracks.items.length === 3);
  check("200 JSON -> status preserved", parsed.status === 200);
}

// --- Test 2: 204 empty success (Player write endpoints) ---
{
  const res = fakeRes({ status: 204, ok: true, text: "" });
  const parsed = await parseSpotifyApiResponse(res);
  check("204 -> ok true", parsed.ok === true);
  check("204 -> bodyType EMPTY_204, deterministic (not parsed)", parsed.bodyType === "EMPTY_204");
  check("204 -> body is null", parsed.body === null);
}

// --- Test 3: successful empty/non-JSON body (the actual reported live bug) ---
{
  const resEmpty200 = fakeRes({ status: 200, text: "" });
  const parsedEmpty = await parseSpotifyApiResponse(resEmpty200);
  check("200 with empty body -> ok true, no throw", parsedEmpty.ok === true);
  check("200 with empty body -> bodyType EMPTY_SUCCESS", parsedEmpty.bodyType === "EMPTY_SUCCESS");

  const resWhitespace = fakeRes({ status: 200, text: "   \n" });
  const parsedWhitespace = await parseSpotifyApiResponse(resWhitespace);
  check("200 with whitespace-only body -> EMPTY_SUCCESS, not a JSON.parse crash", parsedWhitespace.bodyType === "EMPTY_SUCCESS");

  const resPlainText = fakeRes({ status: 200, text: "OK" });
  const parsedPlainText = await parseSpotifyApiResponse(resPlainText);
  check("200 with plain-text 'OK' body -> ok true, no throw (this exact input crashed the old JSON.parse)", parsedPlainText.ok === true);
  check("200 with plain-text body -> bodyType TEXT, raw text preserved", parsedPlainText.bodyType === "TEXT" && parsedPlainText.body === "OK");
}

// --- Test 4: JSON API error ---
{
  const errBody = { error: { status: 404, message: "Device not found" } };
  const res = fakeRes({ status: 404, ok: false, text: JSON.stringify(errBody) });
  const parsed = await parseSpotifyApiResponse(res);
  check("404 JSON error -> ok false", parsed.ok === false);
  check("404 JSON error -> status preserved", parsed.status === 404);
  check("404 JSON error -> bodyType JSON_ERROR", parsed.bodyType === "JSON_ERROR");
  check("404 JSON error -> parsed body preserved (message intact)", parsed.body.error.message === "Device not found");
}

// --- Test 5: text/malformed API error ---
{
  const res = fakeRes({ status: 502, ok: false, text: "<html>Bad Gateway</html>" });
  const parsed = await parseSpotifyApiResponse(res);
  check("502 malformed body -> ok false, no throw", parsed.ok === false);
  check("502 malformed body -> bodyType TEXT_ERROR", parsed.bodyType === "TEXT_ERROR");
  check("502 malformed body -> status preserved", parsed.status === 502);
  check("502 malformed body -> raw safe text preserved", parsed.body.includes("Bad Gateway"));

  const resEmptyErr = fakeRes({ status: 500, ok: false, text: "" });
  const parsedEmptyErr = await parseSpotifyApiResponse(resEmptyErr);
  check("500 empty error body -> documented EMPTY_ERROR fallback, no throw", parsedEmptyErr.ok === false && parsedEmptyErr.bodyType === "EMPTY_ERROR" && parsedEmptyErr.body === null);
}

// --- Test 6: token redaction ---
{
  const leaky = "upstream said: Authorization: Bearer BQD1abcXYZ789.superSecretToken~value not accepted";
  const sanitized = sanitizeErrorText(leaky);
  check("sanitizeErrorText redacts a bearer token if one ever appears in a body", !sanitized.includes("BQD1abcXYZ789"));
  check("sanitizeErrorText leaves the redaction marker in place", sanitized.includes("[REDACTED]"));

  const long = "x".repeat(1000);
  check("sanitizeErrorText truncates long error bodies", sanitizeErrorText(long).length < 1000 && sanitizeErrorText(long).includes("TRUNCATED"));

  // Full-stack check: SpotifyApiError itself must never carry the token
  // used to make the request -- only method/path/status/body/bodyType.
  const err = new SpotifyApiError({ method: "PUT", path: "/me/player/play", status: 404, body: { error: { message: "Device not found" } }, bodyType: "JSON_ERROR" });
  const serialized = JSON.stringify({ message: err.message, ...err });
  check("SpotifyApiError has no token/authorization field at all", !("token" in err) && !("authorization" in err) && !("headers" in err));
  check("SpotifyApiError message contains no secret-shaped substring", !/Bearer\s+[A-Za-z0-9._~-]{10,}/i.test(serialized));
}

// --- Integration: adapter._api() end to end against a fake fetch, proving the real code path (not just the pure parser) ---
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._token = { access_token: "FAKE_TOKEN_NEVER_LOGGED", refresh_token: "r", expires_at_ms: Date.now() + 999999 };
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({ status: 204, ok: true, text: async () => "" });
  const result204 = await adapter._api("/me/player/play?device_id=abc", { method: "PUT" });
  check("adapter._api() on a real 204 response resolves (not throws) with null", result204 === null);

  globalThis.fetch = async () => ({ status: 200, ok: true, text: async () => "" });
  const resultEmpty200 = await adapter._api("/me/player/play?device_id=abc", { method: "PUT" });
  check("adapter._api() on a 200-with-empty-body response resolves (not throws) -- this is the exact reported live bug", resultEmpty200 === null);

  globalThis.fetch = async () => ({ status: 404, ok: false, text: async () => JSON.stringify({ error: { status: 404, message: "Device not found" } }) });
  let threw = null;
  try {
    await adapter._api("/me/player/play?device_id=abc", { method: "PUT" });
  } catch (e) {
    threw = e;
  }
  check("adapter._api() on a 404 JSON error throws SpotifyApiError with status/body preserved", threw instanceof SpotifyApiError && threw.status === 404 && threw.body.error.message === "Device not found");
  check("adapter._api() thrown error's message/fields never contain the access token", !JSON.stringify({ message: threw.message, ...threw }).includes("FAKE_TOKEN_NEVER_LOGGED"));

  globalThis.fetch = originalFetch;
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
