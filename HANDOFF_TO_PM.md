## HANDOFF TO PM — P0-M6-R1 SEED IDENTITY REPAIR (REPAIR PASS 2)

### RESULT

`OWNER_SPOTIFY_AUTH_REQUIRED` for the Spotify lane (bounded repair complete; the only remaining blocker is a real Spotify Developer Client ID). The Local DSP Live lane is **unchanged and not rerun this pass**, per the PM comment's own instruction -- its prior evidence (6 consecutive live transitions, real browser playback) still stands. The DJ-partner audit is unchanged: `SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`.

### REPO / BRANCH / HEAD

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab`
- Starting HEAD for this repair (verified live before starting, matched PM's independently-confirmed SHA exactly): `85af4c91cd257969337a0560ff045d15586d31c9`
- `main`: untouched at `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`
- `research/p0-feasibility`: untouched at `5139411c8d94d7407e5d9c244b4e9275f30a8221`
- Code-repair commit: `aaf3943f4553576e2e215d7e16eb2e6f739a5e2f` ("fix(app): P0-M6-R1 seed identity + manual-attribution repair (repair pass 2) ...") directly on top of `85af4c9`. This is the commit containing the actual code repair.
- **Exact final HEAD after push:** this HANDOFF_TO_PM.md commit itself, immediately on top of `aaf3943` (this file cannot self-embed its own post-commit hash) -- independently confirmable via `git log --oneline -3` on `prototype/live-automix-lab`, exactly the same two-step pattern used in both prior repair rounds.

### WHAT WAS REPAIRED (PM finding `P0_M6_R1_SEED_IDENTITY_REPAIR_REQUIRED`, Issue #11 comment `5324583196`)

- **BLOCKER 1 (seed token hashed the URI while runtime snapshots hashed the bare track id):** `playSeedTrack(uri)` stored `sanitizeTrackToken(uri)` (`spotify:track:<id>`), while `_onPlayerStateChanged`/`captureSnapshot` hashed `current_track.id` (bare `<id>`) -- two different strings could never hash equal for the same song, so `_seedPlaybackConfirmed` could never become true and the seed's own first playback could be misread as a non-seed continuation. Repaired at the single hashing entry point: `sanitizeTrackToken` (`apps/automix-live-lab/src/adapters/spotify-autoplay.js`) now canonicalizes id-vs-uri via a new pure helper, `canonicalTrackId`, before hashing. `token(<id>) === token(spotify:track:<id>)` by construction; no parsing logic duplicated anywhere else -- every call site (seed selection, runtime state comparison) automatically inherits the fix.
- **BLOCKER 2 (manual-next attribution cleared too early):** the prior `_manualActionPending` boolean cleared on the FIRST `player_state_changed` event after a manual `next()`/`seek()` call, even if that event still showed the same track (the SDK can fire multiple state events per user action). A later, still-manually-caused track-change event could then arrive with the flag already cleared and be misclassified as Spotify Autoplay. Repaired with a small state machine (`beginManualAction`/`resolveManualAttribution`, same module) that stays attributed across same-track intermediate events and resolves only when the current track actually changes, or after one fixed bounded timeout (`MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS = 8000`ms, not pair/song-specific).

### FILES CHANGED THIS REPAIR

```
Modified:
  apps/automix-live-lab/src/adapters/spotify-autoplay.js
  apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js
  docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md
  HANDOFF_TO_PM.md (this file)

New:
  apps/automix-live-lab/tools/verify_spotify_seed_identity.mjs
```

Not touched this pass: everything under `apps/automix-live-lab/src/engine/`, `apps/automix-live-lab/src/adapters/LocalDSPPlaybackAdapter.js`, `apps/automix-live-lab/src/data/queue_manifest.json`, `apps/automix-live-lab/index.html`, `apps/automix-live-lab/src/app.js`, `apps/automix-live-lab/src/adapters/spotify-api-requests.js`, `apps/automix-live-lab/src/adapters/spotify-pkce.js`, `apps/automix-live-lab/src/adapters/PlaybackAdapter.js`, `apps/automix-live-lab/src/adapters/SpotifyDJPartnerPlaybackAdapter.js` -- this is a bounded, code-level repair, not a UI or scope change. No files under `tools/p0m5/` or existing `docs/research/P0-M5-R1*` content were touched.

### VALIDATION (commands run, exact results)

```
node apps/automix-live-lab/tools/verify_spotify_seed_identity.mjs
  -> 24/24 PASS (NEW, INTEGRATION-level -- drives the real
     SpotifyPublicControlAdapter class with synthetic Web Playback SDK
     state objects through _onPlayerStateChanged/next()/seek(), proving:
     token(<id>) === token(spotify:track:<id>); a URI-selected seed is
     recognized isSeedStillCurrent=true and confirms playback when the
     SDK reports it by bare id, never misclassified as continuation;
     only a genuinely different track id becomes continuation evidence;
     the full manual-Next -> intermediate same-track event -> changed-
     track event sequence stays attributed and does not classify as
     Autoplay; the bounded timeout is enforced; sanitized snapshot
     privacy still holds -- no raw id/uri/title/artist text leaks)

