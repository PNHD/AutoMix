/**
 * Deterministic metadata-and-affinity next-track planner v0
 * (P0-M6-R2 Phase D). No fetch, no DOM -- pure function over a candidate
 * pool (see spotify-candidate-pool.js) plus session state.
 *
 * This is explicitly NOT an acoustic compatibility model. It never
 * claims (and must never be made to claim) BPM match, key match, beat
 * compatibility, energy match, or transition quality -- public Spotify
 * metadata available to this app does not support those claims (Audio
 * Features/Audio Analysis are unavailable to new Client IDs, see
 * SpotifyPublicControlAdapter.js's getAutoMixPlan() docs). It only ranks
 * by user-affinity source, recent-listening recency, artist diversity,
 * duration continuity, and a final deterministic opaque-ID tie-break.
 */
import { sanitizeTrackToken } from "./spotify-autoplay.js";

export const EXCLUSION_REASON = Object.freeze({
  MALFORMED_ITEM: "MALFORMED_ITEM",
  MISSING_URI: "MISSING_URI",
  IS_CURRENT_TRACK: "IS_CURRENT_TRACK",
  ALREADY_PLAYED_THIS_SESSION: "ALREADY_PLAYED_THIS_SESSION",
  RECENT_REPEAT_EXCLUDED: "RECENT_REPEAT_EXCLUDED",
  UNPLAYABLE: "UNPLAYABLE",
  IMMEDIATE_SAME_ARTIST_REPETITION: "IMMEDIATE_SAME_ARTIST_REPETITION",
  EXPLICIT_CONTENT_RESTRICTED: "EXPLICIT_CONTENT_RESTRICTED",
  DUPLICATE_URI: "DUPLICATE_URI",
  // P0-M6-R2 repair, Blocker 4: a candidate whose queue-write failed
  // non-recoverably this session (see spotify-queue-error-policy.js's
  // CANDIDATE_FAILED classification) must never be offered again --
  // otherwise every orchestration tick would just re-select and re-fail
  // on the exact same track forever.
  PERMANENTLY_FAILED_THIS_SESSION: "PERMANENTLY_FAILED_THIS_SESSION",
});

export const SELECTION_REASON = Object.freeze({
  TOP_TRACK_AFFINITY: "TOP_TRACK_AFFINITY",
  RECENT_LISTENING_AFFINITY: "RECENT_LISTENING_AFFINITY",
  ARTIST_DIVERSITY: "ARTIST_DIVERSITY",
  DURATION_CONTINUITY: "DURATION_CONTINUITY",
  DETERMINISTIC_TIE_BREAK: "DETERMINISTIC_TIE_BREAK",
});

function isMalformedCandidate(c) {
  return !c || typeof c !== "object" || typeof c.id !== "string" || c.id.length === 0;
}

function hasValidTrackUri(c) {
  return typeof c.uri === "string" && c.uri.startsWith("spotify:track:");
}

/**
 * Evaluates every hard exclusion, in priority order, and returns the
 * FIRST matching reason code -- or `null` if the candidate is eligible.
 * Exported standalone so tests (and diagnostics UI) can evaluate one
 * candidate in isolation without running the full ranking pass.
 */
export function evaluateHardExclusion(candidate, ctx = {}) {
  if (isMalformedCandidate(candidate)) return EXCLUSION_REASON.MALFORMED_ITEM;
  if (!hasValidTrackUri(candidate)) return EXCLUSION_REASON.MISSING_URI;

  const token = sanitizeTrackToken(candidate.id);
  if (ctx.seenTokens?.has(token)) return EXCLUSION_REASON.DUPLICATE_URI;
  if (ctx.failedCandidateTokens?.has(token)) return EXCLUSION_REASON.PERMANENTLY_FAILED_THIS_SESSION;
  if (ctx.currentTrackToken && token === ctx.currentTrackToken) return EXCLUSION_REASON.IS_CURRENT_TRACK;
  if (ctx.sessionPlayedTokens?.has(token)) return EXCLUSION_REASON.ALREADY_PLAYED_THIS_SESSION;
  if (ctx.recentRepeatWindowTokens?.has(token)) return EXCLUSION_REASON.RECENT_REPEAT_EXCLUDED;
  if (candidate.isPlayable === false) return EXCLUSION_REASON.UNPLAYABLE;
  if (ctx.currentPrimaryArtistId && candidate.primaryArtistId && candidate.primaryArtistId === ctx.currentPrimaryArtistId) {
    return EXCLUSION_REASON.IMMEDIATE_SAME_ARTIST_REPETITION;
  }
  if (ctx.excludeExplicit && candidate.explicit === true) return EXCLUSION_REASON.EXPLICIT_CONTENT_RESTRICTED;
  return null;
}

function affinityRankFor(source) {
  if (source === "TOP_TRACK_AFFINITY") return 2;
  if (source === "RECENT_LISTENING_AFFINITY") return 1;
  return 0; // SEARCH_FALLBACK or unknown
}

/**
 * Selects exactly one successor from `candidates`, in this priority
 * order (per task Phase D "Candidate preference"):
 *   1. user-affinity source (top tracks > recently played > search)
 *   2. not played recently (candidates with a lower/no recentPlayRank
 *      -- i.e. played longer ago or not in the recently-played window
 *      at all -- are preferred over ones played very recently)
 *   3. artist diversity (an artist not already used this AutoMix session
 *      is preferred over one that was)
 *   4. reasonable duration continuity vs. the current track, when both
 *      durations are known
 *   5. deterministic opaque-ID tie-break (never random)
 *
 * `candidates` are expected in `toPlannerCandidate` shape (id, uri,
 * primaryArtistId, durationMs, explicit, isPlayable, affinitySource,
 * optional recentPlayRank).
 */
