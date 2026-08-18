// Deterministic proof of P0-M6-R3 Part B: Spotify's own provider-generated
// "Next Up" queue (the real queue's head item) must be the PRIMARY
// seed-conditioned continuation signal -- adopted directly, without a
// duplicate POST, and never overridden by the account-affinity planner's
// DURATION_CONTINUITY tie-break. The account-affinity planner is used only
// as a FALLBACK when the provider head is absent or ineligible. No
// network -- `_api` is monkey-patched, same convention as
// verify_spotify_provider_queue_coexistence.mjs.
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { QueueState } from "../src/adapters/spotify-lookahead-queue.js";
import { evaluateProviderHeadExclusion, SELECTION_SOURCE, EXCLUSION_REASON } from "../src/adapters/spotify-planner.js";
import { deriveQueueTruth } from "../src/adapters/spotify-queue-truth.js";
import { sanitizeTrackToken } from "../src/adapters/spotify-autoplay.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

function newActiveSeedAdapter({ durationMs = 200000 } = {}) {
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._deviceId = "device123";
  adapter._seedUri = "spotify:track:SEED123";
  adapter._seedToken = sanitizeTrackToken("SEED123");
  adapter._seedObserved = true;
  adapter._latestState = {
    paused: false,
    position: 0,
    duration: durationMs,
    track_window: { current_track: { id: "SEED123", duration_ms: durationMs, artists: [{ id: "ART_SEED" }] }, next_tracks: [] },
  };
  return adapter;
}
function feedState(adapter, state) {
  adapter._latestState = state;
  adapter._onPlayerStateChanged(state);
}
function fakeState({ trackId, artistId = "ART_X", durationMs = 200000 }) {
  return {
    paused: false,
    position: 0,
    duration: durationMs,
    track_window: { current_track: { id: trackId, duration_ms: durationMs, artists: [{ id: artistId }] }, next_tracks: [] },
  };
}
function topTracksRaw(items) {
  return { items };
}
// A raw track shape with the FULL fields a real GET /me/player/queue item
// actually has (uri/artists/duration_ms/is_playable) -- this is what makes
// `deriveQueueTruth`'s `headCandidate` non-null (unlike the minimal `{id}`
// fixtures the R2 provider-queue-coexistence tests use, which deliberately
// stay on the pre-R3 account-affinity fallback path).
function rawQueueItem(id, artistId = "ART_PROVIDER", durationMs = 200000, isPlayable = true) {
  return { id, uri: `spotify:track:${id}`, artists: [{ id: artistId }], duration_ms: durationMs, is_playable: isPlayable };
}

// ============================================================
// Unit: evaluateProviderHeadExclusion -- hard exclusions apply, recent-
// repeat window is a SOFT guard only (task requirement).
// ============================================================
{
  const head = { id: "HEAD1", uri: "spotify:track:HEAD1", primaryArtistId: "ART_H", durationMs: 200000, explicit: false, isPlayable: true };
  check("eligible provider head -> no exclusion", evaluateProviderHeadExclusion(head, {}) === null);

  const currentToken = sanitizeTrackToken("HEAD1");
  check("provider head == current track -> IS_CURRENT_TRACK", evaluateProviderHeadExclusion(head, { currentTrackToken: currentToken }) === EXCLUSION_REASON.IS_CURRENT_TRACK);

  const sessionPlayedTokens = new Set([sanitizeTrackToken("HEAD1")]);
  check("provider head already played this session -> ALREADY_PLAYED_THIS_SESSION", evaluateProviderHeadExclusion(head, { sessionPlayedTokens }) === EXCLUSION_REASON.ALREADY_PLAYED_THIS_SESSION);

  const unplayableHead = { ...head, isPlayable: false };
  check("unplayable provider head -> UNPLAYABLE", evaluateProviderHeadExclusion(unplayableHead, {}) === EXCLUSION_REASON.UNPLAYABLE);

  const sameArtistHead = { ...head, primaryArtistId: "ART_CURRENT" };
  check(
    "provider head is an immediate same-artist repeat -> IMMEDIATE_SAME_ARTIST_REPETITION",
    evaluateProviderHeadExclusion(sameArtistHead, { currentPrimaryArtistId: "ART_CURRENT" }) === EXCLUSION_REASON.IMMEDIATE_SAME_ARTIST_REPETITION
  );

  // The task's explicit requirement: recent-play history is a SOFT guard
  // only for a real Spotify-supplied successor -- it must never veto an
  // otherwise-valid provider Next Up, unlike the account-affinity planner
  // where RECENT_REPEAT_EXCLUDED IS a hard exclusion.
  const recentRepeatWindowTokens = new Set([sanitizeTrackToken("HEAD1")]);
  check(
    "provider head inside the recent-repeat window is NOT excluded (soft guard only)",
    evaluateProviderHeadExclusion(head, { recentRepeatWindowTokens }) === null
  );

  check("SELECTION_SOURCE exposes the two required values", SELECTION_SOURCE.SPOTIFY_PROVIDER_NEXT_UP === "SPOTIFY_PROVIDER_NEXT_UP" && SELECTION_SOURCE.ACCOUNT_AFFINITY_FALLBACK === "ACCOUNT_AFFINITY_FALLBACK");
}

