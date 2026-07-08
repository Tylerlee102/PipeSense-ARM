# Results Summary

This page summarizes the current validated simulation outputs. The source tables are:

- `results/pipesense_results.csv`
- `results/adaptive_improvement.csv`
- `results/oracle_gap.csv`
- `results/ablation_summary.csv`
- `results/hardware_cost_estimate.csv`
- `results/sweep_adaptive_vs_fixed.csv`
- `results/safety/fuzz_summary.csv`
- `results/synth/area_summary.csv`

The current HDL run contains 60 benchmark/mode rows, with zero timeouts and zero safety faults. `scripts/compare_reference.py` also matches HDL retired counts and final architectural data-state hashes against the sequential ISA reference model.

The constrained-random safety run contains 500 seeds and 2,500 mode-result rows. It reports zero simulator assertion failures, zero safety faults, and zero timeouts. The coverage counters observed the random-harness phase classes encoded by mask `0x1d` and a broad set of mode transitions encoded by mask `0x3adae`, including 141 hazard-during-reconfiguration events, 3,040 back-to-back reconfiguration-request events, and 21 reconfiguration-then-branch events. The current run did not hit the reconfiguration-then-load-use coverage bucket, so coverage should not be described as complete.

## Adaptive versus normal

| Benchmark | Normal cycles | Adaptive cycles | Cycle reduction | IPC improvement | Energy proxy reduction | Reconfigs | Reconfig penalty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic_heavy | 30 | 30 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| branch_heavy | 128 | 114 | 10.94% | 12.28% | 6.64% | 1 | 2 |
| coremark_toy | 162 | 162 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| dhrystone_toy | 133 | 133 | 0.00% | 0.00% | 0.00% | 0 | 0 |
| dsp_fir_codegen | 192 | 194 | -1.04% | -1.03% | 0.36% | 2 | 8 |
| load_use_heavy | 205 | 178 | 13.17% | 15.17% | 7.64% | 1 | 4 |
| memory_heavy | 231 | 201 | 12.99% | 14.92% | 15.68% | 6 | 28 |
| mixed_control | 131 | 127 | 3.05% | 3.14% | 2.28% | 1 | 4 |
| pid_control_codegen | 192 | 200 | -4.17% | -3.99% | -0.79% | 3 | 13 |
| tiny_fir | 159 | 160 | -0.63% | -0.62% | 3.17% | 3 | 14 |

Interpretation: the adaptive controller improves over static normal mode on the phase-biased branch, memory, load-use, and mixed-control tests. It does not help arithmetic-heavy, `dhrystone_toy`, or `coremark_toy`, where the current thresholds do not justify a mode switch. On `tiny_fir`, `dsp_fir_codegen`, and `pid_control_codegen`, adaptive mode increases cycles; the PID-style kernel also increases the activity-energy proxy. These negative cases show that the controller can pay reconfiguration cost without enough useful phase residency.

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
| memory_heavy | fixed_memory | 147 | 201 | -36.73% | 839 | 1038 | -23.72% |
| mixed_control | fixed_memory | 105 | 127 | -20.95% | 617 | 730 | -18.31% |
| pid_control_codegen | fixed_memory | 178 | 200 | -12.36% | 1080 | 1153 | -6.76% |
| tiny_fir | fixed_memory | 127 | 160 | -25.98% | 739 | 855 | -15.70% |

Interpretation: adaptive mode is meaningfully better than static normal mode, but it does not beat the best fixed-mode oracle. This should be framed as an early hardware-control prototype result, not as a final performance win. The largest gaps occur when memory mitigation dominates and the observer/controller does not move into, or stay in, memory-optimized mode early enough.

## Ablation summary

The ablation summary compares aggregate adaptive-mode behavior against the full adaptive default, which totals 1,499 cycles over the ten benchmarks.

| Ablation | Total adaptive cycles | Cycle change vs full | Total adaptive energy | Reconfigs | Reconfig penalty | Safety faults | Timeouts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| observer_disabled | 1,563 | 4.27% | 8,872 | 0 | 0 | 0 | 0 |
| controller_disabled | 1,563 | 4.27% | 8,872 | 0 | 0 | 0 | 0 |
| zero_cost_reconfig | 1,426 | -4.87% | 8,508 | 17 | 0 | 0 | 0 |

Interpretation: disabling either the observer or controller removes all adaptive switching and matches static-normal aggregate behavior. The zero-cost row is an analytical idealization computed from the validated full-adaptive run by subtracting reconfiguration penalty cycles; it is not an unsafe instant-switch RTL run.

## Sweep sensitivity

The corrected 3x3x3 sweep is not flat. All 27 settings complete with 60 rows, but aggregate adaptive cycles range from 1,477 cycles with a 64-cycle observer window and loose thresholds to 1,670 cycles with a 16-cycle window, 8-cycle residency, and tight thresholds. The sweep records 318 adaptive cycle wins and 1,032 non-wins across adaptive-versus-fixed comparison cells.

## Hardware-cost evidence

`scripts/estimate_hardware_cost.py` reports an analytical estimate only, not synthesis evidence. `scripts/synth_area_report.py` now reports a Yosys generic-cell proxy; label that proxy carefully. The current proxy run reports 1,830 cells for the baseline core proxy and 2,819 standalone cells for the observer, controller, and reconfiguration modules combined, or 154.04% of the baseline core proxy. This is not calibrated FPGA/ASIC area, timing, or power.

| Component | Generic cells | Overhead versus core proxy |
| --- | ---: | ---: |
| baseline core proxy | 1,830 | 100.00% |
| pipeline_observer | 2,128 | 116.28% |
| adaptive_controller | 116 | 6.34% |
| reconfig_unit | 575 | 31.42% |
| observer/controller/reconfig sum | 2,819 | 154.04% |

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
- The Yosys numbers are a generic-cell proxy, not calibrated implementation evidence.

## Stronger claims after future work

Only make stronger claims after adding:

- larger benchmark corpus
- machine-checked formal safety proof
- calibrated timing/power evidence for observer/controller overhead
- comparison against a richer static baseline
- sensitivity analysis for thresholds and residency settings
- updated related-work citations for any new verification or workload claims
