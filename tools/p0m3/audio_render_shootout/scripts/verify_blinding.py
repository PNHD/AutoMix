"""
Machine-verifiable blinding integrity checks (Issue #7 "BLINDING
VERIFICATION" + PM STAGE A REVIEW R5 repair). Exits non-zero and prints
every failing assertion if any check fails.

Checks:
  1. Owner ZIP contains no blind key.
  2. No method names appear anywhere in the owner ZIP (filenames + text
     file contents -- WAVs are binary-scanned too, defense in depth).
  3. No method names appear in WAV "metadata" -- verified structurally: our
     WAV writer (dsp/wav_io.write_wav_pcm16) emits ONLY RIFF/fmt /data
     chunks, so there is no LIST/INFO/ID3 metadata chunk for a name to hide
     in; this is asserted directly against each clip's chunk list.
  4. Every listening WAV's SHA-256 appears in the PM's blind_key.json.
  5. The blind mapping reproduces byte-for-byte from the seed supplied via
     AUTOMIX_R3_BLIND_SEED (never a hardcoded default -- R5 repair).
  6. OWNER_RATINGS_TEMPLATE.json (inside the owner ZIP) refers only to
     opaque S#-X clip IDs -- never an internal method name or transition id.
  7. (R5) results/blind_key.json is NOT tracked by git.
  8. (R5) The seed in use is NOT the old, previously-committed seed
     (20260812) -- proof this is a genuinely new mapping, not a reused one.
  9. (R5) Owner WAV format parity: identical sample rate, channel count,
     bit depth/container policy, and clip duration within tolerance across
     every clip -- no method-correlated file-format signal an owner could
     use to guess which clip is which technique.

Usage:
    AUTOMIX_R3_BLIND_SEED=<the same seed used to build the pack> python scripts/verify_blinding.py
"""
import hashlib
import json
import os
import random
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

from scripts.build_listening_pack import SCENARIO_PLAN, BLIND_SEED_ENV_VAR, require_blind_seed  # noqa: E402

OWNER_ZIP = REPO_ROOT / "P0-M3-R3-OWNER-LISTENING.zip"
BLIND_KEY_PATH = ROOT / "results" / "blind_key.json"
OLD_COMMITTED_SEED = 20260812  # the R2-repair-cycle pack's hardcoded seed -- now removed from source; must never reappear

FORBIDDEN_TERMS = [
    "signalsmith", "rubberband", "rubber band", "rubber-band",
    "baseline", "crossfade", "m0", "m1", "m2", "m3",
    "r3-a", "r3-b", "r3-c", "r3-d",
    "full_dj_blend", "short_eq_blend", "simple_crossfade",
]
# Applied to the (small, human-authored) text files. Short 2-3 character
# terms are meaningful there since we wrote every word ourselves.

# Binary WAV scan uses only the LONG, distinctive terms -- 2-3 character
# terms like "m0"/"m3" are statistically near-guaranteed to occur by chance
# in megabytes of raw PCM audio bytes (a 2-byte ASCII sequence has roughly a
# 1/65536 chance per position; millions of positions make a spurious match
# almost certain) and would make this check meaninglessly noisy.
FORBIDDEN_TERMS_BINARY = [t for t in FORBIDDEN_TERMS if len(t) >= 4]

DURATION_TOLERANCE_S = 0.5

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def wav_fmt_info(raw: bytes) -> dict:
    pos = 12
    info = {}
    while pos + 8 <= len(raw):
        cid = raw[pos:pos + 4]
        size = struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            fmt_tag, channels, sample_rate, _byte_rate, _block_align, bits_per_sample = struct.unpack("<HHIIHH", raw[pos + 8:pos + 8 + 16])
            info = {"fmt_tag": fmt_tag, "channels": channels, "sample_rate": sample_rate, "bits_per_sample": bits_per_sample}
        if cid == b"data":
            info["data_size_bytes"] = size
        pos += 8 + size + (size % 2)
    return info


