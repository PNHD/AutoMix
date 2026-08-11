# P0-M3-R1 analyzer shootout -- machine-generated summary

Fixtures: 8. Raw runs: 40. Scored: 40.

| candidate | fixture | run_state | wall_time_s | error |
|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | OK | 22.4525 |  |
| beatnet | FIX-B-half-beat-phase-offset | OK | 0.2084 |  |
| beatnet | FIX-C-wrong-downbeat-phase | OK | 0.3604 |  |
| beatnet | FIX-D-4-4-reference | OK | 0.2275 |  |
| beatnet | FIX-E-non-4-4-waltz | OK | 0.4029 |  |
| beatnet | FIX-F-8bar-16bar-sections | OK | 0.7728 |  |
| beatnet | FIX-G-intro-body-outro-energy | OK | 0.6502 |  |
| beatnet | FIX-H-variable-tempo-ramp | OK | 0.5022 |  |
| cue_detr | FIX-A-constant-120bpm-4-4 | OK | 6.7223 |  |
| cue_detr | FIX-B-half-beat-phase-offset | OK | 1.3141 |  |
| cue_detr | FIX-C-wrong-downbeat-phase | OK | 1.6259 |  |
| cue_detr | FIX-D-4-4-reference | OK | 1.0998 |  |
| cue_detr | FIX-E-non-4-4-waltz | OK | 1.708 |  |
| cue_detr | FIX-F-8bar-16bar-sections | OK | 3.84 |  |
| cue_detr | FIX-G-intro-body-outro-energy | OK | 3.5017 |  |
| cue_detr | FIX-H-variable-tempo-ramp | OK | 2.4971 |  |
| energy_onset_heuristic_baseline | FIX-A-constant-120bpm-4-4 | OK | 0.04889360000015586 |  |
| energy_onset_heuristic_baseline | FIX-B-half-beat-phase-offset | OK | 0.05573119999826304 |  |
| energy_onset_heuristic_baseline | FIX-C-wrong-downbeat-phase | OK | 0.07771860000138986 |  |
| energy_onset_heuristic_baseline | FIX-D-4-4-reference | OK | 0.04840159999730531 |  |
| energy_onset_heuristic_baseline | FIX-E-non-4-4-waltz | OK | 0.06781839999894146 |  |
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | OK | 0.15258220000032452 |  |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | OK | 0.1286863000023004 |  |
| energy_onset_heuristic_baseline | FIX-H-variable-tempo-ramp | OK | 0.09669980000035139 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-A-constant-120bpm-4-4 | OK | 5.699999746866524e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-B-half-beat-phase-offset | OK | 8.099999831756577e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-C-wrong-downbeat-phase | OK | 8.099999831756577e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-D-4-4-reference | OK | 8.400002116104588e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-E-non-4-4-waltz | OK | 5.799996870337054e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | OK | 6.499998562503606e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-G-intro-body-outro-energy | OK | 8.999999408842996e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-H-variable-tempo-ramp | OK | 7.099999493220821e-06 |  |
| scalar_bpm_grid_baseline | FIX-A-constant-120bpm-4-4 | OK | 4.220000118948519e-05 |  |
| scalar_bpm_grid_baseline | FIX-B-half-beat-phase-offset | OK | 6.319999738479964e-05 |  |
| scalar_bpm_grid_baseline | FIX-C-wrong-downbeat-phase | OK | 5.830000009154901e-05 |  |
| scalar_bpm_grid_baseline | FIX-D-4-4-reference | OK | 4.740000076708384e-05 |  |
| scalar_bpm_grid_baseline | FIX-E-non-4-4-waltz | OK | 3.1500003387918696e-05 |  |
| scalar_bpm_grid_baseline | FIX-F-8bar-16bar-sections | OK | 7.829999958630651e-05 |  |
| scalar_bpm_grid_baseline | FIX-G-intro-body-outro-energy | OK | 0.00013800000306218863 |  |
| scalar_bpm_grid_baseline | FIX-H-variable-tempo-ramp | OK | 5.4299998737405986e-05 |  |

## Runtime lifecycle / memory / model-size (PM REPAIR R1)

