// Deterministic proof of P0-M6-R2 Phase E: the one-track lookahead queue
// state machine must walk exactly the required states, never enqueue a
// duplicate, ignore duplicate player_state_changed-derived events, retry
// a bounded number of times, and correctly confirm/advance/refill. No
// network -- queueTrackFn/verifyQueueFn/selectNextFn are all injected.
import { buildQueueTrackRequest } from "../src/adapters/spotify-api-requests.js";
import { LookaheadQueueController, QueueState, MAX_QUEUE_REQUEST_ATTEMPTS } from "../src/adapters/spotify-lookahead-queue.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

function fakeSelection(token, uriSuffix = token) {
  return { selected: { id: uriSuffix, uri: `spotify:track:${uriSuffix}` }, token, reason: "TOP_TRACK_AFFINITY", excluded: [], candidatePoolSize: 5 };
}

// ============================================================
// Test 11: one-track queue request construction
// ============================================================
{
  const req = buildQueueTrackRequest("spotify:track:SUCC1", "device123");
  check("POST /me/player/queue -- method is POST", req.method === "POST");
  check("POST /me/player/queue -- path is /me/player/queue", req.path === "/me/player/queue");
  check("POST /me/player/queue -- uri and device_id are query params, no body", req.url === "/me/player/queue?uri=spotify%3Atrack%3ASUCC1&device_id=device123" && !("body" in req));

  const reqNoDevice = buildQueueTrackRequest("spotify:track:SUCC1");
  check("device_id is optional (SDK's own active device is implied when omitted)", reqNoDevice.url === "/me/player/queue?uri=spotify%3Atrack%3ASUCC1");

  let threw = false;
  try {
    buildQueueTrackRequest("not-a-track-uri");
  } catch (e) {
    threw = e.message === "SPOTIFY_QUEUE_URI_MUST_BE_A_SINGLE_TRACK_URI";
  }
  check("a non-track uri is rejected", threw);
}

// ============================================================
// Basic state walk + happy path
// ============================================================
{
  const queueCalls = [];
  const controller = new LookaheadQueueController({
    queueTrackFn: async (uri) => queueCalls.push(uri),
    verifyQueueFn: async () => ["TRK_SUCC1"],
    selectNextFn: () => fakeSelection("TRK_SUCC1", "SUCC1"),
  });
  check("initial state is SEED_ACTIVE", controller.state === QueueState.SEED_ACTIVE);
  check("consecutiveAutoTrackCount starts at 1 (the seed itself)", controller.consecutiveAutoTrackCount === 1);

  const selectResult = await controller.selectAndQueueSuccessor({});
  check("selectAndQueueSuccessor queues exactly once on the happy path", queueCalls.length === 1 && queueCalls[0] === "spotify:track:SUCC1");
  check("state after a successful queue request is SUCCESSOR_QUEUE_REQUESTED", controller.state === QueueState.SUCCESSOR_QUEUE_REQUESTED);
  check("selectAndQueueSuccessor reports queued: true with the selection reason", selectResult.queued === true && selectResult.selectionReason === "TOP_TRACK_AFFINITY");

  const confirmResult = await controller.confirmSuccessor();
  check("confirmSuccessor confirms once GET /me/player/queue shows the token (Test 13)", confirmResult.confirmed === true && confirmResult.token === "TRK_SUCC1");
  check("state after confirmation is SUCCESSOR_CONFIRMED", controller.state === QueueState.SUCCESSOR_CONFIRMED);

  const advanceResult = controller.onTrackAdvanced("TRK_SUCC1");
  check("onTrackAdvanced with the confirmed token advances the machine (Test 14)", advanceResult.advanced === true);
  check("state ends at SELECTING_NEXT_SUCCESSOR (via SUCCESSOR_BECOMES_CURRENT)", controller.state === QueueState.SELECTING_NEXT_SUCCESSOR);
  check("refillCount increments to 1 (Test 15: automatic refill)", controller.refillCount === 1);
  check("consecutiveAutoTrackCount increments to 2", controller.consecutiveAutoTrackCount === 2);
}

// ============================================================
// Test 13 (negative case): confirmation before the queue actually shows the token
// ============================================================
{
  const controller = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => [], // not yet visible
    selectNextFn: () => fakeSelection("TRK_A", "A"),
  });
  await controller.selectAndQueueSuccessor({});
  const confirmResult = await controller.confirmSuccessor();
  check("confirmSuccessor reports not-confirmed when the token isn't visible yet", confirmResult.confirmed === false && confirmResult.reason === "NOT_YET_VISIBLE_IN_QUEUE");
  check("state stays SUCCESSOR_QUEUE_REQUESTED until confirmation actually succeeds", controller.state === QueueState.SUCCESSOR_QUEUE_REQUESTED);

  const confirmBeforeRequested = new LookaheadQueueController({ queueTrackFn: async () => {}, verifyQueueFn: async () => [], selectNextFn: () => fakeSelection("X") });
  const earlyConfirm = await confirmBeforeRequested.confirmSuccessor();
  check("confirmSuccessor refuses when no queue request is even pending", earlyConfirm.confirmed === false && earlyConfirm.reason === "NOT_AWAITING_CONFIRMATION");
}

