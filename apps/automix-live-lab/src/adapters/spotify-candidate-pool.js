/**
 * Pure public-candidate-pool assembly (P0-M6-R2 Phase C). No fetch, no
 * DOM -- turns raw Spotify Web API responses into a bounded,
 * deduplicated pool of planner-facing candidates (see
 * spotify-api-requests.js's `toPlannerCandidate`). The Recommendations
 * endpoint is never used (deprecated for new Development Mode Client
 * IDs); this module only ever consumes:
 *   - GET /me/top/tracks              (user-affinity source, preferred)
 *   - GET /me/player/recently-played  (user-affinity source, secondary)
 *   - GET /search?type=track          (bounded fallback, limit<=10, only
 *                                       when the above two sources are
 *                                       too small to plan from)
 */
import { toPlannerCandidate } from "./spotify-api-requests.js";

export const AFFINITY_SOURCE = Object.freeze({
  TOP_TRACK: "TOP_TRACK_AFFINITY",
  RECENT_LISTENING: "RECENT_LISTENING_AFFINITY",
  SEARCH_FALLBACK: "SEARCH_FALLBACK",
});

// A pool this size is already far more than a single-lookahead planner
// ever needs to rank; bounding it keeps memory/log size predictable
// regardless of how large the two source pages are.
export const MAX_CANDIDATE_POOL_SIZE = 60;

// The bounded `GET /search` fallback (Phase C) is only issued when the
// user-affinity sources together produce fewer usable candidates than
// this -- "only when necessary," per the task.
export const MIN_POOL_SIZE_BEFORE_SEARCH_FALLBACK = 5;

/** Maps a `GET /me/top/tracks` raw response -> planner candidates tagged TOP_TRACK_AFFINITY. */
export function candidatesFromTopTracks(rawResponse) {
  const items = Array.isArray(rawResponse?.items) ? rawResponse.items : [];
  return items.map((t) => toPlannerCandidate(t, AFFINITY_SOURCE.TOP_TRACK)).filter(Boolean);
}

/**
 * Maps a `GET /me/player/recently-played` raw response -> planner
 * candidates tagged RECENT_LISTENING_AFFINITY. Each raw item is
 * `{ track, played_at, context }`, not a bare track object. Spotify
 * returns this list most-recent-first, so the index IS the recency rank
 * -- stamped as `recentPlayRank` (0 = most recently played) so
 * spotify-planner.js can prefer candidates NOT played recently (Phase D
 * candidate-preference item 2) independently of the harder repeat-window
 * exclusion.
 */
export function candidatesFromRecentlyPlayed(rawResponse) {
  const items = Array.isArray(rawResponse?.items) ? rawResponse.items : [];
  return items
    .map((entry, index) => {
      const c = toPlannerCandidate(entry?.track, AFFINITY_SOURCE.RECENT_LISTENING);
      if (c) c.recentPlayRank = index;
      return c;
    })
    .filter(Boolean);
}

/** Maps a `GET /search?type=track` raw response -> planner candidates tagged SEARCH_FALLBACK. */
export function candidatesFromSearch(rawResponse) {
  const items = rawResponse?.tracks?.items;
  return (Array.isArray(items) ? items : []).map((t) => toPlannerCandidate(t, AFFINITY_SOURCE.SEARCH_FALLBACK)).filter(Boolean);
}

/**
 * Whether the bounded `GET /search` fallback should even be attempted --
 * only when the user-affinity sources alone left the pool too small to
 * plan a meaningful successor from.
 */
export function needsSearchFallback(poolSizeSoFar, minSize = MIN_POOL_SIZE_BEFORE_SEARCH_FALLBACK) {
  return poolSizeSoFar < minSize;
}

/**
 * Merges multiple candidate-list sources into one bounded, deduplicated
 * pool. De-dup keeps the FIRST occurrence of a given track id, so callers
 * must order `sources` by preference (top tracks, then recently played,
 * then search) -- a track appearing in top tracks stays tagged
 * TOP_TRACK_AFFINITY even if it also turns up in recently played.
 */
export function assembleCandidatePool(sources, maxSize = MAX_CANDIDATE_POOL_SIZE) {
  const seen = new Set();
  const pool = [];
  for (const list of sources || []) {
    for (const c of list || []) {
      if (!c || !c.id || seen.has(c.id)) continue;
      seen.add(c.id);
      pool.push(c);
      if (pool.length >= maxSize) return pool;
    }
  }
  return pool;
}
