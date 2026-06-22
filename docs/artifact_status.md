# Artifact Status

## Currently complete

- ARM-like educational five-stage pipeline RTL
- Observer, controller, and reconfiguration modules
- Synthetic benchmark testbench
- Static and adaptive mode matrix
- CSV parser and plotting scripts
- Result validator and requirements traceability audit
- Sequential ISA reference model, benchmark disassembly generator, and HDL/reference retired-count comparator
- Oracle best-fixed comparison
- Parameter sweep script
- Analytical hardware-cost estimate
- Simulation-time safety monitor output
- Formal-property scaffold for the reconfiguration unit
- Documentation for methodology, critique, threats, and reproducibility
- IEEE-style 8-page extended manuscript source and bibliography in `paper/`
- Generated 8-page PDF preview path through `scripts/build_paper_preview.py`
- Local artifact checker that does not require HDL tools
- Ubuntu CI workflow for full simulation on a machine with package installation
- Dockerfile for a reproducible Ubuntu/Icarus/Yosys environment

## Locally verified in this environment

- Python scripts compile.
- `scripts/lint_sv.py` passes repository-specific SystemVerilog contract checks.
- `scripts/audit_requirements.py` passes the original-deliverable traceability audit.
- `scripts/check_benchmark_parity.py` passes through the artifact checker.
- `scripts/check_artifact.py` passes.
- `scripts/isa_reference.py` runs through the artifact checker.
- `scripts/run_sim.py` passes full HDL simulation for all 36 benchmark/mode cases using Icarus Verilog.
- `scripts/validate_results.py` passes on the generated HDL CSVs.
- `scripts/compare_reference.py` passes, matching HDL retired counts and final architectural data-state hashes against the sequential ISA reference model.
- `scripts/sweep_params.py` passes the 3x3 observer-window/min-residency sweep and saves per-setting CSVs under `results/sweeps/`.
- `scripts/estimate_hardware_cost.py` generates `results/hardware_cost_estimate.csv`.
- `scripts/plot_results.py` runs; this local environment lacks `matplotlib`, so it generated the intended text fallback at `results/plot_results.txt`.
- `scripts/check_paper.py` passes, matching the manuscript tables to generated CSVs and checking citation keys.
- `scripts/verify_paper_preview.py` passes on an exactly 8-page generated PDF preview.

## Not locally verified in this environment

- Formal proof, because `sby`/Yosys are not installed.
- Synthesis, because no synthesis flow has been configured.

## Next checkpoints for a stronger paper artifact

For a stronger workshop submission, the next checkpoint is:

1. Run `python scripts/run_sim.py`.
2. Confirm all rows have `timed_out == 0` and `safety_faults == 0`.
3. Run `python scripts/sweep_params.py`.
4. Replace TODO citation placeholders with real references.
5. Add at least one synthesis or formal result table.

## CI path

`.github/workflows/ci.yml` defines the intended continuous-integration path for a normal Ubuntu runner: run no-simulator artifact checks, install Icarus Verilog, run HDL simulation, validate CSVs, and upload generated results.
