"""
PM OWNER LISTENING DIRECTION UPDATE -- "LOUDNESS / ENERGY CONTINUITY
REPAIR". Renders 4 gain-curve variants per scenario on the DIAGNOSTIC
(marker-embedded) audio, using the planner-correct boundary (same as
every other method), and computes the new time-series loudness
diagnostics (dsp/loudness_diagnostics.py) on each so the curves can be
compared on genuine evidence, not assumption.

Variants:
  LA -- current equal-power reference (identical policy to M1)
  LB -- late-outgoing-hold (dsp.mixing.late_outgoing_hold_gains)
  LC -- equal-power + energy-aware makeup gain (dsp.mixing.energy_aware_makeup_db)
  LD -- late-outgoing-hold + energy-aware makeup (combined -- PM's "D. optional" slot)

Gain curves only (no bass-handoff, no tempo correction) -- isolates the
gain-curve variable exactly as M1 does for the render-method shootout, so
the loudness comparison is not confounded by stretch-engine differences.

Usage:
    python scripts/render_loudness_shootout.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsp.wav_io import write_wav_float32  # noqa: E402
from dsp.mixing import assemble_transition_render, apply_headroom_and_safety  # noqa: E402
from dsp.render_common import load_scenario_context, compute_segments, fit_exact_length  # noqa: E402
from dsp.loudness_diagnostics import compute_transition_loudness_diagnostics  # noqa: E402

OUT_DIR = ROOT / "results" / "loudness_shootout"
OUT_META_DIR = ROOT / "results" / "loudness_shootout_meta"

VARIANTS = {
    "LA": {"curve": "equal_power", "energy_aware": False, "label": "current_equal_power_reference"},
    "LB": {"curve": "late_hold", "energy_aware": False, "label": "late_outgoing_hold"},
    "LC": {"curve": "equal_power", "energy_aware": True, "label": "energy_aware_makeup"},
    "LD": {"curve": "late_hold", "energy_aware": True, "label": "late_hold_plus_energy_aware"},
}

SCENARIOS = ["R3-A", "R3-B", "R3-C"]


def render_variant(transition_id: str, variant_id: str, cfg: dict):
    ctx = load_scenario_context(transition_id, variant="diagnostic")
    segs = compute_segments(ctx)
    sr = segs["sr"]
    overlap_len = segs["overlap_len_smp"]
    incoming_overlap = fit_exact_length(segs["incoming_raw_segment"][:overlap_len], overlap_len)
    incoming_post = segs["incoming_raw_segment"][overlap_len:]

    rendered = assemble_transition_render(
        segs["outgoing_pre"], segs["outgoing_overlap"], incoming_overlap, incoming_post,
        sr, use_equal_power=True, use_bass_handoff=False,
        curve=cfg["curve"], energy_aware=cfg["energy_aware"],
    )
    safe_audio, safety_diag = apply_headroom_and_safety(rendered)

    pre_roll_len = segs["onset_smp"] - max(0, segs["onset_smp"] - int(round(15.0 * sr)))
    content_end_render_smp = pre_roll_len + overlap_len
    loudness_diag = compute_transition_loudness_diagnostics(safe_audio, sr, pre_roll_len, content_end_render_smp)

    from dsp.mixing import energy_aware_makeup_db
    makeup_db = energy_aware_makeup_db(segs["outgoing_overlap"], incoming_overlap, sr=sr) if cfg["energy_aware"] else 0.0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_META_DIR.mkdir(parents=True, exist_ok=True)
    write_wav_float32(OUT_DIR / f"{transition_id}_{variant_id}.wav", safe_audio, sr)

    meta = {
        "transition_id": transition_id,
        "variant_id": variant_id,
        "variant_label": cfg["label"],
        "curve": cfg["curve"],
        "energy_aware": cfg["energy_aware"],
        "applied_energy_aware_makeup_db": round(makeup_db, 3),
        "onset_ms": segs["onset_ms"],
        "content_end_ms": segs["content_end_ms"],
        "overlap_len_samples": overlap_len,
        "safety": safety_diag,
        "loudness": loudness_diag,
    }
    (OUT_META_DIR / f"{transition_id}_{variant_id}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    dip = loudness_diag["maximum_loudness_dip_db"]
    rise = loudness_diag["maximum_loudness_rise_db"]
    print(f"{transition_id} {variant_id} ({cfg['label']}): max_dip={dip} max_rise={rise} "
          f"handoff_start={loudness_diag['handoff_loudness_delta_db_at_overlap_start']} "
          f"handoff_end={loudness_diag['handoff_loudness_delta_db_at_overlap_end']} "
          f"makeup_db={round(makeup_db,2)} clip={safety_diag['clipped_sample_count']} peak_dbfs={safety_diag['post_peak_dbfs']:.2f}")


def main():
    for tid in SCENARIOS:
        for variant_id, cfg in VARIANTS.items():
            render_variant(tid, variant_id, cfg)


if __name__ == "__main__":
    main()
