/**
 * One-track lookahead queue state machine (P0-M6-R2 Phase E). No fetch,
 * no DOM -- `queueTrackFn`/`verifyQueueFn`/`selectNextFn` are injected so
 * this is fully testable without a real Spotify session (see
 * tools/verify_spotify_lookahead_queue.mjs), the same pattern used by
 * verify_spotify_transfer_playback.mjs's monkey-patched `_api`.
 *
 * Required states, in order:
 *   SEED_ACTIVE -> NO_SUCCESSOR_QUEUED -> SELECTING_SUCCESSOR ->
 *   SUCCESSOR_QUEUE_REQUESTED -> SUCCESSOR_CONFIRMED ->
 *   SUCCESSOR_BECOMES_CURRENT -> SELECTING_NEXT_SUCCESSOR (which loops
 *   back into SELECTING_SUCCESSOR for the next lookahead cycle).
 */
export const QueueState = Object.freeze({
  SEED_ACTIVE: "SEED_ACTIVE",
  NO_SUCCESSOR_QUEUED: "NO_SUCCESSOR_QUEUED",
  SELECTING_SUCCESSOR: "SELECTING_SUCCESSOR",
  SUCCESSOR_QUEUE_REQUESTED: "SUCCESSOR_QUEUE_REQUESTED",
  SUCCESSOR_CONFIRMED: "SUCCESSOR_CONFIRMED",
  SUCCESSOR_BECOMES_CURRENT: "SUCCESSOR_BECOMES_CURRENT",
  SELECTING_NEXT_SUCCESSOR: "SELECTING_NEXT_SUCCESSOR",
});

// A fixed, bounded retry policy -- never unbounded, never exponential
// backoff complexity. One initial attempt plus this many retries.
export const MAX_QUEUE_REQUEST_ATTEMPTS = 3;

// States from which a new selection cycle may begin.
const SELECTABLE_STATES = new Set([QueueState.SEED_ACTIVE, QueueState.NO_SUCCESSOR_QUEUED, QueueState.SELECTING_NEXT_SUCCESSOR]);

export class LookaheadQueueController {
  /**
   * @param {(uri: string) => Promise<void>} queueTrackFn - POSTs the one chosen successor to the real Spotify queue. Must resolve on success (204 already normalized to a resolved promise by the Phase A repair) and reject on failure.
   * @param {() => Promise<string[]>} verifyQueueFn - returns sanitized tokens currently visible via GET /me/player/queue (or SDK next_tracks), most-imminent first.
   * @param {(ctx: object) => { selected: object|null, token: string|null, reason: string, excluded: object[], candidatePoolSize: number }} selectNextFn - the planner (spotify-planner.js's selectNextTrack), injected for testability.
   * @param {(state: string) => void} [onStateChange]
   * @param {number} [maxAttempts]
   */
  constructor({ queueTrackFn, verifyQueueFn, selectNextFn, onStateChange, maxAttempts = MAX_QUEUE_REQUEST_ATTEMPTS }) {
    this._queueTrackFn = queueTrackFn;
    this._verifyQueueFn = verifyQueueFn;
    this._selectNextFn = selectNextFn;
    this._onStateChange = onStateChange || (() => {});
    this._maxAttempts = maxAttempts;

    this._state = QueueState.SEED_ACTIVE;
    this._pendingToken = null;
    this._pendingSelection = null;
    this._confirmedToken = null;
    this._enqueuedTokens = new Set(); // every token ever successfully POSTed this session -- never re-enqueue one
    this._lastAdvancedToken = null; // duplicate player_state_changed guard
    this._refillCount = 0;
    this._consecutiveAutoTrackCount = 1; // the seed itself is automatic track #1
  }

  get state() {
    return this._state;
  }
  get refillCount() {
    return this._refillCount;
  }
  get consecutiveAutoTrackCount() {
    return this._consecutiveAutoTrackCount;
  }
  get pendingToken() {
    return this._pendingToken;
  }
  get confirmedToken() {
    return this._confirmedToken;
  }

