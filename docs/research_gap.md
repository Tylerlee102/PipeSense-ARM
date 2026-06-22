# Research Gap

PipeSense-ARM targets the space between static microarchitecture design and software-managed adaptation.

## Common adaptation level

Many adaptive systems operate at the software, firmware, compiler, runtime, operating-system, or DVFS policy level. Those approaches can be powerful, but they often observe behavior indirectly through coarse counters, timer interrupts, or software-visible events. They may also react after a phase has already produced avoidable stalls.

TODO citation: Add references on software runtime adaptation, phase detection, DVFS governors, and adaptive embedded systems.

## Hardware-resident observer

This prototype places a small observer inside the pipeline. It samples only narrow microarchitectural taps:

- pipeline valid bits
- stall and flush events
- branch-taken events
- load-use hazards
- memory-wait events
- instruction retirement
- cycle count

The observer does not need full instruction traces or heavyweight profiling support. It keeps rolling-window counters and classifies the current phase with simple threshold logic.

## Microarchitecture-aware feedback

The observer is aware of pipeline causes, not just total performance. It can distinguish branch-heavy, memory-stall-heavy, load-use-heavy, frontend-stall-heavy, balanced, and idle/low-utilization windows. That matters because each class maps to a different local microarchitectural knob.

## Closed-loop reconfiguration

The controller closes the loop by requesting modes at runtime:

- branch optimization
- memory optimization
- hazard optimization
- low-power gating
- normal mode

The reconfiguration unit then enforces a safe boundary before committing the mode. This is the key distinction from a pure measurement design: the hardware both observes and acts.

## Safety and bounded-stall angle

Naive adaptive reconfiguration can lose in-flight instructions, duplicate writeback, or cause unbounded stalls. PipeSense-ARM frames safety as a first-class research property:

- stop new fetches before switching
- let in-flight instructions drain
- switch only when the pipeline is empty
- count reconfiguration penalty
- expose reconfiguration count and penalty in evaluation

The prototype is intentionally small, but the safety contract is the part that can scale into a stronger research contribution.
