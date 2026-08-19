import { PlaybackAdapter, Capability } from "./PlaybackAdapter.js";
import { DeckEngine } from "../engine/deck-engine.js";

/**
 * LocalDSPPlaybackAdapter -- P0-M8-R1 consumer quality slice.
 *
 * Genuine one-song-at-a-time LocalDSP session: the owner picks ONE seed
 * from the local corpus; AutoMix automatically chooses each successor (a
 * real graph lookup over `local_dsp_chain.json`, itself built by reusing
 * `pair_discovery.py`'s already-accepted eligibility function verbatim --
 * see tools/p0m8/), schedules a REAL live two-deck Web Audio crossfade
 * (DeckEngine, unmodified DSP automation reused from the P0-M5/P0-M6
 * lanes), and refills automatically once each successor becomes current.
 * Capability: LOCAL_DSP_FULL.
 *
 * State machine per hop:
 *   1. a track becomes current -> chooseSuccessor() looks up its next hop
 *      in the chain manifest (cheap, synchronous, real graph read) --
 *      if found and AutoMix is ON, it is immediately "PLANNED" (visible as
 *      Next: Ready) but its audio is NOT yet scheduled;
 *   2. once the current track's remaining time to its own exit anchor
 *      drops to REFILL_LOOKAHEAD_S (or immediately after a successful
 *      Jump), the planned successor is "SCHEDULED" -- engine.extendChain()
 *      actually commits the real crossfade automation. This is the
 *      "refill" event (refillCount++);
 *   3. when playback crosses into that scheduled track, it becomes
 *      current and the cycle repeats. If no successor is found at step 1
 *      (the corpus has no further rendered edge from this track), AutoMix
 *      reports a truthful fallback reason and stays on the current track
 *      -- it never forces a low-confidence pair.
 */
const REFILL_LOOKAHEAD_S = 20;
const JUMP_TARGET_S = 15;

export class LocalDSPPlaybackAdapter extends PlaybackAdapter {
  constructor({ audioBaseUrl = "/work_local/local_dsp_chain", chainManifestUrl = "/src/data/local_dsp_chain.json" } = {}) {
    super();
    this._audioBaseUrl = audioBaseUrl;
    this._chainManifestUrl = chainManifestUrl;
    this._ctx = null;
    this._engine = null;
    this._connected = false;
    this._autoMixEnabled = true;
    this._listeners = new Set();
    this._pollHandle = null;
    this._tracksByTag = new Map();
    this._seedTag = null;
    this._plannedSuccessorTag = null; // chosen, not yet scheduled ("Ready")
    this._scheduledSuccessorTag = null; // engine.extendChain() already committed for it
    this._lastCurrentTag = null;
    this._consecutiveAutoTrackCount = 0;
    this._refillCount = 0;
    this._fallbackReason = null;
    this._extendInFlight = false;
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

    const manifest = await fetch(this._chainManifestUrl).then((r) => r.json());
    this._tracksByTag = new Map(manifest.tracks.map((t) => [t.tag, this._toEngineTrack(t)]));
    this._seedTag = manifest.seed_tag;
    await this._engine.preloadFiles(manifest.tracks.map((t) => t.file));

    this._connected = true;
    return { ok: true, reason: "LOCAL_AUDIO_CORPUS_LOADED" };
  }

  _toEngineTrack(t) {
    return {
      tag: t.tag,
      file: t.file,
      durationS: t.duration_s,
      exitOffsetS: t.exit_offset_s,
      windowS: t.window_s,
      bassCutoffHz: t.bass_cutoff_hz,
      bassHandoffSpeed: t.bass_handoff_speed,
      tempoRatio: t.tempo_ratio,
      tempoCorrectionPct: t.tempo_correction_pct,
      exitStructureConfidence: t.exit_structure_confidence,
      harmonicRelationship: t.harmonic_relationship,
      nextTag: t.next_tag,
    };
  }

  isConnected() {
    return this._connected;
  }

  async getAccountReadiness() {
    // No account concept for local playback -- always "ready" once the
    // browser AudioContext is available, which connect() already proved.
    return { premium: true, ready: this._connected, reason: this._connected ? "AUDIO_CONTEXT_READY" : "NOT_CONNECTED" };
  }

  /** @returns {{trackId: string, label: string}[]} local seeds this corpus can currently start a session from. */
  listAvailableSeeds() {
    if (!this._seedTag || !this._tracksByTag.has(this._seedTag)) return [];
    const seed = this._tracksByTag.get(this._seedTag);
    return [{ trackId: seed.tag, label: `${seed.tag} (local corpus, opaque ID -- ${seed.nextTag ? "3+ automatic handoffs available" : "no rendered successor"})` }];
  }

