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

/** Substring from the first occurrence of `startMarker` up to the next occurrence of `endMarker` (searched after startMarker), or null if either isn't found. */
function sliceBetween(text, startMarker, endMarker) {
  const s = text.indexOf(startMarker);
  if (s === -1) return null;
  const e = text.indexOf(endMarker, s + startMarker.length);
  if (e === -1) return null;
  return text.slice(s, e);
}

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

// ============================================================
// P0-M6-R3-PREOWNER UI Defect 1: hide Spotify credential setup from the
// primary dashboard once connect() succeeds, but keep it recoverable from
// Advanced without ever clearing the stored Client ID, and without
// breaking reauth.
// ============================================================
{
  // app.js has TWO "els.ctlConnect.onclick = async () => {" assignments
  // (one inside activateLocal(), one inside activateSpotify()) -- must
  // scope to the Spotify one specifically, not just the first match.
  const activateSpotifyBody = appJs.slice(appJs.indexOf("async function activateSpotify()"), appJs.indexOf("els.spotifySaveClientId.onclick"));
  check("defect 1 test: activateSpotify()'s body is present in app.js", activateSpotifyBody.length > 0);
  const connectHandlerBody = sliceBetween(activateSpotifyBody, "els.ctlConnect.onclick = async () => {", "els.ctlPlay.onclick");
  check("defect 1 test: the Spotify-mode ctlConnect handler body is present in app.js", !!connectHandlerBody);

  const reauthMarker = "SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES";
  const notAuthMarker = 'reason.startsWith("NOT_AUTHENTICATED")';
  const lastEarlyReturnIdx = connectHandlerBody ? connectHandlerBody.lastIndexOf(notAuthMarker) : -1;
  const earlyReturnsOnly = connectHandlerBody && lastEarlyReturnIdx !== -1 ? connectHandlerBody.slice(0, lastEarlyReturnIdx) : "";
  const successPathOnly = connectHandlerBody && lastEarlyReturnIdx !== -1 ? connectHandlerBody.slice(lastEarlyReturnIdx) : "";
  check("test 1 setup: both early-return branches (reauth-required, not-authenticated) are present", !!connectHandlerBody && connectHandlerBody.includes(reauthMarker) && connectHandlerBody.includes(notAuthMarker));
  check("test 1: once connect() actually succeeds, the Spotify setup form is hidden from the primary dashboard", /els\.spotifySetup\.classList\.add\(\s*"hidden"\s*\)/.test(successPathOnly));
  check("test 1: the hide is NOT inside either early-return branch (reauth-required / not-authenticated) -- only the success path hides it", !earlyReturnsOnly.includes('els.spotifySetup.classList.add("hidden")'));

  check('test 2: index.html exposes a "Change Spotify setup" control inside the collapsed Advanced block', advancedBlock.includes('id="ctl-change-spotify-setup"'));
  check("test 2: that control is NOT duplicated as a second Client ID input inside Advanced (the setup form itself stays in Controls, only toggled)", !advancedBlock.includes('id="spotify-client-id"'));
  const changeSetupHandler = sliceBetween(appJs, "els.ctlChangeSpotifySetup.onclick = () => {", "els.ctlDebugToggle.onclick");
  check("test 2: the Change-Spotify-setup control toggles the setup form's visibility (recoverable, not deleted)", !!changeSetupHandler && /els\.spotifySetup\.classList\.toggle\(\s*"hidden"\s*\)/.test(changeSetupHandler));
  check("test 2: the Change-Spotify-setup control never clears the stored Client ID", !!changeSetupHandler && !changeSetupHandler.includes("removeItem(CLIENT_ID_KEY)") && !changeSetupHandler.includes("removeItem(CLIENT_ID_STORAGE_KEY)"));
  check("test 2: reauth is still reachable from the SAME connect handler -- beginLogin() is still called on the reauth/not-authenticated branches, unchanged", !!connectHandlerBody && /await adapter\.beginLogin\(\);/g.test(connectHandlerBody));
  check("test 2: before authentication, the setup form is still shown by default when entering Spotify Live mode (unchanged golden path)", /els\.spotifySetup\.classList\.remove\(\s*"hidden"\s*\);/.test(appJs));
}

