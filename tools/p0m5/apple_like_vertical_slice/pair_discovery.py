"""
P0-M5-R1 Phase C -- deterministic positive-pair discovery.

REPAIR PASS (PM review, Issue #10 comment `5322363724`,
`P0_M5_R1_PRELISTEN_REPAIR_REQUIRED`, BLOCKER 1 + stretch-coverage
requirement): the original pass derived local tempo from `downbeats_s`
(a bar/downbeat EVENT rate, not track beat tempo). Concrete frozen
evidence exposed the defect: `RM089->RM018` was admitted with both sides'
bar-rate values coinciding at ~31.25 (tempo_ratio 1.0), while the two
tracks' actual Beat This beat tempi are ~125 BPM and ~63.83 BPM --
exactly the half/double-time ambiguity this rapid slice explicitly
excludes. Repaired here:

  - local tempo is now computed from `beats_s` (actual beat events) near
    the selected anchors -- `downbeats_s` are used ONLY for bar-phase/
    boundary-snapping (unchanged role), never for tempo;
  - the pair-level tempo test remains a DIRECT ratio only (no half/double
    folding, per Issue #10's original scope);
  - a new, separate per-side guard rejects a local tempo estimate that is
    plausibly an octave (half/double) misread relative to that SAME
    track's own already-cached, already-correct `median_beat_bpm`
    (`beat_analysis_aggregate_sanitized.json`, Phase B's own sanitized
    aggregate -- reused verbatim, not recomputed, no new analyzer pass);
  - discovery is re-run from the existing cached Beat This outputs only
    (`work_local/beat_cache/`); the 100-track Beat This pass itself is
    NOT rerun.

Also implements the PM-required stretch-coverage rule: the frozen 8 must
contain exactly 2 deterministic "stretch-cover" pairs (direct-tempo
correction in [2%, 6%]) plus 6 best remaining near-native pairs, so the
owner listening pack actually exercises the Signalsmith time-stretch path
at least twice -- otherwise (as the unrepaired pass discovered, honestly,
by accident) the frozen set can degenerate to 8/8 zero-correction pairs
that never touch the stretch DSP at all. If fewer than 2 valid
stretch-cover candidates exist anywhere in the corpus, this module stops
at `INSUFFICIENT_POSITIVE_STRETCH_COVERAGE` rather than silently
retreating to an all-near-native set.

Scores every eligible ordered pair using ONLY already-cached evidence:

  - `corpus_analysis.local.json` (the same Stage-B evidence P0-M4-R2 used:
    exit/entry candidates, structure confidence, harmonic/key/loudness/
    texture measurements) -- reused verbatim, no new analyzer;
  - `beat_analysis_aggregate_sanitized.json` + the local per-track
    `beats_s`/`downbeats_s` cache produced by `corpus_beat_analysis.py`
    (Phase B, this task's one authorized new analyzer pass -- not rerun
    by this repair).

No manual song selection and no listening-outcome feedback are used
anywhere in this module (no owner listening has occurred).

Hard eligibility:
  - two distinct tracks;
  - outgoing exit candidate has cached structure_confidence MEDIUM/HIGH
    (the accepted R2 late/natural-region evidence);
  - both tracks have a successful Beat This pass with a downbeat near the
    selected outgoing exit region and near the incoming entry region
    (for bar-phase snapping) AND enough nearby beat events for a local
    tempo estimate;
  - neither side's local beat tempo is octave-ambiguous relative to its
    own track-level median beat BPM;
  - direct tempo relation only: |incoming_local_beat_bpm /
    outgoing_local_beat_bpm - 1| <= 0.06 (no half/double-time folding);
  - no source-analysis failure on either side.

Boundary policy (unchanged by this repair): outgoing exit snaps to the
nearest Beat This downbeat at or after the cached exit_candidate_t_ms;
incoming entry is the first Beat This downbeat at or after the cached
leading-silence-skip point (0 if none is authored) -- SongFormer
intro/outro evidence remains unavailable (`SONGFORMER_BLOCKED_ASSET_TERMS`,
not reopened per PM instruction), so this task uses the "otherwise"
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

MAX_TEMPO_CORRECTION = 0.06  # Issue #10 Phase C hard eligibility -- unchanged
STRETCH_COVER_MIN = 0.02  # PM repair: stretch-cover band lower bound
STRETCH_COVER_MAX = MAX_TEMPO_CORRECTION  # 0.06, same envelope, never widened
STRETCH_COVER_REQUIRED_COUNT = 2
MAX_APPEARANCES = 2
REQUIRED_PAIR_COUNT = 8
HOLDOUT_COUNT = 2
DOWNBEAT_SEARCH_WINDOW_S = 45.0  # how far from the cached exit candidate a downbeat may be snapped
HOLDOUT_SALT = "P0-M5-R1-APPLE-LIKE-V1"
OCTAVE_TOLERANCE = 0.08  # relative tolerance around an exact 2x/0.5x octave ratio


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
    placement, rather than M0 silently inheriting M1's beat-aware anchor.
    `downbeats_s` here is used ONLY for bar-phase boundary snapping, per
    the PM repair -- never for tempo (see `local_beat_tempo_near` below)."""
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
    """Returns (snapped_downbeat_s, raw_skip_point_s, reason). Same
    bar-phase-only role for `downbeats_s` as the outgoing side."""
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