export function selectNextTrack({
  candidates,
  currentTrack = null,
  sessionPlayedIds = [],
  recentRepeatWindowIds = [],
  usedArtistIdsThisSession = [],
  excludeExplicit = false,
  failedCandidateTokens = null,
} = {}) {
  const currentTrackToken = currentTrack?.id ? sanitizeTrackToken(currentTrack.id) : null;
  const currentPrimaryArtistId = currentTrack?.primaryArtistId ?? null;
  const sessionPlayedTokens = new Set((sessionPlayedIds || []).map((id) => sanitizeTrackToken(id)));
  const recentRepeatWindowTokens = new Set((recentRepeatWindowIds || []).map((id) => sanitizeTrackToken(id)));
  const usedArtistIds = new Set((usedArtistIdsThisSession || []).filter(Boolean));
  const seenTokens = new Set();

  const excluded = [];
  const eligible = [];

  for (const candidate of candidates || []) {
    const reason = evaluateHardExclusion(candidate, {
      currentTrackToken,
      sessionPlayedTokens,
      recentRepeatWindowTokens,
      currentPrimaryArtistId,
      excludeExplicit,
      seenTokens,
      failedCandidateTokens,
    });
    const token = candidate && typeof candidate.id === "string" ? sanitizeTrackToken(candidate.id) : null;
    if (reason) {
      excluded.push({ token, reason });
      continue;
    }
    seenTokens.add(token);
    eligible.push({ candidate, token });
  }

  const candidatePoolSize = Array.isArray(candidates) ? candidates.length : 0;
  if (eligible.length === 0) {
    return { selected: null, token: null, reason: "NO_ELIGIBLE_CANDIDATES", excluded, candidatePoolSize };
  }

  const scored = eligible.map(({ candidate, token }) => ({
    candidate,
    token,
    affinityRank: affinityRankFor(candidate.affinitySource),
    // Larger = played longer ago (or never seen in recently-played at all -> +Infinity, most preferred).
    notRecentRank: Number.isInteger(candidate.recentPlayRank) ? candidate.recentPlayRank : Number.POSITIVE_INFINITY,
    diversityRank: usedArtistIds.has(candidate.primaryArtistId) ? 0 : 1,
    durationCloseness:
      Number.isFinite(currentTrack?.durationMs) && Number.isFinite(candidate.durationMs)
        ? -Math.abs(candidate.durationMs - currentTrack.durationMs)
        : Number.NEGATIVE_INFINITY,
  }));

  scored.sort((a, b) => {
    if (b.affinityRank !== a.affinityRank) return b.affinityRank - a.affinityRank;
    if (b.notRecentRank !== a.notRecentRank) return b.notRecentRank - a.notRecentRank;
    if (b.diversityRank !== a.diversityRank) return b.diversityRank - a.diversityRank;
    if (b.durationCloseness !== a.durationCloseness) return b.durationCloseness - a.durationCloseness;
    if (a.token < b.token) return -1;
    if (a.token > b.token) return 1;
    return 0; // identical token is only possible for the exact same candidate
  });

  const winner = scored[0];
  const reason = decideSelectionReason(scored, winner);

  return { selected: winner.candidate, token: winner.token, reason, excluded, candidatePoolSize };
}

/**
 * Names the FIRST priority-order criterion that actually distinguished
 * the winner from at least one other eligible candidate -- i.e. the real
 * reason it won, not just its own affinity tier when every eligible
 * candidate shared that tier. Falls through the same priority order used
 * to sort: affinity -> recency -> artist diversity -> duration
 * continuity -> deterministic tie-break.
 */
function decideSelectionReason(scored, winner) {
  const others = scored.filter((s) => s !== winner);
  const affinityVaries = others.some((s) => s.affinityRank !== winner.affinityRank);
  if (affinityVaries) {
    if (winner.affinityRank === 2) return SELECTION_REASON.TOP_TRACK_AFFINITY;
    if (winner.affinityRank === 1) return SELECTION_REASON.RECENT_LISTENING_AFFINITY;
    return SELECTION_REASON.DETERMINISTIC_TIE_BREAK;
  }
  const baseAffinityReason = winner.affinityRank === 2 ? SELECTION_REASON.TOP_TRACK_AFFINITY : winner.affinityRank === 1 ? SELECTION_REASON.RECENT_LISTENING_AFFINITY : null;

  const recencyVaries = others.some((s) => s.notRecentRank !== winner.notRecentRank);
  if (recencyVaries) return baseAffinityReason || SELECTION_REASON.DETERMINISTIC_TIE_BREAK;

  const diversityVaries = others.some((s) => s.diversityRank !== winner.diversityRank);
  if (diversityVaries) return SELECTION_REASON.ARTIST_DIVERSITY;

  const durationVaries = others.some((s) => s.durationCloseness !== winner.durationCloseness);
  if (durationVaries) return SELECTION_REASON.DURATION_CONTINUITY;

  // Every ranking criterion tied across the whole eligible set -- the
  // only thing that actually decided it was the opaque-ID tie-break.
  return SELECTION_REASON.DETERMINISTIC_TIE_BREAK;
}
