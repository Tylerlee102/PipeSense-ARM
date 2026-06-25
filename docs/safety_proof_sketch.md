# Safety Proof Sketch

This is an invariant-based proof sketch for the reconfiguration protocol. It
is not a machine-checked proof of the whole processor.

## Concrete Safe Boundary

PipeSense-ARM defines a safe boundary as:

```text
pipeline_empty && !mem_wait_signal
```

The reconfiguration unit may start a transition before this predicate is true,
but the visible mode must not change until the predicate holds. During the
transition, fetch is gated so no new instruction enters under a partially
changed mode.

## Invariants

I1. No duplicate dynamic writeback:
retired instruction tags are strictly increasing. Therefore, the same dynamic
instruction cannot retire twice.

I2. Safe mode commit:
`current_mode` changes only when the previous cycle was a safe boundary and
`reconfig_done` was asserted.

I3. Fetch gating during transition:
when `reconfig_active` is asserted, `reconfig_stop_fetch` is asserted.

I4. No torn mode state:
while `reconfig_active` remains asserted, the visible mode remains equal to
the mode captured at the start of the transition.

I5. Bounded reconfiguration penalty:
`reconfig_stall_cycles` is no larger than the configured assertion bound.
The current fuzz harness uses 32 cycles by default. This is a conservative
simulation bound, not a technology timing result.

## Inductive Argument

Base case:
after reset, pipeline valid bits are clear, tags are zeroed, the current mode
equals the boot/fixed mode, and no reconfiguration is active. I1-I5 hold
trivially.

Inductive step without reconfiguration:
normal pipeline advancement preserves tag order because fetched tags increase
monotonically and bubbles/flushes clear valid bits rather than copying a tag
into two retirement positions. The mode does not change, so I2-I4 hold. I5 is
irrelevant when no reconfiguration is active.

Inductive step with reconfiguration active:
the reconfiguration unit gates fetch, so no new instruction enters the
pipeline while the mode transition is pending. In-flight instructions continue
to drain under the old visible mode. The visible mode is stable until the
pipeline is empty and no memory wait is active. When the safe boundary holds,
the reconfiguration unit asserts `reconfig_done` and commits the requested
mode. This preserves I2 and I4. Because no new fetch occurs during the drain,
there is no mixed pre/post-mode instruction stream entering the pipeline,
which supports I3 and I4.

## Assertion Traceability

`verif/sva_safety.sv` checks:

- I1 with monotonic retirement-tag assertions and duplicate live-stage tag
  assertions.
- I2 with the safe-boundary mode-change assertion.
- I3 with the fetch-gating assertion.
- I4 with the stable-mode-while-active assertion.
- I5 with the `RECONFIG_STALL_BOUND` assertion.

`verif/cov_safety.sv` tracks:

- phases visited
- requested mode-transition pairs
- hazards overlapping with reconfiguration
- back-to-back reconfiguration requests
- reconfiguration followed by branch or load-use interactions

`verif/fuzz_runner.py` generates constrained-random instruction streams and
records assertion failures and coverage counters in `results/safety/`.

## What This Does Not Prove

This proof sketch does not prove the full ISA semantics, all forwarding
cases, all memory-ordering behavior, or equivalence against a commercial ARM
processor. It assumes the steady-state hazard and forwarding logic is correct
except where the simulation monitors and ISA reference comparison check it.

The assertion harness is executable evidence, not a complete formal proof.
A stronger version should model instruction conservation across every stage
with a formal solver and should prove the reconfiguration protocol for all
reachable states rather than only simulation traces.
