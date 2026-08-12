"""
P0-M3-R2 (Apple-like redesign) -- deterministic, order-invariant ranking
among ALL eligible near-end candidates.

Repairs the superseded "first eligible candidate wins" behavior (PM
comment R2 / spec section E): the canonical full-track planner must
consider every eligible candidate and select the best one by a documented,
reproducible rule -- never merely the first one encountered in whatever
order the candidate array happens to be in.

Ranking key (descending priority, all evidence already exposed elsewhere
in the trace -- this is a lexicographic tuple, not an opaque score).

R8 (PM REVIEW #3) repair: preservation now ranks by SAFETY BAND first
(PREFERRED/ACCEPTABLE/UNSAFE -- policy/metrics.preservation_band), not the
raw rounded ratio. UNSAFE candidates are already excluded before ranking
by the hard eligibility floor guard, so this is not a weakening of the
preservation safety gate -- it only changes how candidates that are ALREADY
safe get ordered against each other. Within the same band, pair
compatibility now outranks a marginal (<1-band-width) preservation
difference, which is the actual point of ranking a COMPLETE boundary
rather than the single best outgoing-only preservation number:

  1. preservation_band (PREFERRED > ACCEPTABLE > UNSAFE) -- the hard safety
     signal, still first, still dominant across bands.
  2. eligible_for_dynamic_mix (pair compatibility AT this specific
     boundary, when known -- PM REVIEW #2 R1 repair: this now participates
     in ranking itself, not merely applied to the already-selected winner
     afterward. A candidate with unproven/absent pair data ranks in the
     same lower tier as a known-incompatible one, consistent with
     FULL_DJ_BLEND being withheld by default.)
  3. musical_structure_score (outro/phrase/section completion evidence)
  4. energy_continuity_priority (only meaningful once timing/compatibility
     safety gates already passed -- spec "Energy / Excitement Target")
  5. confidence rank (HIGH > MEDIUM > LOW > NONE)
  6. exact outgoing_content_preservation_ratio -- a fine-grained tie-break
     WITHIN an already-equal band/compatibility/structure/energy/confidence
     tuple, never the primary signal.
  7. candidate_id (lexicographic) -- final deterministic tie-break; this
     key never depends on t_ms/array position, which is exactly what makes
     the result order-invariant.
"""

CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
ENERGY_PRIORITY = {"STRONG": 2, "WEAK": 1, "UNKNOWN": 0}
PRESERVATION_BAND_RANK = {"PREFERRED": 2, "ACCEPTABLE": 1, "UNSAFE": 0}


def _sort_key(entry: dict):
    return (
        PRESERVATION_BAND_RANK.get(entry.get("preservation_band", "UNSAFE"), 0),
        1 if entry.get("eligible_for_dynamic_mix") else 0,
        entry.get("musical_structure_score", 0.0),
        ENERGY_PRIORITY.get(entry.get("energy_continuity_priority", "UNKNOWN"), 0),
        CONFIDENCE_RANK.get(entry.get("confidence", "NONE"), 0),
        round(entry.get("outgoing_content_preservation_ratio", 0.0), 4),
    )


def rank_eligible_candidates(eligible_entries: list) -> list:
    """
    Returns a NEW list, ranked best-first, with an added `eligible_rank`
    field (1 = best). Sorting is stable and keyed only on evidence values
    plus a final candidate_id tie-break -- never on input array order or
    t_ms -- so shuffling/reversing the input never changes the winner.
    """
    ordered = sorted(
        eligible_entries,
        key=lambda e: (_sort_key(e), tuple(-ord(c) for c in e["candidate_id"])),
        reverse=True,
    )
    ranked = []
    for idx, entry in enumerate(ordered, start=1):
        new_entry = dict(entry)
        new_entry["eligible_rank"] = idx
        ranked.append(new_entry)
    return ranked


def rank_boundary_plans(eligible_boundaries: list) -> list:
    """
    Same ranking key as rank_eligible_candidates, but for COMPLETE boundary
    plans (outgoing exit x incoming entry x pair compatibility at that
    boundary -- PM REVIEW #2 R1). Tie-break key is the combined
    "outgoing_candidate_id|incoming_candidate_id" string, so the result is
    invariant to both outgoing-array and incoming-array ordering. Mutates
    and returns the SAME dict objects (not copies) so callers that also
    hold these objects in a full trace list see boundary_rank/selected
    reflected there too.
    """
    def boundary_id(e):
        return f"{e['outgoing_candidate_id']}|{e['incoming_candidate_id']}"

    ordered = sorted(
        eligible_boundaries,
        key=lambda e: (_sort_key(e), tuple(-ord(c) for c in boundary_id(e))),
        reverse=True,
    )
    for idx, entry in enumerate(ordered, start=1):
        entry["boundary_rank"] = idx
    return ordered
