/**
 * PlaybackAdapter -- provider-independent playback interface.
 *
 * AGENTS.md rule 5: "Provider integrations must be isolated behind
 * adapters. The AutoMix analysis/planning/DSP core must not depend on
 * Spotify, Apple Music, YouTube Music, or another provider."
 *
 * This is the ONLY contract the UI (src/app.js) and the AutoMix planner
 * are allowed to call. Concrete adapters (LocalDSPPlaybackAdapter,
 * SpotifyPublicControlAdapter, SpotifyDJPartnerPlaybackAdapter) implement
 * it; the UI never imports a provider-specific module directly except to
 * instantiate it once at startup.
 *
 * Capability values (must be one of):
 *   - "LOCAL_DSP_FULL"        -- full two-deck DSP control, local audio.
 *   - "PUBLIC_CONTROL_ONLY"   -- provider playback/queue control only, no
 *                                raw audio access, no true crossfade DSP.
 *   - "PARTNER_ACCESS_REQUIRED" -- capability exists in principle but is
 *                                gated behind a licensed partner SDK this
 *                                app does not (and per AGENTS.md rule 6,
 *                                must not attempt to) hold.
 */

export const Capability = Object.freeze({
  LOCAL_DSP_FULL: "LOCAL_DSP_FULL",
  PUBLIC_CONTROL_ONLY: "PUBLIC_CONTROL_ONLY",
  PARTNER_ACCESS_REQUIRED: "PARTNER_ACCESS_REQUIRED",
});

/** @typedef {{trackId: string, title: string, artist: string, durationMs: number}} TrackInfo */
/** @typedef {{current: TrackInfo|null, next: TrackInfo|null, upcoming: TrackInfo[]}} QueueState */
/** @typedef {{isPlaying: boolean, positionMs: number, durationMs: number, trackId: string|null}} PlaybackState */
/**
 * @typedef {{
 *   available: boolean,
 *   reason: string,
 *   exitAnchorS: number|null,
 *   entryAnchorS: number|null,
 *   tempoCorrectionPct: number|null,
 *   bassEqHandoff: boolean,
 *   beatDownbeatSync: boolean,
 *   executesRealDsp: boolean
 * }} TransitionPlan
 */

export class PlaybackAdapter {
  /** @returns {string} stable id, e.g. "local-dsp", "spotify-public", "spotify-dj-partner" */
  get providerId() {
    throw new Error("NOT_IMPLEMENTED: providerId");
  }

  /** @returns {string} one of Capability */
  get capability() {
    throw new Error("NOT_IMPLEMENTED: capability");
  }

  /** @returns {Promise<{ok: boolean, reason: string}>} */
  async connect() {
    throw new Error("NOT_IMPLEMENTED: connect");
  }

  /** @returns {boolean} */
  isConnected() {
    throw new Error("NOT_IMPLEMENTED: isConnected");
  }

  /** @returns {Promise<{premium: boolean, ready: boolean, reason: string}>} */
  async getAccountReadiness() {
    throw new Error("NOT_IMPLEMENTED: getAccountReadiness");
  }

  /** @returns {Promise<void>} */
  async loadQueue() {
    throw new Error("NOT_IMPLEMENTED: loadQueue");
  }

  /** @returns {QueueState} */
  getQueue() {
    throw new Error("NOT_IMPLEMENTED: getQueue");
  }

  /** @returns {PlaybackState} */
  getPlaybackState() {
    throw new Error("NOT_IMPLEMENTED: getPlaybackState");
  }

  /** @returns {Promise<void>} */
  async play() {
    throw new Error("NOT_IMPLEMENTED: play");
  }

  /** @returns {Promise<void>} */
  async pause() {
    throw new Error("NOT_IMPLEMENTED: pause");
  }

  /** @returns {Promise<void>} */
  async next() {
    throw new Error("NOT_IMPLEMENTED: next");
  }

  /** @param {number} ms @returns {Promise<void>} */
  async seek(_ms) {
    throw new Error("NOT_IMPLEMENTED: seek");
  }

  /** @returns {TransitionPlan} the transition the AutoMix planner would run/is running next */
  getAutoMixPlan() {
    throw new Error("NOT_IMPLEMENTED: getAutoMixPlan");
  }

  /** @param {boolean} enabled */
  setAutoMixEnabled(_enabled) {
    throw new Error("NOT_IMPLEMENTED: setAutoMixEnabled");
  }

  /** @param {(evt: {type: string, detail?: any}) => void} cb @returns {() => void} unsubscribe */
  onStateChange(_cb) {
    throw new Error("NOT_IMPLEMENTED: onStateChange");
  }
}
