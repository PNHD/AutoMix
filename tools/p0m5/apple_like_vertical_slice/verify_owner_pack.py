"""
P0-M5-R1 Phase F verifier -- checks the local owner-listening pack
directory (before zipping) for exactly the required contents and no
privacy leaks. Never prints blind-key values.

Usage:
    python tools/p0m5/apple_like_vertical_slice/verify_owner_pack.py \
        --pack-dir tools/p0m5/apple_like_vertical_slice/work_local/owner_pack
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-dir", required=True)
    args = ap.parse_args()

    pack_dir = Path(args.pack_dir)
    clips_dir = pack_dir / "clips"

    check("pack directory exists", pack_dir.exists(), str(pack_dir))
    check("clips directory exists", clips_dir.exists())
    if not clips_dir.exists():
        for name, ok, detail in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return 1

    clip_files = sorted(p.name for p in clips_dir.glob("*.wav"))
    check("exactly 16 WAV clips", len(clip_files) == 16, str(len(clip_files)))

    expected_names = set()
    for i in range(1, 9):
        expected_names.add(f"S{i:02d}-A.wav")
        expected_names.add(f"S{i:02d}-B.wav")
    check("clip filenames are exactly S01-A..S08-B (tokens only)", set(clip_files) == expected_names, str(sorted(set(clip_files) ^ expected_names)))

    # No filename may leak a method name, opaque ID, or split label.
    leak_pattern = re.compile(r"(M0|M1|RM\d{3}|dev|holdout)", re.IGNORECASE)
    leaky = [f for f in clip_files if leak_pattern.search(f)]
    check("no clip filename leaks method/opaque-ID/split", len(leaky) == 0, str(leaky))

    check("LISTENING_INSTRUCTIONS.md present", (pack_dir / "LISTENING_INSTRUCTIONS.md").exists())
    check("OWNER_RATINGS_TEMPLATE.json present", (pack_dir / "OWNER_RATINGS_TEMPLATE.json").exists())

    if (pack_dir / "OWNER_RATINGS_TEMPLATE.json").exists():
        tmpl = json.loads((pack_dir / "OWNER_RATINGS_TEMPLATE.json").read_text(encoding="utf-8"))
        rows = tmpl.get("ratings", [])
        check("rating template has exactly 8 scenario rows", len(rows) == 8, str(len(rows)))
        required_fields = {
            "scenario", "overall_preference", "A_seamlessness_1_5", "B_seamlessness_1_5",
            "A_musical_intentionality_1_5", "B_musical_intentionality_1_5",
            "A_unacceptable_veto", "B_unacceptable_veto", "note",
        }
        for row in rows:
            missing = required_fields - set(row.keys())
            check(f"rating row {row.get('scenario')}: has all 9 required fields", not missing, str(missing))
        raw = json.dumps(tmpl)
        check("rating template contains no method names/opaque IDs/split labels", not leak_pattern.search(raw), "leak found" if leak_pattern.search(raw) else "")

    if (pack_dir / "LISTENING_INSTRUCTIONS.md").exists():
        instr = (pack_dir / "LISTENING_INSTRUCTIONS.md").read_text(encoding="utf-8")
        check("instructions do not mention method names/opaque IDs/split labels", not leak_pattern.search(instr), "leak found" if leak_pattern.search(instr) else "")
        check("instructions collect all 8 rating dimensions", all(s in instr for s in ("Overall preference", "seamlessness", "musical intentionality", "veto")))

    check("blind_key.local.json exists LOCALLY (not itself a leak -- verified separately never zipped)", (pack_dir / "blind_key.local.json").exists())

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
