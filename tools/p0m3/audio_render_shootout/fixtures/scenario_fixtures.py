"""
P0-M3-R3 -- scenario fixtures (single source of truth for BOTH the R2
planner input and the synthetic audio generator).

Each scenario fixture is shaped exactly like
tools/p0m3/transition_policy/fixtures/transition_fixtures.json's TX-*
entries (outgoing_track/incoming_track/pair_base/boundary_overrides), so it
can be fed directly into the ACCEPTED R2 planner
(tools/p0m3/transition_policy/policy/boundary.plan_transition_boundary)
without reimplementing or guessing planner behavior (Issue #7: "Renderer
MUST consume the accepted R2 PlannerDecision").

Each fixture ALSO carries an `audio_plan` block (consumed only by
fixtures/synth.py + fixtures/generate_audio.py, never by the planner) that
describes how to synthesize deterministic, music-like audio consistent with
the SAME bpm/duration/timestamps the planner fixture declares -- so the
rendered audio and the planner's timing math can never drift apart.

Scenario coverage (Issue #7 "REQUIRED AUDIO SCENARIOS"):
  A -- no-stretch control (bpm_out == bpm_in, DIRECT, ratio 1.0)
  B -- moderate direct stretch (~5%, within the 3-6% band)
  C -- half/double relation with a small non-zero residual correction
  D -- complex/incompatible pair; planner must withhold FULL_DJ_BLEND/
       SHORT_EQ_BLEND and the renderer must use only the allowed fallback
       (SIMPLE_CROSSFADE). D deliberately reuses scenario A's exact
       outgoing/incoming audio plan (same bpm/duration/structure/seed) --
       only the PAIR compatibility differs (vocal-collision override) -- so
       the audio itself is not a confound between "A: compatible" and
       "D: incompatible", isolating the compatibility-gate behavior exactly
       as Issue #7 requires ("do NOT let different cue choices/audio
       contaminate the DSP comparison").
  E -- pitch-shift stress: see fixtures/pitch_shift_stress_conclusion.md --
       NOT rendered. R2's contract (policy/boundary.py,
       policy/compatibility.py, PM REVIEW #3 R7) only ever emits
       required_pitch_shift_semitones == 0 or None; there is no valid
       planner input that authorizes a nonzero semitone correction, so
       fabricating one would violate the "do NOT fabricate it" instruction.
"""

SR = 44100

# ---------------------------------------------------------------------------
# Scenario A -- NO-STRETCH CONTROL
# ---------------------------------------------------------------------------

SCENARIO_A = {
    "transition_id": "R3-A",
    "title": "no_stretch_control_direct_tempo_match",
    "purpose": "Isolate gain/EQ/alignment quality with zero time-stretch: bpm_out == bpm_in, DIRECT relation, required_tempo_ratio == 1.0.",
    "outgoing_track": {
        "duration_ms": 54000,
        "genre_tags": ["house"],
        "bpm": 120,
        "candidates": [
            {
                "candidate_id": "R3A-OUT-EXIT",
                "t_ms": 44000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "LOW",
                "structure_confidence": "HIGH",
                "energy_continuity_hint": "STRONG",
                "is_end_of_track": False,
            },
            {
                "candidate_id": "R3A-OUT-END",
                "t_ms": 54000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "NONE",
                "structure_confidence": "HIGH",
                "is_end_of_track": True,
            },
        ],
    },
    "incoming_track": {
        "genre_tags": ["house"],
        "bpm": 120,
        "candidates": [
            {
                "candidate_id": "R3A-IN-ANCHOR",
                "t_ms": 0,
                "phrase_section_evidence": False,
                "beat_downbeat_aligned": True,
                "is_authored_silence_skip": False,
            }
        ],
    },
    "pair_base": {
        "beat_confidence": "HIGH",
        "downbeat_confidence": "HIGH",
        "harmonic_relationship": "COMPATIBLE",
        "energy_continuity": "STRONG",
        "structure_compatibility": "COMPATIBLE",
        "vocal_collision_risk": "LOW",
        "bass_percussion_collision_risk": "LOW",
        "intro_outro_texture_compatible": True,
        "analysis_confidence": "HIGH",
    },
    "boundary_overrides": {},
    "audio_plan": {
        "outgoing": {
            "bpm": 120, "duration_s": 54.0, "seed": 1001, "root_hz": 220.0,
            "sections": [
                {"start_s": 0.0, "end_s": 8.0, "label": "intro", "energy": 0.30, "layers": ["pad", "hat"]},
                {"start_s": 8.0, "end_s": 24.0, "label": "verse", "energy": 0.65, "layers": ["pad", "hat", "bass", "kick", "snare"]},
                {"start_s": 24.0, "end_s": 40.0, "label": "chorus", "energy": 1.00, "layers": ["pad", "hat", "bass", "kick", "snare", "melody"]},
                {"start_s": 40.0, "end_s": 54.0, "label": "outro", "energy": 0.55, "layers": ["pad", "hat", "bass", "kick"]},
            ],
            "marker_ms": [44000],
        },
        "incoming": {
            "bpm": 120, "duration_s": 50.0, "seed": 2001, "root_hz": 246.94,
            "sections": [
                {"start_s": 0.0, "end_s": 6.0, "label": "intro", "energy": 0.35, "layers": ["pad", "hat", "kick"]},
                {"start_s": 6.0, "end_s": 26.0, "label": "verse", "energy": 0.70, "layers": ["pad", "hat", "bass", "kick", "snare"]},
                {"start_s": 26.0, "end_s": 50.0, "label": "chorus_tail", "energy": 1.00, "layers": ["pad", "hat", "bass", "kick", "snare", "melody"]},
            ],
            "marker_ms": [0],
        },
    },
}

