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

I1b. Instruction-token conservation:
for the abstract five-stage token model, every fetched token is exactly one of
three states: live in a pipeline stage, retired from writeback, or flushed. No
token may be counted in more than one state, and no live stages may share a tag.

I1c. No double commit across a mode switch:
for the abstract drain-before-switch token model in
`formal/no_double_commit_across_mode_switch.sv`, a tag that has committed
before a visible mode switch cannot commit again after the switch. This is
proven as a bounded formal property for k=16 cycles by
`formal/no_double_commit_across_mode_switch.sby`.

I2. Safe mode commit:
`current_mode` changes only on a cycle where the safe boundary holds and
`reconfig_done` is asserted.

I3. Fetch gating during transition:
when `reconfig_active` is asserted, `reconfig_stop_fetch` is asserted.

I4. No torn mode state:
while `reconfig_active` remains asserted, the visible mode remains equal to
the mode captured at the start of the transition.

I5. Bounded reconfiguration penalty:
the bindable safety monitor counts consecutive `reconfig_active` cycles and
asserts that the configured bound is not exceeded. The current fuzz harness
uses 32 cycles by default. This verification-only counter is not present in
the production reconfiguration RTL and is not a technology timing result.

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
pipeline is empty and no memory wait is active. On the cycle where the safe
boundary holds, the reconfiguration unit asserts `reconfig_done` and commits the requested
mode. This preserves I2 and I4. Because no new fetch occurs during the drain,
there is no mixed pre/post-mode instruction stream entering the pipeline,
which supports I3 and I4.

## Assertion Traceability

`verif/sva_safety.sv` checks:

- I1 with monotonic retirement-tag assertions and duplicate live-stage tag
  assertions across all live stage pairs.
- I2 with the safe-boundary mode-change assertion.
- I3 with the fetch-gating assertion.
- I4 with the stable-mode-while-active assertion.
- I5 with the `RECONFIG_STALL_BOUND` assertion.

`formal/token_conservation_properties.sv` and
`formal/token_conservation_formal_harness.sv` turn I1b into a bounded formal
job. The harness abstracts opcode semantics away and symbolically explores
fetch, stall, flush, and retirement choices. The central assertion is that the
live-token count plus retired-token count plus flushed-token count equals the
number of fetched tokens. It also asserts pairwise live-token uniqueness,
stage-ordering of younger and older tags, and writeback-token retirement.
Run it with:

```bash
sby -f formal/token_conservation.sby
```

`formal/no_double_commit_across_mode_switch.sv` turns I1c into an executable
bounded proof. The harness abstracts instruction semantics but preserves the
drain-before-switch protocol: fetch is gated while a mode change is active,
the visible mode changes only when the abstract pipeline is empty, retiring
tags are recorded, and post-switch retirement is checked against the
pre-switch committed-tag set. The current passing run is bounded to k=16
cycles and writes its proof log under
`formal/results/no_double_commit_across_mode_switch/`:

```bash
sby -f -d formal/results/no_double_commit_across_mode_switch formal/no_double_commit_across_mode_switch.sby
```

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

The assertion harness is executable evidence, not a complete proof of the
whole processor. The no-double-commit proof is bounded to k=16 and proves an
abstract token model with flush held off; it does not yet bind directly to
`arm_like_core`. The token-conservation formal job targets a related abstract
model, but it also does not yet connect every instruction in the full RTL core
to that abstraction. A stronger version should bind token-conservation and
no-double-commit properties directly into a reduced formal instance of
`arm_like_core` and should prove the reconfiguration protocol for all reachable
core states rather than only simulation traces.
