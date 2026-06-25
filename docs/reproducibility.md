# Reproducibility Notes

## Tool levels

The repository has three levels of reproducibility.

## Level 1: no HDL simulator required

Run:

```bash
python scripts/check_artifact.py
python scripts/estimate_hardware_cost.py
python scripts/isa_reference.py
python scripts/check_benchmark_parity.py
```

This validates repository structure, Python syntax, SystemVerilog contract checks, parser behavior, benchmark reference-model execution, benchmark parity between Python and SystemVerilog, and documentation guardrails.

## Level 2: HDL simulation

Install Icarus Verilog so both `iverilog` and `vvp` are on PATH, then run:

```bash
python scripts/run_sim.py
python scripts/plot_results.py
```

`scripts/run_sim.py` also runs CSV validation, generates the ISA reference model, and compares HDL retired counts against the reference model.

If `iverilog` and `vvp` are installed outside PATH, pass them explicitly:

```bash
python scripts/run_sim.py --iverilog /path/to/iverilog --vvp /path/to/vvp
python scripts/run_sweep.py --iverilog /path/to/iverilog --vvp /path/to/vvp
python verif/fuzz_runner.py --seeds 500 --iverilog /path/to/iverilog --vvp /path/to/vvp
```

On Ubuntu, the simulator install step is:

```bash
sudo apt-get update
sudo apt-get install -y iverilog
```

On a machine with Docker:

```bash
docker build -t pipesense-arm .
docker run --rm -v "$PWD/results:/workspace/results" pipesense-arm
```

The expected primary outputs are:

- `results/sim_output.txt`
- `results/pipesense_results.csv`
- `results/adaptive_improvement.csv`
- `results/oracle_gap.csv`
- `results/sweep_runs.csv`, `results/sweep_results.csv`, `results/sweep_adaptive_vs_fixed.csv`, and `results/sweeps/<setting>/...` after parameter sweeps
- `results/safety/fuzz_summary.csv` and `results/safety/fuzz_coverage.csv` after the safety regression

Before using results in a paper, confirm:

- `timed_out == 0` for every row
- `safety_faults == 0` for every row
- `assertion_failures == 0` for every fuzz row
- adaptive mode is compared against both normal mode and best fixed mode

## Level 3: formal/synthesis evidence

The `formal/` directory contains a SymbiYosys harness for the reconfiguration unit and an abstract instruction-token conservation job:

```bash
sby -f formal/reconfig_unit.sby
sby -f formal/token_conservation.sby
```

This is not yet a complete proof of the whole processor. Treat the
reconfiguration job as a unit-level safety scaffold and the token-conservation
job as a proof over an abstract five-stage token model.

For generic synthesis evidence, install Yosys and run:

```bash
python scripts/synth_area_report.py
```

Expected output:

- `results/synth/area_summary.csv`
- `results/synth/*_yosys_stat.txt`

Report:

- tool and version
- generic-cell mapping note
- baseline core cell count proxy
- PipeSense observer/controller/reconfiguration cell count proxy
- overhead as a percentage of the baseline core

Do not report this as calibrated FPGA/ASIC area, timing, or power.

## Environment notes

The Python scripts are intentionally standard-library first. `matplotlib` is optional for plots. If it is not installed, `scripts/plot_results.py` writes a text fallback instead.
