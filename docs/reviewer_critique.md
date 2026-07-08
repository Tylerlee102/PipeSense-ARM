# Reviewer Critique

This file captures the critique a graduate computer architecture reviewer is likely to raise, plus the repository changes that address each point.

## 1. Novelty is currently fragile

Weakness: The individual ingredients are familiar: performance counters, phase detection, branch handling, forwarding, memory buffering, and low-power gating. A paper cannot claim those pieces are new.

Patch direction: Scope the claim to the integrated artifact: a tiny hardware-resident observer, a hysteretic controller, and a safe drain-based reconfiguration path inside a small educational pipeline. The README and paper outline now warn against overclaiming.

Cycle 5 status: Added a related-work boundary table to `docs/related_work.md` and `paper/pipesense_urtc_8page.tex`, using only bibliography entries already present in `paper/references.bib`. The inserted one-sentence claim is: PipeSense-ARM's claim is not a new branch, memory, power, or verification mechanism, but the integration of a tiny in-core phase observer, hysteretic mode controller, drain-before-switch safety protocol, and reproducible oracle/ablation evaluation in a compact ARM-like RTL pipeline.

What remains: Add more recent embedded-runtime and adaptive-microarchitecture citations only if the paper makes stronger claims than the current artifact supports.

## 2. The methodology needs stricter baselines

Weakness: Adaptive versus static normal mode is too easy. A reviewer will ask whether a fixed branch, memory, hazard, or low-power mode would have done better if chosen offline.

Patch direction: The testbench now includes `fixed_low_power`. The analyzer now writes `oracle_gap.csv`, comparing adaptive mode against the best fixed mode for each benchmark.

Cycle 0 status: The baseline result set is frozen under `results/v0/` after a clean rerun of `scripts/run_sim.py`, `scripts/validate_results.py`, `scripts/compare_reference.py`, `scripts/run_sweep.py`, `verif/fuzz_runner.py --seeds 500`, `scripts/estimate_hardware_cost.py`, and `scripts/synth_area_report.py`. The exit-gate audit checked 87 frozen CSVs and 6,088 rows with safety, timeout, or assertion columns; all were zero/false. The first freeze attempt failed because stale historical CI artifacts under `results/ci_artifacts/` contained old fuzz assertion failures, so future baseline freezes should start from a clean generated-results directory.

What remains: Add more workloads and report when adaptive is worse than the oracle. That negative result can be useful because it motivates better phase detection and lower reconfiguration cost.

## 3. Hardware realism is limited

Weakness: The memory wait model is synthetic, branch optimization is an early-resolution model, and the energy metric is an activity proxy. None of those are physical implementation results.

Patch direction: Added `scripts/estimate_hardware_cost.py` and `docs/hardware_realism.md` so the prototype separates analytical cost estimates from synthesis claims.

Cycle 2 status: Ran `scripts/synth_area_report.py` with local Yosys. `results/synth/area_summary.csv` reports 1,830 cells for the baseline core proxy and 2,819 standalone cells for the observer, controller, and reconfiguration modules combined, or 154.04% of the baseline core proxy.

What remains: Add calibrated timing/power estimates and replace the synthetic memory model with a parameterized cache or scratchpad model.

## 4. Safety claims need executable evidence

Weakness: The docs say the design avoids lost instructions and duplicate writeback, but the original artifact did not check those claims.

Patch direction: The core now includes simulation-time instruction tags and safety monitors. The testbench emits `safety_faults`, and the methodology states that every reported run should have zero safety faults.

Cycle 1 status: Added `formal/no_double_commit_across_mode_switch.sv` and `formal/no_double_commit_across_mode_switch.sby`. The bounded SymbiYosys run at k=16 passes under `formal/results/no_double_commit_across_mode_switch/`, proving in an abstract drain-before-switch token model that a tag committed before a visible mode switch cannot commit again after the switch.

What remains: Bind the no-double-commit property into a reduced `arm_like_core` formal instance and extend the proof beyond the current k=16 abstract model.

## 5. Evaluation scale is too small

Weakness: The benchmarks are hand-written microbenchmarks. They demonstrate phase response but do not establish generality.

Patch direction: Added a sensitivity-sweep script for observer window size and minimum residency.

Cycle 3 status: Added two generated-style benchmark streams, `dsp_fir_codegen` and `pid_control_codegen`, to both `tb/benchmark_programs.sv` and `scripts/isa_reference.py`. `scripts/check_benchmark_parity.py` passes, `scripts/run_sim.py` now reports `SUMMARY total_cases=60 failed_cases=0`, `scripts/validate_results.py` passes, `scripts/compare_reference.py` passes, and `scripts/run_sweep.py` completes all 27 settings with 60 rows per setting. `results/oracle_gap.csv` includes both new workloads. Adaptive mode loses on both: `dsp_fir_codegen` takes 194 cycles versus a 168-cycle fixed-hazard oracle (-15.48%), and `pid_control_codegen` takes 200 cycles versus a 178-cycle fixed-memory oracle (-12.36%). These losses are preserved in the paper and support the claim that the current controller is conservative and phase-residency limited.

Cycle 4 status: Added `scripts/run_ablations.py`, compile-time observer/controller disable hooks, `results/ablation_summary.csv`, and an ablation table in the paper. Observer-disabled and controller-disabled runs each pass full HDL/reference validation and total 1,563 adaptive cycles with zero reconfigurations. The zero-reconfiguration-penalty row is an analytical headroom estimate from the validated full-adaptive run: 1,426 cycles, 17 reconfiguration events, and zero counted penalty. A failed instant-switch experiment changed the `dsp_fir_codegen` architectural hash, so it was not used as paper evidence.

What remains: Add full compiler-generated embedded benchmark ports, random dependency stress tests, branch traces, and memory latency distributions.

## 6. Writing should separate hypothesis, mechanism, and evidence

Weakness: Early-stage architecture papers often blend a proposed mechanism with assumed benefits.

Patch direction: The docs now emphasize what is measured, what is synthetic, and what remains future work. Results templates include caveats and oracle comparisons.

Cycle 6 status: Completed a writing/readiness pass after the benchmark, ablation, related-work, and sweep updates. The paper now states the claim boundary in one sentence, keeps negative adaptive/oracle results, labels activity energy and Yosys area as proxies, and distinguishes simulation monitors plus bounded abstract proof from full formal verification. A human-facing scan found no AI/tooling provenance language in README, docs, or paper text. `scripts/check_paper.py` passes, and `scripts/verify_paper_preview.py` verifies an exactly 6-page rendered preview.

What remains: For a final submission, replace placeholder author metadata, confirm the current MIT URTC page limit and template, and add any required institutional formatting before upload.
