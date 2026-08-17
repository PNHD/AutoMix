"""
P0-M4-R2 PF4 -- owner-response -> `transition_class_policy` materialization.

PM REVIEW REPAIR (Issue #9 comment `5318289406`), item 2/3: maps a
COMPLETED NG4 owner response row (the corrected per-class
`class_acceptability` schema -- see `build_ng4_annotation_pack.py`) onto
the full P0-M2 `transition_class_policy` object shape
(`docs/research/P0-M2-CORPUS-MANIFEST-SCHEMA.md` SS6):

  - every class the owner marked `true` -> `accepted_unconditional`
    (a source-only human judgment; execution quality is still scored
    separately by the objective/human metrics later, per SS6's own
    "execution quality is still scored separately" note);
  - a class the owner marked `false`, or left `null`/omitted, is NOT
    added to any explicit list -- it falls through to SS6.1 rule 2's
    closed-world default (rejected with the generic, non-`C11`-eligible
    reason). This task does not invent conditional machine evidence from
    a source-only annotation stage, per the PM repair's explicit
    instruction;
  - the three narrow-scope forbidden rendered classes are added to
    `rejected` MECHANICALLY, independent of any owner input -- these are
    deterministic contract restrictions (`docs/research/P0-M4-R1-
    PRESERVATION-FIRST-RESCOPE-CONTRACT.md` SS7's forbidden list /
    benchmark contract SS16.7), never an owner annotation question, and
    the owner annotation UI never offers them as choices.

This module is exercised in this pass ONLY against synthetic response
rows (`verify_pf4_pack.py`) -- no real owner response exists yet. It is
not invoked against real data until a future session, after the owner
completes `response_template.json`.
"""
from __future__ import annotations

NARROW_CLASSES = ["NO_SPECIAL_TRANSITION", "GAPLESS", "SIMPLE_CROSSFADE"]

# Deterministic, contract-mandated -- never an owner annotation question.
# Reasons cite the binding contract restriction (a corpus-design-time-known
# fact about the AUTHORIZED SCOPE, not a per-pair judgment), matching SS6.1
# rule 4's "never name a specific implementation technology" requirement --
# these reasons name the SCOPE restriction, not a technology.
FORBIDDEN_NARROW_CLASSES = {
    "FULL_DJ_BLEND": "not authorized in the narrow PRESERVATION_FIRST_LOCAL_AUTOMIX scope "
                      "(docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md SS7 forbidden list)",
    "SHORT_EQ_BLEND": "research-only/off-by-default in the narrow scope, not a production output "
                       "(docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md SS7)",
    "CUT": "automatic non-natural CUT is not authorized as default behavior in the narrow scope "
           "(docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md SS7)",
}


class InvalidResponseRow(Exception):
    pass


def materialize_transition_class_policy(class_acceptability: dict) -> dict:
    """`class_acceptability`: {"NO_SPECIAL_TRANSITION": bool, "GAPLESS": bool,
    "SIMPLE_CROSSFADE": bool} -- a COMPLETED owner response row (no `None`
    values; see `validate_completed_row` below for the completeness gate).
    Returns a `transition_class_policy`-shaped dict (SS6)."""
    missing = [c for c in NARROW_CLASSES if c not in class_acceptability]
    if missing:
        raise InvalidResponseRow(f"class_acceptability missing narrow classes: {missing}")
    non_bool = [c for c in NARROW_CLASSES if not isinstance(class_acceptability[c], bool)]
    if non_bool:
        raise InvalidResponseRow(f"class_acceptability values must be true/false (row is incomplete): {non_bool}")

    accepted_unconditional = [c for c in NARROW_CLASSES if class_acceptability[c] is True]

    rejected = [{"class": cls, "reason": reason} for cls, reason in FORBIDDEN_NARROW_CLASSES.items()]

    policy = {
        "accepted_unconditional": accepted_unconditional,
        "accepted_conditional": [],
        "rejected_conditional": [],
        "rejected": rejected,
    }

    # SS6.1 rule 1 (mutual exclusivity), verified defensively even though
    # it is structurally guaranteed here (narrow vs. forbidden classes are
    # disjoint sets by construction).
    all_classes_seen = set(accepted_unconditional) | {r["class"] for r in rejected}
    for cls in all_classes_seen:
        in_lists = sum([
            cls in policy["accepted_unconditional"],
            any(e["class"] == cls for e in policy["accepted_conditional"]),
            any(e["class"] == cls for e in policy["rejected_conditional"]),
            any(e["class"] == cls for e in policy["rejected"]),
        ])
        if in_lists != 1:
            raise InvalidResponseRow(f"mutual-exclusivity violation for class {cls}: appears in {in_lists} lists")

    return policy


def validate_completed_row(row: dict) -> list:
    """Returns a list of human-readable problems (empty = fully completed
    and ready to materialize). Does not raise -- callers decide how to
    treat an incomplete row (e.g. still-pending owner response)."""
    problems = []
    ca = row.get("class_acceptability")
    if not isinstance(ca, dict):
        return ["class_acceptability missing or not an object"]
    for c in NARROW_CLASSES:
        if c not in ca:
            problems.append(f"missing narrow class {c}")
        elif ca[c] is None:
            problems.append(f"{c} is still null (owner has not answered)")
        elif not isinstance(ca[c], bool):
            problems.append(f"{c} is not true/false: {ca[c]!r}")
    return problems
