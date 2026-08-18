// Automated, non-browser proof that the Local DSP Live queue schedule is
// gapless and contains >= 5 consecutive transitions, computed from the
// SAME schedule.js module the real Web Audio engine uses at runtime.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { computeQueueSchedule, verifyGapless } from "../src/engine/schedule.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.join(HERE, "..", "src", "data", "queue_manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
  return ok;
}

const { timeline, totalDurationS, transitionCount } = computeQueueSchedule(manifest.items);
const { gapless, issues } = verifyGapless(timeline);

check("queue has exactly 6 items", manifest.items.length === 6);
check("schedule produced 6 timeline entries", timeline.length === 6);
check("transitionCount >= 5 (task requirement)", transitionCount >= 5);
check("schedule is gapless end-to-end (zero-gap, zero-overlap chaining)", gapless);
if (!gapless) console.log("  issues:", JSON.stringify(issues));
check("total session duration is positive and finite", totalDurationS > 0 && Number.isFinite(totalDurationS));
check("first item starts at the lead-in offset, not at t=0", timeline[0].t0 > 0);

for (const entry of timeline) {
  if (entry.mode === "live_two_deck") {
    check(`${entry.tag}: exitAt > t0 (outgoing plays alone before crossfade)`, entry.exitAt > entry.t0);
    check(`${entry.tag}: windowEndAt > exitAt (crossfade window has positive duration)`, entry.windowEndAt > entry.exitAt);
    check(`${entry.tag}: itemEndAt >= windowEndAt (native-tempo tail after crossfade)`, entry.itemEndAt >= entry.windowEndAt);
  } else {
    check(`${entry.tag}: itemEndAt > t0 (baked clip has positive duration)`, entry.itemEndAt > entry.t0);
  }
}

console.log(`\nSchedule summary: ${transitionCount} transitions, total session ${totalDurationS.toFixed(2)}s`);
console.log(`RESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
