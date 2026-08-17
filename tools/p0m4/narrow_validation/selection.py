"""
P0-M4-R2 PF1 -- deterministic real-corpus pair selection.

Implements, verbatim, the accepted P0-M4-R1 rescope contract's frozen
selection algorithm (`docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-
CONTRACT.md` SS12), with fixed salt `P0-M4-R1-NARROW-VALIDATION-v1`. This
module is intentionally a clean re-implementation (not an import) of the
same algorithm `tools/p0m4/verify_rescope_contract.py` already self-tests
against synthetic IDs -- keeping them independent lets either catch drift
in the other, matching this repository's existing verifier pattern.

No filename/title/artist/path is ever read or written by this module: the
only input is the sorted list of opaque track IDs (the keys of the private,
gitignored `id_map.local.json`), and the only output is a sanitized
manifest keyed entirely by those same opaque IDs.

Usage:
    python tools/p0m4/narrow_validation/selection.py \
        --id-map-local tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
        --manifest-out tools/p0m4/narrow_validation/manifest_sanitized.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SELECTION_SALT = "P0-M4-R1-NARROW-VALIDATION-v1"

TARGET_TOTAL = 50
TARGET_HOLDOUT = 22
TARGET_DEV = TARGET_TOTAL - TARGET_HOLDOUT  # 28
MAX_APPEARANCES = 2

NG2_HOLDOUT_N = 9
NG2_DEV_N = 21
NG4_HOLDOUT_N = 7
NG4_DEV_N = 16


def _hash_key(tag: str, out_id: str, in_id: str) -> str:
    payload = f"{SELECTION_SALT}|{tag}|{out_id}|{in_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_pairs(ids: list[str], target: int = TARGET_TOTAL, max_appearances: int = MAX_APPEARANCES) -> list[tuple[str, str]]:
    """SS12.1-SS12.3: deterministic pair-selection scan. Input order never
    matters -- the ids are re-sorted lexicographically first (SS12.1)."""
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


def split_dev_holdout(pairs: list[tuple[str, str]], holdout_n: int = TARGET_HOLDOUT) -> tuple[list, list]:
    """SS12.4: lowest-SPLIT_KEY `holdout_n` pairs become holdout; the rest dev."""
    ranked = sorted(pairs, key=lambda p: (_hash_key("SPLIT", p[0], p[1]), p[0], p[1]))
    holdout = ranked[:holdout_n]
    dev = ranked[holdout_n:]
    return dev, holdout


def hash_subset(pairs: list[tuple[str, str]], tag: str, n: int) -> list[tuple[str, str]]:
    """SS12.5/SS12.6: lowest-`{tag}_KEY` `n` pairs within a partition."""
    ranked = sorted(pairs, key=lambda p: (_hash_key(tag, p[0], p[1]), p[0], p[1]))
    return ranked[:n]


def build_manifest(ids: list[str]) -> dict:
    pairs = select_pairs(ids)
    if len(pairs) != TARGET_TOTAL:
        return {
            "status": "SHORTFALL_HARD_STOP",
            "requested": TARGET_TOTAL,
            "accepted": len(pairs),
            "note": "SS12.3 hard stop: fewer than 50 pairs could be accepted under the no-reverse-duplicate / "
                    "max-2-appearances constraints. Constraints are never loosened automatically.",
        }

    dev, holdout = split_dev_holdout(pairs)
    assert len(dev) == TARGET_DEV and len(holdout) == TARGET_HOLDOUT

    ng2_holdout = hash_subset(holdout, "NG2", NG2_HOLDOUT_N)
    ng2_dev = hash_subset(dev, "NG2", NG2_DEV_N)
    ng4_holdout = hash_subset(holdout, "NG4", NG4_HOLDOUT_N)
    ng4_dev = hash_subset(dev, "NG4", NG4_DEV_N)

    ng2_set = set(ng2_holdout) | set(ng2_dev)
    ng4_set = set(ng4_holdout) | set(ng4_dev)
    holdout_set = set(holdout)

    def pair_record(out_id: str, in_id: str, split: str) -> dict:
        return {
            "out_id": out_id,
            "in_id": in_id,
            "split": split,
            "ng2_member": (out_id, in_id) in ng2_set,
            "ng4_member": (out_id, in_id) in ng4_set,
        }

    all_records = []
    for out_id, in_id in pairs:
        split = "holdout" if (out_id, in_id) in holdout_set else "dev"
        all_records.append(pair_record(out_id, in_id, split))

    return {
        "status": "FROZEN",
        "selection_salt": SELECTION_SALT,
        "algorithm_ref": "docs/research/P0-M4-R1-PRESERVATION-FIRST-RESCOPE-CONTRACT.md SS12",
        "input_id_count": len(set(ids)),
        "total_pairs": len(pairs),
        "dev_count": len(dev),
        "holdout_count": len(holdout),
        "ng2_count": len(ng2_dev) + len(ng2_holdout),
        "ng2_dev_count": len(ng2_dev),
        "ng2_holdout_count": len(ng2_holdout),
        "ng4_count": len(ng4_dev) + len(ng4_holdout),
        "ng4_dev_count": len(ng4_dev),
        "ng4_holdout_count": len(ng4_holdout),
        "pairs": all_records,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id-map-local", required=True, help="Path to the private id_map.local.json (only its KEYS are read; never committed).")
    ap.add_argument("--manifest-out", required=True, help="Path to write the sanitized (opaque-ID-only) manifest.")
    args = ap.parse_args()

    id_map = json.loads(Path(args.id_map_local).read_text(encoding="utf-8"))
    ids = sorted(id_map.keys())  # opaque IDs only; path VALUES are never touched here

    manifest = build_manifest(ids)
    Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"STATUS: {manifest['status']}")
    if manifest["status"] == "FROZEN":
        print(f"input_id_count={manifest['input_id_count']} total_pairs={manifest['total_pairs']} "
              f"dev={manifest['dev_count']} holdout={manifest['holdout_count']} "
              f"ng2={manifest['ng2_count']} (dev={manifest['ng2_dev_count']}/holdout={manifest['ng2_holdout_count']}) "
              f"ng4={manifest['ng4_count']} (dev={manifest['ng4_dev_count']}/holdout={manifest['ng4_holdout_count']})")
    print(f"Wrote sanitized (opaque-ID-only) manifest to {args.manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
