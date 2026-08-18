## HANDOFF TO PM — P0-M6-R1 PRE-AUTH RACE REPAIR (REPAIR PASS 3)

### RESULT

`OWNER_SPOTIFY_AUTH_REQUIRED` for the Spotify lane (bounded repair complete; the only remaining blocker is a real Spotify Developer Client ID). The Local DSP Live lane is **unchanged and not rerun this pass**, per instruction -- its prior evidence still stands. The DJ-partner audit is unchanged: `SPOTIFY_DJ_PARTNER_ACCESS_REQUIRED`.

### REPO / BRANCH / HEAD

- Repository: `PNHD/AutoMix`
- Branch: `prototype/live-automix-lab`
- Starting HEAD for this repair (verified live before starting): `4b2a420914feef083f2cf5979b51664fe7633a49`
- `main`: untouched at `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`
- `research/p0-feasibility`: untouched at `5139411c8d94d7407e5d9c244b4e9275f30a8221`
- Code-repair commit: `1be8baaecec32237648bfa3b1008f0e1b00b60e3` ("fix(app): P0-M6-R1 pre-auth race repair (repair pass 3) ...") directly on top of `4b2a420`. This is the commit containing the actual code repair.
- **Exact final HEAD after push:** this HANDOFF_TO_PM.md commit itself, immediately on top of the code-repair commit -- independently confirmable via `git log --oneline -3` on `prototype/live-automix-lab`, the same two-step pattern used in all three prior repair rounds.

### WHAT WAS REPAIRED (PM finding `P0_M6_R1_PREAUTH_RACE_REPAIR_REQUIRED`, Issue #11 comment `5324756494`)

**Reproduced defect:** immediately after `playSeedTrack()` resets `_autoplaySnapshots`/`_seedToken`, the Web Playback SDK can still emit one stale `player_state_changed` event for whatever was playing BEFORE the new seed, before it ever emits the seed's own state. The prior classifier accepted any non-seed current track with `manuallyTriggered=false` as continuation evidence, so that stale event alone could yield the false-positive verdict `SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED` **before the seed had ever been observed once** -- and the false verdict persisted even after the seed's real state later arrived. PM reproduced this directly against the shipped adapter from the prior PM-review ZIP.

**Repair:** one deterministic phase per seed selection. `playSeedTrack()` now also resets `_seedObserved = false`, entering `AWAITING_SEED_OBSERVATION`. In `_onPlayerStateChanged` (`apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js`), any event whose current track is NOT the seed while still in that phase is tagged `beforeSeedObserved: true` and is excluded from `_autoplaySnapshots` entirely -- it is still captured and emitted as a `pre_seed_diagnostic_snapshot` event (visible in the debug panel), never silently dropped, just excluded from Autoplay evidence. The event where the current track first equals the seed token flips `_seedObserved` to `true` (`SEED_ACTIVE`); from that point on, pre-exposure and continuation are evaluated exactly as before this repair. As defense-in-depth, `classifyAutoplayResult` (`apps/automix-live-lab/src/adapters/spotify-autoplay.js`) also mechanically filters out any `beforeSeedObserved: true` snapshot itself, so the invariant holds even if a future caller passed pre-epoch snapshots in by mistake.

### FILES CHANGED THIS REPAIR

```
Modified:
  apps/automix-live-lab/src/adapters/spotify-autoplay.js
  apps/automix-live-lab/src/adapters/SpotifyPublicControlAdapter.js
  docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md
  HANDOFF_TO_PM.md (this file)

New:
  apps/automix-live-lab/tools/verify_spotify_preauth_race.mjs
```

Not touched this pass: everything under `apps/automix-live-lab/src/engine/`, `LocalDSPPlaybackAdapter.js`, `queue_manifest.json`, `index.html`, `app.js`, `spotify-api-requests.js`, `spotify-pkce.js`, `PlaybackAdapter.js`, `SpotifyDJPartnerPlaybackAdapter.js`, and all prior `verify_*.mjs` test files (rerun only, never edited). No files under `tools/p0m5/` or existing `docs/research/P0-M5-R1*` content were touched.

