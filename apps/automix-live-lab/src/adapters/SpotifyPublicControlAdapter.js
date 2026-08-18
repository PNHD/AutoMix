import { PlaybackAdapter, Capability } from "./PlaybackAdapter.js";
import {
  generateCodeVerifier,
  generateCodeChallenge,
  buildAuthorizeUrl,
  exchangeCodeForToken,
  refreshAccessToken,
  SPOTIFY_SCOPES,
} from "./spotify-pkce.js";
import { buildSearchRequest, buildPlaySeedRequest, toSeedCandidate, MAX_SEARCH_LIMIT } from "./spotify-api-requests.js";
import {
  sanitizeTrackToken,
  captureSnapshot,
  classifyAutoplayResult,
  beginManualAction,
  resolveManualAttribution,
  NO_PENDING_MANUAL_ACTION,
} from "./spotify-autoplay.js";

const TOKEN_STORAGE_KEY = "automix_spotify_token_v1";
const VERIFIER_STORAGE_KEY = "automix_spotify_pkce_verifier_v1";
const STATE_STORAGE_KEY = "automix_spotify_pkce_state_v1";
export const CLIENT_ID_STORAGE_KEY = "automix_spotify_client_id_v1";

/**
 * SpotifyPublicControlAdapter -- Lane S1 (Issue #11 PM comments
 * 5323227813 / 5323231023 / 5323258040 / 5324307503 / 5324583196).
 *
 * REPAIR PASS 2 (`5324583196`, `P0_M6_R1_SEED_IDENTITY_REPAIR_REQUIRED`):
 * `playSeedTrack(uri)` hashed the full `spotify:track:<id>` URI while
 * `_onPlayerStateChanged` hashed the SDK's bare `<id>` -- two different
 * strings for the same song, so `_seedPlaybackConfirmed` could never
 * become true and the seed's own first playback could be misclassified
 * as a non-seed continuation. Fixed at the single source: `sanitizeTrackToken`
 * (spotify-autoplay.js) now canonicalizes id-vs-uri before hashing, so
 * every call site is automatically consistent (BLOCKER 1). Separately,
 * the manual-next/seek attribution boolean cleared on the FIRST
 * `player_state_changed` event after the call even if that event still
 * showed the same track, letting a later, still-manually-caused track
 * change get misclassified as Autoplay; replaced with a small state
 * machine (`beginManualAction`/`resolveManualAttribution`) that stays
 * attributed across same-track intermediate events and resolves only on
 * an actual track change or a fixed bounded timeout (BLOCKER 2).
 *
 * REPAIR PASS 1 (`5324307503`, `P0_M6_R1_SPOTIFY_SEED_LOOP_REPAIR_REQUIRED`):
 * the prior pass centered `/me/playlists` and existing-playback resume.
 * The actual product loop is: search ONE arbitrary track -> play that ONE
 * track as a seed (`PUT /me/player/play` with a single-track `uris`
 * array, never a playlist context) -> observe whether Spotify's own
 * Autoplay supplies a continuation via the Web Playback SDK's
 * `track_window.next_tracks`. No playlist call is made anywhere in this
 * file anymore (BLOCKER 1). Premium/readiness no longer depends on
 * `GET /me` -> `product`, which Spotify's Feb-2026 Development Mode
 * migration can omit for affected apps (BLOCKER 3) -- readiness is
 * derived purely from Web Playback SDK `ready`/`account_error`/auth-error
 * events plus actual confirmed seed playback.
 *
 * Capability is ALWAYS `PUBLIC_CONTROL_ONLY` in this adapter. It never
 * claims to execute real AutoMix DSP against Spotify audio: per the PM
 * direction, Spotify's public Web Playback SDK/Web API must not be used
 * to segue/mix/overlap Spotify Content
 * (https://developer.spotify.com/policy, Section III.7), and new-app
 * Client IDs no longer get Audio Features/Audio Analysis
 * (tempo/key/section data) at all -- Spotify deprecated those endpoints
 * for new apps 2024-11-27. `getAutoMixPlan()` here is ADVISORY ONLY: it
 * shows what a transition WOULD look like using only the metadata public
 * apps can still read (duration/progress), and explicitly reports
 * `executesRealDsp: false`. The Recommendations endpoint is never used
 * (deprecated for new Development Mode Client IDs; BLOCKER 2 explicitly
 * forbids fabricating recommendations ourselves).
 *
 * Auth: Authorization Code with PKCE, fully client-side (no client
 * secret is ever requested or stored) -- see spotify-pkce.js.
 */
