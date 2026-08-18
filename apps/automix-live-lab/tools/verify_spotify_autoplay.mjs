// Deterministic proof of sanitized snapshot capture + the four-way
// Autoplay classification (Issue #11, PM comment `5324307503`, BLOCKER 2).
// No network call, no real Spotify session -- synthetic Web Playback SDK
// state objects only.
import { sanitizeTrackToken, captureSnapshot, classifyAutoplayResult } from "../src/adapters/spotify-autoplay.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// --- sanitizeTrackToken ---
const tokenA1 = sanitizeTrackToken("spotify:track:AAAA111111111111111111");
const tokenA2 = sanitizeTrackToken("spotify:track:AAAA111111111111111111");
const tokenB = sanitizeTrackToken("spotify:track:BBBB222222222222222222");
check("sanitizeTrackToken is deterministic for the same id", tokenA1 === tokenA2);
check("sanitizeTrackToken differs for different ids", tokenA1 !== tokenB);
check("sanitizeTrackToken has the TRK_ prefix and no id substring leaks through", tokenA1.startsWith("TRK_") && !tokenA1.includes("AAAA"));
check("sanitizeTrackToken(null) is null", sanitizeTrackToken(null) === null);

// --- captureSnapshot ---
const seedToken = sanitizeTrackToken("seed-id");
const fakeState = {
  paused: false,
  position: 12345,
  track_window: {
    current_track: { id: "seed-id", name: "Should Never Appear In Snapshot", artists: [{ name: "Nor This" }] },
    next_tracks: [{ id: "next-id-1" }, { id: "next-id-2" }],
  },
};
const snap = captureSnapshot({ state: fakeState, seedToken, capturedAtMs: 1000 });
check("captureSnapshot marks the seed as still current", snap.isSeedStillCurrent === true);
check("captureSnapshot counts next_tracks correctly", snap.nextTrackCount === 2);
check("captureSnapshot sanitizes next_tracks into opaque tokens", snap.nextTokens.every((t) => t.startsWith("TRK_")));
check("captureSnapshot never leaks title/artist text into the snapshot object", JSON.stringify(snap).includes("Should Never Appear") === false);
check("captureSnapshot carries isPlaying from !paused", snap.isPlaying === true);
check("captureSnapshot carries positionMs", snap.positionMs === 12345);
check("captureSnapshot defaults manuallyTriggered to false", snap.manuallyTriggered === false);

// --- classifyAutoplayResult: no data ---
check("empty snapshot list classifies NOT_OBSERVED with NO_SNAPSHOTS_CAPTURED", classifyAutoplayResult([]).result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED" && classifyAutoplayResult([]).reason === "NO_SNAPSHOTS_CAPTURED");

// --- Scenario: next_tracks pre-exposed while seed is current ---
const preExposedSnapshots = [
  { seedToken: "S1", currentToken: "S1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: true, manuallyTriggered: false },
  { seedToken: "S1", currentToken: "S1", nextTokens: ["N1"], nextTrackCount: 1, isSeedStillCurrent: true, manuallyTriggered: false },
];
check(
  "next_tracks populated while seed is current classifies SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE",
  classifyAutoplayResult(preExposedSnapshots).result === "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE"
);

// --- Scenario: continuation happens, but never pre-exposed ---
const lateContinuationSnapshots = [
  { seedToken: "S1", currentToken: "S1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: true, manuallyTriggered: false },
  { seedToken: "S1", currentToken: "S1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: true, manuallyTriggered: false },
  { seedToken: "S1", currentToken: "N1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: false, manuallyTriggered: false },
];
check(
  "unannounced continuation classifies SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED",
  classifyAutoplayResult(lateContinuationSnapshots).result === "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED"
);

// --- Scenario: no continuation at all, setting state unknown ---
const noContinuationSnapshots = [
  { seedToken: "S1", currentToken: "S1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: true, manuallyTriggered: false },
  { seedToken: "S1", currentToken: "S1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: true, manuallyTriggered: false },
];
check(
  "no pre-exposure and no continuation classifies SPOTIFY_AUTOPLAY_NOT_OBSERVED by default",
  classifyAutoplayResult(noContinuationSnapshots).result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED"
);
check(
  "the same no-continuation snapshots classify SPOTIFY_AUTOPLAY_SETTING_REQUIRED when the owner confirms Autoplay is off",
  classifyAutoplayResult(noContinuationSnapshots, { autoplayConfirmedDisabled: true }).result === "SPOTIFY_AUTOPLAY_SETTING_REQUIRED"
);

// --- Scenario: track changed, but WE triggered it (manual Next click) -- must not count as autoplay ---
const manualNextSnapshots = [
  { seedToken: "S1", currentToken: "S1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: true, manuallyTriggered: false },
  { seedToken: "S1", currentToken: "N1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: false, manuallyTriggered: true },
];
check(
  "a manually-triggered track change is NOT classified as autoplay continuation",
  classifyAutoplayResult(manualNextSnapshots).result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED"
);

// --- Scenario: pre-exposure takes priority even if the track later changes ---
const preExposedThenChangedSnapshots = [
  { seedToken: "S1", currentToken: "S1", nextTokens: ["N1"], nextTrackCount: 1, isSeedStillCurrent: true, manuallyTriggered: false },
  { seedToken: "S1", currentToken: "N1", nextTokens: [], nextTrackCount: 0, isSeedStillCurrent: false, manuallyTriggered: false },
];
check(
  "pre-exposure is detected even when a later snapshot also shows continuation",
  classifyAutoplayResult(preExposedThenChangedSnapshots).result === "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE"
);

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
