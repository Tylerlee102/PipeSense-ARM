# Limitations and Honesty Log

This file exists to keep the rest of the repository from overclaiming.

## Toy ISA

The ISA is an educational ARM-like subset, not ARM. It supports only a small
set of arithmetic, logical, load/store, branch, compare, no-op, and halt
operations. Results do not imply compatibility with commercial ARM software.

## Single Pipeline Depth

The evaluated design is one five-stage in-order pipeline. The conclusions do
not show that the same controller works for deeper pipelines, out-of-order
cores, superscalar issue, interrupts, exceptions, caches, or speculative
recovery machinery.

## Workload Realism

The benchmark suite contains six synthetic mechanism-characterization tests and
two recognizable toy-ISA ports inspired by Dhrystone and CoreMark. The synthetic
tests isolate branch, memory, load-use, mixed-control, and low-activity
behavior; the toy ports add integer/control and checksum/list-walk structure.
They are still not a publication-standard workload suite by themselves.

The random safety generator stresses legal instruction mixtures and hazard
density, but it is not a replacement for recognizable embedded benchmarks.
A compiler-generated embedded benchmark subset would be stronger future
evidence.

## Energy Proxy

`energy_proxy` is an activity proxy. It is not calibrated watts, joules, or
power. Any paper text must call it an activity-energy proxy unless a real
synthesis and power flow is added.

## Lightweight Claim

The lightweight claim requires evidence. The repository now includes a Yosys
generic synthesis scaffold and an analytical estimator. If Yosys is not
available or cannot synthesize a module, the claim must be limited to the
available analytical or partial synthesis evidence.

## Safety Claim

The simulation monitors and `verif/` assertion harness make the safety story
reviewable, but they are not a full machine-checked proof of the whole core.
The current safe boundary is drain-before-switch. It is conservative and may
overpay performance penalty compared with a more aggressive design.
The 500-seed constrained-random run is useful stress evidence, not exhaustive
coverage; any unhit coverage bucket should be reported as such.

## Baselines

The fixed modes are self-implemented baselines in the same educational core.
They are useful for controlled comparison but should not be presented as prior
published processors or industrial designs.

## Paper Readiness

This artifact is suitable for an undergraduate research paper if the claims
stay modest. It is not enough for a top-tier architecture venue without
recognizable workloads, real synthesis/timing/power evidence, stronger formal
verification, and tighter related-work positioning.
