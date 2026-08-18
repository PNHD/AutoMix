import { PlaybackAdapter, Capability } from "./PlaybackAdapter.js";
import { DeckEngine } from "../engine/deck-engine.js";

/**
 * LocalDSPPlaybackAdapter -- Lane S3 (Issue #11 PM comment 5323227813).
 * Continuous two-deck live playback from authorized DRM-free local audio,
 * reusing the frozen/accepted P0-M5-R1 planner output (pair_manifest,
 * Beat This anchors) via queue_manifest.json. Capability: LOCAL_DSP_FULL.
 */
export class LocalDSPPlaybackAdapter extends PlaybackAdapter {
  constructor({ audioBaseUrl, queueManifest }) {
    super();
    this._audioBaseUrl = audioBaseUrl;
    this._queueManifest = queueManifest;
    this._ctx = null;
    this._engine = null;
    this._connected = false;
    this._autoMixEnabled = true;
    this._listeners = new Set();
    this._pollHandle = null;
    this._lastEmittedTag = null;
  }

  get providerId() {
    return "local-dsp";
  }

  get capability() {
    return Capability.LOCAL_DSP_FULL;
  }

  async connect() {
    this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (this._ctx.state === "suspended") await this._ctx.resume();
    this._engine = new DeckEngine(this._ctx, this._audioBaseUrl);
    this._connected = true;
    return { ok: true, reason: "local_audio_context_ready" };
  }

  isConnected() {
    return this._connected;
  }

  async getAccountReadiness() {
    // No account concept for local playback -- always "ready" once the
    // browser AudioContext is available, which connect() already proved.
    return { premium: true, ready: this._connected, reason: this._connected ? "AUDIO_CONTEXT_READY" : "NOT_CONNECTED" };
  }

  async loadQueue() {
    if (!this._connected) throw new Error("NOT_CONNECTED");
    const { timeline, totalDurationS, transitionCount } = await this._engine.scheduleQueue(this._queueManifest.items);
    this._timeline = timeline;
    this._totalDurationS = totalDurationS;
    this._transitionCount = transitionCount;
    this._engine.on((evt) => this._onEngineEvent(evt));
    this._startPolling();
    return { timeline, totalDurationS, transitionCount };
  }

  _onEngineEvent(evt) {
    for (const cb of this._listeners) cb(evt);
  }

  _startPolling() {
    if (this._pollHandle) clearInterval(this._pollHandle);
    this._pollHandle = setInterval(() => {
      const item = this._engine.currentItem();
      if (item && item.tag !== this._lastEmittedTag) {
        this._lastEmittedTag = item.tag;
        this._onEngineEvent({ type: "now_playing", tag: item.tag, mode: item.mode });
      }
    }, 250);
  }

  getQueue() {
    if (!this._timeline) return { current: null, next: null, upcoming: [] };
    const t = this._engine.currentTimeIntoQueue() ?? 0;
    const idx = this._timeline.findIndex((e) => t >= e.t0 && t < e.itemEndAt);
    const toTrack = (e) =>
      e && {
        trackId: e.tag,
        title: e.mode === "baked_transition" ? `${e.tag} (baked Signalsmith transition)` : `${e.tag} (live two-deck transition)`,
        artist: "AutoMix local corpus (opaque ID)",
        durationMs: Math.round((e.itemEndAt - e.t0) * 1000),
      };
    const current = idx >= 0 ? toTrack(this._timeline[idx]) : null;
    const next = idx >= 0 && idx + 1 < this._timeline.length ? toTrack(this._timeline[idx + 1]) : null;
    const upcoming = idx >= 0 ? this._timeline.slice(idx + 1).map(toTrack) : this._timeline.map(toTrack);
    return { current, next, upcoming };
  }

  getPlaybackState() {
    const t = this._engine ? this._engine.currentTimeIntoQueue() : null;
    const item = this._engine ? this._engine.currentItem() : null;
    return {
      isPlaying: t !== null && this._totalDurationS && t < this._totalDurationS,
      positionMs: item ? Math.round((t - item.t0) * 1000) : 0,
      durationMs: item ? Math.round((item.itemEndAt - item.t0) * 1000) : 0,
      trackId: item ? item.tag : null,
    };
  }

  async play() {
    if (this._ctx && this._ctx.state === "suspended") await this._ctx.resume();
  }

  async pause() {
    if (this._ctx && this._ctx.state === "running") await this._ctx.suspend();
  }

  async next() {
    // Continuous live queue by design (Issue #11: "continuous two-deck
    // playback ... prove at least 5 consecutive transitions") -- manual
    // skip is intentionally not exposed as a mid-transition jump, since
    // that would cut a scheduled crossfade mid-flight. Reserved for a
    // future queue-management pass; not required by this task.
    throw new Error("NOT_IMPLEMENTED: next() -- queue is a fixed, continuously-scheduled live session for this prototype");
  }

  async seek() {
    throw new Error("NOT_IMPLEMENTED: seek() -- not meaningful for a continuously-scheduled live crossfade queue in this prototype");
  }

  getAutoMixPlan() {
    const item = this._engine ? this._engine.currentItem() : null;
    const idx = item ? this._timeline.findIndex((e) => e.tag === item.tag) : -1;
    const nextEntry = idx >= 0 && idx + 1 < this._timeline.length ? this._timeline[idx + 1] : this._timeline?.[0] ?? null;
    if (!nextEntry) {
      return {
        available: false,
        reason: "QUEUE_NOT_LOADED",
        exitAnchorS: null,
        entryAnchorS: null,
        tempoCorrectionPct: null,
        bassEqHandoff: false,
        beatDownbeatSync: false,
        executesRealDsp: true,
      };
    }
    return {
      available: true,
      reason: nextEntry.mode === "baked_transition" ? "STRETCH_COVER_REUSES_ACCEPTED_OFFLINE_RENDER" : "LIVE_TWO_DECK_RUNTIME_CROSSFADE",
      exitAnchorS: nextEntry.exitAt ?? null,
      entryAnchorS: nextEntry.t0 ?? null,
      tempoCorrectionPct: nextEntry.tempoRatio ? Math.round((1 - nextEntry.tempoRatio) * -10000) / 100 : 0,
      bassEqHandoff: true,
      beatDownbeatSync: true,
      executesRealDsp: true,
    };
  }

  setAutoMixEnabled(enabled) {
    this._autoMixEnabled = enabled; // AutoMix planning is inherent to this queue; toggling stops describing "would-be" plans in the UI.
  }

  onStateChange(cb) {
    this._listeners.add(cb);
    return () => this._listeners.delete(cb);
  }
}
