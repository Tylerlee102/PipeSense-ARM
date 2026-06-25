# Evaluation Plan

## Research questions

1. Can the observer distinguish pipeline bottleneck phases from narrow hardware taps?
2. Does adaptive mode improve cycles or IPC versus static normal mode?
3. How close does adaptive mode get to the best fixed mode for each benchmark?
4. How much reconfiguration penalty does the safe switching protocol introduce?
5. Does low-power mode reduce the activity proxy without hiding correctness or timeout failures?
6. How sensitive are results to observer window size and minimum mode residency?

## Required tables

- Main results: `results/pipesense_results.csv`
- Adaptive versus normal: `results/adaptive_improvement.csv`
- Adaptive versus oracle best fixed mode: `results/oracle_gap.csv`
- Ablation summary: `results/ablation_summary.csv`
- Hardware cost estimate: `results/hardware_cost_estimate.csv`
- Parameter sweep summary: `results/sweep_results.csv`

## Required checks before making claims

- Every row has `timed_out == 0`.
- Every row has `safety_faults == 0`.
- Adaptive improvements are reported alongside reconfiguration penalty.
- Negative adaptive results are preserved rather than filtered out.
- Best fixed-mode comparison is shown for every benchmark.

## Ablations

- done in Cycle 4: observer disabled
- done in Cycle 4: controller disabled
- done in Cycle 4: zero reconfiguration penalty idealization, computed from validated full-adaptive penalty cycles
- future work: reconfiguration drain protocol versus hypothetical instant switch with a safety-preserving model
- Each microarchitectural knob alone
- Observer window and threshold sensitivity

## Stronger benchmark direction

The current benchmarks are useful for debugging, but a paper needs broader evidence. Add:

- done in Cycle 3: `dsp_fir_codegen`, a generated-style FIR stream loop
- done in Cycle 3: `pid_control_codegen`, a generated-style embedded-control loop
- generated random dependency chains
- branch predictability sweeps
- memory latency sweeps
- small DSP kernels
- embedded-control kernels
- full compiler-generated instruction streams for the simplified ISA
- trace-driven frontend and memory event injection
