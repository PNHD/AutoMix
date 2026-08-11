# P0-M3-R2 Benchmark Run -- SUMMARY

Denominators: trap_fixtures=9 (['TP-01', 'TP-02', 'TP-03', 'TP-04', 'TP-05', 'TP-06', 'TP-07', 'TP-08', 'TP-09']), valid_fixtures=10, missed_opportunity_fixtures=6 (['TP-02', 'TP-03', 'TP-04', 'TP-07', 'TP-08', 'TP-10'])

| Policy@Intent | premature_exit_rate | valid_late_exit_capture_rate | missed_opportunity_rate | wrong_class_rate | fallback_rate | mean_fraction_preserved |
|---|---|---|---|---|---|---|
| NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT | 9/9 | 1/10 | 5/6 | 10/10 | 0/10 | 0.2776 |
| BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT | 7/9 | 3/10 | 3/6 | 0/10 | 0/10 | 0.3655 |
| TAIL_ONLY_NATURAL_EXIT_BIASED@FULL_SONG_DEFAULT | 0/9 | 10/10 | 4/6 | 0/2 | 8/10 | 0.9868 |
| STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT | 0/9 | 10/10 | 2/6 | 0/4 | 6/10 | 0.887 |
| STRUCTURE_AWARE_PRESERVATION@BALANCED_MIX | 0/9 | 10/10 | 1/6 | 0/5 | 5/10 | 0.8345 |
| EXPLICIT_HIGHLIGHT@HIGHLIGHT_EXPLICIT | 0/9 | 10/10 | 0/6 | 0/6 | 4/10 | 0.7554 |

## Sensitivity sweep -- STRUCTURE_AWARE_PRESERVATION@FULL_SONG_DEFAULT

| fraction_floor | premature_exit_rate | missed_opportunity_rate | fallback_rate |
|---|---|---|---|
| 0.15 | 0/9 | 0/6 | 0.4 |
| 0.3 | 0/9 | 1/6 | 0.5 |
| 0.45 | 0/9 | 2/6 | 0.6 |
| 0.55 | 0/9 | 3/6 | 0.7 |
| 0.7 | 0/9 | 4/6 | 0.8 |
| 0.85 | 0/9 | 4/6 | 0.8 |

premature_exit_rate is 0/9 at every threshold in this sweep, including the most permissive (0.15) -- because the structural-evidence guard (Task B guard 3) is independent of the fraction floor and already excludes every is_premature_trap/is_vocal_collision_trap candidate in the fixture set regardless of elapsed time or fraction. This is the direct evidence for AC5: no single elapsed-time/fraction threshold is, by itself, the premature-exit guard. Contrast with BPM_KEY_ONLY_EARLY@FULL_SONG_DEFAULT and NAIVE_EARLIEST_COMPATIBLE@FULL_SONG_DEFAULT in metrics.json, which have no structural-evidence guard at all and show a nonzero premature_exit_rate even though they also use a fraction/time floor (0.10 and 0.0 respectively) -- proving the floor alone, without the structural gate, does not prevent the owner's observed failure class.
