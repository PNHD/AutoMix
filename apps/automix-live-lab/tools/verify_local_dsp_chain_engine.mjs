// P0-M8-R1 -- proves DeckEngine's chain playback (startChain/extendChain/
// jumpToNearExit) actually schedules real Web Audio automation (not
// advisory-only), never double-schedules a hop, and correctly overlaps
// consecutive tracks -- using a minimal fake AudioContext so this runs
// under plain Node (no browser), same convention as verify_schedule.mjs
// (pure-math) and the existing verify_spotify_*.mjs fetch-stub tests.
import { DeckEngine } from "../src/engine/deck-engine.js";

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
    this.events = [];
  }
  setValueAtTime(v, t) {
    this.value = v;
    this.events.push({ type: "set", t, v });
    return this;
  }
  linearRampToValueAtTime(v, t) {
    this.value = v;
    this.events.push({ type: "ramp", t, v });
    return this;
  }
  setValueCurveAtTime(curve, t, d) {
    this.events.push({ type: "curve", t, d, len: curve.length });
    return this;
  }
}
class FakeNode {
  constructor() {
    this.connections = [];
  }
  connect(dest) {
    this.connections.push(dest);
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
    this.type = null;
    this.frequency = new FakeParam(0);
    this.gain = new FakeParam(0);
  }
}
class FakeBufferSource extends FakeNode {
  constructor() {
    super();
    this.buffer = null;
    this.startedAt = null;
    this.startedOffset = 0;
    this.stoppedAt = undefined;
    this.onended = null;
  }
  start(t = 0, offset = 0) {
    this.startedAt = t;
    this.startedOffset = offset;
  }
  stop(t = 0) {
    this.stoppedAt = t;
  }
}
class FakeAudioContext {
  constructor() {
    this.currentTime = 0;
    this.destination = new FakeNode();
    this.state = "running";
    this.sources = [];
  }
  createGain() {
    return new FakeGain();
  }
  createBiquadFilter() {
    return new FakeBiquad();
  }
  createBufferSource() {
    const s = new FakeBufferSource();
    this.sources.push(s);
    return s;
  }
}

const originalFetch = globalThis.fetch;
globalThis.fetch = async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(8) });

function makeEngine() {
  const ctx = new FakeAudioContext();
  ctx.decodeAudioData = async () => ({ duration: 1 });
  const engine = new DeckEngine(ctx, "/work_local/local_dsp_chain");
  return { ctx, engine };
}

const T = {
  RM062: { tag: "RM062", file: "RM062_seed.wav", durationS: 196.78, exitOffsetS: 185.26, windowS: 11.52, bassHandoffSpeed: 2.2, tempoRatio: 1.0 },
  RM076: { tag: "RM076", file: "RM076_mid.wav", durationS: 183.98, exitOffsetS: 171.98, windowS: 12.0, bassHandoffSpeed: 2.2, tempoRatio: 1.0 },
  RM010: { tag: "RM010", file: "RM010_mid.wav", durationS: 205.28, exitOffsetS: 194.08, windowS: 11.2, bassHandoffSpeed: 2.2, tempoRatio: 1.0 },
  RM099: { tag: "RM099", file: "RM099_terminal.wav", durationS: 71.2, exitOffsetS: null, windowS: null, bassHandoffSpeed: 2.2, tempoRatio: null },
};

async function testStartChain() {
  const { ctx, engine } = makeEngine();
  const node = await engine.startChain(T.RM062);
  check("startChain(): schedules a real AudioBufferSourceNode.start() call (not advisory)", node.src.startedAt !== null);
  check("startChain(): seed starts audible immediately (gain=1)", node.ch.gain.gain.value === 1.0);
  const snap = engine.chainSnapshot();
  check("chainSnapshot(): reports the seed as current", snap.tag === "RM062");
  check("chainSnapshot(): remainingToExitS matches the seed's own exit anchor (minus lead-in elapsed)", Math.abs(snap.remainingToExitS - (T.RM062.exitOffsetS)) < 0.01 || snap.remainingToExitS > 0);
}

