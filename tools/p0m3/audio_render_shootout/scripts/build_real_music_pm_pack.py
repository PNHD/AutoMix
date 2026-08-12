"""
P0-M3-R3 STAGE B -- builds `P0-M3-R3-REAL-MUSIC-PM-REVIEW.zip` (LOCAL ONLY,
never committed). Because this pass uses private copyrighted owner music,
this pack contains NO source tracks and NO derived audible real-music clips
(Issue #7 PM STAGE B comment) -- sanitized evidence only:

- generic code/docs added or changed this pass (source, no data)
- sanitized aggregate corpus summary (counts/histograms, no filenames)
- sanitized selection rationale/trace (opaque RM### IDs only)
- per-pair REAL PlannerDecision JSON (already free of any file path by
  construction -- `real_music_pipeline.py::build_tx_fixture` never writes a
  path into the fixture/decision)
- per-pair render result/metadata JSON (loudness/tempo/safety diagnostics,
  same path-free-by-construction property)
- the real-music blind key (opaque clip IDs <-> internal pair-id/candidate
  letter only -- NEVER the RM###->real-file mapping, which stays in
  `real_music/work_local/corpus/id_map.local.json` and is excluded here by
  not being referenced at all)
- validation script outputs

Usage:
    python scripts/build_real_music_pm_pack.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

ZIP_PATH = REPO_ROOT / "P0-M3-R3-REAL-MUSIC-PM-REVIEW.zip"

# Explicit ALLOWLIST of files -- never a directory glob over real_music/work_local/
# (which also contains id_map.local.json / corpus_analysis.local.json's sibling
# raw-path-bearing artifacts elsewhere in that tree by design).
CODE_FILES = [
    "scripts/analyze_owner_corpus.py",
    "scripts/select_real_music_pairs.py",
    "scripts/real_music_signalsmith.py",
    "scripts/build_real_music_owner_pack.py",
    "scripts/build_real_music_pm_pack.py",
    "scripts/verify_real_music_stage_b.py",
    "scripts/mutation_test_real_music_stage_b.py",
    "scripts/real_music_pipeline.py",
    "real_music/MANIFEST_SCHEMA.md",
]

EVIDENCE_FILES = [
    "real_music/work_local/corpus_summary_sanitized.json",
    "real_music/work_local/selection_rationale_sanitized.json",
    "real_music/work_local/selection_trace.local.json",
    "real_music/work_local/pipeline_summary_sanitized.json",
    "real_music/work_local/real_music_blind_key.local.json",
    "real_music/work_local/renders/REAL-V1/planner_decision.json",
    "real_music/work_local/renders/REAL-V1/result.json",
    "real_music/work_local/renders/REAL-V2/planner_decision.json",
    "real_music/work_local/renders/REAL-V2/result.json",
    "real_music/work_local/renders/REAL-V2/C_signalsmith_owner_result.json",
    "real_music/work_local/renders/REAL-V3/planner_decision.json",
    "real_music/work_local/renders/REAL-V3/result.json",
    "real_music/work_local/validation_report.json",
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
                zf.write(p, f"evidence/{rel.replace('real_music/work_local/', '')}")
                entries.append(f"evidence/{rel.replace('real_music/work_local/', '')}")
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
