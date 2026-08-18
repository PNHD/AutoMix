// Deterministic proof of P0-M6-R2 Phase C: the public candidate pool
// must be built ONLY from top-tracks / recently-played / bounded search,
// bounded in size, deduplicated, and must never touch Recommendations,
// Audio Features/Analysis, or the deprecated artist-top-tracks endpoint
// (see also verify_spotify_provider_boundary.mjs for the static grep
// proving those endpoints are absent from the source entirely).
import { buildTopTracksRequest, buildRecentlyPlayedRequest, MAX_CANDIDATE_PAGE_LIMIT, toPlannerCandidate } from "../src/adapters/spotify-api-requests.js";
import {
  AFFINITY_SOURCE,
  MAX_CANDIDATE_POOL_SIZE,
  candidatesFromTopTracks,
  candidatesFromRecentlyPlayed,
  candidatesFromSearch,
  needsSearchFallback,
  assembleCandidatePool,
} from "../src/adapters/spotify-candidate-pool.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// --- Request shapes ---
const topReq = buildTopTracksRequest(20);
check("top-tracks request: GET /me/top/tracks", topReq.method === "GET" && topReq.path === "/me/top/tracks");
check("top-tracks request: limit is clamped to <= MAX_CANDIDATE_PAGE_LIMIT", buildTopTracksRequest(999).url.includes(`limit=${MAX_CANDIDATE_PAGE_LIMIT}`));

const recentReq = buildRecentlyPlayedRequest(20);
check("recently-played request: GET /me/player/recently-played", recentReq.method === "GET" && recentReq.path === "/me/player/recently-played");
check("recently-played request: limit clamped too", buildRecentlyPlayedRequest(999).url.includes(`limit=${MAX_CANDIDATE_PAGE_LIMIT}`));

// --- toPlannerCandidate mapping (no title/name leakage) ---
{
  const raw = { id: "T1", uri: "spotify:track:T1", name: "Some Song", artists: [{ id: "A1", name: "Some Artist" }], duration_ms: 210000, explicit: true, is_playable: false };
  const c = toPlannerCandidate(raw, AFFINITY_SOURCE.TOP_TRACK);
  check("toPlannerCandidate keeps id/uri/artist-id/duration/explicit/playability", c.id === "T1" && c.uri === "spotify:track:T1" && c.primaryArtistId === "A1" && c.durationMs === 210000 && c.explicit === true && c.isPlayable === false);
  check("toPlannerCandidate never carries a name/title field", !("name" in c) && !("title" in c));
  check("toPlannerCandidate stamps the affinity source", c.affinitySource === AFFINITY_SOURCE.TOP_TRACK);

  check("toPlannerCandidate returns null for a malformed item (no id)", toPlannerCandidate({ uri: "spotify:track:X" }, AFFINITY_SOURCE.TOP_TRACK) === null);
  check("toPlannerCandidate returns null for a malformed item (no uri)", toPlannerCandidate({ id: "X" }, AFFINITY_SOURCE.TOP_TRACK) === null);
  check("toPlannerCandidate returns null for null input", toPlannerCandidate(null, AFFINITY_SOURCE.TOP_TRACK) === null);
  check("toPlannerCandidate defaults isPlayable true when the field is absent (no market context)", toPlannerCandidate({ id: "Y", uri: "spotify:track:Y" }, AFFINITY_SOURCE.TOP_TRACK).isPlayable === true);
}

// --- candidatesFromTopTracks / candidatesFromRecentlyPlayed / candidatesFromSearch ---
{
  const topRaw = { items: [{ id: "T1", uri: "spotify:track:T1", artists: [{ id: "A1" }] }, null, { id: "T2", uri: "spotify:track:T2", artists: [{ id: "A2" }] }] };
  const topCandidates = candidatesFromTopTracks(topRaw);
  check("candidatesFromTopTracks skips malformed entries, tags TOP_TRACK_AFFINITY", topCandidates.length === 2 && topCandidates.every((c) => c.affinitySource === AFFINITY_SOURCE.TOP_TRACK));

  const recentRaw = { items: [{ track: { id: "R1", uri: "spotify:track:R1", artists: [{ id: "A3" }] }, played_at: "2026-08-01T00:00:00Z" }, { track: null }] };
  const recentCandidates = candidatesFromRecentlyPlayed(recentRaw);
  check("candidatesFromRecentlyPlayed unwraps { track } envelope, tags RECENT_LISTENING_AFFINITY", recentCandidates.length === 1 && recentCandidates[0].affinitySource === AFFINITY_SOURCE.RECENT_LISTENING);

  const searchRaw = { tracks: { items: [{ id: "S1", uri: "spotify:track:S1", artists: [{ id: "A4" }] }] } };
  const searchCandidates = candidatesFromSearch(searchRaw);
  check("candidatesFromSearch tags SEARCH_FALLBACK", searchCandidates.length === 1 && searchCandidates[0].affinitySource === AFFINITY_SOURCE.SEARCH_FALLBACK);

  check("all three source mappers tolerate a null/malformed raw response", candidatesFromTopTracks(null).length === 0 && candidatesFromRecentlyPlayed(undefined).length === 0 && candidatesFromSearch({}).length === 0);
}

// --- needsSearchFallback ---
check("needsSearchFallback is true when the affinity pool is small", needsSearchFallback(2) === true);
check("needsSearchFallback is false once the affinity pool is large enough", needsSearchFallback(20) === false);

// --- assembleCandidatePool: bounding + de-dup, first-occurrence wins ---
{
  const top = [{ id: "DUP", uri: "spotify:track:DUP", affinitySource: AFFINITY_SOURCE.TOP_TRACK }, { id: "T2", uri: "spotify:track:T2", affinitySource: AFFINITY_SOURCE.TOP_TRACK }];
  const recent = [{ id: "DUP", uri: "spotify:track:DUP", affinitySource: AFFINITY_SOURCE.RECENT_LISTENING }, { id: "R2", uri: "spotify:track:R2", affinitySource: AFFINITY_SOURCE.RECENT_LISTENING }];
  const pool = assembleCandidatePool([top, recent]);
  check("assembleCandidatePool de-duplicates by id across sources", pool.length === 3);
  check("assembleCandidatePool keeps the FIRST-seen source's affinity tag for a duplicate id", pool.find((c) => c.id === "DUP").affinitySource === AFFINITY_SOURCE.TOP_TRACK);

  const big = Array.from({ length: 100 }, (_, i) => ({ id: `X${i}`, uri: `spotify:track:X${i}` }));
  const bounded = assembleCandidatePool([big]);
  check(`assembleCandidatePool bounds the pool to MAX_CANDIDATE_POOL_SIZE (${MAX_CANDIDATE_POOL_SIZE})`, bounded.length === MAX_CANDIDATE_POOL_SIZE);

  const customBound = assembleCandidatePool([big], 10);
  check("assembleCandidatePool respects a caller-supplied maxSize", customBound.length === 10);

  check("assembleCandidatePool tolerates undefined/malformed sources without throwing", assembleCandidatePool([undefined, null, [null, { id: "Z", uri: "spotify:track:Z" }]]).length === 1);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
