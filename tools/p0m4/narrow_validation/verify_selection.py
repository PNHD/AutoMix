"""
P0-M4-R2 PF1 verifier -- independently checks the deterministic pair-
selection algorithm (`selection.py`) and, when present, the frozen sanitized
manifest it produced.

Three independent layers, none requiring the private corpus to be present:

1. Synthetic self-test (order-invariance, run-to-run determinism, no
   reverse duplicates, max-2-appearances, exact split/subset counts) --
   mirrors `tools/p0m4/verify_rescope_contract.py`'s own R5 self-test, kept
   as an independent re-implementation so either can catch drift in the
   other.
2. Structural validation of the committed `manifest_sanitized.json` (opaque
   IDs only; no path/filename is ever referenced), checking the exact
   frozen counts this task requires.
3. OPTIONAL: if the private local corpus id_map is present on this machine,
   recompute selection from it and byte-diff against the committed
   manifest -- proves the committed manifest is exactly reproducible from
   the current corpus + fixed salt, not hand-edited. Skipped (not failed)
   when the private corpus is absent, so this verifier still runs
   standalone for PM review without owner audio.

Usage:
    python tools/p0m4/narrow_validation/verify_selection.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import selection as sel  # noqa: E402

MANIFEST_PATH = HERE / "manifest_sanitized.json"
PRIVATE_ID_MAP = HERE.parents[1] / "p0m3" / "audio_render_shootout" / "real_music" / "work_local" / "corpus" / "id_map.local.json"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def run_synthetic_self_test() -> None:
    ids_ordered = [f"T{i:03d}" for i in range(1, 61)]
    ids_shuffled = list(reversed(ids_ordered))

    run_a = sel.select_pairs(ids_ordered)
    run_b = sel.select_pairs(ids_ordered)
    run_c = sel.select_pairs(ids_shuffled)

    check("synthetic: exactly 50 pairs from 60 synthetic IDs", len(run_a) == 50, f"got {len(run_a)}")
    check("synthetic: run-to-run deterministic", run_a == run_b)
    check("synthetic: order-invariant under input permutation", run_a == run_c)

    reverse_of_a = {(b, a) for a, b in run_a}
    check("synthetic: no reverse-duplicate pair", len(set(run_a) & reverse_of_a) == 0)

    appearances: dict[str, int] = {}
    for out_id, in_id in run_a:
        appearances[out_id] = appearances.get(out_id, 0) + 1
        appearances[in_id] = appearances.get(in_id, 0) + 1
    check("synthetic: no track appears more than twice", max(appearances.values()) <= 2, f"max={max(appearances.values())}")

    dev, holdout = sel.split_dev_holdout(run_a)
    check("synthetic: exactly 22 holdout / 28 dev", len(holdout) == 22 and len(dev) == 28)

    ng2_h = sel.hash_subset(holdout, "NG2", sel.NG2_HOLDOUT_N)
    ng2_d = sel.hash_subset(dev, "NG2", sel.NG2_DEV_N)
    check("synthetic: NG2 exactly 9 holdout + 21 dev", len(ng2_h) == 9 and len(ng2_d) == 21)

    ng4_h = sel.hash_subset(holdout, "NG4", sel.NG4_HOLDOUT_N)
    ng4_d = sel.hash_subset(dev, "NG4", sel.NG4_DEV_N)
    check("synthetic: NG4 exactly 7 holdout + 16 dev", len(ng4_h) == 7 and len(ng4_d) == 16)


def validate_committed_manifest() -> None:
    check("committed manifest exists", MANIFEST_PATH.exists(), str(MANIFEST_PATH))
    if not MANIFEST_PATH.exists():
        return
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    check("manifest status FROZEN", m.get("status") == "FROZEN", str(m.get("status")))
    check("manifest salt matches contract SS12.2", m.get("selection_salt") == sel.SELECTION_SALT)
    check("manifest total_pairs == 50", m.get("total_pairs") == 50, str(m.get("total_pairs")))
    check("manifest dev_count == 28", m.get("dev_count") == 28)
    check("manifest holdout_count == 22", m.get("holdout_count") == 22)
    check("manifest ng2 == 30 (21 dev / 9 holdout)", m.get("ng2_count") == 30 and m.get("ng2_dev_count") == 21 and m.get("ng2_holdout_count") == 9)
    check("manifest ng4 == 23 (16 dev / 7 holdout)", m.get("ng4_count") == 23 and m.get("ng4_dev_count") == 16 and m.get("ng4_holdout_count") == 7)

    pairs = m.get("pairs", [])
    check("manifest pairs list has exactly 50 entries", len(pairs) == 50, str(len(pairs)))

    # No private data: every id must look like an opaque RM### token, never
    # a path separator, drive letter, or long filename-like string.
    leak_hits = []
    for p in pairs:
        for key in ("out_id", "in_id"):
            v = p.get(key, "")
            if ("/" in v or "\\" in v or "." in v or len(v) > 12):
                leak_hits.append(f"{key}={v!r}")
    check("no path-like/non-opaque tokens in manifest pair IDs", len(leak_hits) == 0, "; ".join(leak_hits))

    seen = set()
    reverse_hits = []
    appear_count: dict[str, int] = {}
    for p in pairs:
        a, b = p["out_id"], p["in_id"]
        if (b, a) in seen:
            reverse_hits.append(f"{a}->{b} vs {b}->{a}")
        seen.add((a, b))
        appear_count[a] = appear_count.get(a, 0) + 1
        appear_count[b] = appear_count.get(b, 0) + 1
    check("manifest: no reverse-duplicate pair", len(reverse_hits) == 0, "; ".join(reverse_hits))
    over = {k: v for k, v in appear_count.items() if v > 2}
    check("manifest: no opaque ID appears in more than 2 pairs", len(over) == 0, str(over))

    dev_n = sum(1 for p in pairs if p["split"] == "dev")
    holdout_n = sum(1 for p in pairs if p["split"] == "holdout")
    check("manifest: split counts match dev/holdout fields", dev_n == 28 and holdout_n == 22, f"dev={dev_n} holdout={holdout_n}")

    ng2_n = sum(1 for p in pairs if p.get("ng2_member"))
    ng4_n = sum(1 for p in pairs if p.get("ng4_member"))
    check("manifest: ng2_member flags sum to 30", ng2_n == 30, str(ng2_n))
    check("manifest: ng4_member flags sum to 23", ng4_n == 23, str(ng4_n))

    ng2_holdout_n = sum(1 for p in pairs if p.get("ng2_member") and p["split"] == "holdout")
    ng2_dev_n = sum(1 for p in pairs if p.get("ng2_member") and p["split"] == "dev")
    check("manifest: ng2 split is exactly 9 holdout / 21 dev", ng2_holdout_n == 9 and ng2_dev_n == 21, f"holdout={ng2_holdout_n} dev={ng2_dev_n}")

    ng4_holdout_n = sum(1 for p in pairs if p.get("ng4_member") and p["split"] == "holdout")
    ng4_dev_n = sum(1 for p in pairs if p.get("ng4_member") and p["split"] == "dev")
    check("manifest: ng4 split is exactly 7 holdout / 16 dev", ng4_holdout_n == 7 and ng4_dev_n == 16, f"holdout={ng4_holdout_n} dev={ng4_dev_n}")


def cross_check_against_private_corpus_if_present() -> None:
    if not PRIVATE_ID_MAP.exists():
        check("optional: private-corpus cross-check (SKIPPED, corpus not present on this machine)", True)
        return
    ids = sorted(json.loads(PRIVATE_ID_MAP.read_text(encoding="utf-8")).keys())
    recomputed = sel.build_manifest(ids)
    committed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    check(
        "private-corpus cross-check: committed manifest reproduces exactly from current corpus + fixed salt",
        recomputed == committed,
        "manifest differs from a fresh recomputation -- corpus changed or manifest was hand-edited" if recomputed != committed else "",
    )


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    run_synthetic_self_test()
    validate_committed_manifest()
    cross_check_against_private_corpus_if_present()

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
    raise SystemExit(main())
