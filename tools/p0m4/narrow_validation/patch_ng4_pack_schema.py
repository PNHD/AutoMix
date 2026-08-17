"""
P0-M4-R2 PF4 repair -- in-place schema migration for an EXISTING local NG4
annotation pack.

PM REVIEW (`PHASE0_PF4_REPAIR_REQUIRED`, Issue #9 comment `5318289406`):
the owner-facing response schema was repaired (single `assigned_class` ->
independent per-class `class_acceptability` booleans) in `build_ng4_
annotation_pack.py`. That repair must NOT invalidate a pack that was
already built with the old schema -- the 46 source clips and the blind
token<->pair mapping are expensive/sensitive to regenerate and carry no
defect of their own (only the RESPONSE SCHEMA was wrong).

This script patches `INSTRUCTIONS.md` and `response_template.json` of an
EXISTING pack directory IN PLACE, using the exact same shared schema
builder (`build_ng4_annotation_pack.build_response_template`/
`INSTRUCTIONS_TEXT`) the corrected fresh-build path now uses -- so the two
paths can never drift apart. It:

  - reads ONLY the token set (keys) from the existing `blind_key.local.
    json` -- never prints or logs any value (opaque IDs/split) from it;
  - never touches `clips/` or `blind_key.local.json`;
  - refuses to run if any response has already been filled in (protects
    real owner answers from being silently discarded by a schema change);
  - refuses to run if the existing token count is not exactly 23.

Usage:
    python tools/p0m4/narrow_validation/patch_ng4_pack_schema.py \
        --pack-dir tools/p0m4/narrow_validation/work_local/ng4_annotation_pack
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_ng4_annotation_pack import build_response_template, INSTRUCTIONS_TEXT, NARROW_CLASSES  # noqa: E402


def response_already_filled(old_template: dict) -> bool:
    for row in old_template.get("responses", []):
        if "assigned_class" in row and row.get("assigned_class") not in (None, ""):
            return True
        ca = row.get("class_acceptability")
        if isinstance(ca, dict) and any(v is not None for v in ca.values()):
            return True
        if row.get("confidence") not in (None, ""):
            return True
        if row.get("note"):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-dir", required=True, help="Existing LOCAL-ONLY pack directory to patch in place.")
    ap.add_argument("--force", action="store_true", help="Patch even if the existing template appears partially filled in (NOT recommended -- real owner answers would be discarded).")
    args = ap.parse_args()

    pack_dir = Path(args.pack_dir)
    blind_key_path = pack_dir / "blind_key.local.json"
    template_path = pack_dir / "response_template.json"
    instructions_path = pack_dir / "INSTRUCTIONS.md"
    clips_dir = pack_dir / "clips"

    if not blind_key_path.exists():
        print(f"RESULT: BLOCKED -- no existing pack found at {pack_dir} (blind_key.local.json missing). Use build_ng4_annotation_pack.py for a fresh build instead.")
        return 1
    if not clips_dir.exists() or not any(clips_dir.iterdir()):
        print(f"RESULT: BLOCKED -- {clips_dir} is missing or empty; refusing to patch a pack with no clips.")
        return 1

    blind_key = json.loads(blind_key_path.read_text(encoding="utf-8"))
    tokens = sorted(blind_key.keys())  # tokens only -- never a value from blind_key is read/printed below
    if len(tokens) != 23:
        print(f"RESULT: BLOCKED -- expected exactly 23 tokens in the existing blind key, found {len(tokens)}. Refusing to patch.")
        return 1

    if template_path.exists():
        old_template = json.loads(template_path.read_text(encoding="utf-8"))
        if response_already_filled(old_template) and not args.force:
            print("RESULT: BLOCKED -- the existing response_template.json appears to already contain owner answers. "
                  "Refusing to overwrite without --force (which would discard them).")
            return 1
        old_tokens = sorted(r.get("token") for r in old_template.get("responses", []))
        if old_tokens != tokens:
            print("RESULT: BLOCKED -- existing response_template.json token set does not match blind_key.local.json's token set. Refusing to patch (would silently change pack identity).")
            return 1

    new_template = build_response_template(tokens)
    template_path.write_text(json.dumps(new_template, indent=2), encoding="utf-8")
    instructions_path.write_text(INSTRUCTIONS_TEXT, encoding="utf-8")

    print("RESULT: PATCHED")
    print(f"Patched schema in place at: {pack_dir}")
    print(f"  tokens preserved:   {len(tokens)} (unchanged identity)")
    print(f"  narrow classes:     {NARROW_CLASSES}")
    print(f"  clips/ untouched:   yes")
    print(f"  blind_key untouched: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