| candidate | fixture | run_phase | asset_fetch_wall_sec | wall_time_sec | process_peak_rss_mb | python_tracemalloc_peak_mb | memory_measurement_method | checkpoint_size_mb | total_model_asset_footprint_mb |
|---|---|---|---|---|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | COLD_MODEL_LOAD_INFERENCE | 0.0732 | 22.4525 | 544.84 | 185.42 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-B-half-beat-phase-offset | WARM_INFERENCE | None | 0.2084 | 544.84 | 35.82 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-C-wrong-downbeat-phase | WARM_INFERENCE | None | 0.3604 | 544.84 | 44.99 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-D-4-4-reference | WARM_INFERENCE | None | 0.2275 | 544.84 | 32.75 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-E-non-4-4-waltz | WARM_INFERENCE | None | 0.4029 | 544.84 | 49.71 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-F-8bar-16bar-sections | WARM_INFERENCE | None | 0.7728 | 597.07 | 115.8 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-G-intro-body-outro-energy | WARM_INFERENCE | None | 0.6502 | 597.07 | 107.56 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-H-variable-tempo-ramp | WARM_INFERENCE | None | 0.5022 | 597.07 | 77.3 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| cue_detr | FIX-A-constant-120bpm-4-4 | COLD_MODEL_LOAD_INFERENCE | 1.6332 | 6.7223 | 926.72 | 72.73 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-B-half-beat-phase-offset | WARM_INFERENCE | None | 1.3141 | 926.72 | 33.57 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-C-wrong-downbeat-phase | WARM_INFERENCE | None | 1.6259 | 926.72 | 38.41 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-D-4-4-reference | WARM_INFERENCE | None | 1.0998 | 926.72 | 29.4 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-E-non-4-4-waltz | WARM_INFERENCE | None | 1.708 | 926.72 | 42.76 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-F-8bar-16bar-sections | WARM_INFERENCE | None | 3.84 | 1263.85 | 90.06 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-G-intro-body-outro-energy | WARM_INFERENCE | None | 3.5017 | 1263.85 | 83.46 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-H-variable-tempo-ramp | WARM_INFERENCE | None | 2.4971 | 1263.85 | 62.94 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| energy_onset_heuristic_baseline | FIX-A-constant-120bpm-4-4 | N_A | None | 0.04889360000015586 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-B-half-beat-phase-offset | N_A | None | 0.05573119999826304 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-C-wrong-downbeat-phase | N_A | None | 0.07771860000138986 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-D-4-4-reference | N_A | None | 0.04840159999730531 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-E-non-4-4-waltz | N_A | None | 0.06781839999894146 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | N_A | None | 0.15258220000032452 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | N_A | None | 0.1286863000023004 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-H-variable-tempo-ramp | N_A | None | 0.09669980000035139 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-A-constant-120bpm-4-4 | N_A | None | 5.699999746866524e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-B-half-beat-phase-offset | N_A | None | 8.099999831756577e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-C-wrong-downbeat-phase | N_A | None | 8.099999831756577e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-D-4-4-reference | N_A | None | 8.400002116104588e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-E-non-4-4-waltz | N_A | None | 5.799996870337054e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | N_A | None | 6.499998562503606e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-G-intro-body-outro-energy | N_A | None | 8.999999408842996e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-H-variable-tempo-ramp | N_A | None | 7.099999493220821e-06 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-A-constant-120bpm-4-4 | N_A | None | 4.220000118948519e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-B-half-beat-phase-offset | N_A | None | 6.319999738479964e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-C-wrong-downbeat-phase | N_A | None | 5.830000009154901e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-D-4-4-reference | N_A | None | 4.740000076708384e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-E-non-4-4-waltz | N_A | None | 3.1500003387918696e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-F-8bar-16bar-sections | N_A | None | 7.829999958630651e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-G-intro-body-outro-energy | N_A | None | 0.00013800000306218863 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-H-variable-tempo-ramp | N_A | None | 5.4299998737405986e-05 | None | None | N_A | None | None |

## Scored metrics

