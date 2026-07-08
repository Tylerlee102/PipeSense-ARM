# Artifact Checklist

Use this checklist before sharing the repository as a paper artifact.

## Local checks without HDL tools

Run:

```bash
python scripts/check_artifact.py
python scripts/estimate_hardware_cost.py
python scripts/check_paper.py
python scripts/build_paper_preview.py
python scripts/verify_paper_preview.py
```

Expected:

- all required files exist
- all source and docs remain ASCII
- Python scripts compile
- analyzer fixture produces valid CSVs
- README contains the research-contract caveats
- paper draft has no unresolved placeholders and matches generated CSV tables when results are present
- generated PDF preview is exactly 5 pages and each page renders with text
- `results/hardware_cost_estimate.csv` is generated
- required safety, sweep, related-work, and synthesis scaffold files exist

## HDL simulation checks

Run after installing a SystemVerilog simulator:

```bash
python scripts/run_sim.py
python scripts/plot_results.py
python scripts/run_sweep.py
python verif/fuzz_runner.py --seeds 500
```

Required before making performance claims:

- every row has `timed_out == 0`
- every row has `safety_faults == 0`
- `results/oracle_gap.csv` exists
- adaptive results are compared against both static normal and best fixed mode
- `results/sweep_adaptive_vs_fixed.csv` reports non-win cells instead of hiding them
- `results/safety/fuzz_summary.csv` reports zero assertion failures, zero safety faults, and zero timeouts
- `results/safety/fuzz_coverage.csv` records the reached interaction buckets; missing buckets should be stated as coverage gaps

## Synthesis/area proxy

Run after installing Yosys:

```bash
python scripts/synth_area_report.py
```

Expected:

- `results/synth/area_summary.csv` exists
- observer/controller/reconfiguration overhead is reported as a percentage of baseline core cells
- paper text labels the result as a generic-cell area proxy

## Optional formal checks

The `formal/` directory contains assertion scaffolding for the reconfiguration unit and an abstract instruction-token conservation harness. With SymbiYosys/Yosys installed, the intended commands are:

```bash
sby -f formal/reconfig_unit.sby
sby -f formal/token_conservation.sby
```

The token-conservation job proves the abstract token model, not the full RTL core. Treat failures as design or harness issues to investigate, not as paper-ready full-core formal evidence.