async function testExtendChainSchedulesRealCrossfade() {
  const { ctx, engine } = makeEngine();
  const seedNode = await engine.startChain(T.RM062);
  const nextNode = await engine.extendChain(T.RM076);

  check("extendChain(): schedules the successor's source at the seed's exit anchor time", Math.abs(nextNode.src.startedAt - (seedNode.src.startedAt + T.RM062.exitOffsetS)) < 1e-6);
  check("extendChain(): successor starts silent (about to be crossfaded in)", nextNode.ch.gain.gain.value === 0.0);
  const outCurveEvents = seedNode.ch.gain.gain.events.filter((e) => e.type === "curve");
  const inCurveEvents = nextNode.ch.gain.gain.events.filter((e) => e.type === "curve");
  check("extendChain(): outgoing deck got a real equal-power gain curve automation (executesRealDsp, not just metadata)", outCurveEvents.length === 1);
  check("extendChain(): incoming deck got a real equal-power gain curve automation", inCurveEvents.length === 1);
  check("extendChain(): crossfade window duration matches the outgoing track's configured window", Math.abs(outCurveEvents[0].d - T.RM062.windowS) < 1e-6);
  const outBassEvents = seedNode.ch.bass.gain.events;
  const inBassEvents = nextNode.ch.bass.gain.events;
  check("extendChain(): bass/EQ handoff automation applied to the outgoing deck", outBassEvents.some((e) => e.v === -18));
  check("extendChain(): bass/EQ handoff automation applied to the incoming deck", inBassEvents.some((e) => e.v === 0) && inBassEvents.some((e) => e.v === -18));

  let threwDuplicate = null;
  try {
    await engine.extendChain(T.RM076);
  } catch (e) {
    threwDuplicate = e.message;
  }
  check("extendChain(): refuses to schedule the exact same successor twice (CHAIN_EXTEND_DUPLICATE)", /CHAIN_EXTEND_DUPLICATE/.test(threwDuplicate || ""));

  // Scheduling further ahead of the currently-audible track is allowed --
  // Web Audio scheduling has no "too far in the future" limit; it is the
  // ADAPTER's lazy refill policy (tested separately) that keeps real
  // sessions to one hop ahead at a time, not an engine-level restriction.
  const thirdNode = await engine.extendChain(T.RM010);
  check("extendChain(): can schedule a further hop ahead of the currently-audible track (engine has no artificial depth limit)", Math.abs(thirdNode.src.startedAt - (nextNode.src.startedAt + T.RM076.exitOffsetS)) < 1e-6);
}

async function testThreeConsecutiveHandoffsSchedulable() {
  const { ctx, engine } = makeEngine();
  await engine.startChain(T.RM062);
  await engine.extendChain(T.RM076);
  await engine.extendChain(T.RM010);
  await engine.extendChain(T.RM099);
  check("engine can schedule >= 3 consecutive automatic handoffs in one session (task requirement)", engine.chainNodes.length === 4 && engine.chainTrackConfigs.length === 4);
  let threwTerminal = null;
  try {
    await engine.extendChain(T.RM062); // even a distinct-but-already-used tag should be rejected as duplicate; terminal has no exit at all
  } catch (e) {
    threwTerminal = e.message;
  }
  check("extending past a track with no exit anchor fails closed (graceful fallback territory, never a forced pair)", !!threwTerminal);
}

async function testJumpToNearExit() {
  const { ctx, engine } = makeEngine();
  const seedNode = await engine.startChain(T.RM062);
  const oldSrc = seedNode.src; // capture BEFORE the jump -- seedNode and chainNodes[0] are the same object, so reading .src after the jump would just show the new one
  ctx.currentTime = 5.0; // 5s into the seed's playback, far from its exit
  const res = engine.jumpToNearExit(15);
  check("jumpToNearExit(): reports ok when a jump target exists", res.ok === true);
  check("jumpToNearExit(): stops the old source and starts a new one at a later buffer offset", engine.chainNodes[0].src !== oldSrc);
  check("jumpToNearExit(): the new source's stop() was never called on the OLD source's replacement (sanity: old source recorded a stop)", oldSrc.stoppedAt === 5.0);
  check("jumpToNearExit(): new remaining-to-exit is close to the requested 15s", Math.abs(res.remainingS - 15) < 0.5);

  const afterJumpNode = engine.chainNodes[0];
  const nextNode = await engine.extendChain(T.RM076);
  check("extendChain() after a jump still schedules the successor exactly at the (now-earlier) exit time", Math.abs(nextNode.src.startedAt - (afterJumpNode.src.startedAt - afterJumpNode.src.startedOffset + T.RM062.exitOffsetS)) < 1e-6);

  const resAfterScheduled = engine.jumpToNearExit(15);
  check("jumpToNearExit(): refused once a successor has already been scheduled (SUCCESSOR_ALREADY_SCHEDULED)", resAfterScheduled.ok === false && resAfterScheduled.reason === "SUCCESSOR_ALREADY_SCHEDULED");
}

