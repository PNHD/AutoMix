// Deterministic proof of the Transfer Playback runtime fix, found during
// real owner live-testing: PUT /me/player/play 404'd ("Device not found")
// on a freshly-ready Web Playback SDK device because it was never
// transferred to (made active) first. No network call -- the request
// SHAPE is tested directly, and the ordering/idempotency is proven by
// monkey-patching `_api` on the REAL SpotifyPublicControlAdapter class
// to record calls instead of hitting the network.
import { buildTransferPlaybackRequest } from "../src/adapters/spotify-api-requests.js";
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
const req = buildTransferPlaybackRequest("device123");
check("method is PUT", req.method === "PUT");
check("path/url is /me/player (no query string)", req.path === "/me/player" && req.url === "/me/player");
check("body carries device_ids as a single-element array", Array.isArray(req.body.device_ids) && req.body.device_ids.length === 1 && req.body.device_ids[0] === "device123");
check("play defaults to false (activate without auto-resuming whatever was last playing)", req.body.play === false);
check("body has exactly device_ids and play, no other keys", Object.keys(req.body).sort().join(",") === "device_ids,play");

const reqPlayTrue = buildTransferPlaybackRequest("device123", true);
check("play flag is honored when explicitly requested", reqPlayTrue.body.play === true);

let threwNoDevice = false;
try {
  buildTransferPlaybackRequest(null);
} catch (e) {
  threwNoDevice = e.message === "SPOTIFY_DEVICE_ID_REQUIRED";
}
check("missing device id throws SPOTIFY_DEVICE_ID_REQUIRED", threwNoDevice);

// --- Integration: playSeedTrack() must transfer BEFORE it plays, exactly once per device_id ---
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._deviceId = "device123";
  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    return null; // simulate 204 No Content for both PUTs
  };

  await adapter.playSeedTrack("spotify:track:SEED123");
  check("playSeedTrack issues exactly 2 API calls (transfer, then play)", calls.length === 2);
  check("call 1 is the Transfer Playback PUT to /me/player", calls[0].url === "/me/player" && calls[0].method === "PUT");
  check("call 2 is the seed play PUT to /me/player/play?device_id=...", calls[1].url === "/me/player/play?device_id=device123" && calls[1].method === "PUT");
  check("_deviceActivated is true after the first seed play", adapter._deviceActivated === true);

  // A second seed play on the SAME device must NOT re-issue the transfer (idempotent).
  await adapter.playSeedTrack("spotify:track:SEED456");
  check("a second playSeedTrack on the same device issues only 1 more call (play only, no re-transfer)", calls.length === 3);
  check("the 3rd call is the play PUT, not another transfer", calls[2].url.startsWith("/me/player/play"));
}

// --- A fresh device_ready event (e.g. reconnect) must reset activation so transfer happens again ---
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._deviceId = "device123";
  adapter._deviceActivated = true; // simulate an already-activated device from a prior connection

  // Simulate what the 'ready' SDK listener does on a (re)connect with a new device_id.
  adapter._deviceId = "device456";
  adapter._deviceActivated = false;

  const calls = [];
  adapter._api = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || "GET" });
    return null;
  };
  await adapter.playSeedTrack("spotify:track:SEED789");
  check("a new device_id (simulated reconnect) re-issues the transfer call", calls[0].url === "/me/player" && calls.length === 2);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
