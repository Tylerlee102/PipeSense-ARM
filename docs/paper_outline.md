# Paper Outline

## 1. Abstract

Introduce PipeSense-ARM as a lightweight hardware observer/controller for safe adaptive pipeline reconfiguration in an ARM-like educational embedded processor. State the research question, the closed-loop architecture, the safe drain-based switching protocol, and the evaluation across synthetic embedded benchmarks.

## 2. Introduction

Motivate embedded processors that encounter changing phases: control flow, memory stalls, load-use dependencies, and idle periods. Explain why static pipeline policy can be mismatched to phase behavior. Position PipeSense-ARM as a small hardware-native adaptive loop.

## 3. Related Work

Cover adaptive microarchitecture, phase detection, performance counters,
dynamic voltage/frequency scaling, branch prediction, memory prefetching,
low-power embedded processors, and assertion-based verification. Use
`docs/related_work.md` as the source of the novelty boundary.

Be careful not to claim that phase detection, hardware counters, branch optimization, prefetching, or low-power gating are new by themselves. The claim should be about the integrated, minimal, hardware-resident observer/controller/reconfiguration loop in a reviewable educational pipeline.

## 4. Research Gap

Argue that many systems adapt at software/runtime levels or optimize one structure in isolation. PipeSense-ARM instead combines microarchitecture-aware observation, hardware-resident control, and safe runtime mode switching.

## 5. PipeSense Architecture

Describe the five-stage pipeline, instruction subset, observer taps, controller, reconfiguration unit, and mode knobs.

## 6. Observer Design

Explain rolling-window counters, phase classes, threshold parameters, and the minimal signal tap philosophy. Discuss why threshold logic is a useful first prototype before adding learned policies.

## 7. Controller Design

Describe phase-to-mode mapping, hysteresis, minimum residency, reconfiguration requests, and acknowledgement.

## 8. Safe Reconfiguration

Summarize the invariant sketch in `docs/safety_proof_sketch.md`. State the
safety properties:

- no instruction lost during mode switching
- no duplicated writeback
- bounded switching penalty
- explicit reconfiguration accounting

Explain the drain-before-switch protocol and the concrete safe-boundary
predicate.

## 9. Evaluation Methodology

Evaluate arithmetic-heavy, branch-heavy, memory-heavy, load-use-heavy, mixed embedded-control, and tiny FIR-style loops. Compare static normal, fixed branch, fixed memory, fixed hazard, fixed low-power, and adaptive PipeSense modes.

Also include an oracle best-fixed comparison per benchmark, a threshold/window
/residency sweep, and a workload-realism caveat.

Metrics:

- total cycles
- retired instructions
- IPC
- stall cycles
- flush cycles
- memory wait cycles
- load-use stalls
- reconfiguration count
- reconfiguration penalty
- activity-energy proxy
- safety monitor faults
- timeout status
- CPI and normalized event rates

## 10. Results

Use `results/pipesense_results.csv` and `results/adaptive_improvement.csv`. Present per-benchmark tradeoffs and emphasize where adaptive mode helps or pays overhead.

Use `results/oracle_gap.csv` to avoid overclaiming. If adaptive improves over normal mode but is far from the best fixed mode, present that as controller-tuning evidence rather than a performance victory.

Use `results/sweep_adaptive_vs_fixed.csv` to show sensitivity and report
where adaptive mode does not win.

## 11. Hardware Cost

Report `results/synth/area_summary.csv` if Yosys runs successfully. Label it
as a generic-cell area proxy. If Yosys is unavailable, use the analytical
estimate only as a weaker fallback and state that limitation.

## 12. Limitations

The processor is ARM-like, not ARM-compatible. The memory and energy models are synthetic. The branch, hazard, and memory optimizations are simplified research knobs. The observer uses threshold logic and short synthetic benchmarks.

The current artifact still does not include a complete formal proof,
recognizable real benchmark ports, cache behavior, interrupts/exceptions, or a
calibrated physical energy model.

## 13. Future Work

Add richer benchmarks, cycle-accurate memory hierarchy behavior, a real branch predictor, formal safety assertions, parameter sweeps, learned classifiers, and synthesis estimates for observer area/power overhead.

## 14. Conclusion

Summarize the case for hardware-native adaptive processor control: a small observer can classify pipeline phases, a controller can select targeted modes, and a safe reconfiguration unit can bound the cost of adaptation.
