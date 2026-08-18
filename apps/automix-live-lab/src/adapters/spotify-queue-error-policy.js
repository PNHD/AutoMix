/**
 * Pure queue-write failure classification (P0-M6-R2 repair, Blocker 4).
 * No fetch, no DOM, no timers. `LookaheadQueueController` already bounds
 * retries WITHIN one selection cycle (`MAX_QUEUE_REQUEST_ATTEMPTS`); this
 * module decides what the ADAPTER should do ACROSS orchestration ticks
 * after that bounded cycle still failed, so a failing candidate/endpoint
 * can never be retried every ~2s forever.
 */
export const QueueBlockerType = Object.freeze({
  CANDIDATE_FAILED: "CANDIDATE_FAILED", // exclude only this one candidate, no cooldown -- try a different one next tick
  TERMINAL_AUTH: "TERMINAL_AUTH_BLOCKER", // 401/403 -- systemic, no automatic retry at all until reauth/scope fixed
  COOLDOWN: "COOLDOWN", // 429 (Retry-After honored) or transient 5xx/network -- bounded, timed cooldown
});

// Used when a transient/systemic failure carries no explicit Retry-After.
export const DEFAULT_TRANSIENT_COOLDOWN_MS = 30_000;
export const DEFAULT_RATE_LIMIT_COOLDOWN_MS = 30_000;

/**
 * Classifies a failed queue-write attempt by HTTP status (may be `null`
 * for a network-level failure with no response at all).
 *   - 401/403          -> TERMINAL_AUTH (systemic; caller must stop retrying automatically)
 *   - 429               -> COOLDOWN, honoring `retryAfterSec` when present
 *   - 404               -> CANDIDATE_FAILED (this specific track can't be queued; not a systemic problem)
 *   - anything else (5xx, null/network) -> COOLDOWN with the default bound
 */
export function classifyQueueFailure(status, retryAfterSec = null) {
  if (status === 401 || status === 403) {
    return { type: QueueBlockerType.TERMINAL_AUTH, status };
  }
  if (status === 429) {
    const cooldownMs = Number.isFinite(retryAfterSec) && retryAfterSec > 0 ? Math.round(retryAfterSec * 1000) : DEFAULT_RATE_LIMIT_COOLDOWN_MS;
    return { type: QueueBlockerType.COOLDOWN, status, cooldownMs };
  }
  if (status === 404) {
    return { type: QueueBlockerType.CANDIDATE_FAILED, status };
  }
  return { type: QueueBlockerType.COOLDOWN, status: status ?? null, cooldownMs: DEFAULT_TRANSIENT_COOLDOWN_MS };
}

/** True while a previously-set blocker is still in effect (given the current time) and must keep suppressing new queue-write attempts. */
export function isBlockerActive(blocker, nowMs) {
  if (!blocker) return false;
  if (blocker.type === QueueBlockerType.TERMINAL_AUTH) return true; // never auto-clears
  if (blocker.type === QueueBlockerType.COOLDOWN) return nowMs < blocker.untilMs;
  return false;
}