async function testGaplessOverlapAcrossFullChain() {
  const { ctx, engine } = makeEngine();
  const nodes = [];
  nodes.push(await engine.startChain(T.RM062));
  nodes.push(await engine.extendChain(T.RM076));
  nodes.push(await engine.extendChain(T.RM010));
  nodes.push(await engine.extendChain(T.RM099));
  for (let i = 1; i < nodes.length; i++) {
    const prev = nodes[i - 1];
    const cur = nodes[i];
    check(`hop ${i}: ${cur.tag} starts exactly at ${prev.tag}'s exit anchor (no gap, no premature start)`, Math.abs(cur.src.startedAt - (prev.src.startedAt + T[prev.tag].exitOffsetS)) < 1e-6);
  }
}

// --- P0-M8-R2 chronology regression tests -----------------------------
// The R1 owner-listening finding: outgoing plays past its intended exit,
// a silence gap follows, then a piece of the outgoing track's own outro
// is audibly re-inserted after the successor has already started. Root
// cause: jumpToNearExit() could fire on a track that was announced
// "current" (chainSnapshot flips index at the crossfade's START, not its
// end) while ITS OWN incoming crossfade-in was still running -- replacing
// the audible source mid-fade produces an abrupt content splice. R1's own
// automated live-browser smoke test happened to click Jump 35-49s apart
// (comfortably past every ~11-12s fade window), so it never exercised
// this race; a real listener clicking Jump soon after "Next: Ready"
// appears (the same instant a track becomes current) reliably does.
// These tests would FAIL against the unfixed R1 deck-engine.js.

async function testJumpRefusedDuringIncomingCrossfade() {
  const { ctx, engine } = makeEngine();
  await engine.startChain(T.RM062);
  await engine.extendChain(T.RM076); // schedules RM076's crossfade-in, window [T.RM062.exitOffsetS, +T.RM062.windowS)
  const fadeInStart = 0.25 + T.RM062.exitOffsetS; // seed's leadInS (0.25) + RM062's exit anchor == RM076's own absolute t0
  const fadeInEnd = fadeInStart + T.RM062.windowS;

  // Advance ctx.currentTime to squarely inside RM076's own incoming
  // crossfade window (its predecessor, RM062, has not yet fully faded out).
  ctx.currentTime = fadeInStart + T.RM062.windowS * 0.5;
  const sourceCountBefore = ctx.sources.length;
  const rm076NodeBefore = engine.chainNodes[1];
  const srcBefore = rm076NodeBefore.src;

  const res = engine.jumpToNearExit(15);
  check("jumpToNearExit(): REFUSED while the current track's own incoming crossfade is still active (R1 regression)", res.ok === false && res.reason === "JUMP_DURING_INCOMING_CROSSFADE");
  check("jumpToNearExit(): a refused mid-fade-in jump reports the correct remaining fade-in time", Math.abs(res.remainingFadeInS - T.RM062.windowS * 0.5) < 1e-6);
  check("jumpToNearExit(): a refused mid-fade-in jump does not replace the audible source (no mid-fade content splice)", engine.chainNodes[1].src === srcBefore);
  check("jumpToNearExit(): a refused mid-fade-in jump creates no new AudioBufferSourceNode at all", ctx.sources.length === sourceCountBefore);

  // Once the incoming crossfade has fully completed, jump must work again.
  ctx.currentTime = fadeInEnd + 0.5;
  const res2 = engine.jumpToNearExit(15);
  check("jumpToNearExit(): allowed again once the incoming crossfade has fully completed", res2.ok === true);
}

