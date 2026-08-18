"""
P0-M5-R1 Phase C -- deterministic positive-pair discovery.

Scores every eligible ordered pair from the existing authorized owner
corpus using ONLY already-cached evidence:

  - `corpus_analysis.local.json` (the same Stage-B evidence P0-M4-R2 used:
    exit/entry candidates, structure confidence, harmonic/key/loudness/
    texture measurements) -- reused verbatim, no new analyzer;
  - `beat_analysis_aggregate_sanitized.json` + the local per-track beat
    cache produced by `corpus_beat_analysis.py` (Phase B, this task's one
    authorized new analyzer pass).

Unlike P0-M4-R1's hash-only hold-out selection (anti-cherry-picking for a
narrow falsifiable validation), Issue #10 explicitly authorizes this stage
to SEEK positive complex-transition opportunities -- the product itself
only uses complex mixing on suitable pairs, so finding which pairs are
suitable is legitimate discovery, not cherry-picking after listening. No
manual song selection and no listening-outcome feedback are used anywhere
in this module.

Hard eligibility (Issue #10 Phase C):
  - two distinct tracks;
  - outgoing exit candidate has cached structure_confidence MEDIUM/HIGH
    (the accepted R2 late/natural-region evidence);
  - both tracks have a successful Beat This pass with a downbeat near the
    selected outgoing exit region and near the incoming entry region;
  - direct tempo relation only: |incoming_local_bpm/outgoing_local_bpm -
    1| <= 0.06 (no half/double-time folding in this first slice);
  - no source-analysis failure on either side.

Boundary policy: outgoing exit snaps to the nearest Beat This downbeat at
or after the cached exit_candidate_t_ms; incoming entry is the first Beat
This downbeat at or after the cached leading-silence-skip point (0 if none
is authored) -- SongFormer intro/outro evidence is unavailable this pass
(SONGFORMER_BLOCKED_ASSET_TERMS, see beat_this_runtime module docstring /
the Phase A report section) so this task falls through to the "otherwise"
branch Issue #10 itself authorizes.

Soft ranking (in this exact order, all from already-cached evidence):
  1. structure quality (exit_structure_confidence HIGH > MEDIUM);
  2. smaller tempo correction magnitude;
  3. cached harmonic compatibility if confidently known (UNKNOWN is
     neutral, never fatal);
  4. cached energy/loudness continuity (`_combined_energy_gap_db`,
     smaller is better);
  5. deterministic SHA-256 tie-break on the opaque pair ID.

Usage:
    python tools/p0m5/apple_like_vertical_slice/pair_discovery.py \
        --manifest-out tools/p0m5/apple_like_vertical_slice/pair_manifest_sanitized.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SCRIPTS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "scripts"
CORPUS_DIR = REPO_ROOT / "tools" / "p0m3" / "audio_render_shootout" / "real_music" / "work_local" / "corpus"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HERE))

import select_real_music_pairs as srmp  # noqa: E402

MAX_TEMPO_CORRECTION = 0.06  # Issue #10 Phase C hard eligibility
MAX_APPEARANCES = 2
REQUIRED_PAIR_COUNT = 8
HOLDOUT_COUNT = 2
DOWNBEAT_SEARCH_WINDOW_S = 45.0  # how far from the cached exit candidate a downbeat may be snapped
HOLDOUT_SALT = "P0-M5-R1-APPLE-LIKE-V1"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_downbeat_at_or_after(downbeats_s: list, t_s: float, search_window_s: float = DOWNBEAT_SEARCH_WINDOW_S):
    candidates = [d for d in downbeats_s if t_s <= d <= t_s + search_window_s]
    if candidates:
        return min(candidates)
    # fall back to nearest downbeat within the window on either side
    nearby = [d for d in downbeats_s if abs(d - t_s) <= search_window_s]
    if nearby:
        return min(nearby, key=lambda d: abs(d - t_s))
    return None


def outgoing_exit_anchor_s(out_id: str, analysis: dict, beat_cache_dir: Path):
    """Returns (snapped_downbeat_s, raw_r2_candidate_s, reason). The raw
    (un-snapped) R2 candidate is kept separately so M0 (Issue #10: "no
    beat/downbeat alignment") can genuinely differ from M1's beat-snapped
    placement, rather than M0 silently inheriting M1's beat-aware anchor."""
    a = analysis[out_id]
    confidence = a["candidates"]["exit_structure_confidence"]
    if confidence not in ("MEDIUM", "HIGH"):
        return None, None, "EXIT_STRUCTURE_CONFIDENCE_BELOW_MEDIUM"
    exit_t_s = a["candidates"]["exit_candidate_t_ms"] / 1000.0
    beat_data = load_json(beat_cache_dir / f"{out_id}.json")
    if beat_data["summary"]["status"] != "SUCCESS":
        return None, None, "BEAT_THIS_ANALYSIS_FAILED"
    downbeat = nearest_downbeat_at_or_after(beat_data["downbeats_s"], exit_t_s)
    if downbeat is None:
        return None, None, "NO_USABLE_DOWNBEAT_NEAR_EXIT_CANDIDATE"
    return downbeat, exit_t_s, "OK"


def incoming_entry_anchor_s(in_id: str, analysis: dict, beat_cache_dir: Path):
    """Returns (snapped_downbeat_s, raw_skip_point_s, reason)."""
    a = analysis[in_id]
    beat_data = load_json(beat_cache_dir / f"{in_id}.json")
    if beat_data["summary"]["status"] != "SUCCESS":
        return None, None, "BEAT_THIS_ANALYSIS_FAILED"
    skip_point_s = 0.0
    if a["candidates"].get("entry_is_authored_silence_skip"):
        skip_point_s = a["candidates"]["entry_candidate_t_ms"] / 1000.0
    downbeats = beat_data["downbeats_s"]
    after = [d for d in downbeats if d >= skip_point_s]
    if not after:
        return None, None, "NO_USABLE_DOWNBEAT_NEAR_ENTRY_CANDIDATE"
    return min(after), skip_point_s, "OK"


def local_bpm_near(times_s: list, anchor_s: float, n_bars: int = 4) -> float | None:
    """Median bar-period-derived BPM from the `n_bars` downbeat intervals
    nearest the anchor (both sides), converted to a beats-per-minute-style
    scalar consistent across outgoing/incoming for a direct ratio -- since
    only the RATIO matters here (not absolute meter), using bar rate on
    both sides cancels consistently."""
    nearby = sorted(times_s, key=lambda t: abs(t - anchor_s))[: n_bars + 1]
    nearby = sorted(nearby)
    intervals = [b - a for a, b in zip(nearby, nearby[1:]) if b > a]
    if not intervals:
        return None
    intervals.sort()
    mid = intervals[len(intervals) // 2]
    return 60.0 / mid if mid > 0 else None


def build_pair_id(out_id: str, in_id: str) -> str:
    return hashlib.sha256(f"{out_id}|{in_id}".encode("utf-8")).hexdigest()


def evaluate_pair(out_id: str, in_id: str, analysis: dict, beat_cache_dir: Path) -> dict:
    exit_anchor_s, exit_raw_s, exit_reason = outgoing_exit_anchor_s(out_id, analysis, beat_cache_dir)
    if exit_anchor_s is None:
        return {"eligible": False, "reason": exit_reason}
    entry_anchor_s, entry_raw_s, entry_reason = incoming_entry_anchor_s(in_id, analysis, beat_cache_dir)
    if entry_anchor_s is None:
        return {"eligible": False, "reason": entry_reason}

    out_beats = load_json(beat_cache_dir / f"{out_id}.json")["downbeats_s"]
    in_beats = load_json(beat_cache_dir / f"{in_id}.json")["downbeats_s"]
    out_bpm = local_bpm_near(out_beats, exit_anchor_s)
    in_bpm = local_bpm_near(in_beats, entry_anchor_s)
    if not out_bpm or not in_bpm:
        return {"eligible": False, "reason": "LOCAL_TEMPO_UNAVAILABLE"}

    ratio = in_bpm / out_bpm  # direct relation only, no half/double folding
    correction = abs(ratio - 1.0)
    if correction > MAX_TEMPO_CORRECTION:
        return {"eligible": False, "reason": "TEMPO_CORRECTION_EXCEEDS_6PCT", "tempo_correction": round(correction, 4)}

    out_a, in_a = analysis[out_id], analysis[in_id]
    compat_input = srmp.build_pair_compat_input(out_a, in_a)

    return {
        "eligible": True,
        "reason": "OK",
        "exit_anchor_s": round(exit_anchor_s, 3),
        "entry_anchor_s": round(entry_anchor_s, 3),
        "exit_anchor_raw_s": round(exit_raw_s, 3),
        "entry_anchor_raw_s": round(entry_raw_s, 3),
        "outgoing_local_bpm": round(out_bpm, 2),
        "incoming_local_bpm": round(in_bpm, 2),
        "tempo_ratio": round(ratio, 4),
        "tempo_correction": round(correction, 4),
        "exit_structure_confidence": out_a["candidates"]["exit_structure_confidence"],
        "harmonic_relationship": compat_input["harmonic_relationship"],
        "combined_energy_gap_db": compat_input["_combined_energy_gap_db"],
    }


def soft_rank_key(pair_id: str, ev: dict):
    structure_rank = 0 if ev["exit_structure_confidence"] == "HIGH" else 1
    tempo_rank = ev["tempo_correction"]
    harmonic_rank = 0 if ev["harmonic_relationship"] == "COMPATIBLE" else (1 if ev["harmonic_relationship"] is None else 2)
    energy_rank = ev["combined_energy_gap_db"]
    return (structure_rank, tempo_rank, harmonic_rank, energy_rank, pair_id)


def select_final_8(ranked_eligible: list) -> list:
    """Greedy selection in soft-rank order, enforcing max-2-appearances and
    no-reverse-duplicate, until REQUIRED_PAIR_COUNT are frozen."""
    selected = []
    appearances: dict[str, int] = {}
    reverse_selected: set[tuple[str, str]] = set()
    for out_id, in_id, ev in ranked_eligible:
        if (in_id, out_id) in reverse_selected:
            continue
        if appearances.get(out_id, 0) + 1 > MAX_APPEARANCES:
            continue
        if appearances.get(in_id, 0) + 1 > MAX_APPEARANCES:
            continue
        selected.append((out_id, in_id, ev))
        reverse_selected.add((out_id, in_id))
        appearances[out_id] = appearances.get(out_id, 0) + 1
        appearances[in_id] = appearances.get(in_id, 0) + 1
        if len(selected) == REQUIRED_PAIR_COUNT:
            break
    return selected


def assign_holdout(selected: list) -> dict:
    def split_key(out_id, in_id):
        return hashlib.sha256(f"{HOLDOUT_SALT}|SPLIT|{out_id}|{in_id}".encode("utf-8")).hexdigest()
    ranked = sorted(selected, key=lambda t: (split_key(t[0], t[1]), t[0], t[1]))
    holdout_keys = {(o, i) for o, i, _ in ranked[:HOLDOUT_COUNT]}
    return holdout_keys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--beat-cache", default=str(HERE / "work_local" / "beat_cache"))
    ap.add_argument("--manifest-out", required=True)
    args = ap.parse_args()

    analysis = load_json(CORPUS_DIR / "corpus_analysis.local.json")
    beat_cache_dir = Path(args.beat_cache)
    ids = sorted(analysis.keys())

    eligible = []
    ineligible_reason_counts: dict[str, int] = {}
    for out_id in ids:
        for in_id in ids:
            if out_id == in_id:
                continue
            pair_id = build_pair_id(out_id, in_id)
            ev = evaluate_pair(out_id, in_id, analysis, beat_cache_dir)
            if ev["eligible"]:
                eligible.append((out_id, in_id, ev))
            else:
                ineligible_reason_counts[ev["reason"]] = ineligible_reason_counts.get(ev["reason"], 0) + 1

    ranked = sorted(eligible, key=lambda t: soft_rank_key(build_pair_id(t[0], t[1]), t[2]))
    print(f"Eligible pairs found: {len(eligible)} (out of {len(ids) * (len(ids) - 1)} ordered pairs)")
    for reason, count in sorted(ineligible_reason_counts.items(), key=lambda x: -x[1]):
        print(f"  ineligible[{reason}] = {count}")

    if len(eligible) < REQUIRED_PAIR_COUNT:
        out = {
            "status": "INSUFFICIENT_POSITIVE_REAL_PAIRS",
            "eligible_pair_count": len(eligible),
            "required": REQUIRED_PAIR_COUNT,
            "ineligible_reason_counts": ineligible_reason_counts,
        }
        Path(args.manifest_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"RESULT: INSUFFICIENT_POSITIVE_REAL_PAIRS ({len(eligible)}/{REQUIRED_PAIR_COUNT})")
        return 1

    selected = select_final_8(ranked)
    if len(selected) < REQUIRED_PAIR_COUNT:
        out = {
            "status": "INSUFFICIENT_POSITIVE_REAL_PAIRS",
            "eligible_pair_count": len(eligible),
            "selected_after_appearance_cap": len(selected),
            "required": REQUIRED_PAIR_COUNT,
            "ineligible_reason_counts": ineligible_reason_counts,
        }
        Path(args.manifest_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"RESULT: INSUFFICIENT_POSITIVE_REAL_PAIRS after appearance-cap ({len(selected)}/{REQUIRED_PAIR_COUNT})")
        return 1

    holdout_keys = assign_holdout(selected)
    pairs_out = []
    for out_id, in_id, ev in selected:
        split = "holdout" if (out_id, in_id) in holdout_keys else "dev"
        pairs_out.append({"out_id": out_id, "in_id": in_id, "split": split, **ev})

    manifest = {
        "status": "FROZEN",
        "pair_count": len(pairs_out),
        "dev_count": sum(1 for p in pairs_out if p["split"] == "dev"),
        "holdout_count": sum(1 for p in pairs_out if p["split"] == "holdout"),
        "max_tempo_correction_envelope": MAX_TEMPO_CORRECTION,
        "eligible_pair_count_before_appearance_cap": len(eligible),
        "pairs": pairs_out,
    }
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"RESULT: FROZEN {len(pairs_out)} pairs ({manifest['dev_count']} dev / {manifest['holdout_count']} holdout)")
    for p in pairs_out:
        print(f"  {p['out_id']}->{p['in_id']} [{p['split']}] tempo_correction={p['tempo_correction']} structure={p['exit_structure_confidence']} harmonic={p['harmonic_relationship']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
