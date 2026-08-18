/**
 * Pure, DOM-independent seek math + drag/commit controller for the
 * Spotify Live progress slider and "Jump to last 15s" near-end probe
 * button. No fetch, no DOM -- unit-tested in tools/verify_spotify_seek.mjs
 * without a browser.
 */

// Never seek to the exact last sample -- leaves a 1s trailing guard so a
// committed seek can't land past the end of the track.
export const SEEK_TRAILING_GUARD_MS = 1000;

// The near-end probe targets the final 15s of the track so a repeat
// owner-validation pass doesn't require replaying a full song.
export const NEAR_END_PROBE_WINDOW_MS = 15000;

/** Clamp a requested seek target into `[0, durationMs - SEEK_TRAILING_GUARD_MS]`, safe for any durationMs including 0/negative/short tracks. */
export function clampSeekTargetMs(targetMs, durationMs) {
  if (!Number.isFinite(durationMs) || durationMs <= 0) return 0;
  const maxTarget = Math.max(0, durationMs - SEEK_TRAILING_GUARD_MS);
  const t = Number.isFinite(targetMs) ? targetMs : 0;
  return Math.max(0, Math.min(t, maxTarget));
}

/** "Jump to last 15s" target: max(0, durationMs - 15000), then safely clamped for short tracks via clampSeekTargetMs. */
export function computeNearEndProbeTargetMs(durationMs) {
  const raw = Math.max(0, (Number.isFinite(durationMs) ? durationMs : 0) - NEAR_END_PROBE_WINDOW_MS);
  return clampSeekTargetMs(raw, durationMs);
}

/**
 * The progress slider must stay disabled until all of these hold:
 * SDK ready, a current playable track exists, a positive duration is
 * known, and Spotify hasn't reported `disallows.seeking`.
 */
export function isSeekControlEnabled({ sdkReady, hasCurrentTrack, durationMs, disallowsSeeking }) {
  return !!sdkReady && !!hasCurrentTrack && Number.isFinite(durationMs) && durationMs > 0 && disallowsSeeking !== true;
}

/**
 * DOM-independent drag/commit controller. The caller wires:
 *   - the slider's `input` event (fires continuously while dragging) to
 *     `onDrag(ms)` -- updates the displayed value only, NEVER seeks;
 *   - the slider's `change` event (fires exactly once when the user
 *     releases/commits) to `onCommit(ms)` -- calls `seekFn` exactly once
 *     with the clamped target.
 * `seekFn` is injected so this stays testable without a real adapter.
 */
export function createSeekDragController({ seekFn, getDurationMs }) {
  let displayValueMs = 0;
  let dragging = false;
  return {
    onDragStart(ms) {
      dragging = true;
      displayValueMs = ms;
    },
    onDrag(ms) {
      displayValueMs = ms; // visual only -- never calls seekFn
    },
    onCommit(ms) {
      dragging = false;
      const target = clampSeekTargetMs(ms, getDurationMs());
      displayValueMs = target;
      seekFn(target);
      return target;
    },
    get displayValueMs() {
      return displayValueMs;
    },
    get isDragging() {
      return dragging;
    },
  };
}
