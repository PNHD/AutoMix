"""
P0-M3-R3 FINAL REAL-CORPUS REPLAY (Issue #7 PM comment id 5313303841,
"PM REVIEW -- ALIGNMENT-ANCHOR CONTRACT ACCEPTED; ONE PRE-FLIGHT
CONSISTENCY FIX FOLDED INTO FINAL REAL-CORPUS REPLAY").

This is a REPLAY, not a new analysis pass: it reads ONLY the already-cached
`real_music/work_local/corpus/corpus_analysis.local.json` /
`id_map.local.json` (100-track owner corpus, already analyzed in prior
accepted sessions). No audio is decoded. No analyzer (All-In-One, BeatNet,
madmom, harmonic, style) is rerun corpus-wide. No render, no Signalsmith,
no Rubber Band, no owner listening pack.

Candidate-universe construction reuses the SAME deterministic building
blocks the accepted Stage-B selector (select_real_music_pairs.py) and its
shared gate-classification module (pair_gate_audit.py) already use -- this
script does not reimplement pool membership, gate semantics, or ranking; it
only ADDS the definitive per-candidate proof step the pool-membership
shortcut never performed: actually invoking the REAL, UNCHANGED canonical
boundary planner (tools/p0m3/transition_policy/policy/boundary
.plan_transition_boundary) on every gate-passing candidate, now carrying
the accepted alignment-anchor contract separation
(select_real_music_pairs.alignment_anchor_fields -- independent per-side
beat/downbeat evidence, PM REVIEW pre-flight consistency fix already
applied to policy/contract.py this same task).

A candidate is a STRICT FULL_DJ survivor only if:
  1. every pair_gate_audit.GATE_ORDER hard gate independently passes
     (genre/tempo/beat/downbeat/harmonic/structure/texture/vocal/bass/
     analysis_confidence) -- identical semantics to
     compatibility.evaluate_pair_compatibility, unmodified this pass;
  2. the outgoing exit candidate clears the real structural-evidence
     renderability guard (select_real_music_pairs.exit_candidate_renderable,
     mirroring policy/eligibility.py Guard 2, unmodified);
  3. the REAL policy.boundary.plan_transition_boundary(), given a
     synthetic-but-evidence-faithful transition fixture built directly from
     the cached per-track analysis (never from audio), returns
     decision_type == "TRANSITION" with "FULL_DJ_BLEND" in
     allowed_transition_class_set.

No RM id is ever special-cased in this script's control flow -- every
candidate is processed by the exact same code path regardless of opaque id.

Usage:
    python scripts/final_real_corpus_replay.py \
        --corpus-dir real_music/work_local/corpus \
        --out results/final_real_corpus_replay_sanitized.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import pair_gate_audit as audit  # noqa: E402
import select_real_music_pairs as selector  # noqa: E402
from policy.boundary import plan_transition_boundary  # noqa: E402
from policy.eligibility import SEAMLESS_FULL_TRACK_DEFAULT  # noqa: E402

CATEGORY_BANDS = {"V1": (0.0, 0.02), "V2": (0.03, 0.06)}
CATEGORY_TEMPO_TARGET_CENTER = {"V1": 0.0, "V2": 0.045}


def build_replay_tx_fixture(out_id: str, in_id: str, out_a: dict, in_a: dict, compat_input: dict) -> dict:
    """Builds the SAME transition-fixture shape
    real_music_pipeline.build_tx_fixture() constructs from a manifest pair
    -- reusing select_real_music_pairs.build_manifest_pair()'s outgoing/
    incoming dict construction so the alignment-anchor representation is
    byte-identical to what a real manifest entry for this pair would carry
    -- but built directly from cached analysis (no manifest round-trip, no
    local audio path, no decode)."""
    pair = selector.build_manifest_pair(f"REPLAY-{out_id}-{in_id}", "replay", out_id, in_id, out_a, in_a, compat_input)
    out, inc = pair["outgoing"], pair["incoming"]

    exit_candidate = {
        "candidate_id": f"{out_id}-OUT-EXIT",
        "t_ms": out["exit_candidate_t_ms"],
        "source": "cached_corpus_analysis",
        "in_acceptable_exit_region": out.get("in_acceptable_exit_region", False),
        "musical_unit_complete": out.get("musical_unit_complete", False),
        "is_outro_tail_opportunity": out.get("is_outro_tail_opportunity", False),
        "vocal_collision_risk": out.get("vocal_collision_risk", "NONE"),
        "structure_confidence": out.get("structure_confidence", "NONE"),
        "energy_continuity_hint": out.get("energy_continuity_hint", "UNKNOWN"),
        "is_end_of_track": False,
    }
    if "beat_alignment_target_ms" in out or "downbeat_alignment_target_ms" in out:
        if "beat_alignment_target_ms" in out:
            exit_candidate["beat_alignment_target_ms"] = out["beat_alignment_target_ms"]
        if "downbeat_alignment_target_ms" in out:
            exit_candidate["downbeat_alignment_target_ms"] = out["downbeat_alignment_target_ms"]
    else:
        exit_candidate["beat_downbeat_aligned"] = out.get("beat_downbeat_aligned", False)

    end_candidate = {
        "candidate_id": f"{out_id}-OUT-END",
        "t_ms": out["duration_ms"],
        "source": "cached_corpus_analysis",
        "in_acceptable_exit_region": True,
        "musical_unit_complete": True,
        "is_outro_tail_opportunity": True,
        "vocal_collision_risk": "NONE",
        "structure_confidence": out.get("structure_confidence", "NONE"),
        "is_end_of_track": True,
    }

    entry_candidate = {
        "candidate_id": f"{in_id}-IN-ANCHOR",
        "t_ms": inc["entry_candidate_t_ms"],
        "phrase_section_evidence": inc.get("phrase_section_evidence", False),
        "is_authored_silence_skip": inc.get("is_authored_silence_skip", False),
    }
    if "beat_alignment_target_ms" in inc or "downbeat_alignment_target_ms" in inc:
        if "beat_alignment_target_ms" in inc:
            entry_candidate["beat_alignment_target_ms"] = inc["beat_alignment_target_ms"]
        if "downbeat_alignment_target_ms" in inc:
            entry_candidate["downbeat_alignment_target_ms"] = inc["downbeat_alignment_target_ms"]
    else:
        entry_candidate["beat_downbeat_aligned"] = inc.get("beat_downbeat_aligned", False)

    return {
        "transition_id": f"REPLAY-{out_id}-{in_id}",
        "outgoing_track": {
            "duration_ms": out["duration_ms"],
            "genre_tags": out.get("genre_tags", []),
            "bpm": out["bpm"],
            "candidates": [exit_candidate, end_candidate],
        },
        "incoming_track": {
            "genre_tags": inc.get("genre_tags", []),
            "bpm": inc["bpm"],
            "leading_silence_is_authored_non_musical": inc.get("leading_silence_is_authored_non_musical", False),
            "leading_silence_ms": inc.get("leading_silence_ms", 0),
            "candidates": [entry_candidate],
        },
        "pair_base": pair["pair_compatibility"],
        "boundary_overrides": {},
    }


def replay_category(tag: str, analysis: dict):
    lo, hi = CATEGORY_BANDS[tag]
    tempo_target_center = CATEGORY_TEMPO_TARGET_CENTER[tag]
    ids = sorted(analysis.keys())
    total_pair_universe = len(ids) * (len(ids) - 1)

    records = audit.audit_universe(analysis, lo, hi)
    tempo_eligible_universe = len(records)

    gate_rejection_counts = {g: 0 for g in audit.GATE_ORDER}
    gate_rejection_counts["exit_structure_not_renderable"] = 0
    gate_rejection_counts["canonical_planner_full_dj_withheld"] = 0

    survivors = []
    for r in records:
        out_a, in_a = r["out_a"], r["in_a"]
        for g in r["failed_gates"]:
            gate_rejection_counts[g] += 1
        if r["failed_gates"]:
            continue
        if not selector.exit_candidate_renderable(out_a):
            gate_rejection_counts["exit_structure_not_renderable"] += 1
            continue

        fixture = build_replay_tx_fixture(r["out_id"], r["in_id"], out_a, in_a, r["compat_input"])
        decision = plan_transition_boundary(fixture, SEAMLESS_FULL_TRACK_DEFAULT)
        full_dj = decision.decision_type == "TRANSITION" and "FULL_DJ_BLEND" in decision.allowed_transition_class_set
        if not full_dj:
            gate_rejection_counts["canonical_planner_full_dj_withheld"] += 1
            continue

        cand = selector.build_candidate(r["out_id"], r["in_id"], out_a, in_a, r["relation"], r["stretch_pct"], r["ratio"], require_full_dj=True)
        survivors.append({
            "out_id": r["out_id"], "in_id": r["in_id"], "cand": cand,
            "tempo_deviation_pct": round(r["stretch_pct"] * 100, 2),
            "required_tempo_ratio": r["ratio"],
            "decision_type": decision.decision_type,
            "allowed_transition_class_set": decision.allowed_transition_class_set,
            "beat_alignment_action": decision.beat_alignment_action,
            "bar_alignment_action": decision.bar_alignment_action,
            "beat_phase_relation": decision.beat_phase_relation,
            "bar_phase_relation": decision.bar_phase_relation,
            "outgoing_content_preservation_target": decision.outgoing_content_preservation_target,
            "outgoing_beat_alignment_target_ms": decision.outgoing_beat_alignment_target_ms,
            "incoming_beat_alignment_target_ms": decision.incoming_beat_alignment_target_ms,
            "outgoing_downbeat_alignment_target_ms": decision.outgoing_downbeat_alignment_target_ms,
            "incoming_downbeat_alignment_target_ms": decision.incoming_downbeat_alignment_target_ms,
            "next_track_entry_window_ms": decision.next_track_entry_window_ms,
            "reason_codes": decision.reason_codes,
            "analysis_confidence": r["compat_input"]["analysis_confidence"],
        })

    ranked_survivors = sorted(
        survivors,
        key=lambda s: selector.rank_key(s["cand"], tempo_target_center, lambda i: analysis[i], lambda i: analysis[i]),
    )
    near_misses = audit.rank_near_misses(records, top_n=10)

    def sanitize_survivor(s):
        out = {k: v for k, v in s.items() if k != "cand"}
        return out

    return {
        "total_pair_universe": total_pair_universe,
        "tempo_eligible_universe": tempo_eligible_universe,
        "gate_rejection_counts": gate_rejection_counts,
        "strict_full_dj_survivor_count": len(ranked_survivors),
        "survivors_ranked_best_first": [sanitize_survivor(s) for s in ranked_survivors],
        "near_misses_top10_ranked_by_fewest_failed_gates": near_misses,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--starting-head", required=True, help="Git commit SHA the replay started from (recorded verbatim in the sanitized output for provenance).")
    args = ap.parse_args()

    corpus_dir = Path(args.corpus_dir)
    analysis = json.loads((corpus_dir / "corpus_analysis.local.json").read_text(encoding="utf-8"))
    corpus_track_count = len(analysis)

    v1 = replay_category("V1", analysis)
    v2 = replay_category("V2", analysis)

    result = "REAL_RENDER_CANDIDATE_RECOVERED" if (v1["strict_full_dj_survivor_count"] > 0 or v2["strict_full_dj_survivor_count"] > 0) else "R3_FINAL_PARTIAL_NO_VALID_V1_V2"

    out = {
        "starting_head": args.starting_head,
        "corpus_track_count": corpus_track_count,
        "candidate_universe_construction": "REUSED_VERBATIM_FROM_select_real_music_pairs.py_AND_pair_gate_audit.py",
        "no_source_audio_decoded_this_pass": True,
        "no_corpus_wide_analyzer_rerun_this_pass": True,
        "alignment_anchor_evidence_consumed": {
            "mechanism": "select_real_music_pairs.alignment_anchor_fields -- generic per-track beat/downbeat confidence, applied identically to every candidate, no RM-id-specific override",
            "rm014_diagnostic_numeric_anchor_injected": False,
            "provenance": "docs/research/P0-M3-R3-RM014-ENTRY-ANCHOR-FEASIBILITY.md result SEPARATE_ENTRY_AND_ALIGNMENT_ANCHOR_JUSTIFIED is architectural motivation only; its specific candidate timestamps were never promoted to a production value and are NOT read by this script",
        },
        "no_evidence_promotion_declaration": "Diagnostic-only evidence (All-In-One functional/downbeat outputs, madmom oracle outputs) was NOT promoted to canonical HIGH this pass. analysis_confidence, beat/downbeat confidence, and every compatibility.py gate are computed by the SAME unmodified evaluator used before this task.",
        "V1": v1,
        "V2": v2,
        "result": result,
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"V1: total={v1['total_pair_universe']} tempo_eligible={v1['tempo_eligible_universe']} strict_survivors={v1['strict_full_dj_survivor_count']}")
    print(f"V2: total={v2['total_pair_universe']} tempo_eligible={v2['tempo_eligible_universe']} strict_survivors={v2['strict_full_dj_survivor_count']}")
    print(f"RESULT: {result}")
    print(f"Wrote sanitized replay evidence to {args.out}")


if __name__ == "__main__":
    main()
