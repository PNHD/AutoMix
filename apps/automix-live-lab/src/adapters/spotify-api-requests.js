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

/**
 * PUT /v1/me/player  body: {"device_ids":["<id>"],"play":false}
 *
 * Runtime defect found during real owner validation (not a PM comment --
 * observed directly against the live Spotify API): a freshly-`ready` Web
 * Playback SDK device is registered with Spotify Connect but is NOT
 * automatically the *active* device. Calling `PUT /me/player/play` with
 * that `device_id` before transferring playback to it 404s
 * ("Device not found"), even though the device_id itself is valid. The
 * official flow (Web Playback SDK Getting Started / Transfer Playback
 * docs) is: SDK connect -> `ready(device_id)` -> Transfer Playback to
 * that device -> THEN Start/Resume Playback. Uses the same
 * `user-modify-playback-state` scope already requested for
 * `buildPlaySeedRequest` -- no scope broadening needed.
 */
export function buildTransferPlaybackRequest(deviceId, play = false) {
  if (!deviceId) throw new Error("SPOTIFY_DEVICE_ID_REQUIRED");
  return {
    method: "PUT",
    path: "/me/player",
    url: "/me/player",
    body: { device_ids: [deviceId], play },
  };
}

// P0-M6-R2 Phase C: bounded candidate-pool page sizes. Spotify's own max
// `limit` for both of these endpoints is 50; the planner only ever needs
// a small pool, so this stays well under that ceiling by default.
export const MAX_CANDIDATE_PAGE_LIMIT = 50;
const DEFAULT_CANDIDATE_PAGE_LIMIT = 20;

function clampCandidateLimit(limit) {
  return Math.max(1, Math.min(MAX_CANDIDATE_PAGE_LIMIT, Math.trunc(Number.isFinite(limit) ? limit : DEFAULT_CANDIDATE_PAGE_LIMIT)));
}

/**
 * GET /v1/me/player/queue
 * P0-M6-R2 Phase B: the only public surface that can truthfully answer
 * "does a real queued successor exist" -- requires `user-read-playback-state`.
 */
export function buildGetQueueRequest() {
  return { method: "GET", path: "/me/player/queue", url: "/me/player/queue" };
}

/**
 * POST /v1/me/player/queue?uri=<uri>&device_id=<id>
 * P0-M6-R2 Phase E: adds exactly ONE track to the live Spotify queue.
 * `uri` and `device_id` are query parameters on this endpoint, not a
 * JSON body -- there is no body at all. Responds 204 on success (must be
 * treated as success by the Phase A repair).
 */
export function buildQueueTrackRequest(uri, deviceId) {
  if (typeof uri !== "string" || !uri.startsWith("spotify:track:")) {
    throw new Error("SPOTIFY_QUEUE_URI_MUST_BE_A_SINGLE_TRACK_URI");
  }
  const params = new URLSearchParams({ uri });
  if (deviceId) params.set("device_id", deviceId);
  return {
    method: "POST",
    path: "/me/player/queue",
    query: params,
    url: `/me/player/queue?${params.toString()}`,
  };
}

/**
 * GET /v1/me/top/tracks?limit=<=50
 * P0-M6-R2 Phase C: one of two user-affinity candidate-pool sources.
 * Requires `user-top-read`. Never the deprecated Recommendations
 * endpoint and never Audio Features/Audio Analysis.
 */
export function buildTopTracksRequest(limit = DEFAULT_CANDIDATE_PAGE_LIMIT) {
  const params = new URLSearchParams({ limit: String(clampCandidateLimit(limit)) });
  return { method: "GET", path: "/me/top/tracks", query: params, url: `/me/top/tracks?${params.toString()}` };
}

/**
 * GET /v1/me/player/recently-played?limit=<=50
 * P0-M6-R2 Phase C: the second user-affinity candidate-pool source.
 * Requires `user-read-recently-played`.
 */
export function buildRecentlyPlayedRequest(limit = DEFAULT_CANDIDATE_PAGE_LIMIT) {
  const params = new URLSearchParams({ limit: String(clampCandidateLimit(limit)) });
  return { method: "GET", path: "/me/player/recently-played", query: params, url: `/me/player/recently-played?${params.toString()}` };
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

/**
 * Maps one raw Spotify track object (from top-tracks, recently-played, or
 * search) into the minimal, planner-facing shape `spotify-planner.js`
 * needs -- primary artist id (for same-artist exclusion), duration (for
 * duration-continuity ranking), explicit flag, and playability. Never
 * includes name/title text -- the planner's own diagnostics stay
 * opaque-token-only (BLOCKER 2 precedent, spotify-autoplay.js).
 * `affinitySource` is stamped by the caller (spotify-candidate-pool.js)
 * since the same raw shape is reused across different source endpoints.
 */
export function toPlannerCandidate(track, affinitySource) {
  if (!track || typeof track !== "object" || !track.id || !track.uri) return null;
  return {
    id: track.id,
    uri: track.uri,
    primaryArtistId: track.artists?.[0]?.id ?? null,
    durationMs: typeof track.duration_ms === "number" ? track.duration_ms : null,
    explicit: track.explicit === true,
    isPlayable: track.is_playable !== false, // absent field (search/top-tracks without market) defaults to playable
    affinitySource,
  };
}