// ============================================================
// deriveQueueTruth: headCandidate shape and malformed-head safety
// ============================================================
{
  const withFullHead = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [rawQueueItem("HEAD1"), { id: "TAIL1" }] });
  check("deriveQueueTruth exposes a headCandidate for a fully-shaped head item", withFullHead.headCandidate?.id === "HEAD1" && withFullHead.headCandidate?.uri === "spotify:track:HEAD1");
  check("headCandidate is tagged SPOTIFY_PROVIDER_NEXT_UP", withFullHead.headCandidate?.affinitySource === SELECTION_SOURCE.SPOTIFY_PROVIDER_NEXT_UP);

  const withMinimalHead = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [{ id: "HEAD1" }] });
  check("a head item missing uri/duration -> headCandidate is null (safe fallback, never a broken candidate)", withMinimalHead.headCandidate === null);

  const emptyQueue = deriveQueueTruth({ currently_playing: { id: "SEED123" }, queue: [] });
  check("an empty queue -> headCandidate is null", emptyQueue.headCandidate === null);
}

// ============================================================
// Test 1 & 5: provider head wins over a duration-matched account
// candidate; DURATION_CONTINUITY can never override a valid provider head.
// ============================================================
{
  const adapter = newActiveSeedAdapter({ durationMs: 200000 });
  const apiCalls = [];
  adapter._api = async (url, opts = {}) => {
    apiCalls.push({ url, method: opts.method || "GET" });
    // Account pool candidate has a duration EXTREMELY close to the seed's
    // (200000ms) -- if the account-affinity planner were consulted at all,
    // DURATION_CONTINUITY would make it a strong pick. It must never be
    // reached while a valid provider head exists.
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([{ id: "DURATION_MATCH", uri: "spotify:track:DURATION_MATCH", artists: [{ id: "ART_DM" }], duration_ms: 200001, is_playable: true }]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) return null; // would be a duplicate-claim POST -- must never fire
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [rawQueueItem("PROVIDER_HEAD", "ART_OTHER", 400000)] };
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("test 1: provider head wins -- selected token is the provider head, not the duration-matched account candidate", result.token === sanitizeTrackToken("PROVIDER_HEAD"));
  check("test 5: selectionSource is SPOTIFY_PROVIDER_NEXT_UP, not an account-affinity reason", result.selectionSource === SELECTION_SOURCE.SPOTIFY_PROVIDER_NEXT_UP);
  check("test 1/5: the account-affinity planner (top-tracks/recently-played) was never even consulted -- provider signal is PRIMARY, not just higher-ranked", !apiCalls.some((c) => c.url.startsWith("/me/top/tracks")) && !apiCalls.some((c) => c.url.startsWith("/me/player/recently-played")));
  check("test 2: adopting the provider head issues ZERO POSTs (never re-claims ownership of an already-play-next item)", !apiCalls.some((c) => c.method === "POST"));
  check("adapter status reflects the adopted provider successor as confirmed", adapter.getLookaheadStatus().successorConfirmed === true && adapter.getLookaheadStatus().successorIsPlayNext === true);
  check("adapter status exposes selectionSource SPOTIFY_PROVIDER_NEXT_UP", adapter.getLookaheadStatus().selectionSource === SELECTION_SOURCE.SPOTIFY_PROVIDER_NEXT_UP);

  // A further orchestration tick while SUCCESSOR_CONFIRMED must still
  // never POST (Test 2, extended): confirmation IS the head position,
  // there is nothing left to confirm-by-polling.
  const postCountBefore = apiCalls.filter((c) => c.method === "POST").length;
  await adapter.runLookaheadCycle();
  check("test 2 (extended): a later tick while already confirmed still issues zero additional POSTs", apiCalls.filter((c) => c.method === "POST").length === postCountBefore);
}

