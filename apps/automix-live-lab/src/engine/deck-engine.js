import { computeQueueSchedule, computeChainSchedule } from "./schedule.js";

/**
 * DeckEngine -- genuine live two-deck Web Audio playback.
 *
 * For "live_two_deck" queue items, the equal-power crossfade AND the
 * bass/EQ handoff are computed and applied at RUNTIME via Web Audio gain
 * and biquad-filter automation (AudioParam.setValueCurveAtTime /
 * linearRampToValueAtTime) -- they are not pre-rendered. Beat/downbeat
 * anchors and tempo-ratio values are read verbatim from the frozen
 * P0-M5-R1 pair manifest (via queue_manifest.json); this engine never
 * re-runs Beat This or re-derives an anchor.
 *
 * For "baked_transition" items (the one <=6% Signalsmith stretch-cover
 * pair in this queue), a single AudioBufferSourceNode plays the existing
 * accepted offline M1 render verbatim -- see queue_manifest.json's
 * `source_note` for that item. This is disclosed, not hidden.
 *
 * Equal-power law: gain = cos/sin(progress * pi/2) -- the same
 * constant-power panning law documented in
 * tools/p0m3/audio_render_shootout/dsp/mixing.py's `equal_power_gains`
 * (public-domain formula, independently implemented here for Web Audio's
 * AudioParam curve API rather than imported, since that module is numpy,
 * not JS).
 */
export class DeckEngine {
  constructor(audioContext, audioBaseUrl) {
    this.ctx = audioContext;
    this.audioBaseUrl = audioBaseUrl;
    this.master = audioContext.createGain();
    this.master.gain.value = 1.0;
    this.master.connect(audioContext.destination);
    this.bufferCache = new Map();
    this.scheduledNodes = [];
    this.timeline = [];
    this.startedAtCtxTime = null;
    this.listeners = new Set();
    this.chainTrackConfigs = [];
    this.chainNodes = [];
    this._chainOriginCtxTime = null;
    this._chainLeadInS = 0.25;
  }

