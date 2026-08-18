/**
 * Spotify Authorization Code with PKCE helpers -- fully client-side, no
 * client secret, per Spotify's documented PKCE flow
 * (https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow).
 * Uses only Web Crypto (`crypto.subtle`), available in browsers and under
 * Node's `node:crypto` webcrypto shim for isomorphic unit testing (see
 * tools/verify_pkce.mjs).
 */

function base64UrlEncode(bytes) {
  let binary = "";
  const arr = new Uint8Array(bytes);
  for (let i = 0; i < arr.byteLength; i++) binary += String.fromCharCode(arr[i]);
  const b64 = (typeof btoa === "function" ? btoa(binary) : Buffer.from(binary, "binary").toString("base64"));
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function generateCodeVerifier(length = 64) {
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  const randomVals = new Uint8Array(length);
  globalThis.crypto.getRandomValues(randomVals);
  let out = "";
  for (let i = 0; i < length; i++) out += possible[randomVals[i] % possible.length];
  return out;
}

export async function generateCodeChallenge(verifier) {
  const data = new TextEncoder().encode(verifier);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", data);
  return base64UrlEncode(digest);
}

export function buildAuthorizeUrl({ clientId, redirectUri, scopes, codeChallenge, state }) {
  const url = new URL("https://accounts.spotify.com/authorize");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", codeChallenge);
  url.searchParams.set("scope", scopes.join(" "));
  url.searchParams.set("state", state);
  return url.toString();
}

export async function exchangeCodeForToken({ clientId, redirectUri, code, codeVerifier }) {
  const body = new URLSearchParams({
    client_id: clientId,
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
    code_verifier: codeVerifier,
  });
  const res = await fetch("https://accounts.spotify.com/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`SPOTIFY_TOKEN_EXCHANGE_FAILED: ${res.status} ${text}`);
  }
  return res.json(); // { access_token, token_type, expires_in, refresh_token, scope }
}

export async function refreshAccessToken({ clientId, refreshToken }) {
  const body = new URLSearchParams({
    client_id: clientId,
    grant_type: "refresh_token",
    refresh_token: refreshToken,
  });
  const res = await fetch("https://accounts.spotify.com/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`SPOTIFY_TOKEN_REFRESH_FAILED: ${res.status}`);
  return res.json();
}

export const SPOTIFY_SCOPES = Object.freeze([
  "user-read-private",
  "user-read-email",
  "user-read-playback-state",
  "user-modify-playback-state",
  "user-read-currently-playing",
  "playlist-read-private",
  "user-library-read",
  "streaming",
]);
