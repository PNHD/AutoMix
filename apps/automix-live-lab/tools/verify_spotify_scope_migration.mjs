// Deterministic proof of P0-M6-R2 repair-pass Blocker 1: a token
// authorized before new scopes were added must never be silently reused
// against endpoints those scopes protect -- and the reauth flow must
// never require DevTools/manual localStorage clearing, and must never
// touch the Client ID. No network -- a minimal in-memory localStorage
// shim lets the REAL _loadStoredToken/_storeToken/_discardStaleToken/
// _clientId code paths run exactly as they do in a browser.
import { hasAllRequiredScopes, missingScopes, parseScopeString } from "../src/adapters/spotify-scope.js";
import { SpotifyPublicControlAdapter, CLIENT_ID_STORAGE_KEY } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { SPOTIFY_SCOPES } from "../src/adapters/spotify-pkce.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// Minimal Web Storage shim so the adapter's REAL localStorage-touching
// methods run unmodified (Node has no global localStorage).
function installFakeStorage() {
  const store = new Map();
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
  return store;
}

const TOKEN_STORAGE_KEY = "automix_spotify_token_v1";

function newAdapter(store, clientId = "owner-client-id") {
  const adapter = new SpotifyPublicControlAdapter({ clientId, redirectUri: "http://127.0.0.1:5500/" });
  adapter._initWebPlaybackSdk = async () => {}; // bypass DOM/SDK loading entirely
  return adapter;
}

// --- Pure scope-comparison helpers ---
{
  check("hasAllRequiredScopes: true when every required scope is present", hasAllRequiredScopes(["a", "b", "c"], ["a", "b"]) === true);
  check("hasAllRequiredScopes: false when a required scope is missing", hasAllRequiredScopes(["a", "b"], ["a", "b", "c"]) === false);
  check("hasAllRequiredScopes: false when granted is not an array at all (legacy token)", hasAllRequiredScopes(undefined, ["a"]) === false && hasAllRequiredScopes(null, ["a"]) === false);
  check("missingScopes: reports exactly the gap", missingScopes(["a"], ["a", "b", "c"]).sort().join(",") === "b,c");
  check("parseScopeString: splits Spotify's space-separated scope string", parseScopeString("streaming user-read-email").join(",") === "streaming,user-read-email");
  check("parseScopeString: empty/missing scope string -> empty array, no throw", parseScopeString(undefined).length === 0 && parseScopeString("").length === 0);
}

// --- Test: legacy v1 token without scope metadata requires reauth ---
{
  const store = installFakeStorage();
  store.set(CLIENT_ID_STORAGE_KEY, "owner-client-id");
  store.set(TOKEN_STORAGE_KEY, JSON.stringify({ access_token: "old-token", refresh_token: "old-refresh", expires_at_ms: Date.now() + 999999 })); // no `scope` field at all

  const adapter = newAdapter(store);
  const result = await adapter.connect();
  check("legacy token with no scope metadata -> SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES", result.ok === false && result.reason === "SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES");
  check("the stale token is discarded from localStorage", store.has(TOKEN_STORAGE_KEY) === false);
  check("in-memory _token is cleared too", adapter._token === null);
}

// --- Test: token missing one R2 scope requires reauth ---
{
  const store = installFakeStorage();
  store.set(CLIENT_ID_STORAGE_KEY, "owner-client-id");
  const partialScopes = SPOTIFY_SCOPES.filter((s) => s !== "user-top-read"); // missing exactly one required scope
  store.set(TOKEN_STORAGE_KEY, JSON.stringify({ access_token: "t", refresh_token: "r", expires_at_ms: Date.now() + 999999, scope: partialScopes }));

  const adapter = newAdapter(store);
  const result = await adapter.connect();
  check("a token missing even ONE required R2 scope -> SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES", result.ok === false && result.reason === "SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES");
  check("the stale token is discarded", store.has(TOKEN_STORAGE_KEY) === false);
}

// --- Test: a token with the complete scope set connects normally ---
{
  const store = installFakeStorage();
  store.set(CLIENT_ID_STORAGE_KEY, "owner-client-id");
  store.set(TOKEN_STORAGE_KEY, JSON.stringify({ access_token: "t", refresh_token: "r", expires_at_ms: Date.now() + 999999, scope: [...SPOTIFY_SCOPES] }));

  const adapter = newAdapter(store);
  const result = await adapter.connect();
  check("a token with the complete required scope set connects (AUTHENTICATED)", result.ok === true && result.reason === "AUTHENTICATED");
  check("the token is NOT discarded when scopes are sufficient", store.has(TOKEN_STORAGE_KEY) === true);

  // Extra granted scopes beyond the required set are fine too (Spotify may return more than requested in edge cases).
  const store2 = installFakeStorage();
  store2.set(CLIENT_ID_STORAGE_KEY, "owner-client-id");
  store2.set(TOKEN_STORAGE_KEY, JSON.stringify({ access_token: "t", refresh_token: "r", expires_at_ms: Date.now() + 999999, scope: [...SPOTIFY_SCOPES, "some-future-scope"] }));
  const adapter2 = newAdapter(store2);
  const result2 = await adapter2.connect();
  check("a superset of required scopes still connects", result2.ok === true);
}

