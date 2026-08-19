// P0-M8-R1 -- pure-math + structural proof for the LocalDSP consumer
// chain: gapless/overlap-correct scheduling (schedule.js, the same module
// deck-engine.js uses at runtime) plus the transition-quality invariants
// (<=6% tempo correction, "preserves almost all outgoing song") over the
// actual prepared chain manifest and its known source-track durations.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { computeChainSchedule, verifyChainOverlap } from "../src/engine/schedule.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const chainPath = path.join(HERE, "..", "src", "data", "local_dsp_chain.json");
const chain = JSON.parse(readFileSync(chainPath, "utf-8"));

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
  return ok;
}

// ffprobe'd durations of the FULL decoded source tracks (before any
// trimming) -- tools/p0m8/prepare_local_dsp_chain.py trims a SPAN of each,
// never the whole file; these are the denominators for the "preserves
// almost all outgoing song" invariant below.
const FULL_SOURCE_DURATION_S = { RM062: 199.749683, RM076: 186.235669, RM010: 227.938707, RM099: 231.73517 };

check("chain manifest declares >= 4 tracks (>= 3 transitions, task requirement)", chain.tracks.length >= 4);
check("chain manifest declares transition_count >= 3", chain.transition_count >= 3);

const engineTracks = chain.tracks.map((t) => ({ tag: t.tag, durationS: t.duration_s, exitOffsetS: t.exit_offset_s, windowS: t.window_s }));
const { timeline } = computeChainSchedule(engineTracks);
const { ok: overlapOk, issues } = verifyChainOverlap(timeline);

check("computeChainSchedule produced one timeline entry per track", timeline.length === chain.tracks.length);
check("chain overlap is well-formed end-to-end (each hop starts exactly at the previous track's exit anchor)", overlapOk);
if (!overlapOk) console.log("  issues:", JSON.stringify(issues));
check("first track starts at the lead-in offset, not at t=0", timeline[0].t0 > 0);

for (let i = 0; i < timeline.length; i++) {
  const e = timeline[i];
  const isTerminal = i === timeline.length - 1;
  if (!isTerminal) {
    check(`${e.tag}: has a defined exit anchor (non-terminal track)`, e.exitAt !== null);
    check(`${e.tag}: exitAt > t0 (plays alone before its own crossfade)`, e.exitAt > e.t0);
    check(`${e.tag}: windowEndAt > exitAt (positive crossfade window)`, e.windowEndAt > e.exitAt);
  } else {
    check(`${e.tag}: terminal track has no further exit anchor (graceful end of chain)`, e.exitAt === null);
  }
}

// --- Phase C invariant: abs tempo correction never exceeds 6% ---
for (const t of chain.tracks) {
  if (t.tempo_correction_pct === null) continue;
  check(`${t.tag}: |tempo_correction_pct| <= 6% (Phase C hard ceiling)`, Math.abs(t.tempo_correction_pct) <= 6.0);
}

// --- Phase C invariant: "preserve almost all outgoing song" / "exit near natural ending" ---
for (const t of chain.tracks) {
  if (t.exit_offset_s === null) continue;
  const fullDurationS = FULL_SOURCE_DURATION_S[t.tag];
  const absoluteExitS = t.trim_start_s + t.exit_offset_s;
  const preservedFraction = absoluteExitS / fullDurationS;
  check(`${t.tag}: exits at ${(preservedFraction * 100).toFixed(1)}% into its own full-length source track (>= 85%, "preserves almost all")`, preservedFraction >= 0.85);
  const introSkippedS = t.trim_start_s;
  check(`${t.tag}: intro skipped before playback starts is small (<= 10s, not abandoning the song's own start)`, introSkippedS <= 10.0);
}

// --- Reused-eligibility consistency: this file's tempo/exit values must
// match what tools/p0m8/discover_local_dsp_graph.py computed by reusing
// pair_discovery.py's evaluate_pair() verbatim (no independently-authored
// anchor math anywhere in this app). ---
const graphPath = path.join(HERE, "..", "..", "..", "tools", "p0m8", "local_dsp_graph.json");
try {
  const graph = JSON.parse(readFileSync(graphPath, "utf-8"));
  const hops = [["RM062", "RM076"], ["RM076", "RM010"], ["RM010", "RM099"]];
  for (const [outId, inId] of hops) {
    const edge = (graph.adjacency[outId] || []).find((e) => e.in_id === inId);
    check(`${outId}->${inId}: present in the reused-eligibility graph`, !!edge);
    if (edge) check(`${outId}->${inId}: eligibility evidence is tempo_correction 0.0 (near-native, no live stretch needed)`, edge.tempo_correction === 0.0);
  }
} catch (e) {
  check("tools/p0m8/local_dsp_graph.json readable for cross-check", false);
  console.log(`  (${e.message})`);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
