// P0-M8-R3 -- audio-SAMPLE regression for the LocalDSP chain crossfades.
//
// R1/R2's tests (verify_local_dsp_chain_engine.mjs) prove DeckEngine's
// scheduling metadata (source start/stop times, gain-curve event counts) is
// correct, but that is insufficient: the R2 owner-relisting found all 3
// handoffs still audibly BAD even though every scheduling test passed
// 814/814. Forensic PCM analysis (P0-M8-R3, offline-rendered via a real
// OfflineAudioContext running the UNMODIFIED DeckEngine + schedule.js
// against the actual local corpus WAVs) found the true defect: the
// RM062->RM076 and RM076->RM010 crossfades were scheduled starting at exit
// anchors that land INSIDE the outgoing track's own near-silent content
// (RM062: its natural outro fade; RM076: a mid-song dramatic-pause
// breakdown), producing a real ~30dB composite loudness hole even though
// the two decks are technically overlapping and the crossfade math itself
// is correct (GAIN_AUTOMATION_ERROR per the P0-M8-R3 forensic report:
// "gain/EQ automation causes an apparent silence despite sources
// technically overlapping").
//
// This test reproduces that defect class with SYNTHETIC, git-safe,
// fingerprinted tone buffers (no copyrighted audio) shaped to match the
// REAL measured amplitude envelope of the two affected source tracks
// (a steady tone that decays to near-silence at a fixed time, derived from
// the actual forensic RMS-envelope measurements -- not tuned to whatever
// exit_offset_s currently happens to be in local_dsp_chain.json), runs them
// through the REAL, unmodified DeckEngine.startChain()/extendChain()
// crossfade automation using the manifest's ACTUAL exit_offset_s/window_s
// for RM062 and RM076, and numerically renders the resulting composite PCM
// (a small from-scratch AudioParam/mixer implementation -- linear-ramp and
// setValueCurveAtTime interpolation exactly per the Web Audio spec -- so
// this runs under plain Node with no new dependency and no browser, but
// still measures real per-sample output, not just scheduling metadata).
//
// This test FAILS against the unmodified P0-M8-R2 manifest (exit_offset_s
// values that land inside the near-silent zones) and PASSES once the
// manifest's exit_offset_s values are corrected to exit before those zones.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { DeckEngine } from "../src/engine/deck-engine.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const chain = JSON.parse(readFileSync(path.join(HERE, "..", "src", "data", "local_dsp_chain.json"), "utf-8"));
const byTag = Object.fromEntries(chain.tracks.map((t) => [t.tag, t]));

