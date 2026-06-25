# Reviewer Critique

This file captures the critique a graduate computer architecture reviewer is likely to raise, plus the repository changes that address each point.

## 1. Novelty is currently fragile

Weakness: The individual ingredients are familiar: performance counters, phase detection, branch handling, forwarding, memory buffering, and low-power gating. A paper cannot claim those pieces are new.

Patch direction: Scope the claim to the integrated artifact: a tiny hardware-resident observer, a hysteretic controller, and a safe drain-based reconfiguration path inside a small educational pipeline. The README and paper outline now warn against overclaiming.

What remains: Add a real related-work section with citations and a table that distinguishes PipeSense from software runtime policies, DVFS governors, hardware performance counters, and adaptive branch/memory mechanisms.

## 2. The methodology needs stricter baselines

Weakness: Adaptive versus static normal mode is too easy. A reviewer will ask whether a fixed branch, memory, hazard, or low-power mode would have done better if chosen offline.

Patch direction: The testbench now includes `fixed_low_power`. The analyzer now writes `oracle_gap.csv`, comparing adaptive mode against the best fixed mode for each benchmark.

What remains: Add more workloads and report when adaptive is worse than the oracle. That negative result can be useful because it motivates better phase detection and lower reconfiguration cost.

## 3. Hardware realism is limited

Weakness: The memory wait model is synthetic, branch optimization is an early-resolution model, and the energy metric is an activity proxy. None of those are physical implementation results.

Patch direction: Added `scripts/estimate_hardware_cost.py` and `docs/hardware_realism.md` so the prototype separates analytical cost estimates from synthesis claims.

What remains: Run synthesis, report area/timing/power estimates, and replace the synthetic memory model with a parameterized cache or scratchpad model.

## 4. Safety claims need executable evidence

Weakness: The docs say the design avoids lost instructions and duplicate writeback, but the original artifact did not check those claims.

Patch direction: The core now includes simulation-time instruction tags and safety monitors. The testbench emits `safety_faults`, and the methodology states that every reported run should have zero safety faults.

What remains: Add SystemVerilog Assertions or formal checks for the reconfiguration protocol. The simulation tags are a useful artifact check, not a proof.

## 5. Evaluation scale is too small

Weakness: The benchmarks are hand-written microbenchmarks. They demonstrate phase response but do not establish generality.

Patch direction: Added a sensitivity-sweep script for observer window size and minimum residency.

What remains: Add compiler-generated embedded kernels, random dependency stress tests, branch traces, memory latency distributions, and ablation studies.

## 6. Writing should separate hypothesis, mechanism, and evidence

Weakness: Early-stage architecture papers often blend a proposed mechanism with assumed benefits.

Patch direction: The docs now emphasize what is measured, what is synthetic, and what remains future work. Results templates include caveats and oracle comparisons.

What remains: After running simulations, write results in an answer-first style: state where PipeSense helps, where it hurts, and why the overhead is or is not justified.
