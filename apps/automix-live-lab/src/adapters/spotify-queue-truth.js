/**
 * Pure Spotify real-queue-truthfulness helpers (P0-M6-R2 Phase B, repair
 * pass Blocker 2). No fetch, no DOM -- turns a raw `GET /me/player/queue`
 * response into a sanitized, decision-ready shape (opaque tokens only,
 * same convention as spotify-autoplay.js).
 *
 * Blocker 2 repair: the original version collapsed EVERY failure mode
 * (a genuinely empty queue, and any API error -- 401/403/429/5xx/network)
 * into the same "empty queue" result. That is unsafe: it let an API
 * error be silently treated as `KNOWN_EMPTY`, which (after the Blocker 3
 * repair) would have made queue INJECTION possible during an outage the
 * caller never actually confirmed was safe. Queue truth is now an
 * explicit four-state value:
 *   - `KNOWN_EMPTY`        -- successfully polled, queue has zero items.
 *   - `KNOWN_NONEMPTY`     -- successfully polled, queue has >=1 item.
 *   - `UNKNOWN_NOT_POLLED` -- never successfully polled yet this session.
 *   - `UNKNOWN_API_ERROR`  -- the poll itself failed; the real state is
 *                             simply not known, NOT assumed empty.
 */
import { sanitizeTrackToken } from "./spotify-autoplay.js";
import { toPlannerCandidate } from "./spotify-api-requests.js";

// P0-M6-R3 Part B: label for the head-of-real-queue candidate, so
// downstream selection-source reporting can distinguish a track Spotify
// itself already placed as play-next from anything this app's own
// account-affinity planner picked.
export const PROVIDER_NEXT_UP_AFFINITY_SOURCE = "SPOTIFY_PROVIDER_NEXT_UP";

export const QueueTruthState = Object.freeze({
  KNOWN_EMPTY: "KNOWN_EMPTY",
  KNOWN_NONEMPTY: "KNOWN_NONEMPTY",
  UNKNOWN_NOT_POLLED: "UNKNOWN_NOT_POLLED",
  UNKNOWN_API_ERROR: "UNKNOWN_API_ERROR",
});

export const NO_QUEUED_NEXT_TRACK = "NO_QUEUED_NEXT_TRACK";
export const NEXT_TRACK_QUEUED = "NEXT_TRACK_QUEUED";
export const QUEUE_STATE_UNKNOWN_NOT_POLLED = "QUEUE_STATE_UNKNOWN_NOT_POLLED";
export const QUEUE_STATE_UNKNOWN_API_ERROR = "QUEUE_STATE_UNKNOWN_API_ERROR";

/**
 * Maps a SUCCESSFUL raw `{ currently_playing, queue: [...] }` response
 * (Spotify's documented `GET /me/player/queue` response) into a
 * `KNOWN_EMPTY`/`KNOWN_NONEMPTY` queue-truth snapshot. Only call this
 * when the API call itself succeeded -- see `unknownApiErrorQueueTruth`
 * for the failure path. Tolerates a missing/malformed response shape (no
 * `queue` array, non-object items, items missing `id`) by treating those
 * entries as absent rather than throwing.
 */
export function deriveQueueTruth(rawQueueResponse) {
  const rawQueue = Array.isArray(rawQueueResponse?.queue) ? rawQueueResponse.queue : [];
  const tokens = rawQueue.map((t) => (t && typeof t === "object" && t.id ? sanitizeTrackToken(t.id) : null)).filter(Boolean);
  const currentlyPlaying = rawQueueResponse?.currently_playing;
  const currentToken = currentlyPlaying && typeof currentlyPlaying === "object" && currentlyPlaying.id ? sanitizeTrackToken(currentlyPlaying.id) : null;
  // P0-M6-R3 Part B: the real queue's head item, in planner-candidate
  // shape (id/uri/primaryArtistId/durationMs/explicit/isPlayable), tagged
  // SPOTIFY_PROVIDER_NEXT_UP -- this is what lets the lookahead cycle
  // treat Spotify's own provider-generated Next Up as the PRIMARY
  // continuation signal instead of only this app's account-affinity
  // planner. `toPlannerCandidate` already returns null for a
  // malformed/URI-less raw item, so a head item lacking a real track uri
  // safely yields no provider head rather than a broken one.
  const rawHeadItem = rawQueue.find((t) => t && typeof t === "object" && t.id);
  const headCandidate = rawHeadItem ? toPlannerCandidate(rawHeadItem, PROVIDER_NEXT_UP_AFFINITY_SOURCE) : null;
  return {
    state: tokens.length > 0 ? QueueTruthState.KNOWN_NONEMPTY : QueueTruthState.KNOWN_EMPTY,
    hasQueuedSuccessor: tokens.length > 0,
    queueSize: tokens.length,
    nextToken: tokens[0] || null,
    tokens,
    currentToken,
    headCandidate,
    error: null,
  };
}

