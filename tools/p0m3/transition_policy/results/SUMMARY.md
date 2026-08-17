# P0-M3-R2 Apple-like Benchmark Run -- SUMMARY

Denominators: trap_fixtures=10 (['TP-01', 'TP-02', 'TP-03', 'TP-04', 'TP-05', 'TP-06', 'TP-07', 'TP-08', 'TP-09', 'TP-11']), valid_fixtures=14, missed_opportunity_fixtures=9 (['TP-02', 'TP-03', 'TP-04', 'TP-08', 'TP-10', 'TP-11', 'TP-12', 'TP-13', 'TP-14'])

| Policy@Intent | premature_exit_rate | valid_late_exit_capture_rate | missed_opportunity_rate | forced_FULL_DJ_BLEND_rate | fallback_rate | mean_preservation_ratio |
|---|---|---|---|---|---|---|
| NAIVE_EARLIEST_COMPATIBLE@SEAMLESS_FULL_TRACK_DEFAULT | 10/10 | 4/14 | 6/9 | 0/14 | 0/14 | 0.4 |
| BPM_KEY_ONLY_EARLY@SEAMLESS_FULL_TRACK_DEFAULT | 8/10 | 4/14 | 6/9 | 0/14 | 0/14 | 0.4628 |
| TAIL_ONLY_NATURAL_EXIT_BIASED@SEAMLESS_FULL_TRACK_DEFAULT | 0/10 | 14/14 | 3/9 | 0/7 | 7/14 | 0.9465 |
| FIXED_SECONDS_BEFORE_END_ONLY@SEAMLESS_FULL_TRACK_DEFAULT | 0/10 | 14/14 | 5/9 | 0/5 | 9/14 | 0.9702 |
| SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT **<- RECOMMENDED** | 0/10 | 14/14 | 1/9 | 0/8 | 6/14 | 0.9981 |
| BALANCED_MIX_RESEARCH_CONTROL@BALANCED_MIX | 0/10 | 13/14 | 1/9 | 0/9 | 5/14 | 0.9749 |
| EXPLICIT_HIGHLIGHT_RESEARCH_CONTROL@HIGHLIGHT_EXPLICIT | 0/10 | 12/14 | 2/9 | 0/10 | 4/14 | 0.9049 |

## Sensitivity sweep -- SEAMLESS_FULL_TRACK_DEFAULT@SEAMLESS_FULL_TRACK_DEFAULT

| preservation_floor | band | premature_exit_rate | missed_opportunity_rate | fallback_rate |
|---|---|---|---|---|
| 0.9 | at_catastrophic_ceiling | 0/10 | 1/9 | 0.4286 |
| 0.93 | at_catastrophic_ceiling | 0/10 | 1/9 | 0.4286 |
| 0.95 | acceptable_p0_default_candidate_band | 0/10 | 1/9 | 0.4286 |
| 0.97 | preferred_band_lower_bound | 0/10 | 1/9 | 0.4286 |
| 0.98 | preferred_band | 0/10 | 2/9 | 0.5 |

premature_exit_rate is 0/9 at every tested floor from 0.90 to 0.98, including the strict catastrophic ceiling itself (0.90) -- because the structural-evidence guard (eligibility guard 3) and vocal-collision guard (guard 1) are independent of the preservation floor and already exclude every is_premature_trap/is_vocal_collision_trap candidate regardless of elapsed time or preservation ratio. This is the direct evidence that no single preservation-ratio threshold is, by itself, the premature-exit guard -- contrast with NAIVE_EARLIEST_COMPATIBLE and BPM_KEY_ONLY_EARLY in metrics.json, which have no structural-evidence guard at all and show nonzero premature_exit_rate. Missed-transition-opportunity rate is monitored across the same sweep to show the floor's effect on capture, separate from safety.

## Multi-candidate order invariance (TP-12)

normal=TP-12-Y reversed=TP-12-Y shuffled=TP-12-Y -> order_invariant=True

## Pair compatibility gate

incompatible_pair_downgrade_rate=0.7692 (10/13)

| Pair | Letter | Expected eligible | Computed eligible | Matches | TP-11+pair: FULL_DJ_BLEND offered |
|---|---|---|---|---|---|
| PAIR-01 | G | True | True | True | True |
| PAIR-02 | H | False | False | True | False |
| PAIR-03 | I | False | False | True | False |
| PAIR-04 | J | False | False | True | False |
| PAIR-05 | K | True | True | True | True |
| PAIR-06 | R4 | False | False | True | False |
| PAIR-07 | R4 | False | False | True | False |
| PAIR-08 | R4 | False | False | True | False |
| PAIR-09 | R4 | True | True | True | True |
| PAIR-10 | R4 | False | False | True | False |
| PAIR-11 | R7 | False | False | True | False |
| PAIR-12 | R7 | False | False | True | False |
| PAIR-13 | R7 | False | False | True | False |

## PM REVIEW #2 -- complete boundary-plan results (TX-01..08)

| Transition | Expected winner | Selected winner | Matches |
|---|---|---|---|
| TX-01 | TX01-OUT-B + TX01-IN-2 | TX01-OUT-B + TX01-IN-2 | True |
| TX-02 | TX02-OUT-1 + TX02-IN-ZERO | TX02-OUT-1 + TX02-IN-ZERO | True |
| TX-03 | TX03-OUT-1 + TX03-IN-SKIP | TX03-OUT-1 + TX03-IN-SKIP | True |
| TX-04 | TX04-OUT-1 + TX04-IN-CUE | TX04-OUT-1 + TX04-IN-CUE | True |
| TX-05 | TX05-OUT-1 + TX05-IN-B | TX05-OUT-1 + TX05-IN-B | True |
| TX-06 | TX06-OUT-1 + TX06-IN-ZERO-ANCHORED | TX06-OUT-1 + TX06-IN-ZERO-ANCHORED | True |
| TX-07 | TX07-OUT-B + TX07-IN-1 | TX07-OUT-B + TX07-IN-1 | True |
| TX-08 | TX08-OUT-1 + TX08-IN-ZERO-SEPARATE-ANCHOR | TX08-OUT-1 + TX08-IN-ZERO-SEPARATE-ANCHOR | True |

TX-01 order invariance (exit array x entry array, 5 orderings): order_invariant=True

## R4 -- UNKNOWN structure/texture/harmonic mutation tests

| Pair | Expected eligible | Computed eligible | Matches |
|---|---|---|---|
| PAIR-06 | False | False | True |
| PAIR-07 | False | False | True |
| PAIR-08 | False | False | True |
| PAIR-09 | True | True | True |
| PAIR-10 | False | False | True |
