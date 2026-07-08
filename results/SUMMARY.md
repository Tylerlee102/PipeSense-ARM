# PipeSense-ARM Results Summary

Generated in this workspace on 2026-07-08 using the project Docker path.
Host PowerShell did not have `iverilog`, `vvp`, `yosys`, `sby`, or `apt-get`
on PATH. The Docker image provides Icarus Verilog 12.0 and Yosys 0.33.
SymbiYosys was not available in the Docker path, so formal scaffolds were not
rerun in this pass.

## Scripts Run

| Step | Command | Status |
| --- | --- | --- |
| Tool versions | `iverilog -V`, `vvp -V`, `yosys -V` in container | PASS |
| Simulation matrix | `python3 scripts/run_sim.py` | PASS: 78 cases, 0 failed |
| Result validation | `python3 scripts/validate_results.py` | PASS |
| Reference comparison | `python3 scripts/compare_reference.py` | PASS |
| Parameter sweep | `python3 scripts/run_sweep.py` | PASS: 27 configs, 2,106 result rows |
| Safety fuzz | `python3 verif/fuzz_runner.py --seeds 500` | PASS: 500 seeds, 2,500 rows |
| Yosys area proxy | `python3 scripts/synth_area_report.py` | PASS |
| Hardware estimate | `python3 scripts/estimate_hardware_cost.py` | PASS |
| Ablations | `python3 scripts/run_ablations.py` | PASS |
| Paper check | `python3 scripts/check_paper.py` | PASS: no claimed-number mismatches |
| Paper preview build | `python3 scripts/build_paper_preview.py` | PASS |
| Paper preview verification | `python3 scripts/verify_paper_preview.py` | PASS: exactly 5 pages |
| Artifact check | `python3 scripts/check_artifact.py` | PASS |
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
- Yosys generic-cell area proxy: baseline core proxy 1,830 cells.
- Yosys generic-cell area proxy: observer/controller/reconfiguration standalone sum 2,885 cells, 157.65% of baseline core proxy.
- Yosys integrated generic-cell proxy: 4,850 cells, 165.03% delta over baseline core proxy.
- Paper preview: exactly 5 generated pages.

## Paper and Citation Check

`scripts/check_paper.py` passed after the 13-workload data generation and
five-page paper trim. No paper claimed-number mismatches were reported.
All cited bibliography keys are present in `paper/references.bib`; no citation
was flagged as unverified in the manuscript.

## Remaining Blockers

- No data-generation or paper-number blocker prevents a scoped workshop artifact submission.
- Confirm the preferred author name, affiliation, and contact email before final venue upload. The current author block uses the repository Git identity rather than an institutional affiliation supplied by the user.
- Confirm the current URTC template and any institutional formatting requirements before submission.
- The Yosys result is a generic-cell proxy, not FPGA utilization, timing, calibrated power, or ASIC physical area.
- The safety evidence includes simulation assertions, 500-seed fuzzing, and formal scaffolding; SymbiYosys was not available here, and this is not a full-core proof.
- The workload evidence is a 13-workload toy/stress suite, not a broad compiler-generated embedded benchmark suite.
