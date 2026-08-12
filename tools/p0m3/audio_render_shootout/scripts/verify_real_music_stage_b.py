"""
P0-M3-R3 STAGE B -- consolidated validation against the newest Issue #7 PM
"PM STAGE B -- OWNER REAL-MUSIC VALIDATION AUTHORIZED" comment's VALIDATION
checklist (items 1,2,5,6,7,8,9,11 checked directly here; 3/4/10/12 verified
by construction/re-run and reported in HANDOFF_TO_PM.md).

Usage:
    AUTOMIX_R3_REAL_MUSIC_BLIND_SEED=<the same seed used to build the pack> python scripts/verify_real_music_stage_b.py
"""
from __future__ import annotations

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

AUTHORIZED_ROOT_MARKERS = ["owner_music_input", ".mp3", ".flac", ".m4a"]
PATH_LIKE_PATTERN = re.compile(r"[A-Za-z]:[\\/]|/mnt/|/home/|/Users/")

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def scan_text_for_leaks(path: Path, label: str):
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in AUTHORIZED_ROOT_MARKERS:
        check(marker.lower() not in text.lower(), f"{label}: no '{marker}' marker present")
    check(not PATH_LIKE_PATTERN.search(text), f"{label}: no absolute filesystem path pattern present")


def check_1_2_no_private_paths_in_tracked_and_summaries():
    print("\n--- Checks 1+2: no private root path / basenames / hashes in tracked or summary files ---")
    git_files = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"], capture_output=True, text=True
    ).stdout.splitlines()
    leaked = []
    for rel in git_files:
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        if p.suffix.lower() in (".wav", ".mp3", ".flac", ".m4a", ".zip", ".png", ".jpg"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "owner_music_input" in text.lower():
            leaked.append(rel)
    check(len(leaked) == 0, f"no git-tracked file contains 'owner_music_input': leaked={leaked}")

    for rel in [
        "real_music/work_local/corpus_summary_sanitized.json",
        "real_music/work_local/selection_rationale_sanitized.json",
        "real_music/work_local/selection_trace.local.json",
        "real_music/work_local/pipeline_summary_sanitized.json",
        "real_music/work_local/real_music_blind_key.local.json",
    ]:
        p = ROOT / rel
        if p.exists():
            scan_text_for_leaks(p, rel)
        else:
            check(False, f"{rel} exists")

    for pair_id in ("REAL-V1", "REAL-V2", "REAL-V3"):
        for fname in ("planner_decision.json", "result.json"):
            p = RENDERS_DIR / pair_id / fname
            if p.exists():
                scan_text_for_leaks(p, f"{pair_id}/{fname}")


def check_5_v2_within_conditional_zone():
    print("\n--- Check 5: V2 correction within ~3-6% conditional zone + R2 hard envelope ---")
    result = json.loads((RENDERS_DIR / "REAL-V2" / "result.json").read_text(encoding="utf-8"))
    dev = result["tempo_mode_evidence"]["deviation"]
    check(0.02 <= dev <= 0.07, f"REAL-V2 tempo deviation {dev*100:.2f}% is within the ~3-6% conditional zone (with small tolerance)")
    check(result["tempo_mode_evidence"]["benchmark_zone"] == "CONDITIONAL_ZONE_2_6_PCT", "REAL-V2 zone classification is CONDITIONAL_ZONE_2_6_PCT")
    check(abs(result["required_tempo_ratio"] - 1.0) <= 0.12, "REAL-V2 required_tempo_ratio is within the R2 hard envelope ceiling (12%)")
    check(result["tempo_mode"] == "MATCH_INCOMING_DURING_OVERLAP", "REAL-V2 tempo_mode is MATCH_INCOMING_DURING_OVERLAP")


def check_6_v2_signalsmith_owner_candidate():
    print("\n--- Check 6: V2 owner candidate C is Signalsmith, pitch-preserving, no unsafe ramp ---")
    p = RENDERS_DIR / "REAL-V2" / "C_signalsmith_owner_result.json"
    check(p.exists(), "REAL-V2 Signalsmith owner-facing render result exists")
    if p.exists():
        meta = json.loads(p.read_text(encoding="utf-8"))
        check(meta["engine"] == "official_pinned_web_release_wasm_webaudio_fallback", "owner C engine is the official pinned Signalsmith WASM/WebAudio release")
        check(meta["applied_pitch_shift_semitones"] == 0, "owner C applies zero pitch shift (pitch preserved)")
        check(meta["tempo_mode"] != "MATCH_AND_RETURN_TO_NATIVE", "owner C tempo_mode is never the unsafe return-to-native ramp")
        check(meta["sample_rate_resample_applied"] in (False,) or meta["canonical_sample_rate"] == meta["browser_output_sample_rate_from_file"], "owner C sample rate parity holds (native match or explicit normalization)")
        check(meta["safety"]["nan_inf_sample_count"] == 0 and meta["safety"]["clipped_sample_count"] == 0, "owner C render has no NaN/Inf/clipped samples")
    ref_c = RENDERS_DIR / "REAL-V2" / "C_conditional_tempo_candidate.wav"
    check(ref_c.exists(), "PM/reference-only ffmpeg-Rubber-Band C also exists (kept separate, never the owner-facing file)")


def check_7_v3_never_forces_full_dj():
    print("\n--- Check 7: V3 never forces FULL_DJ_BLEND ---")
    result = json.loads((RENDERS_DIR / "REAL-V3" / "result.json").read_text(encoding="utf-8"))
    check("FULL_DJ_BLEND" not in result["allowed_transition_class_set"], "REAL-V3 planner allowed_transition_class_set excludes FULL_DJ_BLEND")
    check("C" not in result.get("renders", {}), "REAL-V3 has no rendered C candidate (FULL_DJ withheld -> no tempo-match candidate rendered)")
    check(result["tempo_mode"] == "NATIVE_TEMPO", "REAL-V3 tempo_mode is NATIVE_TEMPO (no forced correction for an incompatible pair)")


def check_8_shared_boundary_per_scenario():
    print("\n--- Check 8: A/B/C within each scenario share the identical planner boundary ---")
    for pair_id in ("REAL-V1", "REAL-V2", "REAL-V3"):
        result = json.loads((RENDERS_DIR / pair_id / "result.json").read_text(encoding="utf-8"))
        onset_ms, content_end_ms, entry_ms = result["onset_ms"], result["content_end_ms"], result["entry_ms"]
        c_path = RENDERS_DIR / pair_id / "C_signalsmith_owner_result.json"
        if c_path.exists():
            c_meta = json.loads(c_path.read_text(encoding="utf-8"))
            check(c_meta["onset_ms"] == onset_ms and c_meta["content_end_ms"] == content_end_ms and c_meta["entry_ms"] == entry_ms,
                  f"{pair_id}: Signalsmith owner C shares the exact same onset/content_end/entry boundary as A/B")


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
    fmt_infos = {}
    durations = {}
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

    # No internal method-identity terms in filenames/text (song identity is allowed).
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


def main():
    print("=== P0-M3-R3 STAGE B validation ===")
    check_1_2_no_private_paths_in_tracked_and_summaries()
    check_5_v2_within_conditional_zone()
    check_6_v2_signalsmith_owner_candidate()
    check_7_v3_never_forces_full_dj()
    check_8_shared_boundary_per_scenario()
    check_9_owner_format_parity_and_metadata()
    check_11_new_seed_not_reused()

    print(f"\n{'ALL CHECKS PASS' if not failures else f'{len(failures)} CHECK(S) FAILED'}")
    report = {"result": "PASS" if not failures else "FAIL", "failures": failures}
    (ROOT / "real_music" / "work_local" / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
