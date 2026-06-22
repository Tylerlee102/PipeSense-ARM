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

The first implementation uses thresholds instead of machine learning to keep the hardware policy explainable and cheap.

## Controller

The adaptive controller maps phases to modes:

```text
branch heavy       -> MODE_BRANCH_OPT
memory stall       -> MODE_MEMORY_OPT
load-use hazard    -> MODE_HAZARD_OPT
frontend stall     -> MODE_BRANCH_OPT
idle/low-util      -> MODE_LOW_POWER
balanced           -> MODE_NORMAL
```

It applies hysteresis through a stable-phase counter and a minimum mode residency counter.

## Reconfiguration safety

The reconfiguration unit does not switch modes immediately. It stops new fetches, lets in-flight instructions drain through writeback, and only commits the new mode when the pipeline is empty and no memory wait is active.

This models a conservative safe boundary. It may overpay penalty compared with a more aggressive industrial design, but it makes the safety contract clear.

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

`scripts/analyze_results.py` parses simulator output and computes adaptive improvement over static normal mode. It also writes `oracle_gap.csv`, which compares adaptive PipeSense against the best fixed mode for each benchmark.

`scripts/plot_results.py` generates simple plots when matplotlib is installed. `scripts/sweep_params.py` runs a small observer-window and minimum-residency sweep. `scripts/estimate_hardware_cost.py` writes an analytical cost estimate for the observer, controller, reconfiguration unit, and simulation safety monitor.

## Safety checks

The core exports `safety_faults`, which is incremented when simulation-time monitors detect:

- mode changes outside an empty-pipeline boundary
- reconfiguration acknowledgement before drain completion
- fetch not gated during active reconfiguration
- duplicated or backward-moving retired instruction tags

These monitors are not a substitute for formal verification, but they make the artifact more reviewable because safety claims are connected to executable checks.

## Baseline discipline

The paper should avoid relying only on adaptive versus normal-mode speedup. A reviewer will also ask whether the adaptive controller beats, or at least approaches, the best fixed policy for the workload. The oracle fixed-mode comparison is not a deployable policy, but it is a useful upper-bound baseline.
