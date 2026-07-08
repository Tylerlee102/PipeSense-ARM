# Artifact Status

## Currently complete

- ARM-like educational five-stage pipeline RTL
- Observer, controller, and reconfiguration modules
- Synthetic benchmark testbench plus Dhrystone/CoreMark-style toy ports and generated-style DSP/control kernels
- Static and adaptive mode matrix
- CSV parser and plotting scripts
- Result validator and requirements traceability audit
- Sequential ISA reference model, benchmark disassembly generator, and HDL/reference retired-count comparator
- Oracle best-fixed comparison
- Sweep script across observer window, threshold profile, and residency
- Ablation script for observer-disabled, controller-disabled, and zero-cost reconfiguration headroom rows
- Analytical hardware-cost estimate
- Yosys generic-cell synthesis scaffold
- Simulation-time safety monitor output
- Bindable safety assertion monitor and functional coverage counters in `verif/`
- Constrained-random safety generator and fuzz runner
- Formal-property scaffold for the reconfiguration unit and abstract instruction-token conservation
- Documentation for methodology, critique, threats, and reproducibility
- IEEE-style six-page workshop manuscript source and bibliography in `paper/`
- Generated six-page PDF preview path through `scripts/build_paper_preview.py`
- Local artifact checker that does not require HDL tools
- Ubuntu CI workflow for full simulation on a machine with package installation
- Dockerfile for a reproducible Ubuntu/Icarus/Yosys environment

## Locally verified in this environment

- Python scripts compile.
- `scripts/lint_sv.py` passes repository-specific SystemVerilog contract checks.
- `scripts/audit_requirements.py` passes the deliverable traceability audit.
- `scripts/check_benchmark_parity.py` passes through the artifact checker.
- `scripts/check_artifact.py` passes.
- `scripts/isa_reference.py` runs through the artifact checker.
- `scripts/run_sim.py` passes full HDL simulation for all 60 benchmark/mode cases using Icarus Verilog.
- `scripts/validate_results.py` passes on the generated HDL CSVs.
- `scripts/compare_reference.py` passes, matching HDL retired counts and final architectural data-state hashes against the sequential ISA reference model.
- `scripts/run_sweep.py` passes the 27-configuration observer-window/threshold-profile/min-residency sweep and saves per-setting CSVs under `results/sweeps/`.
- `scripts/run_ablations.py` passes and generates `results/ablation_summary.csv`; observer-disabled and controller-disabled each total 1,563 adaptive cycles, while the analytical zero-cost reconfiguration row totals 1,426 cycles.
- `verif/fuzz_runner.py --seeds 500` passes with the default 96-instruction random programs: 500 seeds, 2,500 mode-result rows, zero assertion failures, zero safety faults, and zero timeouts.
- `sby -f -d formal/results/no_double_commit_across_mode_switch formal/no_double_commit_across_mode_switch.sby` passes as a bounded k=16 abstract proof.
- `scripts/estimate_hardware_cost.py` generates `results/hardware_cost_estimate.csv`.
- `scripts/synth_area_report.py` runs with local Yosys and generates a non-placeholder `results/synth/area_summary.csv`.
- `scripts/plot_results.py` generates base plots plus sensitivity and reconfiguration-overhead plots.
- `scripts/check_paper.py` passes, matching the manuscript tables to generated CSVs and checking citation keys.
- `scripts/verify_paper_preview.py` passes on an exactly 6-page generated PDF preview.

## Not locally verified in this environment

- Full-core formal proof runs bound directly to `arm_like_core`.

## Next checkpoints for a stronger paper artifact

For a stronger workshop submission, the next checkpoint is:

1. Run `python scripts/run_sim.py`.
2. Confirm all rows have `timed_out == 0` and `safety_faults == 0`.
3. Run `python scripts/run_sweep.py`.
4. Keep verification and workload citations aligned with new claims.
5. Keep `python verif/fuzz_runner.py --seeds 500` passing after RTL or assertion edits.
6. Regenerate `results/synth/area_summary.csv` through the CI or local Yosys after RTL or proxy changes.

## CI path

`.github/workflows/ci.yml` defines the intended continuous-integration path for a normal Ubuntu runner: run no-simulator artifact checks, install Icarus Verilog, run HDL simulation, validate CSVs, and upload generated results. The safety fuzz and Yosys area paths are available as local commands and can be added to CI once runtime budget is acceptable.
