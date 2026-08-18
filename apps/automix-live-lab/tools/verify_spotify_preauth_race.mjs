// Deterministic INTEGRATION-level proof of the pre-auth race repair
// (Issue #11, PM comment `5324756494`, `P0_M6_R1_PREAUTH_RACE_REPAIR_REQUIRED`).
// Runs against the REAL SpotifyPublicControlAdapter class, reproducing the
// exact defect PM found: a stale player_state_changed event for the
// PREVIOUSLY playing track can arrive after playSeedTrack() but before the
// SDK ever reports the requested seed as current.
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

/** Mirrors exactly what playSeedTrack(uri) sets, without the network call. */
function selectSeed(adapter, uri) {
  adapter._seedUri = uri;
  adapter._seedToken = sanitizeTrackToken(uri);
  adapter._autoplaySnapshots = [];
  adapter._seedPlaybackConfirmed = false;
  adapter._seedObserved = false;
}

// ============================================================
// PM-specified 9-step sequence: select SEED123 -> stale OLD_TRACK ->
// SEED123 becomes current -> later AUTO_NEXT.
// ============================================================
{
  const adapter = newAdapter();
  const diagnosticEvents = [];
  adapter.onStateChange((evt) => {
    if (evt.type === "pre_seed_diagnostic_snapshot") diagnosticEvents.push(evt);
  });

  // 1. select spotify:track:SEED123
  selectSeed(adapter, "spotify:track:SEED123");
  check("1. seed selection enters AWAITING_SEED_OBSERVATION (_seedObserved=false)", adapter._seedObserved === false);

  // 2. feed stale OLD_TRACK
  feedState(adapter, fakeState({ trackId: "OLD_TRACK" }));

  // 3. classification remains SPOTIFY_AUTOPLAY_NOT_OBSERVED; seed still unconfirmed
  check("3. stale pre-seed event: classification is SPOTIFY_AUTOPLAY_NOT_OBSERVED (NOT continuation)", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED");
  check("4. stale pre-seed event: seed is still NOT confirmed", adapter._seedPlaybackConfirmed === false);
  check("stale pre-seed event: does not enter _autoplaySnapshots at all", adapter._autoplaySnapshots.length === 0);
  check("stale pre-seed event: is captured as a diagnostic event instead (not silently dropped)", diagnosticEvents.length === 1 && diagnosticEvents[0].snapshot.beforeSeedObserved === true);
  check("stale pre-seed event: still AWAITING_SEED_OBSERVATION afterward", adapter._seedObserved === false);

  // 5. feed SEED123
  feedState(adapter, fakeState({ trackId: "SEED123" }));

  // 6. seed becomes confirmed; 7. still no continuation verdict
  check("6. seed's own first observation: _seedObserved flips to true (SEED_ACTIVE)", adapter._seedObserved === true);
  check("6. seed's own first observation: seed playback becomes confirmed", adapter._seedPlaybackConfirmed === true);
  check("7. seed's own first observation: still no continuation verdict", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED");
  check("seed's own first observation: DOES enter _autoplaySnapshots (SEED_ACTIVE evidence)", adapter._autoplaySnapshots.length === 1);

  // 8. feed later AUTO_NEXT (genuinely different, no manual action)
  feedState(adapter, fakeState({ trackId: "AUTO_NEXT" }));

  // 9. only now may it become CONTINUES_BUT_NEXT_NOT_PREEXPOSED
  check("9. genuinely different track AFTER seed observation classifies as continuation", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED");

  // The stale OLD_TRACK snapshot must never have contributed -- confirm by
  // inspecting the final evidence array directly: exactly 2 entries (SEED123, AUTO_NEXT), never OLD_TRACK.
  const tokens = adapter._autoplaySnapshots.map((s) => s.currentToken);
  check("final evidence array contains exactly [SEED123, AUTO_NEXT] tokens, OLD_TRACK never present", tokens.length === 2 && tokens[0] === sanitizeTrackToken("SEED123") && tokens[1] === sanitizeTrackToken("AUTO_NEXT"));
}

// ============================================================
// 10. stale pre-seed next_tracks must NOT produce SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE.
// ============================================================
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");

  // Stale event for the OLD track, which happens to have its OWN next_tracks populated.
  feedState(adapter, fakeState({ trackId: "OLD_TRACK", nextIds: ["OLD_TRACKS_OWN_NEXT"] }));
  check("10. stale pre-seed next_tracks does not classify as SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE", adapter.getAutoplayClassification().result !== "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE");
  check("10. stale pre-seed next_tracks: classification stays SPOTIFY_AUTOPLAY_NOT_OBSERVED", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED");

  // Now the seed itself becomes current with no next_tracks -- still no pre-exposure.
  feedState(adapter, fakeState({ trackId: "SEED123", nextIds: [] }));
  check("after seed observed with empty next_tracks, still not NEXT_TRACKS_VISIBLE", adapter.getAutoplayClassification().result !== "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE");

  // But genuine pre-exposure AFTER seed observation still works as before this repair.
  const adapter2 = newAdapter();
  selectSeed(adapter2, "spotify:track:SEED123");
  feedState(adapter2, fakeState({ trackId: "SEED123", nextIds: ["GENUINE_NEXT"] }));
  check("genuine pre-exposure AFTER seed observation still classifies SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE (regression check)", adapter2.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE");
}

// ============================================================
// Regression: existing BLOCKER-1/2 scenarios (seed fed as the FIRST
// event, no stale event) must behave exactly as before this repair.
// ============================================================
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123" })); // seed IS the first event -- no stale race here
  check("regression: seed-first (no stale event) still confirms playback immediately", adapter._seedPlaybackConfirmed === true);
  check("regression: seed-first event still enters _autoplaySnapshots (not treated as stale)", adapter._autoplaySnapshots.length === 1);
}
{
  const adapter = newAdapter();
  selectSeed(adapter, "spotify:track:SEED123");
  feedState(adapter, fakeState({ trackId: "SEED123" }));
  await adapter.next(); // manual action begins after seed is already active
  feedState(adapter, fakeState({ trackId: "SEED123" })); // intermediate, same track
  feedState(adapter, fakeState({ trackId: "MANUALLY_SELECTED_NEXT" })); // actual manual change
  check("regression: manual-Next attribution across intermediate events still works after this repair", adapter.getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED");
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
