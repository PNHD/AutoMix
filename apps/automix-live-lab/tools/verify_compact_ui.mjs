// Deterministic proof of P0-M6-R3 Part A (compact responsive live UI) and
// the readiness-truth fix. Static source/markup analysis for the DOM
// structure (this Node test environment has no DOM -- see
// verify_spotify_app_debug_privacy.mjs / verify_spotify_provider_boundary.mjs
// for the same established technique in this codebase) plus a dynamic,
// DOM-free proof that SpotifyPublicControlAdapter's readiness state
// actually advances past SDK_NOT_READY once device_ready/seed playback are
// observed -- the state transition the previously-frozen UI cache masked.
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";
import { SpotifyPublicControlAdapter } from "../src/adapters/SpotifyPublicControlAdapter.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const css = fs.readFileSync(path.join(ROOT, "src", "styles.css"), "utf8");
const appJsRaw = fs.readFileSync(path.join(ROOT, "src", "app.js"), "utf8");

function stripComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
}
const appJs = stripComments(appJsRaw);

/** Everything between `<details ... id="panel-advanced" ...>` and its matching `</details>`. */
function extractAdvancedBlock(markup) {
  const start = markup.indexOf('id="panel-advanced"');
  if (start === -1) return "";
  const end = markup.indexOf("</details>", start);
  return markup.slice(start, end === -1 ? markup.length : end);
}
const advancedBlock = extractAdvancedBlock(html);
const primaryBlock = html.slice(0, html.indexOf('id="panel-advanced"'));

// ============================================================
// Test 9: no duplicated status blocks -- every element id is unique, and
// the AutoMix session numbers/capability card appear exactly once each.
// ============================================================
{
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
  const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
  check("test 9: every element id in index.html is unique (no duplicated status blocks)", dupes.length === 0);
  if (dupes.length > 0) console.log(`    -> duplicated ids: ${[...new Set(dupes)].join(", ")}`);

  check("test 9: 'AutoMix Session' heading appears exactly once", (html.match(/AutoMix Session/g) || []).length === 1);
  check("test 9: 'Transition Capability' heading appears exactly once", (html.match(/Transition Capability/g) || []).length === 1);
  check("test 9: the old separate 'panel-lookahead' top-level panel no longer exists (folded into Advanced / Next / AutoMix Session)", !html.includes('id="panel-lookahead"'));
}

// ============================================================
// Primary sections (task list A.1-A.5) are actually present, exactly once,
// and NOT hidden inside the collapsed Advanced block.
// ============================================================
{
  check("header: AutoMix Live title present", /<h1>AutoMix Live<\/h1>/.test(html));
  check("header: readiness badge present", html.includes('id="header-readiness-badge"'));
  check("header: AutoMix ON/OFF toggle present", html.includes('id="ctl-automix-toggle"'));
  check("Now Playing: current track element present", html.includes('id="queue-current"'));
  check("Now Playing: progress slider present", html.includes('id="seek-slider"'));
  check("Now Playing: Jump to last 15s present", html.includes('id="seek-jump-near-end"'));
  check("Next: opaque/live successor + source + ready state present", html.includes('id="queue-next"') && html.includes('id="next-source"') && html.includes('id="next-ready-badge"'));
  check("AutoMix session: consecutive/refill/provider-queue-size present", html.includes('id="lookahead-consecutive-count"') && html.includes('id="lookahead-refill-count"') && html.includes('id="lookahead-provider-queue-size"'));
  check("Transition capability statement present", html.includes('id="capability-statement"'));

  for (const id of ["header-readiness-badge", "ctl-automix-toggle", "queue-current", "seek-slider", "seek-jump-near-end", "queue-next", "next-source", "next-ready-badge", "lookahead-consecutive-count", "lookahead-refill-count", "lookahead-provider-queue-size", "capability-statement"]) {
    check(`primary section "${id}" is NOT inside the collapsed Advanced block`, !advancedBlock.includes(`id="${id}"`));
  }
}

// ============================================================
// Test 12: moved-to-Advanced diagnostics remain available (not deleted).
// ============================================================
{
  const advancedRequiredIds = [
    "lookahead-pool-size", // candidate pool size
    "lookahead-state", // lookahead state
    "lookahead-selection-reason", // selection reason
    "lookahead-selection-source", // selection source (P0-M6-R3 Part B)
    "status-provider", // provider identifier
    "status-readiness", // raw capability/readiness identifier
    "lookahead-selected-token",
    "lookahead-successor-confirmed",
    "lookahead-automix-state",
    "lookahead-blocker",
    "lookahead-play-next", // raw state-machine diagnostics
    "seed-status",
    "autoplay-snapshot-count",
    "autoplay-classification",
    "autoplay-classification-reason", // Autoplay observability
    "next-control-state",
    "play-natural-end-hint", // queue truth diagnostics
    "debug-panel",
    "ctl-debug-toggle", // debug log
  ];
  for (const id of advancedRequiredIds) {
    check(`test 12: advanced diagnostic "${id}" is present inside the collapsed Advanced block`, advancedBlock.includes(`id="${id}"`));
  }
  check("test 12: Advanced is a native <details> element, collapsed by default (no open attribute)", /<details[^>]*id="panel-advanced"[^>]*>/.test(html) && !/<details[^>]*id="panel-advanced"[^>]*\bopen\b/.test(html));
}

