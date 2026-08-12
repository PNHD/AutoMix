"""
P0-M3-R2 (Apple-like redesign) -- deterministic, order-invariant ranking
among ALL eligible near-end candidates.

Repairs the superseded "first eligible candidate wins" behavior (PM
comment R2 / spec section E): the canonical full-track planner must
consider every eligible candidate and select the best one by a documented,
reproducible rule -- never merely the first one encountered in whatever
order the candidate array happens to be in.

Ranking key (descending priority, all evidence already exposed elsewhere
in the trace -- this is a lexicographic tuple, not an opaque score):

  1. outgoing_content_preservation_ratio, rounded to 2 decimals
     (near-end song preservation is the load-bearing default signal)
  2. musical_structure_score (outro/phrase/section completion evidence)
  3. energy_continuity_priority (only meaningful once timing/compatibility
     safety gates already passed -- spec "Energy / Excitement Target")
  4. confidence rank (HIGH > MEDIUM > LOW > NONE)
  5. candidate_id (lexicographic) -- final deterministic tie-break; this
     key never depends on t_ms/array position, which is exactly what makes
     the result order-invariant.
"""

CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
ENERGY_PRIORITY = {"STRONG": 2, "WEAK": 1, "UNKNOWN": 0}


def _sort_key(entry: dict):
    return (
        round(entry["outgoing_content_preservation_ratio"], 2),
        entry.get("musical_structure_score", 0.0),
        ENERGY_PRIORITY.get(entry.get("energy_continuity_priority", "UNKNOWN"), 0),
        CONFIDENCE_RANK.get(entry.get("confidence", "NONE"), 0),
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
