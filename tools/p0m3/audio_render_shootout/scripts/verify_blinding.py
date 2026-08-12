"""
Machine-verifiable blinding integrity checks (Issue #7 "BLINDING
VERIFICATION"). Exits non-zero and prints every failing assertion if any
check fails.

Checks:
  1. Owner ZIP contains no blind key.
  2. No method names appear anywhere in the owner ZIP (filenames + text
     file contents -- WAVs are binary-scanned too, defense in depth).
  3. No method names appear in WAV "metadata" -- verified structurally: our
     WAV writer (dsp/wav_io.write_wav_pcm16) emits ONLY RIFF/fmt /data
     chunks, so there is no LIST/INFO/ID3 metadata chunk for a name to hide
     in; this is asserted directly against each clip's chunk list.
  4. Every listening WAV's SHA-256 appears in the PM's blind_key.json.
  5. The blind mapping reproduces byte-for-byte from the fixed seed
     (re-running scripts/build_listening_pack.py's shuffle logic).
  6. OWNER_RATINGS_TEMPLATE.json (inside the owner ZIP) refers only to
     opaque S#-X clip IDs -- never an internal method name or transition id.

Usage:
    python scripts/verify_blinding.py
"""
import hashlib
import json
import random
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(ROOT))

from scripts.build_listening_pack import SCENARIO_PLAN, BLIND_SEED  # noqa: E402

OWNER_ZIP = REPO_ROOT / "P0-M3-R3-OWNER-LISTENING.zip"
BLIND_KEY_PATH = ROOT / "results" / "blind_key.json"

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

failures = []


def check(condition: bool, message: str):
    if not condition:
        failures.append(message)
        print(f"FAIL: {message}")
    else:
        print(f"OK:   {message}")


def main():
    zf = zipfile.ZipFile(OWNER_ZIP)
    names = zf.namelist()

    check("blind_key.json" not in names, "owner ZIP contains no blind_key.json")
    check(all("blind_key" not in n.lower() for n in names), "owner ZIP contains no file with 'blind_key' in its name")

    text_files = [n for n in names if n.endswith(".md") or n.endswith(".json")]
    for name in text_files:
        content = zf.read(name).decode("utf-8", errors="replace").lower()
        for term in FORBIDDEN_TERMS:
            check(term not in content, f"'{term}' not present in {name}")

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

    blind_key = json.loads(BLIND_KEY_PATH.read_text(encoding="utf-8"))
    manifest_hashes = {entry["clip_name"]: entry["sha256"] for entry in blind_key["clip_manifest"]}
    for name in names:
        if name.endswith(".wav"):
            actual_sha = hashlib.sha256(zf.read(name)).hexdigest()
            check(name in manifest_hashes, f"{name} is present in PM blind_key.json's clip_manifest")
            if name in manifest_hashes:
                check(actual_sha == manifest_hashes[name], f"{name} SHA-256 in owner ZIP matches PM blind_key.json ({actual_sha[:12]}...)")

    # Reproduce the seeded shuffle independently and compare.
    for scenario_label, transition_id, methods in SCENARIO_PLAN:
        rng = random.Random(f"{BLIND_SEED}:{transition_id}")
        letters = list("ABCDEFGH")[: len(methods)]
        shuffled = methods[:]
        rng.shuffle(shuffled)
        expected = dict(zip(letters, shuffled))
        actual = blind_key["scenarios"][scenario_label]["letter_to_method"]
        check(expected == actual, f"{scenario_label} blind mapping reproduces exactly from seed {BLIND_SEED}")

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
