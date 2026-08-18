import { LocalDSPPlaybackAdapter } from "./adapters/LocalDSPPlaybackAdapter.js";
import { SpotifyPublicControlAdapter, CLIENT_ID_STORAGE_KEY } from "./adapters/SpotifyPublicControlAdapter.js";
import { SpotifyDJPartnerPlaybackAdapter } from "./adapters/SpotifyDJPartnerPlaybackAdapter.js"; // eslint-disable-line no-unused-vars -- wired for future partner access, see Lane S2 doc

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
  seedSearchInput: document.getElementById("seed-search-input"),
  seedSearchBtn: document.getElementById("seed-search-btn"),
  seedResults: document.getElementById("seed-results"),
  seedStatus: document.getElementById("seed-status"),
  autoplaySnapshotCount: document.getElementById("autoplay-snapshot-count"),
  autoplayClassification: document.getElementById("autoplay-classification"),
  autoplayClassificationReason: document.getElementById("autoplay-classification-reason"),
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

function startStatusLoop(adapter) {
  stopStatusLoop();
  refreshHandle = setInterval(() => {
    renderQueue(adapter);
    renderStatus(adapter, adapter._lastReadiness);
  }, 500);
}
function stopStatusLoop() {
  if (refreshHandle) clearInterval(refreshHandle);
  refreshHandle = null;
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

async function renderSeedResults(adapter, query) {
  els.seedResults.innerHTML = "";
  let results;
  try {
    results = await adapter.searchTracks(query);
  } catch (e) {
    logDebug(`searchTracks() -> ERROR: ${e.message}`);
    return;
  }
  logDebug(`searchTracks("${query}") -> ${results.length} result(s) (GET /search?type=track, limit<=10)`);
  for (const track of results) {
    const li = document.createElement("li");
    li.className = "seed-result-row";
    const label = document.createElement("span");
    label.textContent = `${track.name} -- ${track.artists} (${Math.round(track.durationMs / 1000)}s)`;
    const btn = document.createElement("button");
    btn.textContent = "Play as seed";
    btn.onclick = async () => {
      try {
        await adapter.playSeedTrack(track.uri);
        logDebug(`playSeedTrack(${track.uri}) -> PUT /me/player/play?device_id=... {"uris":["${track.uri}"]}`);
        renderAutoplayStatus(adapter);
      } catch (e) {
        logDebug(`playSeedTrack() -> ERROR: ${e.message}`);
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

  const adapter = new SpotifyPublicControlAdapter({ clientId, redirectUri: REDIRECT_URI });
  activeAdapter = adapter;
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
    startStatusLoop(adapter);
    renderStatus(adapter, readiness);
    renderQueue(adapter);
    renderAutoplayStatus(adapter);
  };
  els.ctlPlay.onclick = () => adapter.play().catch((e) => logDebug(`play() -> ${e.message}`));
  els.ctlPause.onclick = () => adapter.pause().catch((e) => logDebug(`pause() -> ${e.message}`));
  els.ctlNext.onclick = () => adapter.next().catch((e) => logDebug(`next() -> ${e.message}`));
  els.seedSearchBtn.onclick = () => {
    const q = els.seedSearchInput.value.trim();
    if (q) renderSeedResults(adapter, q);
  };
  els.seedSearchInput.onkeydown = (ev) => {
    if (ev.key === "Enter") els.seedSearchBtn.click();
  };
  renderStatus(adapter, null);
  renderQueue(adapter);
  renderAutoplayStatus(adapter);
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
  stopStatusLoop();
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
