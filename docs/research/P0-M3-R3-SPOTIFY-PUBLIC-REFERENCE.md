# P0-M3-R3 -- Spotify Public Reference Note (Behavioral Inspiration Only)

Status date: 2026-08-12

## Label

**`PUBLIC_APPLE_EVIDENCE`-equivalent for Spotify** -- this document quotes
ONLY Spotify's own public support/newsroom pages, retrieved this session.
It makes **no claim about Spotify's proprietary internal implementation**,
does not reverse engineer any Spotify client/service, and was not produced
by inspecting Spotify's app binary, network traffic, or any non-public
source. Per PM OWNER LISTENING DIRECTION UPDATE's "SPOTIFY PUBLIC
REFERENCE BOUNDARY" -- used strictly as **behavioral inspiration**, the
same evidence-tier discipline this project already applies to Apple
Music AutoMix in `docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` §2.

## 1. Automix (existing, playback-level)

Source: Spotify Support, "Transitions between tracks"
(`support.spotify.com/us/article/tracks-transitions/`), retrieved
2026-08-12.

> "Allows beat-matched seamless transitions between songs on select
> Spotify playlists. Works even on Shuffle."

This is a **playback setting** (Playback settings, mobile and desktop),
not a playlist-editing feature -- it applies automatically to eligible
playlists during normal listening, with no user-authored transition
points. No exact algorithm, timing threshold, or percentage is publicly
disclosed; none is claimed here.

## 2. Mix -- user-created/editable mixed-playlist transitions

Source: Spotify Newsroom, "Mix Your Favorite Playlists Seamlessly by
Adding Your Own Transitions" (`newsroom.spotify.com/2025-08-19/...`),
retrieved 2026-08-12.

> "Open a playlist you've already created, or make a new one. Select
> 'Mix' from the toolbar and see your playlist change."

> "Start with 'Auto' for an instant blend, or tap to customize your mix
> and create unique transitions that fit your style."

> "Experiment with specific settings for volume, EQ, and effects, and use
> the waveform and beat data to find the best spot in each track for your
> transition."

The same article describes preset transition styles ("Fade", "Rise") and
a "Match tempos and keys" control that surfaces each track's own BPM/key
data to the user. Rolling out to eligible Premium users (Premium
requirement stated explicitly in the source).

**Distinction from this project's product target**: this is an explicit
playlist-EDITING workflow (the user opens an editor, chooses "Mix" mode,
and authors/adjusts transitions per-playlist) -- not an always-on,
zero-setup consumer listening default. Per the PM comment: *"Spotify's
newer mixed-playlist flow was also subjectively acceptable in prior owner
testing, though its playlist-creation workflow is not the desired product
UX."* This project's target remains the Apple-Music-AutoMix-style
always-on background behavior (`docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md`
§3), not a playlist-authoring tool.

## 3. Smart Reorder -- BPM/key-based playlist reordering

Source: Spotify Newsroom, "Level Up Your Playlists' Transitions With
Smart Reorder" (`newsroom.spotify.com/2026-02-25/smart-reorder-playlist-mixing/`),
retrieved 2026-08-12.

> "Tracks are now reordered with BPM and key so that your transitions
> sound better."

Accessed via Mix -> Edit -> Smart Reorder (Premium, regions where Spotify
Mix has launched per the secondary coverage below). Does not touch
tracks the user has already manually customized transitions for.

## 4. What this project takes from this evidence (INFERENCE, not a Spotify claim)

- Public confirmation that at least one major consumer streaming product
  ships both (a) an always-on beat-matched transition mode (Automix) and
  (b) a separate, editable, BPM/key-aware playlist-mixing tool (Mix +
  Smart Reorder) -- i.e. the "always-on background behavior" vs.
  "user-authored mixing tool" distinction this project already draws
  between its own Apple-Music-AutoMix-like target and a DJ/highlight tool
  is a real, publicly-shipped product distinction elsewhere in the
  market, not an invented one.
- BPM/key as the two signals Spotify's own public description leads with
  for playlist-reordering quality is directionally consistent with this
  project's own reliance on bpm/genre/harmonic-compatibility fields in
  `tools/p0m3/transition_policy/policy/compatibility.py` -- offered only
  as loose behavioral corroboration, not as evidence this project's
  specific thresholds (`MAX_JUSTIFIED_TEMPO_STRETCH_PCT`, the PM OWNER
  LISTENING DIRECTION UPDATE's 0-2%/2-6%/>6% buckets, etc.) match
  Spotify's undisclosed internals -- they do not claim to, and no
  evidence here would support that claim either way.

## 5. Explicit non-claims

- No reverse engineering, decompilation, network traffic inspection, or
  DRM circumvention of any Spotify client/service was performed or is
  claimed.
- No proprietary Spotify algorithm, internal threshold, or internal
  architecture is described -- everything above is a direct quote from
  Spotify's own public support/newsroom pages.
- This document does not assert this project's design choices are
  "the same as Spotify's" -- only that they are directionally consistent
  with publicly-observable product behavior, offered as inspiration per
  the PM's explicit instruction.

## 6. Retrieval commands (reproducible)

Retrieved via web fetch this session, 2026-08-12:
- `https://support.spotify.com/us/article/tracks-transitions/`
- `https://newsroom.spotify.com/2025-08-19/mix-your-favorite-playlists-seamlessly-by-adding-your-own-transitions/`
- `https://newsroom.spotify.com/2026-02-25/smart-reorder-playlist-mixing/`