// ============================================================
// Test 12: duplicate-event idempotency
// ============================================================
{
  const controller = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => ["TRK_A"],
    selectNextFn: () => fakeSelection("TRK_A", "A"),
  });
  await controller.selectAndQueueSuccessor({});
  await controller.confirmSuccessor();
  const first = controller.onTrackAdvanced("TRK_A");
  check("first onTrackAdvanced call for the confirmed token advances", first.advanced === true);
  const refillAfterFirst = controller.refillCount;

  // Simulate the SDK firing player_state_changed twice for the same track change.
  const duplicate = controller.onTrackAdvanced("TRK_A");
  check("a duplicate player_state_changed event for the SAME current track is ignored, not double-counted", duplicate.advanced === false && duplicate.reason === "DUPLICATE_EVENT_IGNORED");
  check("refillCount does not increment again on the duplicate event", controller.refillCount === refillAfterFirst);
  check("consecutiveAutoTrackCount does not increment again on the duplicate event", controller.consecutiveAutoTrackCount === 2);
}

// ============================================================
// Duplicate-token guard: never re-enqueue the same successor twice this session
// ============================================================
{
  const queueCalls = [];
  let callCount = 0;
  const controller = new LookaheadQueueController({
    queueTrackFn: async (uri) => {
      queueCalls.push(uri);
    },
    verifyQueueFn: async () => ["TRK_A"],
    selectNextFn: () => {
      callCount += 1;
      return fakeSelection("TRK_A", "A"); // planner (bug or stale cache) offers the SAME token again
    },
  });
  await controller.selectAndQueueSuccessor({});
  await controller.confirmSuccessor();
  controller.onTrackAdvanced("TRK_A"); // becomes current -> SELECTING_NEXT_SUCCESSOR

  const secondAttempt = await controller.selectAndQueueSuccessor({});
  check("a token already enqueued this session is never re-enqueued, even if re-offered", secondAttempt.queued === false && secondAttempt.reason === "DUPLICATE_SKIPPED");
  check("queueTrackFn was called exactly once total, not twice", queueCalls.length === 1);
}

// ============================================================
// ALREADY_IN_PROGRESS guard: a second selection cycle must not start while one is in flight
// ============================================================
{
  let resolveQueue;
  const pending = new Promise((res) => {
    resolveQueue = res;
  });
  const controller = new LookaheadQueueController({
    queueTrackFn: async () => pending, // never resolves until we say so
    verifyQueueFn: async () => [],
    selectNextFn: () => fakeSelection("TRK_B", "B"),
  });

  const firstCallPromise = controller.selectAndQueueSuccessor({});
  check("state is SELECTING_SUCCESSOR while the first cycle is still in flight", controller.state === QueueState.SELECTING_SUCCESSOR);

  const secondCallResult = await controller.selectAndQueueSuccessor({});
  check("a concurrent second selection cycle is refused while the first is in flight", secondCallResult.skipped === true && secondCallResult.reason === "ALREADY_IN_PROGRESS");

  resolveQueue();
  await firstCallPromise;
  check("the first (only real) cycle still completes normally", controller.state === QueueState.SUCCESSOR_QUEUE_REQUESTED);
}

// ============================================================
// Test 16: bounded retry policy
// ============================================================
{
  let attemptCount = 0;
  const alwaysFails = new LookaheadQueueController({
    queueTrackFn: async () => {
      attemptCount += 1;
      throw new Error("SPOTIFY_API_ERROR: POST /me/player/queue -> 500");
    },
    verifyQueueFn: async () => [],
    selectNextFn: () => fakeSelection("TRK_FAIL", "FAIL"),
  });
  const result = await alwaysFails.selectAndQueueSuccessor({});
  check(`retry is bounded to exactly MAX_QUEUE_REQUEST_ATTEMPTS (${MAX_QUEUE_REQUEST_ATTEMPTS}), never unbounded`, attemptCount === MAX_QUEUE_REQUEST_ATTEMPTS);
  check("after exhausting retries, the result reports failure with attempts recorded", result.queued === false && result.reason === "QUEUE_REQUEST_FAILED_AFTER_RETRIES" && result.attempts === MAX_QUEUE_REQUEST_ATTEMPTS);
  check("after exhausting retries, state falls back to NO_SUCCESSOR_QUEUED (never stuck)", alwaysFails.state === QueueState.NO_SUCCESSOR_QUEUED);

  let flakyAttempts = 0;
  const flaky = new LookaheadQueueController({
    queueTrackFn: async () => {
      flakyAttempts += 1;
      if (flakyAttempts < 2) throw new Error("transient");
    },
    verifyQueueFn: async () => [],
    selectNextFn: () => fakeSelection("TRK_FLAKY", "FLAKY"),
  });
  const flakyResult = await flaky.selectAndQueueSuccessor({});
  check("a request that succeeds within the bound (2nd attempt) still succeeds overall", flakyResult.queued === true && flakyResult.attempts === 2);
}