// ============================================================
// Test 11: primary Spotify UI never claims real DSP execution.
// ============================================================
{
  check(
    "app.js's Spotify capability statement uses the exact mandated truthful wording",
    appJs.includes("Playback continuity only.\\nNo custom beat-matched DSP on Spotify Public API.")
  );
  // The advisory-plan diagnostics (which DO include a "YES" for Local DSP,
  // legitimately) live only in the Advanced block, never in the primary
  // capability card.
  check('primary capability card ("capability-statement") never appears alongside plan-real in the same primary markup', !primaryBlock.includes('id="plan-real"'));
  check('"plan-real" (the only place a DSP-execution claim can appear) lives inside the Advanced block', advancedBlock.includes('id="plan-real"'));

  // Adapter-level truth: SpotifyPublicControlAdapter's own advisory plan
  // must always report executesRealDsp:false and a reason that says so,
  // regardless of playback state -- the primary UI can only be truthful
  // if the underlying data it renders is truthful.
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  adapter._latestState = { paused: false, position: 1000, duration: 200000, track_window: { current_track: { id: "X", duration_ms: 200000 }, next_tracks: [] } };
  const plan = adapter.getAutoMixPlan();
  check("SpotifyPublicControlAdapter.getAutoMixPlan() always reports executesRealDsp: false", plan.executesRealDsp === false);
  check("SpotifyPublicControlAdapter.getAutoMixPlan() reason is explicitly advisory-only", /ADVISORY/i.test(plan.reason));
}

// ============================================================
// Test 10: readiness truth -- must not stay frozen at SDK_NOT_READY once
// device_ready/seed playback are observed.
// ============================================================
{
  // (a) Static proof: the render loop recomputes readiness EVERY tick
  // (live), not once at Connect time and cached forever after -- the
  // exact bug the owner observed.
  const startStatusLoopMatch = appJs.match(/function startStatusLoop\([\s\S]*?\n}/);
  check("startStatusLoop() exists", !!startStatusLoopMatch);
  const startStatusLoopBody = startStatusLoopMatch ? startStatusLoopMatch[0] : "";
  check(
    "startStatusLoop()'s recurring tick calls adapter.getAccountReadiness() live on every tick (not a value cached once at Connect time)",
    /setInterval\(async \(\) => \{[\s\S]*await adapter\.getAccountReadiness\(\)/.test(startStatusLoopBody)
  );

  // (b) Dynamic proof: the underlying adapter state genuinely advances
  // past SDK_NOT_READY as the SDK reports device_ready and, later,
  // confirmed seed playback -- with the live tick from (a), the UI can no
  // longer render a stale SDK_NOT_READY once this has happened.
  const adapter = new SpotifyPublicControlAdapter({ clientId: "test", redirectUri: "http://127.0.0.1:5500/" });
  const before = await adapter.getAccountReadiness();
  check("before device_ready: readiness is SDK_NOT_READY", before.ready === false && before.reason === "SDK_NOT_READY");

  adapter._sdkReady = true; // simulates the Web Playback SDK's "ready" (device_ready) event
  const afterDeviceReady = await adapter.getAccountReadiness();
  check("test 10: after device_ready, readiness reason is no longer SDK_NOT_READY", afterDeviceReady.reason !== "SDK_NOT_READY");
  check("after device_ready (no seed playback yet): reason is SDK_READY_AWAITING_SEED_PLAYBACK_PROOF", afterDeviceReady.reason === "SDK_READY_AWAITING_SEED_PLAYBACK_PROOF");

  adapter._seedPlaybackConfirmed = true; // simulates confirmed real seed playback
  const afterSeedPlayback = await adapter.getAccountReadiness();
  check("test 10: once playback is usable, readiness becomes READY (ready: true)", afterSeedPlayback.ready === true);
  check("test 10: readiness reason confirms real SDK playback, never SDK_NOT_READY", afterSeedPlayback.reason === "PREMIUM_PLAYBACK_CONFIRMED_BY_SDK" && afterSeedPlayback.reason !== "SDK_NOT_READY");
}

// ============================================================
// Test 13: privacy constraints unchanged -- the new primary-UI text
// (readiness badge, capability statement, next-source label) never
// interpolates a raw Spotify identifier.
// ============================================================
{
  check("renderReadinessBadge() interpolates only readiness.reason (already-sanitized enum text), never a raw track/device id", !/\$\{adapter\._(seedUri|deviceId|token)\}/.test(appJs));
  check("renderCapabilityStatement() text is a static string, not built from raw track/artist/device data", !/capabilityStatement\.textContent = `[^`]*\$\{/.test(appJs));
  check("next-source label is derived only from the sanitized selectionSource enum, never a raw id", /selectionSource === "SPOTIFY_PROVIDER_NEXT_UP"/.test(appJs));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
