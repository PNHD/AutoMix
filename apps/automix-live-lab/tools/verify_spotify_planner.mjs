// Deterministic proof of P0-M6-R2 Phase D: the next-track planner must
// apply every hard exclusion, rank deterministically (never randomly),
// and never claim BPM/key/beat/energy/transition-quality compatibility.
// No network.
import { evaluateHardExclusion, selectNextTrack, EXCLUSION_REASON, SELECTION_REASON } from "../src/adapters/spotify-planner.js";
import { sanitizeTrackToken } from "../src/adapters/spotify-autoplay.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

function track(id, { artist = "ART_X", durationMs = 200000, explicit = false, isPlayable = true, affinitySource = "TOP_TRACK_AFFINITY", recentPlayRank } = {}) {
  return { id, uri: `spotify:track:${id}`, primaryArtistId: artist, durationMs, explicit, isPlayable, affinitySource, recentPlayRank };
}

const currentTrack = { id: "CURRENT", primaryArtistId: "ART_CURRENT", durationMs: 200000 };

// ============================================================
// Test 7: candidate hard exclusions (each reason individually)
// ============================================================
{
  check("malformed item (not an object) -> MALFORMED_ITEM", evaluateHardExclusion(null) === EXCLUSION_REASON.MALFORMED_ITEM);
  check("malformed item (no id) -> MALFORMED_ITEM", evaluateHardExclusion({ uri: "spotify:track:X" }) === EXCLUSION_REASON.MALFORMED_ITEM);
  check("missing/malformed uri -> MISSING_URI", evaluateHardExclusion({ id: "X", uri: "not-a-track-uri" }) === EXCLUSION_REASON.MISSING_URI);
  check(
    "unavailable/unplayable item -> UNPLAYABLE",
    evaluateHardExclusion(track("X", { isPlayable: false }), {}) === EXCLUSION_REASON.UNPLAYABLE
  );

  const currentToken = sanitizeTrackToken("CURRENT");
  check(
    "is the current seed/current track -> IS_CURRENT_TRACK",
    evaluateHardExclusion(track("CURRENT"), { currentTrackToken: currentToken }) === EXCLUSION_REASON.IS_CURRENT_TRACK
  );

  const sessionPlayedTokens = new Set([sanitizeTrackToken("PLAYED1")]);
  check(
    "already played this AutoMix session -> ALREADY_PLAYED_THIS_SESSION",
    evaluateHardExclusion(track("PLAYED1"), { sessionPlayedTokens }) === EXCLUSION_REASON.ALREADY_PLAYED_THIS_SESSION
  );

  const seenTokens = new Set([sanitizeTrackToken("DUP")]);
  check(
    "duplicate uri/id already seen in this pool -> DUPLICATE_URI",
    evaluateHardExclusion(track("DUP"), { seenTokens }) === EXCLUSION_REASON.DUPLICATE_URI
  );

  check(
    "explicit-content restriction, when the runtime context requests it -> EXPLICIT_CONTENT_RESTRICTED",
    evaluateHardExclusion(track("EXP", { explicit: true }), { excludeExplicit: true }) === EXCLUSION_REASON.EXPLICIT_CONTENT_RESTRICTED
  );
  check(
    "explicit track is NOT excluded when no explicit restriction is in effect",
    evaluateHardExclusion(track("EXP2", { explicit: true }), { excludeExplicit: false }) === null
  );

  check("an eligible candidate returns null (no exclusion)", evaluateHardExclusion(track("OK"), {}) === null);
}

// ============================================================
// Test 9: recent-repeat exclusion window
// ============================================================
{
  const recentRepeatWindowTokens = new Set([sanitizeTrackToken("REPEAT1")]);
  check(
    "a track inside the recent-repeat exclusion window -> RECENT_REPEAT_EXCLUDED",
    evaluateHardExclusion(track("REPEAT1"), { recentRepeatWindowTokens }) === EXCLUSION_REASON.RECENT_REPEAT_EXCLUDED
  );
  check(
    "a track outside the window is not excluded by it",
    evaluateHardExclusion(track("FRESH"), { recentRepeatWindowTokens }) === null
  );

  const result = selectNextTrack({
    candidates: [track("REPEAT1"), track("FRESH1")],
    currentTrack,
    recentRepeatWindowIds: ["REPEAT1"],
  });
  check("selectNextTrack end-to-end: recent-repeat-window track is excluded from the winner pool", result.selected.id === "FRESH1");
  check("selectNextTrack end-to-end: the excluded list records the RECENT_REPEAT_EXCLUDED reason", result.excluded.some((e) => e.reason === EXCLUSION_REASON.RECENT_REPEAT_EXCLUDED));
}

// ============================================================
// Test 10: immediate same-primary-artist exclusion
// ============================================================
{
  check(
    "immediate same-primary-artist repetition (vs. the currently playing track) -> IMMEDIATE_SAME_ARTIST_REPETITION",
    evaluateHardExclusion(track("SAMEARTIST", { artist: "ART_CURRENT" }), { currentPrimaryArtistId: "ART_CURRENT" }) === EXCLUSION_REASON.IMMEDIATE_SAME_ARTIST_REPETITION
  );

  const result = selectNextTrack({
    candidates: [track("SAMEARTIST", { artist: "ART_CURRENT" }), track("DIFFARTIST", { artist: "ART_OTHER" })],
    currentTrack,
  });
  check("selectNextTrack end-to-end: same-primary-artist candidate is excluded, the different-artist one wins", result.selected.id === "DIFFARTIST");
}

