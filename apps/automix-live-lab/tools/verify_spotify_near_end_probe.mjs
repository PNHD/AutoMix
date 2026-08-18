// Deterministic INTEGRATION-level proof of the near-end Autoplay probe
// and the Manual-Seek-vs-Manual-Next attribution split (owner-requested
// Sections B/C/D). Drives the REAL SpotifyPublicControlAdapter class with
// synthetic Web Playback SDK state objects -- no network.
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

function newAdapter() {
  return new SpotifyPublicControlAdapter({ clientId: "test-client-id", redirectUri: "http://127.0.0.1:5500/" });
}

function feedState(adapter, state) {
  adapter._latestState = state;
  adapter._onPlayerStateChanged(state);
}

function fakeState({ trackId, nextIds = [], paused = false, position = 0, duration = 200_000 }) {
  return {
    paused,
    position,
    duration,
    track_window: {
      current_track: { id: trackId, name: "irrelevant", artists: [{ name: "irrelevant" }] },
      next_tracks: nextIds.map((id) => ({ id, name: "irrelevant-next", artists: [{ name: "irrelevant" }] })),
    },
  };
}

function selectSeed(adapter, uri) {
  adapter._seedUri = uri;
  adapter._seedToken = sanitizeTrackToken(uri);
  adapter._autoplaySnapshots = [];
  adapter._seedPlaybackConfirmed = false;
  adapter._seedObserved = false;
}

// ============================================================
// D.5/D.6: Manual Seek must NOT attribute a later natural track change;
// Manual Next still must.
// ============================================================
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123" })); // seed active

  const seekEvents = [];
  adapter.onStateChange((evt) => {
    if (evt.type === "manual_seek") seekEvents.push(evt);
  });

  await adapter.seek(150_000); // Manual Seek -- must NOT create pending attribution
  check("D: seek() never touches _manualAction (stays NO_PENDING)", adapter._manualAction.pendingSinceMs === null);
  check("D: seek() emits exactly one sanitized manual_seek diagnostic event", seekEvents.length === 1);
  check("D: manual_seek event carries the (clamped) requested position", typeof seekEvents[0].requestedPositionMs === "number");

  feedState(adapter, fakeState({ trackId: "AUTO_AFTER_SEEK" })); // a later, genuinely different track, no manual action taken
  check(
    "D.5: the later natural track change after a Manual Seek IS classified as Autoplay continuation (not suppressed)",
    adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED"
  );
}
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123" }));

  await adapter.next(); // Manual Next -- MUST create pending attribution
  check("D.6 regression: next() still begins pending manual attribution", adapter._manualAction.pendingSinceMs !== null);
  feedState(adapter, fakeState({ trackId: "SEED123" })); // intermediate, same track
  feedState(adapter, fakeState({ trackId: "MANUALLY_SELECTED" })); // the actual manual change
  check(
    "D.6 regression: the resulting track change after a Manual Next is NOT classified as Autoplay",
    adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED"
  );
}

// ============================================================
// D.7 / D.8 / D.9 / D.10: startNearEndProbe() itself.
// ============================================================
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123", duration: 200_000 }));

  // Guard: probing before the seed is observed must fail closed.
  const freshAdapter = newAdapter();
  freshAdapter._seedToken = sanitizeTrackToken("spotify:track:SEED123");
  let threwNotActive = false;
  try {
    await freshAdapter.startNearEndProbe();
  } catch (e) {
    threwNotActive = e.message === "SEED_NOT_YET_ACTIVE_FOR_PROBE";
  }
  check("startNearEndProbe() refuses to run before the seed is SEED_ACTIVE", threwNotActive);

  // D.8 setup: contaminate the pre-probe evidence with a NEXT_TRACKS_VISIBLE-triggering snapshot.
  feedState(adapter, fakeState({ trackId: "SEED123", nextIds: ["PRE_PROBE_NEXT"], duration: 200_000 }));
  check("pre-probe: next_tracks pre-exposure is (correctly) visible before the probe", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE");

  const preProbeSeedToken = adapter._seedToken;
  const { targetMs, durationMs } = await adapter.startNearEndProbe();
  check("startNearEndProbe() computes a target within the track", targetMs >= 0 && targetMs < durationMs);

  // D.7: seed stays SEED_ACTIVE, same token, across the probe.
  check("D.7: _seedObserved remains true (SEED_ACTIVE) across the probe", adapter._seedObserved === true);
  check("D.7: _seedToken is unchanged across the probe (same seed, just repositioned)", adapter._seedToken === preProbeSeedToken);
  check("D.7: _seedPlaybackConfirmed remains true across the probe", adapter._seedPlaybackConfirmed === true);

  // D.8: pre-probe snapshots archived, evidence array reset, cannot contaminate the new classification.
  check("D.8: pre-probe snapshots are archived (diagnostic-only), not deleted outright", adapter._preProbeSnapshotsArchive.length === 1 && adapter._preProbeSnapshotsArchive[0].snapshots.length > 0);
  check("D.8: the live evidence array is empty immediately after starting the probe", adapter._autoplaySnapshots.length === 0);
  check(
    "D.8: classification right after the probe starts is NOT contaminated by the pre-probe NEXT_TRACKS_VISIBLE evidence",
    adapter.getAutoplayClassification().result !== "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE"
  );

  // Post-seek, the SDK reports the seed still playing near the end (no next_tracks this time).
  feedState(adapter, fakeState({ trackId: "SEED123", nextIds: [], position: targetMs, duration: 200_000 }));
  check("post-probe: still no false NEXT_TRACKS_VISIBLE from the fresh window", adapter.getAutoplayClassification().result !== "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE");

  // D.9: a genuinely different track after the seek DOES count as continuation.
  feedState(adapter, fakeState({ trackId: "REAL_AUTOPLAY_CONTINUATION", duration: 200_000 }));
  check(
    "D.9: a genuinely different track appearing naturally after the near-end seek classifies as continuation",
    adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED"
  );
}

// D.10: same seed simply stops at the end, no continuation track ever appears.
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123", duration: 200_000 }));
  await adapter.startNearEndProbe();
  feedState(adapter, fakeState({ trackId: "SEED123", paused: false, position: 199_000, duration: 200_000 }));
  feedState(adapter, fakeState({ trackId: "SEED123", paused: true, position: 200_000, duration: 200_000 })); // natural end -- stops, same track, no continuation
  check(
    "D.10: same-seed stopped-at-end state (no continuation track) classifies SPOTIFY_AUTOPLAY_NOT_OBSERVED",
    adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED"
  );
}

// ============================================================
// D.11: privacy remains opaque-token-only across the new artifacts.
// ============================================================
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123", duration: 200_000 }));

  const events = [];
  adapter.onStateChange((evt) => events.push(evt));

  await adapter.startNearEndProbe();
  feedState(adapter, fakeState({ trackId: "SEED123", position: 185_000, duration: 200_000 }));

  const serialized = JSON.stringify(events);
  check("D.11: no raw track id text leaks across manual_seek/near_end_probe_started/autoplay_snapshot events", !serialized.includes("SEED123"));
  check("D.11: no spotify:track: uri scheme leaks", !serialized.includes("spotify:track:"));
  check("D.11: no title/artist text leaks", !serialized.includes("irrelevant"));
  check("D.11: near_end_probe_started event carries only numeric targetMs/durationMs", events.some((e) => e.type === "near_end_probe_started" && typeof e.targetMs === "number" && typeof e.durationMs === "number"));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
