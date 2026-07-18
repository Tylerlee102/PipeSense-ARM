# Published Adaptive Baseline

The comparison baseline is derived from A. Efthymiou and J. D. Garside,
"Adaptive Pipeline Structures for Speculation Control," ASYNC 2003,
pp. 46-55, DOI: 10.1109/ASYNC.2003.1199165.

## Published policy

The published AMULET3 design detects an instruction that changes ARM condition
codes, collapses its asynchronous pipeline while a branch is anticipated, and
returns to the fully pipelined configuration when execution reaches the branch
target. The paper evaluates real collapsible latch controllers in an
asynchronous processor.

## What this repository implements

`rtl/async03_speculation_controller.sv` implements only the observable control
heuristic:

1. Detect `CMP` at decode as the condition-setting hint.
2. Request PipeSense's low-activity mode while a branch is anticipated.
3. Request normal mode when the following branch reaches decode.
4. Use the same drain-before-switch reconfiguration unit and costs as
   PipeSense.

Select it with `--controller-policy async03`. It runs the same 13 directed
workloads and the same random seeds 1 through 500 as the PipeSense controller.

## Non-comparability warning

This is an **architectural approximation, not a reproduction**. PipeSense is a
synchronous five-stage educational core; it cannot make latches transparent,
merge stages, duplicate AMULET3 timing, or use extracted node capacitances.
The low-activity mode is only the closest existing mode to the paper's
collapsed state. PipeSense's safe drain also makes each request much more
expensive than the asynchronous transition described by Efthymiou and
Garside. Energy values are simulation proxy units, not joules or measured
power.

## Recorded outcome

Across the 13 directed workloads, PipeSense used 3,056 cycles, 18,055 energy
proxy units, and 12 transitions. The ASYNC'03 approximation used 4,875 cycles,
18,732 proxy units, and 425 transitions. Across 500 identical random seeds,
PipeSense used 61,588 cycles, 351,499 proxy units, and 406 transitions; the
approximation used 90,330 cycles, 346,504 proxy units, and 7,330 transitions.
Both had zero recorded safety faults and timeouts.

Raw directed rows, 500 per-seed logs, coverage, and paired comparisons are in
`results/adaptive_baseline/`. Regenerate them with:

```text
python scripts/run_adaptive_baseline.py --seeds 500
```