/** The initial value before any poll has ever succeeded or failed this session. */
export function unknownNotPolledQueueTruth() {
  return {
    state: QueueTruthState.UNKNOWN_NOT_POLLED,
    hasQueuedSuccessor: false,
    queueSize: 0,
    nextToken: null,
    tokens: [],
    currentToken: null,
    headCandidate: null,
    error: null,
  };
}

/**
 * Built when the `GET /me/player/queue` call itself failed. `error`
 * carries ONLY sanitized diagnostics -- endpoint path with no raw query
 * identifiers, HTTP status, bodyType, and a sanitized Spotify error
 * code/message when available. Never a token, raw URI, or device id.
 */
export function unknownApiErrorQueueTruth({ path, status, bodyType, sanitizedMessage } = {}) {
  return {
    state: QueueTruthState.UNKNOWN_API_ERROR,
    hasQueuedSuccessor: false,
    queueSize: 0,
    nextToken: null,
    tokens: [],
    currentToken: null,
    headCandidate: null,
    error: { path: path ?? null, status: status ?? null, bodyType: bodyType ?? null, sanitizedMessage: sanitizedMessage ?? null },
  };
}

export const UNKNOWN_QUEUE_TRUTH = Object.freeze(unknownNotPolledQueueTruth());

/** Next must be disabled for EMPTY (no real successor) OR either UNKNOWN state -- only a confirmed nonempty queue enables it. */
export function isNextControlEnabled(queueTruth) {
  return queueTruth?.state === QueueTruthState.KNOWN_NONEMPTY;
}

/**
 * Queue injection (Blocker 3, repaired per real owner finding): allowed
 * whenever the real queue state is KNOWN -- either genuinely empty OR
 * genuinely non-empty. A non-empty queue is NOT automatically an owner
 * conflict: Spotify's own client keeps a provider-generated "Next Up"
 * queue populated after any track starts playing, and the public API
 * offers no trustworthy way to distinguish that from anything else the
 * owner might have queued. `POST /me/player/queue` is documented to add
 * an item to be played NEXT, so injecting over a provider queue is safe
 * -- it does not clear or reorder whatever is already there, it only
 * asks Spotify to play our one chosen successor immediately after the
 * current track. Injection remains forbidden only when the real state is
 * genuinely unknown -- never polled yet, or the last poll errored.
 */
export function canInjectToQueue(queueTruth) {
  return queueTruth?.state === QueueTruthState.KNOWN_EMPTY || queueTruth?.state === QueueTruthState.KNOWN_NONEMPTY;
}

/** UI-facing state label for the Next control / queue panel -- distinguishes "confirmed empty" from "we don't actually know" so the owner sees the real blocker, not a false negative. */
export function nextControlState(queueTruth) {
  switch (queueTruth?.state) {
    case QueueTruthState.KNOWN_NONEMPTY:
      return NEXT_TRACK_QUEUED;
    case QueueTruthState.KNOWN_EMPTY:
      return NO_QUEUED_NEXT_TRACK;
    case QueueTruthState.UNKNOWN_API_ERROR:
      return QUEUE_STATE_UNKNOWN_API_ERROR;
    default:
      return QUEUE_STATE_UNKNOWN_NOT_POLLED;
  }
}

/**
 * Truthful description of what Play does at natural end. A confirmed
 * empty or unknown queue must never be described as if Play will
 * definitely advance -- and an unknown state must not be described as
 * definitely restarting either, since the real state is simply not known
 * yet (e.g. never polled, or the last poll errored).
 */
export function describePlayAtNaturalEnd(queueTruth) {
  if (queueTruth?.state === QueueTruthState.KNOWN_NONEMPTY) {
    return { action: "RESUME_OR_ADVANCE", message: "A real successor is queued -- Play/Spotify will advance to it." };
  }
  if (queueTruth?.state === QueueTruthState.KNOWN_EMPTY) {
    return {
      action: "RESTART_SAME_SEED",
      message: "No queued successor -- Play will restart/resume the same seed track, not advance to a new one.",
    };
  }
  const reason = queueTruth?.state === QueueTruthState.UNKNOWN_API_ERROR ? "the last queue check failed" : "the queue has not been checked yet";
  return {
    action: "UNKNOWN",
    message: `Real queue state is unknown (${reason}) -- whether Play restarts the seed or advances cannot be stated truthfully right now.`,
  };
}