### VALIDATION (commands run, exact results)

```
node apps/automix-live-lab/tools/verify_spotify_preauth_race.mjs
  -> 19/19 PASS (NEW, INTEGRATION-level -- drives the real
     SpotifyPublicControlAdapter through the exact PM-specified sequence:
     select seed -> stale OLD_TRACK (classification stays
     SPOTIFY_AUTOPLAY_NOT_OBSERVED, seed unconfirmed, zero entries in
     _autoplaySnapshots, event captured as pre_seed_diagnostic_snapshot
     instead) -> seed SEED123 becomes current (seed confirmed,
     _seedObserved flips true, still no continuation verdict) -> later
     genuinely different AUTO_NEXT (only now classifies as
     SPOTIFY_AUTOPLAY_CONTINUES_BUT_NEXT_NOT_PREEXPOSED) -- plus stale
     pre-seed next_tracks cannot produce SPOTIFY_AUTOPLAY_NEXT_TRACKS_VISIBLE
     while genuine post-observation pre-exposure still can, and regression
     cases for seed-fed-first sequences and manual-Next attribution)

Full regression rerun (all previously-passing suites, all unchanged):
node apps/automix-live-lab/tools/verify_spotify_seed_identity.mjs -> 24/24 PASS
node apps/automix-live-lab/tools/verify_spotify_search.mjs        -> 17/17 PASS
node apps/automix-live-lab/tools/verify_spotify_play_seed.mjs     -> 10/10 PASS
node apps/automix-live-lab/tools/verify_spotify_autoplay.mjs      -> 18/18 PASS
node apps/automix-live-lab/tools/verify_pkce.mjs                  -> 12/12 PASS
node apps/automix-live-lab/tools/verify_schedule.mjs              -> 22/22 PASS
  (Local DSP engine untouched; its 193s live session was NOT rerun,
   per this PM comment's explicit instruction)

Real-browser smoke check (Browser tool, http://127.0.0.1:5500/):
  app loads cleanly, zero console errors, after the repair. Local DSP
  Live's Connect button was deliberately NOT clicked this pass.
```

Combined this pass: 19 new automated PASS checks + 103 regression-rerun PASS checks = **122/122, 0 FAIL**.

### AC CHECK (against PM comment `5324756494`)

| Requirement | Status | Evidence |
|---|---|---|
| One deterministic seed-epoch / seed-observed phase | PASS | `_seedObserved` flag, `AWAITING_SEED_OBSERVATION` -> `SEED_ACTIVE` |
| SDK states before `currentToken === seedToken` excluded from Autoplay evidence | PASS | never pushed to `_autoplaySnapshots`; also filtered defensively in `classifyAutoplayResult` |
| Retained diagnostic-only (not silently dropped) | PASS | emitted as `pre_seed_diagnostic_snapshot` |
| 1. select `spotify:track:SEED123` | PASS | `verify_spotify_preauth_race.mjs` check 1 |
| 2-3. stale `OLD_TRACK` -> classification remains `SPOTIFY_AUTOPLAY_NOT_OBSERVED` | PASS | checks 3-6 |
| 4. seed still unconfirmed | PASS | check 4 |
| 5-6. feed `SEED123` -> seed becomes confirmed | PASS | checks 7-8 |
| 7. still no continuation verdict | PASS | check 9 |
| 8-9. feed `AUTO_NEXT` -> only now `CONTINUES_BUT_NEXT_NOT_PREEXPOSED` | PASS | checks 11-12 |
| 10. stale pre-seed `next_tracks` does NOT produce `NEXT_TRACKS_VISIBLE` | PASS | checks 13-16 |
| Preserve identity/manual-attribution/search/one-URI-seed/no-playlist/no-Recommendations/four-scopes/SDK-readiness/privacy | PASS, all unmodified | none of those files touched this pass; regression suites all green |
| Local DSP unchanged, 193s not rerun | PASS | engine files untouched; only `verify_schedule.mjs` rerun as a cheap regression check |
| Run all existing + new tests | PASS | 122/122 |
| Commit/push; verify origin HEAD exact | PASS | see PM_REVIEW_REQUEST |
| `main`/`research/p0-feasibility` untouched | PASS | verified via `git rev-parse` |
| Do not broaden scope | PASS | zero scope/UI/product changes this pass |