# ---------------------------------------------------------------------------
# Scenario B -- MODERATE DIRECT STRETCH (~5%, within the 3-6% band)
# ---------------------------------------------------------------------------

SCENARIO_B = {
    "transition_id": "R3-B",
    "title": "moderate_direct_stretch_5_pct",
    "purpose": "Realistic modest tempo correction (126->120 == 5% deviation, inside MAX_JUSTIFIED_TEMPO_STRETCH_PCT=0.12): exposes transient smearing/phasiness/bass-vocal artifacts from a real DIRECT time-stretch.",
    # PM STAGE A REVIEW R2 repair: the exit candidate MUST land on a real
    # beat AND downbeat of the authored 126bpm grid. bar_dur_ms =
    # 4*(60000/126) = 1904.761904...; the 24th bar boundary is
    # 24*1904.761904... = 45714.285714...ms -- rounded to the nearest
    # integer ms (45714) for the fixture's t_ms field, 0.2857ms from the
    # true grid position (well within any reasonable analyzer tolerance).
    # The PRIOR value (45000ms) was exactly 94.5 beats from t=0 -- a half-
    # beat offset, not a beat or downbeat at all -- and had been accepted
    # as `beat_downbeat_aligned: true` without ever being checked against
    # the actual synthetic beat grid. See
    # scripts/verify_beat_grid_membership.py for the machine check that
    # would have caught this.
    "outgoing_track": {
        "duration_ms": 56000,
        "genre_tags": ["house"],
        "bpm": 126,
        "candidates": [
            {
                "candidate_id": "R3B-OUT-EXIT",
                "t_ms": 45714,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "LOW",
                "structure_confidence": "HIGH",
                "energy_continuity_hint": "STRONG",
                "is_end_of_track": False,
            },
            {
                "candidate_id": "R3B-OUT-END",
                "t_ms": 56000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "NONE",
                "structure_confidence": "HIGH",
                "is_end_of_track": True,
            },
        ],
    },
    "incoming_track": {
        "genre_tags": ["house"],
        "bpm": 120,
        "candidates": [
            {
                "candidate_id": "R3B-IN-ANCHOR",
                "t_ms": 0,
                "phrase_section_evidence": False,
                "beat_downbeat_aligned": True,
                "is_authored_silence_skip": False,
            }
        ],
    },
    "pair_base": {
        "beat_confidence": "HIGH",
        "downbeat_confidence": "HIGH",
        "harmonic_relationship": "COMPATIBLE",
        "energy_continuity": "STRONG",
        "structure_compatibility": "COMPATIBLE",
        "vocal_collision_risk": "LOW",
        "bass_percussion_collision_risk": "LOW",
        "intro_outro_texture_compatible": True,
        "analysis_confidence": "HIGH",
    },
    "boundary_overrides": {},
    "audio_plan": {
        "outgoing": {
            "bpm": 126, "duration_s": 56.0, "seed": 1002, "root_hz": 220.0,
            "sections": [
                {"start_s": 0.0, "end_s": 8.0, "label": "intro", "energy": 0.30, "layers": ["pad", "hat"]},
                {"start_s": 8.0, "end_s": 25.0, "label": "verse", "energy": 0.65, "layers": ["pad", "hat", "bass", "kick", "snare"]},
                {"start_s": 25.0, "end_s": 41.0, "label": "chorus", "energy": 1.00, "layers": ["pad", "hat", "bass", "kick", "snare", "melody"]},
                {"start_s": 41.0, "end_s": 56.0, "label": "outro", "energy": 0.55, "layers": ["pad", "hat", "bass", "kick"]},
            ],
            "marker_ms": [45714],
        },
        "incoming": {
            "bpm": 120, "duration_s": 50.0, "seed": 2002, "root_hz": 246.94,
            "sections": [
                {"start_s": 0.0, "end_s": 6.0, "label": "intro", "energy": 0.35, "layers": ["pad", "hat", "kick"]},
                {"start_s": 6.0, "end_s": 26.0, "label": "verse", "energy": 0.70, "layers": ["pad", "hat", "bass", "kick", "snare"]},
                {"start_s": 26.0, "end_s": 50.0, "label": "chorus_tail", "energy": 1.00, "layers": ["pad", "hat", "bass", "kick", "snare", "melody"]},
            ],
            "marker_ms": [0],
        },
    },
}