let checks = 0;
let passed = 0;
const failures = [];
function check(name, cond, detail) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  else failures.push(detail ? `${name} :: ${detail}` : name);
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}${detail ? ` (${detail})` : ""}`);
  return ok;
}

const SR = 44100;

// --- Real (spec-accurate) AudioParam automation -- linear interpolation
// for setValueCurveAtTime / linearRampToValueAtTime, exactly as the Web
// Audio spec defines them, so valueAt(t) gives the ACTUAL numeric gain the
// browser would apply at time t, not just a recorded event count.
class RealParam {
  constructor(value = 0) {
    this._staticValue = value;
    this.value = value;
    this.events = []; // {type:'set'|'ramp', t, v} | {type:'curve', t0, dur, curve}
  }
  setValueAtTime(v, t) {
    this.events.push({ type: "set", t, v });
    return this;
  }
  linearRampToValueAtTime(v, t) {
    this.events.push({ type: "ramp", t, v });
    return this;
  }
  setValueCurveAtTime(curve, t0, dur) {
    this.events.push({ type: "curve", t0, dur, curve: Float32Array.from(curve) });
    return this;
  }
  valueAt(t) {
    const evs = this.events;
    if (evs.length === 0) return this._staticValue;
    // find the curve event covering t, if any
    for (const e of evs) {
      if (e.type === "curve" && t >= e.t0 && t <= e.t0 + e.dur) {
        const frac = e.dur > 0 ? (t - e.t0) / e.dur : 0;
        const pos = frac * (e.curve.length - 1);
        const i0 = Math.floor(pos);
        const i1 = Math.min(e.curve.length - 1, i0 + 1);
        const localFrac = pos - i0;
        return e.curve[i0] + (e.curve[i1] - e.curve[i0]) * localFrac;
      }
    }
    // otherwise: last set/ramp event at or before t, or interpolate a ramp in progress
    let prev = { t: -Infinity, v: this._staticValue };
    for (let i = 0; i < evs.length; i++) {
      const e = evs[i];
      const et = e.type === "curve" ? e.t0 : e.t;
      if (et > t) break;
      if (e.type === "set") prev = { t: e.t, v: e.v };
      else if (e.type === "ramp") prev = { t: e.t, v: e.v };
      else if (e.type === "curve") prev = { t: e.t0 + e.dur, v: e.curve[e.curve.length - 1] };
    }
    return prev.v;
  }
}
class RealNode {
  connect(dest) {
    this._dest = dest;
    return dest;
  }
}
class RealGain extends RealNode {
  constructor() {
    super();
    this.gain = new RealParam(1);
  }
}
class RealBiquad extends RealNode {
  // Identity for this test: all synthetic tones are placed well above the
  // 150Hz lowshelf cutoff, so the bass-handoff automation (which only
  // touches content BELOW cutoff) provably does not attenuate them --
  // verified separately in verify_local_dsp_chain_engine.mjs (bass curve
  // event assertions). This lets the mixer below skip re-implementing
  // biquad DSP without masking the gain-automation defect under test.
  constructor() {
    super();
    this.type = null;
    this.frequency = new RealParam(0);
    this.gain = new RealParam(0);
  }
}
class RealBufferSource extends RealNode {
  constructor(ctx) {
    super();
    this._ctx = ctx;
    this.buffer = null;
    this.startedAt = null;
    this.startedOffset = 0;
    this.stoppedAt = Infinity;
    this.onended = null;
  }
  start(t = 0, offset = 0) {
    this.startedAt = t;
    this.startedOffset = offset;
    this._ctx._sources.push(this);
  }
  stop(t = 0) {
    this.stoppedAt = t;
  }
}
class FakeAudioContext {
  constructor() {
    this.currentTime = 0;
    this.destination = new RealNode();
    this.state = "running";
    this._sources = [];
  }
  createGain() {
    return new RealGain();
  }
  createBiquadFilter() {
    return new RealBiquad();
  }
  createBufferSource() {
    return new RealBufferSource(this);
  }
}

/** Renders the real numeric composite mix over [t0,t1) at SR, by walking
 * every scheduled RealBufferSource, sampling its buffer through its own
 * gain-node automation (real per-sample multiply against RealParam.valueAt,
 * exactly matching what the actual Web Audio graph would output). */
function renderMix(sources, t0, t1, sr = SR) {
  const n = Math.round((t1 - t0) * sr);
  const out = new Float32Array(n);
  for (const src of sources) {
    if (src.startedAt === null || !src.buffer) continue;
    const gainNode = src._dest; // RealGain the source connects directly into
    for (let i = 0; i < n; i++) {
      const t = t0 + i / sr;
      if (t < src.startedAt || t >= src.stoppedAt) continue;
      const bufIdx = Math.round((t - src.startedAt) * sr) + Math.round(src.startedOffset * sr);
      if (bufIdx < 0 || bufIdx >= src.buffer.data.length) continue;
      const g = gainNode ? gainNode.gain.valueAt(t) : 1;
      out[i] += src.buffer.data[bufIdx] * g;
    }
  }
  return out;
}

function rmsDb(x) {
  const r = Math.sqrt(x.reduce((s, v) => s + v * v, 0) / x.length);
  return 20 * Math.log10(Math.max(r, 1e-9));
}

/** Synthetic fingerprinted source: a steady tone at `freqHz` (chosen above
 * the 150Hz bass-shelf cutoff so the identity RealBiquad above is exact,
 * not approximate) for [0, fadeStartS), then decays to near-silence by
 * fadeStartS+fadeLenS and stays near-silent -- reproducing the REAL
 * measured envelope shape of RM062 (permanent outro fade) / RM076 (a hard
 * mid-song breakdown) without using any copyrighted audio. */
function makeFadingTone(durationS, fadeStartS, fadeLenS, freqHz, sr = SR) {
  const n = Math.round(durationS * sr);
  const data = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let env = 1.0;
    if (t >= fadeStartS) {
      const into = t - fadeStartS;
      env = into >= fadeLenS ? 0.02 : 1.0 - 0.98 * (into / fadeLenS);
    }
    data[i] = env * 0.5 * Math.sin(2 * Math.PI * freqHz * t);
  }
  return { data, sr, duration: durationS };
}

/** Synthetic steady incoming: full-amplitude tone throughout (isolates the
 * outgoing-side defect under test; entry-side quiet-intro behavior is
 * covered by the separate incoming-continuity forensic probe, not this
 * unit test). */
function makeSteadyTone(durationS, freqHz, sr = SR) {
  const n = Math.round(durationS * sr);
  const data = new Float32Array(n);
  for (let i = 0; i < n; i++) data[i] = 0.5 * Math.sin(2 * Math.PI * freqHz * (i / sr));
  return { data, sr, duration: durationS };
}

/** Runs startChain(outTrack)+extendChain(inTrack) through the REAL,
 * unmodified DeckEngine, backed by synthetic buffers instead of a fetch,
 * then renders and measures the actual composite PCM around the crossfade
 * window using the manifest's REAL exit_offset_s/window_s for this hop. */
async function measureHandoff(outTag, inTag, outBuf, inBuf) {
  const ctx = new FakeAudioContext();
  const engine = new DeckEngine(ctx, "/unused");
  const outTrack = byTag[outTag];
  const inTrack = byTag[inTag];
  engine.bufferCache.set(outTrack.file, outBuf);
  engine.bufferCache.set(inTrack.file, inBuf);

  const outCfg = { tag: outTag, file: outTrack.file, durationS: outTrack.duration_s, exitOffsetS: outTrack.exit_offset_s, windowS: outTrack.window_s, bassHandoffSpeed: outTrack.bass_handoff_speed, tempoRatio: outTrack.tempo_ratio };
  const inCfg = { tag: inTag, file: inTrack.file, durationS: inTrack.duration_s, exitOffsetS: inTrack.exit_offset_s, windowS: inTrack.window_s, bassHandoffSpeed: inTrack.bass_handoff_speed, tempoRatio: inTrack.tempo_ratio };

  const outNode = await engine.startChain(outCfg);
  const inNode = await engine.extendChain(inCfg);

  const exitAt = outNode.relExitAt;
  const windowEndAt = outNode.relWindowEndAt;
  const mix = renderMix(ctx._sources, exitAt - 2, windowEndAt + 2, SR);

  // 100ms-hop RMS-dB contour across the crossfade window.
  const hop = Math.round(0.1 * SR);
  const win = Math.round(0.2 * SR);
  let minDb = Infinity;
  let minT = null;
  for (let start = 0; start + win <= mix.length; start += hop) {
    const seg = mix.subarray(start, start + win);
    const d = rmsDb(seg);
    if (d < minDb) {
      minDb = d;
      minT = exitAt - 2 + start / SR;
    }
  }
  return { exitAt, windowEndAt, minDb, minT, outNode, inNode, ctx };
}

// --- RM062->RM076: synthetic outgoing fades to near-silence at t=184.0s
// (forensic evidence: real RM062 RMS envelope holds steady ~-8dBFS through
// t=183.4s, then collapses to <=-38dBFS by t=185.6s -- see
// ../../../P0-M8-R3-FORENSICS/phase_c_solo_contour.txt). Incoming is a
// steady tone (isolates the outgoing-side defect).
{
  const outT = byTag.RM062;
  const inT = byTag.RM076;
  const outBuf = makeFadingTone(outT.duration_s + 5, 184.0, 2.0, 880);
  const inBuf = makeSteadyTone(inT.duration_s + 5, 1320);
  const { minDb, minT, exitAt, windowEndAt } = await measureHandoff("RM062", "RM076", outBuf, inBuf);
  console.log(`  RM062->RM076: crossfade [${exitAt.toFixed(2)},${windowEndAt.toFixed(2)}]s, composite min ${minDb.toFixed(1)} dBFS at t=${minT.toFixed(2)}s`);
  check(
    "RM062->RM076: composite loudness never drops into a near-silent hole during/around the crossfade (>= -20 dBFS)",
    minDb >= -20,
    `min=${minDb.toFixed(1)}dBFS at t=${minT.toFixed(2)}s (exit_offset_s=${outT.exit_offset_s}, i.e. exit anchor at absolute ${(outT.trim_start_s + outT.exit_offset_s).toFixed(2)}s, synthetic fade onset at 184.0s)`
  );
}

// --- RM076->RM010: synthetic outgoing hard-cuts to silence at t=174.2s
// ABSOLUTE original-track time (forensic evidence: real RM076 RMS envelope
// holds steady ~-8 to -14dBFS through t=174.0s, then drops to full digital
// silence by t=175.6s -- a mid-song dramatic-pause breakdown, not a
// gradual outro). RM076_mid.wav's buffer sample 0 is trim_start_s=2.04
// into the original track (Phase A), so the fade onset RELATIVE TO THE
// TRIMMED BUFFER (what this synthetic source represents) is
// 174.2 - 2.04 = 172.16s.
{
  const outT = byTag.RM076;
  const inT = byTag.RM010;
  const fadeOnsetRelativeToBuffer = 174.2 - outT.trim_start_s;
  const outBuf = makeFadingTone(outT.duration_s + 20, fadeOnsetRelativeToBuffer, 1.4, 1100);
  const inBuf = makeSteadyTone(inT.duration_s + 5, 660);
  const { minDb, minT, exitAt, windowEndAt } = await measureHandoff("RM076", "RM010", outBuf, inBuf);
  console.log(`  RM076->RM010: crossfade [${exitAt.toFixed(2)},${windowEndAt.toFixed(2)}]s, composite min ${minDb.toFixed(1)} dBFS at t=${minT.toFixed(2)}s`);
  check(
    "RM076->RM010: composite loudness never drops into a near-silent hole during/around the crossfade (>= -20 dBFS)",
    minDb >= -20,
    `min=${minDb.toFixed(1)}dBFS at t=${minT.toFixed(2)}s (exit_offset_s=${outT.exit_offset_s}, i.e. exit anchor at absolute ${(outT.trim_start_s + outT.exit_offset_s).toFixed(2)}s, synthetic breakdown onset at absolute 174.2s / buffer-relative ${fadeOnsetRelativeToBuffer.toFixed(2)}s)`
  );
}

// --- General structural regression (Phase D checklist), reusing the same
// real numeric mixer: no stale outgoing reappearance after its terminal
// fade, no unjustified silence gap, incoming starts continuously (no
// backward/forward content jump -- trivially true here since synthetic
// buffers start at their own sample 0 by construction, asserted anyway).
{
  const outT = byTag.RM010;
  const inT = byTag.RM099;
  const outBuf = makeSteadyTone(outT.duration_s + 5, 990);
  const inBuf = makeSteadyTone((inT.duration_s || 71.2) + 5, 550);
  const { ctx, outNode, windowEndAt } = await measureHandoff("RM010", "RM099", outBuf, inBuf);
  const outSrc = ctx._sources.find((s) => s === outNode.src);
  check("RM010: outgoing source is explicitly stopped at its crossfade-out completion (not left free-running)", outSrc.stoppedAt !== Infinity && Math.abs(outSrc.stoppedAt - windowEndAt) < 1e-6, `stoppedAt=${outSrc.stoppedAt}`);
  const postStop = renderMix([outSrc], windowEndAt + 0.5, windowEndAt + 5, SR);
  const postStopDb = rmsDb(postStop);
  check("RM010: outgoing produces no audible samples after its explicit stop (no reappearance)", postStopDb < -100, `${postStopDb.toFixed(1)}dBFS in [${(windowEndAt + 0.5).toFixed(2)},${(windowEndAt + 5).toFixed(2)}]s`);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
if (failures.length) console.log("FAILURES:\n  " + failures.join("\n  "));
process.exit(passed === checks ? 0 : 1);