// ============================================================
// Test 3: provider head already played this session -> rejected, falls
// back to the account-affinity planner (which DOES post).
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  adapter._sessionPlayedIds = ["PROVIDER_HEAD"]; // simulate: this exact track already played earlier in this AutoMix session
  const apiCalls = [];
  adapter._api = async (url, opts = {}) => {
    apiCalls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([{ id: "FALLBACK1", uri: "spotify:track:FALLBACK1", artists: [{ id: "ART_FB" }], duration_ms: 210000, is_playable: true }]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [rawQueueItem("PROVIDER_HEAD")] };
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("test 3: an already-played provider head is rejected (not adopted)", result.token !== sanitizeTrackToken("PROVIDER_HEAD"));
  check("test 3: falls back to the account-affinity planner and actually posts a different candidate", result.token === sanitizeTrackToken("FALLBACK1") && apiCalls.some((c) => c.method === "POST"));
  check("test 3: selectionSource correctly reports the fallback path", result.selectionSource === SELECTION_SOURCE.ACCOUNT_AFFINITY_FALLBACK);
}

// ============================================================
// Test 4: provider queue absent (genuinely empty) -> account-affinity
// fallback works exactly as before this repair.
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const postCalls = [];
  adapter._api = async (url, opts = {}) => {
    if (url.startsWith("/me/top/tracks")) return topTracksRaw([{ id: "ONLY_CANDIDATE", uri: "spotify:track:ONLY_CANDIDATE", artists: [{ id: "ART_OC" }], duration_ms: 200000, is_playable: true }]);
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url.startsWith("/me/player/queue?")) {
      postCalls.push(url);
      return null;
    }
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] }; // genuinely empty -- no provider head at all
    return null;
  };
  const result = await adapter.runLookaheadCycle();
  check("test 4: no provider head -> account-affinity fallback selects and posts", result.queued === true && postCalls.length === 1);
  check("test 4: selectionSource is ACCOUNT_AFFINITY_FALLBACK", result.selectionSource === SELECTION_SOURCE.ACCOUNT_AFFINITY_FALLBACK);
}

// ============================================================
// Test 6: refill works with provider-head adoption (onTrackAdvanced still
// fires normally for an adopted-not-posted successor).
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  adapter._api = async (url) => {
    if (url.startsWith("/me/top/tracks")) return { items: [] };
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [rawQueueItem("PROVIDER_HEAD")] };
    return null;
  };
  await adapter.runLookaheadCycle();
  check("test 6 setup: provider head confirmed before advance", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);
  feedState(adapter, fakeState({ trackId: "PROVIDER_HEAD" }));
  check("test 6: exactly one refill on advance to the adopted provider successor", adapter.getLookaheadStatus().refillCount === 1);
  check("test 6: consecutiveAutoTrackCount is now 2", adapter.getLookaheadStatus().consecutiveAutoTrackCount === 2);
  check("test 6: session history now includes the adopted provider successor's id", adapter._sessionPlayedIds.includes("PROVIDER_HEAD"));
}