  on(cb) {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  _emit(evt) {
    for (const cb of this.listeners) cb(evt);
  }

  async _loadBuffer(fileName) {
    if (this.bufferCache.has(fileName)) return this.bufferCache.get(fileName);
    const res = await fetch(`${this.audioBaseUrl}/${fileName}`);
    if (!res.ok) throw new Error(`AUDIO_FETCH_FAILED: ${fileName} (${res.status})`);
    const arrayBuf = await res.arrayBuffer();
    const audioBuf = await this.ctx.decodeAudioData(arrayBuf);
    this.bufferCache.set(fileName, audioBuf);
    return audioBuf;
  }

  async preloadAll(items) {
    const files = new Set();
    for (const item of items) {
      if (item.mode === "baked_transition") files.add(item.file);
      else {
        files.add(item.out_file);
        files.add(item.in_file);
      }
    }
    await Promise.all([...files].map((f) => this._loadBuffer(f)));
  }

  /** Preloads a flat list of file names (P0-M8-R1 chain tracks -- one file per track, no out/in pairing). */
  async preloadFiles(fileNames) {
    await Promise.all([...new Set(fileNames)].map((f) => this._loadBuffer(f)));
  }

  _equalPowerCurve(steps, invert) {
    const arr = new Float32Array(steps);
    for (let i = 0; i < steps; i++) {
      const p = i / (steps - 1);
      const angle = (p * Math.PI) / 2;
      arr[i] = invert ? Math.cos(angle) : Math.sin(angle);
    }
    return arr;
  }

  _makeChannel() {
    const gain = this.ctx.createGain();
    const bass = this.ctx.createBiquadFilter();
    bass.type = "lowshelf";
    bass.frequency.value = 150;
    bass.gain.value = 0;
    gain.connect(bass);
    bass.connect(this.master);
    return { gain, bass };
  }

  /**
   * Applies the equal-power crossfade + bass/EQ handoff automation between
   * an outgoing and incoming channel, starting at `startTime` (AudioContext
   * absolute time) over `windowS` seconds. Shared by the legacy baked-queue
   * path (scheduleQueue) and the P0-M8-R1 chain path (extendChain) so both
   * execute the exact same automation code, not a re-derived copy.
   */
  _crossfade(outCh, inCh, startTime, windowS, bassHandoffSpeed) {
    const steps = Math.max(8, Math.round(windowS * 20)); // ~20 automation points/sec
    const outCurve = this._equalPowerCurve(steps, true);
    const inCurve = this._equalPowerCurve(steps, false);
    outCh.gain.gain.setValueCurveAtTime(outCurve, startTime, windowS);
    inCh.gain.gain.setValueCurveAtTime(inCurve, startTime, windowS);

    // Live bass/EQ handoff: outgoing bass cut ramps down faster
    // (bassHandoffSpeed multiplier, reused from dsp/mixing.py's
    // BASS_HANDOFF_SPEED) than the full-band crossfade; incoming bass
    // ramps up to match, so low end changes hands before the rest of
    // the spectrum finishes crossfading (reduces bass-on-bass buildup).
    const bassWindowS = windowS / bassHandoffSpeed;
    outCh.bass.gain.setValueAtTime(0, startTime);
    outCh.bass.gain.linearRampToValueAtTime(-18, startTime + bassWindowS);
    inCh.bass.gain.setValueAtTime(-18, startTime);
    inCh.bass.gain.linearRampToValueAtTime(0, startTime + bassWindowS);
  }

  /**
   * Schedules the full queue against computeQueueSchedule's timeline (the
   * SAME pure function verified offline in tools/verify_schedule.mjs) and
   * returns that timeline plus the AudioContext base time it was anchored
   * to, so the caller can independently confirm real playback matches the
   * mathematically-proven gapless schedule.
   */
  async scheduleQueue(items) {
    await this.preloadAll(items);
    const { timeline, totalDurationS, transitionCount } = computeQueueSchedule(items);
    const base = this.ctx.currentTime;
    this.startedAtCtxTime = base;
    this.timeline = timeline;

    for (const entry of timeline) {
      if (entry.mode === "baked_transition") {
        const buf = this.bufferCache.get(entry.file);
        const src = this.ctx.createBufferSource();
        src.buffer = buf;
        const { gain, bass } = this._makeChannel();
        gain.gain.value = 1.0;
        src.connect(gain);
        src.start(base + entry.t0);
        this.scheduledNodes.push(src);
        src.onended = () => this._emit({ type: "item_ended", tag: entry.tag, mode: entry.mode });
        this._emit({ type: "item_scheduled", tag: entry.tag, mode: entry.mode, t0: entry.t0, itemEndAt: entry.itemEndAt });
        continue;
      }

      // live_two_deck: genuine runtime crossfade + bass handoff automation.
      const outBuf = this.bufferCache.get(entry.outFile);
      const inBuf = this.bufferCache.get(entry.inFile);

      const outSrc = this.ctx.createBufferSource();
      outSrc.buffer = outBuf;
      const outCh = this._makeChannel();
      outCh.gain.gain.value = 1.0;
      outSrc.connect(outCh.gain);
      outSrc.start(base + entry.t0);

      const inSrc = this.ctx.createBufferSource();
      inSrc.buffer = inBuf;
      const inCh = this._makeChannel();
      inCh.gain.gain.value = 0.0;
      inSrc.connect(inCh.gain);
      inSrc.start(base + entry.exitAt, entry.entryOffsetS);

      const windowS = entry.windowEndAt - entry.exitAt;
      const exitTime = base + entry.exitAt;
      this._crossfade(outCh, inCh, exitTime, windowS, entry.bassHandoffSpeed);

      this.scheduledNodes.push(outSrc, inSrc);
      inSrc.onended = () => this._emit({ type: "item_ended", tag: entry.tag, mode: entry.mode });
      this._emit({
        type: "item_scheduled",
        tag: entry.tag,
        mode: entry.mode,
        t0: entry.t0,
        exitAt: entry.exitAt,
        windowEndAt: entry.windowEndAt,
        itemEndAt: entry.itemEndAt,
        tempoRatio: entry.tempoRatio,
      });
    }

    return { timeline, totalDurationS, transitionCount, baseCtxTime: base };
  }

  currentTimeIntoQueue() {
    if (this.startedAtCtxTime === null) return null;
    return this.ctx.currentTime - this.startedAtCtxTime;
  }

  currentItem() {
    const t = this.currentTimeIntoQueue();
    if (t === null) return null;
    return this.timeline.find((e) => t >= e.t0 && t < e.itemEndAt) || null;
  }

  stopAll() {
    for (const n of this.scheduledNodes) {
      try {
        n.stop();
      } catch {
        /* already stopped/ended */
      }
    }
    this.scheduledNodes = [];
    this.timeline = [];
    this.startedAtCtxTime = null;
    this.chainTrackConfigs = [];
    this.chainNodes = [];
    this._chainOriginCtxTime = null;
    this._chainLeadInS = 0.25;
  }

  // ---- P0-M8-R1: genuine single-current-track LocalDSP chain ----
  //
  // Unlike scheduleQueue() (a whole session pre-baked from a fixed item
  // list), a chain is built ONE track at a time: startChain() plays only
  // the seed; extendChain() is called later (by the adapter, once it has
  // chosen an automatic successor) to schedule exactly one more track and
  // crossfade into it from the CURRENTLY PLAYING deck -- the same buffer
  // that has been audible since it became current, never restarted. This
  // is what makes "AutoMix refills after the successor becomes current"
  // a genuine runtime event rather than a UI label over a precomputed plan.

  /** @param {{tag:string,file:string,durationS:number,exitOffsetS:number|null,windowS:number|null,bassHandoffSpeed:number,tempoRatio:number|null}} track */
  async startChain(track, leadInS = 0.25) {
    await this._loadBuffer(track.file);
    this._chainOriginCtxTime = this.ctx.currentTime;
    this._chainLeadInS = leadInS;
    this.chainTrackConfigs = [track];
    this.chainNodes = [];

    const entry = computeChainSchedule([track], leadInS).timeline[0];
    const buf = this.bufferCache.get(track.file);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    const ch = this._makeChannel();
    ch.gain.gain.value = 1.0;
    src.connect(ch.gain);
    const absT0 = this._chainOriginCtxTime + entry.t0;
    src.start(absT0);
    this.scheduledNodes.push(src);
    src.onended = () => this._emit({ type: "chain_track_ended", tag: track.tag });

    const node = { tag: track.tag, track, src, ch, relT0: entry.t0, relExitAt: entry.exitAt, relWindowEndAt: entry.windowEndAt, relItemEndAt: entry.itemEndAt };
    this.chainNodes = [node];
    this._emit({ type: "chain_track_scheduled", tag: track.tag, index: 0, hasExit: entry.exitAt !== null });
    return node;
  }

  /**
   * Schedules exactly one more chain track, crossfading in from whichever
   * track is currently last in the chain. Throws if the current last track
   * has no exit anchor (nothing to crossfade from -- graceful fallback
   * territory, the caller should not have offered a successor) or if this
   * exact track tag is already scheduled anywhere in the chain (guards
   * against duplicate scheduling from rapid/duplicate state events).
   * Scheduling more than one hop ahead of the currently AUDIBLE track is
   * allowed (Web Audio scheduling is not time-limited); the adapter's own
   * refill policy is what keeps this to one hop at a time in practice.
   */
  async extendChain(track) {
    if (!this.chainNodes.length) throw new Error("CHAIN_EXTEND_WITHOUT_SEED: startChain() was not called");
    if (this.chainTrackConfigs.some((t) => t.tag === track.tag)) throw new Error(`CHAIN_EXTEND_DUPLICATE: ${track.tag} is already scheduled in this chain`);
    const prevNode = this.chainNodes[this.chainNodes.length - 1];
    if (prevNode.relExitAt === null) throw new Error(`CHAIN_EXTEND_WITHOUT_EXIT: ${prevNode.tag} has no exit anchor to crossfade from`);

    await this._loadBuffer(track.file);
    this.chainTrackConfigs.push(track);
    const timeline = computeChainSchedule(this.chainTrackConfigs, this._chainLeadInS).timeline;
    const prevEntry = timeline[timeline.length - 2];
    const entry = timeline[timeline.length - 1];

    const buf = this.bufferCache.get(track.file);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    const ch = this._makeChannel();
    ch.gain.gain.value = 0.0;
    src.connect(ch.gain);
    const absT0 = this._chainOriginCtxTime + entry.t0;
    src.start(absT0);
    this.scheduledNodes.push(src);
    src.onended = () => this._emit({ type: "chain_track_ended", tag: track.tag });

    const exitTimeAbs = this._chainOriginCtxTime + prevEntry.exitAt;
    const windowS = prevEntry.windowEndAt - prevEntry.exitAt;
    this._crossfade(prevNode.ch, ch, exitTimeAbs, windowS, prevNode.track.bassHandoffSpeed);

    const node = { tag: track.tag, track, src, ch, relT0: entry.t0, relExitAt: entry.exitAt, relWindowEndAt: entry.windowEndAt, relItemEndAt: entry.itemEndAt };
    this.chainNodes.push(node);
    this._emit({ type: "chain_track_scheduled", tag: track.tag, index: this.chainNodes.length - 1, hasExit: entry.exitAt !== null });
    return node;
  }

  /**
   * Owner acceleration control: seeks the CURRENTLY LAST (not yet extended)
   * chain track forward so its exit anchor arrives in ~`secondsBeforeExit`
   * seconds, by stopping and restarting its AudioBufferSourceNode at a
   * later buffer offset (Web Audio has no live-seek), then shifting the
   * chain's time origin so every not-yet-scheduled future track inherits
   * the same wall-clock shift. Never available once a successor has
   * already been scheduled for the current track (no mid-crossfade jump).
   */
  jumpToNearExit(secondsBeforeExit = 15) {
    const snap = this.chainSnapshot();
    if (!snap) return { ok: false, reason: "NO_CURRENT_TRACK" };
    if (snap.hasSuccessorScheduled) return { ok: false, reason: "SUCCESSOR_ALREADY_SCHEDULED" };
    const idx = snap.index;
    const node = this.chainNodes[idx];
    if (node.relExitAt === null) return { ok: false, reason: "NO_EXIT_ANCHOR" };

    const now = this.ctx.currentTime;
    const absExitAt = this._chainOriginCtxTime + node.relExitAt;
    const absT0 = this._chainOriginCtxTime + node.relT0;
    const remainingS = absExitAt - now;
    if (remainingS <= secondsBeforeExit) return { ok: false, reason: "ALREADY_NEAR_EXIT", remainingS };

    const currentBufferOffsetS = now - absT0;
    const targetBufferOffsetS = Math.max(currentBufferOffsetS, node.track.exitOffsetS - secondsBeforeExit);
    if (targetBufferOffsetS <= currentBufferOffsetS) return { ok: false, reason: "ALREADY_PAST_JUMP_TARGET" };

    try {
      node.src.stop(now);
    } catch {
      /* already stopped/ended */
    }
    const newSrc = this.ctx.createBufferSource();
    newSrc.buffer = node.src.buffer;
    newSrc.connect(node.ch.gain);
    newSrc.start(now, targetBufferOffsetS);
    this.scheduledNodes.push(newSrc);
    newSrc.onended = () => this._emit({ type: "chain_track_ended", tag: node.tag });
    node.src = newSrc;

    const newAbsT0 = now - targetBufferOffsetS;
    const deltaS = newAbsT0 - absT0;
    this._chainOriginCtxTime += deltaS; // shifts this + all not-yet-scheduled future tracks uniformly

    const newRemainingS = this._chainOriginCtxTime + node.relExitAt - now;
    this._emit({ type: "chain_jump", tag: node.tag, targetBufferOffsetS, remainingS: newRemainingS });
    return { ok: true, remainingS: newRemainingS };
  }

  /**
   * Snapshot of the currently audible chain track, or null if no chain is
   * playing. During a crossfade window BOTH the outgoing and incoming
   * track's own buffer intervals contain `now` (the outgoing deck is still
   * fading out while it plays out its own tail) -- "current" means the
   * MOST RECENTLY STARTED track (the incoming/successor deck), not
   * whichever interval happens to be found first.
   */
  chainSnapshot() {
    if (!this.chainNodes.length) return null;
    const now = this.ctx.currentTime;
    const timeline = computeChainSchedule(this.chainTrackConfigs, this._chainLeadInS).timeline;
    let idx = -1;
    for (let i = timeline.length - 1; i >= 0; i--) {
      if (now >= this._chainOriginCtxTime + timeline[i].t0) {
        idx = i;
        break;
      }
    }
    if (idx === -1) idx = 0; // before the seed's own lead-in has elapsed
    const entry = timeline[idx];
    const absT0 = this._chainOriginCtxTime + entry.t0;
    const absExitAt = entry.exitAt !== null ? this._chainOriginCtxTime + entry.exitAt : null;
    return {
      index: idx,
      tag: entry.tag,
      track: this.chainTrackConfigs[idx],
      positionS: Math.max(0, now - absT0),
      durationS: entry.itemEndAt - entry.t0,
      remainingToExitS: absExitAt !== null ? absExitAt - now : null,
      hasSuccessorScheduled: this.chainNodes.length > idx + 1,
      trackCount: this.chainTrackConfigs.length,
    };
  }
}
