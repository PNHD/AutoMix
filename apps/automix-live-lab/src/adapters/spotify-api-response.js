/**
 * Pure Spotify Web API response parsing -- no fetch, no DOM, no class
 * state. Kept separate from SpotifyPublicControlAdapter.js so response
 * SHAPE handling can be unit-tested by constructing fake Response-like
 * objects, exactly like spotify-api-requests.js does for request shapes
 * (see tools/verify_spotify_api_response.mjs).
 *
 * P0-M6-R2 Phase A: the live owner log showed successful Player API
 * write operations (Transfer Playback, Play, Pause, Next, Queue) throwing
 * `Unexpected token ... is not valid JSON`. Spotify Player write
 * endpoints commonly reply `204 No Content` (already handled), but some
 * successful responses arrive as `200` with an EMPTY or plain-text body
 * (not JSON) -- the prior `_api()` unconditionally ran `JSON.parse(text)`
 * on any non-204 response with a non-empty `text`, and any non-JSON
 * truthy text (even whitespace) threw exactly that error. This module
 * makes the success/empty/JSON/text and error/JSON/text/empty cases each
 * an explicit, testable branch instead of one unconditional JSON.parse.
 */

// Kept well under typical Spotify error payload sizes so a sanitized
// error never balloons a log line, while still preserving enough of the
// body to diagnose a real failure.
const MAX_ERROR_TEXT_LENGTH = 300;

/**
 * Defense-in-depth redaction: a bearer token must never reach a thrown
 * error or a log line, even if some future Spotify error body happened to
 * echo an Authorization header back (it doesn't today, but this call site
 * is exactly where such a leak would surface). Real secrets never flow
 * through this path today -- this exists so a future response shape
 * change cannot silently introduce one.
 */
export function sanitizeErrorText(text) {
  if (typeof text !== "string") return "";
  const scrubbed = text.replace(/Bearer\s+[A-Za-z0-9\-._~+/]+=*/gi, "Bearer [REDACTED]");
  return scrubbed.length > MAX_ERROR_TEXT_LENGTH ? `${scrubbed.slice(0, MAX_ERROR_TEXT_LENGTH)}...[TRUNCATED]` : scrubbed;
}

/**
 * Parses one fetch-`Response`-shaped object (`{ status, ok, text() }` --
 * a real `Response` or a test fake) into a deterministic, discriminated
 * result. Never throws for a well-formed HTTP response, successful or
 * not -- the caller (`_api()`) decides whether a non-ok result should
 * become a thrown `SpotifyApiError`.
 *
 * Returned shape: `{ ok, status, body, bodyType }`.
 *   - `ok: true, bodyType: "EMPTY_204"`        -- 204 No Content, `body: null`, never parsed.
 *   - `ok: true, bodyType: "EMPTY_SUCCESS"`    -- 2xx with an empty/whitespace-only body, `body: null`, never parsed.
 *   - `ok: true, bodyType: "JSON"`             -- 2xx with a valid JSON body, `body` is the parsed value.
 *   - `ok: true, bodyType: "TEXT"`             -- 2xx with a non-JSON, non-empty body, `body` is the raw (unsanitized -- it's a SUCCESS body, not an error) text.
 *   - `ok: false, bodyType: "EMPTY_ERROR"`     -- non-2xx with an empty body, `body: null`.
 *   - `ok: false, bodyType: "JSON_ERROR"`      -- non-2xx with a valid JSON error body, `body` is the parsed value (Spotify's documented `{error:{status,message}}` shape).
 *   - `ok: false, bodyType: "TEXT_ERROR"`      -- non-2xx with a non-JSON body, `body` is sanitizeErrorText(text).
 */
export async function parseSpotifyApiResponse(res) {
  const status = res.status;
  if (status === 204) {
    return { ok: true, status, body: null, bodyType: "EMPTY_204" };
  }

  let text = "";
  try {
    text = await res.text();
  } catch {
    text = "";
  }
  const trimmed = typeof text === "string" ? text.trim() : "";
  const okStatus = typeof res.ok === "boolean" ? res.ok : status >= 200 && status < 300;

  if (okStatus) {
    if (trimmed.length === 0) {
      return { ok: true, status, body: null, bodyType: "EMPTY_SUCCESS" };
    }
    try {
      return { ok: true, status, body: JSON.parse(trimmed), bodyType: "JSON" };
    } catch {
      return { ok: true, status, body: text, bodyType: "TEXT" };
    }
  }

  if (trimmed.length === 0) {
    return { ok: false, status, body: null, bodyType: "EMPTY_ERROR" };
  }
  try {
    return { ok: false, status, body: JSON.parse(trimmed), bodyType: "JSON_ERROR" };
  } catch {
    return { ok: false, status, body: sanitizeErrorText(text), bodyType: "TEXT_ERROR" };
  }
}

/**
 * Thrown by `_api()` for any non-ok response. Carries only `method`,
 * `path` (never the full URL with query secrets, and never headers), the
 * HTTP `status`, and the already-parsed/sanitized `body`/`bodyType` from
 * `parseSpotifyApiResponse` -- there is no field on this error that could
 * ever hold an Authorization header or access token.
 */
export class SpotifyApiError extends Error {
  constructor({ method, path, status, body, bodyType }) {
    super(`SPOTIFY_API_ERROR: ${method} ${path} -> ${status}`);
    this.name = "SpotifyApiError";
    this.method = method;
    this.path = path;
    this.status = status;
    this.body = body;
    this.bodyType = bodyType;
  }
}
