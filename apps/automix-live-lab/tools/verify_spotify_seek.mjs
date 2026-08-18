// Deterministic proof of the pure seek math + drag/commit controller
// (owner-requested Section A/D, near-end probe UI). No DOM, no network.
import {
  clampSeekTargetMs,
  computeNearEndProbeTargetMs,
  isSeekControlEnabled,
  createSeekDragController,
  SEEK_TRAILING_GUARD_MS,
  NEAR_END_PROBE_WINDOW_MS,
} from "../src/adapters/spotify-seek.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// --- D.2 target clamping ---
check("clampSeekTargetMs clamps within [0, duration - guard]", clampSeekTargetMs(50_000, 200_000) === 50_000);
check("clampSeekTargetMs clamps a target past the end down to duration - guard", clampSeekTargetMs(999_000, 200_000) === 200_000 - SEEK_TRAILING_GUARD_MS);
check("clampSeekTargetMs clamps a negative target up to 0", clampSeekTargetMs(-5000, 200_000) === 0);
check("clampSeekTargetMs returns 0 for a non-finite/zero/negative duration", clampSeekTargetMs(5000, 0) === 0 && clampSeekTargetMs(5000, -1) === 0 && clampSeekTargetMs(5000, NaN) === 0);
check("clampSeekTargetMs treats a non-finite target as 0", clampSeekTargetMs(NaN, 200_000) === 0);

// --- D.1 near-end target calculation ---
check("computeNearEndProbeTargetMs targets duration - 15000ms", computeNearEndProbeTargetMs(180_000) === 180_000 - NEAR_END_PROBE_WINDOW_MS);
check("computeNearEndProbeTargetMs on a short (<15s) track clamps safely to 0, never negative", computeNearEndProbeTargetMs(8000) === 0);
check("computeNearEndProbeTargetMs on a track just over 15s still respects the trailing guard", computeNearEndProbeTargetMs(15_500) === clampSeekTargetMs(500, 15_500));
check("computeNearEndProbeTargetMs never exceeds duration - SEEK_TRAILING_GUARD_MS", computeNearEndProbeTargetMs(180_000) <= 180_000 - SEEK_TRAILING_GUARD_MS);

// --- isSeekControlEnabled ---
const baseEnabled = { sdkReady: true, hasCurrentTrack: true, durationMs: 180_000, disallowsSeeking: false };
check("isSeekControlEnabled is true when every condition holds", isSeekControlEnabled(baseEnabled) === true);
check("isSeekControlEnabled is false when SDK not ready", isSeekControlEnabled({ ...baseEnabled, sdkReady: false }) === false);
check("isSeekControlEnabled is false with no current track", isSeekControlEnabled({ ...baseEnabled, hasCurrentTrack: false }) === false);
check("isSeekControlEnabled is false with zero/unknown duration", isSeekControlEnabled({ ...baseEnabled, durationMs: 0 }) === false);
check("isSeekControlEnabled is false when Spotify reports disallows.seeking", isSeekControlEnabled({ ...baseEnabled, disallowsSeeking: true }) === false);

// --- D.3/D.4: drag vs commit controller ---
{
  const seekCalls = [];
  const controller = createSeekDragController({ seekFn: (ms) => seekCalls.push(ms), getDurationMs: () => 200_000 });

  controller.onDragStart(10_000);
  controller.onDrag(20_000);
  controller.onDrag(35_000);
  controller.onDrag(50_000);
  check("D.4: no seek call while merely dragging (3 drag events, 0 seek calls)", seekCalls.length === 0);
  check("displayValueMs reflects the latest drag position without seeking", controller.displayValueMs === 50_000);
  check("isDragging is true mid-drag", controller.isDragging === true);

  controller.onCommit(50_000);
  check("D.3: exactly ONE seek call is issued on commit", seekCalls.length === 1);
  check("the committed seek call carries the clamped target", seekCalls[0] === 50_000);
  check("isDragging is false after commit", controller.isDragging === false);

  // A second independent drag+commit cycle must not accumulate extra calls.
  controller.onDrag(70_000);
  controller.onDrag(90_000);
  controller.onCommit(999_000); // past duration -- must clamp
  check("a second commit still issues exactly one more seek call (2 total)", seekCalls.length === 2);
  check("an out-of-range commit target is clamped before reaching seekFn", seekCalls[1] === 200_000 - SEEK_TRAILING_GUARD_MS);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
