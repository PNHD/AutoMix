// P0-M8-R3 -- STOP AUDIO control: proves LocalDSPPlaybackAdapter.stopAudio()
// actually stops every scheduled AudioBufferSourceNode (current AND a
// successor already extendChain()-scheduled ahead of it) via real
// AudioBufferSourceNode.stop() calls -- not a mute/gain-only no-op -- and
// leaves the adapter able to start a fresh session afterward. Same
// fake-AudioContext + stubbed-fetch convention as verify_local_dsp_adapter.mjs.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { LocalDSPPlaybackAdapter } from "../src/adapters/LocalDSPPlaybackAdapter.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const chainManifest = JSON.parse(readFileSync(path.join(HERE, "..", "src", "data", "local_dsp_chain.json"), "utf-8"));

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
  return ok;
}

class FakeParam {
  constructor(value = 0) {
    this.value = value;
  }
  setValueAtTime(v) {
    this.value = v;
    return this;
  }
  linearRampToValueAtTime(v) {
    this.value = v;
    return this;
  }
  setValueCurveAtTime() {
    return this;
  }
}
class FakeNode {
  connect(dest) {
    return dest;
  }
}
class FakeGain extends FakeNode {
  constructor() {
    super();
    this.gain = new FakeParam(1);
  }
}
class FakeBiquad extends FakeNode {
  constructor() {
    super();
    this.frequency = new FakeParam(0);
    this.gain = new FakeParam(0);
  }
}
class FakeBufferSource extends FakeNode {
  start(t = 0, offset = 0) {
    this.startedAt = t;
    this.startedOffset = offset;
    this.stoppedAt = undefined;
  }
  stop(t) {
    this.stoppedAt = t ?? "IMMEDIATE";
  }
}
class FakeAudioContext {
  constructor() {
    this.currentTime = 0;
    this.destination = new FakeNode();
    this.state = "running";
  }
  createGain() {
    return new FakeGain();
  }
  createBiquadFilter() {
    return new FakeBiquad();
  }
  createBufferSource() {
    return new FakeBufferSource();
  }
  decodeAudioData() {
    return Promise.resolve({ duration: 1 });
  }
  resume() {
    this.state = "running";
    return Promise.resolve();
  }
}

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;

function installStubs() {
  globalThis.fetch = async (url) => {
    if (String(url).includes("local_dsp_chain.json")) return { ok: true, json: async () => chainManifest };
    return { ok: true, arrayBuffer: async () => new ArrayBuffer(8) };
  };
  globalThis.window = {
    AudioContext: function () {
      return new FakeAudioContext();
    },
  };
}
function restoreStubs() {
  globalThis.fetch = originalFetch;
  globalThis.window = originalWindow;
}

async function freshAdapter() {
  installStubs();
  const adapter = new LocalDSPPlaybackAdapter();
  await adapter.connect();
  if (adapter._pollHandle) clearInterval(adapter._pollHandle); // drive ticks manually, deterministically
  return adapter;
}

async function testStopAudioCancelsCurrentAndScheduledSuccessor() {
  const adapter = await freshAdapter();
  const seeds = adapter.listAvailableSeeds();
  await adapter.selectSeed(seeds[0].trackId);
  adapter._tick();
  // Force the successor to be scheduled ahead of the currently-audible
  // track (the real "STOP must cancel FUTURE scheduled nodes too" case).
  await adapter._refill(adapter._plannedSuccessorTag);

  const engine = adapter._engine;
  const nodesBefore = engine.scheduledNodes.slice();
  check("setup: at least 2 real AudioBufferSourceNodes scheduled (seed + successor) before stop", nodesBefore.length >= 2);
  // The seed's own crossfade-out stop (a legitimate FUTURE-scheduled time
  // set by extendChain()'s normal automation) is expected here; only an
  // "IMMEDIATE" (no-arg) stop would mean something already hard-stopped it.
  check("setup: no node has been hard-stopped (IMMEDIATE) before stopAudio() runs", nodesBefore.every((n) => n.stoppedAt !== "IMMEDIATE"));

  const res = adapter.stopAudio();

  check("stopAudio() reports ok", res.ok === true);
  check(
    "stopAudio() calls real .stop() on EVERY previously-scheduled node (current AND the pre-scheduled successor), not a mute",
    nodesBefore.every((n) => n.stoppedAt !== undefined)
  );
  check("stopAudio() hard-stops the successor immediately (not merely relying on its own future-scheduled automation)", nodesBefore[nodesBefore.length - 1].stoppedAt === "IMMEDIATE");
  check("stopAudio() clears the engine's chain state (no dangling chainNodes)", engine.chainNodes.length === 0 && engine.chainTrackConfigs.length === 0);
  check("stopAudio() clears the adapter's session bookkeeping", adapter._plannedSuccessorTag === null && adapter._scheduledSuccessorTag === null && adapter._lastCurrentTag === null && adapter._refillCount === 0);
  check("stopAudio() stops the adapter's own poll loop (no further auto-refill ticks)", adapter._pollHandle === null);
  check("after stopAudio(), chainSnapshot() reports no current track (session genuinely cleared)", engine.chainSnapshot() === null);
  check("after stopAudio(), getQueue() shows nothing loaded", adapter.getQueue().current === null && adapter.getQueue().next === null);

  // "leave the app able to start a new seed afterward"
  await adapter.selectSeed(seeds[0].trackId);
  adapter._tick();
  const freshSnap = engine.chainSnapshot();
  check("a fresh selectSeed() after stopAudio() genuinely starts playing again", freshSnap !== null && freshSnap.tag === seeds[0].trackId);
  const newNode = engine.scheduledNodes[engine.scheduledNodes.length - 1];
  check("the fresh session schedules a brand-new AudioBufferSourceNode (not a reused/already-stopped one)", newNode.stoppedAt === undefined);
}

async function testStopAudioSafeWithNoActiveSession() {
  const adapter = await freshAdapter();
  let threw = null;
  let res;
  try {
    res = adapter.stopAudio();
  } catch (e) {
    threw = e;
  }
  check("stopAudio() before any seed is selected does not throw", threw === null);
  check("stopAudio() before any seed is selected still reports ok", res && res.ok === true);
}

await testStopAudioCancelsCurrentAndScheduledSuccessor();
await testStopAudioSafeWithNoActiveSession();

restoreStubs();

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
