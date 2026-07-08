# PipeSense-ARM Results Summary

## Environment

- Host PATH did not provide `iverilog`, `vvp`, or `yosys`.
- The repo Dockerfile was built as `pipesense-arm-results` and used for all generated results.
- Container toolchain: Icarus Verilog 12.0, VVP 12.0, Yosys 0.33.
- See `results/ENVIRONMENT_NOTES.md` for the environment record.

## Scripts Run

| Step | Command | Status | Primary outputs |
| --- | --- | --- | --- |
| Core simulation | `python3 scripts/run_sim.py` | Clean | `results/pipesense_results.csv`, `results/adaptive_improvement.csv`, `results/oracle_gap.csv`, `results/reference_model.csv`, `results/run_sim_stdout.txt` |
| Validation | `python3 scripts/validate_results.py` | Clean | `results/validate_results_stdout.txt` |
| Reference comparison | `python3 scripts/compare_reference.py` | Clean | `results/compare_reference_stdout.txt` |
| Full sweep | `python3 scripts/run_sweep.py` | Clean, 27/27 configs return code 0 | `results/sweep_results.csv`, `results/sweep_runs.csv`, `results/sweep_adaptive_vs_fixed.csv`, `results/sweeps/` |
| Ablation summary | `python3 scripts/run_ablations.py` | Clean | `results/ablation_summary.csv`, `results/ablations/`, `results/run_ablations_stdout.txt` |
| Fuzz safety regression | `python3 verif/fuzz_runner.py --seeds 500` | Clean | `results/safety/fuzz_summary.csv`, `results/safety/fuzz_coverage.csv`, `results/safety/fuzz_runner_stdout.txt` |
| Area proxy | `python3 scripts/synth_area_report.py` | Clean | `results/synth/area_summary.csv`, Yosys stat logs |
| Paper cross-check | `python3 scripts/check_paper.py` | Clean after source fix | `results/check_paper_stdout.txt` |

## Resolved Issue

- Initial paper cross-check failed because `scripts/run_sweep.py` left the final sweep setting's top-level `adaptive_improvement.csv` and `oracle_gap.csv` in `results/`, causing the paper-facing adaptive table to mismatch `branch_heavy`.
- Fixed `scripts/run_sweep.py` to restore pre-existing top-level generated tables after writing sweep artifacts.
- Regenerated baseline results, reran the full sweep, regenerated ablations, updated the paper's Yosys area numbers to match the generated CSV, and strengthened `scripts/check_paper.py` to validate the full area table.

## Headline Numbers

- Core HDL run: 60 benchmark/mode rows, 0 failed cases, 0 timeouts, 0 safety faults.
- Adaptive versus static normal aggregate cycles: 1,563 normal cycles vs 1,499 adaptive cycles, a 4.09% cycle reduction.
- Adaptive versus static normal aggregate energy proxy: 8,872 normal vs 8,508 adaptive, a 4.10% reduction.
- Adaptive cycle outcomes: improved on 4 benchmarks, unchanged on 3, worse on 3.
- Best adaptive cycle improvement: `load_use_heavy`, 13.17%.
- Worst adaptive cycle change: `pid_control_codegen`, -4.17%.
- Adaptive versus best fixed oracle aggregate cycles: 1,302 oracle cycles vs 1,499 adaptive cycles, a -15.13% oracle gap.
- Worst oracle gap: `memory_heavy`, -36.73%.
- Fuzz safety regression: 500 seeds, 2,500 result rows, 0 safety faults, 0 assertion failures, 0 timeouts.
- Yosys area proxy: baseline core proxy 1,830 cells; observer/controller/reconfig standalone sum 2,819 cells, 154.04% of the baseline core proxy.

## Paper Cross-Check

- Final `scripts/check_paper.py` result: passed.
- Current mismatches between `paper/pipesense_urtc_8page.tex` and generated CSVs: none found.
- Area table checking is now included in `scripts/check_paper.py`.

## TODOs

- No TODOs remain that block a fully data-backed Results section in this environment.
- Treat the Yosys numbers only as a generic-cell proxy, not calibrated FPGA or ASIC area.
