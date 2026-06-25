# Design Decisions

## Safe Boundary

Decision: define safe commit as `pipeline_empty && !mem_wait_signal`.

Rationale: this is conservative and easy to check. It avoids changing visible
mode while any instruction could still depend on pre-transition forwarding,
branch, or memory behavior.

## Request Versus Commit

Decision: allow the controller to request a transition before the pipeline is
empty, but require the reconfiguration unit to gate fetch and delay the actual
mode commit until the safe boundary.

Rationale: waiting for a naturally empty pipeline before requesting would make
adaptive control ineffective on continuous programs. The safety property is
therefore attached to mode commit, not the first request edge.

## Workload Suite

Decision: keep six synthetic kernels as mechanism-characterization tests, add
Dhrystone-style and CoreMark-style toy-ISA ports for recognizability, add two
generated-style DSP/control streams, and keep a separate constrained-random
safety regression.

Rationale: the synthetic kernels isolate mechanisms cleanly. The random
regression increases safety stress. The toy ports and generated-style kernels
improve external readability, but full compiler-generated embedded benchmark
ports are still needed for stronger external validity.

## Threshold Classifier

Decision: use parameterized threshold logic, not machine learning.

Rationale: threshold logic is transparent, synthesizable, and easy for a
reviewer to inspect. Sensitivity is handled by `scripts/run_sweep.py`.

## Synthesis Evidence

Decision: add a Yosys generic-cell scaffold and keep the older analytical
cost estimator.

Rationale: generic synthesis gives a more concrete lightweight check when
Yosys is available. The analytical estimator remains useful as a tool-free
fallback, but it is weaker evidence.

## Energy Reporting

Decision: report an activity-energy proxy until a calibrated power flow
exists.

Rationale: the current RTL does not include clock tree, placement, routing,
switching activity annotation, or a standard-cell/FPGA power model.