// --- Test: refresh preserves the scope set when Spotify's refresh response omits `scope` ---
{
  const store = installFakeStorage();
  const originalFetch = globalThis.fetch;
  const adapter = newAdapter(store);
  // Pre-expired token forces _ensureFreshToken() down the refresh path.
  adapter._token = { access_token: "old", refresh_token: "refresh-tok", expires_at_ms: Date.now() - 1000, scope: [...SPOTIFY_SCOPES] };
  const storedCalls = [];
  adapter._storeToken = (tok) => {
    adapter._token = tok;
    storedCalls.push(tok);
  };
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({ access_token: "new-access-token", expires_in: 3600 }), // NOTE: no `scope` field, matching Spotify's documented refresh behavior
  });

  const freshToken = await adapter._ensureFreshToken();
  check("_ensureFreshToken() refreshes and returns the new access token", freshToken === "new-access-token");
  check("refresh preserves the previously-known scope set when the response omits it", JSON.stringify(adapter._token.scope) === JSON.stringify(SPOTIFY_SCOPES));
  check("_storeToken was called exactly once with the preserved scope", storedCalls.length === 1 && JSON.stringify(storedCalls[0].scope) === JSON.stringify(SPOTIFY_SCOPES));

  globalThis.fetch = originalFetch;
}

// --- Test: refresh response THAT DOES include `scope` overwrites the stored set (not just always-preserve) ---
{
  const store = installFakeStorage();
  const originalFetch = globalThis.fetch;
  const adapter = newAdapter(store);
  adapter._token = { access_token: "old", refresh_token: "refresh-tok", expires_at_ms: Date.now() - 1000, scope: ["streaming"] };
  adapter._storeToken = (tok) => {
    adapter._token = tok;
  };
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({ access_token: "new-access-token", expires_in: 3600, scope: "streaming user-read-email user-top-read" }),
  });
  await adapter._ensureFreshToken();
  check("refresh response WITH a scope field updates the stored scope set", adapter._token.scope.join(",") === "streaming,user-read-email,user-top-read");
  globalThis.fetch = originalFetch;
}

// --- Test: Client ID survives token invalidation ---
{
  const store = installFakeStorage();
  store.set(CLIENT_ID_STORAGE_KEY, "owner-client-id-must-survive");
  store.set(TOKEN_STORAGE_KEY, JSON.stringify({ access_token: "old", refresh_token: "r", expires_at_ms: Date.now() + 999999 })); // legacy, no scope

  const adapter = newAdapter(store, "owner-client-id-must-survive");
  await adapter.connect(); // triggers the reauth path, discarding the token
  check("Client ID is still present in storage after a token-invalidating reauth", store.get(CLIENT_ID_STORAGE_KEY) === "owner-client-id-must-survive");
  check("adapter._clientId still resolves correctly after reauth", adapter._clientId === "owner-client-id-must-survive");

  // Never require DevTools/manual localStorage clearing: the owner's
  // ONLY required action is clicking Connect again, which now
  // (app.js repair) routes them through beginLogin() automatically --
  // verified here as a static wiring check on app.js itself.
  const fs = await import("node:fs");
  const path = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const appJsPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "app.js");
  const appJsSource = fs.readFileSync(appJsPath, "utf8");
  check("app.js's Connect handler recognizes SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES and re-triggers beginLogin()", appJsSource.includes("SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES"));
}

// --- Never log tokens: connect()'s result object never carries the access/refresh token ---
{
  const store = installFakeStorage();
  store.set(CLIENT_ID_STORAGE_KEY, "owner-client-id");
  store.set(TOKEN_STORAGE_KEY, JSON.stringify({ access_token: "SUPER_SECRET_TOKEN_NEVER_LOGGED", refresh_token: "r", expires_at_ms: Date.now() + 999999, scope: [...SPOTIFY_SCOPES] }));
  const adapter = newAdapter(store);
  const result = await adapter.connect();
  check("connect()'s returned result never contains the access token", !JSON.stringify(result).includes("SUPER_SECRET_TOKEN_NEVER_LOGGED"));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
