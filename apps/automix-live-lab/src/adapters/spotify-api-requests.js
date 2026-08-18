/**
 * Pure Spotify Web API request-shape builders -- no fetch, no DOM, no
 * class state. Kept separate from SpotifyPublicControlAdapter.js so
 * request SHAPE (path/query/method/body) can be unit-tested without
 * mocking a network call (see tools/verify_spotify_search.mjs and
 * tools/verify_spotify_play_seed.mjs).
 *
 * Repair pass (Issue #11, PM comment `5324307503`,
 * `P0_M6_R1_SPOTIFY_SEED_LOOP_REPAIR_REQUIRED`, BLOCKER 1): the prior
 * pass's core Spotify flow centered `/me/playlists`. The product loop is
 * search ONE arbitrary track -> play that ONE track as a seed -> observe
 * Spotify's own automatic continuation. This module intentionally has no
 * playlist-shaped request builder at all.
 */

// Spotify's current Development Mode search quota caps `limit` at 10 for
// apps without extended quota (PM comment: "current Development Mode max
// limit <= 10"). Clamped here, not just documented, so a caller can never
// silently exceed it.
export const MAX_SEARCH_LIMIT = 10;

/**
 * GET /v1/search?q=...&type=track&limit=<=10
 * Returns a plain description of the request, not a live fetch call, so
 * it can be asserted against in a pure unit test.
 */
export function buildSearchRequest(query, limit = MAX_SEARCH_LIMIT) {
  if (typeof query !== "string" || query.trim().length === 0) {
    throw new Error("SPOTIFY_SEARCH_QUERY_REQUIRED");
  }
  const clampedLimit = Math.max(1, Math.min(MAX_SEARCH_LIMIT, Math.trunc(limit)));
  const params = new URLSearchParams({ q: query, type: "track", limit: String(clampedLimit) });
  return {
    method: "GET",
    path: "/search",
    query: params,
    url: `/search?${params.toString()}`,
  };
}

/**
 * PUT /v1/me/player/play?device_id=<id>  body: {"uris":["spotify:track:..."]}
 * BLOCKER 1: exactly ONE uri, targeting the Web Playback SDK's own
 * device_id -- this is "play one seed track," never a playlist context.
 */
export function buildPlaySeedRequest(deviceId, uri) {
  if (!deviceId) throw new Error("SPOTIFY_DEVICE_ID_REQUIRED");
  if (typeof uri !== "string" || !uri.startsWith("spotify:track:")) {
    throw new Error("SPOTIFY_SEED_URI_MUST_BE_A_SINGLE_TRACK_URI");
  }
  const params = new URLSearchParams({ device_id: deviceId });
  return {
    method: "PUT",
    path: "/me/player/play",
    query: params,
    url: `/me/player/play?${params.toString()}`,
    body: { uris: [uri] },
  };
}

/** Maps one raw Spotify search-result track object to the minimal shape the seed-picker UI needs. */
export function toSeedCandidate(track) {
  return {
    id: track.id,
    uri: track.uri,
    name: track.name,
    artists: (track.artists || []).map((a) => a.name).join(", "),
    durationMs: track.duration_ms,
  };
}
