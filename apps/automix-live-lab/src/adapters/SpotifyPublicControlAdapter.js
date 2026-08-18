import { PlaybackAdapter, Capability } from "./PlaybackAdapter.js";
import {
  generateCodeVerifier,
  generateCodeChallenge,
  buildAuthorizeUrl,
  exchangeCodeForToken,
  refreshAccessToken,
  SPOTIFY_SCOPES,
} from "./spotify-pkce.js";
import {
  buildSearchRequest,
  buildPlaySeedRequest,
  buildTransferPlaybackRequest,
  buildGetQueueRequest,
  buildQueueTrackRequest,
  buildTopTracksRequest,
  buildRecentlyPlayedRequest,
  toSeedCandidate,
  MAX_SEARCH_LIMIT,
} from "./spotify-api-requests.js";
import { deriveQueueTruth, isNextControlEnabled, nextControlState, describePlayAtNaturalEnd, NO_QUEUED_NEXT_TRACK, EMPTY_QUEUE_TRUTH } from "./spotify-queue-truth.js";
import {
  sanitizeTrackToken,
  captureSnapshot,
  classifyAutoplayResult,
  beginManualAction,
  resolveManualAttribution,
  NO_PENDING_MANUAL_ACTION,
} from "./spotify-autoplay.js";
import { clampSeekTargetMs, computeNearEndProbeTargetMs } from "./spotify-seek.js";
import { parseSpotifyApiResponse, SpotifyApiError } from "./spotify-api-response.js";
import { candidatesFromTopTracks, candidatesFromRecentlyPlayed, candidatesFromSearch, assembleCandidatePool, needsSearchFallback } from "./spotify-candidate-pool.js";
import { selectNextTrack } from "./spotify-planner.js";
import { LookaheadQueueController, QueueState } from "./spotify-lookahead-queue.js";

// P0-M6-R2 Phase D: how many of the most-recently-auto-played tracks (in
// this AutoMix session) stay in the recent-repeat exclusion window, on
// top of the unconditional "already played this session" exclusion.
// Currently equal to the full session history -- kept as a separate,
// named constant because the planner treats "recent repeat" and
// "already played this session" as two distinct hard-exclusion reasons.
const RECENT_REPEAT_WINDOW_SIZE = 20;

const TOKEN_STORAGE_KEY = "automix_spotify_token_v1";
const VERIFIER_STORAGE_KEY = "automix_spotify_pkce_verifier_v1";
const STATE_STORAGE_KEY = "automix_spotify_pkce_state_v1";
export const CLIENT_ID_STORAGE_KEY = "automix_spotify_client_id_v1";

