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
python scripts/sweep_params.py --iverilog /path/to/iverilog --vvp /path/to/vvp
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
- `results/sweep_summary.csv` and `results/sweeps/<setting>/...` after parameter sweeps

Before using results in a paper, confirm:

- `timed_out == 0` for every row
- `safety_faults == 0` for every row
- adaptive mode is compared against both normal mode and best fixed mode

## Level 3: formal/synthesis evidence

The `formal/` directory contains a starting SymbiYosys harness for the reconfiguration unit:

```bash
sby -f formal/reconfig_unit.sby
```

This is not yet a complete proof of the whole processor. Treat it as a starting point for the safe-reconfiguration argument.

For synthesis evidence, add a real flow and report:

- tool and version
- target FPGA or process
- baseline core registers/LUTs/cells
- PipeSense observer/controller/reconfiguration overhead
- timing impact
- power or toggle-based activity estimate

## Environment notes

The Python scripts are intentionally standard-library first. `matplotlib` is optional for plots. If it is not installed, `scripts/plot_results.py` writes a text fallback instead.