# ---------------------------------------------------------------------------
# Scenario C -- HALF/DOUBLE RELATION + SMALL RESIDUAL CORRECTION
# ---------------------------------------------------------------------------

SCENARIO_C = {
    "transition_id": "R3-C",
    "title": "half_double_relation_residual_correction",
    "purpose": "Legitimate half/double-time relation (120 vs 61.8 bpm) needing only a small residual playback-rate correction (required_tempo_ratio=0.9709, per P0-M3-R2-TRANSITION-POLICY-PLANNER.md sec.23 R6 worked example) -- verifies the R2 tempo contract is executable without rhythmic discontinuity.",
    "outgoing_track": {
        "duration_ms": 54000,
        "genre_tags": ["house"],
        "bpm": 120,
        "candidates": [
            {
                "candidate_id": "R3C-OUT-EXIT",
                "t_ms": 44000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "LOW",
                "structure_confidence": "HIGH",
                "energy_continuity_hint": "STRONG",
                "is_end_of_track": False,
            },
            {
                "candidate_id": "R3C-OUT-END",
                "t_ms": 54000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "NONE",
                "structure_confidence": "HIGH",
                "is_end_of_track": True,
            },
        ],
    },
    "incoming_track": {
        "genre_tags": ["house"],
        "bpm": 61.8,
        "candidates": [
            {
                "candidate_id": "R3C-IN-ANCHOR",
                "t_ms": 0,
                "phrase_section_evidence": False,
                "beat_downbeat_aligned": True,
                "is_authored_silence_skip": False,
            }
        ],
    },
    "pair_base": {
        "beat_confidence": "HIGH",
        "downbeat_confidence": "HIGH",
        "harmonic_relationship": "COMPATIBLE",
        "energy_continuity": "STRONG",
        "structure_compatibility": "COMPATIBLE",
        "vocal_collision_risk": "LOW",
        "bass_percussion_collision_risk": "LOW",
        "intro_outro_texture_compatible": True,
        "analysis_confidence": "HIGH",
    },
    "boundary_overrides": {},
    "audio_plan": {
        "outgoing": {
            "bpm": 120, "duration_s": 54.0, "seed": 1003, "root_hz": 220.0,
            "sections": [
                {"start_s": 0.0, "end_s": 8.0, "label": "intro", "energy": 0.30, "layers": ["pad", "hat"]},
                {"start_s": 8.0, "end_s": 24.0, "label": "verse", "energy": 0.65, "layers": ["pad", "hat", "bass", "kick", "snare"]},
                {"start_s": 24.0, "end_s": 40.0, "label": "chorus", "energy": 1.00, "layers": ["pad", "hat", "bass", "kick", "snare", "melody"]},
                {"start_s": 40.0, "end_s": 54.0, "label": "outro", "energy": 0.55, "layers": ["pad", "hat", "bass", "kick"]},
            ],
            "marker_ms": [44000],
        },
        # Half-time incoming track: same musical bar length as the outgoing
        # track's double-time grid (61.8bpm bars are twice as long as
        # 120bpm bars), so its authored structure is expressed in half as
        # many bars over a comparable wall-clock duration.
        "incoming": {
            "bpm": 61.8, "duration_s": 50.0, "seed": 2003, "root_hz": 246.94,
            "sections": [
                {"start_s": 0.0, "end_s": 7.8, "label": "intro", "energy": 0.35, "layers": ["pad", "hat", "kick"]},
                {"start_s": 7.8, "end_s": 27.0, "label": "verse", "energy": 0.70, "layers": ["pad", "hat", "bass", "kick", "snare"]},
                {"start_s": 27.0, "end_s": 50.0, "label": "chorus_tail", "energy": 1.00, "layers": ["pad", "hat", "bass", "kick", "snare", "melody"]},
            ],
            "marker_ms": [0],
        },
    },
}