// ============================================================
// P0-M6-R3-PREOWNER UI Defect 2: collapse/clear the search-results list
// once a seed is confirmed playing, replaced by a small "Change seed"
// control that restores (never auto-runs) the search workflow.
// ============================================================
{
  const collapseFn = appJs.match(/function collapseSeedSearch\(\)[\s\S]*?\n}/)?.[0] || "";
  check("test 3: collapseSeedSearch() exists", collapseFn.length > 0);
  check("test 3: collapseSeedSearch() clears the search-results list", /seedResults\.innerHTML = ""/.test(collapseFn));
  check("test 3: collapseSeedSearch() hides the search input/button/results container", /seedSearchControls\.classList\.add\(\s*"hidden"\s*\)/.test(collapseFn));
  check("test 3: collapseSeedSearch() reveals the small 'Change seed' control", /ctlChangeSeed\.classList\.remove\(\s*"hidden"\s*\)/.test(collapseFn));
  check("test 3: collapseSeedSearch() never touches Now Playing's own elements (queueCurrent/seekSlider untouched)", !/queueCurrent|seekSlider/.test(collapseFn));

  const playAsSeedHandler = sliceBetween(appJs, "btn.onclick = async () => {", "} catch (e) {");
  check("test 3: the 'Play as seed' handler calls collapseSeedSearch() only after playSeedTrack() actually succeeds (inside the try block, after the await)", !!playAsSeedHandler && /await adapter\.playSeedTrack\(track\.uri\);[\s\S]*collapseSeedSearch\(\);/.test(playAsSeedHandler));

  const restoreFn = appJs.match(/function restoreSeedSearch\(\)[\s\S]*?\n}/)?.[0] || "";
  check("test 4: restoreSeedSearch() exists", restoreFn.length > 0);
  check("test 4: restoreSeedSearch() reveals the search input/button/results container", /seedSearchControls\.classList\.remove\(\s*"hidden"\s*\)/.test(restoreFn));
  check("test 4: restoreSeedSearch() hides the 'Change seed' control", /ctlChangeSeed\.classList\.add\(\s*"hidden"\s*\)/.test(restoreFn));
  check("test 4: 'Change seed' never triggers a search or plays/changes a track by itself (no searchTracks/playSeedTrack call in restoreSeedSearch())", !/searchTracks|playSeedTrack/.test(restoreFn));
  check("test 4: the 'Change seed' button is wired to call restoreSeedSearch() and nothing else", /els\.ctlChangeSeed\.onclick = \(\) => restoreSeedSearch\(\);/.test(appJs));
  const activateSpotifySetupSection = appJs.slice(appJs.indexOf("async function activateSpotify()"), appJs.indexOf("const adapter = new SpotifyPublicControlAdapter"));
  check("test 4: entering/reactivating Spotify Live mode resets to the default search-visible state (a fresh adapter has no seed yet)", /restoreSeedSearch\(\);/.test(activateSpotifySetupSection));
}

// ============================================================
// Tests 5 & 6: the primary post-auth/post-seed screenshot state contains
// neither the Client ID input nor the redirect URI. Proven structurally:
// both live inside the exact single `#spotify-setup` container that test
// 1 proves is hidden once connect() succeeds, and neither appears
// anywhere else in the primary markup.
// ============================================================
{
  const setupBlock = sliceBetween(html, 'id="spotify-setup"', "</div>");
  check("test 5: the Client ID input lives inside the #spotify-setup container (the one hidden on connect success)", !!setupBlock && setupBlock.includes('id="spotify-client-id"'));
  check("test 6: the redirect URI hint lives inside the SAME #spotify-setup container", !!setupBlock && setupBlock.includes('id="redirect-uri-hint"'));
  check("test 5: no element outside #spotify-setup in the primary markup contains the Client ID input", (primaryBlock.match(/id="spotify-client-id"/g) || []).length === 1);
  check("test 6: no element outside #spotify-setup in the primary markup contains the redirect URI hint", (primaryBlock.match(/id="redirect-uri-hint"/g) || []).length === 1);
  check("test 5/6: neither id appears a second time anywhere in the whole document (Advanced included)", (html.match(/id="spotify-client-id"/g) || []).length === 1 && (html.match(/id="redirect-uri-hint"/g) || []).length === 1);
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
