// Deterministic proof of P0-M6-R2 repair-pass Blocker 5: recent-repeat
// exclusion must come from REAL GET /me/player/recently-played history,
// distinct from ALREADY_PLAYED_THIS_SESSION -- and a track appearing in
// BOTH Top Tracks and Recently Played must keep its stronger
// TOP_TRACK_AFFINITY tag AND its recentPlayRank (previously dropped by
// the candidate-pool dedup). No network.
import { assembleCandidatePool, AFFINITY_SOURCE, candidatesFromTopTracks, candidatesFromRecentlyPlayed } from "../src/adapters/spotify-candidate-pool.js";
import { selectNextTrack, EXCLUSION_REASON } from "../src/adapters/spotify-planner.js";
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { sanitizeTrackToken } from "../src/adapters/spotify-autoplay.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// ============================================================
// Test: a top-track candidate that's ALSO recent rank 0 keeps both signals
// ============================================================
{
  const topRaw = candidatesFromTopTracks({ items: [{ id: "DUP", uri: "spotify:track:DUP", artists: [{ id: "A1" }] }] });
  const recentRaw = candidatesFromRecentlyPlayed({ items: [{ track: { id: "DUP", uri: "spotify:track:DUP", artists: [{ id: "A1" }] } }] }); // index 0 -> recentPlayRank 0
  check("candidatesFromTopTracks has no recentPlayRank on its own", !("recentPlayRank" in topRaw[0]) || topRaw[0].recentPlayRank === undefined);
  check("candidatesFromRecentlyPlayed stamps recentPlayRank 0 for the most recent item", recentRaw[0].recentPlayRank === 0);

  const pool = assembleCandidatePool([topRaw, recentRaw]);
  check("pool has exactly one entry for the duplicated id", pool.length === 1);
  check("dedup KEEPS the stronger TOP_TRACK_AFFINITY source", pool[0].affinitySource === AFFINITY_SOURCE.TOP_TRACK);
  check("dedup ALSO retains recentPlayRank from the later recently-played entry (Blocker 5 fix)", pool[0].recentPlayRank === 0);
}

// ============================================================
// Test: recent rank 0 excluded by the recent-repeat window (hard exclusion)
// ============================================================
{
  const currentTrack = { id: "CURRENT", primaryArtistId: "ART_CURRENT", durationMs: 200000 };
  const candidates = [
    { id: "JUST_PLAYED", uri: "spotify:track:JUST_PLAYED", primaryArtistId: "A1", durationMs: 200000, affinitySource: "RECENT_LISTENING_AFFINITY", recentPlayRank: 0 },
    { id: "FRESH", uri: "spotify:track:FRESH", primaryArtistId: "A2", durationMs: 200000, affinitySource: "RECENT_LISTENING_AFFINITY" },
  ];
  const result = selectNextTrack({ candidates, currentTrack, recentRepeatWindowIds: ["JUST_PLAYED"] });
  check("a track inside the real recent-repeat window is hard-excluded (RECENT_REPEAT_EXCLUDED)", result.excluded.some((e) => e.reason === EXCLUSION_REASON.RECENT_REPEAT_EXCLUDED));
  check("the winner is the one NOT in the recent-repeat window", result.selected.id === "FRESH");
}

// ============================================================
// Test: an older eligible TOP track wins over a just-played TOP track (soft ranking, once recentPlayRank is correctly retained)
// ============================================================
{
  const currentTrack = { id: "CURRENT", primaryArtistId: "ART_CURRENT", durationMs: 200000 };
  const topRaw = candidatesFromTopTracks({
    items: [
      { id: "TOP_JUST_PLAYED", uri: "spotify:track:TOP_JUST_PLAYED", artists: [{ id: "A1" }], duration_ms: 200000 },
      { id: "TOP_OLDER", uri: "spotify:track:TOP_OLDER", artists: [{ id: "A2" }], duration_ms: 200000 },
    ],
  });
  const recentRaw = candidatesFromRecentlyPlayed({
    items: [
      { track: { id: "TOP_JUST_PLAYED", uri: "spotify:track:TOP_JUST_PLAYED", artists: [{ id: "A1" }] } }, // rank 0 -- just played
      { track: { id: "TOP_OLDER", uri: "spotify:track:TOP_OLDER", artists: [{ id: "A2" }] } }, // rank 1 -- played a bit further back... still need it further to prove "older wins" clearly, so add filler entries
    ],
  });
  // Push TOP_OLDER's rank further back to make the "older wins" case unambiguous.
  const recentRawSpread = candidatesFromRecentlyPlayed({
    items: [
      { track: { id: "TOP_JUST_PLAYED", uri: "spotify:track:TOP_JUST_PLAYED", artists: [{ id: "A1" }] } }, // rank 0
      { track: { id: "FILLER1", uri: "spotify:track:FILLER1", artists: [{ id: "AF1" }] } }, // rank 1
      { track: { id: "FILLER2", uri: "spotify:track:FILLER2", artists: [{ id: "AF2" }] } }, // rank 2
      { track: { id: "TOP_OLDER", uri: "spotify:track:TOP_OLDER", artists: [{ id: "A2" }] } }, // rank 3 -- played longer ago than TOP_JUST_PLAYED
    ],
  });

  const pool = assembleCandidatePool([topRaw, recentRawSpread]);
  const bothTopCandidates = pool.filter((c) => c.id === "TOP_JUST_PLAYED" || c.id === "TOP_OLDER");
  check("both candidates keep TOP_TRACK_AFFINITY even though both are also in Recently Played", bothTopCandidates.every((c) => c.affinitySource === AFFINITY_SOURCE.TOP_TRACK));

  const result = selectNextTrack({ candidates: pool.filter((c) => c.id === "TOP_JUST_PLAYED" || c.id === "TOP_OLDER"), currentTrack });
  check("the TOP track played LONGER AGO wins over the TOP track played JUST NOW (Blocker 5: a top track can't hide behind 'never recently played')", result.selected.id === "TOP_OLDER");
}

