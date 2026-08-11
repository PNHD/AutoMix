# P0-M3-R1 analyzer shootout -- machine-generated summary

Fixtures: 8. Raw runs: 40. Scored: 40.

| candidate | fixture | run_state | total_call_wall_sec | error |
|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | OK | 10.4653 |  |
| beatnet | FIX-B-half-beat-phase-offset | OK | 0.2819 |  |
| beatnet | FIX-C-wrong-downbeat-phase | OK | 0.3299 |  |
| beatnet | FIX-D-4-4-reference | OK | 0.2391 |  |
| beatnet | FIX-E-non-4-4-waltz | OK | 0.3719 |  |
| beatnet | FIX-F-8bar-16bar-sections | OK | 0.6767 |  |
| beatnet | FIX-G-intro-body-outro-energy | OK | 0.805 |  |
| beatnet | FIX-H-variable-tempo-ramp | OK | 0.7635 |  |
| cue_detr | FIX-A-constant-120bpm-4-4 | OK | 6.6902 |  |
| cue_detr | FIX-B-half-beat-phase-offset | OK | 2.165 |  |
| cue_detr | FIX-C-wrong-downbeat-phase | OK | 2.6605 |  |
| cue_detr | FIX-D-4-4-reference | OK | 2.3149 |  |
| cue_detr | FIX-E-non-4-4-waltz | OK | 2.6068 |  |
| cue_detr | FIX-F-8bar-16bar-sections | OK | 4.1807 |  |
| cue_detr | FIX-G-intro-body-outro-energy | OK | 3.9152 |  |
| cue_detr | FIX-H-variable-tempo-ramp | OK | 3.1768 |  |
| energy_onset_heuristic_baseline | FIX-A-constant-120bpm-4-4 | OK | 0.055840400000306545 |  |
| energy_onset_heuristic_baseline | FIX-B-half-beat-phase-offset | OK | 0.051339800000278046 |  |
| energy_onset_heuristic_baseline | FIX-C-wrong-downbeat-phase | OK | 0.061729899996862514 |  |
| energy_onset_heuristic_baseline | FIX-D-4-4-reference | OK | 0.04407519999949727 |  |
| energy_onset_heuristic_baseline | FIX-E-non-4-4-waltz | OK | 0.06751509999958216 |  |
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | OK | 0.1634522000022116 |  |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | OK | 0.16038660000049276 |  |
| energy_onset_heuristic_baseline | FIX-H-variable-tempo-ramp | OK | 0.11549699999886798 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-A-constant-120bpm-4-4 | OK | 8.999999408842996e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-B-half-beat-phase-offset | OK | 6.599999323952943e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-C-wrong-downbeat-phase | OK | 6.000002031214535e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-D-4-4-reference | OK | 6.099999154685065e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-E-non-4-4-waltz | OK | 6.199999916134402e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | OK | 1.7399997886968777e-05 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-G-intro-body-outro-energy | OK | 6.400001439033076e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-H-variable-tempo-ramp | OK | 7.499998901039362e-06 |  |
| scalar_bpm_grid_baseline | FIX-A-constant-120bpm-4-4 | OK | 4.27999984822236e-05 |  |
| scalar_bpm_grid_baseline | FIX-B-half-beat-phase-offset | OK | 3.149999974993989e-05 |  |
| scalar_bpm_grid_baseline | FIX-C-wrong-downbeat-phase | OK | 3.229999856557697e-05 |  |
| scalar_bpm_grid_baseline | FIX-D-4-4-reference | OK | 3.270000161137432e-05 |  |
| scalar_bpm_grid_baseline | FIX-E-non-4-4-waltz | OK | 3.1299998227041215e-05 |  |
| scalar_bpm_grid_baseline | FIX-F-8bar-16bar-sections | OK | 0.00016589999722782522 |  |
| scalar_bpm_grid_baseline | FIX-G-intro-body-outro-energy | OK | 6.280000161495991e-05 |  |
| scalar_bpm_grid_baseline | FIX-H-variable-tempo-ramp | OK | 7.249999907799065e-05 |  |

## Canonical (fresh-per-call, PM REVIEW #2 R8) runtime lifecycle / memory / model-size

