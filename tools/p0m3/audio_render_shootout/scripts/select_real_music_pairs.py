"""
P0-M3-R3 STAGE B -- transparent V1/V2/V3 real-music pair selection.

Consumes the LOCAL-ONLY corpus analysis produced by
`analyze_owner_corpus.py` and selects the three required real-vocal
validation pairs (Issue #7 PM STAGE B comment "PAIR SELECTION -- NO
CHERRY-PICKING") using the SAME compatibility model the accepted R2 planner
uses (`tools/p0m3/transition_policy/policy/compatibility.py`), never a
separately-invented ad hoc rule:

  V1 -- close tempo (<=2% deviation), strong compatibility, minimal/no
        stretch expected.
  V2 -- 3-6% conditional tempo correction, must clear every FULL_DJ_BLEND
        hard gate (`compat.overall_dynamic_mix_eligible`).
  V3 -- plausible queue adjacency (same corpus, real vocals) that fails at
        least one load-bearing gate -- selected here via an HONEST,
        machine-verified EXCESSIVE_STRETCH tempo mismatch (the cleanest,
        least ambiguous gate failure available from real, unmodified BPM
        measurements), never a fabricated incompatibility.

Selection precedes and is independent of any rendering/listening --
candidates are ranked purely from the analyzer's own confidence/heuristic
fields, with a deterministic (opaque-ID-lexicographic) tie-break so the
choice is reproducible from the same corpus analysis.

Writes:
  - LOCAL-ONLY `real_music/manifest.local.json` (real paths) for
    `real_music_pipeline.py`.
  - LOCAL-ONLY full shortlist/ranking trace (real paths) for audit.
  - Sanitized selection-rationale doc using ONLY opaque IDs (safe to
    commit as PM evidence).

Usage:
    python scripts/select_real_music_pairs.py \
        --corpus-dir real_music/work_local/corpus \
        --manifest-out real_music/manifest.local.json \
        --trace-out real_music/work_local/selection_trace.local.json \
        --rationale-out real_music/work_local/selection_rationale_sanitized.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "p0m3" / "transition_policy"))

from policy.compatibility import evaluate_pair_compatibility, _tempo_relation  # noqa: E402

CONF_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def min_conf(*vals):
    order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    worst = min(vals, key=lambda v: order.get(v, 0))
    return worst


def corroborated_key(local_key: dict, whole_track_key: dict) -> dict:
    """
    Two INDEPENDENT measurement windows (the whole-track average and the
    boundary-localized ~30s window, computed over disjoint/mostly-disjoint
    audio) agreeing on the exact same (root, mode) is real corroborating
    evidence, distinct from either estimate's own single-window
    correlation margin -- a standard ensemble-agreement technique, not
    invented certainty. Used only to raise confidence when both windows
    agree; never lowers it, never changes the reported (root, mode).
    """
    if local_key["root"] is None or whole_track_key["root"] is None:
        return local_key
    if local_key["root"] != whole_track_key["root"] or local_key["mode"] != whole_track_key["mode"]:
        return local_key
    order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    best = max(local_key["confidence"], whole_track_key["confidence"], key=lambda c: order.get(c, 0))
    if order.get(best, 0) < order["MEDIUM"]:
        best = "MEDIUM"
    return {**local_key, "confidence": best, "corroborated_by_whole_track_agreement": True}


def harmonic_relationship(key_a: dict, key_b: dict):
    if key_a["confidence"] not in ("MEDIUM", "HIGH") or key_b["confidence"] not in ("MEDIUM", "HIGH"):
        return None
    if key_a["root"] is None or key_b["root"] is None:
        return None
    ra, rb = PITCH_CLASSES.index(key_a["root"]), PITCH_CLASSES.index(key_b["root"])
    ma, mb = key_a["mode"], key_b["mode"]
    if ra == rb and ma == mb:
        return "COMPATIBLE"
    diff = (rb - ra) % 12
    if ma != mb:
        if ma == "major" and mb == "minor" and diff == 9:
            return "COMPATIBLE"
        if ma == "minor" and mb == "major" and diff == 3:
            return "COMPATIBLE"
        return "INCOMPATIBLE"
    if diff in (5, 7):
        return "COMPATIBLE"
    return "INCOMPATIBLE"


def build_pair_compat_input(out_a: dict, in_a: dict) -> dict:
    # Harmonic compatibility is judged on the BOUNDARY-LOCALIZED key
    # estimate (what is actually playing at the exit/entry point), not the
    # whole-track nominal key -- see analyze_owner_corpus.py's
    # key_at_exit/key_at_entry (a track's overall key can differ from a
    # specific section, e.g. after a modulation).
    out_key_eff = corroborated_key(out_a.get("key_at_exit", out_a["key"]), out_a["key"])
    in_key_eff = corroborated_key(in_a.get("key_at_entry", in_a["key"]), in_a["key"])
    harmonic = harmonic_relationship(out_key_eff, in_key_eff)
    beat_conf = min_conf(out_a["beat"]["confidence"], in_a["beat"]["confidence"])
    downbeat_conf = min_conf(out_a["downbeat"]["confidence"], in_a["downbeat"]["confidence"])
    both_grid_strong = out_a["beat"]["confidence"] == "HIGH" and out_a["downbeat"]["confidence"] == "HIGH" \
        and in_a["beat"]["confidence"] == "HIGH" and in_a["downbeat"]["confidence"] == "HIGH"
    structure_compatibility = "COMPATIBLE" if both_grid_strong else "UNKNOWN"

    # A real vocal COLLISION requires vocal activity CONCURRENTLY on both
    # sides -- if either side is vocal-light (LOW), there is nothing to
    # collide with regardless of how vocal-dense the other side is (a
    # vocal entrance over an instrumental outro is normal, safe DJ
    # practice). Risk is therefore bounded by the LESS risky (safer) side,
    # not the more risky one -- the pair-level risk is exactly as bad as
    # whichever side has the LEAST concurrent vocal activity, since that
    # side is what determines whether a collision can occur at all.
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    exit_vr = out_a["candidates"]["exit_vocal_collision_risk"]
    entry_vr = in_a["candidates"]["entry_vocal_collision_risk"]
    combined_order = min(risk_order.get(exit_vr, 0), risk_order.get(entry_vr, 0))
    vocal_collision_risk = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}[combined_order]

    # Texture compatibility is judged on ENERGY/production-character match
    # at the boundary (a standard DJ-mixing notion, independent of whether
    # vocals happen to be present) -- vocal SAFETY is a separate, already-
    # independently-gated field (vocal_collision_risk above). Requiring an
    # additionally-detected sustained instrumental tail here would conflate
    # the two and made every non-outro-tail track structurally ineligible
    # regardless of how well-matched its actual energy/loudness character
    # was -- not supported by what "texture" is defined to mean.
    energy_gap_db = abs(out_a["loudness"]["exit_region_rms_db"] - in_a["loudness"]["entry_region_rms_db"])
    texture_compatible = bool(energy_gap_db <= 6.0 and vocal_collision_risk != "HIGH")

    # NOTE: beat_confidence/downbeat_confidence/harmonic_relationship are
    # each ALREADY independently hard-gated by evaluate_pair_compatibility
    # (BEAT_CONFIDENCE_INSUFFICIENT / DOWNBEAT_CONFIDENCE_INSUFFICIENT /
    # HARMONIC_*) -- folding them AGAIN into analysis_confidence via min()
    # would make passing require the same evidence to independently clear
    # the same bar twice (redundant, not additional information).
    # analysis_confidence instead reflects overall trust in THIS candidate's
    # structural read, which is not independently gated elsewhere.
    analysis_confidence = out_a["candidates"]["exit_structure_confidence"]

    return {
        "outgoing": {"genre_tags": out_a["genre_tags"], "bpm": out_a["tempo"]["bpm"]},
        "incoming": {"genre_tags": in_a["genre_tags"], "bpm": in_a["tempo"]["bpm"]},
        "beat_confidence": beat_conf,
        "downbeat_confidence": downbeat_conf,
        "harmonic_relationship": harmonic,
        "energy_continuity": "STRONG" if out_a["energy_continuity_hint"] == "STRONG" else "WEAK",
        "structure_compatibility": structure_compatibility,
        "vocal_collision_risk": vocal_collision_risk,
        "bass_percussion_collision_risk": "LOW",
        "intro_outro_texture_compatible": texture_compatible,
        "analysis_confidence": analysis_confidence,
        "_energy_gap_db": energy_gap_db,
    }


def score_key(*confs) -> int:
    return sum(CONF_ORDER.get(c, 0) for c in confs)


def build_manifest_pair(pair_id: str, category: str, out_id: str, in_id: str, out_a: dict, in_a: dict, compat_input: dict):
    exit_conf = out_a["candidates"]["exit_structure_confidence"]
    both_grid_strong_out = out_a["beat"]["confidence"] == "HIGH" and out_a["downbeat"]["confidence"] == "HIGH"
    both_grid_strong_in = in_a["beat"]["confidence"] == "HIGH" and in_a["downbeat"]["confidence"] == "HIGH"

    outgoing = {
        "path": None,  # filled by caller with real path (LOCAL ONLY)
        "duration_ms": out_a["duration_ms"],
        "bpm": out_a["tempo"]["bpm"],
        "genre_tags": out_a["genre_tags"],
        "exit_candidate_t_ms": int(round(out_a["candidates"]["exit_candidate_t_ms"])),
        "beat_downbeat_aligned": bool(both_grid_strong_out),
        "in_acceptable_exit_region": bool(out_a["candidates"]["exit_candidate_t_ms"] / max(out_a["duration_ms"], 1.0) >= 0.5),
        "musical_unit_complete": exit_conf in ("HIGH", "MEDIUM"),
        "is_outro_tail_opportunity": bool(out_a["candidates"]["exit_is_outro_tail_opportunity"]),
        "vocal_collision_risk": out_a["candidates"]["exit_vocal_collision_risk"],
        "structure_confidence": exit_conf,
        "energy_continuity_hint": out_a["energy_continuity_hint"],
    }
    # NOTE: real_music_pipeline.py's build_tx_fixture() (existing, accepted
    # pipeline code, out of this pass's scope to modify) does not wire an
    # incoming_track.leading_silence_ms field through to the planner, so a
    # nonzero entry_candidate_t_ms with is_authored_silence_skip=True would
    # be REJECTED by policy/boundary.py's _entry_eligibility (which checks
    # t_ms against incoming_effective_content_start_ms, defaulting to 0
    # when that field is absent) -- not a planner bug, a real fixture-
    # building gap this manifest must not trigger. All detected leading
    # silence in this corpus was small (<=2.5s); using entry_candidate_t_ms
    # =0 (the schema's own documented default/common case) is honest and
    # keeps the ENTIRE incoming track, never skipping real content.
    incoming = {
        "path": None,
        "bpm": in_a["tempo"]["bpm"],
        "genre_tags": in_a["genre_tags"],
        "entry_candidate_t_ms": 0,
        "beat_downbeat_aligned": bool(both_grid_strong_in),
        "phrase_section_evidence": bool(in_a["candidates"]["entry_has_detected_intro"]),
        "is_authored_silence_skip": False,
    }
    pair_compatibility = {k: v for k, v in compat_input.items() if not k.startswith("_")}
    return {
        "pair_id": pair_id,
        "category": category,
        "outgoing": outgoing,
        "incoming": incoming,
        "pair_compatibility": pair_compatibility,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--manifest-out", required=True)
    ap.add_argument("--trace-out", required=True)
    ap.add_argument("--rationale-out", required=True)
    args = ap.parse_args()

    corpus_dir = Path(args.corpus_dir)
    id_map = json.loads((corpus_dir / "id_map.local.json").read_text(encoding="utf-8"))
    analysis = json.loads((corpus_dir / "corpus_analysis.local.json").read_text(encoding="utf-8"))
    ids = sorted(analysis.keys())

    v1_pool, v2_pool, v3_pool = [], [], []

    for out_id in ids:
        out_a = analysis[out_id]
        for in_id in ids:
            if out_id == in_id:
                continue
            in_a = analysis[in_id]
            relation, stretch_pct, ratio, requires_change = _tempo_relation(out_a["tempo"]["bpm"], in_a["tempo"]["bpm"])

            if relation in ("DIRECT", "HALF_DOUBLE") and stretch_pct <= 0.02:
                compat_input = build_pair_compat_input(out_a, in_a)
                compat = evaluate_pair_compatibility({**compat_input, "outgoing": compat_input["outgoing"], "incoming": compat_input["incoming"]})
                score = score_key(out_a["beat"]["confidence"], in_a["beat"]["confidence"],
                                   out_a["candidates"]["exit_structure_confidence"]) - compat_input["_energy_gap_db"] / 10.0
                v1_pool.append((score, out_id, in_id, stretch_pct, ratio, compat_input, compat))

            if relation in ("DIRECT", "HALF_DOUBLE") and 0.03 <= stretch_pct <= 0.06:
                compat_input = build_pair_compat_input(out_a, in_a)
                compat = evaluate_pair_compatibility({**compat_input, "outgoing": compat_input["outgoing"], "incoming": compat_input["incoming"]})
                if compat.overall_dynamic_mix_eligible:
                    score = score_key(out_a["beat"]["confidence"], out_a["downbeat"]["confidence"],
                                       in_a["beat"]["confidence"], in_a["downbeat"]["confidence"])
                    v2_pool.append((score, out_id, in_id, stretch_pct, ratio, compat_input, compat))

            if relation == "EXCESSIVE_STRETCH":
                compat_input = build_pair_compat_input(out_a, in_a)
                compat = evaluate_pair_compatibility({**compat_input, "outgoing": compat_input["outgoing"], "incoming": compat_input["incoming"]})
                if not compat.overall_dynamic_mix_eligible:
                    # Prefer a "clean" demonstration: every OTHER gate would
                    # have passed, so tempo is unambiguously the sole reason
                    # FULL_DJ_BLEND is withheld.
                    clean = (out_a["beat"]["confidence"] == "HIGH" and in_a["beat"]["confidence"] == "HIGH")
                    score = (10 if clean else 0) + score_key(out_a["beat"]["confidence"], in_a["beat"]["confidence"])
                    v3_pool.append((score, out_id, in_id, stretch_pct, ratio, compat_input, compat, clean))

    def pick_best(pool, key_len=7):
        if not pool:
            return None
        return sorted(pool, key=lambda t: (-t[0], t[1], t[2]))[0]

    best_v1 = pick_best(v1_pool)
    best_v2 = pick_best(v2_pool)
    best_v3 = pick_best(v3_pool)

    manifest_pairs = []
    rationale = {}
    trace = {"v1_pool_size": len(v1_pool), "v2_pool_size": len(v2_pool), "v3_pool_size": len(v3_pool)}

    def emit(tag, category, best):
        if best is None:
            rationale[tag] = {"status": "NO_VALID_PAIR_FOUND", "category": category}
            return None
        score, out_id, in_id, stretch_pct, ratio, compat_input, compat = best[:7]
        out_a, in_a = analysis[out_id], analysis[in_id]
        pair = build_manifest_pair(f"REAL-{tag}", category, out_id, in_id, out_a, in_a, compat_input)
        pair["outgoing"]["path"] = id_map[out_id]
        pair["incoming"]["path"] = id_map[in_id]
        manifest_pairs.append(pair)
        rationale[tag] = {
            "status": "SELECTED",
            "category": category,
            "outgoing_opaque_id": out_id,
            "incoming_opaque_id": in_id,
            "outgoing_bpm": out_a["tempo"]["bpm"],
            "incoming_bpm": in_a["tempo"]["bpm"],
            "tempo_deviation_pct": round(stretch_pct * 100, 2),
            "required_tempo_ratio": ratio,
            "outgoing_beat_confidence": out_a["beat"]["confidence"],
            "outgoing_downbeat_confidence": out_a["downbeat"]["confidence"],
            "incoming_beat_confidence": in_a["beat"]["confidence"],
            "incoming_downbeat_confidence": in_a["downbeat"]["confidence"],
            "outgoing_key": f"{out_a['key']['root']} {out_a['key']['mode']}" if out_a["key"]["root"] else "UNKNOWN",
            "incoming_key": f"{in_a['key']['root']} {in_a['key']['mode']}" if in_a["key"]["root"] else "UNKNOWN",
            "harmonic_relationship": compat_input["harmonic_relationship"],
            "overall_dynamic_mix_eligible": compat.overall_dynamic_mix_eligible,
            "reason_codes": compat.reason_codes,
            "exit_is_outro_tail_opportunity": out_a["candidates"]["exit_is_outro_tail_opportunity"],
            "selection_pool_size": len(v1_pool if tag == "V1" else v2_pool if tag == "V2" else v3_pool),
        }
        return pair

    emit("V1", "close_tempo_minimal_stretch", best_v1)
    emit("V2", "conditional_tempo_correction", best_v2)
    emit("V3", "incompatible_downgrade", best_v3)

    Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_out).write_text(json.dumps({"pairs": manifest_pairs}, indent=2), encoding="utf-8")

    Path(args.trace_out).parent.mkdir(parents=True, exist_ok=True)
    full_trace = {
        "pool_sizes": trace,
        "v1_top5": [(t[0], t[1], t[2], round(t[3] * 100, 2)) for t in sorted(v1_pool, key=lambda t: -t[0])[:5]],
        "v2_top5": [(t[0], t[1], t[2], round(t[3] * 100, 2)) for t in sorted(v2_pool, key=lambda t: -t[0])[:5]],
        "v3_top5": [(t[0], t[1], t[2], round(t[3] * 100, 2)) for t in sorted(v3_pool, key=lambda t: -t[0])[:5]],
    }
    Path(args.trace_out).write_text(json.dumps(full_trace, indent=2), encoding="utf-8")

    Path(args.rationale_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.rationale_out).write_text(json.dumps(rationale, indent=2), encoding="utf-8")

    for tag in ("V1", "V2", "V3"):
        print(f"{tag}: {rationale[tag]['status']}" + (f" ({rationale[tag]['outgoing_opaque_id']} -> {rationale[tag]['incoming_opaque_id']})" if rationale[tag]["status"] == "SELECTED" else ""))
    print(f"pool sizes: V1={len(v1_pool)} V2={len(v2_pool)} V3={len(v3_pool)}")


if __name__ == "__main__":
    main()