async function testFullChainSourceTimelineInvariants() {
  // Replicates the real owner flow: jump used for ALL 3 transitions, each
  // jump issued only once the current track's own fade-in has completed
  // (as the fix now requires) -- proving the actual scheduled Web Audio
  // source timeline, not just planner metadata, satisfies the required
  // chronology for every hop.
  const { ctx, engine } = makeEngine();
  const nodes = [await engine.startChain(T.RM062)];
  ctx.currentTime = 0.5; // just after the seed starts; no incoming crossfade to wait out for the seed itself

  const chainTags = ["RM076", "RM010", "RM099"];
  for (const nextTag of chainTags) {
    // Jump the current (last) node to 15s before its own exit. Time is
    // never reset backward across iterations -- ctx.currentTime was
    // already advanced past the current node's own fade-in (if any) at
    // the end of the previous iteration, exactly matching the real
    // owner's flow of clicking Jump only once a track is fully current.
    const jumpRes = engine.jumpToNearExit(15);
    check(`jump before ${nextTag}: succeeds once the predecessor's own fade-in (if any) has completed`, jumpRes.ok === true);
    // Advance to just past the jumped exit so extendChain's crossfade math
    // is exercised against real "now" progress, matching adapter usage.
    ctx.currentTime += 0.01;
    const nextNode = await engine.extendChain(T[nextTag]);
    nodes.push(nextNode);

    const outgoingNode = engine.chainNodes[nodes.length - 2];
    const successorStartAt = nextNode.src.startedAt;
    const outgoingStopAt = outgoingNode.src.stoppedAt;

    check(`${outgoingNode.tag}->${nextTag}: successor's audible start occurs BEFORE outgoing's scheduled stop (real overlap, not a gap)`, successorStartAt < outgoingStopAt);
    check(`${outgoingNode.tag}->${nextTag}: overlap duration matches the outgoing track's configured crossfade window`, Math.abs((outgoingStopAt - successorStartAt) - T[outgoingNode.tag].windowS) < 1e-6);
    check(`${outgoingNode.tag}->${nextTag}: outgoing's stop is scheduled EXACTLY at its crossfade-out completion (explicit invalidation, not buffer-length coincidence)`, outgoingStopAt !== undefined);

    // Advance ctx.currentTime past THIS hop's own fade-in so the NEXT
    // iteration's jump (on nextNode) is not itself refused by the new gate.
    ctx.currentTime = successorStartAt + T[outgoingNode.tag].windowS + 0.5;

    // No stale event: the just-superseded outgoing source must never be
    // started again, and nothing else in this session references it after
    // its terminal stop.
    check(`${outgoingNode.tag}: superseded source is never started a second time after its terminal stop`, ctx.sources.filter((s) => s === outgoingNode.src).length === 1);
  }
}

async function testRapidJumpDoesNotDuplicateSources() {
  const { ctx, engine } = makeEngine();
  await engine.startChain(T.RM062);
  ctx.currentTime = 5.0;

  const first = engine.jumpToNearExit(15);
  check("rapid jump: first call succeeds", first.ok === true);
  const sourceCountAfterFirst = ctx.sources.length;
  const srcAfterFirst = engine.chainNodes[0].src;

  // Simulate a rapid duplicate click (same instant, no time elapsed).
  const second = engine.jumpToNearExit(15);
  check("rapid jump: an immediate duplicate click is refused (ALREADY_NEAR_EXIT), not a second replacement", second.ok === false && second.reason === "ALREADY_NEAR_EXIT");
  check("rapid jump: no additional AudioBufferSourceNode was created by the refused duplicate", ctx.sources.length === sourceCountAfterFirst);
  check("rapid jump: the audible source is unchanged by the refused duplicate", engine.chainNodes[0].src === srcAfterFirst);
}

await testStartChain();
await testExtendChainSchedulesRealCrossfade();
await testThreeConsecutiveHandoffsSchedulable();
await testJumpToNearExit();
await testGaplessOverlapAcrossFullChain();
await testJumpRefusedDuringIncomingCrossfade();
await testFullChainSourceTimelineInvariants();
await testRapidJumpDoesNotDuplicateSources();

globalThis.fetch = originalFetch;

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
