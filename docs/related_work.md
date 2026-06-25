# Related Work

PipeSense-ARM sits at the intersection of phase detection, adaptive
microarchitecture, hardware performance monitoring, and safety checking for
runtime hardware control. The important novelty boundary is that none of
those areas is new by itself.

## Phase Detection and Classification

Program phase behavior has been studied as a way to identify recurring
regions of execution with similar microarchitectural behavior. Sherwood,
Perelman, Hamerly, and Calder studied automatic phase characterization using
program behavior signatures. Dhodapkar and Smith studied working-set
signatures for detecting phase changes and managing multi-configuration
hardware.

PipeSense-ARM is much smaller and narrower. It does not build long program
signatures or train a classifier. It samples a small set of direct pipeline
events over a short rolling window and classifies the current bottleneck with
threshold logic.

## Adaptive Microarchitecture and Counters

Prior work has explored adapting hardware structures such as memory
hierarchies, branch behavior, clocking, and power-management policies based on
runtime behavior. Balasubramonian et al. studied reconfigurable memory
hierarchies. Wattch and related architectural power-modeling work made
microarchitectural activity visible for design exploration. Isci and
Martonosi studied runtime power monitoring using hardware counters.

PipeSense-ARM borrows the general idea that microarchitectural events can
drive policy, but it intentionally uses a tiny observer and a small in-order
core rather than a full-system runtime manager.

## Branch, Memory, and Hazard Knobs

The mode knobs in PipeSense-ARM are not individually novel. Earlier branch
handling policies, static prediction, memory buffering, forwarding, and
low-activity modes are standard computer architecture ideas. The branch mode
should be read as a simple earlier-resolution/static-policy model, the memory
mode as a simulation-level wait-mitigation approximation, and the low-power
mode as an activity proxy.

## Verification of Runtime Reconfiguration

Assertion-based verification is the right style of evidence for the safety
claim because the risk is not only performance loss; it is lost instructions,
duplicated writeback, torn mode state, or unbounded stalls.

[TODO: CITE - find a specific assertion-based verification or formal
verification paper for dynamically reconfigurable or adaptive processor
control. This placeholder should not be replaced by a vague citation.]

## Precise Novelty Claim

The defensible novelty claim is the integrated artifact: a minimal always-on
hardware observer, threshold phase classifier, hysteretic hardware controller,
bounded drain-before-switch reconfiguration path, executable safety checks,
and sweep-based evaluation inside one small educational ARM-like in-order
pipeline.

PipeSense-ARM should not claim that phase detection, counters, branch
optimization, memory buffering, forwarding, or low-power gating are new on
their own.
