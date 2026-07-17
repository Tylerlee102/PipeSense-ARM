# Methodology

## Prototype design

PipeSense-ARM uses a five-stage educational pipeline:

```text
IF -> ID -> EX -> MEM -> WB
```

The core includes instruction memory, data memory, register file, program counter, pipeline valid bits, forwarding, load-use hazard handling, branch flushes, performance counters, and a simulation-only `HALT` instruction.

## Observer

The observer samples minimal pipeline taps and accumulates rolling-window counts. Its current phase classes are:

- balanced
- branch heavy
- memory stall
- load-use hazard
- frontend stall
- idle or low utilization

The first implementation uses parameterized thresholds instead of machine
learning to keep the hardware policy explainable and cheap. `scripts/run_sim.py`
can override the observer window and all phase thresholds, and
`scripts/run_sweep.py` runs tight, medium, and loose threshold profiles.

## Controller

The adaptive controller maps phases to modes:

```text
branch heavy       -> MODE_BRANCH_OPT
memory stall       -> MODE_MEMORY_OPT
load-use hazard    -> MODE_HAZARD_OPT
frontend stall     -> MODE_BRANCH_OPT
idle/low-util      -> MODE_LOW_POWER
balanced           -> keep current mode
```

It applies hysteresis through a stable-phase counter and mode-specific minimum
residency requirements. Memory mode can enter faster than branch, hazard,
low-power, or normal modes because memory stalls dominate the short benchmark
suite.

## Reconfiguration safety

The reconfiguration unit does not switch modes immediately. It stops new fetches, lets in-flight instructions drain through writeback, and only commits the new mode when the pipeline is empty and no memory wait is active.

This models a conservative safe boundary. It may overpay penalty compared with a more aggressive industrial design, but it makes the safety contract clear.

The proof sketch in `docs/safety_proof_sketch.md` defines the safe boundary
as `pipeline_empty && !mem_wait_signal`. The executable safety monitors in
`verif/sva_safety.sv` check monotonic retirement tags, safe mode commit,
fetch gating, stable mode during reconfiguration, and bounded stall time.

## Experimental matrix

Each benchmark runs in six configurations:

- static normal mode
- fixed branch-optimized mode
- fixed memory-optimized mode
- fixed hazard-optimized mode
- fixed low-power mode
- adaptive PipeSense mode

Benchmarks:

- arithmetic-heavy program
- branch-heavy loop
- memory-heavy loop
- load-use hazard-heavy loop
- mixed embedded-control loop
- tiny FIR-style loop
- Dhrystone-style integer/control toy port
- CoreMark-style checksum/list-walk toy port
- generated-style FIR stream loop
- generated-style PID-control loop
- long FIR stress loop
- PID phase stress loop
- randomized memory-latency stress loop

The suite remains small, but it now separates two purposes. The six original
kernels are synthetic and phase-biased by design. The two toy ports add
recognizable Dhrystone/CoreMark-style structure, the generated-style kernels add
DSP/control instruction streams, and the three longer stress workloads reduce
overfitting to tiny loops without pretending to be full benchmark-suite
executions. `verif/random_seq_gen.py` and
`verif/fuzz_runner.py` add constrained-random instruction mixes for safety
stress. The remaining workload limitation is the lack of full compiler-generated
embedded benchmark ports, tracked in `docs/limitations_and_honesty.md`.

## Metrics

The testbench reports:

- cycles
- retired instructions
- IPC
- stall cycles
- flush cycles
- memory wait cycles
- load-use stalls
- reconfiguration count
- total reconfiguration penalty
- activity-energy proxy
- safety faults from simulation-time monitors
- timeout flag
- normalized rates such as stalls per retired instruction

## Analysis

`scripts/analyze_results.py` parses simulator output and computes adaptive
improvement over static normal mode. It also writes `oracle_gap.csv`, which
compares adaptive PipeSense against the best fixed mode for each benchmark.

`scripts/run_sweep.py` runs a sweep over observer window size, threshold
profile, and minimum residency. It writes `sweep_adaptive_vs_fixed.csv`, which
preserves the sweep dimensions and explicitly flags cells where adaptive mode
does not beat a fixed baseline. `scripts/plot_results.py` generates basic
comparison plots and sweep visualizations when matplotlib is installed.

`scripts/run_ablations.py` runs the observer-disabled and controller-disabled
variants, then writes `ablation_summary.csv` with an additional analytical
zero-reconfiguration-penalty headroom row computed from the validated
full-adaptive run.

`scripts/synth_area_report.py` runs the Yosys generic synthesis scaffold. Its
baseline and integrated runs share a 1,838-cell core shell and synthesize the
production observer/controller/reconfiguration RTL. The modules total 550
standalone cells (29.92% of the shell); the integrated top maps to 2,380 cells
(29.49% delta). This is not full processor synthesis, calibrated ASIC area,
FPGA utilization, timing, or power.

## Safety checks

The core exports `safety_faults`, which is incremented when simulation-time monitors detect:

- mode changes outside an empty-pipeline boundary
- reconfiguration acknowledgement before drain completion
- fetch not gated during active reconfiguration
- duplicated or backward-moving retired instruction tags

These monitors complement three bounded SymbiYosys jobs: the production
reconfiguration unit at depth 24, abstract token conservation at depth 9, and
abstract no-double-commit checking at depth 14. They do not constitute a
full-core proof.

Additional safety regression:

```bash
python verif/fuzz_runner.py --seeds 500
```

The default seed count is intentionally high for a paper artifact. For a quick
local smoke test, use `--seeds 5`. The current 500-seed run produced 2,500
mode-result rows with zero assertion failures, zero safety faults, and zero
timeouts. Its coverage counters hit several reconfiguration interaction
buckets, but did not hit every bucket, so the result should be presented as
stress evidence rather than exhaustive safety coverage.

## Baseline discipline

The paper should avoid relying only on adaptive versus normal-mode speedup. A reviewer will also ask whether the adaptive controller beats, or at least approaches, the best fixed policy for the workload. The oracle fixed-mode comparison is not a deployable policy, but it is a useful upper-bound baseline.