// ============================================================
// Test: session-played and account-recent exclusions are distinct
// ============================================================
{
  const currentTrack = { id: "CURRENT", primaryArtistId: "ART_CURRENT", durationMs: 200000 };
  const candidates = [
    { id: "SESSION_ONLY", uri: "spotify:track:SESSION_ONLY", primaryArtistId: "A1", durationMs: 200000, affinitySource: "TOP_TRACK_AFFINITY" },
    { id: "ACCOUNT_RECENT_ONLY", uri: "spotify:track:ACCOUNT_RECENT_ONLY", primaryArtistId: "A2", durationMs: 200000, affinitySource: "TOP_TRACK_AFFINITY" },
    { id: "NEITHER", uri: "spotify:track:NEITHER", primaryArtistId: "A3", durationMs: 200000, affinitySource: "TOP_TRACK_AFFINITY" },
  ];
  const result = selectNextTrack({
    candidates,
    currentTrack,
    sessionPlayedIds: ["SESSION_ONLY"], // played THIS AutoMix session
    recentRepeatWindowIds: ["ACCOUNT_RECENT_ONLY"], // played recently on the ACCOUNT, but not this session
  });
  const sessionExclusion = result.excluded.find((e) => e.token === sanitizeTrackToken("SESSION_ONLY"));
  const accountExclusion = result.excluded.find((e) => e.token === sanitizeTrackToken("ACCOUNT_RECENT_ONLY"));
  check("a track played THIS session is excluded as ALREADY_PLAYED_THIS_SESSION", sessionExclusion?.reason === EXCLUSION_REASON.ALREADY_PLAYED_THIS_SESSION);
  check("a track in the account's recent-play window (but NOT this session) is excluded as RECENT_REPEAT_EXCLUDED -- a DIFFERENT reason", accountExclusion?.reason === EXCLUSION_REASON.RECENT_REPEAT_EXCLUDED);
  check("the two exclusion reasons are genuinely distinct values, not duplicates of each other", sessionExclusion.reason !== accountExclusion.reason);
  check("the only fully-eligible candidate wins", result.selected.id === "NEITHER");
}

// ============================================================
// Adapter integration: runLookaheadCycle() sources recentRepeatWindowIds from REAL recently-played, not from sessionPlayedIds
// ============================================================
{
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._deviceId = "device123";
  adapter._seedUri = "spotify:track:SEED123";
  adapter._seedToken = sanitizeTrackToken("SEED123");
  adapter._seedObserved = true;
  adapter._latestState = {
    paused: false,
    position: 0,
    duration: 200000,
    track_window: { current_track: { id: "SEED123", duration_ms: 200000, artists: [{ id: "ART_SEED" }] }, next_tracks: [] },
  };
  // This AutoMix session has only ever played the seed -- "ACCOUNT_RECENT"
  // was never played THIS session, only shows up in real account history.
  adapter._sessionPlayedIds = ["SEED123"];

  adapter._api = async (url) => {
    if (url.startsWith("/me/top/tracks")) return { items: [{ id: "ACCOUNT_RECENT", uri: "spotify:track:ACCOUNT_RECENT", artists: [{ id: "A1" }], duration_ms: 200000, is_playable: true }, { id: "FRESH", uri: "spotify:track:FRESH", artists: [{ id: "A2" }], duration_ms: 200000, is_playable: true }] };
    if (url.startsWith("/me/player/recently-played")) return { items: [{ track: { id: "ACCOUNT_RECENT", uri: "spotify:track:ACCOUNT_RECENT", artists: [{ id: "A1" }] } }] }; // real account history
    if (url === "/me/player/queue") return { currently_playing: { id: "SEED123" }, queue: [] };
    if (url.startsWith("/me/player/queue?")) return null;
    return null;
  };

  const result = await adapter.runLookaheadCycle();
  check("runLookaheadCycle() excludes a track only present in REAL recently-played (not sessionPlayedIds)", result.selectionReason && result.token === sanitizeTrackToken("FRESH"));
  check("real recently-played history was actually fetched and captured", adapter._lastRecentlyPlayedIds.includes("ACCOUNT_RECENT"));
  check("_sessionPlayedIds (a genuinely separate list) does NOT contain the account-recent track", !adapter._sessionPlayedIds.includes("ACCOUNT_RECENT"));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