| candidate | fixture | estimator_lifecycle | model_load_wall_sec | asset_fetch_wall_sec | inference_wall_sec | total_call_wall_sec | process_peak_rss_mb | python_tracemalloc_peak_mb | memory_measurement_method | checkpoint_size_mb | total_model_asset_footprint_mb |
|---|---|---|---|---|---|---|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | FRESH_PER_CALL | 4.034 | None | 6.4313 | 10.4653 | 450.87 | 101.99 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-B-half-beat-phase-offset | FRESH_PER_CALL | 0.0138 | None | 0.2681 | 0.2819 | 450.87 | 36.46 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-C-wrong-downbeat-phase | FRESH_PER_CALL | 0.0192 | None | 0.3107 | 0.3299 | 450.87 | 45.48 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-D-4-4-reference | FRESH_PER_CALL | 0.0151 | None | 0.224 | 0.2391 | 450.87 | 33.23 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-E-non-4-4-waltz | FRESH_PER_CALL | 0.0205 | None | 0.3514 | 0.3719 | 450.87 | 50.2 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-F-8bar-16bar-sections | FRESH_PER_CALL | 0.0137 | None | 0.663 | 0.6767 | 547.79 | 116.35 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-G-intro-body-outro-energy | FRESH_PER_CALL | 0.0127 | None | 0.7923 | 0.805 | 547.79 | 108.1 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| beatnet | FIX-H-variable-tempo-ramp | FRESH_PER_CALL | 0.0136 | None | 0.7499 | 0.7635 | 547.79 | 77.79 | PSUTIL_PROCESS_PEAK_WSET_RSS | 1.54 | 1.54 |
| cue_detr | FIX-A-constant-120bpm-4-4 | FRESH_PER_CALL | 1.5013 | None | 5.1889 | 6.6902 | 944.77 | 66.26 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-B-half-beat-phase-offset | FRESH_PER_CALL | 1.1532 | None | 1.0118 | 2.165 | 944.77 | 29.92 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-C-wrong-downbeat-phase | FRESH_PER_CALL | 1.1531 | None | 1.5074 | 2.6605 | 979.31 | 33.86 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-D-4-4-reference | FRESH_PER_CALL | 1.1133 | None | 1.2016 | 2.3149 | 984.0 | 26.06 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-E-non-4-4-waltz | FRESH_PER_CALL | 1.0933 | None | 1.5135 | 2.6068 | 995.61 | 37.75 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-F-8bar-16bar-sections | FRESH_PER_CALL | 1.1509 | None | 3.0298 | 4.1807 | 1301.25 | 78.71 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-G-intro-body-outro-energy | FRESH_PER_CALL | 1.0768 | None | 2.8384 | 3.9152 | 1301.25 | 72.88 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| cue_detr | FIX-H-variable-tempo-ramp | FRESH_PER_CALL | 1.0549 | None | 2.1219 | 3.1768 | 1301.25 | 55.29 | PSUTIL_PROCESS_PEAK_WSET_RSS | 158.78 | 158.78 |
| energy_onset_heuristic_baseline | FIX-A-constant-120bpm-4-4 | N_A | None | None | None | 0.055840400000306545 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-B-half-beat-phase-offset | N_A | None | None | None | 0.051339800000278046 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-C-wrong-downbeat-phase | N_A | None | None | None | 0.061729899996862514 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-D-4-4-reference | N_A | None | None | None | 0.04407519999949727 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-E-non-4-4-waltz | N_A | None | None | None | 0.06751509999958216 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | N_A | None | None | None | 0.1634522000022116 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | N_A | None | None | None | 0.16038660000049276 | None | None | N_A | None | None |
| energy_onset_heuristic_baseline | FIX-H-variable-tempo-ramp | N_A | None | None | None | 0.11549699999886798 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-A-constant-120bpm-4-4 | N_A | None | None | None | 8.999999408842996e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-B-half-beat-phase-offset | N_A | None | None | None | 6.599999323952943e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-C-wrong-downbeat-phase | N_A | None | None | None | 6.000002031214535e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-D-4-4-reference | N_A | None | None | None | 6.099999154685065e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-E-non-4-4-waltz | N_A | None | None | None | 6.199999916134402e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | N_A | None | None | None | 1.7399997886968777e-05 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-G-intro-body-outro-energy | N_A | None | None | None | 6.400001439033076e-06 | None | None | N_A | None | None |
| fixed_32_beat_phrase_proxy_baseline | FIX-H-variable-tempo-ramp | N_A | None | None | None | 7.499998901039362e-06 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-A-constant-120bpm-4-4 | N_A | None | None | None | 4.27999984822236e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-B-half-beat-phase-offset | N_A | None | None | None | 3.149999974993989e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-C-wrong-downbeat-phase | N_A | None | None | None | 3.229999856557697e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-D-4-4-reference | N_A | None | None | None | 3.270000161137432e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-E-non-4-4-waltz | N_A | None | None | None | 3.1299998227041215e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-F-8bar-16bar-sections | N_A | None | None | None | 0.00016589999722782522 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-G-intro-body-outro-energy | N_A | None | None | None | 6.280000161495991e-05 | None | None | N_A | None | None |
| scalar_bpm_grid_baseline | FIX-H-variable-tempo-ramp | N_A | None | None | None | 7.249999907799065e-05 | None | None | N_A | None | None |

## Scored metrics

| candidate | fixture | beat_fraction_ok_rate | median_beat_frac_err | downbeat_within_10pct_bar | exact_bar_phase_acc | meter_correct | bpm_abs_err_pct |
|---|---|---|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | 1.0 | 0.04 | 1.0 | 1.0 | False | None |
| beatnet | FIX-B-half-beat-phase-offset | 1.0 | 0.029866666666666666 | 1.0 | 1.0 | False | None |
| beatnet | FIX-C-wrong-downbeat-phase | 1.0 | 0.03333333333333333 | 1.0 | 1.0 | False | None |
| beatnet | FIX-D-4-4-reference | 1.0 | 0.03266666666666667 | 0.9166666666666666 | 0.9166666666666666 | False | None |
| beatnet | FIX-E-non-4-4-waltz | 1.0 | 0.0195 | 0.5 | 0.5 | False | None |
| beatnet | FIX-F-8bar-16bar-sections | 1.0 | 0.023466666666666667 | 0.0 | 0.0 | False | None |
| beatnet | FIX-G-intro-body-outro-energy | 1.0 | 0.02383333333333333 | 1.0 | 1.0 | False | None |
| beatnet | FIX-H-variable-tempo-ramp | 1.0 | 0.026833333333333334 | 1.0 | 1.0 | False | None |
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

## CUE-DETR score/validation fields (PM REPAIR R5, PM REVIEW #2 R10 -- validated = raw predictions FILTERED to [0,duration_ms], never clamped)

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
