# Results Summary

This page summarizes the current validated simulation outputs. The source tables are:

- `results/pipesense_results.csv`
- `results/adaptive_improvement.csv`
- `results/oracle_gap.csv`
- `results/ablation_summary.csv`
- `results/sweep_adaptive_vs_fixed.csv`
- `results/safety/fuzz_summary.csv`
- `results/synth/area_summary.csv`

The current HDL run contains 78 benchmark/mode rows, with zero timeouts and zero safety faults. `scripts/compare_reference.py` matches HDL retired counts and final architectural data-state hashes against the sequential ISA reference model.

The constrained-random safety run contains 500 seeds and 2,500 mode-result rows. It reports zero simulator assertion failures, zero safety faults, and zero timeouts. Coverage should be described as stress evidence, not exhaustive proof.

## Adaptive versus normal

| Benchmark | Normal cycles | Adaptive cycles | Cycle reduction | IPC improvement | Energy proxy reduction | Reconfigs | Reconfig penalty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic_heavy | 30 | 30 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| branch_heavy | 128 | 114 | 10.94% | 12.28% | 6.64% | 1 | 2 |
| coremark_toy | 162 | 162 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| dhrystone_toy | 133 | 133 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| dsp_fir_codegen | 192 | 194 | -1.04% | -1.03% | 0.36% | 2 | 8 |
| load_use_heavy | 205 | 178 | 13.17% | 15.17% | 7.64% | 1 | 4 |
| long_fir_stress | 876 | 792 | 9.59% | 10.62% | 7.63% | 1 | 4 |
| memory_heavy | 231 | 162 | 29.87% | 42.60% | 26.81% | 1 | 3 |
| mixed_control | 131 | 127 | 3.05% | 3.14% | 2.28% | 1 | 4 |
| pid_control_codegen | 192 | 188 | 2.08% | 2.13% | 1.49% | 1 | 4 |
| pid_phase_stress | 653 | 620 | 5.05% | 5.32% | 2.62% | 1 | 4 |
| random_mem_latency_stress | 215 | 204 | 5.12% | 5.39% | 5.05% | 1 | 4 |
| tiny_fir | 159 | 152 | 4.40% | 4.61% | 6.00% | 2 | 10 |

Interpretation: adaptive mode improves 9 of 13 workloads, ties 3, and slows `dsp_fir_codegen` by 1.04%. Aggregate static-normal execution takes 3,307 cycles; adaptive execution takes 3,056 cycles, a 7.59% total cycle reduction. Total activity-energy proxy falls from 19,162 to 18,055, a 5.78% reduction.

## Oracle fixed-mode comparison

The oracle comparison asks whether adaptive mode approaches the best single fixed mode selected with hindsight. Negative gap values mean adaptive is worse than the oracle.

| Benchmark | Best fixed mode | Best fixed cycles | Adaptive cycles | Adaptive cycle gap | Best fixed energy | Adaptive energy | Adaptive energy gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic_heavy | fixed_hazard | 29 | 30 | -3.45% | 173 | 176 | -1.73% |
| branch_heavy | fixed_branch | 105 | 114 | -8.57% | 609 | 633 | -3.94% |
| coremark_toy | fixed_hazard | 150 | 162 | -8.00% | 927 | 957 | -3.24% |
| dhrystone_toy | fixed_branch | 124 | 133 | -7.26% | 798 | 825 | -3.38% |
| dsp_fir_codegen | fixed_hazard | 168 | 194 | -15.48% | 1046 | 1102 | -5.35% |
| load_use_heavy | fixed_hazard | 169 | 178 | -5.33% | 1017 | 1039 | -2.16% |
| long_fir_stress | fixed_memory | 778 | 792 | -1.80% | 4656 | 4709 | -1.14% |
| memory_heavy | fixed_memory | 147 | 162 | -10.20% | 839 | 901 | -7.39% |
| mixed_control | fixed_memory | 105 | 127 | -20.95% | 617 | 730 | -18.31% |
| pid_control_codegen | fixed_memory | 178 | 188 | -5.62% | 1080 | 1127 | -4.35% |
| pid_phase_stress | fixed_memory | 611 | 620 | -1.47% | 3775 | 3861 | -2.28% |
| random_mem_latency_stress | fixed_memory | 189 | 204 | -7.94% | 1109 | 1165 | -5.05% |
| tiny_fir | fixed_memory | 127 | 152 | -19.69% | 739 | 830 | -12.31% |

Interpretation: adaptive mode is better than static normal mode in aggregate, but it does not beat the best fixed-mode oracle. The average adaptive gap is -8.90% in cycles and -5.43% in the activity-energy proxy.

## Ablation summary

The ablation summary compares aggregate adaptive-mode behavior against the full adaptive default, which totals 3,056 cycles over the 13 workloads.

| Ablation | Total adaptive cycles | Cycle change vs full | Total adaptive energy | Reconfigs | Reconfig penalty | Safety faults | Timeouts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| observer_disabled | 3,307 | 8.21% | 19,162 | 0 | 0 | 0 | 0 |
| controller_disabled | 3,307 | 8.21% | 19,162 | 0 | 0 | 0 | 0 |
| zero_cost_reconfig | 3,009 | -1.54% | 18,055 | 12 | 0 | 0 | 0 |

Interpretation: disabling either the observer or controller removes all adaptive switching and matches static-normal aggregate behavior. The zero-cost row is an analytical idealization computed from the validated full-adaptive run by subtracting reconfiguration penalty cycles; it is not an unsafe instant-switch RTL run.

## Sweep sensitivity

The corrected 3x3x3 sweep completes all 27 settings with 78 rows per setting, for 2,106 result rows. It records adaptive-versus-fixed comparison cells, including non-wins, rather than filtering to favorable cases.

## Hardware-cost evidence

`scripts/synth_area_report.py` reports a Yosys generic-cell proxy. Label that proxy carefully. This is not calibrated FPGA/ASIC area, timing, or power.

| Component | Generic cells | Overhead versus core proxy |
| --- | ---: | ---: |
| baseline core proxy | 1,838 | 100.00% |
| pipeline_observer | 319 | 17.36% |
| adaptive_controller | 180 | 9.79% |
| reconfig_unit | 51 | 2.77% |
| integrated core proxy | 2,380 | 29.49% delta |
| observer/controller/reconfig sum | 550 | 29.92% |

## Figures

`scripts/plot_results.py` generates PNG plots when `matplotlib` is installed.

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
- Benchmarks are toy-ISA kernels and stress workloads, not full embedded applications.
- The ISA is ARM-like and educational.
- The current observer is threshold-based.
- The best fixed-mode baseline is an oracle over this workload set.
- Simulation-time safety monitors, fuzz assertions, and architectural hashes increase artifact confidence but are not formal proof.
- The Yosys numbers are a generic-cell proxy, not calibrated implementation evidence.

## Stronger claims after future work

Only make stronger claims after adding:

- larger compiler-generated benchmark corpus
- machine-checked formal safety proof bound into the full core
- calibrated timing/power evidence for observer/controller overhead
- comparison against a richer static baseline
- sensitivity analysis for thresholds and residency settings
- updated related-work citations for any new verification or workload claims