def main():
    blind_seed = require_blind_seed()

    check(blind_seed != OLD_COMMITTED_SEED, f"blind seed ({blind_seed}) is NOT the old previously-committed seed ({OLD_COMMITTED_SEED}) -- genuinely new mapping")

    git_ls = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch",
                              "tools/p0m3/audio_render_shootout/results/blind_key.json"],
                             capture_output=True, text=True)
    check(git_ls.returncode != 0, "results/blind_key.json is NOT tracked by git (git ls-files --error-unmatch fails)")

    zf = zipfile.ZipFile(OWNER_ZIP)
    names = zf.namelist()

    check("blind_key.json" not in names, "owner ZIP contains no blind_key.json")
    check(all("blind_key" not in n.lower() for n in names), "owner ZIP contains no file with 'blind_key' in its name")

    text_files = [n for n in names if n.endswith(".md") or n.endswith(".json")]
    for name in text_files:
        content = zf.read(name).decode("utf-8", errors="replace").lower()
        for term in FORBIDDEN_TERMS:
            check(term not in content, f"'{term}' not present in {name}")

    fmt_infos = {}
    durations = {}
    for name in names:
        if name.endswith(".wav"):
            lower_name = name.lower()
            for term in FORBIDDEN_TERMS:
                check(term not in lower_name, f"'{term}' not present in WAV filename {name}")
            raw = zf.read(name)
            # Structural chunk check: only RIFF/WAVE with fmt + data chunks,
            # no LIST/INFO/id3 metadata chunk present at all.
            chunk_ids = []
            pos = 12
            while pos + 8 <= len(raw):
                cid = raw[pos:pos + 4]
                size = struct.unpack("<I", raw[pos + 4:pos + 8])[0]
                chunk_ids.append(cid)
                pos += 8 + size + (size % 2)
            check(set(chunk_ids) <= {b"fmt ", b"data"}, f"{name} has ONLY fmt /data chunks (no LIST/INFO/id3 metadata chunk): found {chunk_ids}")
            # Binary defense-in-depth scan for forbidden ASCII substrings
            # (long/distinctive terms only -- see FORBIDDEN_TERMS_BINARY).
            raw_lower = raw.lower()
            for term in FORBIDDEN_TERMS_BINARY:
                check(term.encode() not in raw_lower, f"'{term}' not present as raw bytes in {name}")

            info = wav_fmt_info(raw)
            fmt_infos[name] = info
            bytes_per_frame = info["channels"] * (info["bits_per_sample"] // 8)
            durations[name] = info["data_size_bytes"] / bytes_per_frame / info["sample_rate"]

    # R5 format-parity: no method-correlated file-format signal.
    if fmt_infos:
        sample_rates = {v["sample_rate"] for v in fmt_infos.values()}
        channels = {v["channels"] for v in fmt_infos.values()}
        bit_depths = {v["bits_per_sample"] for v in fmt_infos.values()}
        fmt_tags = {v["fmt_tag"] for v in fmt_infos.values()}
        check(len(sample_rates) == 1, f"all owner WAVs share one sample rate: {sample_rates}")
        check(len(channels) == 1, f"all owner WAVs share one channel count: {channels}")
        check(len(bit_depths) == 1, f"all owner WAVs share one bit depth: {bit_depths}")
        check(len(fmt_tags) == 1, f"all owner WAVs share one container/format tag (PCM vs float, etc): {fmt_tags}")
        dur_values = list(durations.values())
        dur_spread = max(dur_values) - min(dur_values)
        check(dur_spread <= DURATION_TOLERANCE_S, f"all owner WAV durations within {DURATION_TOLERANCE_S}s of each other (spread={dur_spread:.3f}s): {durations}")

    blind_key = json.loads(BLIND_KEY_PATH.read_text(encoding="utf-8"))
    check(blind_key.get("seed") == blind_seed, f"blind_key.json's recorded seed matches the seed supplied via {BLIND_SEED_ENV_VAR}")
    manifest_hashes = {entry["clip_name"]: entry["sha256"] for entry in blind_key["clip_manifest"]}
    for name in names:
        if name.endswith(".wav"):
            actual_sha = hashlib.sha256(zf.read(name)).hexdigest()
            check(name in manifest_hashes, f"{name} is present in PM blind_key.json's clip_manifest")
            if name in manifest_hashes:
                check(actual_sha == manifest_hashes[name], f"{name} SHA-256 in owner ZIP matches PM blind_key.json ({actual_sha[:12]}...)")

    # Reproduce the seeded shuffle independently and compare.
    for scenario_label, transition_id, methods in SCENARIO_PLAN:
        rng = random.Random(f"{blind_seed}:{transition_id}")
        letters = list("ABCDEFGH")[: len(methods)]
        shuffled = methods[:]
        rng.shuffle(shuffled)
        expected = dict(zip(letters, shuffled))
        actual = blind_key["scenarios"][scenario_label]["letter_to_method"]
        check(expected == actual, f"{scenario_label} blind mapping reproduces exactly from the supplied seed")

    ratings = json.loads(zf.read("OWNER_RATINGS_TEMPLATE.json").decode("utf-8"))
    clip_ids = set(ratings["clips"].keys())
    expected_ids = {n.replace(".wav", "") for n in names if n.endswith(".wav")}
    check(clip_ids == expected_ids, "OWNER_RATINGS_TEMPLATE.json keys are exactly the opaque clip IDs (nothing more, nothing less)")
    for cid in clip_ids:
        check(cid.split("-")[0].startswith("S") and cid.split("-")[0][1:].isdigit(), f"{cid} uses only the opaque S#-X naming scheme")

    print(f"\n{'ALL CHECKS PASS' if not failures else f'{len(failures)} CHECK(S) FAILED'}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