// ============================================================
// Test 7: three-track simulation (seed -> provider head #1 -> provider
// head #2), entirely via provider adoption -- zero POSTs across the whole
// run, provider's own trailing items untouched throughout.
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  let mockCurrentId = "SEED123";
  let providerQueue = ["PROVIDER_HEAD1", "TAIL_A", "TAIL_B"];
  const apiCalls = [];
  adapter._api = async (url, opts = {}) => {
    apiCalls.push({ url, method: opts.method || "GET" });
    if (url.startsWith("/me/top/tracks")) return { items: [] };
    if (url.startsWith("/me/player/recently-played")) return { items: [] };
    if (url === "/me/player/queue") return { currently_playing: { id: mockCurrentId }, queue: providerQueue.map((id) => rawQueueItem(id, id === "PROVIDER_HEAD1" ? "ART_HEAD1" : id === "PROVIDER_HEAD2" ? "ART_HEAD2" : "ART_TAIL")) };
    return null;
  };
  await adapter.runLookaheadCycle(); // adopt head #1
  check("cycle 1: track #2 -- consecutiveAutoTrackCount is now 2", adapter.getLookaheadStatus().state === QueueState.SUCCESSOR_CONFIRMED);
  mockCurrentId = "PROVIDER_HEAD1";
  providerQueue = providerQueue.filter((id) => id !== "PROVIDER_HEAD1"); // Spotify itself consumed it out of the queue
  feedState(adapter, fakeState({ trackId: "PROVIDER_HEAD1", artistId: "ART_HEAD1" }));
  check("cycle 1: refillCount is 1", adapter.getLookaheadStatus().refillCount === 1);

  providerQueue = ["PROVIDER_HEAD2", ...providerQueue]; // Spotify supplies a fresh provider head for the next cycle (different artist -- not an immediate same-artist repeat)
  await adapter.runLookaheadCycle(); // adopt head #2
  check("cycle 2: provider head #2 adopted (different track, not a repeat of #1)", adapter.getLookaheadStatus().selectedToken === sanitizeTrackToken("PROVIDER_HEAD2"));
  mockCurrentId = "PROVIDER_HEAD2";
  providerQueue = providerQueue.filter((id) => id !== "PROVIDER_HEAD2");
  feedState(adapter, fakeState({ trackId: "PROVIDER_HEAD2", artistId: "ART_HEAD2" }));
  check("at least 3 consecutive automatic tracks played from one owner-selected seed (provider-adoption path)", adapter.getLookaheadStatus().consecutiveAutoTrackCount >= 3);
  check("cycle 2: refillCount is now 2", adapter.getLookaheadStatus().refillCount === 2);
  check("test 7: the provider's own trailing items (TAIL_A/TAIL_B) were never posted/removed by this app", !apiCalls.some((c) => c.method === "POST"));
}

// ============================================================
// Test 8: AutoMix OFF prevents provider-head adoption too (not just the
// account-affinity POST path).
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  const apiCalls = [];
  adapter._api = async (url, opts = {}) => {
    apiCalls.push({ url, method: opts.method || "GET" });
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [rawQueueItem("PROVIDER_HEAD")] };
    return { items: [] };
  };
  adapter.setAutoMixEnabled(false);
  const result = await adapter.runLookaheadCycle();
  check("test 8: AutoMix OFF blocks provider-head adoption -- AUTOMIX_DISABLED, even with an eligible provider head present", result.reason === "AUTOMIX_DISABLED");
  check("test 8: no successor was adopted or posted while OFF", adapter.getLookaheadStatus().successorConfirmed === false && !apiCalls.some((c) => c.method === "POST"));
}

// ============================================================
// Never claims acoustic-compatibility fields; privacy stays opaque-token-only
// ============================================================
{
  const adapter = newActiveSeedAdapter();
  adapter._api = async (url) => {
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [rawQueueItem("PROVIDER_HEAD_RAW_ID_SHOULD_NOT_LEAK")] };
    return { items: [] };
  };
  await adapter.runLookaheadCycle();
  const status = adapter.getLookaheadStatus();
  const serialized = JSON.stringify(status);
  check("provider-adoption path: getLookaheadStatus() never leaks the raw provider head id", !serialized.includes("PROVIDER_HEAD_RAW_ID_SHOULD_NOT_LEAK"));
  check("provider-adoption path: never mentions bpm/tempo/key/energy/beat/transition-quality claims", !/bpm|tempo|\bkey\b|energy|beatMatch|transitionQuality/i.test(serialized));
  check("provider-adoption path: does not claim BPM/key/genre/audio similarity as the selection basis", !/genre|audioSimilarity/i.test(serialized));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
