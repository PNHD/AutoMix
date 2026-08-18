/**
 * Sanitized Autoplay/next-track observability instrumentation.
 * Issue #11 PM comment `5324307503`, BLOCKER 2.
 *
 * Spotify's Web Playback SDK `player_state_changed` event exposes
 * `track_window.{current_track, next_tracks}`. This module turns that raw
 * event into a SANITIZED snapshot (opaque tokens only, never title/artist)
 * suitable for tracked evidence, and classifies a sequence of snapshots
 * into exactly one of the four PM-defined Autoplay observability results.
 *
 * No fetch, no DOM -- pure functions, unit-tested in
 * tools/verify_spotify_autoplay.mjs without a real Spotify session.
 */

// Repair pass (Issue #11, PM comment `5324583196`,
// `P0_M6_R1_SEED_IDENTITY_REPAIR_REQUIRED`, BLOCKER 1): Spotify identifies
// the same track two ways depending on the surface -- `PUT /me/player/play`
// takes a full URI (`spotify:track:<id>`), while Web Playback SDK's
// `track_window.current_track.id` is the bare `<id>`. Hashing these two
// shapes directly, as the prior pass did, produces two DIFFERENT tokens for
// the SAME song. `canonicalTrackId` is the single place that strips the URI
// prefix; `sanitizeTrackToken` always canonicalizes before hashing, so
// every call site (seed selection via URI, runtime state via bare id) goes
// through the exact same normalization -- no ad-hoc parsing anywhere else.
import { fnv1aHex } from "./spotify-privacy.js";

const SPOTIFY_TRACK_URI_PREFIX = "spotify:track:";

export function canonicalTrackId(idOrUri) {
  if (!idOrUri) return null;
  return idOrUri.startsWith(SPOTIFY_TRACK_URI_PREFIX) ? idOrUri.slice(SPOTIFY_TRACK_URI_PREFIX.length) : idOrUri;
}

/**
 * Deterministic, synchronous, non-cryptographic hash (`fnv1aHex`,
 * spotify-privacy.js -- shared with device-id sanitization, Blocker 7).
 * Used only to produce an opaque, stable, non-reversible-in-practice
 * token for a Spotify track id -- NOT a security primitive. Synchronous
 * (unlike Web Crypto's SubtleCrypto) so it can run directly inside the
 * `player_state_changed` event handler without an extra async hop.
 *
 * Accepts EITHER a bare track id ("SEED123") OR a full track URI
 * ("spotify:track:SEED123") and always returns the SAME token for the
 * same underlying track -- see `canonicalTrackId` above.
 */
export function sanitizeTrackToken(trackIdOrUri) {
  const id = canonicalTrackId(trackIdOrUri);
  if (!id) return null;
  return `TRK_${fnv1aHex(id)}`;
}

// Repair pass (Issue #11, PM comment `5324583196`, BLOCKER 2): the prior
// pass's `_manualActionPending` boolean was cleared on the FIRST
// `player_state_changed` event after a manual next()/seek() call, even if
// that event still showed the SAME track (SDK state events can fire more
// than once for one user action -- e.g. a position/paused update before
// the track itself actually changes). That let a later, still-manually-
// caused track-change event arrive with the flag already cleared and get
// misclassified as Spotify Autoplay. This state machine keeps attribution
// alive across same-track intermediate events and only consumes
// (resolves) it on the event where the track ACTUALLY changes -- bounded
// by a fixed timeout so a manual action can never suppress attribution
// forever if the track change is missed for some reason. Not pair/song-
// specific: the timeout is a single fixed constant.
export const MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS = 8000;

export const NO_PENDING_MANUAL_ACTION = Object.freeze({ pendingSinceMs: null, preActionToken: null });

/** Call when next()/seek() is invoked, with the token of whatever is current right before the call. */
export function beginManualAction(nowMs, currentTokenBeforeAction) {
  return { pendingSinceMs: nowMs, preActionToken: currentTokenBeforeAction };
}

/**
 * Call on every `player_state_changed` event with the CURRENT manual-action
 * state, the new event's current-track token, and the current time.
 * Returns `{ manuallyTriggered, nextState }` -- `nextState` must replace
 * whatever manual-action state the caller was holding.
 */
export function resolveManualAttribution(manualState, currentToken, nowMs, timeoutMs = MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS) {
  const state = manualState || NO_PENDING_MANUAL_ACTION;
  if (state.pendingSinceMs === null) {
    return { manuallyTriggered: false, nextState: NO_PENDING_MANUAL_ACTION };
  }
  if (nowMs - state.pendingSinceMs > timeoutMs) {
    // Bounded timeout expired -- stop attributing; this event is judged normally.
    return { manuallyTriggered: false, nextState: NO_PENDING_MANUAL_ACTION };
  }
  if (currentToken !== state.preActionToken) {
    // The track has now actually changed -- this IS the manual transition
    // becoming visible. Attribute it, then resolve (consume) the pending state.
    return { manuallyTriggered: true, nextState: NO_PENDING_MANUAL_ACTION };
  }
  // Same track as before the manual action -- an intermediate event
  // (e.g. a position update). Still within the manual action's effect;
  // keep the pending state alive for the next event.
  return { manuallyTriggered: true, nextState: state };
}

