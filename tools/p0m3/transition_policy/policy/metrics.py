"""
P0-M3-R2 (Apple-like redesign) -- song-preservation / transition-timing
metrics.

Core repair over the superseded fraction_consumed-only model: transition
ONSET (when incoming audio first becomes materially audible) and outgoing
CONTENT PRESERVATION (when the outgoing track's meaningful content actually
stops being audible) are separate, independently computed quantities. A
transition may begin tens of seconds before the outgoing track's natural end
while the outgoing track remains audible, via overlap, through nearly all of
its meaningful content -- that is a correct Apple-like outcome, not a
truncation.

None of the numeric constants in this module are claims about Apple's
private implementation. They are PROJECT_INFERENCE / BENCHMARK_PROPOSAL
values -- see docs/research/P0-M3-R2-TRANSITION-POLICY-PLANNER.md
"Apple-like behavioral target -- public evidence vs project inference".
"""

from dataclasses import dataclass

# P0 placeholder: the largest overlap this planner will propose between two
# tracks, in milliseconds. This is NOT an Apple-documented number. It exists
# so a candidate whose remaining content is short (a genuine near-end
# candidate) can have that entire remainder covered by the overlap -- while
# a candidate whose remaining content is long (e.g. minutes) cannot have its
# preservation ratio rescued by an unrealistically long overlap. Sensitivity
# to this constant is a P0-M3-R3 DSP-execution question, not this planner's;
# this module only needs it to be duration-normalized (bounded by the
# candidate's own remaining content) and finite.
NEAR_END_MAX_OVERLAP_MS = 40_000

# Recommended default preservation floor for SEAMLESS_FULL_TRACK_DEFAULT
# (project benchmark proposal, sensitivity-tested at 0.90/0.93/0.95/0.97/0.98
# in results/sensitivity_matrix.json). Preferred band is 0.97-1.00; the
# acceptable P0 default-candidate band is 0.95-1.00.
DEFAULT_PRESERVATION_FLOOR = 0.95
CATASTROPHIC_PRESERVATION_CEILING = 0.90  # strictly below this => catastrophic
# R8 (PM REVIEW #3): the boundary between the ACCEPTABLE and PREFERRED
# preservation safety bands used by policy/ranking.py. Same 0.97 value the
# docs already describe as "preferred band 0.97-1.00" -- not a new policy.
PREFERRED_PRESERVATION_THRESHOLD = 0.97


def preservation_band(ratio: float, floor: float) -> str:
    """
    PREFERRED (>=0.97) / ACCEPTABLE (>=floor and <0.97) / UNSAFE (<floor).
    UNSAFE candidates are already excluded before ranking by the hard
    preservation-floor eligibility guard -- this function exists so the
    boundary is computed once, consistently, wherever it's needed (it is
    not itself a new gate).
    """
    if ratio < floor:
        return "UNSAFE"
    if ratio >= PREFERRED_PRESERVATION_THRESHOLD:
        return "PREFERRED"
    return "ACCEPTABLE"


@dataclass
class PreservationMetrics:
    effective_content_end_ms: int
    transition_onset_ms: int
    transition_onset_ratio: float
    remaining_content_at_onset_ms: int
    overlap_duration_ms: int
    outgoing_last_audible_ms: int
    outgoing_content_preservation_ratio: float
    outgoing_content_lost_ms: int
    is_catastrophic_loss: bool


def effective_content_end_ms(fixture: dict) -> int:
    """
    The meaningful musical ending, excluding authored trailing dead-air
    where the fixture explicitly annotates it as non-musical silence
    (`trailing_dead_air_ms`). A fixture with no such annotation uses
    `duration_ms` unchanged -- an unannotated tail is NEVER silently
    treated as removable dead air (spec: "do NOT silently remove a musical
    outro as silence").
    """
    duration_ms = fixture["duration_ms"]
    dead_air_ms = fixture.get("trailing_dead_air_ms", 0)
    if not fixture.get("trailing_dead_air_is_authored_non_musical", False):
        return duration_ms
    return max(0, duration_ms - dead_air_ms)


def compute_preservation(fixture: dict, transition_onset_ms: int, proposed_overlap_ms: int = NEAR_END_MAX_OVERLAP_MS) -> PreservationMetrics:
    """
    Compute the full preservation/timing metric set for a candidate
    transition_onset_ms against this fixture's effective content end.

    overlap is bounded by the actual remaining musical content -- a
    candidate cannot "borrow" preservation from content that does not
    exist, and cannot exceed the plausible overlap ceiling either.
    """
    content_end = effective_content_end_ms(fixture)
    onset = min(transition_onset_ms, content_end)
    remaining = max(0, content_end - onset)
    overlap = max(0, min(proposed_overlap_ms, remaining))
    outgoing_last_audible = onset + overlap
    lost_ms = max(0, content_end - outgoing_last_audible)
    preservation_ratio = round(outgoing_last_audible / content_end, 4) if content_end else 1.0
    onset_ratio = round(onset / content_end, 4) if content_end else 0.0

    return PreservationMetrics(
        effective_content_end_ms=content_end,
        transition_onset_ms=onset,
        transition_onset_ratio=onset_ratio,
        remaining_content_at_onset_ms=remaining,
        overlap_duration_ms=overlap,
        outgoing_last_audible_ms=outgoing_last_audible,
        outgoing_content_preservation_ratio=preservation_ratio,
        outgoing_content_lost_ms=lost_ms,
        is_catastrophic_loss=preservation_ratio < CATASTROPHIC_PRESERVATION_CEILING,
    )
