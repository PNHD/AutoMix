// Verifies generateCodeChallenge() against the official RFC 7636 Appendix B
// test vector (S256), and sanity-checks buildAuthorizeUrl()'s query shape
// against Spotify's documented PKCE authorize parameters. Node-only (no
// browser needed) via the webcrypto shim.
import { webcrypto } from "node:crypto";
if (!globalThis.crypto) globalThis.crypto = webcrypto;

import { generateCodeChallenge, generateCodeVerifier, buildAuthorizeUrl } from "../src/adapters/spotify-pkce.js";

let checks = 0;
let passed = 0;
function check(name, cond) {
  checks += 1;
  const ok = !!cond;
  if (ok) passed += 1;
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}`);
}

// RFC 7636 Appendix B official example.
const RFC_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
const RFC_EXPECTED_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM";

const actual = await generateCodeChallenge(RFC_VERIFIER);
check("S256 code_challenge matches RFC 7636 Appendix B test vector", actual === RFC_EXPECTED_CHALLENGE);

const v1 = generateCodeVerifier();
const v2 = generateCodeVerifier();
check("generateCodeVerifier produces 64-char strings", v1.length === 64);
check("generateCodeVerifier is non-deterministic across calls", v1 !== v2);
check("generateCodeVerifier only uses PKCE-unreserved charset", /^[A-Za-z0-9\-._~]+$/.test(v1));

const url = buildAuthorizeUrl({
  clientId: "TEST_CLIENT_ID",
  redirectUri: "http://127.0.0.1:8080/callback.html",
  scopes: ["user-read-email", "streaming"],
  codeChallenge: actual,
  state: "teststate123",
});
const parsed = new URL(url);
check("authorize URL host is accounts.spotify.com", parsed.host === "accounts.spotify.com");
check("authorize URL path is /authorize", parsed.pathname === "/authorize");
check("authorize URL sets response_type=code", parsed.searchParams.get("response_type") === "code");
check("authorize URL sets code_challenge_method=S256", parsed.searchParams.get("code_challenge_method") === "S256");
check("authorize URL carries the exact code_challenge computed above", parsed.searchParams.get("code_challenge") === actual);
check("authorize URL carries client_id", parsed.searchParams.get("client_id") === "TEST_CLIENT_ID");
check("authorize URL carries redirect_uri unmodified", parsed.searchParams.get("redirect_uri") === "http://127.0.0.1:8080/callback.html");
check("authorize URL never contains a client secret", !url.includes("secret"));

console.log(`\nRESULT: ${passed}/${checks} PASS`);
process.exit(passed === checks ? 0 : 1);