/**
 * SpotifyPublicControlAdapter -- Lane S1 (Issue #11 PM comments
 * 5323227813 / 5323231023 / 5323258040 / 5324307503 / 5324583196 /
 * 5324756494, plus two runtime fixes found during real owner validation).
 *
 * NEAR-END PROBE (owner live-testing follow-up): the first real owner run
 * completed a full song and correctly classified
 * `SPOTIFY_AUTOPLAY_NOT_OBSERVED`. To make repeat validation passes fast
 * (no full-length replay needed), added a progress slider + "Jump to last
 * 15s" probe (`startNearEndProbe()`, spotify-seek.js). Section B of that
 * request is load-bearing: `seek()` was refactored to NEVER create
 * pending manual-track-change attribution the way `next()` does -- a
 * manual seek only emits a sanitized `manual_seek` diagnostic event, so
 * whatever Spotify does naturally after the seek (continue automatically,
 * or just stop) is judged as genuine, unsuppressed Autoplay evidence.
 * `startNearEndProbe()` preserves `_seedToken`/`_seedObserved` (the seed
 * never changes, only its playback position does) and archives+clears
 * only `_autoplaySnapshots` (the array `classifyAutoplayResult` reads),
 * so a fresh probe never inherits evidence from the pre-probe window.
 *
 * RUNTIME FIX (owner live-testing, not a PM comment): the real Spotify
 * API returned `404` from `PUT /me/player/play?device_id=<sdk device>`
 * on the very first seed play attempt, even with a valid `ready`
 * device_id. Root cause: a freshly-connected Web Playback SDK device is
 * registered with Spotify Connect but is NOT automatically the *active*
 * device -- the official flow (Web Playback SDK Getting Started /
 * Transfer Playback docs) requires `PUT /me/player` (Transfer Playback)
 * to that device_id before Start/Resume Playback will accept it. Fixed
 * with `_ensureDeviceActive()` (idempotent per device_id), called before
 * the seed's `PUT /me/player/play`. Uses the SAME `user-modify-playback-
 * state` scope already requested -- no scope broadening.
 *
 * REPAIR PASS 3 (`5324756494`, `P0_M6_R1_PREAUTH_RACE_REPAIR_REQUIRED`):
 * immediately after `playSeedTrack()`, the Web Playback SDK can still
 * emit one stale `player_state_changed` event for whatever was playing
 * BEFORE the seed, before it emits the seed's own state. The prior pass
 * fixed identity (BLOCKER 1) but that stale non-seed event could still be
 * accepted as continuation evidence before the seed had ever even been
 * observed as current once. Repaired with a small phase/epoch: every
 * `playSeedTrack()` call enters `AWAITING_SEED_OBSERVATION`
 * (`_seedObserved = false`); any SDK event in that phase whose current
 * track is NOT the seed is tagged `beforeSeedObserved: true` and is
 * mechanically excluded from `_autoplaySnapshots` (and, defense-in-depth,
 * from `classifyAutoplayResult` itself even if a caller included it
 * anyway -- see spotify-autoplay.js). The event where the seed first
 * becomes current transitions the adapter into `SEED_ACTIVE`
 * (`_seedObserved = true`); only events from that point on can count as
 * pre-exposure or continuation evidence, exactly as before this repair.
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
    this._deviceActivated = false; // Transfer Playback runtime fix -- see _ensureDeviceActive()
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
    // Near-end probe (Section C): each startNearEndProbe() archives the
    // pre-probe _autoplaySnapshots here (diagnostic-only, never fed to
    // classifyAutoplayResult) before clearing the live array.
    this._preProbeSnapshotsArchive = [];
    // Repair (`5324756494`, pre-auth race): AWAITING_SEED_OBSERVATION
    // until the SDK reports the seed itself as current at least once,
    // then SEED_ACTIVE. See _onPlayerStateChanged/playSeedTrack.
    this._seedObserved = false;
    // Repair (`5324583196`, BLOCKER 2): a manual next() stays attributed
    // across same-track intermediate `player_state_changed` events,
    // resolving only when the current track actually changes (or a
    // bounded timeout expires) -- see resolveManualAttribution(). Manual
    // Seek deliberately does NOT use this mechanism (Section B) -- see
    // seek() below.
    this._manualAction = NO_PENDING_MANUAL_ACTION;

    // P0-M6-R2 Phase B: last-known real-queue truth from
    // GET /me/player/queue (see getRealQueueTruth()). null until the
    // first successful poll; the Next control and Play-at-natural-end
    // messaging must never claim a successor exists before this is known.
    this._lastQueueTruth = null;

    // P0-M6-R2 Phases C/D/E: app-controlled continuation queue state.
    // Reset per seed (see playSeedTrack()) -- this is per-AutoMix-session
    // state, not persisted across seeds.
    this._sessionPlayedIds = []; // raw track ids observed as current this session (seed + every confirmed successor)
    this._usedArtistIds = []; // primary artist ids of every track observed as current this session
    this._lastCandidatePoolSize = 0;
    this._lastCandidatePoolBreakdown = { topCount: 0, recentCount: 0, searchFallbackUsed: false };
    this._lastSelectionResult = null; // most recent selectNextTrack() result (see runLookaheadCycle())
    this._lookaheadController = null; // created lazily on the first runLookaheadCycle() call for this seed
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

  /**
   * P0-M6-R2 Phase A repair: response handling is delegated entirely to
   * `parseSpotifyApiResponse` (spotify-api-response.js) so every
   * successful-but-non-JSON shape (204, empty 200, plain-text 200 --
   * common for Player write endpoints) is an explicit branch instead of
   * one unconditional `JSON.parse(text)` that threw `Unexpected token ...
   * is not valid JSON` on the real live API. Never includes the token or
   * the query string (only `path`) in a thrown error.
   */
  async _api(path, opts = {}) {
    const token = await this._ensureFreshToken();
    const res = await fetch(`https://api.spotify.com/v1${path}`, {
      ...opts,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(opts.headers || {}) },
    });
    const parsed = await parseSpotifyApiResponse(res);
    if (!parsed.ok) {
      throw new SpotifyApiError({ method: opts.method || "GET", path, status: parsed.status, body: parsed.body, bodyType: parsed.bodyType });
    }
    return parsed.body;
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
      this._deviceActivated = false; // a (re)connect gets a fresh device_id -- must transfer again
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
   * event is turned into a sanitized snapshot (opaque tokens only). If
   * the currently-playing track is the seed and this is the first time
   * we see actual playback of it, that also confirms Premium playback
   * readiness (BLOCKER 3).
   *
   * Pre-auth race repair (`5324756494`): while still
   * `AWAITING_SEED_OBSERVATION` (`!_seedObserved`), any event whose
   * current track is NOT the seed is a stale leftover from whatever was
   * playing before `playSeedTrack()` -- it is captured for diagnostics
   * (emitted, never silently dropped) but NOT appended to
   * `_autoplaySnapshots`, so it can never feed `classifyAutoplayResult`.
   * The event where the seed first becomes current flips the adapter
   * into `SEED_ACTIVE` and is processed normally from then on.
   */
  _onPlayerStateChanged(state) {
    if (!this._seedToken) return; // no seed selected yet -- nothing to instrument
    const currentTrack = state?.track_window?.current_track;
    // BLOCKER 1 repair: sanitizeTrackToken now canonicalizes id vs uri
    // internally, so this comparison correctly matches a URI-selected seed
    // against the SDK's bare-id current_track -- no separate parsing here.
    const currentToken = currentTrack ? sanitizeTrackToken(currentTrack.id) : null;

    const wasSeedObservedBefore = this._seedObserved;
    if (!this._seedObserved && currentToken === this._seedToken) {
      this._seedObserved = true; // AWAITING_SEED_OBSERVATION -> SEED_ACTIVE
    }
    const isStalePreSeedEvent = !wasSeedObservedBefore && currentToken !== this._seedToken;

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
      beforeSeedObserved: isStalePreSeedEvent,
    });

    if (isStalePreSeedEvent) {
      this._emit({ type: "pre_seed_diagnostic_snapshot", snapshot });
      return; // never enters _autoplaySnapshots / Autoplay classification evidence
    }
    this._autoplaySnapshots.push(snapshot);
    this._emit({ type: "autoplay_snapshot", snapshot });

    // P0-M6-R2 Phase E: every genuine (non-stale) current-track
    // observation is fed to the lookahead controller. The controller
    // itself is the single source of idempotency (a repeat observation
    // of the same current track is a no-op there, see
    // spotify-lookahead-queue.js's onTrackAdvanced) -- this call site
    // does not need its own duplicate guard. Also grows the session's
    // played-id/used-artist-id history, which the planner's hard
    // exclusions and diversity ranking read on the NEXT cycle.
    if (currentTrack?.id && !this._sessionPlayedIds.includes(currentTrack.id)) {
      this._sessionPlayedIds.push(currentTrack.id);
    }
    const artistId = currentTrack?.artists?.[0]?.id;
    if (artistId && !this._usedArtistIds.includes(artistId)) {
      this._usedArtistIds.push(artistId);
    }
    this._lookaheadController?.onTrackAdvanced(currentToken);
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
   * Transfer Playback runtime fix: a freshly-`ready` Web Playback SDK
   * device is not automatically the *active* Spotify Connect device --
   * `PUT /me/player/play?device_id=...` 404s ("Device not found") until
   * this has been called at least once for the current device_id.
   * Idempotent per device_id (`_deviceActivated`), so repeated seed plays
   * don't re-issue the transfer call every time.
   */
  async _ensureDeviceActive() {
    if (this._deviceActivated) return;
    const req = buildTransferPlaybackRequest(this._deviceId, false);
    await this._api(req.url, { method: req.method, body: JSON.stringify(req.body) });
    this._deviceActivated = true;
    this._emit({ type: "device_activated", deviceId: this._deviceId });
  }

  /**
   * BLOCKER 1: plays exactly ONE seed track on the SDK's own device.
   * Never a playlist context, never more than one uri.
   */
  async playSeedTrack(uri) {
    if (!this._deviceId) throw new Error("SPOTIFY_DEVICE_NOT_READY");
    await this._ensureDeviceActive();
    const req = buildPlaySeedRequest(this._deviceId, uri);
    await this._api(req.url, { method: req.method, body: JSON.stringify(req.body) });
    this._seedUri = uri;
    this._seedToken = sanitizeTrackToken(uri);
    this._autoplaySnapshots = [];
    this._seedPlaybackConfirmed = false;
    this._seedObserved = false; // enter AWAITING_SEED_OBSERVATION for this new seed epoch

    // P0-M6-R2 Phases C/D/E: a new seed starts a fresh AutoMix
    // continuation session -- prior session history/lookahead state must
    // never leak into a different seed's planning.
    this._sessionPlayedIds = [];
    this._usedArtistIds = [];
    this._lastCandidatePoolSize = 0;
    this._lastCandidatePoolBreakdown = { topCount: 0, recentCount: 0, searchFallbackUsed: false };
    this._lastSelectionResult = null;
    this._lookaheadController = null;

    this._emit({ type: "seed_track_played", seedToken: this._seedToken });
  }

  /** Current Autoplay-observability classification from snapshots captured so far (BLOCKER 2). */
  getAutoplayClassification(opts) {
    return classifyAutoplayResult(this._autoplaySnapshots, opts);
  }

  /**
   * P0-M6-R2 Phase C: builds one bounded, deduplicated candidate pool
   * from ONLY the two user-affinity sources plus a bounded `GET /search`
   * fallback (used only when the affinity sources alone are too small,
   * per `needsSearchFallback`). Never calls Recommendations, Audio
   * Features, Audio Analysis, or the deprecated artist-top-tracks
   * endpoint -- see spotify-candidate-pool.js. A source failing (e.g. a
   * transient 500) degrades that source to zero candidates rather than
   * failing the whole pool.
   */
  async _fetchCandidatePool({ fallbackSearchQuery } = {}) {
    const [topRaw, recentRaw] = await Promise.all([
      this._api(buildTopTracksRequest().url).catch(() => null),
      this._api(buildRecentlyPlayedRequest().url).catch(() => null),
    ]);
    const topCandidates = candidatesFromTopTracks(topRaw);
    const recentCandidates = candidatesFromRecentlyPlayed(recentRaw);

    let searchCandidates = [];
    const searchFallbackUsed = needsSearchFallback(topCandidates.length + recentCandidates.length) && !!fallbackSearchQuery;
    if (searchFallbackUsed) {
      try {
        const searchReq = buildSearchRequest(fallbackSearchQuery, MAX_SEARCH_LIMIT);
        const searchRaw = await this._api(searchReq.url);
        searchCandidates = candidatesFromSearch(searchRaw);
      } catch (e) {
        this._emit({ type: "candidate_pool_search_fallback_failed", message: e.message });
        searchCandidates = [];
      }
    }

    const pool = assembleCandidatePool([topCandidates, recentCandidates, searchCandidates]);
    this._lastCandidatePoolSize = pool.length;
    this._lastCandidatePoolBreakdown = { topCount: topCandidates.length, recentCount: recentCandidates.length, searchFallbackUsed: searchCandidates.length > 0 };
    this._emit({ type: "candidate_pool_built", size: pool.length, ...this._lastCandidatePoolBreakdown });
    return pool;
  }

  /**
   * P0-M6-R2 Phase E orchestration: builds the candidate pool (Phase C),
   * runs the planner (Phase D), and enqueues exactly one chosen successor
   * (Phase E) via the one-track lookahead queue state machine. Lazily
   * creates the `LookaheadQueueController` (once per seed -- see
   * playSeedTrack()'s reset) wired to this adapter's own `_api()` (so it
   * automatically inherits the Phase A response-parsing repair) and
   * `getRealQueueTruth()` (Phase B) for confirmation.
   */
  async runLookaheadCycle() {
    if (!this._seedObserved) throw new Error("SEED_NOT_YET_ACTIVE_FOR_LOOKAHEAD");
    if (!this._lookaheadController) {
      this._lookaheadController = new LookaheadQueueController({
        queueTrackFn: async (uri) => {
          const req = buildQueueTrackRequest(uri, this._deviceId);
          await this._api(req.url, { method: req.method });
        },
        verifyQueueFn: async () => (await this.getRealQueueTruth()).tokens,
        selectNextFn: (ctx) => selectNextTrack(ctx),
        onStateChange: (s) => this._emit({ type: "lookahead_state_changed", state: s }),
      });
    }

    const currentTrackRaw = this._latestState?.track_window?.current_track;
    const currentTrack = currentTrackRaw
      ? { id: currentTrackRaw.id, primaryArtistId: currentTrackRaw.artists?.[0]?.id ?? null, durationMs: currentTrackRaw.duration_ms }
      : null;
    const fallbackSearchQuery = currentTrackRaw?.artists?.[0]?.name || null;

    const pool = await this._fetchCandidatePool({ fallbackSearchQuery });
    const result = await this._lookaheadController.selectAndQueueSuccessor({
      candidates: pool,
      currentTrack,
      sessionPlayedIds: this._sessionPlayedIds,
      recentRepeatWindowIds: this._sessionPlayedIds.slice(-RECENT_REPEAT_WINDOW_SIZE),
      usedArtistIdsThisSession: this._usedArtistIds,
    });
    this._lastSelectionResult = result;
    this._emit({ type: "successor_selection_result", token: result.token ?? null, queued: result.queued, reason: result.reason ?? result.selectionReason ?? null });
    return result;
  }

  /** P0-M6-R2 Phase E: confirms the pending successor is actually visible in the real queue (GET /me/player/queue) before trusting it. */
  async confirmLookaheadSuccessor() {
    if (!this._lookaheadController) return { confirmed: false, reason: "NO_LOOKAHEAD_CYCLE_STARTED" };
    return this._lookaheadController.confirmSuccessor();
  }

  /** Sanitized status snapshot for Phase F live-validation UX -- opaque token only, never a raw Spotify id. */
  getLookaheadStatus() {
    const c = this._lookaheadController;
    return {
      state: c?.state ?? null,
      candidatePoolSize: this._lastCandidatePoolSize,
      candidatePoolBreakdown: this._lastCandidatePoolBreakdown,
      selectedToken: this._lastSelectionResult?.token ?? null,
      selectionReason: this._lastSelectionResult?.selectionReason ?? this._lastSelectionResult?.reason ?? null,
      refillCount: c?.refillCount ?? 0,
      consecutiveAutoTrackCount: c?.consecutiveAutoTrackCount ?? 1,
      successorConfirmed: c ? c.state === QueueState.SUCCESSOR_CONFIRMED || c.state === QueueState.SUCCESSOR_BECOMES_CURRENT || c.state === QueueState.SELECTING_NEXT_SUCCESSOR : false,
    };
  }

  /**
   * P0-M6-R2 Phase B: the ONLY truthful source for "does a real queued
   * successor exist" -- `GET /me/player/queue` (requires
   * `user-read-playback-state`). Caches the result on `_lastQueueTruth`
   * so `next()`/UI can consult it synchronously between polls. Never
   * throws on a malformed/empty response -- `deriveQueueTruth` treats
   * that as "no successor" rather than crashing the poll loop.
   */
  async getRealQueueTruth() {
    let raw = null;
    try {
      raw = await this._api(buildGetQueueRequest().url);
    } catch (e) {
      this._emit({ type: "queue_truth_poll_failed", message: e.message });
      raw = null;
    }
    const truth = deriveQueueTruth(raw);
    this._lastQueueTruth = truth;
    this._emit({ type: "queue_truth_updated", queueSize: truth.queueSize, hasQueuedSuccessor: truth.hasQueuedSuccessor });
    return truth;
  }

  /** UI-facing: whether the manual Next control should be enabled right now, per the last known real-queue truth. */
  isNextControlEnabled() {
    return isNextControlEnabled(this._lastQueueTruth || EMPTY_QUEUE_TRUTH);
  }

  /** UI-facing state label ("NEXT_TRACK_QUEUED" | "NO_QUEUED_NEXT_TRACK") -- never implies Next creates a recommendation. */
  getNextControlState() {
    return nextControlState(this._lastQueueTruth || EMPTY_QUEUE_TRUTH);
  }

  /** Truthful description of what Play does right now at natural end (restart same seed vs. advance to a real successor). */
  getPlayAtNaturalEndDescription() {
    return describePlayAtNaturalEnd(this._lastQueueTruth || EMPTY_QUEUE_TRUTH);
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
    if (!s) return { isPlaying: false, positionMs: 0, durationMs: 0, trackId: null, disallowsSeeking: false };
    return {
      isPlaying: !s.paused,
      positionMs: s.position,
      durationMs: s.duration,
      trackId: s.track_window?.current_track?.id ?? null,
      disallowsSeeking: !!s.disallows?.seeking,
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

  /**
   * Manual Next: creates pending track-change attribution (BLOCKER 2,
   * `5324583196`) so the resulting changed current track is correctly
   * judged manual, not Autoplay.
   *
   * P0-M6-R2 Phase B truthfulness gate: once `_lastQueueTruth` has been
   * populated at least once (via `getRealQueueTruth()`) and it shows no
   * real queued successor, this refuses to call the SDK's `nextTrack()`
   * at all -- calling it anyway would either no-op or surface a
   * misleading Spotify-side error, and would falsely suggest Next can
   * conjure a recommendation. Before the first poll (`_lastQueueTruth ===
   * null`) this is permissive, preserving all pre-existing manual-Next
   * attribution tests that never populate queue truth.
   */
  async next() {
    if (this._lastQueueTruth && !this._lastQueueTruth.hasQueuedSuccessor) {
      this._emit({ type: "next_blocked", reason: NO_QUEUED_NEXT_TRACK });
      return { ok: false, reason: NO_QUEUED_NEXT_TRACK };
    }
    this._manualAction = beginManualAction(Date.now(), this._currentTokenFromLatestState(), "next");
    await this._player?.nextTrack();
    return { ok: true };
  }

  /**
   * Manual Seek (Section B, this repair): deliberately does NOT create
   * pending track-change attribution and NEVER touches `_manualAction`.
   * A seek only repositions playback within the SAME track -- it must
   * never cause a LATER, unrelated natural end-of-track change to be
   * misjudged as manual. Only a sanitized `manual_seek` diagnostic event
   * (opaque pre-seek token + numeric positions, no titles) is emitted.
   * Uses the Web Playback SDK's own local `seek()` (the browser device is
   * already active) rather than an extra Web API call. Always clamps via
   * `clampSeekTargetMs` regardless of caller, so the adapter itself
   * guarantees the seek-target invariant.
   */
  async seek(ms) {
    const target = clampSeekTargetMs(ms, this.getPlaybackState().durationMs);
    this._emit({ type: "manual_seek", requestedPositionMs: target, preSeekToken: this._currentTokenFromLatestState(), capturedAtMs: Date.now() });
    await this._player?.seek(target);
    return target;
  }

  /**
   * Near-end Autoplay probe (Section C): jumps the ALREADY-ACTIVE seed to
   * its final ~15s so a repeat owner-validation pass doesn't require
   * replaying a full song. Requires the seed to already be SEED_ACTIVE
   * (`_seedObserved`); preserves `_seedToken`/`_seedObserved`/
   * `_seedPlaybackConfirmed` untouched (same seed, just repositioned).
   * Archives the pre-probe `_autoplaySnapshots` (diagnostic-only, never
   * classified) and starts a fresh, empty evidence window so the new
   * classification can only reflect what happens naturally AFTER this
   * seek. Never calls next() and never queues anything.
   */
  async startNearEndProbe() {
    if (!this._seedObserved) throw new Error("SEED_NOT_YET_ACTIVE_FOR_PROBE");
    const durationMs = this.getPlaybackState().durationMs;
    if (!durationMs || durationMs <= 0) throw new Error("NO_DURATION_KNOWN_FOR_PROBE");
    const targetMs = computeNearEndProbeTargetMs(durationMs);

    this._preProbeSnapshotsArchive.push({ archivedAtMs: Date.now(), snapshots: this._autoplaySnapshots });
    this._autoplaySnapshots = [];
    this._emit({ type: "near_end_probe_started", targetMs, durationMs });

    await this.seek(targetMs);
    return { targetMs, durationMs };
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
