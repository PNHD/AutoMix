// Deterministic INTEGRATION-level proof of the seed-identity repair
// (Issue #11, PM comment `5324583196`, `P0_M6_R1_SEED_IDENTITY_REPAIR_REQUIRED`).
// Runs against the REAL SpotifyPublicControlAdapter class (not a
// reimplementation), driving its actual `_onPlayerStateChanged`/`next()`/
// `seek()` code paths with synthetic Web Playback SDK state objects. No
// network, no window/localStorage required -- the adapter's browser-only
// calls (`_player?.nextTrack()`, the `localStorage` read inside the
// `_clientId` getter) are either optional-chained or already fail closed.
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";
import { sanitizeTrackToken, canonicalTrackId, resolveManualAttribution, NO_PENDING_MANUAL_ACTION } from "../src/adapters/spotify-autoplay.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

function newAdapter() {
  return new SpotifyPublicControlAdapter({ clientId: "test-client-id", redirectUri: "http://127.0.0.1:5500/" });
}

// Mirrors exactly what the real Web Playback SDK listener in
// _registerPlayer() does: set _latestState, then run the instrumentation.
function feedState(adapter, state) {
  adapter._latestState = state;
  adapter._onPlayerStateChanged(state);
}

function fakeState({ trackId, nextIds = [], paused = false, position = 0 }) {
  return {
    paused,
    position,
    track_window: {
      current_track: { id: trackId, name: "irrelevant", artists: [{ name: "irrelevant" }] },
      next_tracks: nextIds.map((id) => ({ id, name: "irrelevant-next", artists: [{ name: "irrelevant" }] })),
    },
  };
}

// ============================================================
// Requirement 1: token(<id>) === token(spotify:track:<id>)
// ============================================================
check("canonicalTrackId strips the spotify:track: prefix", canonicalTrackId("spotify:track:SEED123") === "SEED123");
check("canonicalTrackId leaves a bare id unchanged", canonicalTrackId("SEED123") === "SEED123");
check("canonicalTrackId(null) is null", canonicalTrackId(null) === null);
check(
  "sanitizeTrackToken produces the SAME token for a bare id and its matching URI (the core invariant)",
  sanitizeTrackToken("SEED123") === sanitizeTrackToken("spotify:track:SEED123")
);
check(
  "sanitizeTrackToken still differs for genuinely different tracks, URI-shaped or not",
  sanitizeTrackToken("spotify:track:SEED123") !== sanitizeTrackToken("spotify:track:OTHER999")
);

// ============================================================
// Requirement 2: seed selected via URI, SDK emits bare id ->
// isSeedStillCurrent=true, seed playback confirmed, NOT continuation.
// ============================================================
{
  const adapter = newAdapter();
  adapter._seedToken = sanitizeTrackToken("spotify:track:SEED123"); // as playSeedTrack("spotify:track:SEED123") would set it
  adapter._seedPlaybackConfirmed = false;
  adapter._autoplaySnapshots = [];

  feedState(adapter, fakeState({ trackId: "SEED123", paused: false })); // SDK's own bare-id shape

  const lastSnap = adapter._autoplaySnapshots.at(-1);
  check("seed selected by URI: isSeedStillCurrent is true when SDK reports the same track by bare id", lastSnap.isSeedStillCurrent === true);
  check("seed selected by URI: seed playback becomes confirmed", adapter._seedPlaybackConfirmed === true);
  check(
    "seed selected by URI: seed's own first playback event is not classified as continuation",
    adapter.getAutoplayClassification().result !== "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED"
  );
}