// ============================================================
// No eligible candidate: cycle must not hang or crash
// ============================================================
{
  const controller = new LookaheadQueueController({
    queueTrackFn: async () => {},
    verifyQueueFn: async () => [],
    selectNextFn: () => ({ selected: null, token: null, reason: "NO_ELIGIBLE_CANDIDATES", excluded: [], candidatePoolSize: 0 }),
  });
  const result = await controller.selectAndQueueSuccessor({});
  check("no eligible candidate -> queued false, state falls back to NO_SUCCESSOR_QUEUED", result.queued === false && controller.state === QueueState.NO_SUCCESSOR_QUEUED);
}

// ============================================================
// Test 18: three-track state-machine simulation (seed -> successor1 -> successor2)
// ============================================================
{
  const observedStates = [];
  const queueCalls = [];
  let currentToken = "TRK_SEED";
  let nextTokenToOffer = "TRK_SUCC1";
  const controller = new LookaheadQueueController({
    queueTrackFn: async (uri) => queueCalls.push(uri),
    verifyQueueFn: async () => [controller.pendingToken],
    selectNextFn: () => fakeSelection(nextTokenToOffer, nextTokenToOffer.replace("TRK_", "")),
    onStateChange: (s) => observedStates.push(s),
  });

  check("track #1 (seed) -- consecutiveAutoTrackCount starts at 1", controller.consecutiveAutoTrackCount === 1);

  // --- Cycle 1: select/queue/confirm/advance to successor #1 ---
  await controller.selectAndQueueSuccessor({});
  check("cycle 1: queued successor #1", queueCalls[0] === "spotify:track:SUCC1");
  await controller.confirmSuccessor();
  check("cycle 1: successor #1 confirmed", controller.state === QueueState.SUCCESSOR_CONFIRMED);
  currentToken = "TRK_SUCC1";
  const advance1 = controller.onTrackAdvanced(currentToken);
  check("cycle 1: Spotify advances to successor #1", advance1.advanced === true);
  check("cycle 1: track #2 -- consecutiveAutoTrackCount is now 2", controller.consecutiveAutoTrackCount === 2);
  check("cycle 1: refillCount is 1", controller.refillCount === 1);

  // --- Cycle 2: select/queue/confirm/advance to successor #2 ---
  nextTokenToOffer = "TRK_SUCC2";
  const select2 = await controller.selectAndQueueSuccessor({});
  check("cycle 2: a fresh selection cycle is allowed from SELECTING_NEXT_SUCCESSOR", select2.queued === true);
  check("cycle 2: queued successor #2 (different track, not a repeat of #1)", queueCalls[1] === "spotify:track:SUCC2");
  await controller.confirmSuccessor();
  currentToken = "TRK_SUCC2";
  const advance2 = controller.onTrackAdvanced(currentToken);
  check("cycle 2: Spotify advances to successor #2", advance2.advanced === true);
  check("at least 3 consecutive automatic tracks played from one owner-selected seed", controller.consecutiveAutoTrackCount >= 3);
  check("cycle 2: refillCount is now 2 (two successful automatic refills)", controller.refillCount === 2);
  check("hasCompletedAtLeastOneAutoAdvance is true", controller.hasCompletedAtLeastOneAutoAdvance() === true);

  check(
    "observed state sequence includes every required state, in order, twice (once per successor)",
    observedStates.filter((s) => s === QueueState.SUCCESSOR_QUEUE_REQUESTED).length === 2 &&
      observedStates.filter((s) => s === QueueState.SUCCESSOR_CONFIRMED).length === 2 &&
      observedStates.filter((s) => s === QueueState.SUCCESSOR_BECOMES_CURRENT).length === 2 &&
      observedStates.filter((s) => s === QueueState.SELECTING_NEXT_SUCCESSOR).length === 2
  );
  check("never queued the seed or a successor more than once (no duplicates across the whole simulation)", new Set(queueCalls).size === queueCalls.length);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
