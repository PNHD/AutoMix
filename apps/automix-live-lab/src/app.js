import { LocalDSPPlaybackAdapter } from "./adapters/LocalDSPPlaybackAdapter.js";
import { SpotifyPublicControlAdapter, CLIENT_ID_STORAGE_KEY } from "./adapters/SpotifyPublicControlAdapter.js";
import { SpotifyDJPartnerPlaybackAdapter } from "./adapters/SpotifyDJPartnerPlaybackAdapter.js"; // eslint-disable-line no-unused-vars -- wired for future partner access, see Lane S2 doc
import { isSeekControlEnabled, createSeekDragController } from "./adapters/spotify-seek.js";
import { sanitizeTrackToken } from "./adapters/spotify-autoplay.js";

const CLIENT_ID_KEY = CLIENT_ID_STORAGE_KEY;

const els = {
  modeSpotify: document.getElementById("mode-spotify"),
  modeLocal: document.getElementById("mode-local"),
  headerReadinessBadge: document.getElementById("header-readiness-badge"),
  capabilityStatement: document.getElementById("capability-statement"),
  queueCurrent: document.getElementById("queue-current"),
  queueNext: document.getElementById("queue-next"),
  queueUpcoming: document.getElementById("queue-upcoming"),
  nextAutomixMeta: document.getElementById("next-automix-meta"),
  nextSource: document.getElementById("next-source"),
  nextReadyBadge: document.getElementById("next-ready-badge"),
  panelSession: document.getElementById("panel-session"),
  statusProvider: document.getElementById("status-provider"),
  statusCapability: document.getElementById("status-capability"),
  statusReadiness: document.getElementById("status-readiness"),
  planExit: document.getElementById("plan-exit"),
  planEntry: document.getElementById("plan-entry"),
  planTempo: document.getElementById("plan-tempo"),
  planEq: document.getElementById("plan-eq"),
  planBeat: document.getElementById("plan-beat"),
  planReal: document.getElementById("plan-real"),
  planReason: document.getElementById("plan-reason"),
  spotifySetup: document.getElementById("spotify-setup"),
  spotifyClientIdInput: document.getElementById("spotify-client-id"),
  spotifySaveClientId: document.getElementById("spotify-save-client-id"),
  redirectUriHint: document.getElementById("redirect-uri-hint"),
  panelSeed: document.getElementById("panel-seed"),
  advancedSpotifyOnly: document.getElementById("advanced-spotify-only"),
  nextControlState: document.getElementById("next-control-state"),
  playNaturalEndHint: document.getElementById("play-natural-end-hint"),
  lookaheadState: document.getElementById("lookahead-state"),
  lookaheadPoolSize: document.getElementById("lookahead-pool-size"),
  lookaheadSelectedToken: document.getElementById("lookahead-selected-token"),
  lookaheadSelectionReason: document.getElementById("lookahead-selection-reason"),
  lookaheadSelectionSource: document.getElementById("lookahead-selection-source"),
  lookaheadSuccessorConfirmed: document.getElementById("lookahead-successor-confirmed"),
  lookaheadRefillCount: document.getElementById("lookahead-refill-count"),
  lookaheadConsecutiveCount: document.getElementById("lookahead-consecutive-count"),
  lookaheadAutoMixState: document.getElementById("lookahead-automix-state"),
  lookaheadBlocker: document.getElementById("lookahead-blocker"),
  lookaheadPlayNext: document.getElementById("lookahead-play-next"),
  lookaheadProviderQueueSize: document.getElementById("lookahead-provider-queue-size"),
  seedSearchControls: document.getElementById("seed-search-controls"),
  ctlChangeSeed: document.getElementById("ctl-change-seed"),
  seedSearchInput: document.getElementById("seed-search-input"),
  seedSearchBtn: document.getElementById("seed-search-btn"),
  seedResults: document.getElementById("seed-results"),
  seedStatus: document.getElementById("seed-status"),
  localSeedControls: document.getElementById("local-seed-controls"),
  localSeedList: document.getElementById("local-seed-list"),
  sessionSpotifyOnly: document.getElementById("session-spotify-only"),
  sessionLocalOnly: document.getElementById("session-local-only"),
  localSuccessorState: document.getElementById("local-successor-state"),
  localFallbackReason: document.getElementById("local-fallback-reason"),
  advancedLocalOnly: document.getElementById("advanced-local-only"),
  localTransitionMode: document.getElementById("local-transition-mode"),
  localTransitionDuration: document.getElementById("local-transition-duration"),
  localJumpAvailable: document.getElementById("local-jump-available"),
  ctlChangeSpotifySetup: document.getElementById("ctl-change-spotify-setup"),
  autoplaySnapshotCount: document.getElementById("autoplay-snapshot-count"),
  autoplayClassification: document.getElementById("autoplay-classification"),
  autoplayClassificationReason: document.getElementById("autoplay-classification-reason"),
  seekSlider: document.getElementById("seek-slider"),
  seekCurrentLabel: document.getElementById("seek-current-label"),
  seekDurationLabel: document.getElementById("seek-duration-label"),
  seekJumpNearEndBtn: document.getElementById("seek-jump-near-end"),
  ctlConnect: document.getElementById("ctl-connect"),
  ctlPlay: document.getElementById("ctl-play"),
  ctlPause: document.getElementById("ctl-pause"),
  ctlNext: document.getElementById("ctl-next"),
  ctlAutoMixToggle: document.getElementById("ctl-automix-toggle"),
  ctlDebugToggle: document.getElementById("ctl-debug-toggle"),
  debugPanel: document.getElementById("debug-panel"),
};

