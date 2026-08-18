import { LocalDSPPlaybackAdapter } from "./adapters/LocalDSPPlaybackAdapter.js";
import { SpotifyPublicControlAdapter, CLIENT_ID_STORAGE_KEY } from "./adapters/SpotifyPublicControlAdapter.js";
import { SpotifyDJPartnerPlaybackAdapter } from "./adapters/SpotifyDJPartnerPlaybackAdapter.js"; // eslint-disable-line no-unused-vars -- wired for future partner access, see Lane S2 doc
import { isSeekControlEnabled, createSeekDragController } from "./adapters/spotify-seek.js";
import { sanitizeTrackToken } from "./adapters/spotify-autoplay.js";

const CLIENT_ID_KEY = CLIENT_ID_STORAGE_KEY;

const els = {
  modeSpotify: document.getElementById("mode-spotify"),
  modeLocal: document.getElementById("mode-local"),
  queueCurrent: document.getElementById("queue-current"),
  queueNext: document.getElementById("queue-next"),
  queueUpcoming: document.getElementById("queue-upcoming"),
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
  panelLookahead: document.getElementById("panel-lookahead"),
  nextControlState: document.getElementById("next-control-state"),
  playNaturalEndHint: document.getElementById("play-natural-end-hint"),
  lookaheadState: document.getElementById("lookahead-state"),
  lookaheadPoolSize: document.getElementById("lookahead-pool-size"),
  lookaheadSelectedToken: document.getElementById("lookahead-selected-token"),
  lookaheadSelectionReason: document.getElementById("lookahead-selection-reason"),
  lookaheadSuccessorConfirmed: document.getElementById("lookahead-successor-confirmed"),
  lookaheadRefillCount: document.getElementById("lookahead-refill-count"),
  lookaheadConsecutiveCount: document.getElementById("lookahead-consecutive-count"),
  lookaheadAutoMixState: document.getElementById("lookahead-automix-state"),
  lookaheadBlocker: document.getElementById("lookahead-blocker"),
  seedSearchInput: document.getElementById("seed-search-input"),
  seedSearchBtn: document.getElementById("seed-search-btn"),
  seedResults: document.getElementById("seed-results"),
  seedStatus: document.getElementById("seed-status"),
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

function renderStatus(adapter, readiness) {
  els.statusProvider.textContent = adapter.providerId;
  els.statusCapability.textContent = adapter.capability;
  els.statusReadiness.textContent = readiness ? `${readiness.ready ? "READY" : "NOT READY"} (${readiness.reason})` : "--";

  const plan = adapter.getAutoMixPlan();
  els.planExit.textContent = plan.exitAnchorS !== null ? `${plan.exitAnchorS.toFixed(2)}s` : "--";
  els.planEntry.textContent = plan.entryAnchorS !== null ? `${plan.entryAnchorS.toFixed(2)}s` : "--";
  els.planTempo.textContent = plan.tempoCorrectionPct !== null ? `${plan.tempoCorrectionPct}%` : "unknown";
  els.planEq.textContent = plan.bassEqHandoff ? "yes" : "no";
  els.planBeat.textContent = plan.beatDownbeatSync ? "yes" : "no";
  els.planReal.textContent = plan.executesRealDsp ? "YES (this app's own DSP)" : "no (advisory only)";
  els.planReason.textContent = plan.reason;
}

function startStatusLoop(adapter, extraRenderFn) {
  stopStatusLoop();
  refreshHandle = setInterval(() => {
    renderQueue(adapter);
    renderStatus(adapter, adapter._lastReadiness);
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

async function activateLocal() {
  activeMode = "local";
  setModeUi();
  logDebug("Activating LocalDSPPlaybackAdapter...");
  const queueManifest = await fetch("/src/data/queue_manifest.json").then((r) => r.json());
  const adapter = new LocalDSPPlaybackAdapter({ audioBaseUrl: "/work_local/queue_audio", queueManifest });
  activeAdapter = adapter;
  adapter.onStateChange((evt) => logDebug(`[local-dsp] ${JSON.stringify(evt)}`));

  els.ctlConnect.onclick = async () => {
    const res = await adapter.connect();
    logDebug(`connect() -> ${JSON.stringify(res)}`);
    const readiness = await adapter.getAccountReadiness();
    adapter._lastReadiness = readiness;
    const { timeline, totalDurationS, transitionCount } = await adapter.loadQueue();
    logDebug(`loadQueue() -> ${transitionCount} transitions, ${totalDurationS.toFixed(2)}s total session`);
    logDebug(`timeline: ${JSON.stringify(timeline.map((t) => ({ tag: t.tag, t0: +t.t0.toFixed(2), itemEndAt: +t.itemEndAt.toFixed(2) })))}`);
    startStatusLoop(adapter);
    renderStatus(adapter, readiness);
    renderQueue(adapter);
  };
  els.ctlPlay.onclick = () => adapter.play();
  els.ctlPause.onclick = () => adapter.pause();
  els.ctlNext.onclick = () => adapter.next().catch((e) => logDebug(`next() -> ${e.message}`));
  renderStatus(adapter, null);
  renderQueue(adapter);
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
  els.panelLookahead.classList.remove("hidden");

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

els.spotifySaveClientId.onclick = () => {
  localStorage.setItem(CLIENT_ID_KEY, els.spotifyClientIdInput.value.trim());
  logDebug("Spotify Client ID saved locally (localStorage only, never sent anywhere but Spotify's own accounts/API endpoints).");
};

function setModeUi() {
  els.modeSpotify.setAttribute("aria-selected", String(activeMode === "spotify"));
  els.modeLocal.setAttribute("aria-selected", String(activeMode === "local"));
  els.spotifySetup.classList.toggle("hidden", activeMode !== "spotify");
  els.panelSeed.classList.toggle("hidden", activeMode !== "spotify");
  els.panelLookahead.classList.toggle("hidden", activeMode !== "spotify");
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
