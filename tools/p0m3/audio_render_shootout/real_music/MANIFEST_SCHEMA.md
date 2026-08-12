# Tier-B Real-Music Manifest Schema

PM OWNER LISTENING DIRECTION UPDATE, Task 3 "REAL-MUSIC PRIVATE VALIDATION
HARNESS". This describes the JSON manifest `scripts/real_music_pipeline.py`
consumes to render real transitions from **owner-supplied local audio
only**. The manifest itself, and every path/filename/fingerprint it
contains, is **LOCAL ONLY and NEVER committed** -- only this schema
document and `manifest.example.json` (placeholder paths, no real music
references) are committed.

## Why a manifest, not automatic full-track analysis

This P0 harness does not implement a general-purpose beat/structure
analyzer (that is `P0-M3-R1-ANALYZER-SHOOTOUT.md`'s scope, not this
pass's). The manifest instead lets the owner (or a human annotator)
supply the same small set of structural facts the accepted R2 planner
already consumes for the synthetic fixtures (`fixtures/scenario_fixtures.py`)
-- exit/entry candidate timestamps, bpm, and pair-compatibility
annotations -- so every real-music `PlannerDecision` is produced by
calling the REAL `policy.boundary.plan_transition_boundary()`, exactly
like every synthetic scenario in this pass, never a separately-invented
decision path.

This pass does not ship an automatic BPM/beat estimator -- the manifest's
`bpm` and candidate-timestamp fields must be supplied directly (from the
track's own metadata, a DAW/tap-tempo tool, or any external analyzer the
owner already trusts). A future pass could add a convenience estimator
without changing this manifest shape.

## Top-level shape

```json
{
  "pairs": [ { ... one pair object per required transition pair ... } ]
}
```

Provide **at least 3 pairs**, covering:

- `"category": "close_tempo_minimal_stretch"` -- real vocals, close tempo, little/no stretch expected.
- `"category": "conditional_tempo_correction"` -- real vocals, strong compatibility, ~3-6% tempo correction expected to be useful.
- `"category": "incompatible_downgrade"` -- real vocals, a pair where FULL_DJ should be rejected/downgraded (vocal/genre/tempo/structure incompatibility) -- author the `pair_compatibility` block honestly to reflect the REAL incompatibility (e.g. `vocal_collision_risk: "HIGH"`, or mismatched `genre_tags`), not a fabricated one.

## Pair object

```json
{
  "pair_id": "REAL-R1",
  "category": "close_tempo_minimal_stretch",
  "outgoing": {
    "path": "C:/absolute/local/path/to/outgoing_track.wav",
    "duration_ms": 220000,
    "bpm": 120.0,
    "genre_tags": ["pop"],
    "exit_candidate_t_ms": 210000,
    "beat_downbeat_aligned": true,
    "in_acceptable_exit_region": true,
    "musical_unit_complete": true,
    "is_outro_tail_opportunity": true,
    "vocal_collision_risk": "LOW",
    "structure_confidence": "HIGH",
    "energy_continuity_hint": "STRONG"
  },
  "incoming": {
    "path": "C:/absolute/local/path/to/incoming_track.wav",
    "bpm": 121.0,
    "genre_tags": ["pop"],
    "entry_candidate_t_ms": 0,
    "beat_downbeat_aligned": true,
    "phrase_section_evidence": false,
    "is_authored_silence_skip": false
  },
  "pair_compatibility": {
    "beat_confidence": "HIGH",
    "downbeat_confidence": "HIGH",
    "harmonic_relationship": "COMPATIBLE",
    "energy_continuity": "STRONG",
    "structure_compatibility": "COMPATIBLE",
    "vocal_collision_risk": "LOW",
    "bass_percussion_collision_risk": "LOW",
    "intro_outro_texture_compatible": true,
    "analysis_confidence": "HIGH"
  }
}
```

Field meanings are IDENTICAL to `tools/p0m3/transition_policy/fixtures/transition_fixtures.json`'s
TX-fixture shape (`outgoing_track.candidates[]`, `incoming_track.candidates[]`,
`pair_base`) -- `scripts/real_music_pipeline.py` maps this manifest 1:1
onto that shape before calling the real planner. See
`docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md` for exactly what
each field means and how the planner uses it.

### Choosing `exit_candidate_t_ms` / `entry_candidate_t_ms`

- Prefer a **near-end** outgoing region (Issue #7 / this pass's product
  target: preserve essentially the whole outgoing song). Do NOT choose an
  early/highlight-style cut.
- `entry_candidate_t_ms` is usually `0` (start of the incoming track)
  unless there is a genuine authored intro to skip or a real phrase/cue
  point that is clearly a better entry (see the R2 doc's "incoming entry"
  rules -- an unevidenced later-than-zero entry is rejected by the
  planner, by design).

## Running the harness

```bash
python scripts/real_music_pipeline.py --manifest real_music/manifest.local.json --work-dir real_music/work_local
```

- `--manifest`: required, no default. If omitted or the file does not
  exist, the script reports `OWNER_REAL_MUSIC_INPUT_REQUIRED` and exits
  without fabricating anything.
- `--work-dir`: required local-only output directory (converted audio,
  renders, blind clips) -- gitignored, never committed. Both `.gitignore`
  entries (`real_music/manifest.local.json`, `real_music/work_local/`)
  are already in place.
- Supported input formats: WAV, FLAC, MP3, M4A (anything `ffmpeg` can
  decode) -- converted once to canonical 44100Hz stereo float32 WAV in
  the work dir.

## Hard boundaries (enforced by the script, not just documented)

- Never reads from any Spotify/Apple Music protected-stream path or
  attempts DRM circumvention -- the script only ever calls `ffmpeg -i
  <local_file_path>`, nothing network-facing.
- Never logs, hashes, fingerprints, or prints the manifest's file paths
  or filenames into any COMMITTED file -- machine result JSON that is
  committed (see `scripts/real_music_pipeline.py`'s `--summary-out`)
  contains only `pair_id`/`category`/planner-decision numeric fields,
  never a path or filename.
- Never writes converted/rendered audio anywhere under a path this
  project's `.gitignore` doesn't already exclude.
