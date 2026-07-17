# PipeSense-ARM Results Summary

Generated in this workspace on 2026-07-17 using the project Docker path. The
image provides Icarus Verilog 12.0, Yosys 0.33, pinned SymbiYosys, Z3, and
CVC4.

## Scripts Run

| Step | Command | Status |
| --- | --- | --- |
| Tool versions | `iverilog -V`, `vvp -V`, `yosys -V` in container | PASS |
| Simulation matrix | `python3 scripts/run_sim.py` | PASS: 78 cases, 0 failed |
| Result validation | `python3 scripts/validate_results.py` | PASS |
| Reference comparison | `python3 scripts/compare_reference.py` | PASS |
| Parameter sweep | `python3 scripts/run_sweep.py` | PASS: 27 configs, 2,106 result rows |
| Safety fuzz | `python3 verif/fuzz_runner.py --seeds 500` | PASS: 500 seeds, 2,500 rows |
| Bounded formal | `python3 scripts/run_formal.py` | PASS: 3 jobs at depths 24, 9, and 14 |
| Yosys area proxy | `python3 scripts/synth_area_report.py` | PASS |
| Hardware estimate | `python3 scripts/estimate_hardware_cost.py` | PASS |
| Ablations | `python3 scripts/run_ablations.py` | PASS |
| Artifact check | `python3 scripts/check_artifact.py` | PASS |
| Summary consistency | `python3 scripts/check_results_summary.py` | PASS |
| Plot generation | `python3 scripts/plot_results.py` | PASS |

## Headline Numbers

All numbers below are copied from generated CSV files under `results/`.

- Main simulation: 13 benchmarks x 6 modes = 78 rows.
- Simulation safety faults: 0.
- Simulation timeouts: 0.
- Adaptive vs static normal, total cycles: 3,056 adaptive vs 3,307 static.
- Adaptive vs static normal, total cycle reduction: 7.59%.
- Adaptive vs static normal, average per-benchmark cycle reduction: 6.33%.
- Adaptive vs static normal, average IPC improvement: 7.71%.
- Adaptive vs static normal, total activity-energy proxy reduction: 5.78%.
- Adaptive vs static normal, average per-benchmark activity-energy proxy reduction: 5.12%.
- Adaptive cycle outcomes: 9 improved, 3 tied, 1 regressed.
- Regressed adaptive workload: `dsp_fir_codegen` at -1.04% cycles vs static normal.
- Adaptive vs best fixed mode, average cycle gap: -8.90%.
- Adaptive vs best fixed mode, average activity-energy proxy gap: -5.43%.
- Safety fuzz: 500 seeds, 2,500 mode-result rows, 0 safety faults, 0 assertion failures, 0 timeouts, 0 nonzero return codes.
- Sweep: 27 configurations, 2,106 result rows, 0 failed configurations, 478 adaptive win cells, 1,277 adaptive non-win cells.
- Ablation, observer disabled: 3,307 adaptive cycles, +8.21% cycles vs full adaptive, 0 safety faults, 0 timeouts.
- Ablation, controller disabled: 3,307 adaptive cycles, +8.21% cycles vs full adaptive, 0 safety faults, 0 timeouts.
- Ablation, zero-cost reconfiguration idealization: 3,009 adaptive cycles, -1.54% cycles vs full adaptive.
- Yosys generic-cell area proxy: baseline core proxy 1,838 cells.
- Yosys generic-cell area proxy: observer/controller/reconfiguration standalone sum 550 cells, 29.92% of baseline core proxy.
- Yosys integrated generic-cell proxy: 2,380 cells, 29.49% delta over baseline core proxy.
- Bounded formal: production reconfiguration safety passes at depth 24; abstract token conservation passes at depth 9; abstract no-double-commit passes at depth 14.

## Manuscript Scope

The manuscript source and final rendered PDF are checked in under `paper/`, but
they are not built or certified by the CI workflow. This summary reports only
repository-backed simulation, validation, sweep, fuzzing, hardware-cost,
synthesis-proxy, and plotting results. Manuscript claims, citations, page
count, formatting, and submission readiness must be checked separately by the
author.

## Scope and Limitations

- The repository does not certify manuscript page count, citations, author metadata, venue formatting, or submission readiness.
- The Yosys result is a generic-cell proxy, not FPGA utilization, timing, calibrated power, or ASIC physical area.
- The safety evidence includes simulation assertions, 500-seed fuzzing, and three passing bounded formal jobs; this is not a full-core proof.
- The workload evidence is a 13-workload toy/stress suite, not a broad compiler-generated embedded benchmark suite.