const REDIRECT_URI = `${window.location.origin}${window.location.pathname}`;
els.redirectUriHint.textContent = REDIRECT_URI;

let activeAdapter = null;
let activeMode = null; // "spotify" | "local"
let refreshHandle = null;
let lookaheadHandle = null; // P0-M6-R2 Phase F: separate, slower poll loop driving Phase B/C/D/E
let lookaheadCycleInFlight = false;
const debugLines = [];

function logDebug(line) {
  const stamped = `[${new Date().toISOString().split("T")[1].replace("Z", "")}] ${line}`;
  debugLines.push(stamped);
  if (debugLines.length > 300) debugLines.shift();
  els.debugPanel.textContent = debugLines.join("\n");
  els.debugPanel.scrollTop = els.debugPanel.scrollHeight;
  console.log(stamped);
}

function fmtTrack(t) {
  if (!t) return "";
  return `${t.title} -- ${t.artist} (${Math.round(t.durationMs / 1000)}s)`;
}

function formatMs(ms) {
  const totalS = Math.max(0, Math.round((ms || 0) / 1000));
  const m = Math.floor(totalS / 60);
  const s = totalS % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function renderQueue(adapter) {
  const q = adapter.getQueue();
  els.queueCurrent.textContent = q.current ? `Now: ${fmtTrack(q.current)}` : "No track loaded";
  els.queueNext.textContent = q.next ? `Next: ${fmtTrack(q.next)}` : "";
  els.queueUpcoming.innerHTML = "";
  for (const t of q.upcoming.slice(1)) {
    const li = document.createElement("li");
    li.textContent = fmtTrack(t);
    els.queueUpcoming.appendChild(li);
  }
}

/**
 * P0-M6-R3 Part A: the header readiness badge is driven by whatever
 * `readiness` the caller just computed -- never a value cached once at
 * Connect time. See the fixed readiness-truth bug in `startStatusLoop()`
 * below: `getAccountReadiness()` is now called fresh on every tick, so
 * once the SDK actually reports `device_ready` (and, later, confirmed
 * seed playback), this badge advances past `SDK_NOT_READY` within one
 * tick instead of being frozen at whatever was true when Connect was
 * clicked.
 */
function renderReadinessBadge(adapter, readiness) {
  const badge = els.headerReadinessBadge;
  if (!adapter.isConnected()) {
    badge.textContent = "NOT CONNECTED";
    badge.className = "badge badge-muted";
    return;
  }
  if (!readiness) {
    badge.textContent = "--";
    badge.className = "badge badge-muted";
    return;
  }
  if (readiness.ready) {
    badge.textContent = "READY";
    badge.className = "badge badge-ready";
  } else {
    badge.textContent = `NOT READY (${readiness.reason})`;
    badge.className = "badge badge-not-ready";
  }
}

/**
 * P0-M6-R3 Part C: the primary Transition Capability card must never
 * imply real Spotify-audio DSP executes. Spotify's public capability is
 * always exactly these two truthful lines, regardless of session state --
 * Local DSP is a genuinely different, unaffected lane (real beat-matched
 * DSP in this browser tab, not Spotify audio) and is described
 * separately, truthfully.
 */
function renderCapabilityStatement(adapter) {
  els.capabilityStatement.textContent =
    adapter instanceof SpotifyPublicControlAdapter
      ? "Playback continuity only.\nNo custom beat-matched DSP on Spotify Public API."
      : "CONTINUATION: WORKING. CUSTOM SPOTIFY MIXING: REQUIRES PARTNER/AUDIO ENTITLEMENT (not applicable here -- this is the Local DSP lane, which runs its own real beat-matched crossfade DSP in this browser tab).";
}

function renderStatus(adapter, readiness) {
  els.statusProvider.textContent = adapter.providerId;
  els.statusCapability.textContent = adapter.capability;
  els.statusReadiness.textContent = readiness ? `${readiness.ready ? "READY" : "NOT READY"} (${readiness.reason})` : "--";
  renderReadinessBadge(adapter, readiness);
  renderCapabilityStatement(adapter);

  const plan = adapter.getAutoMixPlan();
  els.planExit.textContent = plan.exitAnchorS !== null ? `${plan.exitAnchorS.toFixed(2)}s` : "--";
  els.planEntry.textContent = plan.entryAnchorS !== null ? `${plan.entryAnchorS.toFixed(2)}s` : "--";
  els.planTempo.textContent = plan.tempoCorrectionPct !== null ? `${plan.tempoCorrectionPct}%` : "unknown";
  els.planEq.textContent = plan.bassEqHandoff ? "yes" : "no";
  els.planBeat.textContent = plan.beatDownbeatSync ? "yes" : "no";
  els.planReal.textContent = plan.executesRealDsp ? "YES (this app's own DSP)" : "no (advisory only)";
  els.planReason.textContent = plan.reason;
}

/**
 * P0-M6-R3 Part A repair: readiness-truth bug. `getAccountReadiness()` was
 * previously called ONCE at Connect time and cached on `adapter._lastReadiness`
 * forever after -- but `device_ready` (and later, confirmed seed playback)
 * arrive asynchronously from the Web Playback SDK, often AFTER that single
 * snapshot was taken. The owner-observed defect ("Account readiness UI
 * showed SDK_NOT_READY while real SDK playback was already functioning")
 * was this exact staleness, not a logic error in `getAccountReadiness()`
 * itself. Fixed by recomputing readiness fresh on every tick -- cheap
 * (no network I/O; pure boolean/state checks) -- instead of ever trusting
 * a value captured earlier.
 */
function startStatusLoop(adapter, extraRenderFn) {
  stopStatusLoop();
  refreshHandle = setInterval(async () => {
    const readiness = await adapter.getAccountReadiness();
    adapter._lastReadiness = readiness;
    renderQueue(adapter);
    renderStatus(adapter, readiness);
    extraRenderFn?.();
  }, 500);
}
function stopStatusLoop() {
  if (refreshHandle) clearInterval(refreshHandle);
  refreshHandle = null;
}

/**
 * P0-M6-R2 Phase F, repaired (repair pass 2, Blocker 1, item C): the
 * loop that actually makes the product flow "automatic." Calls
 * `adapter.runLookaheadCycle()` as the SINGLE orchestration entry point
 * -- it internally handles initial selection, requested-successor
 * confirmation, idle waiting, and refill-after-advance, all from ONE
 * fresh `GET /me/player/queue` poll per call. This file must NOT
 * implement a parallel confirmation path (a separate
 * `getRealQueueTruth()` call followed by inspecting controller state and
 * calling `confirmLookaheadSuccessor()` on the side) -- that shape is
 * exactly what caused the double-poll confirmation race this repair
 * fixes. One in-flight guard (`lookaheadCycleInFlight`) ensures a normal
 * tick never overlaps a still-running one. Runs on its own slower
 * interval (real Web API calls, not local SDK state) so it doesn't fire
 * every 500ms alongside the local status-render loop.
 */
function startLookaheadOrchestration(adapter) {
  stopLookaheadOrchestration();
  lookaheadHandle = setInterval(async () => {
    if (!(adapter instanceof SpotifyPublicControlAdapter)) return;
    if (!adapter._seedObserved) return; // nothing to plan/confirm/poll until the seed itself is confirmed active
    if (lookaheadCycleInFlight) return; // never overlap two ticks
    lookaheadCycleInFlight = true;
    try {
      const result = await adapter.runLookaheadCycle();
      logDebug(`runLookaheadCycle() -> queued=${result.queued} confirmed=${result.confirmed ?? "--"} reason=${result.reason || result.selectionReason || "--"}`);
    } catch (e) {
      logDebug(`runLookaheadCycle() -> ERROR: ${e.message}`);
    } finally {
      lookaheadCycleInFlight = false;
    }
    renderNextControlState(adapter);
    renderLookaheadStatus(adapter);
  }, 2000);
}
function stopLookaheadOrchestration() {
  if (lookaheadHandle) clearInterval(lookaheadHandle);
  lookaheadHandle = null;
  lookaheadCycleInFlight = false;
}

function renderAutoplayStatus(adapter) {
  if (!(adapter instanceof SpotifyPublicControlAdapter)) return;
  const count = adapter._autoplaySnapshots.length;
  els.autoplaySnapshotCount.textContent = String(count);
  els.seedStatus.textContent = adapter._seedToken
    ? `${adapter._seedToken}${adapter._seedPlaybackConfirmed ? " (confirmed playing)" : " (play requested, awaiting confirmation)"}`
    : "no seed selected";
  const { result, reason } = adapter.getAutoplayClassification();
  els.autoplayClassification.textContent = result;
  els.autoplayClassificationReason.textContent = reason;
}

function renderSeekUI(adapter, seekController) {
  if (!(adapter instanceof SpotifyPublicControlAdapter)) return;
  const ps = adapter.getPlaybackState();
  const enabled = isSeekControlEnabled({
    sdkReady: adapter._sdkReady,
    hasCurrentTrack: !!ps.trackId,
    durationMs: ps.durationMs,
    disallowsSeeking: ps.disallowsSeeking,
  });
  els.seekSlider.disabled = !enabled;
  els.seekJumpNearEndBtn.disabled = !enabled;
  els.seekSlider.max = String(ps.durationMs || 0);
  els.seekDurationLabel.textContent = formatMs(ps.durationMs || 0);
  if (!seekController.isDragging) {
    els.seekSlider.value = String(ps.positionMs || 0);
    els.seekCurrentLabel.textContent = formatMs(ps.positionMs || 0);
  }
}

/** P0-M6-R2 Phase B: Next control must never claim a successor exists that isn't real, and Play's natural-end behavior must be described truthfully. */
function renderNextControlState(adapter) {
  if (!(adapter instanceof SpotifyPublicControlAdapter)) return;
  els.ctlNext.disabled = !adapter.isNextControlEnabled();
  els.nextControlState.textContent = adapter.getNextControlState();
  els.playNaturalEndHint.textContent = adapter.getPlayAtNaturalEndDescription().message;
}

/** P0-M6-R2 Phase F: visible status for the app-controlled continuation queue -- opaque token only, no raw Spotify IDs. */
function renderLookaheadStatus(adapter) {
  if (!(adapter instanceof SpotifyPublicControlAdapter)) return;
  const s = adapter.getLookaheadStatus();
  els.lookaheadState.textContent = s.state || (adapter._seedObserved ? "SEED_ACTIVE" : "--");
  els.lookaheadPoolSize.textContent = String(s.candidatePoolSize);
  els.lookaheadSelectedToken.textContent = s.selectedToken || "--";
  els.lookaheadSelectionReason.textContent = s.selectionReason || "--";
  els.lookaheadSelectionSource.textContent = s.selectionSource || "--";
  els.lookaheadSuccessorConfirmed.textContent = s.successorConfirmed ? "yes" : "no";
  els.lookaheadRefillCount.textContent = String(s.refillCount);
  els.lookaheadConsecutiveCount.textContent = String(s.consecutiveAutoTrackCount);
  els.lookaheadAutoMixState.textContent = s.autoMixEnabled ? "ON" : "OFF (paused)";
  // P0-M6-R2 repair, Blocker 2/4: the owner UI must show the REAL
  // blocker (terminal auth, a timed cooldown, or none) -- never just a
  // generic "not working."
  if (s.queueBlocker?.type === "TERMINAL_AUTH_BLOCKER") {
    els.lookaheadBlocker.textContent = `TERMINAL_AUTH_BLOCKER (status ${s.queueBlocker.status ?? "?"}) -- reauthorize / check scopes`;
  } else if (s.queueBlocker?.type === "COOLDOWN") {
    const remainingS = Math.max(0, Math.round((s.queueBlocker.untilMs - Date.now()) / 1000));
    els.lookaheadBlocker.textContent = `COOLDOWN -- retrying in ~${remainingS}s (status ${s.queueBlocker.status ?? "?"})`;
  } else {
    els.lookaheadBlocker.textContent = s.failedCandidateCount > 0 ? `none (${s.failedCandidateCount} candidate(s) excluded this session)` : "none";
  }
  // Real owner finding (provider-queue coexistence repair): Spotify's
  // own "Next Up" queue is normal and expected -- shown here as
  // informational, sanitized (count only), never a blocker.
  els.lookaheadPlayNext.textContent = s.successorConfirmed ? (s.successorIsPlayNext ? "yes" : "no (unexpected -- see debug panel)") : "--";
  els.lookaheadProviderQueueSize.textContent = String(s.providerQueueSize);

  // P0-M6-R3 Part A/B: primary "Next" card -- friendly selection-source
  // label (never claims BPM/key/genre similarity, just names the real
  // signal) plus a Ready/Waiting badge driven by the same successor
  // confirmation state as the Advanced diagnostics above.
  const sourceLabel =
    s.selectionSource === "SPOTIFY_PROVIDER_NEXT_UP" ? "Spotify Next Up" : s.selectionSource === "ACCOUNT_AFFINITY_FALLBACK" ? "AutoMix fallback pick" : "--";
  els.nextSource.textContent = sourceLabel;
  els.nextReadyBadge.textContent = s.successorConfirmed ? "Ready" : s.state ? "Waiting" : "--";
  els.nextReadyBadge.className = s.successorConfirmed ? "badge badge-ready" : "badge badge-muted";
}

/**
 * P0-M6-R3 pre-owner UI repair (UI Defect 2): once a seed is confirmed
 * playing, the full 10-result search list has no reason to stay on
 * screen -- it defeats the compact screenshot goal. Collapses the
 * search input/button/results into a single small "Change seed" control;
 * Now Playing (outside `#seed-search-controls`) is untouched and stays
 * visible throughout.
 */
function collapseSeedSearch() {
  els.seedResults.innerHTML = "";
  els.seedSearchControls.classList.add("hidden");
  els.ctlChangeSeed.classList.remove("hidden");
}

/**
 * "Change seed" restores the search workflow so a NEW seed can be picked
 * -- it must never itself trigger a search or change the currently
 * active song; it only reveals the controls the owner already knows how
 * to use.
 */
function restoreSeedSearch() {
  els.seedSearchControls.classList.remove("hidden");
  els.ctlChangeSeed.classList.add("hidden");
}

/**
 * P0-M6-R2 repair pass 2, Blocker 2: the debug panel is tracked
 * diagnostic evidence, not ephemeral UI -- it must never carry the
 * owner's raw search text, a raw `spotify:track:` URI, or any other raw
 * Spotify identifier. Only the RESULT LIST rendered directly in the DOM
 * below (song name/artist as plain `<span>` text, never logged) may show
 * that, because the owner needs it to pick a song. Every `logDebug()`
 * call in this function uses only a result count, an opaque `TRK_`
 * token (`sanitizeTrackToken`), and/or an endpoint name with no query
 * string.
 */
async function renderSeedResults(adapter, query) {
  els.seedResults.innerHTML = "";
  let results;
  try {
    results = await adapter.searchTracks(query);
  } catch (e) {
    logDebug(`searchTracks() -> ERROR: ${e.message}`);
    return;
  }
  logDebug(`searchTracks() -> ${results.length} result(s)`);
  for (const track of results) {
    const li = document.createElement("li");
    li.className = "seed-result-row";
    const label = document.createElement("span");
    label.textContent = `${track.name} -- ${track.artists} (${Math.round(track.durationMs / 1000)}s)`;
    const btn = document.createElement("button");
    btn.textContent = "Play as seed";
    btn.onclick = async () => {
      const seedToken = sanitizeTrackToken(track.uri);
      try {
        await adapter.playSeedTrack(track.uri);
        logDebug(`playSeedTrack(${seedToken}) -> request accepted`);
        renderAutoplayStatus(adapter);
        collapseSeedSearch();
      } catch (e) {
        logDebug(`playSeedTrack(${seedToken}) -> ERROR: ${e.message}`);
      }
    };
    li.appendChild(label);
    li.appendChild(btn);
    els.seedResults.appendChild(li);
  }
}

async function activateSpotify() {
  activeMode = "spotify";
  setModeUi();
  logDebug("Activating SpotifyPublicControlAdapter...");
  const clientId = localStorage.getItem(CLIENT_ID_KEY) || "";
  els.spotifyClientIdInput.value = clientId;
  els.spotifySetup.classList.remove("hidden");
  els.panelSeed.classList.remove("hidden");
  els.advancedSpotifyOnly.classList.remove("hidden");
  els.nextAutomixMeta.classList.remove("hidden");
  els.panelSession.classList.remove("hidden");
  restoreSeedSearch(); // fresh adapter instance for this activation -- no seed chosen yet

  const adapter = new SpotifyPublicControlAdapter({ clientId, redirectUri: REDIRECT_URI });
  activeAdapter = adapter;
  const seekController = createSeekDragController({
    seekFn: (ms) => adapter.seek(ms).catch((e) => logDebug(`seek() -> ERROR: ${e.message}`)),
    getDurationMs: () => adapter.getPlaybackState().durationMs,
  });
  adapter.onStateChange((evt) => {
    logDebug(`[spotify-public] ${JSON.stringify(evt.type === "state_changed" ? { type: evt.type } : evt)}`);
    if (evt.type === "autoplay_snapshot" || evt.type === "seed_playback_confirmed" || evt.type === "seed_track_played") {
      renderAutoplayStatus(adapter);
    }
  });

  try {
    const loggedInJustNow = await adapter.completeLoginIfRedirected();
    if (loggedInJustNow) logDebug("PKCE login completed, token stored.");
  } catch (e) {
    logDebug(`completeLoginIfRedirected() -> ERROR: ${e.message}`);
  }

  els.ctlConnect.onclick = async () => {
    if (!localStorage.getItem(CLIENT_ID_KEY)) {
      logDebug("BLOCKED: OWNER_SPOTIFY_AUTH_REQUIRED -- no Spotify Client ID configured. Paste one above and Save.");
      return;
    }
    const res = await adapter.connect();
    logDebug(`connect() -> ${JSON.stringify(res)}`);
    if (!res.ok && res.reason === "SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES") {
      // P0-M6-R2 repair, Blocker 1: the previously-stored token doesn't
      // cover a scope this build now requires -- connect() already
      // discarded ONLY that stale token (Client ID untouched); routing
      // straight back through PKCE here means the owner never has to
      // open DevTools or clear localStorage by hand.
      logDebug("Reauthorization required for new scopes -- redirecting to Spotify authorize page (PKCE)...");
      await adapter.beginLogin();
      return;
    }
    if (!res.ok && res.reason.startsWith("NOT_AUTHENTICATED")) {
      logDebug("Redirecting to Spotify authorize page (PKCE)...");
      await adapter.beginLogin();
      return;
    }
    // BLOCKER 1 repair: no /me/playlists call anywhere in this flow --
    // readiness/status polling starts immediately; the seed search/select
    // panel (not a playlist) is how playback actually starts.
    const readiness = await adapter.getAccountReadiness();
    adapter._lastReadiness = readiness;
    // UI Defect 1 (P0-M6-R3 pre-owner UI repair): once connect() has
    // actually succeeded, the Client ID field and redirect URI have no
    // reason to stay on the primary compact dashboard -- and a screenshot
    // taken from here on must not show either. The locally-stored Client
    // ID itself is untouched; "Change Spotify setup" (Advanced) reveals
    // this same form again on demand, it is never cleared.
    els.spotifySetup.classList.add("hidden");
    els.ctlChangeSpotifySetup.textContent = "Change Spotify setup";
    startStatusLoop(adapter, () => renderSeekUI(adapter, seekController));
    startLookaheadOrchestration(adapter);
    renderStatus(adapter, readiness);
    renderQueue(adapter);
    renderAutoplayStatus(adapter);
    renderSeekUI(adapter, seekController);
    renderNextControlState(adapter);
    renderLookaheadStatus(adapter);
  };
  els.ctlPlay.onclick = () => adapter.play().catch((e) => logDebug(`play() -> ${e.message}`));
  els.ctlPause.onclick = () => adapter.pause().catch((e) => logDebug(`pause() -> ${e.message}`));
  els.ctlNext.onclick = () =>
    adapter
      .next()
      .then((res) => {
        if (res && res.ok === false) logDebug(`next() -> BLOCKED: ${res.reason} (no real queued successor -- Next cannot fabricate one)`);
      })
      .catch((e) => logDebug(`next() -> ${e.message}`));
  els.seedSearchBtn.onclick = () => {
    const q = els.seedSearchInput.value.trim();
    if (q) renderSeedResults(adapter, q);
  };
  els.seedSearchInput.onkeydown = (ev) => {
    if (ev.key === "Enter") els.seedSearchBtn.click();
  };
  // UI Defect 2: "Change seed" only reveals the search workflow again --
  // it must never itself search or touch the currently-playing track.
  els.ctlChangeSeed.onclick = () => restoreSeedSearch();

  // Section A: drag (input event, continuous, never seeks) vs commit
  // (change event, fires exactly once on release) -- standard <input
  // type=range> semantics map directly onto the drag/commit controller.
  els.seekSlider.oninput = () => {
    seekController.onDrag(Number(els.seekSlider.value));
    els.seekCurrentLabel.textContent = formatMs(seekController.displayValueMs);
  };
  els.seekSlider.onchange = () => {
    const target = seekController.onCommit(Number(els.seekSlider.value));
    els.seekCurrentLabel.textContent = formatMs(target);
    logDebug(`seek() committed -> target=${target}ms`);
  };
  els.seekJumpNearEndBtn.onclick = async () => {
    try {
      const { targetMs, durationMs } = await adapter.startNearEndProbe();
      logDebug(`startNearEndProbe() -> targetMs=${targetMs} (durationMs=${durationMs}); Autoplay evidence window reset`);
      renderAutoplayStatus(adapter);
      renderSeekUI(adapter, seekController);
    } catch (e) {
      logDebug(`startNearEndProbe() -> ERROR: ${e.message}`);
    }
  };

  renderStatus(adapter, null);
  renderQueue(adapter);
  renderAutoplayStatus(adapter);
  renderSeekUI(adapter, seekController);
  renderNextControlState(adapter);
  renderLookaheadStatus(adapter);
}

/**
 * P0-M8-R1 Phase D: Local DSP telemetry -- successor state, transition
 * mode/duration, jump availability, fallback reason, plus the shared
 * (generic) consecutive-track and refill counters in panel-session. Never
 * claims tempo/beat/downbeat certainty beyond what getAutoMixPlan() itself
 * reports from the reused eligibility evidence.
 */
function renderLocalSessionState(adapter) {
  if (!(adapter instanceof LocalDSPPlaybackAdapter)) return;
  const plan = adapter.getAutoMixPlan();
  els.lookaheadConsecutiveCount.textContent = String(plan.consecutiveAutoTrackCount);
  els.lookaheadRefillCount.textContent = String(plan.refillCount);
  els.localSuccessorState.textContent = plan.successorState;
  els.localSuccessorState.className = plan.successorState === "SCHEDULED" || plan.successorState === "PLANNED" ? "badge badge-ready" : "badge badge-muted";
  els.localFallbackReason.textContent = plan.fallbackReason || "none";
  els.localTransitionMode.textContent = plan.transitionMode || "--";
  els.localTransitionDuration.textContent = plan.transitionDurationS != null ? `${plan.transitionDurationS.toFixed(2)}s` : "--";
  const jumpAvailable = adapter.isJumpAvailable();
  els.localJumpAvailable.textContent = jumpAvailable ? "yes" : "no";
  els.localJumpAvailable.className = jumpAvailable ? "badge badge-ready" : "badge badge-muted";
  els.seekJumpNearEndBtn.disabled = !jumpAvailable;

  els.nextAutomixMeta.classList.remove("hidden");
  els.nextSource.textContent = "AutoMix successor (local corpus, real graph lookup)";
  if (plan.available) {
    els.nextReadyBadge.textContent = "Ready";
    els.nextReadyBadge.className = "badge badge-ready";
  } else if (plan.fallbackReason) {
    els.nextReadyBadge.textContent = "No successor";
    els.nextReadyBadge.className = "badge badge-muted";
  } else {
    els.nextReadyBadge.textContent = "--";
    els.nextReadyBadge.className = "badge badge-muted";
  }
}

/** Read-only position/duration display -- Local DSP chain playback has no arbitrary manual seek, only Jump-to-last-15s. */
function renderLocalSeekUI(adapter) {
  const ps = adapter.getPlaybackState();
  els.seekSlider.disabled = true;
  els.seekSlider.max = String(ps.durationMs || 0);
  els.seekSlider.value = String(ps.positionMs || 0);
  els.seekDurationLabel.textContent = formatMs(ps.durationMs || 0);
  els.seekCurrentLabel.textContent = formatMs(ps.positionMs || 0);
}

/** Mirrors collapseSeedSearch()/restoreSeedSearch() (P0-M6-R3) for the Local seed picker -- same compact-screenshot contract, separate markup so the two providers' seed UIs never interfere. */
function collapseLocalSeedPicker() {
  els.localSeedList.innerHTML = "";
  els.localSeedControls.classList.add("hidden");
  els.ctlChangeSeed.classList.remove("hidden");
}
function restoreLocalSeedPicker(adapter) {
  els.localSeedControls.classList.remove("hidden");
  els.ctlChangeSeed.classList.add("hidden");
  renderLocalSeedOptions(adapter);
}

function renderLocalSeedOptions(adapter) {
  els.localSeedList.innerHTML = "";
  for (const seed of adapter.listAvailableSeeds()) {
    const li = document.createElement("li");
    li.className = "seed-result-row";
    const label = document.createElement("span");
    label.textContent = seed.label;
    const btn = document.createElement("button");
    btn.textContent = "Play as seed";
    btn.onclick = async () => {
      try {
        await adapter.selectSeed(seed.trackId);
        logDebug(`selectSeed(${seed.trackId}) -> session started`);
        collapseLocalSeedPicker();
        renderQueue(adapter);
        renderLocalSessionState(adapter);
      } catch (e) {
        logDebug(`selectSeed(${seed.trackId}) -> ERROR: ${e.message}`);
      }
    };
    li.appendChild(label);
    li.appendChild(btn);
    els.localSeedList.appendChild(li);
  }
}

async function activateLocal() {
  activeMode = "local";
  setModeUi();
  logDebug("Activating LocalDSPPlaybackAdapter...");

  const adapter = new LocalDSPPlaybackAdapter({});
  activeAdapter = adapter;
  adapter.onStateChange((evt) => logDebug(`[local-dsp] ${JSON.stringify(evt)}`));

  els.ctlConnect.onclick = async () => {
    const res = await adapter.connect();
    logDebug(`connect() -> ${JSON.stringify(res)}`);
    const readiness = await adapter.getAccountReadiness();
    adapter._lastReadiness = readiness;
    renderLocalSeedOptions(adapter);
    startStatusLoop(adapter, () => {
      renderLocalSessionState(adapter);
      renderLocalSeekUI(adapter);
    });
    renderStatus(adapter, readiness);
    renderQueue(adapter);
    renderLocalSessionState(adapter);
    renderLocalSeekUI(adapter);
  };
  els.ctlPlay.onclick = () => adapter.play();
  els.ctlPause.onclick = () => adapter.pause();
  els.ctlNext.disabled = true; // chain playback is continuous-by-design; use Jump to accelerate instead
  els.ctlChangeSeed.onclick = () => restoreLocalSeedPicker(adapter);
  els.seekJumpNearEndBtn.onclick = () => {
    const res = adapter.jumpToNearExit(15);
    logDebug(`jumpToNearExit(15) -> ${JSON.stringify(res)}`);
    renderLocalSessionState(adapter);
  };

  renderStatus(adapter, null);
  renderQueue(adapter);
  renderLocalSessionState(adapter);
  renderLocalSeekUI(adapter);
}

els.spotifySaveClientId.onclick = () => {
  localStorage.setItem(CLIENT_ID_KEY, els.spotifyClientIdInput.value.trim());
  logDebug("Spotify Client ID saved locally (localStorage only, never sent anywhere but Spotify's own accounts/API endpoints).");
};

function setModeUi() {
  els.modeSpotify.setAttribute("aria-selected", String(activeMode === "spotify"));
  els.modeLocal.setAttribute("aria-selected", String(activeMode === "local"));
  els.spotifySetup.classList.toggle("hidden", activeMode !== "spotify");
  // P0-M8-R1: the seed panel, Next card, and AutoMix Session panel are now
  // generic across both providers (Local DSP gained its own genuine
  // seed-picker + successor telemetry) -- only the PROVIDER-SPECIFIC
  // sub-blocks inside them toggle by mode.
  els.panelSeed.classList.remove("hidden");
  els.nextAutomixMeta.classList.remove("hidden");
  els.panelSession.classList.remove("hidden");
  els.advancedSpotifyOnly.classList.toggle("hidden", activeMode !== "spotify");
  els.advancedLocalOnly.classList.toggle("hidden", activeMode !== "local");
  els.sessionSpotifyOnly.classList.toggle("hidden", activeMode !== "spotify");
  els.sessionLocalOnly.classList.toggle("hidden", activeMode !== "local");
  els.seedSearchControls.classList.toggle("hidden", activeMode !== "spotify");
  els.localSeedControls.classList.toggle("hidden", activeMode !== "local");
  els.ctlChangeSeed.classList.add("hidden");
  els.ctlConnect.textContent = activeMode === "spotify" ? "Connect / Authorize" : "Connect (start local audio)";
  els.ctlNext.disabled = activeMode === "local";
  stopStatusLoop();
  stopLookaheadOrchestration();
}

els.modeSpotify.onclick = () => activateSpotify();
els.modeLocal.onclick = () => activateLocal();

els.ctlAutoMixToggle.onclick = () => {
  const pressed = els.ctlAutoMixToggle.getAttribute("aria-pressed") === "true";
  const next = !pressed;
  els.ctlAutoMixToggle.setAttribute("aria-pressed", String(next));
  els.ctlAutoMixToggle.textContent = `AutoMix: ${next ? "ON" : "OFF"}`;
  activeAdapter?.setAutoMixEnabled(next);
};

// UI Defect 1: the only way back to the Client ID / redirect URI form
// once it's been auto-hidden after a successful connect(). Never clears
// the stored Client ID -- this only toggles visibility of the existing
// form (same convention as the debug-panel toggle below).
els.ctlChangeSpotifySetup.onclick = () => {
  els.spotifySetup.classList.toggle("hidden");
  els.ctlChangeSpotifySetup.textContent = els.spotifySetup.classList.contains("hidden") ? "Change Spotify setup" : "Hide Spotify setup";
};

els.ctlDebugToggle.onclick = () => {
  els.debugPanel.classList.toggle("hidden");
  els.ctlDebugToggle.textContent = els.debugPanel.classList.contains("hidden") ? "Show debug panel" : "Hide debug panel";
};

// Default to Local DSP Live on load unless we're mid-Spotify-redirect.
if (new URLSearchParams(window.location.search).has("code")) {
  activateSpotify();
} else {
  activateLocal();
}
