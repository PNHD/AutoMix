import { PlaybackAdapter, Capability } from "./PlaybackAdapter.js";

/**
 * SpotifyDJPartnerPlaybackAdapter -- Lane S2 stub (Issue #11 PM comments
 * 5323227813 / 5323231023).
 *
 * As of this task's research (docs/research/P0-M6-R1-SPOTIFY-COMPETITIVE-
 * BASELINE.md), the real-time multi-track Spotify catalog mixing that
 * djay/rekordbox/Serato ship is a licensed partner integration
 * (Spotify newsroom, 2025-09-24 / 2025-12-11), not something reachable
 * through the ordinary public Client ID / Web API / Web Playback SDK --
 * Spotify's own developer policy (Section III.7) explicitly forbids an
 * ordinary app from segueing/mixing/overlapping Spotify Content, and no
 * public application process or SDK for the DJ-partner entitlement was
 * found on developer.spotify.com.
 *
 * Per AGENTS.md rule 6 ("Treat public API policy and licensed-partner
 * capabilities as different things. Do not infer public access from
 * capabilities available only to approved partners.") and rule 7
 * ("If a required capability is blocked by API policy or DRM, document
 * the blocker and continue with the nearest legal test surface instead
 * of bypassing it."), this adapter is intentionally a documented stub,
 * not a workaround. It exists so the provider-adapter boundary
 * (LocalDSPPlaybackAdapter / SpotifyPublicControlAdapter /
 * SpotifyDJPartnerPlaybackAdapter, all implementing the same
 * PlaybackAdapter interface) is already shaped for the day a genuine
 * partner SDK/entitlement is obtained -- swapping this stub for a real
 * implementation should not require touching the planner, the UI, or
 * either of the other two adapters.
 */
export class SpotifyDJPartnerPlaybackAdapter extends PlaybackAdapter {
  get providerId() {
    return "spotify-dj-partner";
  }

  get capability() {
    return Capability.PARTNER_ACCESS_REQUIRED;
  }

  async connect() {
    return { ok: false, reason: "SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED" };
  }

  isConnected() {
    return false;
  }

  async getAccountReadiness() {
    return { premium: false, ready: false, reason: "SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED" };
  }

  async loadQueue() {
    throw new Error("SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED");
  }

  getQueue() {
    return { current: null, next: null, upcoming: [] };
  }

  getPlaybackState() {
    return { isPlaying: false, positionMs: 0, durationMs: 0, trackId: null };
  }

  async play() {
    throw new Error("SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED");
  }
  async pause() {
    throw new Error("SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED");
  }
  async next() {
    throw new Error("SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED");
  }
  async seek() {
    throw new Error("SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED");
  }

  getAutoMixPlan() {
    return {
      available: false,
      reason: "SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED",
      exitAnchorS: null,
      entryAnchorS: null,
      tempoCorrectionPct: null,
      bassEqHandoff: false,
      beatDownbeatSync: false,
      executesRealDsp: false,
    };
  }

  setAutoMixEnabled() {}

  onStateChange() {
    return () => {};
  }
}