### UNKNOWNS / RISKS

- Unchanged from prior handoffs: real Spotify search/seed-playback/Autoplay-classification outcomes remain `UNKNOWN_NEEDS_PROOF` until the owner completes research doc §9.
- The stale-event race was reproduced and fixed using synthetic SDK state sequences (matching PM's own reproduction pattern); the exact number/timing of stale events a REAL Web Playback SDK session emits before the seed appears is still `UNKNOWN_NEEDS_PROOF` -- this repair's phase boundary handles any number of stale events (not just one) before the seed is first observed, so it should be robust regardless, but that robustness itself is only proven against synthetic sequences.
- All risks carried over from the prior two handoffs (MANUAL_ACTION_ATTRIBUTION_TIMEOUT_MS judgment call, Autoplay-setting non-detectability, INFERENCE-level competitor differentiation) are unchanged and still disclosed in the research doc.

### PM REVIEW ZIP

`P0-M6-R1-PM-REVIEW.zip` (repo root, local-only, never committed to git) -- rebuilt this pass:

- **SHA-256:** `35c446a6e8549fb5bfd8905ec917b7ba2f645bc71bc2cec294ab4af610fcd40f` (computed independently via both PowerShell `Get-FileHash`-equivalent Python `hashlib.sha256` and re-verified against the Python `zipfile` member listing)
- **Size:** `70,427` bytes
- **Members:** `27`
- Contains: full `apps/automix-live-lab/{index.html,server/,src/,tools/}`, `docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md`, `HANDOFF_TO_PM.md` (the version at commit `1be8baa`, one commit before this SHA-recording commit), and a fresh `VALIDATION_ALL.txt` capturing all 7 suites' output: 122/122 PASS, 0 FAIL. No secrets/tokens/credentials present (independently grepped).

### PM REVIEW REQUEST

Please independently verify:

1. `git log --oneline -8` on `prototype/live-automix-lab` (both locally and on `origin/prototype/live-automix-lab` after the push) shows this repair's commit(s) directly on top of `4b2a420`, and `git diff --stat 4b2a420..HEAD` touches only the files listed above.
2. Re-run `node apps/automix-live-lab/tools/verify_spotify_preauth_race.mjs` and confirm 19/19, plus the 6 regression suites for their exact counts.
3. Reproduce the exact defect sequence PM used and confirm it's fixed: instantiate `SpotifyPublicControlAdapter`, select a seed, feed a stale non-seed `player_state_changed` state, confirm `getAutoplayClassification().result === "SPOTIFY_AUTOPLAY_NOT_OBSERVED"` (not `CONTINUES_BUT_NEXT_NOT_PREEXPOSED`), then feed the seed's own state and confirm it becomes confirmed with the verdict still unchanged.
4. Confirm `git grep -in "client_secret"` under `apps/automix-live-lab/` returns nothing.
5. Confirm `main` is untouched: `git rev-parse main` == `2450d55c60601bcee5eb52a2c38ce5d6e87a76aa`, and `research/p0-feasibility` is untouched at `5139411c8d94d7407e5d9c244b4e9275f30a8221`.
6. Confirm the push: `gh api repos/PNHD/AutoMix/branches/prototype/live-automix-lab --jq '.commit.sha'` shows the same SHA as local `HEAD`.
7. Independently recompute the ZIP's SHA-256 and member count against the values recorded above.

---

`OWNER_SPOTIFY_AUTH_REQUIRED` (Spotify lane only, pre-auth race repair complete) -- exact setup steps are in `docs/research/P0-M6-R1-SPOTIFY-FIRST-LIVE-PROTOTYPE.md` §9. Local DSP Live lane remains unchanged and not blocked.
