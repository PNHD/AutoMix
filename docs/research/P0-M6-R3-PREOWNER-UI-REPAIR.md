# P0-M6-R3-PREOWNER — Compact Screenshot UX Repair

Status date: 2026-08-19

Binding task: `P0_M6_R3_PREOWNER_REPAIR_REQUIRED`, issued directly by the PM against the accepted `P0-M6-R3` implementation HEAD `22d2d4392c432262a31e37fa90cf445ef0f7d3c7`, ahead of the still-pending owner UI/listening review. Scope explicitly restricted to the compact-screenshot UX only -- recommendation/planner/queue-controller behavior and Local DSP were not touched.

## UI Defect 1 — Spotify credential setup leaked into the primary dashboard

`#spotify-setup` (Client ID input + Save + redirect URI hint) stayed visible in the primary Controls panel indefinitely once Spotify Live mode was active, including after a successful `connect()`. That defeats the compact-screenshot goal and risks exposing the Client ID in a screenshot.

Repaired in `app.js`'s `activateSpotify()` connect handler: once `connect()` actually succeeds (strictly after both early-return branches -- `SPOTIFY_REAUTH_REQUIRED_FOR_NEW_SCOPES` and `NOT_AUTHENTICATED*` -- have already returned), `els.spotifySetup.classList.add("hidden")` removes it from the primary view. Before authentication it is still shown by default (unchanged golden path -- the form is needed to get the owner authenticated in the first place). A new "Change Spotify setup" toggle button lives inside the collapsed Advanced panel (`#advanced-spotify-only`), wired to `els.spotifySetup.classList.toggle("hidden")` -- it only ever changes visibility, never calls `localStorage.removeItem` on the Client ID key, and reauth (`beginLogin()` on either early-return branch) is completely untouched.

## UI Defect 2 — search results stayed visible after a seed was chosen

`renderSeedResults()` left the full (up to 10-row) search-results list on screen indefinitely after `Play as seed` succeeded -- nothing ever cleared it.

Repaired with two new pure DOM helpers in `app.js`:
- `collapseSeedSearch()` -- clears `#seed-results`, hides the `#seed-search-controls` container (search input + button + results), and reveals a small `Change seed` button. Called only inside the "Play as seed" button's success path, immediately after `await adapter.playSeedTrack(track.uri)` resolves (never on failure, so a failed attempt leaves the search UI intact for retry).
- `restoreSeedSearch()` -- the inverse: reveals `#seed-search-controls`, hides `Change seed`. Wired to the `Change seed` button's `onclick` and to nothing else -- it contains no call to `searchTracks`/`playSeedTrack`, so opening it never runs a search or touches the currently-playing track. Also called once at the top of `activateSpotify()` so a freshly (re)activated Spotify session starts in the default search-visible state.

Now Playing (`#queue-current`, the progress slider, "Jump to last 15s") lives as a sibling of `#panel-seed`'s search subsection, not inside it -- collapsing the search UI never touches it.

## Screenshot target -- verified

Real-browser smoke check (Browser tool, `http://127.0.0.1:5500/`) at 1280x900 and 375x812: starting from the real pre-auth DOM state (setup + search visible, `Change seed` hidden -- confirmed live), then applying the exact class transitions the tested code paths perform (`#spotify-setup` hidden on connect success; `#seed-results` cleared / `#seed-search-controls` hidden / `Change seed` revealed on seed-play success) and confirming the resulting primary view's `document.body.innerText` contains none of: "Spotify Client ID", "Redirect URI to register", "Play as seed", "Debug log", "Lookahead state" -- at both widths, with `document.documentElement.scrollWidth === window.innerWidth` (zero horizontal overflow) and zero console errors. The `#spotify-setup` container's `getComputedStyle(...).display` was independently confirmed to be `"none"` even with a value already typed into the Client ID input, proving the field cannot render regardless of its stored value.

Toggle round-trips were also verified live: clicking `Change seed` restores the search controls without altering `#queue-current`'s text (the active song); clicking `Change Spotify setup` twice reveals then re-hides the form, and its label text flips between "Change Spotify setup" / "Hide Spotify setup" correctly.

## Test summary

28 verifier suites, 712/712 deterministic checks, 0 FAIL. `verify_compact_ui.mjs` grew from 60 to 88 checks (28 new: UI Defect 1 -- hide-on-success scoped correctly to the Spotify (not Local DSP) connect handler, recoverability via the Advanced control without clearing the stored Client ID, reauth still reachable, pre-auth golden path unchanged; UI Defect 2 -- `collapseSeedSearch()`/`restoreSeedSearch()` shape and wiring, success-only collapse, no auto-search/no-track-change guarantee, default-state reset on (re)activation; screenshot-target structural proof that the Client ID input and redirect URI hint live only inside the one container proven hidden on connect success). All other 27 suites rerun unchanged, still green.