  /** Starts a fresh session from one local seed track. */
  async selectSeed(trackId) {
    if (!this._connected) throw new Error("NOT_CONNECTED");
    const track = this._tracksByTag.get(trackId);
    if (!track) throw new Error(`UNKNOWN_LOCAL_SEED: ${trackId}`);

    this._plannedSuccessorTag = null;
    this._scheduledSuccessorTag = null;
    this._lastCurrentTag = null;
    this._consecutiveAutoTrackCount = 0;
    this._refillCount = 0;
    this._fallbackReason = null;

    await this._engine.startChain(track);
    this._onEngineEvent({ type: "seed_selected", tag: track.tag });
    this._startPolling();
    return { ok: true, tag: track.tag };
  }

  _onEngineEvent(evt) {
    for (const cb of this._listeners) cb(evt);
  }

  _startPolling() {
    if (this._pollHandle) clearInterval(this._pollHandle);
    this._pollHandle = setInterval(() => this._tick(), 250);
  }

  /** Single orchestration tick: detects hop advancement, plans the next successor, and refills (schedules) it once due. Never overlaps itself (guarded by `_extendInFlight`). */
  _tick() {
    const snap = this._engine?.chainSnapshot();
    if (!snap) return;

    if (snap.tag !== this._lastCurrentTag) {
      // A new track just became current (seed on first tick, or a real crossfade completed).
      this._lastCurrentTag = snap.tag;
      this._consecutiveAutoTrackCount += 1;
      this._plannedSuccessorTag = null;
      this._scheduledSuccessorTag = null;
      this._fallbackReason = null;
      this._onEngineEvent({ type: "now_playing", tag: snap.tag });
    }

    // (Re)plan the successor whenever there isn't one yet for the CURRENT
    // track -- not just on the tick a new track arrives, so re-enabling
    // AutoMix on an already-current track resumes planning immediately
    // rather than waiting for the next handoff.
    if (this._autoMixEnabled && !this._plannedSuccessorTag && !this._scheduledSuccessorTag && !this._fallbackReason) {
      const cur = this._tracksByTag.get(snap.tag);
      const nextTag = cur?.nextTag;
      if (!nextTag || !this._tracksByTag.has(nextTag)) {
        this._fallbackReason = cur?.nextTag ? "SUCCESSOR_AUDIO_NOT_AVAILABLE" : "NO_ELIGIBLE_SUCCESSOR_IN_LOCAL_CORPUS";
        this._onEngineEvent({ type: "fallback", tag: snap.tag, reason: this._fallbackReason });
      } else {
        this._plannedSuccessorTag = nextTag; // automatic successor choice -- real graph lookup, immediate
        this._onEngineEvent({ type: "successor_planned", tag: snap.tag, nextTag });
      }
    }

    if (
      this._autoMixEnabled &&
      this._plannedSuccessorTag &&
      !this._scheduledSuccessorTag &&
      !this._extendInFlight &&
      snap.remainingToExitS !== null &&
      snap.remainingToExitS <= REFILL_LOOKAHEAD_S
    ) {
      this._refill(this._plannedSuccessorTag);
    }
  }

  async _refill(nextTag) {
    if (this._extendInFlight || this._scheduledSuccessorTag) return; // never double-schedule
    this._extendInFlight = true;
    try {
      const track = this._tracksByTag.get(nextTag);
      await this._engine.extendChain(track);
      this._scheduledSuccessorTag = nextTag;
      this._refillCount += 1;
      this._onEngineEvent({ type: "refill_scheduled", tag: nextTag, refillCount: this._refillCount });
    } catch (e) {
      this._fallbackReason = `REFILL_FAILED: ${e.message}`;
      this._onEngineEvent({ type: "fallback", reason: this._fallbackReason });
    } finally {
      this._extendInFlight = false;
    }
  }

  /** Owner acceleration control -- available only while a successor is planned but not yet scheduled. */
  jumpToNearExit(secondsBeforeExit = JUMP_TARGET_S) {
    if (!this._engine) return { ok: false, reason: "NOT_CONNECTED" };
    const res = this._engine.jumpToNearExit(secondsBeforeExit);
    if (res.ok) this._onEngineEvent({ type: "jump", ...res });
    return res;
  }

  isJumpAvailable() {
    const snap = this._engine?.chainSnapshot();
    return !!(snap && !snap.hasSuccessorScheduled && snap.remainingToExitS !== null);
  }