/**
 * Builds one sanitized snapshot from a raw Web Playback SDK state object
 * (the same shape passed to `player_state_changed`). Only opaque tokens,
 * counts, and numbers are retained -- no title/artist/album text.
 *
 * `beforeSeedObserved` (repair pass, PM comment `5324756494`,
 * `P0_M6_R1_PREAUTH_RACE_REPAIR_REQUIRED`): tags a snapshot captured
 * while still in the `AWAITING_SEED_OBSERVATION` phase -- i.e. a stale
 * SDK event for whatever was playing before `playSeedTrack()`, arriving
 * before the SDK has ever reported the requested seed as current. Purely
 * informational on the snapshot itself; the adapter (not this function)
 * is responsible for excluding such snapshots from the array it feeds to
 * `classifyAutoplayResult`, see `SpotifyPublicControlAdapter.js`.
 */
export function captureSnapshot({ state, seedToken, capturedAtMs, manuallyTriggered = false, beforeSeedObserved = false }) {
  const currentTrack = state?.track_window?.current_track ?? null;
  const nextTracks = state?.track_window?.next_tracks ?? [];
  return {
    capturedAtMs,
    seedToken,
    currentToken: currentTrack ? sanitizeTrackToken(currentTrack.id) : null,
    nextTokens: nextTracks.map((t) => sanitizeTrackToken(t.id)).filter(Boolean),
    nextTrackCount: nextTracks.length,
    positionMs: state?.position ?? null,
    isPlaying: state ? !state.paused : null,
    isSeedStillCurrent: currentTrack ? sanitizeTrackToken(currentTrack.id) === seedToken : null,
    manuallyTriggered,
    beforeSeedObserved,
  };
}

/**
 * Classifies a sanitized snapshot sequence into exactly one of the four
 * PM-defined results (Issue #11 comment `5324307503`, BLOCKER 2):
 *
 *   - SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE: `next_tracks` was populated
 *     while the seed track was still current -- Spotify pre-exposed the
 *     continuation before it started playing.
 *   - SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED: the current
 *     track changed to something other than the seed, without this app
 *     ever calling play/seek/next itself, but `next_tracks` was empty
 *     the whole time the seed was current -- continuation happened, but
 *     couldn't be inspected ahead of time.
 *   - SPOTIFY_AUTOPLAY_SETTING_REQUIRED: no continuation was observed AND
 *     the caller has told us (out-of-band, via `autoplayConfirmedDisabled`
 *     -- Spotify does not expose the Autoplay toggle state through any
 *     public API, so this can only come from the owner checking their own
 *     account/device settings) that Autoplay is off.
 *   - SPOTIFY_AUTOPLAY_NOT_OBSERVED: no continuation was observed and the
 *     Autoplay setting state is unknown/not confirmed disabled -- the
 *     mechanical default.
 *
 * Repair pass (PM comment `5324756494`,
 * `P0_M6_R1_PREAUTH_RACE_REPAIR_REQUIRED`): any snapshot tagged
 * `beforeSeedObserved: true` (a stale SDK event for the previously-
 * playing track, arriving before the requested seed was ever observed
 * as current) is mechanically excluded from every decision below, no
 * matter what the caller passes in -- the invariant "non-seed state
 * before first seed observation != continuation evidence" is enforced
 * here unconditionally, not merely by callers remembering not to append
 * such snapshots in the first place.
 */
export function classifyAutoplayResult(snapshots, { autoplayConfirmedDisabled = false } = {}) {
  const eligible = Array.isArray(snapshots) ? snapshots.filter((s) => !s.beforeSeedObserved) : [];
  if (eligible.length === 0) {
    const reason = Array.isArray(snapshots) && snapshots.length > 0 ? "ALL_SNAPSHOTS_BEFORE_SEED_OBSERVED" : "NO_SNAPSHOTS_CAPTURED";
    return { result: "SPOTIFY_AUTOPLAY_NOT_OBSERVED", reason };
  }
  const seedToken = eligible[0].seedToken;

  const preExposed = eligible.some((s) => s.isSeedStillCurrent && s.nextTrackCount > 0);
  if (preExposed) {
    return { result: "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE", reason: "next_tracks was populated while the seed track was still current" };
  }

  const continuedWithoutManualTrigger = eligible.find(
    (s) => s.currentToken && s.currentToken !== seedToken && !s.manuallyTriggered
  );
  if (continuedWithoutManualTrigger) {
    return {
      result: "SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED",
      reason: "current track changed to a non-seed track without a manual play/seek/next call, but next_tracks was never populated beforehand",
    };
  }

  if (autoplayConfirmedDisabled) {
    return {
      result: "SPOTIFY_AUTOPLAY_SETTING_REQUIRED",
      reason: "owner confirmed Autoplay is disabled in Spotify account/device settings; enable it and retry",
    };
  }

  return {
    result: "SPOTIFY_AUTOPLAY_NOT_OBSERVED",
    reason: "no next_tracks pre-exposure and no automatic continuation observed within the capture window",
  };
}
