/**
 * Shared opaque-token privacy primitive (P0-M6-R2 repair, Blocker 7).
 * No fetch, no DOM. `spotify-autoplay.js`'s `sanitizeTrackToken` and this
 * module's `sanitizeDeviceToken` both hash through the same
 * deterministic, synchronous, non-cryptographic FNV-1a 32-bit function --
 * kept here once so track and device identifiers are sanitized
 * identically instead of two independently-maintained implementations.
 * NOT a security primitive.
 */
export function fnv1aHex(input) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

/**
 * Blocker 7: device lifecycle events (`device_ready`, `device_activated`)
 * must never emit a raw Spotify Connect `device_id` into tracked
 * evidence/debug output. This produces a stable, opaque, per-session
 * token for the same device_id instead.
 */
export function sanitizeDeviceToken(deviceId) {
  if (!deviceId) return null;
  return `DEV_${fnv1aHex(String(deviceId))}`;
}
