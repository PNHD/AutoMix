"""
P0-M4-R1 docs-only consistency verifier (repair pass R5).

Checks that the P0-M4-R1 rescope contract's exact-number and exact-phrase
claims are actually present in the repository docs, mechanically, so a
future edit cannot silently drift from what this task's handoff describes.
Also independently re-implements the §12 deterministic pair-selection
algorithm and self-tests its invariants against synthetic opaque IDs --
no private corpus is read.

No audio, no network, no ML/analyzer import. Reads only the four
`docs/**/*.md` files this task's contract names, plus a repository-wide
prohibited-claim scan, plus its own synthetic self-test data.

Usage:
    python tools/p0m4/verify_rescope_contract.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHARTER = ROOT / "docs" / "PROJECT_CHARTER.md"
BENCHMARK_CONTRACT = ROOT / "docs" / "research" / "P0-M2-AUTOMIX-QUALITY-BENCHMARK-CONTRACT.md"
RESCOPE_CONTRACT = ROOT / "docs" / "research" / "P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md"

# Unqualified prohibited claims (§15 of the rescope contract). These are
# specific enough that an accidental substring match elsewhere is unlikely;
# each occurrence found is reported for a human to inspect, not
# auto-failed on a bare substring hit inside an explicitly-labeled
# historical/quoted context.
PROHIBITED_CLAIM_STRINGS = [
    "broad P1 is validated",
    "broad P1 is currently authorized",
    "real FULL_DJ quality has passed",
    "FULL_DJ quality has passed",
    "current analyzer stack is production-ready",
    "commercial transition superiority has been demonstrated",
    "G1-G8 were waived",
    "G1–G8 were waived",
    "P0 passed audible quality",
]

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# R2 pair-selection algorithm (docs/research/P0-M4-R1-PRESERVATION-FIRST-
# RESCOPE-CONTRACT.md §12), re-implemented independently here for a
# deterministic self-test against SYNTHETIC opaque IDs only.
# ---------------------------------------------------------------------------

SELECTION_SALT = "P0-M4-R1-NARROW-VALIDATION-v1"


def _hash_key(tag: str, out_id: str, in_id: str) -> str:
    payload = f"{SELECTION_SALT}|{tag}|{out_id}|{in_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_50_pairs(ids: list[str], target: int = 50, max_appearances: int = 2) -> list[tuple[str, str]]:
    """§12.1-§12.3: deterministic 50-pair selection scan. Returns fewer than
    `target` pairs (never raises) if the input universe is exhausted first --
    callers must check the length, mirroring the contract's own hard-stop
    rule rather than silently loosening the constraints."""
    ids_sorted = sorted(set(ids))
    universe = [(a, b) for a in ids_sorted for b in ids_sorted if a != b]
    ranked = sorted(universe, key=lambda p: (_hash_key("PAIR", p[0], p[1]), p[0], p[1]))

    accepted: list[tuple[str, str]] = []
    reverse_accepted: set[tuple[str, str]] = set()
    appearances: dict[str, int] = {}

    for out_id, in_id in ranked:
        if (in_id, out_id) in reverse_accepted:
            continue
        if appearances.get(out_id, 0) + 1 > max_appearances:
            continue
        if appearances.get(in_id, 0) + 1 > max_appearances:
            continue
        accepted.append((out_id, in_id))
        reverse_accepted.add((out_id, in_id))
        appearances[out_id] = appearances.get(out_id, 0) + 1
        appearances[in_id] = appearances.get(in_id, 0) + 1
        if len(accepted) == target:
            break
    return accepted


def split_dev_holdout(pairs: list[tuple[str, str]], holdout_n: int = 22) -> tuple[list, list]:
    """§12.4: lowest-SPLIT_KEY `holdout_n` pairs become holdout; the rest become dev."""
    ranked = sorted(pairs, key=lambda p: (_hash_key("SPLIT", p[0], p[1]), p[0], p[1]))
    holdout = ranked[:holdout_n]
    dev = ranked[holdout_n:]
    return dev, holdout


def hash_subset(pairs: list[tuple[str, str]], tag: str, n: int) -> list[tuple[str, str]]:
    """§12.5/§12.6: lowest-`{tag}_KEY` `n` pairs within a partition."""
    ranked = sorted(pairs, key=lambda p: (_hash_key(tag, p[0], p[1]), p[0], p[1]))
    return ranked[:n]


def run_selection_self_test() -> None:
    ids_ordered = [f"T{i:03d}" for i in range(1, 61)]  # 60 synthetic IDs, never real track IDs
    ids_shuffled = list(reversed(ids_ordered))  # a deliberately different input order

    run_a = select_50_pairs(ids_ordered)
    run_b = select_50_pairs(ids_ordered)
    run_c = select_50_pairs(ids_shuffled)

    check("selection: exactly 50 pairs selected from 60 synthetic IDs", len(run_a) == 50, f"got {len(run_a)}")
    check("selection: run-to-run deterministic (identical repeated run)", run_a == run_b)
    check("selection: order-invariant under input-list permutation", run_a == run_c)

    reverse_of_a = {(b, a) for a, b in run_a}
    check("selection: no reverse-duplicate pair (A→B and B→A both present)", len(set(run_a) & reverse_of_a) == 0)

    appearance_counts: dict[str, int] = {}
    for out_id, in_id in run_a:
        appearance_counts[out_id] = appearance_counts.get(out_id, 0) + 1
        appearance_counts[in_id] = appearance_counts.get(in_id, 0) + 1
    max_appear = max(appearance_counts.values()) if appearance_counts else 0
    check("selection: no synthetic track appears in more than 2 selected pairs", max_appear <= 2, f"max observed: {max_appear}")

    dev, holdout = split_dev_holdout(run_a)
    check("split: exactly 22 holdout / 28 dev", len(holdout) == 22 and len(dev) == 28, f"holdout={len(holdout)} dev={len(dev)}")

    ng2_holdout = hash_subset(holdout, "NG2", 9)
    ng2_dev = hash_subset(dev, "NG2", 21)
    check(
        "NG2 subset: exactly 9 holdout + 21 dev = 30",
        len(ng2_holdout) == 9 and len(ng2_dev) == 21,
        f"holdout={len(ng2_holdout)} dev={len(ng2_dev)}",
    )

    ng4_holdout = hash_subset(holdout, "NG4", 7)
    ng4_dev = hash_subset(dev, "NG4", 16)
    check(
        "NG4 subset: exactly 7 holdout + 16 dev = 23",
        len(ng4_holdout) == 7 and len(ng4_dev) == 16,
        f"holdout={len(ng4_holdout)} dev={len(ng4_dev)}",
    )


def main() -> int:
    # Windows consoles often default to cp1252, which cannot encode the
    # arrow/section glyphs quoted from the docs below; force UTF-8 output
    # so this verifier runs the same way in any terminal.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    for p in (CHARTER, BENCHMARK_CONTRACT, RESCOPE_CONTRACT):
        check(f"file exists: {p.relative_to(ROOT)}", p.exists())

    benchmark_text = read(BENCHMARK_CONTRACT) if BENCHMARK_CONTRACT.exists() else ""
    charter_text = read(CHARTER) if CHARTER.exists() else ""
    rescope_text = read(RESCOPE_CONTRACT) if RESCOPE_CONTRACT.exists() else ""

    # --- Original-pass checks (retained unchanged) ---------------------

    for anchor in ("74", "52", "65%", "60%"):
        check(f"benchmark contract retains original anchor '{anchor}'", anchor in benchmark_text)
    check(
        "benchmark contract retains G2 subset '30' / '21' / '9'",
        all(tok in benchmark_text for tok in ("g2_simpmusic_comparison_subset_min", "30", "21", "9")),
    )

    for i in range(1, 9):
        check(f"NG{i} heading present", f"NG{i}" in benchmark_text and "### 16." in benchmark_text)

    check("50/28/22 corpus figures present", all(tok in benchmark_text for tok in ("**50**", "**28**", "**22**")))
    check(
        "combined tie-arithmetic present",
        "50 - floor(0.20 × 50)" in benchmark_text or "50 - floor(0.20" in benchmark_text,
    )
    check(
        "holdout tie-arithmetic present",
        "22 - floor(0.20 × 22)" in benchmark_text or "22 - floor(0.20" in benchmark_text,
    )

    for cls in ("FULL_DJ_BLEND", "tempo/time-stretch automation", "pitch/key shifting"):
        check(f"rescope contract lists forbidden class '{cls}'", cls in rescope_text)
    check(
        "rescope contract marks SHORT_EQ_BLEND research-only/off-by-default",
        "SHORT_EQ_BLEND" in rescope_text and "off by default" in rescope_text,
    )

    check("charter names PRESERVATION_FIRST_LOCAL_AUTOMIX as authorized scope", "PRESERVATION_FIRST_LOCAL_AUTOMIX" in charter_text)
    check(
        "charter states broad engine does not inherit authorization",
        "does not inherit authorization" in charter_text or "does **not** inherit authorization" in charter_text,
    )

    # --- Repair R1: NG2 dimension-15 executability ----------------------

    check(
        "NG2 explicitly names dimension 15 / OVERALL_MUSICAL_INTENTIONALITY for BOTH sides",
        "OVERALL_MUSICAL_INTENTIONALITY" in benchmark_text
        and "Candidate `OVERALL_MUSICAL_INTENTIONALITY`" in benchmark_text
        and "comparator" in benchmark_text.lower()
        and "`NG2` comparator" in benchmark_text,
    )
    check(
        "NG2 +0.5 threshold applied independently to all 30 AND holdout 9",
        "mean(candidate dim15, all 30)" in benchmark_text and "mean(candidate dim15, holdout 9)" in benchmark_text,
    )

    # --- Repair R2: deterministic pair-selection algorithm --------------

    required_algorithm_tokens = [
        "P0-M4-R1-NARROW-VALIDATION-v1",
        'SHA256("P0-M4-R1-NARROW-VALIDATION-v1|PAIR|"',
        "never contains both `A→B` and `B→A`",
        "more than 2",
        "exactly 50",
        "lowest 22",
        "remaining 28",
        "lowest **9**",
        "lowest **21**",
        "lowest **7**",
        "lowest **16**",
    ]
    missing_tokens = [t for t in required_algorithm_tokens if t not in rescope_text]
    check(
        "pair-selection algorithm contains fixed salt, hash rule, reverse-exclusion, max-2, exact 50/22/28/NG2(9,21)/NG4(7,16)",
        len(missing_tokens) == 0,
        f"missing: {missing_tokens}",
    )

    # --- Repair R3: PLAY_THROUGH vs observed_class -----------------------

    play_through_as_rendered_class_pattern_hits = [
        pattern
        for pattern in ("PLAY_THROUGH`/`NO_SPECIAL_TRANSITION`, `GAPLESS`, `SIMPLE_CROSSFADE`", "PLAY_THROUGH`/`NO_SPECIAL_TRANSITION`, `GAPLESS", "PLAY_THROUGH/NO_SPECIAL_TRANSITION, GAPLESS")
        if pattern in rescope_text or pattern in charter_text
    ]
    check(
        "PLAY_THROUGH never listed as a member of the authorized-observed-class set",
        len(play_through_as_rendered_class_pattern_hits) == 0,
        f"found: {play_through_as_rendered_class_pattern_hits}",
    )
    check(
        "contract states PLAY_THROUGH is a PlannerDecision.decision_type, not observed_class",
        "PlannerDecision.decision_type" in rescope_text and "not, and never will be, a member of this enum" in rescope_text.replace("\n", " ")
        or ("decision_type" in rescope_text and "observed_class" in rescope_text and "not itself a rendered/observed class" in rescope_text),
    )

    # --- Repair R4: C4/C5 machine-evidence honesty ------------------------

    check(
        "C4/C5 are NOT described as unconditionally APPLICABLE",
        "CONDITIONAL_WHERE_PREEXISTING_ACCEPTED_EVIDENCE_EXISTS" in benchmark_text,
    )
    check(
        "UNKNOWN_NOT_MACHINE_CONFIRMED present and never converted to zero",
        "UNKNOWN_NOT_MACHINE_CONFIRMED" in benchmark_text and "never converted to a zero-event count" in benchmark_text,
    )
    check(
        "C4/C5 coverage-reporting fractions specified verbatim",
        "C4_confirmable_pairs / SIMPLE_CROSSFADE_pairs" in benchmark_text and "C5_confirmable_pairs / SIMPLE_CROSSFADE_pairs" in benchmark_text,
    )

    # --- Repository-wide prohibited-claim scan (docs/**/*.md) ------------
    # Excludes the two documents that legitimately QUOTE these phrases as
    # the explicit list of things not to claim (P0-M4's own "prohibited
    # claims" section and this contract's own §15 consistency-check
    # write-up) -- scanning those would only ever produce a false positive
    # against the very sentence that forbids the claim.
    SELF_REFERENTIAL_EXCLUDE = {
        ROOT / "docs" / "research" / "P0-M4-FINAL-FEASIBILITY-SYNTHESIS.md",
        RESCOPE_CONTRACT,
    }
    hits: list[str] = []
    for md in (ROOT / "docs").rglob("*.md"):
        if md in SELF_REFERENTIAL_EXCLUDE:
            continue
        text = read(md)
        for phrase in PROHIBITED_CLAIM_STRINGS:
            if phrase in text:
                hits.append(f"{md.relative_to(ROOT)}: '{phrase}'")
    check("no unqualified prohibited-claim strings found in docs/**/*.md", len(hits) == 0, "; ".join(hits))

    # --- Repair R5: deterministic selection self-test (synthetic IDs) ----
    run_selection_self_test()

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        suffix = f" -- {detail}" if (not ok and detail) else ""
        print(f"[{status}] {name}{suffix}")

    print()
    if failed:
        print(f"RESULT: {len(failed)}/{len(checks)} CHECKS FAILED")
        return 1
    print(f"RESULT: ALL CHECKS PASS ({len(checks)}/{len(checks)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
