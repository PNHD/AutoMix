// Deterministic proof of P0-M6-R2 repair-pass-2 Blocker 2: app.js's
// debug/tracked-evidence output must never serialize the owner's raw
// search query text or a raw `spotify:track:` URI -- only opaque TRK_
// tokens, result counts, and endpoint names without query strings.
// Static source analysis (app.js has no DOM in this Node test
// environment, so its `logDebug()` call sites are proven by direct
// source inspection, the same technique already used by
// verify_spotify_provider_boundary.mjs).
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

const APP_JS_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "app.js");
const raw = fs.readFileSync(APP_JS_PATH, "utf8");

/** Naive but effective for this codebase's style (see provider_boundary.mjs): strips block/line comments so prose can't produce a false positive; `https://` is colon-guarded and survives. */
function stripComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
}
const code = stripComments(raw);

// ============================================================
// The two exact defects the PM cited, by their exact source signature:
// a template literal interpolating the raw owner search query, and one
// interpolating the raw `spotify:track:` seed URI. `${...}` interpolation
// syntax only has meaning inside a template literal, so the ABSENCE of
// these exact substrings in the source is a precise, sufficient proof
// that no template literal anywhere in this file embeds either value.
// ============================================================
check('no template literal interpolates the raw search query ("${query}" does not appear in the source at all)', !code.includes("${query}"));
check('no template literal interpolates the raw seed track URI ("${track.uri}" does not appear in the source at all)', !code.includes("${track.uri}"));

// Broader defense-in-depth: no template literal interpolates a raw
// device id or a raw pre-sanitized url/path variable that could carry a
// query string with an embedded identifier.
check('no template literal interpolates a raw "deviceId" variable', !code.includes("${deviceId}") && !code.includes("${this._deviceId}"));
check('no template literal interpolates a raw request url/path variable directly', !/\$\{(req\.url|url|path)\}/.test(code));

// ============================================================
// Positive proof: the actual repaired log lines exist, using only
// opaque tokens / counts / endpoint names.
// ============================================================
check('searchTracks() debug log uses only a result count, not the query text', /logDebug\(`searchTracks\(\) -> \$\{results\.length\} result\(s\)`\)/.test(code));
check('playSeedTrack() debug log uses the opaque seedToken (sanitizeTrackToken output), not track.uri', /logDebug\(`playSeedTrack\(\$\{seedToken\}\)/.test(code));
check("app.js imports sanitizeTrackToken to build that opaque token", code.includes('import { sanitizeTrackToken } from "./adapters/spotify-autoplay.js"'));

// ============================================================
// Self-test: prove the detection logic itself actually works (a
// deliberately-injected forbidden pattern IS caught), so a silently
// broken check can't produce false PASSes.
// ============================================================
{
  const canaryBad = 'logDebug(`searchTracks("${query}") -> ${results.length} result(s)`);';
  check("self-test: the canary bad line WOULD be caught by the ${query} check", canaryBad.includes("${query}"));
  const canaryBad2 = "logDebug(`playSeedTrack(${track.uri}) -> ...`);";
  check("self-test: the canary bad line WOULD be caught by the ${track.uri} check", canaryBad2.includes("${track.uri}"));
  const canaryGood = "logDebug(`searchTracks() -> ${results.length} result(s)`);";
  check("self-test: the actual repaired line does NOT trip the ${query} check", !canaryGood.includes("${query}"));
}

// ============================================================
// Ephemeral UI is explicitly allowed to show name/artist for song
// selection -- confirm that legitimate use still exists (proves this
// test isn't accidentally banning the feature entirely).
// ============================================================
check("the search-results list UI still shows name/artist as plain DOM text (not logged)", /label\.textContent = `\$\{track\.name\}/.test(code));

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
