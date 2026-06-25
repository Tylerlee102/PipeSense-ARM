# Related Work

PipeSense-ARM sits at the intersection of phase detection, adaptive
microarchitecture, hardware performance monitoring, and safety checking for
runtime hardware control. The important novelty boundary is that none of
those areas is new by itself.

| Area | Representative sources | What they establish | PipeSense-ARM boundary |
| --- | --- | --- | --- |
| Branch policy | Smith 1981 | Control-flow behavior can be measured and exploited by hardware policy. | Uses an early-resolution toy mode, not a realistic predictor. |
| Memory adaptation | Jouppi 1990; Balasubramonian et al. 2000 | Small buffers and configurable memory hierarchies can trade performance and energy. | Uses synthetic wait mitigation, not a cache or real prefetcher. |
| Phase behavior | Sherwood et al. 2002; Dhodapkar and Smith 2002 | Programs have phases that can guide multi-configuration hardware. | Uses short in-core event windows, not signatures or long traces. |
| Power/counter evidence | Wattch; Mudge; Isci and Martonosi | Activity and counters can support architecture energy/policy studies. | Reports an activity proxy, not calibrated physical energy. |
| Safety verification | IEEE 1800; Foster et al.; Clarke et al.; Borgatti et al. | Assertions and formal methods can check runtime hardware control. | Provides simulation monitors and bounded abstract proofs, not full-core formal verification. |
| Artifact methodology | SimpleScalar; Hennessy and Patterson | Architecture claims need executable models, baselines, and quantitative interpretation. | Provides a narrow RTL artifact, not a general-purpose simulator. |

One-sentence claim: PipeSense-ARM's claim is not a new branch, memory, power,
or verification mechanism, but the integration of a tiny in-core phase
observer, hysteretic mode controller, drain-before-switch safety protocol, and
reproducible oracle/ablation evaluation in a compact ARM-like RTL pipeline.

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

SystemVerilog Assertions are part of the IEEE 1800 SystemVerilog standard and
provide a practical way to express clocked safety properties close to RTL
signals. Foster, Krolnik, and Lacey's Assertion-Based Design text gives the
methodological framing: assertions should capture design intent and be usable
both in simulation and formal contexts. Clarke, Emerson, and Sistla's temporal
logic model-checking work is the classic formal foundation for finite-state
property checking, which is directly relevant to bounded pipeline-control
proofs. For reconfigurable hardware systems specifically, Borgatti et al.
describe an integrated design and verification methodology for dynamically
reconfigurable multimedia SoCs that combines formal and semi-formal
verification techniques.

PipeSense-ARM is more modest than that body of work. It now includes
simulation-compatible safety monitors and formal scaffolding for drain,
fetch-gating, mode-commit, and instruction-token conservation properties, but
it should not claim a complete machine-checked proof of the whole processor.

## Precise Novelty Claim

The defensible novelty claim is the integrated artifact: a minimal always-on
hardware observer, threshold phase classifier, hysteretic hardware controller,
bounded drain-before-switch reconfiguration path, executable safety checks,
and sweep-based evaluation inside one small educational ARM-like in-order
pipeline.

PipeSense-ARM should not claim that phase detection, counters, branch
optimization, memory buffering, forwarding, or low-power gating are new on
their own.
