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

/**
 * Deterministic, synchronous, non-cryptographic FNV-1a 32-bit hash. Used
 * only to produce an opaque, stable, non-reversible-in-practice token for
 * a Spotify track id -- NOT a security primitive. Synchronous (unlike
 * Web Crypto's SubtleCrypto) so it can run directly inside the
 * `player_state_changed` event handler without an extra async hop.
 */
export function sanitizeTrackToken(trackId) {
  if (!trackId) return null;
  let hash = 0x811c9dc5;
  for (let i = 0; i < trackId.length; i++) {
    hash ^= trackId.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  const hex = (hash >>> 0).toString(16).padStart(8, "0");
  return `TRK_${hex}`;
}

/**
 * Builds one sanitized snapshot from a raw Web Playback SDK state object
 * (the same shape passed to `player_state_changed`). Only opaque tokens,
 * counts, and numbers are retained -- no title/artist/album text.
 */
export function captureSnapshot({ state, seedToken, capturedAtMs, manuallyTriggered = false }) {
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
 */
export function classifyAutoplayResult(snapshots, { autoplayConfirmedDisabled = false } = {}) {
  if (!Array.isArray(snapshots) || snapshots.length === 0) {
    return { result: "SPOTIFY_AUTOPLAY_NOT_OBSERVED", reason: "NO_SNAPSHOTS_CAPTURED" };
  }
  const seedToken = snapshots[0].seedToken;

  const preExposed = snapshots.some((s) => s.isSeedStillCurrent && s.nextTrackCount > 0);
  if (preExposed) {
    return { result: "SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE", reason: "next_tracks was populated while the seed track was still current" };
  }

  const continuedWithoutManualTrigger = snapshots.find(
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
