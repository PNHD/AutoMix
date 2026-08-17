"""
P0-M4-R1 docs-only consistency verifier.

Checks that the P0-M4-R1 rescope contract's exact-number and exact-phrase
claims are actually present in the repository docs, mechanically, so a
future edit cannot silently drift from what this task's handoff describes.

No audio, no network, no ML/analyzer import. Reads only the four
`docs/**/*.md` files this task's contract names, plus a repository-wide
prohibited-claim scan.

Usage:
    python tools/p0m4/verify_rescope_contract.py
"""
from __future__ import annotations

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


def main() -> int:
    for p in (CHARTER, BENCHMARK_CONTRACT, RESCOPE_CONTRACT):
        check(f"file exists: {p.relative_to(ROOT)}", p.exists())

    benchmark_text = read(BENCHMARK_CONTRACT) if BENCHMARK_CONTRACT.exists() else ""
    charter_text = read(CHARTER) if CHARTER.exists() else ""
    rescope_text = read(RESCOPE_CONTRACT) if RESCOPE_CONTRACT.exists() else ""

    # 1. Original G1-G8 numeric anchors unchanged/present.
    original_anchors = ["74", "52", "22", "65%", "60%", "n≥", "30", "21", "9"]
    for anchor in ("74", "52", "65%", "60%"):
        check(f"benchmark contract retains original anchor '{anchor}'", anchor in benchmark_text)
    check(
        "benchmark contract retains G2 subset '30' / '21' / '9'",
        all(tok in benchmark_text for tok in ("g2_simpmusic_comparison_subset_min", "30", "21", "9")),
    )

    # 2. NG1-NG8 headings present.
    for i in range(1, 9):
        check(f"NG{i} heading present", f"NG{i}" in benchmark_text and f"### 16." in benchmark_text)

    # 3. Corpus arithmetic present verbatim.
    check("50/28/22 corpus figures present", all(tok in benchmark_text for tok in ("**50**", "**28**", "**22**")))
    check(
        "combined tie-arithmetic present",
        "50 - floor(0.20 × 50)" in benchmark_text or "50 × 20%" in benchmark_text or "50 - floor(0.20" in benchmark_text,
    )
    check(
        "holdout tie-arithmetic present",
        "22 - floor(0.20 × 22)" in benchmark_text or "22 - floor(0.20" in benchmark_text,
    )

    # 4. Rescope contract forbidden-class list + SHORT_EQ_BLEND research-only statement.
    for cls in ("FULL_DJ_BLEND", "tempo/time-stretch automation", "pitch/key shifting"):
        check(f"rescope contract lists forbidden class '{cls}'", cls in rescope_text)
    check(
        "rescope contract marks SHORT_EQ_BLEND research-only/off-by-default",
        "SHORT_EQ_BLEND" in rescope_text and "off by default" in rescope_text,
    )

    # 5. Charter authorized-scope statement.
    check("charter names PRESERVATION_FIRST_LOCAL_AUTOMIX as authorized scope", "PRESERVATION_FIRST_LOCAL_AUTOMIX" in charter_text)
    check(
        "charter states broad engine does not inherit authorization",
        "does not inherit authorization" in charter_text or "does **not** inherit authorization" in charter_text,
    )

    # 6. Repository-wide prohibited-claim scan (docs/**/*.md).
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
