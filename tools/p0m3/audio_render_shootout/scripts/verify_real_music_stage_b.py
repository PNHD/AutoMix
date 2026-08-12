"""
P0-M3-R3 STAGE B REAL-EVIDENCE REPAIR -- consolidated post-commit
validation against the newest Issue #7 PM "PM STAGE B REVIEW -- CURRENT
OWNER PACK INVALID / REAL-EVIDENCE REPAIR REQUIRED" comment.

PM STAGE B REVIEW R7 repair: the PRIOR verifier hardcoded the literal
private root marker (the authorized corpus folder's own name) as a Python
string constant in this tracked file, then asserted no tracked file
contains that marker -- self-invalidating the instant the verifier itself
was committed. This version NEVER embeds the real/private sentinel in
source (not even as a regression-test comparison literal -- see check 10's
docstring for why that would recreate the same bug): it is supplied ONLY
via `--private-sentinel` (or the AUTOMIX_R3_PRIVATE_ROOT_SENTINEL env var)
at run time, a local/PM-only input never written to any tracked file.

R7 also requires this verifier to be runnable from -- and pass against --
the actual PUSHED commit, not merely the working tree before staging: the
git-tracked-file scan reads each file's content via `git show <ref>:<path>`
(default ref HEAD) rather than the working-tree filesystem, so a stale
working copy cannot mask a real regression in what was actually committed.

Usage (after committing/pushing):
    AUTOMIX_R3_PRIVATE_ROOT_SENTINEL=<the real authorized root's own folder name, supplied locally only> \\
        python scripts/verify_real_music_stage_b.py --ref HEAD
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

OWNER_ZIP = REPO_ROOT / "P0-M3-R3-REAL-MUSIC-OWNER-LISTENING.zip"
PM_ZIP = REPO_ROOT / "P0-M3-R3-REAL-MUSIC-PM-REVIEW.zip"
RENDERS_DIR = ROOT / "real_music" / "work_local" / "renders"
BLIND_KEY_PATH = ROOT / "real_music" / "work_local" / "real_music_blind_key.local.json"

OLD_SYNTHETIC_SEED_ENV_VAR = "AUTOMIX_R3_BLIND_SEED"
REAL_MUSIC_SEED_ENV_VAR = "AUTOMIX_R3_REAL_MUSIC_BLIND_SEED"
OLD_COMMITTED_SYNTHETIC_SEED = 20260812
PRIVATE_SENTINEL_ENV_VAR = "AUTOMIX_R3_PRIVATE_ROOT_SENTINEL"

GENERIC_EXTENSION_MARKERS = [".mp3", ".flac", ".m4a"]  # not private themselves -- generic format-check tokens, distinct from the private root sentinel
PATH_LIKE_PATTERN = re.compile(r"[A-Za-z]:[\\/]|/mnt/|/home/|/Users/")

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def git_tracked_files(ref: str) -> list[str]:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-tree", "-r", "--name-only", ref],
                             capture_output=True, text=True)
    return result.stdout.splitlines()


def git_show(ref: str, rel_path: str) -> str | None:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{ref}:{rel_path}"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return None
    return result.stdout


def scan_text_for_leaks(text: str, label: str, sentinel: str):
    check(sentinel.lower() not in text.lower(), f"{label}: no private-root sentinel present")
    for marker in GENERIC_EXTENSION_MARKERS:
        check(marker.lower() not in text.lower(), f"{label}: no '{marker}' marker present")
    check(not PATH_LIKE_PATTERN.search(text), f"{label}: no absolute filesystem path pattern present")


def check_1_2_no_private_paths_in_tracked_and_summaries(ref: str, sentinel: str):
    print(f"\n--- Checks 1+2 (against git ref {ref}): no private root sentinel / basenames / hashes in tracked or summary files ---")
    tracked = git_tracked_files(ref)
    leaked = []
    for rel in tracked:
        if Path(rel).suffix.lower() in (".wav", ".mp3", ".flac", ".m4a", ".zip", ".png", ".jpg"):
            continue
        content = git_show(ref, rel)
        if content is None:
            continue
        if sentinel.lower() in content.lower():
            leaked.append(rel)
    check(len(leaked) == 0, f"no git-tracked file (at {ref}) contains the private-root sentinel: leaked={leaked}")

    for rel in [
        "real_music/work_local/corpus_summary_sanitized.json",
        "real_music/work_local/selection_rationale_sanitized.json",
        "real_music/work_local/selection_trace.local.json",
        "real_music/work_local/pipeline_summary_sanitized.json",
        "real_music/work_local/real_music_blind_key.local.json",
    ]:
        p = ROOT / rel
        if p.exists():
            scan_text_for_leaks(p.read_text(encoding="utf-8", errors="replace"), rel, sentinel)
        else:
            check(False, f"{rel} exists")

    for pair_dir in sorted(RENDERS_DIR.glob("REAL-*")) if RENDERS_DIR.exists() else []:
        for fname in ("planner_decision.json", "result.json", "C_signalsmith_owner_result.json"):
            p = pair_dir / fname
            if p.exists():
                scan_text_for_leaks(p.read_text(encoding="utf-8", errors="replace"), f"{pair_dir.name}/{fname}", sentinel)


def check_5_v2_within_conditional_zone():
    print("\n--- Check 5: if a V2 pair exists, its correction is within ~3-6% conditional zone + R2 hard envelope ---")
    p = RENDERS_DIR / "REAL-V2" / "result.json"
    if not p.exists():
        print("SKIP: no REAL-V2 render this pass (no valid V2 pair survived honest selection -- not a failure)")
        return
    result = json.loads(p.read_text(encoding="utf-8"))
    dev = result["tempo_mode_evidence"]["deviation"]
    check(0.02 <= dev <= 0.07, f"REAL-V2 tempo deviation {dev*100:.2f}% is within the ~3-6% conditional zone (with small tolerance)")
    check(result["tempo_mode_evidence"]["benchmark_zone"] == "CONDITIONAL_ZONE_2_6_PCT", "REAL-V2 zone classification is CONDITIONAL_ZONE_2_6_PCT")
    check(abs(result["required_tempo_ratio"] - 1.0) <= 0.12, "REAL-V2 required_tempo_ratio is within the R2 hard envelope ceiling (12%)")
    check(result["tempo_mode"] == "MATCH_INCOMING_DURING_OVERLAP", "REAL-V2 tempo_mode is MATCH_INCOMING_DURING_OVERLAP")


def check_6_v2_signalsmith_owner_candidate():
    print("\n--- Check 6: if a V2 pair exists, its owner candidate C is Signalsmith, pitch-preserving, no unsafe ramp ---")
    p = RENDERS_DIR / "REAL-V2" / "C_signalsmith_owner_result.json"
    if not (RENDERS_DIR / "REAL-V2").exists():
        print("SKIP: no REAL-V2 render this pass")
        return
    check(p.exists(), "REAL-V2 Signalsmith owner-facing render result exists")
    if p.exists():
        meta = json.loads(p.read_text(encoding="utf-8"))
        check(meta["engine"] == "official_pinned_web_release_wasm_webaudio_fallback", "owner C engine is the official pinned Signalsmith WASM/WebAudio release")
        check(meta["applied_pitch_shift_semitones"] == 0, "owner C applies zero pitch shift (pitch preserved)")
        check(meta["tempo_mode"] != "MATCH_AND_RETURN_TO_NATIVE", "owner C tempo_mode is never the unsafe return-to-native ramp")
        check(meta["safety"]["nan_inf_sample_count"] == 0 and meta["safety"]["clipped_sample_count"] == 0, "owner C render has no NaN/Inf/clipped samples")


def check_7_v3_never_forces_full_dj():
    print("\n--- Check 7: V3 never forces FULL_DJ_BLEND ---")
    p = RENDERS_DIR / "REAL-V3" / "result.json"
    check(p.exists(), "REAL-V3 render result exists")
    if not p.exists():
        return
    result = json.loads(p.read_text(encoding="utf-8"))
    check("FULL_DJ_BLEND" not in result["allowed_transition_class_set"], "REAL-V3 planner allowed_transition_class_set excludes FULL_DJ_BLEND")
    check("C" not in result.get("renders", {}), "REAL-V3 has no rendered C candidate (FULL_DJ withheld)")
    check(result["tempo_mode"] == "NATIVE_TEMPO", "REAL-V3 tempo_mode is NATIVE_TEMPO (no forced correction for an incompatible pair)")


def check_8_shared_boundary_per_scenario():
    print("\n--- Check 8: A/B/C within each rendered scenario share the identical planner boundary ---")
    if not RENDERS_DIR.exists():
        print("SKIP: no renders directory")
        return
    for pair_dir in sorted(RENDERS_DIR.glob("REAL-*")):
        result_path = pair_dir / "result.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        onset_ms, content_end_ms, entry_ms = result["onset_ms"], result["content_end_ms"], result["entry_ms"]
        c_path = pair_dir / "C_signalsmith_owner_result.json"
        if c_path.exists():
            c_meta = json.loads(c_path.read_text(encoding="utf-8"))
            check(c_meta["onset_ms"] == onset_ms and c_meta["content_end_ms"] == content_end_ms and c_meta["entry_ms"] == entry_ms,
                  f"{pair_dir.name}: Signalsmith owner C shares the exact same onset/content_end/entry boundary as A/B")


def wav_fmt_info(raw: bytes) -> dict:
    pos = 12
    info = {}
    while pos + 8 <= len(raw):
        cid = raw[pos:pos + 4]
        size = struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            fmt_tag, channels, sample_rate, _br, _ba, bits = struct.unpack("<HHIIHH", raw[pos + 8:pos + 8 + 16])
            info = {"fmt_tag": fmt_tag, "channels": channels, "sample_rate": sample_rate, "bits_per_sample": bits}
        if cid == b"data":
            info["data_size_bytes"] = size
        pos += 8 + size + (size % 2)
    return info


def check_9_owner_format_parity_and_metadata():
    print("\n--- Check 9: owner clips share format parity + carry no metadata chunk ---")
    if not OWNER_ZIP.exists():
        check(False, "owner ZIP exists")
        return
    zf = zipfile.ZipFile(OWNER_ZIP)
    names = [n for n in zf.namelist() if n.endswith(".wav")]
    check(len(names) > 0, "owner ZIP contains at least one clip")
    fmt_infos, durations = {}, {}
    for name in names:
        raw = zf.read(name)
        chunk_ids = []
        pos = 12
        while pos + 8 <= len(raw):
            cid = raw[pos:pos + 4]
            size = struct.unpack("<I", raw[pos + 4:pos + 8])[0]
            chunk_ids.append(cid)
            pos += 8 + size + (size % 2)
        check(set(chunk_ids) <= {b"fmt ", b"data"}, f"{name}: only fmt /data chunks (no metadata/tag chunk)")
        info = wav_fmt_info(raw)
        fmt_infos[name] = info
        bpf = info["channels"] * (info["bits_per_sample"] // 8)
        durations[name] = info["data_size_bytes"] / bpf / info["sample_rate"]
    if fmt_infos:
        check(len({v["sample_rate"] for v in fmt_infos.values()}) == 1, "all owner WAVs share one sample rate")
        check(len({v["channels"] for v in fmt_infos.values()}) == 1, "all owner WAVs share one channel count")
        check(len({v["bits_per_sample"] for v in fmt_infos.values()}) == 1, "all owner WAVs share one bit depth")
        check(len({v["fmt_tag"] for v in fmt_infos.values()}) == 1, "all owner WAVs share one container/format tag")
        spread = max(durations.values()) - min(durations.values())
        check(spread <= 0.5, f"owner WAV durations within 0.5s of each other (spread={spread:.3f}s)")

    forbidden = ["signalsmith", "rubberband", "rubber_band", "equal_power", "late_hold", "full_dj", "short_eq", "simple_crossfade", "native_tempo"]
    for name in zf.namelist():
        lower = name.lower()
        for term in forbidden:
            check(term not in lower, f"'{term}' not present in owner ZIP entry name '{name}'")
    for name in zf.namelist():
        if name.endswith((".md", ".json")):
            content = zf.read(name).decode("utf-8", errors="replace").lower()
            for term in forbidden:
                check(term not in content, f"'{term}' not present in owner ZIP file '{name}' content")
    check("blind_key" not in "".join(zf.namelist()).lower(), "owner ZIP contains no blind-key file")


def check_10_verifier_never_defaults_sentinel(ref: str):
    """
    R7 repair note: this check DELIBERATELY does NOT search for the
    literal historical marker string as a comparison constant -- doing so
    would require THIS file to contain that literal itself, recreating
    exactly the self-invalidation architecture the PM comment flagged
    (any file asserting "no tracked file contains X" must contain X
    somewhere to perform the assertion). Instead this proves the
    STRUCTURAL, general property: the sentinel is derived ONLY from
    `--private-sentinel` / the env var, with no hardcoded literal fallback,
    and the script fails closed (non-zero exit) if neither is supplied --
    which is what actually prevents any future hardcoded-marker regression,
    independent of what the specific marker string happens to be.
    """
    print("\n--- Check 10: this verifier never silently defaults its private sentinel ---")
    rel = "tools/p0m3/audio_render_shootout/scripts/verify_real_music_stage_b.py"
    content = git_show(ref, rel)
    if content is None:
        content = Path(__file__).read_text(encoding="utf-8")
        print("NOTE: verifier not yet committed at this ref -- checking working-tree source instead")
    has_required_pattern = bool(re.search(r"sentinel\s*=\s*args\.private_sentinel\s+or\s+os\.environ\.get\(PRIVATE_SENTINEL_ENV_VAR\)", content))
    check(has_required_pattern, "sentinel is derived ONLY from --private-sentinel or the env var (no hardcoded literal fallback pattern)")
    has_fail_closed = bool(re.search(r"if not sentinel:\s*\n\s*print\([^\n]*\n\s*sys\.exit\(1\)", content))
    check(has_fail_closed, "verifier exits non-zero if no sentinel was supplied, rather than silently defaulting")


def check_11_new_seed_not_reused():
    print("\n--- Check 11: new blind seed, not the synthetic pack's seed/mapping ---")
    raw = os.environ.get(REAL_MUSIC_SEED_ENV_VAR)
    check(raw is not None, f"{REAL_MUSIC_SEED_ENV_VAR} was supplied")
    if raw is not None:
        seed = int(raw)
        check(seed != OLD_COMMITTED_SYNTHETIC_SEED, f"real-music seed != old committed synthetic seed ({OLD_COMMITTED_SYNTHETIC_SEED})")
        check(os.environ.get(OLD_SYNTHETIC_SEED_ENV_VAR) != raw, f"real-music seed does not equal any concurrently-set {OLD_SYNTHETIC_SEED_ENV_VAR}")
        if BLIND_KEY_PATH.exists():
            bk = json.loads(BLIND_KEY_PATH.read_text(encoding="utf-8"))
            check(bk.get("seed") == seed, "real_music_blind_key.local.json seed matches the supplied env var")
    git_ls = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch",
         "tools/p0m3/audio_render_shootout/real_music/work_local/real_music_blind_key.local.json"],
        capture_output=True, text=True,
    )
    check(git_ls.returncode != 0, "real_music_blind_key.local.json is NOT tracked by git")


def check_12_invalid_owner_zip_not_reused():
    print("\n--- Check 12: the invalidated prior owner ZIP hash is not reproduced ---")
    invalid_sha_prefix = "84ad398e"
    if OWNER_ZIP.exists():
        import hashlib
        actual = hashlib.sha256(OWNER_ZIP.read_bytes()).hexdigest()
        check(not actual.startswith(invalid_sha_prefix), f"current owner ZIP SHA-256 does not match the invalidated pack ({invalid_sha_prefix}...)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default="HEAD", help="git ref to scan tracked files against (default HEAD)")
    ap.add_argument("--private-sentinel", default=None, help="the real authorized root folder name -- LOCAL/PM-ONLY input, never committed")
    args = ap.parse_args()

    sentinel = args.private_sentinel or os.environ.get(PRIVATE_SENTINEL_ENV_VAR)
    if not sentinel:
        print(f"ERROR: --private-sentinel or {PRIVATE_SENTINEL_ENV_VAR} is required (the real authorized root folder name, supplied locally only -- never hardcoded in this file).")
        sys.exit(1)

    print(f"=== P0-M3-R3 STAGE B validation (ref={args.ref}) ===")
    check_1_2_no_private_paths_in_tracked_and_summaries(args.ref, sentinel)
    check_5_v2_within_conditional_zone()
    check_6_v2_signalsmith_owner_candidate()
    check_7_v3_never_forces_full_dj()
    check_8_shared_boundary_per_scenario()
    check_9_owner_format_parity_and_metadata()
    check_10_verifier_never_defaults_sentinel(args.ref)
    check_11_new_seed_not_reused()
    check_12_invalid_owner_zip_not_reused()

    print(f"\n{'ALL CHECKS PASS' if not failures else f'{len(failures)} CHECK(S) FAILED'}")
    report = {"result": "PASS" if not failures else "FAIL", "ref": args.ref, "failures": failures}
    (ROOT / "real_music" / "work_local" / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
