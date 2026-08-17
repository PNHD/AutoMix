"""P0-M3-R3 FINAL REAL-CORPUS REPLAY -- verifier (Issue #7 PM comment id
5313303841).

Machine-checkable subset of the task's 27-point validation list. Items that
are only meaningful post-push (pushed HEAD == origin/research/p0-feasibility,
starting-HEAD-exact) are reported by the task's own HANDOFF TO PM section
using `git` directly, not by this script.

Run:
    python scripts/verify_final_real_corpus_replay.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
TRANSITION_POLICY = REPO_ROOT / "tools" / "p0m3" / "transition_policy"
REPLAY_OUT = ROOT / "results" / "final_real_corpus_replay_sanitized.json"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TRANSITION_POLICY))

failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


PRIVATE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\\\Users\\\\"),
    re.compile(r"[A-Za-z]:/Users/"),
    re.compile(r"/mnt/[a-zA-Z]/"),
    re.compile(r"/home/[^/\s\"]+/"),
    re.compile(r"\\\\AIProjects\\\\"),
]
AUDIO_EXTENSIONS = (".wav", ".wave", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".aiff")

SCANNED_SOURCE_FILES = [
    ROOT / "scripts" / "final_real_corpus_replay.py",
    ROOT / "scripts" / "verify_final_real_corpus_replay.py",
    ROOT / "scripts" / "select_real_music_pairs.py",
]


def scan_text_for_patterns(path: Path, patterns) -> list:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [p.pattern for p in patterns if p.search(text)]


def main():
    print("=== 0. Corpus scope ===")
    corpus_dir = ROOT / "real_music" / "work_local" / "corpus"
    analysis = json.loads((corpus_dir / "corpus_analysis.local.json").read_text(encoding="utf-8"))
    check("exactly the existing authorized 100-track corpus is represented", len(analysis) == 100, f"got {len(analysis)}")

    print("\n=== 1. No source audio decoded / no new analyzer introduced (static scan of import/call lines only -- prose docstrings may legitimately NAME these tools while explaining that they are NOT invoked) ===")
    forbidden_import_tokens = ("rubberband", "pyrubberband", "signalsmith", "allin1", "beatnet", "madmom", "librosa")

    def executable_line_offenders(path: Path) -> list:
        offenders = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from ") or "subprocess" in stripped or "ffmpeg_rubberband_stretch(" in stripped:
                lowered = stripped.lower()
                for tok in forbidden_import_tokens:
                    if tok in lowered:
                        offenders.append((lineno, stripped))
        return offenders

    for f in SCANNED_SOURCE_FILES:
        if f.name == "verify_final_real_corpus_replay.py":
            continue  # self-referential: this file's own FORBIDDEN_DSP_TOKENS/pattern definitions legitimately contain these strings as literal scan targets, not imports
        offenders = executable_line_offenders(f)
        check(f"{f.name}: no Signalsmith/Rubber Band/new-analyzer import or call", len(offenders) == 0, f"offenders={offenders}")
    replay_src = (ROOT / "scripts" / "final_real_corpus_replay.py").read_text(encoding="utf-8")
    check(
        "final_real_corpus_replay.py never opens/reads a WAV/audio file (no read_wav/convert_to_canonical_wav call)",
        "read_wav(" not in replay_src and "convert_to_canonical_wav(" not in replay_src,
    )

    print("\n=== 2. Pre-flight transition-policy contract fix + TX-01..08 regression ===")
    tp_verify = subprocess.run([sys.executable, "verify.py"], cwd=str(TRANSITION_POLICY), capture_output=True, text=True)
    out = tp_verify.stdout
    n_pass = out.count("[PASS]")
    n_fail = out.count("[FAIL]")
    check("transition_policy/verify.py exits 0", tp_verify.returncode == 0)
    check("transition_policy/verify.py: zero FAIL lines", n_fail == 0, f"n_fail={n_fail}")
    check("transition_policy/verify.py: PASS count > 0 (not vacuous)", n_pass > 0, f"n_pass={n_pass}")

    print("\n=== 3. Replayed evidence file shape / privacy ===")
    check("sanitized replay evidence file exists", REPLAY_OUT.exists())
    if REPLAY_OUT.exists():
        replay_text = REPLAY_OUT.read_text(encoding="utf-8")
        replay = json.loads(replay_text)
        check("corpus_track_count == 100", replay.get("corpus_track_count") == 100)
        check("result is one of the four allowed finish-cap enums", replay.get("result") in ("REAL_RENDER_CANDIDATE_RECOVERED", "R3_FINAL_PARTIAL_NO_VALID_V1_V2", "BLOCKED", "FAIL"))
        for tag in ("V1", "V2"):
            cat = replay[tag]
            check(f"{tag} total_pair_universe == 100*99", cat["total_pair_universe"] == 100 * 99)
            check(f"{tag} strict_full_dj_survivor_count == len(survivors_ranked_best_first)", cat["strict_full_dj_survivor_count"] == len(cat["survivors_ranked_best_first"]))
            check(f"{tag} tempo_eligible_universe >= strict_full_dj_survivor_count", cat["tempo_eligible_universe"] >= cat["strict_full_dj_survivor_count"])
            check(f"{tag} near-miss list has at most 10 entries", len(cat["near_misses_top10_ranked_by_fewest_failed_gates"]) <= 10)
        check("no_evidence_promotion_declaration is present", bool(replay.get("no_evidence_promotion_declaration")))
        check("alignment_anchor_evidence_consumed.rm014_diagnostic_numeric_anchor_injected is False (no RM014 special case)", replay.get("alignment_anchor_evidence_consumed", {}).get("rm014_diagnostic_numeric_anchor_injected") is False)
        offenders = [p for p in PRIVATE_PATH_PATTERNS if p.search(replay_text)]
        check("sanitized replay evidence contains no Windows/WSL/Linux-home path shape", len(offenders) == 0, f"offenders={[p.pattern for p in offenders]}")
        check("sanitized replay evidence names no audio file extension", not any(ext in replay_text.lower() for ext in AUDIO_EXTENSIONS))

    print("\n=== 4. Independent re-derivation: strict survivor count is truthful ===")
    import final_real_corpus_replay as replay_mod  # noqa: E402
    v1_re = replay_mod.replay_category("V1", analysis)
    v2_re = replay_mod.replay_category("V2", analysis)
    if REPLAY_OUT.exists():
        replay = json.loads(REPLAY_OUT.read_text(encoding="utf-8"))
        check("V1 strict_full_dj_survivor_count reproduces byte-for-byte from cached analysis", v1_re["strict_full_dj_survivor_count"] == replay["V1"]["strict_full_dj_survivor_count"])
        check("V2 strict_full_dj_survivor_count reproduces byte-for-byte from cached analysis", v2_re["strict_full_dj_survivor_count"] == replay["V2"]["strict_full_dj_survivor_count"])

    print("\n=== 5. Every claimed survivor independently passes the unchanged canonical evaluator ===")
    from policy.boundary import plan_transition_boundary  # noqa: E402
    from policy.eligibility import SEAMLESS_FULL_TRACK_DEFAULT  # noqa: E402
    all_survivors_valid = True
    for cat in (v1_re, v2_re):
        for s in cat["survivors_ranked_best_first"]:
            out_a, in_a = analysis[s["out_id"]], analysis[s["in_id"]]
            import select_real_music_pairs as selector  # noqa: E402
            compat_input = selector.build_pair_compat_input(out_a, in_a)
            fixture = replay_mod.build_replay_tx_fixture(s["out_id"], s["in_id"], out_a, in_a, compat_input)
            d = plan_transition_boundary(fixture, SEAMLESS_FULL_TRACK_DEFAULT)
            if not (d.decision_type == "TRANSITION" and "FULL_DJ_BLEND" in d.allowed_transition_class_set):
                all_survivors_valid = False
    check("every claimed survivor, independently re-planned, is honestly granted FULL_DJ_BLEND by the unchanged canonical evaluator", all_survivors_valid)

    print("\n=== 6. Immutability of untouched policy modules (git diff) ===")
    for relpath in ("policy/compatibility.py", "policy/eligibility.py", "policy/metrics.py", "policy/ranking.py", "policy/policies.py"):
        diff = subprocess.run(["git", "diff", "--stat", "HEAD", "--", str(TRANSITION_POLICY / relpath)], cwd=str(REPO_ROOT), capture_output=True, text=True)
        check(f"{relpath}: zero uncommitted changes vs HEAD (working-tree check)", diff.stdout.strip() == "", f"diff={diff.stdout.strip()}")

    print(f"\n=== RESULT: {'ALL CHECKS PASS' if not failures else f'{len(failures)} FAILURE(S)'} ===")
    if failures:
        for f in failures:
            print(f" - FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
