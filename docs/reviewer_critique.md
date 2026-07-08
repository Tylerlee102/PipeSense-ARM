# Reviewer Critique

This file captures the critique a graduate computer architecture reviewer is likely to raise, plus the repository changes that address each point.

## 1. Novelty is currently fragile

Weakness: The individual ingredients are familiar: performance counters, phase detection, branch handling, forwarding, memory buffering, and low-power gating. A paper cannot claim those pieces are new.

Patch direction: Scope the claim to the integrated artifact: a tiny hardware-resident observer, a hysteretic controller, and a safe drain-based reconfiguration path inside a small educational pipeline. The README and paper outline now warn against overclaiming.

Cycle 5 status: Added a related-work boundary table to `docs/related_work.md` and scoped the claim to the artifact evidence. The one-sentence claim remains: PipeSense-ARM's claim is not a new branch, memory, power, or verification mechanism, but the integration of a tiny in-core phase observer, hysteretic mode controller, drain-before-switch safety protocol, and reproducible oracle/ablation evaluation in a compact ARM-like RTL pipeline.

What remains: Add more recent embedded-runtime and adaptive-microarchitecture citations only if the paper makes stronger claims than the current artifact supports.

## 2. The methodology needs stricter baselines

Weakness: Adaptive versus static normal mode is too easy. A reviewer will ask whether a fixed branch, memory, hazard, or low-power mode would have done better if chosen offline.

Patch direction: The testbench now includes `fixed_low_power`. The analyzer now writes `oracle_gap.csv`, comparing adaptive mode against the best fixed mode for each benchmark.

Cycle 0 status: The baseline result set is frozen under `results/v0/` after a clean rerun of `scripts/run_sim.py`, `scripts/validate_results.py`, `scripts/compare_reference.py`, `scripts/run_sweep.py`, `verif/fuzz_runner.py --seeds 500`, `scripts/estimate_hardware_cost.py`, and `scripts/synth_area_report.py`. The exit-gate audit checked 87 frozen CSVs and 6,088 rows with safety, timeout, or assertion columns; all were zero/false. The first freeze attempt failed because stale historical CI artifacts under `results/ci_artifacts/` contained old fuzz assertion failures, so future baseline freezes should start from a clean generated-results directory.

What remains: Add more workloads and report when adaptive is worse than the oracle. That negative result can be useful because it motivates better phase detection and lower reconfiguration cost.

## 3. Hardware realism is limited

Weakness: The memory wait model is synthetic, branch optimization is an early-resolution model, and the energy metric is an activity proxy. None of those are physical implementation results.

Patch direction: Added `scripts/estimate_hardware_cost.py` and `docs/hardware_realism.md` so the prototype separates analytical cost estimates from synthesis claims.

Cycle 7 status: Ran `scripts/synth_area_report.py` with local Yosys after adding an integrated proxy top module. `results/synth/area_summary.csv` reports 1,830 cells for the baseline core proxy, 2,885 standalone cells for the observer, controller, and reconfiguration modules combined (157.65% of baseline), and 4,850 cells for the integrated proxy (165.03% delta over baseline).

What remains: Add calibrated timing/power estimates and replace the synthetic memory model with a parameterized cache or scratchpad model.

## 4. Safety claims need executable evidence

Weakness: The docs say the design avoids lost instructions and duplicate writeback, but the original artifact did not check those claims.

Patch direction: The core now includes simulation-time instruction tags and safety monitors. The testbench emits `safety_faults`, and the methodology states that every reported run should have zero safety faults.

Cycle 1 status: Added `formal/no_double_commit_across_mode_switch.sv` and `formal/no_double_commit_across_mode_switch.sby`. The bounded SymbiYosys run at k=16 passes under `formal/results/no_double_commit_across_mode_switch/`, proving in an abstract drain-before-switch token model that a tag committed before a visible mode switch cannot commit again after the switch.

What remains: Bind the no-double-commit property into a reduced `arm_like_core` formal instance and extend the proof beyond the current k=16 abstract model.

## 5. Evaluation scale is too small

Weakness: The benchmarks are hand-written microbenchmarks. They demonstrate phase response but do not establish generality.

Patch direction: Added a sensitivity-sweep script for observer window size and minimum residency.

Cycle 7 status: Added three longer stress workloads, `long_fir_stress`, `pid_phase_stress`, and `random_mem_latency_stress`, to both `tb/benchmark_programs.sv` and `scripts/isa_reference.py`. `scripts/check_benchmark_parity.py` passes, `scripts/run_sim.py` reports `SUMMARY total_cases=78 failed_cases=0`, `scripts/validate_results.py` passes, `scripts/compare_reference.py` passes, and `scripts/run_sweep.py` covers all 27 settings with 78 rows per setting. Adaptive mode now improves 9 of 13 workloads, ties 3, and preserves the negative `dsp_fir_codegen` row at -1.04% cycles versus static normal.

Cycle 7 status: `scripts/run_ablations.py` passes on the 13-workload set. Observer-disabled and controller-disabled runs each pass full HDL/reference validation and total 3,307 adaptive cycles with zero reconfigurations. The zero-reconfiguration-penalty row is an analytical headroom estimate from the validated full-adaptive run: 3,009 cycles, 12 reconfiguration events, and zero counted penalty.

What remains: Add full compiler-generated embedded benchmark ports, random dependency stress tests, branch traces, and memory latency distributions.

## 6. Writing should separate hypothesis, mechanism, and evidence

Weakness: Early-stage architecture papers often blend a proposed mechanism with assumed benefits.

Patch direction: The docs now emphasize what is measured, what is synthetic, and what remains future work. Results templates include caveats and oracle comparisons.

Cycle 7 status: Completed a readiness pass after the controller-v2, workload, synthesis, CI, and result-data updates. The public repository now keeps the claim boundary in README/docs, preserves negative adaptive/oracle results in CSVs, labels activity energy and Yosys area as proxies, and distinguishes simulation monitors plus bounded abstract proof from full formal verification.

What remains: For a final submission, confirm the preferred author metadata, current MIT URTC template, and any required institutional formatting before upload.
