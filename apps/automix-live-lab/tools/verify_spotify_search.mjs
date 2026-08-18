// Deterministic proof of the repaired search request shape (Issue #11,
// PM comment `5324307503`, BLOCKER 1). No network call, no Spotify
// credentials -- pure function under test.
import { buildSearchRequest, MAX_SEARCH_LIMIT, toSeedCandidate } from "../src/adapters/spotify-api-requests.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

check("MAX_SEARCH_LIMIT is 10 (current Development Mode cap)", MAX_SEARCH_LIMIT === 10);

const req = buildSearchRequest("daft punk");
check("method is GET", req.method === "GET");
check("path is /search", req.path === "/search");
check("type=track is present", req.query.get("type") === "track");
check("q carries the exact query text", req.query.get("q") === "daft punk");
check("default limit is 10", req.query.get("limit") === "10");
check("url string embeds the query params", req.url.startsWith("/search?"));
check("url never mentions playlist (BLOCKER 1: no playlist-first flow)", !req.url.includes("playlist"));

const reqCustomLimit = buildSearchRequest("test", 5);
check("custom limit under the cap is honored", reqCustomLimit.query.get("limit") === "5");

const reqOverLimit = buildSearchRequest("test", 999);
check("limit is clamped to MAX_SEARCH_LIMIT even if a caller requests more", reqOverLimit.query.get("limit") === "10");

const reqZeroLimit = buildSearchRequest("test", 0);
check("limit is clamped to at least 1", reqZeroLimit.query.get("limit") === "1");

const reqFloatLimit = buildSearchRequest("test", 7.9);
check("non-integer limit is truncated, not rounded up over the cap", reqFloatLimit.query.get("limit") === "7");

let threw = false;
try {
  buildSearchRequest("");
} catch {
  threw = true;
}
check("empty query throws SPOTIFY_SEARCH_QUERY_REQUIRED instead of building a bad request", threw);

const specialCharsReq = buildSearchRequest("a&b=c d");
check("special characters are URL-encoded by URLSearchParams (round-trips back to the exact original query)", specialCharsReq.query.get("q") === "a&b=c d");

const candidate = toSeedCandidate({
  id: "abc123",
  uri: "spotify:track:abc123",
  name: "Some Song",
  artists: [{ name: "Artist A" }, { name: "Artist B" }],
  duration_ms: 210000,
});
check("toSeedCandidate maps id/uri/name through", candidate.id === "abc123" && candidate.uri === "spotify:track:abc123" && candidate.name === "Some Song");
check("toSeedCandidate joins multiple artists", candidate.artists === "Artist A, Artist B");
check("toSeedCandidate maps duration_ms -> durationMs", candidate.durationMs === 210000);

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
