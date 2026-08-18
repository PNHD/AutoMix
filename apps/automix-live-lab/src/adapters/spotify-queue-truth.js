/**
 * Pure Spotify real-queue-truthfulness helpers (P0-M6-R2 Phase B). No
 * fetch, no DOM -- turns a raw `GET /me/player/queue` response into a
 * sanitized, decision-ready shape (opaque tokens only, same convention
 * as spotify-autoplay.js), and answers "does a real queued successor
 * exist" without ever implying Next creates a recommendation.
 */
import { sanitizeTrackToken } from "./spotify-autoplay.js";

export const NO_QUEUED_NEXT_TRACK = "NO_QUEUED_NEXT_TRACK";
export const NEXT_TRACK_QUEUED = "NEXT_TRACK_QUEUED";

/**
 * Maps the raw `{ currently_playing, queue: [...] }` response shape
 * (Spotify's documented `GET /me/player/queue` response) into a sanitized
 * queue-truth snapshot. Tolerates a missing/malformed response (no
 * `queue` array, non-object items, items missing `id`) by treating those
 * entries as absent rather than throwing -- this endpoint's exact shape
 * has not yet been observed against a real account in this repository.
 */
export function deriveQueueTruth(rawQueueResponse) {
  const rawQueue = Array.isArray(rawQueueResponse?.queue) ? rawQueueResponse.queue : [];
  const tokens = rawQueue.map((t) => (t && typeof t === "object" && t.id ? sanitizeTrackToken(t.id) : null)).filter(Boolean);
  const currentlyPlaying = rawQueueResponse?.currently_playing;
  const currentToken = currentlyPlaying && typeof currentlyPlaying === "object" && currentlyPlaying.id ? sanitizeTrackToken(currentlyPlaying.id) : null;
  return {
    hasQueuedSuccessor: tokens.length > 0,
    queueSize: tokens.length,
    nextToken: tokens[0] || null,
    tokens,
    currentToken,
  };
}

export const EMPTY_QUEUE_TRUTH = Object.freeze(deriveQueueTruth(null));

/** Next must be disabled whenever there is no real queued successor -- this is the single source of truth the UI must consult before enabling the Next control. */
export function isNextControlEnabled(queueTruth) {
  return !!queueTruth?.hasQueuedSuccessor;
}

/** UI-facing state label for the Next control / queue panel. */
export function nextControlState(queueTruth) {
  return isNextControlEnabled(queueTruth) ? NEXT_TRACK_QUEUED : NO_QUEUED_NEXT_TRACK;
}

/**
 * Truthful description of what Play does at natural end with an empty
 * queue. Play may restart/resume the SAME seed when nothing is queued --
 * it must never be described as advancing to a new track, and the UI
 * must render this string, not a generic "Play" label, in that state.
 */
export function describePlayAtNaturalEnd(queueTruth) {
  if (isNextControlEnabled(queueTruth)) {
    return { action: "RESUME_OR_ADVANCE", message: "A real successor is queued -- Play/Spotify will advance to it." };
  }
  return {
    action: "RESTART_SAME_SEED",
    message: "No queued successor -- Play will restart/resume the same seed track, not advance to a new one.",
  };
}
