# Results Summary

This page summarizes the current validated simulation outputs. The source tables are:

- `results/pipesense_results.csv`
- `results/adaptive_improvement.csv`
- `results/oracle_gap.csv`
- `results/hardware_cost_estimate.csv`
- `results/sweep_adaptive_vs_fixed.csv`
- `results/safety/fuzz_summary.csv`
- `results/synth/area_summary.csv`

The current HDL run contains 36 benchmark/mode rows, with zero timeouts and zero safety faults. `scripts/compare_reference.py` also matches HDL retired counts and final architectural data-state hashes against the sequential ISA reference model.

## Adaptive versus normal

| Benchmark | Normal cycles | Adaptive cycles | Cycle reduction | IPC improvement | Energy proxy reduction | Reconfigs | Reconfig penalty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic_heavy | 30 | 30 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| branch_heavy | 128 | 114 | 10.94% | 12.28% | 6.64% | 1 | 2 |
| memory_heavy | 231 | 201 | 12.99% | 14.92% | 15.68% | 6 | 28 |
| load_use_heavy | 205 | 178 | 13.17% | 15.17% | 7.64% | 1 | 4 |
| mixed_control | 131 | 127 | 3.05% | 3.14% | 2.28% | 1 | 4 |
| tiny_fir | 159 | 160 | -0.63% | -0.62% | 3.17% | 3 | 14 |

Interpretation: the adaptive controller improves over static normal mode on the phase-biased branch, memory, load-use, and mixed-control tests. It does not help arithmetic-heavy code, where normal execution is already close to suitable. On `tiny_fir`, adaptive mode slightly hurts cycles while still lowering the activity-energy proxy; this is useful negative evidence because it shows the controller can pay reconfiguration cost without enough cycle benefit.

## Oracle fixed-mode comparison

The oracle comparison asks whether adaptive mode approaches the best single fixed mode selected with hindsight. Negative gap values mean adaptive is worse than the oracle.

| Benchmark | Best fixed mode | Best fixed cycles | Adaptive cycles | Adaptive cycle gap | Best fixed energy | Adaptive energy | Adaptive energy gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic_heavy | fixed_hazard | 29 | 30 | -3.45% | 173 | 176 | -1.73% |
| branch_heavy | fixed_branch | 105 | 114 | -8.57% | 609 | 633 | -3.94% |
| memory_heavy | fixed_memory | 147 | 201 | -36.73% | 839 | 1038 | -23.72% |
| load_use_heavy | fixed_hazard | 169 | 178 | -5.33% | 1017 | 1039 | -2.16% |
| mixed_control | fixed_memory | 105 | 127 | -20.95% | 617 | 730 | -18.31% |
| tiny_fir | fixed_memory | 127 | 160 | -25.98% | 739 | 855 | -15.70% |

Interpretation: adaptive mode is meaningfully better than static normal mode, but it does not beat the best fixed-mode oracle. This should be framed as an early hardware-control prototype result, not as a final performance win. The largest gaps occur when memory mitigation dominates and the observer/controller does not move into, or stay in, memory-optimized mode early enough.

## Hardware-cost estimate

`scripts/estimate_hardware_cost.py` reports an analytical estimate only, not synthesis evidence. `scripts/synth_area_report.py` reports a Yosys generic-cell proxy when Yosys is installed; label that proxy carefully.

| Component | Estimated FF bits | Comparators | Adders | Notes |
| --- | ---: | ---: | ---: | --- |
| pipeline_observer | 228 | 5 | 7 | Seven 32-bit counters plus phase/window bits; excludes routing and threshold constants. |
| adaptive_controller | 31 | 4 | 2 | Residency counter, stable counter, desired/requested modes, and request state. |
| reconfig_unit | 104 | 2 | 3 | Mode registers, active counter, total reconfiguration count, and penalty counter. |
| safety_monitor_sim | 193 | 4 | 1 | Simulation/artifact monitor for instruction tags and safety faults; not part of a minimal synthesized design. |

## Figures

`scripts/plot_results.py` generates PNG plots when `matplotlib` is installed. In the current local environment, `matplotlib` is not installed, so the script wrote `results/plot_results.txt` as a text fallback.

Suggested paper figures:

- cycles by benchmark and mode
- IPC by benchmark and mode
- memory wait cycles by benchmark and mode
- load-use stalls by benchmark and mode
- reconfiguration penalty in adaptive mode
- activity-energy proxy by benchmark and mode
- adaptive gap to best fixed mode
- sensitivity of adaptive performance to observer window and residency
- sensitivity of adaptive performance to threshold profile
- reconfiguration overhead versus cycle benefit
- fuzz coverage summary for safety interactions

## Caveats to state

- The memory wait model is deterministic and synthetic.
- The energy metric is an activity proxy.
- Benchmarks are microbenchmarks, not full embedded applications.
- The ISA is ARM-like and educational.
- The current observer is threshold-based.
- The best fixed-mode baseline is an oracle over this tiny workload set.
- Simulation-time safety monitors, fuzz assertions, and architectural hashes increase artifact confidence but are not formal proof.

## Stronger claims after future work

Only make stronger claims after adding:

- larger benchmark corpus
- machine-checked formal safety proof
- calibrated synthesis/timing/power evidence for observer/controller overhead
- comparison against a richer static baseline
- sensitivity analysis for thresholds and residency settings
- real related-work citations in place of TODO citation placeholders