  _setState(next) {
    this._state = next;
    this._onStateChange(next);
  }

  /**
   * Runs one full selection-and-enqueue cycle: SELECTING_SUCCESSOR ->
   * (queueTrackFn, bounded retry) -> SUCCESSOR_QUEUE_REQUESTED, or back
   * to NO_SUCCESSOR_QUEUED on no-eligible-candidate / exhausted retries.
   * Idempotency: refuses to start a second cycle while one is already in
   * flight (duplicate `player_state_changed` events must not trigger
   * concurrent/duplicate selection cycles), and refuses to re-enqueue a
   * token this session has already successfully queued once.
   */
  async selectAndQueueSuccessor(ctx) {
    if (!SELECTABLE_STATES.has(this._state)) {
      return { queued: false, skipped: true, reason: "ALREADY_IN_PROGRESS", state: this._state };
    }
    this._setState(QueueState.SELECTING_SUCCESSOR);

    const result = this._selectNextFn(ctx);
    if (!result || !result.selected || !result.token) {
      this._setState(QueueState.NO_SUCCESSOR_QUEUED);
      return { queued: false, reason: result?.reason || "NO_ELIGIBLE_CANDIDATES", selectionReason: result?.reason, candidatePoolSize: result?.candidatePoolSize ?? 0, excluded: result?.excluded ?? [] };
    }

    if (this._enqueuedTokens.has(result.token)) {
      // This exact successor was already queued once this session --
      // never enqueue a duplicate, even if the planner offered it again.
      this._setState(QueueState.NO_SUCCESSOR_QUEUED);
      return { queued: false, reason: "DUPLICATE_SKIPPED", token: result.token, selectionReason: result.reason };
    }

    this._pendingToken = result.token;
    this._pendingSelection = result;

    let attempts = 0;
    let lastError = null;
    while (attempts < this._maxAttempts) {
      attempts += 1;
      try {
        await this._queueTrackFn(result.selected.uri);
        this._enqueuedTokens.add(result.token);
        this._setState(QueueState.SUCCESSOR_QUEUE_REQUESTED);
        return {
          queued: true,
          token: result.token,
          selectionReason: result.reason,
          candidatePoolSize: result.candidatePoolSize,
          excluded: result.excluded,
          attempts,
        };
      } catch (e) {
        lastError = e;
      }
    }

    // Bounded retry exhausted -- fail back to NO_SUCCESSOR_QUEUED rather
    // than being stuck in SELECTING_SUCCESSOR forever. P0-M6-R2 repair,
    // Blocker 4: `errorStatus`/`errorRetryAfterSec` are surfaced (not
    // just `error.message`) so the caller can classify the failure
    // (spotify-queue-error-policy.js) and decide whether to blacklist
    // just this candidate, enter a cooldown, or stop entirely for a
    // terminal auth/scope error -- instead of the orchestration loop
    // blindly retrying the exact same failing candidate every tick.
    const failedToken = result.token;
    this._pendingToken = null;
    this._pendingSelection = null;
    this._setState(QueueState.NO_SUCCESSOR_QUEUED);
    return {
      queued: false,
      reason: "QUEUE_REQUEST_FAILED_AFTER_RETRIES",
      attempts,
      token: failedToken,
      error: lastError?.message,
      errorStatus: lastError?.status ?? null,
      errorRetryAfterSec: lastError?.retryAfterSec ?? null,
    };
  }