// ============================================================
// Test 8: deterministic ranking (same inputs -> same output, every time; documented priority order honored)
// ============================================================
{
  const candidates = [
    track("TOP1", { artist: "A1", affinitySource: "TOP_TRACK_AFFINITY" }),
    track("RECENT1", { artist: "A2", affinitySource: "RECENT_LISTENING_AFFINITY" }),
    track("SEARCH1", { artist: "A3", affinitySource: "SEARCH_FALLBACK" }),
  ];
  const results = Array.from({ length: 5 }, () => selectNextTrack({ candidates: [...candidates], currentTrack }));
  check("selectNextTrack is deterministic across repeated calls with identical input", results.every((r) => r.selected.id === results[0].selected.id));
  check("top-track affinity outranks recent-listening and search-fallback", results[0].selected.id === "TOP1");
  check("winning reason is TOP_TRACK_AFFINITY", results[0].reason === SELECTION_REASON.TOP_TRACK_AFFINITY);

  // Recent-listening beats search-fallback when no top-track candidate is present.
  const noTop = selectNextTrack({ candidates: [track("RECENT1", { artist: "A2", affinitySource: "RECENT_LISTENING_AFFINITY" }), track("SEARCH1", { artist: "A3", affinitySource: "SEARCH_FALLBACK" })], currentTrack });
  check("recent-listening affinity outranks search-fallback", noTop.selected.id === "RECENT1" && noTop.reason === SELECTION_REASON.RECENT_LISTENING_AFFINITY);

  // Not-played-recently preference: among two same-affinity candidates, the one with a HIGHER (older) recentPlayRank wins.
  const recencyCandidates = [
    track("JUST_PLAYED", { artist: "A4", affinitySource: "RECENT_LISTENING_AFFINITY", recentPlayRank: 0 }),
    track("PLAYED_A_WHILE_AGO", { artist: "A5", affinitySource: "RECENT_LISTENING_AFFINITY", recentPlayRank: 15 }),
  ];
  const recencyResult = selectNextTrack({ candidates: recencyCandidates, currentTrack });
  check("candidate played longer ago (or not recently played) is preferred over a just-played one", recencyResult.selected.id === "PLAYED_A_WHILE_AGO");

  // Artist diversity: among two equally-affine, equally-recent candidates, an artist not yet used this session wins.
  const diversityCandidates = [
    track("USED_ARTIST", { artist: "A_USED", affinitySource: "TOP_TRACK_AFFINITY" }),
    track("FRESH_ARTIST", { artist: "A_FRESH", affinitySource: "TOP_TRACK_AFFINITY" }),
  ];
  const diversityResult = selectNextTrack({ candidates: diversityCandidates, currentTrack, usedArtistIdsThisSession: ["A_USED"] });
  check("artist not yet used this session is preferred (diversity)", diversityResult.selected.id === "FRESH_ARTIST");
  check("winning reason is ARTIST_DIVERSITY when that's the deciding factor", diversityResult.reason === SELECTION_REASON.ARTIST_DIVERSITY);

  // Duration continuity: among remaining ties, the closer duration to current wins.
  const durationCandidates = [
    track("FAR_DURATION", { artist: "A6", affinitySource: "TOP_TRACK_AFFINITY", durationMs: 400000 }),
    track("CLOSE_DURATION", { artist: "A7", affinitySource: "TOP_TRACK_AFFINITY", durationMs: 205000 }),
  ];
  const durationResult = selectNextTrack({ candidates: durationCandidates, currentTrack });
  check("closer duration to the current track is preferred when other factors tie", durationResult.selected.id === "CLOSE_DURATION");

  // Deterministic opaque-ID tie-break: fully tied candidates (except id) always resolve to the same winner, never randomly.
  const tiedA = track("TIE_AAA", { artist: "A8", affinitySource: "TOP_TRACK_AFFINITY", durationMs: 200000 });
  const tiedB = track("TIE_BBB", { artist: "A9", affinitySource: "TOP_TRACK_AFFINITY", durationMs: 200000 });
  const tieOrder1 = selectNextTrack({ candidates: [tiedA, tiedB], currentTrack: { id: "OTHERCURRENT", primaryArtistId: "NONE", durationMs: null } });
  const tieOrder2 = selectNextTrack({ candidates: [tiedB, tiedA], currentTrack: { id: "OTHERCURRENT", primaryArtistId: "NONE", durationMs: null } });
  check("tie-break result does not depend on input array order (deterministic, not first-wins)", tieOrder1.selected.id === tieOrder2.selected.id);
  check("tie-break reason is DETERMINISTIC_TIE_BREAK when no other factor decides", tieOrder1.reason === SELECTION_REASON.DETERMINISTIC_TIE_BREAK);
}

// --- Empty/all-excluded pool ---
{
  const result = selectNextTrack({ candidates: [track("REPEAT1")], currentTrack, recentRepeatWindowIds: ["REPEAT1"] });
  check("an all-excluded pool returns selected: null with NO_ELIGIBLE_CANDIDATES", result.selected === null && result.reason === "NO_ELIGIBLE_CANDIDATES");
  const emptyResult = selectNextTrack({ candidates: [], currentTrack });
  check("an empty pool returns selected: null, no throw", emptyResult.selected === null);
  check("selectNextTrack tolerates undefined/missing arguments entirely", selectNextTrack().selected === null);
}

// --- Never claims acoustic-compatibility fields ---
{
  const result = selectNextTrack({ candidates: [track("ONLY")], currentTrack });
  const serialized = JSON.stringify(result);
  check("planner output never mentions bpm/tempo/key/energy/beat/transition claims", !/bpm|tempo|\bkey\b|energy|beatMatch|transitionQuality/i.test(serialized));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
