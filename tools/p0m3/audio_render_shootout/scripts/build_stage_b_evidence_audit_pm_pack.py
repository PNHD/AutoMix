"""
P0-M3-R3 STAGE-B EVIDENCE AUDIT REPAIR -- builds
`P0-M3-R3-STAGE-B-EVIDENCE-AUDIT-PM-REVIEW.zip` (LOCAL ONLY, never
committed) per the newest Issue #7 PM comment ("PM STAGE-B REAL-EVIDENCE
REPAIR REVIEW -- NARROW REPAIR REQUIRED"). No owner audio was decoded,
rendered, or included this pass -- this ZIP is code + sanitized evidence
only.

Usage:
    python scripts/build_stage_b_evidence_audit_pm_pack.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

ZIP_PATH = REPO_ROOT / "P0-M3-R3-STAGE-B-EVIDENCE-AUDIT-PM-REVIEW.zip"

CODE_FILES = [
    "scripts/select_real_music_pairs.py",
    "scripts/pair_gate_audit.py",
    "scripts/compute_pair_gate_calibration.py",
    "scripts/verify_real_music_stage_b.py",
    "scripts/mutation_test_real_music_stage_b.py",
    "scripts/build_stage_b_evidence_audit_pm_pack.py",
]

EVIDENCE_FILES = [
    "real_music/work_local/pair_gate_calibration_sanitized.json",
    "real_music/work_local/selection_rationale_sanitized.json",
    "real_music/work_local/selection_trace.local.json",
    "real_music/work_local/verifier_output.txt",
    "real_music/work_local/mutation_test_output.txt",
]

DOC_FILES = [
    "docs/research/P0-M3-R3-REAL-MUSIC-STAGE-B.md",
]

HANDOFF_FILE = "HANDOFF_TO_PM.md"


def main():
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    entries = []
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in CODE_FILES:
            p = ROOT / rel
            if p.exists():
                zf.write(p, f"code/{rel}")
                entries.append(f"code/{rel}")
        for rel in EVIDENCE_FILES:
            p = ROOT / rel
            if p.exists():
                arcname = f"evidence/{rel.replace('real_music/work_local/', '')}"
                zf.write(p, arcname)
                entries.append(arcname)
        for rel in DOC_FILES:
            p = REPO_ROOT / rel
            if p.exists():
                zf.write(p, rel)
                entries.append(rel)
        handoff_path = REPO_ROOT / HANDOFF_FILE
        if handoff_path.exists():
            zf.write(handoff_path, HANDOFF_FILE)
            entries.append(HANDOFF_FILE)

    print(f"Wrote {ZIP_PATH} with {len(entries)} entries")
    for e in entries:
        print(f"  {e}")


if __name__ == "__main__":
    main()