# ---------------------------------------------------------------------------
# Scenario D -- COMPLEX MIX NOT ALLOWED (deliberately reuses A's audio)
# ---------------------------------------------------------------------------

SCENARIO_D = {
    "transition_id": "R3-D",
    "title": "incompatible_pair_forced_fallback_only",
    "purpose": "Otherwise-plausible boundary (same bpm/timing as scenario A) that fails a load-bearing pair-compatibility gate (HIGH vocal-collision risk at this specific boundary) -- FULL_DJ_BLEND and SHORT_EQ_BLEND must be withheld; renderer must use ONLY the allowed fallback (SIMPLE_CROSSFADE), never force complex DSP. Audio is deliberately the SAME as scenario A's (same bpm/duration/structure/seeds) so the DSP-fallback behavior is isolated from any audio/cue confound.",
    "outgoing_track": {
        "duration_ms": 54000,
        "genre_tags": ["house"],
        "bpm": 120,
        "candidates": [
            {
                "candidate_id": "R3D-OUT-EXIT",
                "t_ms": 44000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "LOW",
                "structure_confidence": "HIGH",
                "energy_continuity_hint": "STRONG",
                "is_end_of_track": False,
            },
            {
                "candidate_id": "R3D-OUT-END",
                "t_ms": 54000,
                "source": "authored_outro",
                "beat_downbeat_aligned": True,
                "in_acceptable_exit_region": True,
                "musical_unit_complete": True,
                "is_outro_tail_opportunity": True,
                "vocal_collision_risk": "NONE",
                "structure_confidence": "HIGH",
                "is_end_of_track": True,
            },
        ],
    },
    "incoming_track": {
        "genre_tags": ["house"],
        "bpm": 120,
        "candidates": [
            {
                "candidate_id": "R3D-IN-ANCHOR",
                "t_ms": 0,
                "phrase_section_evidence": False,
                "beat_downbeat_aligned": True,
                "is_authored_silence_skip": False,
            }
        ],
    },
    "pair_base": {
        "beat_confidence": "HIGH",
        "downbeat_confidence": "HIGH",
        "harmonic_relationship": "COMPATIBLE",
        "energy_continuity": "STRONG",
        "structure_compatibility": "COMPATIBLE",
        "vocal_collision_risk": "LOW",
        "bass_percussion_collision_risk": "LOW",
        "intro_outro_texture_compatible": True,
        "analysis_confidence": "HIGH",
    },
    # This is the load-bearing part of scenario D: at THIS specific
    # (exit, entry) boundary, vocal-collision risk is HIGH -- pair
    # compatibility must withhold FULL_DJ_BLEND/SHORT_EQ_BLEND regardless of
    # timing/structure/tempo all otherwise passing.
    "boundary_overrides": {
        "R3D-OUT-EXIT|R3D-IN-ANCHOR": {"vocal_collision_risk": "HIGH"},
    },
    # No independent audio_plan -- scenario D reuses scenario A's rendered
    # audio verbatim (see generate_audio.py / render_all.py); this key is
    # intentionally omitted so tooling fails loudly if it's ever read as if
    # D had its own audio.
    "reuses_audio_from": "R3-A",
}

ALL_SCENARIOS = [SCENARIO_A, SCENARIO_B, SCENARIO_C, SCENARIO_D]
SCENARIOS_BY_ID = {s["transition_id"]: s for s in ALL_SCENARIOS}
