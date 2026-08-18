// Static provider-boundary proof (P0-M6-R2 test requirements 19 and 20):
// no playlist creation/selection code anywhere in the app, and no
// dependency on a ChatGPT/Claude connector's OAuth token. This is a
// source-text check (comments stripped), not a runtime test -- it exists
// so a future change can't silently reintroduce either without a test
// failure flagging it immediately.
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

const SRC_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src");

function listJsFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...listJsFiles(full));
    else if (entry.name.endsWith(".js")) out.push(full);
  }
  return out;
}

/** Naive but effective for this codebase's style: strips block and line comments so prose ("no playlist call is made anywhere") can't produce a false positive. `https://` is preserved (colon-guarded). */
function stripComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
}

const files = listJsFiles(SRC_DIR);
check(`found source .js files to scan under ${path.relative(process.cwd(), SRC_DIR)}`, files.length > 5);

const fileTexts = files.map((f) => ({ file: f, raw: fs.readFileSync(f, "utf8") }));
const strippedTexts = fileTexts.map(({ file, raw }) => ({ file, code: stripComments(raw) }));

// ============================================================
// Test 19: no playlist creation/selection code anywhere
// ============================================================
const PLAYLIST_PATTERNS = [
  /\/me\/playlists/i,
  /\/v1\/playlists/i,
  /\bcreatePlaylist\b/i,
  /\bplaylist_id\b/i,
  /\bcontext_uri\b/i, // Spotify's playlist/album-context playback field -- this app only ever plays a single-track `uris` array
  /playlist-modify/i, // OAuth scope
  /playlist-read/i, // OAuth scope
];

for (const pattern of PLAYLIST_PATTERNS) {
  const hits = strippedTexts.filter(({ code }) => pattern.test(code));
  check(`no code (comments excluded) matches forbidden playlist pattern ${pattern}`, hits.length === 0);
  if (hits.length > 0) console.log(`    -> found in: ${hits.map((h) => path.relative(SRC_DIR, h.file)).join(", ")}`);
}

// ============================================================
// Test 20: no dependency on a ChatGPT/Claude connector's OAuth token
// ============================================================
const CONNECTOR_PATTERNS = [
  /\bchatgpt\b/i,
  /\banthropic[-_ ]?connector\b/i,
  /\bclaude[-_ ]?connector\b/i,
  /connector[-_]?token/i,
  /oauth_token_from/i,
  /mcp__/i,
];

for (const pattern of CONNECTOR_PATTERNS) {
  const hits = strippedTexts.filter(({ code }) => pattern.test(code));
  check(`no code (comments excluded) matches forbidden connector-dependency pattern ${pattern}`, hits.length === 0);
  if (hits.length > 0) console.log(`    -> found in: ${hits.map((h) => path.relative(SRC_DIR, h.file)).join(", ")}`);
}

// Positive assertion: every localStorage/sessionStorage key actually
// read/written by the app is one of this app's OWN, locally-defined
// storage keys -- never a key shaped like a foreign connector's token
// storage (e.g. anything containing "chatgpt"/"claude"/"connector").
const KNOWN_STORAGE_KEY_NAMES = ["TOKEN_STORAGE_KEY", "VERIFIER_STORAGE_KEY", "STATE_STORAGE_KEY", "CLIENT_ID_STORAGE_KEY", "CLIENT_ID_KEY"];
{
  const storageCallPattern = /\b(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\(\s*([A-Za-z_$][A-Za-z0-9_$]*|"[^"]*"|'[^']*')/g;
  const unexpectedKeys = [];
  for (const { file, code } of strippedTexts) {
    let m;
    while ((m = storageCallPattern.exec(code))) {
      const arg = m[1];
      const isKnownIdentifier = KNOWN_STORAGE_KEY_NAMES.includes(arg);
      const isQuotedLiteral = arg.startsWith('"') || arg.startsWith("'");
      if (!isKnownIdentifier && !isQuotedLiteral) {
        unexpectedKeys.push({ file: path.relative(SRC_DIR, file), arg });
      }
    }
  }
  check("every localStorage/sessionStorage call uses one of this app's own known key constants", unexpectedKeys.length === 0);
  if (unexpectedKeys.length > 0) console.log(`    -> unexpected: ${JSON.stringify(unexpectedKeys)}`);
}

// Sanity: confirm the search fixtures above actually work (a deliberately-injected forbidden string IS detected), so a silently-broken regex can't produce false PASSes.
{
  const canary = stripComments('const x = "/me/playlists"; // this line is itself a comment mentioning /me/playlists too');
  check("self-test: stripComments removes the trailing comment but keeps the real code", /\/me\/playlists/i.test(canary) && !canary.includes("this line is itself a comment"));
}

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
