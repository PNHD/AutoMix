import { computeQueueSchedule } from "./schedule.js";

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
      const steps = Math.max(8, Math.round(windowS * 20)); // ~20 automation points/sec
      const outCurve = this._equalPowerCurve(steps, true);
      const inCurve = this._equalPowerCurve(steps, false);
      const exitTime = base + entry.exitAt;
      outCh.gain.gain.setValueCurveAtTime(outCurve, exitTime, windowS);
      inCh.gain.gain.setValueCurveAtTime(inCurve, exitTime, windowS);

      // Live bass/EQ handoff: outgoing bass cut ramps down faster
      // (bassHandoffSpeed multiplier, reused from dsp/mixing.py's
      // BASS_HANDOFF_SPEED) than the full-band crossfade; incoming bass
      // ramps up to match, so low end changes hands before the rest of
      // the spectrum finishes crossfading (reduces bass-on-bass buildup).
      const bassWindowS = windowS / entry.bassHandoffSpeed;
      outCh.bass.gain.setValueAtTime(0, exitTime);
      outCh.bass.gain.linearRampToValueAtTime(-18, exitTime + bassWindowS);
      inCh.bass.gain.setValueAtTime(-18, exitTime);
      inCh.bass.gain.linearRampToValueAtTime(0, exitTime + bassWindowS);

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
  }
}
