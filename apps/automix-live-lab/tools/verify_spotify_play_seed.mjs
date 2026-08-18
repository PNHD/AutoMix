// Deterministic proof of the repaired one-URI seed-playback request shape
// (Issue #11, PM comment `5324307503`, BLOCKER 1). No network call.
import { buildPlaySeedRequest } from "../src/adapters/spotify-api-requests.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

const req = buildPlaySeedRequest("device123", "spotify:track:seedtrack1");
check("method is PUT", req.method === "PUT");
check("path is /me/player/play", req.path === "/me/player/play");
check("device_id is targeted via query param", req.query.get("device_id") === "device123");
check("url embeds device_id", req.url === "/me/player/play?device_id=device123");
check("body carries exactly ONE uri", Array.isArray(req.body.uris) && req.body.uris.length === 1);
check("body's single uri matches the requested seed", req.body.uris[0] === "spotify:track:seedtrack1");
check("body has no other keys (no context_uri/offset -- never a playlist context)", Object.keys(req.body).length === 1 && Object.keys(req.body)[0] === "uris");

let threwNoDevice = false;
try {
  buildPlaySeedRequest(null, "spotify:track:x");
} catch (e) {
  threwNoDevice = e.message === "SPOTIFY_DEVICE_ID_REQUIRED";
}
check("missing device id throws SPOTIFY_DEVICE_ID_REQUIRED", threwNoDevice);

let threwBadUri = false;
try {
  buildPlaySeedRequest("device123", "spotify:playlist:notatrack");
} catch (e) {
  threwBadUri = e.message === "SPOTIFY_SEED_URI_MUST_BE_A_SINGLE_TRACK_URI";
}
check("a playlist URI is rejected (BLOCKER 1: never a playlist context)", threwBadUri);

let threwArrayUri = false;
try {
  buildPlaySeedRequest("device123", ["spotify:track:a", "spotify:track:b"]);
} catch {
  threwArrayUri = true;
}
check("an array of uris (multi-track) is rejected -- exactly one seed only", threwArrayUri);

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
