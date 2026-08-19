// P0-M8-R1 -- proves LocalDSPPlaybackAdapter's consumer-facing session
// behavior: automatic successor choice, refill exactly once per handoff,
// >=3 consecutive automatic handoffs, graceful fallback at the end of the
// corpus, AutoMix OFF preventing continuation, no duplicate scheduling
// across rapid ticks, and truthful getAutoMixPlan() telemetry. Uses a fake
// AudioContext + stubbed fetch (same convention as the other verify_*.mjs
// fetch-stub tests) and drives the adapter's internal poll tick manually
// (via ctx.currentTime + adapter._tick()) instead of real timers, so this
// runs instantly and deterministically under plain Node.
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
  }
  stop() {}
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
  suspend() {
    this.state = "suspended";
    return Promise.resolve();
  }
}

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
let sharedCtx = null;

function installStubs() {
  globalThis.fetch = async (url) => {
    if (String(url).includes("local_dsp_chain.json")) return { ok: true, json: async () => chainManifest };
    return { ok: true, arrayBuffer: async () => new ArrayBuffer(8) };
  };
  globalThis.window = {
    AudioContext: function () {
      sharedCtx = new FakeAudioContext();
      return sharedCtx;
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

// --- 1. Local seed -> automatic successor ---
async function testSeedToAutomaticSuccessor() {
  const adapter = await freshAdapter();
  const seeds = adapter.listAvailableSeeds();
  check("listAvailableSeeds() returns at least one local seed", seeds.length >= 1);
  await adapter.selectSeed(seeds[0].trackId);
  adapter._tick();
  const plan = adapter.getAutoMixPlan();
  check("after seed selection, AutoMix immediately plans a real successor (automatic successor choice)", plan.successorState === "PLANNED" && plan.available === true);
  check("getQueue().next reflects the planned successor", adapter.getQueue().next?.trackId === "RM076");
  check("getAutoMixPlan() reports executesRealDsp: true (not advisory-only)", plan.executesRealDsp === true);
  check("getAutoMixPlan() reports the real beat/downbeat + bass/EQ handoff evidence", plan.beatDownbeatSync === true && plan.bassEqHandoff === true);
}

// --- 2/7/13. refill occurs exactly once per handoff, no duplicate scheduling across rapid ticks ---
async function testRefillExactlyOnceNoDuplicates() {
  const adapter = await freshAdapter();
  await adapter.selectSeed("RM062");
  sharedCtx.currentTime = 0.25 + 185.26 - 10; // 10s before the seed's exit anchor -- inside the refill lookahead window
  for (let i = 0; i < 20; i++) adapter._tick(); // rapid/duplicate ticks at the exact same instant
  await new Promise((r) => setTimeout(r, 0)); // let the async _refill() microtask settle
  for (let i = 0; i < 20; i++) adapter._tick();
  await new Promise((r) => setTimeout(r, 0));
  check("refillCount is exactly 1 after many rapid ticks inside the lookahead window (no duplicate scheduling)", adapter._refillCount === 1);
  check("successor state advances to SCHEDULED exactly once", adapter.getAutoMixPlan().successorState === "SCHEDULED");
}

// --- 6/8. confirmed successor becomes current exactly once; >=3 consecutive automatic handoffs schedulable ---
async function testThreeConsecutiveHandoffs() {
  const adapter = await freshAdapter();
  await adapter.selectSeed("RM062");
  const seenCurrentTags = [];
  const track = (tag) => chainManifest.tracks.find((t) => t.tag === tag);

  // Advance through all 3 real hops by simulating time crossing each
  // track's exit anchor, ticking, and letting the refill microtask settle.
  const hops = [
    { from: "RM062", to: "RM076" },
    { from: "RM076", to: "RM010" },
    { from: "RM010", to: "RM099" },
  ];
  let cumulativeAbs = 0.25; // matches DeckEngine's leadInS
  for (const hop of hops) {
    const fromTrack = track(hop.from);
    // land inside the refill lookahead window for this hop, then trigger refill
    sharedCtx.currentTime = cumulativeAbs + fromTrack.exit_offset_s - 5;
    adapter._tick();
    await new Promise((r) => setTimeout(r, 0));
    // now cross the actual exit anchor so the successor becomes current
    cumulativeAbs = cumulativeAbs + fromTrack.exit_offset_s;
    sharedCtx.currentTime = cumulativeAbs + 0.01;
    adapter._tick();
    await new Promise((r) => setTimeout(r, 0));
    seenCurrentTags.push(adapter._lastCurrentTag);
  }

  check("chain advanced through all 3 hops (RM076, RM010, RM099 each became current in order)", JSON.stringify(seenCurrentTags) === JSON.stringify(["RM076", "RM010", "RM099"]));
  check("consecutiveAutoTrackCount reached 4 (seed + 3 automatic successors, task requirement of >= 3 handoffs)", adapter._consecutiveAutoTrackCount === 4);
  check("refillCount reached 3 (one refill per automatic handoff)", adapter._refillCount === 3);

  // ticking many more times at the same final instant must not re-count the current track again
  const countBefore = adapter._consecutiveAutoTrackCount;
  for (let i = 0; i < 10; i++) adapter._tick();
  check("a track that is already current is never re-counted as a new arrival across repeated ticks", adapter._consecutiveAutoTrackCount === countBefore);
}

// --- 5. incompatible/exhausted pair uses graceful fallback instead of forced DSP ---
async function testGracefulFallbackAtChainEnd() {
  const adapter = await freshAdapter();
  await adapter.selectSeed("RM062");
  // Jump straight to RM099 becoming current by manually walking the internal state the same way testThreeConsecutiveHandoffs did, but only assert the terminal fallback here.
  adapter._lastCurrentTag = "RM010"; // pretend we're already on the last track before the terminal
  adapter._tick(); // no-op, tag unchanged
  // Simulate the engine reporting RM099 as current (terminal, no next_tag).
  adapter._engine.chainSnapshot = () => ({ index: 3, tag: "RM099", track: null, positionS: 1, durationS: 71.2, remainingToExitS: null, hasSuccessorScheduled: false, trackCount: 4 });
  adapter._tick();
  const plan = adapter.getAutoMixPlan();
  check("at the end of the rendered corpus, AutoMix reports a truthful fallback reason", plan.fallbackReason === "NO_ELIGIBLE_SUCCESSOR_IN_LOCAL_CORPUS");
  check("no successor is force-scheduled when none is eligible (successorState NONE)", plan.successorState === "NONE" && plan.available === false);
  check("refillCount does not advance when there is nothing eligible to refill", adapter._refillCount === 0);
}

// --- 9. AutoMix OFF prevents automatic continuation ---
async function testAutoMixOffPreventsContinuation() {
  const adapter = await freshAdapter();
  await adapter.selectSeed("RM062");
  adapter._tick(); // plans RM076 while AutoMix is still ON by default
  check("(sanity) AutoMix is ON by default and plans a successor", adapter._plannedSuccessorTag === "RM076");

  adapter.setAutoMixEnabled(false);
  check("setAutoMixEnabled(false) clears the pending plan immediately", adapter._plannedSuccessorTag === null);
  sharedCtx.currentTime = 0.25 + 185.26 - 5; // well inside the refill lookahead window
  for (let i = 0; i < 5; i++) adapter._tick();
  await new Promise((r) => setTimeout(r, 0));
  check("with AutoMix OFF, no successor gets planned even inside the lookahead window", adapter._plannedSuccessorTag === null);
  check("with AutoMix OFF, refillCount never advances (no automatic continuation)", adapter._refillCount === 0);

  adapter.setAutoMixEnabled(true);
  adapter._tick();
  check("re-enabling AutoMix resumes planning on the next tick", adapter._plannedSuccessorTag === "RM076");
}

// --- 12. local mode never reads/acquires Spotify audio (structural) ---
function testNoSpotifyReferenceInLocalDspSource() {
  const adapterSrc = readFileSync(path.join(HERE, "..", "src", "adapters", "LocalDSPPlaybackAdapter.js"), "utf-8");
  const engineSrc = readFileSync(path.join(HERE, "..", "src", "engine", "deck-engine.js"), "utf-8");
  check("LocalDSPPlaybackAdapter.js contains no reference to Spotify (structural provider-boundary check)", !/spotify/i.test(adapterSrc));
  check("deck-engine.js contains no reference to Spotify (structural provider-boundary check)", !/spotify/i.test(engineSrc));
}

await testSeedToAutomaticSuccessor();
await testRefillExactlyOnceNoDuplicates();
await testThreeConsecutiveHandoffs();
await testGracefulFallbackAtChainEnd();
await testAutoMixOffPreventsContinuation();
testNoSpotifyReferenceInLocalDspSource();

restoreStubs();

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
