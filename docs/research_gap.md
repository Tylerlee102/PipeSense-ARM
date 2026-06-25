# Research Gap

PipeSense-ARM targets the space between static microarchitecture design and
software-managed adaptation. This gap statement is bounded by
`docs/related_work.md`: phase detection, counters, branch handling, memory
latency mitigation, and low-power control are established ideas. The claim
here is the integrated, inspectable hardware-control artifact.

## Common adaptation level

Many adaptive systems operate at the software, firmware, compiler, runtime, operating-system, or DVFS policy level. Those approaches can be powerful, but they often observe behavior indirectly through coarse counters, timer interrupts, or software-visible events. They may also react after a phase has already produced avoidable stalls.

See `docs/related_work.md` for the current literature map and citation TODOs.

## Hardware-resident observer

This prototype places a small observer inside the pipeline. It samples only narrow microarchitectural taps:

- pipeline valid bits
- stall and flush events
- branch-taken events
- load-use hazards
- memory-wait events
- instruction retirement
- cycle count

The observer does not need full instruction traces or heavyweight profiling
support. It keeps rolling-window counters and classifies the current phase
with parameterized threshold logic. `scripts/run_sweep.py` varies these
thresholds so the claim is not tied to one hidden setting.

## Microarchitecture-aware feedback

The observer is aware of pipeline causes, not just total performance. It can distinguish branch-heavy, memory-stall-heavy, load-use-heavy, frontend-stall-heavy, balanced, and idle/low-utilization windows. That matters because each class maps to a different local microarchitectural knob.

## Closed-loop reconfiguration

The controller closes the loop by requesting modes at runtime:

- branch optimization
- memory optimization
- hazard optimization
- low-power gating
- normal mode

The reconfiguration unit then enforces a safe boundary before committing the
mode. This is the key distinction from a pure measurement design: the hardware
both observes and acts. The concrete safety predicate and invariant argument
are in `docs/safety_proof_sketch.md`.

## Safety and bounded-stall angle

Naive adaptive reconfiguration can lose in-flight instructions, duplicate writeback, or cause unbounded stalls. PipeSense-ARM frames safety as a first-class research property:

- stop new fetches before switching
- let in-flight instructions drain
- switch only when the pipeline is empty and no memory wait is active
- count reconfiguration penalty
- expose reconfiguration count and penalty in evaluation
- check assertions and interaction coverage in `verif/`

The prototype is intentionally small, but the safety contract is the part that
can scale into a stronger research contribution. The current safety evidence
is executable simulation and assertion scaffolding, not a full formal proof.
