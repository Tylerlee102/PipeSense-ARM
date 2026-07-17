# Artifact Status

## Currently complete

- ARM-like educational five-stage pipeline RTL
- Observer, controller, and reconfiguration modules
- Synthetic benchmark testbench plus Dhrystone/CoreMark-style toy ports, generated-style DSP/control kernels, and three longer stress workloads
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
- Passing bounded formal jobs for the reconfiguration unit, abstract instruction-token conservation, and no-double-commit model
- Documentation for methodology, critique, threats, and reproducibility
- GitHub-visible result data under `results/`, including `results/SUMMARY.md`
- Local artifact checker that does not require HDL tools
- Ubuntu CI workflow for full simulation on a machine with package installation
- Dockerfile for a reproducible Ubuntu/Icarus/Yosys/SymbiYosys environment

## Locally verified in this environment

- Python scripts compile.
- `scripts/lint_sv.py` passes repository-specific SystemVerilog contract checks.
- `scripts/audit_requirements.py` passes the deliverable traceability audit.
- `scripts/check_benchmark_parity.py` passes through the artifact checker.
- `scripts/check_artifact.py` passes.
- `scripts/isa_reference.py` runs through the artifact checker.
- `scripts/run_sim.py` passes full HDL simulation for all 78 benchmark/mode cases using Icarus Verilog.
- `scripts/validate_results.py` passes on the generated HDL CSVs.
- `scripts/compare_reference.py` passes, matching HDL retired counts and final architectural data-state hashes against the sequential ISA reference model.
- `scripts/run_sweep.py` passes the 27-configuration observer-window/threshold-profile/min-residency sweep and saves per-setting CSVs under `results/sweeps/`.
- `scripts/run_ablations.py` passes and generates `results/ablation_summary.csv`; observer-disabled and controller-disabled each total 3,307 adaptive cycles, while the analytical zero-cost reconfiguration row totals 3,009 cycles.
- `verif/fuzz_runner.py --seeds 500` passes with the default 96-instruction random programs: 500 seeds, 2,500 mode-result rows, zero assertion failures, zero safety faults, and zero timeouts.
- `scripts/estimate_hardware_cost.py` generates `results/hardware_cost_estimate.csv`.
- `scripts/synth_area_report.py` runs with local Yosys and generates a non-placeholder `results/synth/area_summary.csv`.
- `scripts/run_formal.py` passes three bounded jobs at depths 24, 9, and 14.
- `scripts/plot_results.py` generates base plots plus sensitivity and reconfiguration-overhead plots.
- Generated result CSVs and logs are present for the current checked-in run.

## Not locally verified in this environment

- Full-core formal proof runs bound directly to `arm_like_core`.

## Next checkpoints for stronger public data

1. Run `python scripts/run_sim.py`.
2. Confirm all rows have `timed_out == 0` and `safety_faults == 0`.
3. Run `python scripts/run_sweep.py`.
4. Keep verification and workload caveats aligned with new claims.
5. Keep `python verif/fuzz_runner.py --seeds 500` passing after RTL or assertion edits.
6. Regenerate `results/synth/area_summary.csv` through the CI or local Yosys after RTL or proxy changes.

## CI path

`.github/workflows/ci.yml` installs the HDL and formal tools, then runs artifact
checks, simulation, the full sweep, 500-seed fuzzing, ablations, relative
synthesis, bounded formal jobs, and summary consistency before uploading
generated results.