  getQueue() {
    const snap = this._engine?.chainSnapshot();
    if (!snap) return { current: null, next: null, upcoming: [] };
    const toTrack = (tag, role) => {
      const t = this._tracksByTag.get(tag);
      if (!t) return null;
      return {
        trackId: tag,
        title: `${tag} (${role})`,
        artist: "AutoMix local corpus (opaque ID)",
        durationMs: Math.round((t.durationS || 0) * 1000),
      };
    };
    const current = toTrack(snap.tag, "live two-deck, currently playing");
    const nextTag = this._scheduledSuccessorTag || this._plannedSuccessorTag;
    const next = nextTag ? toTrack(nextTag, this._scheduledSuccessorTag ? "scheduled" : "planned") : null;
    return { current, next, upcoming: next ? [next] : [] };
  }

  getPlaybackState() {
    const snap = this._engine?.chainSnapshot();
    if (!snap) return { isPlaying: false, positionMs: 0, durationMs: 0, trackId: null };
    return {
      isPlaying: true,
      positionMs: Math.round(snap.positionS * 1000),
      durationMs: Math.round(snap.durationS * 1000),
      trackId: snap.tag,
    };
  }

  async play() {
    if (this._ctx && this._ctx.state === "suspended") await this._ctx.resume();
  }

  async pause() {
    if (this._ctx && this._ctx.state === "running") await this._ctx.suspend();
  }

  async next() {
    // Chain playback is continuous-by-design (successive real crossfades);
    // a manual mid-transition skip is intentionally not exposed, since it
    // would cut a scheduled crossfade mid-flight. Use Jump to accelerate
    // toward the next natural transition instead.
    throw new Error("NOT_IMPLEMENTED: next() -- use jumpToNearExit() to accelerate toward the next automatic transition");
  }

  async seek() {
    throw new Error("NOT_IMPLEMENTED: seek() -- not meaningful for a continuously-scheduled live crossfade chain; use jumpToNearExit()");
  }

  getAutoMixPlan() {
    const snap = this._engine?.chainSnapshot();
    const cur = snap ? this._tracksByTag.get(snap.tag) : null;
    const nextTag = this._scheduledSuccessorTag || this._plannedSuccessorTag;
    const nextTrack = nextTag ? this._tracksByTag.get(nextTag) : null;

    if (!snap || !cur) {
      return {
        available: false,
        reason: "NO_SEED_SELECTED",
        exitAnchorS: null,
        entryAnchorS: null,
        tempoCorrectionPct: null,
        bassEqHandoff: false,
        beatDownbeatSync: false,
        executesRealDsp: true,
        successorState: "NONE",
        transitionMode: "LOCAL_LIVE_TWO_DECK_CHAIN",
        transitionDurationS: null,
        consecutiveAutoTrackCount: 0,
        refillCount: 0,
        fallbackReason: null,
      };
    }

    if (!nextTrack) {
      return {
        available: false,
        reason: this._fallbackReason || "AWAITING_AUTOMIX_PLANNING",
        exitAnchorS: cur.exitOffsetS,
        entryAnchorS: null,
        tempoCorrectionPct: null,
        bassEqHandoff: false,
        beatDownbeatSync: false,
        executesRealDsp: true,
        successorState: "NONE",
        transitionMode: "LOCAL_LIVE_TWO_DECK_CHAIN",
        transitionDurationS: null,
        consecutiveAutoTrackCount: this._consecutiveAutoTrackCount,
        refillCount: this._refillCount,
        fallbackReason: this._fallbackReason,
      };
    }

    return {
      available: true,
      reason: "LIVE_TWO_DECK_RUNTIME_CROSSFADE",
      exitAnchorS: cur.exitOffsetS,
      entryAnchorS: 0,
      tempoCorrectionPct: cur.tempoCorrectionPct,
      bassEqHandoff: true,
      beatDownbeatSync: cur.exitStructureConfidence === "HIGH" || cur.exitStructureConfidence === "MEDIUM",
      executesRealDsp: true,
      successorState: this._scheduledSuccessorTag === nextTag ? "SCHEDULED" : "PLANNED",
      transitionMode: "LOCAL_LIVE_TWO_DECK_CHAIN",
      transitionDurationS: cur.windowS,
      consecutiveAutoTrackCount: this._consecutiveAutoTrackCount,
      refillCount: this._refillCount,
      fallbackReason: this._fallbackReason,
    };
  }

  setAutoMixEnabled(enabled) {
    this._autoMixEnabled = enabled;
    if (!enabled) this._plannedSuccessorTag = null; // stop planning further hops; already-scheduled crossfades still complete honestly
  }

  onStateChange(cb) {
    this._listeners.add(cb);
    return () => this._listeners.delete(cb);
  }
}
