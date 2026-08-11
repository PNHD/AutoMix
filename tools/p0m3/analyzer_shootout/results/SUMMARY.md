# P0-M3-R1 analyzer shootout -- machine-generated summary

Fixtures: 8. Raw runs: 40. Scored: 40.

| candidate | fixture | run_state | wall_time_s | error |
|---|---|---|---|---|
| beatnet | FIX-A-constant-120bpm-4-4 | OK | 12.7042 |  |
| beatnet | FIX-B-half-beat-phase-offset | OK | 0.2979 |  |
| beatnet | FIX-C-wrong-downbeat-phase | OK | 0.3479 |  |
| beatnet | FIX-D-4-4-reference | OK | 0.2595 |  |
| beatnet | FIX-E-non-4-4-waltz | OK | 0.3728 |  |
| beatnet | FIX-F-8bar-16bar-sections | OK | 0.7381 |  |
| beatnet | FIX-G-intro-body-outro-energy | OK | 0.6972 |  |
| beatnet | FIX-H-variable-tempo-ramp | OK | 0.5416 |  |
| cue_detr | FIX-A-constant-120bpm-4-4 | OK | 11.2251 |  |
| cue_detr | FIX-B-half-beat-phase-offset | OK | 1.5918 |  |
| cue_detr | FIX-C-wrong-downbeat-phase | OK | 1.6044 |  |
| cue_detr | FIX-D-4-4-reference | OK | 1.7476 |  |
| cue_detr | FIX-E-non-4-4-waltz | OK | 1.8901 |  |
| cue_detr | FIX-F-8bar-16bar-sections | OK | 3.8741 |  |
| cue_detr | FIX-G-intro-body-outro-energy | OK | 4.3144 |  |
| cue_detr | FIX-H-variable-tempo-ramp | OK | 3.1413 |  |
| energy_onset_heuristic_baseline | FIX-A-constant-120bpm-4-4 | OK | 0.04946200000267709 |  |
| energy_onset_heuristic_baseline | FIX-B-half-beat-phase-offset | OK | 0.039167599999927916 |  |
| energy_onset_heuristic_baseline | FIX-C-wrong-downbeat-phase | OK | 0.04909939999924973 |  |
| energy_onset_heuristic_baseline | FIX-D-4-4-reference | OK | 0.03606899999795132 |  |
| energy_onset_heuristic_baseline | FIX-E-non-4-4-waltz | OK | 0.05453010000201175 |  |
| energy_onset_heuristic_baseline | FIX-F-8bar-16bar-sections | OK | 0.12454000000070664 |  |
| energy_onset_heuristic_baseline | FIX-G-intro-body-outro-energy | OK | 0.10691070000029868 |  |
| energy_onset_heuristic_baseline | FIX-H-variable-tempo-ramp | OK | 0.07695810000222991 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-A-constant-120bpm-4-4 | OK | 5.300000339047983e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-B-half-beat-phase-offset | OK | 6.000002031214535e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-C-wrong-downbeat-phase | OK | 1.0399999155197293e-05 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-D-4-4-reference | OK | 8.499999239575118e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-E-non-4-4-waltz | OK | 4.999998054699972e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-F-8bar-16bar-sections | OK | 6.70000008540228e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-G-intro-body-outro-energy | OK | 6.199999916134402e-06 |  |
| fixed_32_beat_phrase_proxy_baseline | FIX-H-variable-tempo-ramp | OK | 5.999998393235728e-06 |  |
| scalar_bpm_grid_baseline | FIX-A-constant-120bpm-4-4 | OK | 4.3799998820759356e-05 |  |
| scalar_bpm_grid_baseline | FIX-B-half-beat-phase-offset | OK | 3.130000186502002e-05 |  |
| scalar_bpm_grid_baseline | FIX-C-wrong-downbeat-phase | OK | 5.160000000614673e-05 |  |
| scalar_bpm_grid_baseline | FIX-D-4-4-reference | OK | 5.6000000768108293e-05 |  |
| scalar_bpm_grid_baseline | FIX-E-non-4-4-waltz | OK | 3.070000093430281e-05 |  |
| scalar_bpm_grid_baseline | FIX-F-8bar-16bar-sections | OK | 0.0001100999979826156 |  |
| scalar_bpm_grid_baseline | FIX-G-intro-body-outro-energy | OK | 6.779999966965988e-05 |  |
| scalar_bpm_grid_baseline | FIX-H-variable-tempo-ramp | OK | 6.629999916185625e-05 |  |

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