def local_beat_tempo_near(beats_s: list, anchor_s: float, n_beats: int = 8) -> float | None:
    """PM repair (BLOCKER 1): median BEAT (not bar/downbeat) interval near
    the anchor, converted to true beats-per-minute. This is the track's
    actual playable tempo at this point, not a bar/downbeat event rate."""
    nearby = sorted(beats_s, key=lambda t: abs(t - anchor_s))[: n_beats + 1]
    nearby = sorted(nearby)
    intervals = [b - a for a, b in zip(nearby, nearby[1:]) if b > a]
    if not intervals:
        return None
    intervals.sort()
    mid = intervals[len(intervals) // 2]
    return 60.0 / mid if mid > 0 else None


def local_bar_period_s_near(downbeats_s: list, anchor_s: float, n_bars: int = 4) -> float | None:
    """Bar (downbeat-interval) period in SECONDS near the anchor -- used
    ONLY for sizing the render window to a whole number of bars
    (`apple_like_render.py`), never for tempo/eligibility. Kept as a
    period (not converted to a bpm-shaped scalar) so it can never be
    mistaken for the beat-tempo field again."""
    nearby = sorted(downbeats_s, key=lambda t: abs(t - anchor_s))[: n_bars + 1]
    nearby = sorted(nearby)
    intervals = [b - a for a, b in zip(nearby, nearby[1:]) if b > a]
    if not intervals:
        return None
    intervals.sort()
    return intervals[len(intervals) // 2]


def octave_ambiguous(local_bpm: float, track_median_bpm: float, tol: float = OCTAVE_TOLERANCE) -> bool:
    """PM repair (BLOCKER 1, guard 3): true if `local_bpm` is plausibly an
    octave (half/double) misread of this SAME track's own already-cached
    median beat BPM -- a local passage where Beat This's beat spacing
    locally looks doubled/halved relative to the track's own documented
    tempo. Deterministic, fixed tolerance; never silently normalized."""
    if not local_bpm or not track_median_bpm:
        return False
    ratio = local_bpm / track_median_bpm
    return abs(ratio - 2.0) <= 2.0 * tol or abs(ratio - 0.5) <= 0.5 * tol


def build_pair_id(out_id: str, in_id: str) -> str:
    return hashlib.sha256(f"{out_id}|{in_id}".encode("utf-8")).hexdigest()


def evaluate_pair(out_id: str, in_id: str, analysis: dict, beat_cache_dir: Path, beat_aggregate: dict) -> dict:
    exit_anchor_s, exit_raw_s, exit_reason = outgoing_exit_anchor_s(out_id, analysis, beat_cache_dir)
    if exit_anchor_s is None:
        return {"eligible": False, "reason": exit_reason}
    entry_anchor_s, entry_raw_s, entry_reason = incoming_entry_anchor_s(in_id, analysis, beat_cache_dir)
    if entry_anchor_s is None:
        return {"eligible": False, "reason": entry_reason}

    out_cache = load_json(beat_cache_dir / f"{out_id}.json")
    in_cache = load_json(beat_cache_dir / f"{in_id}.json")

    out_bpm = local_beat_tempo_near(out_cache["beats_s"], exit_anchor_s)
    in_bpm = local_beat_tempo_near(in_cache["beats_s"], entry_anchor_s)
    if not out_bpm or not in_bpm:
        return {"eligible": False, "reason": "LOCAL_TEMPO_UNAVAILABLE"}

    out_track_median_bpm = beat_aggregate["tracks"][out_id]["median_beat_bpm"]
    in_track_median_bpm = beat_aggregate["tracks"][in_id]["median_beat_bpm"]
    if octave_ambiguous(out_bpm, out_track_median_bpm):
        return {"eligible": False, "reason": "LOCAL_TEMPO_OCTAVE_AMBIGUITY"}
    if octave_ambiguous(in_bpm, in_track_median_bpm):
        return {"eligible": False, "reason": "LOCAL_TEMPO_OCTAVE_AMBIGUITY"}

    ratio = in_bpm / out_bpm  # direct relation only, no half/double folding
    correction = abs(ratio - 1.0)
    if correction > MAX_TEMPO_CORRECTION:
        return {"eligible": False, "reason": "TEMPO_CORRECTION_EXCEEDS_6PCT", "tempo_correction": round(correction, 4)}

    out_bar_period_s = local_bar_period_s_near(out_cache["downbeats_s"], exit_anchor_s)
    if not out_bar_period_s:
        return {"eligible": False, "reason": "BAR_PERIOD_UNAVAILABLE"}

    out_a, in_a = analysis[out_id], analysis[in_id]
    compat_input = srmp.build_pair_compat_input(out_a, in_a)

    return {
        "eligible": True,
        "reason": "OK",
        "exit_anchor_s": round(exit_anchor_s, 3),
        "entry_anchor_s": round(entry_anchor_s, 3),
        "exit_anchor_raw_s": round(exit_raw_s, 3),
        "entry_anchor_raw_s": round(entry_raw_s, 3),
        "outgoing_local_beat_bpm": round(out_bpm, 2),
        "incoming_local_beat_bpm": round(in_bpm, 2),
        "outgoing_bar_period_s": round(out_bar_period_s, 4),
        "tempo_ratio": round(ratio, 4),
        "tempo_correction": round(correction, 4),
        "is_stretch_cover_candidate": bool(STRETCH_COVER_MIN <= correction <= STRETCH_COVER_MAX),
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


def greedy_fill(ranked_pool: list, target_count: int, appearances: dict, reverse_selected: set, already_selected_ids: set) -> list:
    """Greedy selection in soft-rank order, enforcing max-2-appearances and
    no-reverse-duplicate against the CURRENT (shared, mutated in place)
    appearance/reverse-pair state, skipping anything already selected."""
    picked = []
    for out_id, in_id, ev in ranked_pool:
        pid = build_pair_id(out_id, in_id)
        if pid in already_selected_ids:
            continue
        if (in_id, out_id) in reverse_selected:
            continue
        if appearances.get(out_id, 0) + 1 > MAX_APPEARANCES:
            continue
        if appearances.get(in_id, 0) + 1 > MAX_APPEARANCES:
            continue
        picked.append((out_id, in_id, ev))
        reverse_selected.add((out_id, in_id))
        appearances[out_id] = appearances.get(out_id, 0) + 1
        appearances[in_id] = appearances.get(in_id, 0) + 1
        already_selected_ids.add(pid)
        if len(picked) == target_count:
            break
    return picked


def assign_holdout_with_stretch_coverage(selected: list, stretch_pair_ids: set) -> set:
    """PM repair: deterministic holdout assignment that guarantees at
    least one stretch-cover pair lands in holdout whenever stretch-cover
    pairs were selected (always geometrically feasible here: 2 stretch
    pairs among 8 total, 2 holdout slots -- forcing exactly one stretch
    pair into holdout always leaves a valid remaining assignment)."""
    def split_key(out_id, in_id):
        return hashlib.sha256(f"{HOLDOUT_SALT}|SPLIT|{out_id}|{in_id}".encode("utf-8")).hexdigest()

    stretch_members = [(o, i, ev) for o, i, ev in selected if build_pair_id(o, i) in stretch_pair_ids]
    if not stretch_members:
        ranked = sorted(selected, key=lambda t: (split_key(t[0], t[1]), t[0], t[1]))
        return {(o, i) for o, i, _ in ranked[:HOLDOUT_COUNT]}

    stretch_ranked = sorted(stretch_members, key=lambda t: (split_key(t[0], t[1]), t[0], t[1]))
    guaranteed_holdout = stretch_ranked[0]
    remaining = [t for t in selected if t != guaranteed_holdout]
    remaining_ranked = sorted(remaining, key=lambda t: (split_key(t[0], t[1]), t[0], t[1]))
    holdout = {(guaranteed_holdout[0], guaranteed_holdout[1])}
    for o, i, _ in remaining_ranked:
        if len(holdout) >= HOLDOUT_COUNT:
            break
        holdout.add((o, i))
    return holdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--beat-cache", default=str(HERE / "work_local" / "beat_cache"))
    ap.add_argument("--beat-aggregate", default=str(HERE / "beat_analysis_aggregate_sanitized.json"))
    ap.add_argument("--manifest-out", required=True)
    args = ap.parse_args()

    analysis = load_json(CORPUS_DIR / "corpus_analysis.local.json")
    beat_cache_dir = Path(args.beat_cache)
    beat_aggregate = load_json(Path(args.beat_aggregate))
    ids = sorted(analysis.keys())

    eligible = []
    ineligible_reason_counts: dict[str, int] = {}
    for out_id in ids:
        for in_id in ids:
            if out_id == in_id:
                continue
            ev = evaluate_pair(out_id, in_id, analysis, beat_cache_dir, beat_aggregate)
            if ev["eligible"]:
                eligible.append((out_id, in_id, ev))
            else:
                ineligible_reason_counts[ev["reason"]] = ineligible_reason_counts.get(ev["reason"], 0) + 1

    ranked = sorted(eligible, key=lambda t: soft_rank_key(build_pair_id(t[0], t[1]), t[2]))
    print(f"Eligible pairs found: {len(eligible)} (out of {len(ids) * (len(ids) - 1)} ordered pairs)")
    for reason, count in sorted(ineligible_reason_counts.items(), key=lambda x: -x[1]):
        print(f"  ineligible[{reason}] = {count}")

    stretch_pool = [t for t in ranked if t[2]["is_stretch_cover_candidate"]]
    print(f"Stretch-cover candidates (correction in [{STRETCH_COVER_MIN},{STRETCH_COVER_MAX}]): {len(stretch_pool)}")

    if len(eligible) < REQUIRED_PAIR_COUNT:
        out = {"status": "INSUFFICIENT_POSITIVE_REAL_PAIRS", "eligible_pair_count": len(eligible), "required": REQUIRED_PAIR_COUNT, "ineligible_reason_counts": ineligible_reason_counts}
        Path(args.manifest_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"RESULT: INSUFFICIENT_POSITIVE_REAL_PAIRS ({len(eligible)}/{REQUIRED_PAIR_COUNT})")
        return 1

    if len(stretch_pool) < STRETCH_COVER_REQUIRED_COUNT:
        out = {
            "status": "INSUFFICIENT_POSITIVE_STRETCH_COVERAGE",
            "eligible_pair_count": len(eligible),
            "stretch_cover_candidate_count": len(stretch_pool),
            "required_stretch_cover_count": STRETCH_COVER_REQUIRED_COUNT,
            "stretch_cover_band": [STRETCH_COVER_MIN, STRETCH_COVER_MAX],
        }
        Path(args.manifest_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"RESULT: INSUFFICIENT_POSITIVE_STRETCH_COVERAGE ({len(stretch_pool)}/{STRETCH_COVER_REQUIRED_COUNT} candidates in band)")
        return 2

    appearances: dict[str, int] = {}
    reverse_selected: set[tuple[str, str]] = set()
    already_selected_ids: set[str] = set()

    stretch_selected = greedy_fill(stretch_pool, STRETCH_COVER_REQUIRED_COUNT, appearances, reverse_selected, already_selected_ids)
    if len(stretch_selected) < STRETCH_COVER_REQUIRED_COUNT:
        out = {
            "status": "INSUFFICIENT_POSITIVE_STRETCH_COVERAGE",
            "eligible_pair_count": len(eligible),
            "stretch_cover_candidate_count": len(stretch_pool),
            "stretch_selected_after_appearance_cap": len(stretch_selected),
            "required_stretch_cover_count": STRETCH_COVER_REQUIRED_COUNT,
        }
        Path(args.manifest_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"RESULT: INSUFFICIENT_POSITIVE_STRETCH_COVERAGE after appearance-cap ({len(stretch_selected)}/{STRETCH_COVER_REQUIRED_COUNT})")
        return 2

    near_native_selected = greedy_fill(ranked, REQUIRED_PAIR_COUNT - STRETCH_COVER_REQUIRED_COUNT, appearances, reverse_selected, already_selected_ids)
    selected = stretch_selected + near_native_selected
    if len(selected) < REQUIRED_PAIR_COUNT:
        out = {"status": "INSUFFICIENT_POSITIVE_REAL_PAIRS", "eligible_pair_count": len(eligible), "selected_after_appearance_cap": len(selected), "required": REQUIRED_PAIR_COUNT}
        Path(args.manifest_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"RESULT: INSUFFICIENT_POSITIVE_REAL_PAIRS after appearance-cap ({len(selected)}/{REQUIRED_PAIR_COUNT})")
        return 1

    stretch_ids = {build_pair_id(o, i) for o, i, _ in stretch_selected}
    holdout_keys = assign_holdout_with_stretch_coverage(selected, stretch_ids)

    pairs_out = []
    for out_id, in_id, ev in selected:
        split = "holdout" if (out_id, in_id) in holdout_keys else "dev"
        pairs_out.append({"out_id": out_id, "in_id": in_id, "split": split, **ev})

    manifest = {
        "status": "FROZEN",
        "pair_count": len(pairs_out),
        "dev_count": sum(1 for p in pairs_out if p["split"] == "dev"),
        "holdout_count": sum(1 for p in pairs_out if p["split"] == "holdout"),
        "stretch_cover_count": sum(1 for p in pairs_out if p["is_stretch_cover_candidate"]),
        "stretch_cover_holdout_count": sum(1 for p in pairs_out if p["is_stretch_cover_candidate"] and p["split"] == "holdout"),
        "max_tempo_correction_envelope": MAX_TEMPO_CORRECTION,
        "stretch_cover_band": [STRETCH_COVER_MIN, STRETCH_COVER_MAX],
        "eligible_pair_count_before_appearance_cap": len(eligible),
        "stretch_cover_candidate_count_before_appearance_cap": len(stretch_pool),
        "pairs": pairs_out,
    }
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"RESULT: FROZEN {len(pairs_out)} pairs ({manifest['dev_count']} dev / {manifest['holdout_count']} holdout; "
          f"{manifest['stretch_cover_count']} stretch-cover, {manifest['stretch_cover_holdout_count']} of them in holdout)")
    for p in pairs_out:
        print(f"  {p['out_id']}->{p['in_id']} [{p['split']}] stretch_cover={p['is_stretch_cover_candidate']} "
              f"tempo_correction={p['tempo_correction']} structure={p['exit_structure_confidence']} harmonic={p['harmonic_relationship']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