// ============================================================
// Requirement 3: only a genuinely DIFFERENT current track id
// becomes continuation evidence.
// ============================================================
{
  const adapter = newAdapter();
  adapter._seedToken = sanitizeTrackToken("spotify:track:SEED123");
  adapter._seedPlaybackConfirmed = false;
  adapter._autoplaySnapshots = [];

  feedState(adapter, fakeState({ trackId: "SEED123" })); // seed playing
  feedState(adapter, fakeState({ trackId: "SEED123" })); // still the seed, no change
  check("repeated same-track events do not by themselves classify as continuation", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED");

  feedState(adapter, fakeState({ trackId: "GENUINELY_DIFFERENT_456" })); // a real, unrequested track change
  check(
    "a genuinely different current track id (no manual action taken) DOES classify as continuation",
    adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED"
  );
}

// ============================================================
// BLOCKER 2: manual Next -> intermediate same-track event ->
// later changed-track event. Final event MUST stay manual and
// MUST NOT classify as Autoplay.
// ============================================================
{
  const adapter = newAdapter();
  adapter._seedToken = sanitizeTrackToken("spotify:track:SEED123");
  adapter._seedPlaybackConfirmed = false;
  adapter._autoplaySnapshots = [];

  feedState(adapter, fakeState({ trackId: "SEED123" })); // seed established, _latestState now reflects SEED123

  await adapter.next(); // manual action begins, baseline token = SEED123
  check("next() begins a pending manual-action window", adapter._manualAction.pendingSinceMs !== null);

  feedState(adapter, fakeState({ trackId: "SEED123" })); // intermediate SDK event, track hasn't changed yet
  const intermediateSnap = adapter._autoplaySnapshots.at(-1);
  check("intermediate same-track event after manual Next is still marked manuallyTriggered", intermediateSnap.manuallyTriggered === true);
  check("intermediate same-track event does NOT resolve (clear) the pending manual action", adapter._manualAction.pendingSinceMs !== null);

  feedState(adapter, fakeState({ trackId: "NEXT_TRACK_789" })); // the actual manually-caused track change
  const finalSnap = adapter._autoplaySnapshots.at(-1);
  check("the event where the track actually changes is still marked manuallyTriggered", finalSnap.manuallyTriggered === true);
  check("the pending manual action is resolved (cleared) once the track actually changes", adapter._manualAction.pendingSinceMs === null);
  check(
    "the manually-triggered track change is NOT classified as Spotify Autoplay continuation",
    adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED"
  );
}

// Pure-function bounded-timeout check (no adapter needed).
{
  const pending = { pendingSinceMs: 1000, preActionToken: "A" };
  const withinWindow = resolveManualAttribution(pending, "A", 1000 + 4000, 8000);
  check("within the timeout window, an unresolved same-track event stays attributed", withinWindow.manuallyTriggered === true && withinWindow.nextState.pendingSinceMs !== null);

  const afterTimeout = resolveManualAttribution(pending, "A", 1000 + 9000, 8000);
  check("past the fixed bounded timeout, attribution stops even if the track never visibly changed", afterTimeout.manuallyTriggered === false);
  check("past the timeout, the manual-action state is fully cleared", JSON.stringify(afterTimeout.nextState) === JSON.stringify(NO_PENDING_MANUAL_ACTION));

  const noPending = resolveManualAttribution(NO_PENDING_MANUAL_ACTION, "X", 5000);
  check("with no pending manual action, a normal event is never marked manual", noPending.manuallyTriggered === false);
}

// ============================================================
// Requirement 4: sanitized snapshot privacy still holds after the fix.
// ============================================================
{
  const adapter = newAdapter();
  adapter._seedToken = sanitizeTrackToken("spotify:track:SEED123");
  adapter._autoplaySnapshots = [];
  feedState(adapter, fakeState({ trackId: "SEED123", nextIds: ["NEXT_A"] }));
  const snap = adapter._autoplaySnapshots.at(-1);
  const serialized = JSON.stringify(snap);
  check("snapshot never leaks the raw track id text", !serialized.includes("SEED123"));
  check("snapshot never leaks the spotify:track: uri scheme", !serialized.includes("spotify:track:"));
  check("snapshot never leaks title/artist text", !serialized.includes("irrelevant"));
  check("snapshot tokens are all opaque TRK_ tokens", serialized.match(/TRK_[0-9a-f]{8}/g)?.length >= 2);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