  /**
   * P0-M6-R2 repair pass 2, Blocker 1: PURE confirmation decision -- no
   * network I/O of its own. Takes an ALREADY-FETCHED array of sanitized
   * queue tokens (one fresh `GET /me/player/queue` snapshot, fetched
   * exactly once by the caller) and decides whether the pending
   * successor is visible in THAT SAME snapshot.
   *
   * This exists because the previous double-poll design had a real
   * race: `SpotifyPublicControlAdapter.runLookaheadCycle()` would poll
   * queue truth once to decide what to do, then (for the "awaiting
   * confirmation" branch) call the OLD async `confirmSuccessor()`, which
   * polled AGAIN internally. Between those two polls, Spotify could
   * legitimately advance the pending successor to `current` -- so poll
   * #2 would see an EMPTY queue (the item was consumed, not never
   * visible) and wrongly report `NOT_YET_VISIBLE_IN_QUEUE`, leaving the
   * controller stuck in `SUCCESSOR_QUEUE_REQUESTED` forever (it can
   * never reach `SUCCESSOR_CONFIRMED`, so the later
   * `player_state_changed` for that same track can't advance it either).
   * The fix is architectural: ONE orchestration decision must use ONE
   * fresh snapshot. `runLookaheadCycle()` now calls this method directly
   * with the tokens from its own single poll.
   */
  confirmSuccessorFromTokens(tokens) {
    if (this._state !== QueueState.SUCCESSOR_QUEUE_REQUESTED) {
      return { confirmed: false, reason: "NOT_AWAITING_CONFIRMATION", state: this._state };
    }
    if (Array.isArray(tokens) && tokens.includes(this._pendingToken)) {
      this._confirmedToken = this._pendingToken;
      this._setState(QueueState.SUCCESSOR_CONFIRMED);
      return { confirmed: true, token: this._confirmedToken };
    }
    return { confirmed: false, reason: "NOT_YET_VISIBLE_IN_QUEUE" };
  }

  /**
   * Convenience wrapper that performs its OWN `GET /me/player/queue`
   * fetch via `verifyQueueFn` before delegating to
   * `confirmSuccessorFromTokens`. Kept for standalone/manual use (e.g.
   * `SpotifyPublicControlAdapter.confirmLookaheadSuccessor()`) where a
   * fresh, dedicated poll is actually wanted -- the normal orchestration
   * path (`runLookaheadCycle()`) MUST NOT use this; it already has a
   * fresh snapshot from its own single poll and must call
   * `confirmSuccessorFromTokens` directly instead.
   */
  async confirmSuccessor() {
    if (this._state !== QueueState.SUCCESSOR_QUEUE_REQUESTED) {
      return { confirmed: false, reason: "NOT_AWAITING_CONFIRMATION", state: this._state };
    }
    const tokens = await this._verifyQueueFn();
    return this.confirmSuccessorFromTokens(tokens);
  }

  /**
   * Feed every `player_state_changed`-derived current-track token here.
   * Only a transition FROM the confirmed successor's token, while
   * SUCCESSOR_CONFIRMED, advances the machine
   * (SUCCESSOR_BECOMES_CURRENT -> SELECTING_NEXT_SUCCESSOR, refill count
   * +1, consecutive-auto-track count +1). Any other event, including an
   * exact repeat of the last-advanced token (duplicate SDK event), is a
   * no-op -- this is the idempotency guard required by the task.
   */
  onTrackAdvanced(currentToken) {
    if (currentToken === this._lastAdvancedToken) {
      return { advanced: false, reason: "DUPLICATE_EVENT_IGNORED" };
    }
    if (this._state === QueueState.SUCCESSOR_CONFIRMED && currentToken === this._confirmedToken) {
      this._lastAdvancedToken = currentToken;
      this._setState(QueueState.SUCCESSOR_BECOMES_CURRENT);
      this._refillCount += 1;
      this._consecutiveAutoTrackCount += 1;
      this._pendingToken = null;
      this._pendingSelection = null;
      this._confirmedToken = null;
      this._setState(QueueState.SELECTING_NEXT_SUCCESSOR);
      return { advanced: true, refillCount: this._refillCount, consecutiveAutoTrackCount: this._consecutiveAutoTrackCount };
    }
    return { advanced: false, reason: "NOT_EXPECTED_SUCCESSOR" };
  }

  /** True once at least one non-seed track has played automatically as a result of this controller's queueing (i.e. the loop is actually working end to end). */
  hasCompletedAtLeastOneAutoAdvance() {
    return this._refillCount > 0;
  }
}
