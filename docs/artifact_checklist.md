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
- generated PDF preview is exactly 8 pages and each page renders with text
- `results/hardware_cost_estimate.csv` is generated

## HDL simulation checks

Run after installing a SystemVerilog simulator:

```bash
python scripts/run_sim.py
python scripts/plot_results.py
```

Required before making performance claims:

- every row has `timed_out == 0`
- every row has `safety_faults == 0`
- `results/oracle_gap.csv` exists
- adaptive results are compared against both static normal and best fixed mode

## Optional formal checks

The `formal/` directory contains assertion scaffolding for the reconfiguration unit. With SymbiYosys/Yosys installed, the intended command is:

```bash
sby -f formal/reconfig_unit.sby
```

This is a scaffold, not a completed proof package. Treat failures as design or harness issues to investigate, not as paper-ready formal evidence.
