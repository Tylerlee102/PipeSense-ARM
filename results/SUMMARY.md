# PipeSense-ARM Results Summary

Generated in this workspace on 2026-07-08 using the project Docker path.
Host PowerShell did not have `iverilog`, `vvp`, `yosys`, or `apt-get` on PATH.
The Dockerfile installed the required Linux tools with `apt-get`; the container
reported Icarus Verilog 12.0 and Yosys 0.33.

## Scripts Run

| Step | Command | Status |
| --- | --- | --- |
| Tool container | `docker build -t pipesense-arm-readiness .` | PASS |
| Tool versions | `iverilog -V`, `vvp -V`, `yosys -V` in container | PASS |
| Simulation matrix | `python3 scripts/run_sim.py` | PASS: 60 cases, 0 failed |
| Result validation | `python3 scripts/validate_results.py` | PASS |
| Reference comparison | `python3 scripts/compare_reference.py` | PASS |
| Parameter sweep | `python3 scripts/run_sweep.py` | PASS: 27 configs, 1620 result rows |
| Safety fuzz | `python3 verif/fuzz_runner.py --seeds 500` | PASS: 500 seeds, 2500 rows |
| Yosys area proxy | `python3 scripts/synth_area_report.py` | PASS |
| Hardware estimate | `python3 scripts/estimate_hardware_cost.py` | PASS |
| Ablations | `python3 scripts/run_ablations.py` | PASS |
| Paper check | `python3 scripts/check_paper.py` | PASS |
| Paper preview build | `python3 scripts/build_paper_preview.py` | PASS |
| Paper preview verification | `python3 scripts/verify_paper_preview.py` | PASS: exactly 6 pages |
| Artifact check | `python3 scripts/check_artifact.py` | PASS |

## Headline Numbers

All numbers below are copied from generated CSV files under `results/` after
the fresh run. Raw CSV and log files are intentionally not committed.

- Main simulation: 10 benchmarks x 6 modes = 60 rows.
- Simulation safety faults: 0.
- Simulation timeouts: 0.
- Adaptive vs static normal, total cycles: 1499 adaptive vs 1563 static.
- Adaptive vs static normal, total cycle reduction: 4.09%.
- Adaptive vs static normal, average per-benchmark cycle reduction: 3.43%.
- Adaptive vs static normal, average IPC improvement: 3.99%.
- Adaptive vs static normal, total activity-energy proxy reduction: 4.10%.
- Adaptive vs static normal, average per-benchmark activity-energy proxy reduction: 3.50%.
- Adaptive vs best fixed mode, average cycle gap: -14.41%.
- Adaptive vs best fixed mode, average activity-energy proxy gap: -8.43%.
- Safety fuzz: 500 seeds, 2500 mode-result rows, 0 safety faults, 0 assertion failures, 0 timeouts, 0 nonzero return codes.
- Sweep: 27 configurations, 1620 result rows, 0 failed configurations, 1032 adaptive non-win comparison cells recorded.
- Ablation, observer disabled: 1563 adaptive cycles, +4.27% cycles vs full adaptive, 0 safety faults, 0 timeouts.
- Ablation, controller disabled: 1563 adaptive cycles, +4.27% cycles vs full adaptive, 0 safety faults, 0 timeouts.
- Ablation, zero-cost reconfiguration idealization: 1426 adaptive cycles, -4.87% cycles vs full adaptive.
- Yosys generic-cell area proxy: baseline core proxy 1830 cells.
- Yosys generic-cell area proxy: observer/controller/reconfiguration standalone sum 2819 cells.
- Yosys generic-cell area proxy overhead vs core: 154.04%.

## Paper Number Check

`scripts/check_paper.py` passed after the fresh data generation and after the
six-page paper trim. No paper claimed-number mismatches were reported.
`scripts/verify_paper_preview.py` verified an exactly 6-page preview PDF.

## Remaining Blockers

- No data-generation or paper-number blocker prevents a scoped workshop artifact submission.
- The author block still contains placeholder metadata and must be replaced before final venue upload.
- The current venue page limit, template, and institutional formatting still need a human submission check.
- The Yosys result is a generic-cell proxy, not FPGA utilization, timing,
  calibrated power, or ASIC physical area.
- The safety evidence includes simulation assertions, 500-seed fuzzing, and
  bounded/abstract formal scaffolding; it is not a full-core proof.
- The workload evidence is a 10-benchmark prototype suite plus a parameter
  sweep, not a broad compiler-generated embedded benchmark suite.