| candidate | fixture | beat_fraction_ok_rate | median_beat_frac_err | downbeat_within_10pct_bar | exact_bar_phase_acc | meter_correct | bpm_abs_err_pct |
|---|---|---|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | 1.0 | 0.04 | 1.0 | 1.0 | False | None |
| beatnet | FIX-B-half-beat-phase-offset | 1.0 | 0.029866666666666666 | 1.0 | 1.0 | False | None |
| beatnet | FIX-C-wrong-downbeat-phase | 1.0 | 0.03333333333333333 | 1.0 | 1.0 | False | None |
| beatnet | FIX-D-4-4-reference | 1.0 | 0.03266666666666667 | 0.9166666666666666 | 0.9166666666666666 | False | None |
| beatnet | FIX-E-non-4-4-waltz | 1.0 | 0.0195 | 0.5 | 0.5625 | False | None |
| beatnet | FIX-F-8bar-16bar-sections | 1.0 | 0.023466666666666667 | 0.0 | 0.025 | False | None |
| beatnet | FIX-G-intro-body-outro-energy | 1.0 | 0.02383333333333333 | 0.96875 | 0.96875 | False | None |
| beatnet | FIX-H-variable-tempo-ramp | 0.9895833333333334 | 0.026833333333333334 | 0.9583333333333334 | 0.9583333333333334 | False | None |
| cue_detr | FIX-A-constant-120bpm-4-4 | None | None | None | None | None | None |
| cue_detr | FIX-B-half-beat-phase-offset | None | None | None | None | None | None |
| cue_detr | FIX-C-wrong-downbeat-phase | None | None | None | None | None | None |
| cue_detr | FIX-D-4-4-reference | None | None | None | None | None | None |
| cue_detr | FIX-E-non-4-4-waltz | None | None | None | None | None | None |
| cue_detr | FIX-F-8bar-16bar-sections | None | None | None | None | None | None |
| cue_detr | FIX-G-intro-body-outro-energy | None | None | None | None | None | None |
| cue_detr | FIX-H-variable-tempo-ramp | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-A-constant-120bpm-4-4 | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-B-half-beat-phase-offset | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-C-wrong-downbeat-phase | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-D-4-4-reference | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-E-non-4-4-waltz | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | None | None | None | None | None | None |
| energy_onset_heuristic_baseline | FIX-H-variable-tempo-ramp | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-A-constant-120bpm-4-4 | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-B-half-beat-phase-offset | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-C-wrong-downbeat-phase | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-D-4-4-reference | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-E-non-4-4-waltz | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-G-intro-body-outro-energy | None | None | None | None | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-H-variable-tempo-ramp | None | None | None | None | None | None |
| scalar_bpm_grid_baseline | FIX-A-constant-120bpm-4-4 | 1.0 | 0.0 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-B-half-beat-phase-offset | 0.0 | 0.4997333333333333 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-C-wrong-downbeat-phase | 1.0 | 0.0 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-D-4-4-reference | 1.0 | 0.0006673333333334692 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-E-non-4-4-waltz | 1.0 | 0.0004994999999980792 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-F-8bar-16bar-sections | 1.0 | 0.0005333333333333334 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-G-intro-body-outro-energy | 1.0 | 0.0005005000000019208 | None | None | None | 0.0 |
| scalar_bpm_grid_baseline | FIX-H-variable-tempo-ramp | 0.125 | 0.27191750000000503 | None | None | None | 0.0 |

## Phrase/section boundary event metrics (PM REPAIR R2/R5, tolerance grounded in P0-M2 COND_PHRASE_OK / COND_SECTION_OK)

| candidate | fixture | kind | tolerance_ms | n_gt | n_pred | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | COND_SECTION_OK | 1875.0 | 4 | 4 | 3 | 1 | 1 | 0.75 | 0.75 | 0.75 |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | COND_SECTION_OK | 2181.818 | 3 | 5 | 2 | 3 | 1 | 0.4 | 0.6666666666666666 | 0.5 |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | COND_PHRASE_OK | 234.375 | 4 | 5 | 4 | 1 | 0 | 0.8 | 1.0 | 0.888888888888889 |

## CUE-DETR score/validation fields (PM REPAIR R5/R10)

| candidate | fixture | cue_score_kind | cue_confidence | n_raw | n_validated | n_invalid | invalid_raw_ms |
|---|---|---|---|---|---|---|---|
| cue_detr | FIX-A-constant-120bpm-4-4 | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 2 | 2 | 0 | [] |
| cue_detr | FIX-B-half-beat-phase-offset | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 1 | 1 | 0 | [] |
| cue_detr | FIX-C-wrong-downbeat-phase | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 1 | 1 | 0 | [] |
| cue_detr | FIX-D-4-4-reference | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 1 | 1 | 0 | [] |
| cue_detr | FIX-E-non-4-4-waltz | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 2 | 1 | 1 | [-139.3] |
| cue_detr | FIX-F-8bar-16bar-sections | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 1 | 0 | 1 | [-69.7] |
| cue_detr | FIX-G-intro-body-outro-energy | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 2 | 0 | 2 | [-46.4, 71842.5] |
| cue_detr | FIX-H-variable-tempo-ramp | MINMAX_NORMALIZED_DETR_DETECTION_SCORE | None | 1 | 1 | 0 | [] |