export class SpotifyPublicControlAdapter extends PlaybackAdapter {
  constructor({ clientId, redirectUri }) {
    super();
    this._clientIdFallback = clientId || "";
    this._redirectUri = redirectUri;
    this._token = null; // { access_token, expires_at_ms, refresh_token }
    this._player = null; // Spotify.Player instance (Web Playback SDK)
    this._deviceId = null;
    this._latestState = null;
    this._listeners = new Set();
    this._connected = false;

    // BLOCKER 3: readiness state machine, no `/me`.product dependency.
    this._sdkReady = false;
    this._sdkAccountError = null;
    this._sdkAuthError = null;
    this._seedPlaybackConfirmed = false;

    // BLOCKER 2: seed/autoplay observability.
    this._seedUri = null;
    this._seedToken = null;
    this._autoplaySnapshots = [];
    // Repair (`5324583196`, BLOCKER 2): a manual next()/seek() stays
    // attributed across same-track intermediate `player_state_changed`
    // events, resolving only when the current track actually changes (or
    // a bounded timeout expires) -- see resolveManualAttribution().
    this._manualAction = NO_PENDING_MANUAL_ACTION;
  }

  /**
   * Always reads localStorage live rather than a value captured at
   * construction time -- the Client ID input can be saved AFTER this
   * adapter is instantiated (e.g. while its own setup panel is open),
   * and a captured-once value would silently ignore that save.
   */
  get _clientId() {
    try {
      return localStorage.getItem(CLIENT_ID_STORAGE_KEY) || this._clientIdFallback || "";
    } catch {
      return this._clientIdFallback || "";
    }
  }

  get providerId() {
    return "spotify-public";
  }

  get capability() {
    return Capability.PUBLIC_CONTROL_ONLY;
  }

  _loadStoredToken() {
    try {
      const raw = localStorage.getItem(TOKEN_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  _storeToken(tok) {
    this._token = tok;
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tok));
  }

  /**
   * Step 1 of PKCE: redirect the browser to Spotify's authorize page.
   * Call this from a user gesture (button click).
   */
  async beginLogin() {
    if (!this._clientId) throw new Error("SPOTIFY_CLIENT_ID_NOT_CONFIGURED");
    const verifier = generateCodeVerifier();
    const challenge = await generateCodeChallenge(verifier);
    const state = generateCodeVerifier(16);
    sessionStorage.setItem(VERIFIER_STORAGE_KEY, verifier);
    sessionStorage.setItem(STATE_STORAGE_KEY, state);
    const url = buildAuthorizeUrl({
      clientId: this._clientId,
      redirectUri: this._redirectUri,
      scopes: SPOTIFY_SCOPES,
      codeChallenge: challenge,
      state,
    });
    window.location.assign(url);
  }

  /**
   * Step 2 of PKCE: call this on page load. If the URL carries
   * ?code=...&state=..., completes the token exchange and cleans the URL.
   * Returns true if a fresh login was just completed.
   */
  async completeLoginIfRedirected() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const returnedState = params.get("state");
    const error = params.get("error");
    if (error) throw new Error(`SPOTIFY_AUTH_ERROR: ${error}`);
    if (!code) return false;

    const expectedState = sessionStorage.getItem(STATE_STORAGE_KEY);
    if (!expectedState || returnedState !== expectedState) {
      throw new Error("SPOTIFY_AUTH_STATE_MISMATCH");
    }
    const verifier = sessionStorage.getItem(VERIFIER_STORAGE_KEY);
    if (!verifier) throw new Error("SPOTIFY_AUTH_MISSING_CODE_VERIFIER");

    const tokenResp = await exchangeCodeForToken({
      clientId: this._clientId,
      redirectUri: this._redirectUri,
      code,
      codeVerifier: verifier,
    });
    this._storeToken({
      access_token: tokenResp.access_token,
      refresh_token: tokenResp.refresh_token,
      expires_at_ms: Date.now() + tokenResp.expires_in * 1000,
    });
    sessionStorage.removeItem(VERIFIER_STORAGE_KEY);
    sessionStorage.removeItem(STATE_STORAGE_KEY);
    window.history.replaceState({}, "", window.location.pathname);
    return true;
  }