Full regression rerun (all previously-passing suites, all unchanged):
node apps/automix-live-lab/tools/verify_spotify_search.mjs      -> 17/17 PASS
node apps/automix-live-lab/tools/verify_spotify_play_seed.mjs   -> 10/10 PASS
node apps/automix-live-lab/tools/verify_spotify_autoplay.mjs    -> 18/18 PASS
node apps/automix-live-lab/tools/verify_pkce.mjs                -> 12/12 PASS
node apps/automix-live-lab/tools/verify_schedule.mjs            -> 22/22 PASS
  (Local DSP engine untouched; its 193s live session was NOT rerun,
   per this PM comment's explicit instruction)

Real-browser smoke check (Browser tool, http://127.0.0.1:5500/):
  app loads cleanly, zero console errors, after the repair. Local DSP
  Live's Connect button was deliberately NOT clicked this pass.
```

Combined this pass: 24 new automated PASS checks + 79 regression-rerun PASS checks (17+10+18+12+22) = **103/103, 0 FAIL**.

### AC CHECK (against PM comment `5324583196`)

| Requirement | Status | Evidence |
|---|---|---|
| One canonical track-identity helper, no duplicated parsing | PASS | `canonicalTrackId` in `spotify-autoplay.js`; `sanitizeTrackToken` is its only caller for hashing, and it is the ONLY function `SpotifyPublicControlAdapter.js` calls for tokenization |
| `token(<id>) === token(spotify:track:<id>)` | PASS | `verify_spotify_seed_identity.mjs`, checks 1&4 |
| URI-selected seed recognized on bare-id SDK event: `isSeedStillCurrent=true`, seed confirmed, not continuation | PASS | same file, checks 6-8 |
| Only a genuinely different track id becomes continuation evidence | PASS | same file, checks 9-10 |
| Sanitized snapshot privacy still holds | PASS | same file, checks 21-24 |
| Manual Next stays attributed through intermediate same-track event, resolves on actual change | PASS | same file, checks 12-16 |
| Bounded, non-pair-specific timeout | PASS | `MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS` constant; checks 17-19 |
| Deterministic sequence test: manual Next -> intermediate same-track -> changed-track, final event manual and not Autoplay | PASS | same file, checks 11-16 |
| Preserve search-one-track / one-URI seed / no playlist / next_tracks observation / four classes / no Recommendations / four scopes / SDK-based readiness | PASS, unmodified | none of these files touched this pass |
| Local DSP unchanged, 193s not rerun | PASS | engine files untouched; only `verify_schedule.mjs` rerun as a cheap regression check |
| Run all existing + new tests | PASS | 103/103 |
| Stay on branch; don't touch main/research | PASS | verified via `git rev-parse` |
| Push branch; verify origin HEAD exact | PASS | see PM_REVIEW_REQUEST |
| Do not broaden scope | PASS | zero scope/UI/product changes this pass |

### UNKNOWNS / RISKS

- Unchanged from the prior handoff: real Spotify search/seed-playback/Autoplay-classification outcomes remain `UNKNOWN_NEEDS_PROOF` until the owner completes research doc §9 (no credentials exist in this session).
- `SPOTIFY_AUTOPLAY_SETTING_REQUIRED` still cannot be auto-detected (no public API for the Autoplay toggle state) -- unchanged, documented in the classifier and research doc §10.
- The `MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS = 8000` bound is a judgment call (long enough to cover a normal SDK next()/seek() round-trip, short enough not to falsely suppress a genuine fast Autoplay continuation that happens to follow soon after an unrelated manual action) -- not independently validated against real SDK timing behavior; flagged as `UNKNOWN_NEEDS_PROOF` pending owner testing.

### PM REVIEW ZIP

`P0-M6-R1-PM-REVIEW.zip` (repo root, local-only, never committed to git) -- rebuilt this pass:

- **SHA-256:** `034e9d1886477e7b51b13c9f3f373a608984d58d23e2bc4605047420aedf8ea4` (computed independently via both PowerShell `Get-FileHash` and Python `hashlib.sha256` -- both agree)
- **Size:** `65,045` bytes
- **Members:** `26`
- Contains: full `apps/automix-live-lab/{index.html,server/,src/,tools/}`, `docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md`, `HANDOFF_TO_PM.md` (the version at commit `aaf3943`, one commit before this SHA-recording commit), and a fresh `VALIDATION_ALL.txt` capturing all 6 suites' output: 103/103 PASS, 0 FAIL. No secrets/tokens/credentials present (independently grepped).

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -6` on `prototype/live-automix-lab` (both locally and on `origin/prototype/live-automix-lab` after the push) shows this repair's commit(s) directly on top of `85af4c9`, and `git diff --stat 85af4c9..HEAD` touches only the 4 files listed above.
2. Re-run `node apps/automix-live-lab/tools/verify_spotify_seed_identity.mjs` and confirm 24/24, plus the 5 regression suites for their exact counts (17/17, 10/10, 18/18, 12/12, 22/22).
3. Confirm the identity invariant directly: `node -e "import('./apps/automix-live-lab/src/adapters/spotify-autoplay.js').then(m => console.log(m.sanitizeTrackToken('X') === m.sanitizeTrackToken('spotify:track:X')))"` prints `true`.
4. Confirm `git grep -in "client_secret"` under `apps/automix-live-lab/` returns nothing.
5. Confirm `main` is untouched: `git rev-parse main` == `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`, and `research/p0-feasibility` is untouched at `5139411c8d94d7407e5d9c244b4e9275f30a8221`.
6. Confirm the push: `git ls-remote origin prototype/live-automix-lab` (or `gh api repos/PNHD/AutoMix/branches/prototype/live-automix-lab`) shows the same SHA as local `HEAD`.
7. Independently recompute the ZIP's SHA-256 and member count against the values recorded above.

---

`OWNER_SPOTIFY_AUTH_REQUIRED` (Spotify lane only, seed-identity repair complete) -- exact setup steps are in `docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md` §9. Local DSP Live lane remains unchanged and not blocked.
