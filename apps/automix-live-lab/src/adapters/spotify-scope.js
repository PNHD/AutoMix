/**
 * Pure OAuth scope comparison helpers (P0-M6-R2 repair, Blocker 1). No
 * fetch, no DOM, no localStorage -- `SpotifyPublicControlAdapter.js`
 * calls these against the scope set stored alongside a token to decide
 * whether that token still covers everything `SPOTIFY_SCOPES` currently
 * requires, before ever attempting to use it.
 */

/** Spotify's token/refresh responses carry `scope` as a single space-separated string. */
export function parseScopeString(scopeStr) {
  if (typeof scopeStr !== "string" || scopeStr.trim().length === 0) return [];
  return scopeStr.trim().split(/\s+/);
}

/**
 * True only when every scope in `requiredScopes` is present in
 * `grantedScopes`. A legacy stored token with no `scope` metadata at all
 * (not an array) is never sufficient -- it must be treated as stale
 * rather than assumed to already cover new scopes.
 */
export function hasAllRequiredScopes(grantedScopes, requiredScopes) {
  if (!Array.isArray(grantedScopes)) return false;
  const granted = new Set(grantedScopes);
  return requiredScopes.every((s) => granted.has(s));
}

/** The exact scopes `requiredScopes` needs that `grantedScopes` does not have -- for diagnostics, never for enforcement decisions (use `hasAllRequiredScopes` for that). */
export function missingScopes(grantedScopes, requiredScopes) {
  const granted = new Set(Array.isArray(grantedScopes) ? grantedScopes : []);
  return requiredScopes.filter((s) => !granted.has(s));
}