  async _ensureFreshToken() {
    if (!this._token) this._token = this._loadStoredToken();
    if (!this._token) throw new Error("SPOTIFY_NOT_AUTHENTICATED");
    if (Date.now() > this._token.expires_at_ms - 30_000) {
      const refreshed = await refreshAccessToken({ clientId: this._clientId, refreshToken: this._token.refresh_token });
      this._storeToken({
        access_token: refreshed.access_token,
        refresh_token: refreshed.refresh_token || this._token.refresh_token,
        expires_at_ms: Date.now() + refreshed.expires_in * 1000,
      });
    }
    return this._token.access_token;
  }

  async _api(path, opts = {}) {
    const token = await this._ensureFreshToken();
    const res = await fetch(`https://api.spotify.com/v1${path}`, {
      ...opts,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(opts.headers || {}) },
    });
    if (res.status === 204) return null;
    if (!res.ok) throw new Error(`SPOTIFY_API_ERROR: ${opts.method || "GET"} ${path} -> ${res.status}`);
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  }

  async connect() {
    this._token = this._loadStoredToken();
    if (!this._token) {
      return { ok: false, reason: "NOT_AUTHENTICATED_CALL_beginLogin" };
    }
    try {
      await this._ensureFreshToken();
    } catch (e) {
      return { ok: false, reason: `TOKEN_REFRESH_FAILED: ${e.message}` };
    }
    await this._initWebPlaybackSdk();
    this._connected = true;
    return { ok: true, reason: "AUTHENTICATED" };
  }

  isConnected() {
    return this._connected;
  }

  /**
   * BLOCKER 3 repair: no `GET /me` -> `product` dependency (removed for
   * affected apps by Spotify's Feb-2026 Development Mode migration, which
   * could make this adapter falsely report a Premium account as
   * unknown/non-Premium). Readiness is derived entirely from Web Playback
   * SDK signals plus actual confirmed seed playback:
   *   - `PREMIUM_PLAYBACK_CONFIRMED_BY_SDK` only once the SDK device is
   *     `ready` AND a seed track has actually started playing;
   *   - the exact SDK `account_error`/auth-error message otherwise, never
   *     a fabricated tier;
   *   - `SDK_READY_AWAITING_SEED_PLAYBACK_PROOF` once the device is
   *     registered but no seed has been confirmed playing yet;
   *   - `SDK_NOT_READY` before device registration completes.
   */
  async getAccountReadiness() {
    if (this._seedPlaybackConfirmed) {
      return { premium: true, ready: true, reason: "PREMIUM_PLAYBACK_CONFIRMED_BY_SDK" };
    }
    if (this._sdkAccountError) {
      return { premium: false, ready: false, reason: `ACCOUNT_ERROR: ${this._sdkAccountError}` };
    }
    if (this._sdkAuthError) {
      return { premium: false, ready: false, reason: `AUTH_ERROR: ${this._sdkAuthError}` };
    }
    if (this._sdkReady) {
      return { premium: null, ready: false, reason: "SDK_READY_AWAITING_SEED_PLAYBACK_PROOF" };
    }
    return { premium: null, ready: false, reason: "SDK_NOT_READY" };
  }

  async _initWebPlaybackSdk() {
    if (window.Spotify) return this._registerPlayer();
    await new Promise((resolve, reject) => {
      window.onSpotifyWebPlaybackSDKReady = () => resolve();
      const script = document.createElement("script");
      script.src = "https://sdk.scdn.co/spotify-player.js";
      script.onerror = () => reject(new Error("SPOTIFY_SDK_LOAD_FAILED"));
      document.head.appendChild(script);
      setTimeout(() => reject(new Error("SPOTIFY_SDK_LOAD_TIMEOUT")), 15000);
    });
    await this._registerPlayer();
  }

  async _registerPlayer() {
    const token = await this._ensureFreshToken();
    this._player = new window.Spotify.Player({
      name: "AutoMix Live Lab (PUBLIC_CONTROL_ONLY)",
      getOAuthToken: (cb) => cb(token),
      volume: 0.8,
    });
    this._player.addListener("ready", ({ device_id }) => {
      this._deviceId = device_id;
      this._sdkReady = true;
      this._emit({ type: "device_ready", deviceId: device_id });
    });
    this._player.addListener("player_state_changed", (state) => {
      this._latestState = state;
      this._onPlayerStateChanged(state);
      this._emit({ type: "state_changed", state });
    });
    this._player.addListener("initialization_error", ({ message }) => {
      this._emit({ type: "sdk_error", stage: "initialization_error", message });
    });
    this._player.addListener("authentication_error", ({ message }) => {
      this._sdkAuthError = message;
      this._emit({ type: "sdk_error", stage: "authentication_error", message });
    });
    this._player.addListener("account_error", ({ message }) => {
      this._sdkAccountError = `${message} (Web Playback SDK requires Spotify Premium)`;
      this._emit({ type: "sdk_error", stage: "account_error", message: this._sdkAccountError });
    });
    await this._player.connect();
  }

  /**
   * BLOCKER 2: instrumentation point. Every real `player_state_changed`
   * event is turned into a sanitized snapshot (opaque tokens only) and
   * appended to `_autoplaySnapshots`. If the currently-playing track is
   * the seed and this is the first time we see actual playback of it,
   * that also confirms Premium playback readiness (BLOCKER 3).
   */
  _onPlayerStateChanged(state) {
    if (!this._seedToken) return; // no seed selected yet -- nothing to instrument
    const currentTrack = state?.track_window?.current_track;
    // BLOCKER 1 repair: sanitizeTrackToken now canonicalizes id vs uri
    // internally, so this comparison correctly matches a URI-selected seed
    // against the SDK's bare-id current_track -- no separate parsing here.
    const currentToken = currentTrack ? sanitizeTrackToken(currentTrack.id) : null;
    if (!this._seedPlaybackConfirmed && currentToken === this._seedToken && !state.paused) {
      this._seedPlaybackConfirmed = true;
      this._emit({ type: "seed_playback_confirmed", seedToken: this._seedToken });
    }

    const now = Date.now();
    const { manuallyTriggered, nextState } = resolveManualAttribution(this._manualAction, currentToken, now);
    this._manualAction = nextState;

    const snapshot = captureSnapshot({
      state,
      seedToken: this._seedToken,
      capturedAtMs: now,
      manuallyTriggered,
    });
    this._autoplaySnapshots.push(snapshot);
    this._emit({ type: "autoplay_snapshot", snapshot });
  }

  /**
   * BLOCKER 1: `GET /search?type=track`, Development Mode limit clamped
   * to <=10. Returns UI-facing candidates (title/artist ARE needed here
   * so the owner can actually pick a song -- this is ephemeral runtime
   * UI state, never written to tracked evidence; tracked snapshots use
   * `spotify-autoplay.js`'s opaque tokens instead, see `_onPlayerStateChanged`).
   */
  async searchTracks(query, limit = MAX_SEARCH_LIMIT) {
    const req = buildSearchRequest(query, limit);
    const resp = await this._api(req.url);
    const items = resp?.tracks?.items ?? [];
    return items.map(toSeedCandidate);
  }

  /**
   * BLOCKER 1: plays exactly ONE seed track on the SDK's own device.
   * Never a playlist context, never more than one uri.
   */
  async playSeedTrack(uri) {
    if (!this._deviceId) throw new Error("SPOTIFY_DEVICE_NOT_READY");
    const req = buildPlaySeedRequest(this._deviceId, uri);
    await this._api(req.url, { method: req.method, body: JSON.stringify(req.body) });
    this._seedUri = uri;
    this._seedToken = sanitizeTrackToken(uri);
    this._autoplaySnapshots = [];
    this._seedPlaybackConfirmed = false;
    this._emit({ type: "seed_track_played", seedToken: this._seedToken });
  }

  /** Current Autoplay-observability classification from snapshots captured so far (BLOCKER 2). */
  getAutoplayClassification(opts) {
    return classifyAutoplayResult(this._autoplaySnapshots, opts);
  }

  getQueue() {
    const s = this._latestState;
    const toTrack = (t) =>
      t && { trackId: t.id, title: t.name, artist: (t.artists || []).map((a) => a.name).join(", "), durationMs: t.duration_ms };
    if (!s) return { current: null, next: null, upcoming: [] };
    const upcoming = (s.track_window?.next_tracks || []).map(toTrack);
    return {
      current: toTrack(s.track_window?.current_track),
      next: upcoming[0] || null,
      upcoming,
    };
  }

  getPlaybackState() {
    const s = this._latestState;
    if (!s) return { isPlaying: false, positionMs: 0, durationMs: 0, trackId: null };
    return {
      isPlaying: !s.paused,
      positionMs: s.position,
      durationMs: s.duration,
      trackId: s.track_window?.current_track?.id ?? null,
    };
  }

  async play() {
    if (this._deviceId) await this._api(`/me/player/play?device_id=${this._deviceId}`, { method: "PUT" });
    else await this._player?.resume();
  }

  async pause() {
    await this._player?.pause();
  }

  /** Token of whatever the SDK currently reports as playing, right before a manual action -- the manual-attribution baseline. */
  _currentTokenFromLatestState() {
    const t = this._latestState?.track_window?.current_track;
    return t ? sanitizeTrackToken(t.id) : null;
  }

  async next() {
    this._manualAction = beginManualAction(Date.now(), this._currentTokenFromLatestState());
    await this._player?.nextTrack();
  }

  async seek(ms) {
    this._manualAction = beginManualAction(Date.now(), this._currentTokenFromLatestState());
    await this._player?.seek(ms);
  }

  /**
   * ADVISORY ONLY. Uses only metadata a public/new Client ID can still
   * read post-2024-11-27 (track duration + live playback progress).
   * Audio Features / Audio Analysis (tempo, key, section boundaries) are
   * NOT available to new Spotify apps -- see
   * docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md. This method
   * therefore always returns `executesRealDsp: false` and never touches
   * Spotify playback beyond what play/pause/next/seek already do.
   */
  getAutoMixPlan() {
    const q = this.getQueue();
    const state = this.getPlaybackState();
    if (!q.current) {
      return {
        available: false,
        reason: "NO_ACTIVE_SPOTIFY_PLAYBACK",
        exitAnchorS: null,
        entryAnchorS: null,
        tempoCorrectionPct: null,
        bassEqHandoff: false,
        beatDownbeatSync: false,
        executesRealDsp: false,
      };
    }
    const remainingS = Math.max(0, (state.durationMs - state.positionMs) / 1000);
    return {
      available: true,
      reason: "ADVISORY_ONLY_NO_TEMPO_KEY_DATA_AVAILABLE_TO_PUBLIC_APPS",
      exitAnchorS: Math.max(0, state.durationMs / 1000 - Math.min(8, remainingS)), // naive last-8s heuristic, no beat data
      entryAnchorS: 0,
      tempoCorrectionPct: null, // genuinely unknown -- Audio Features not available
      bassEqHandoff: false,
      beatDownbeatSync: false,
      executesRealDsp: false,
    };
  }

  setAutoMixEnabled() {
    // No-op beyond UI state: PUBLIC_CONTROL_ONLY never executes DSP regardless.
  }

  onStateChange(cb) {
    this._listeners.add(cb);
    return () => this._listeners.delete(cb);
  }

  _emit(evt) {
    for (const cb of this._listeners) cb(evt);
  }
}
