# PipeSense-ARM

PipeSense-ARM is a research-prototype repository for an ARM-like educational embedded processor pipeline with a small hardware-resident observer/controller. The design is intentionally sequential, pipeline-based, closed-loop, and microarchitecture-aware.

It is not a commercial ARM processor and it does not implement the full ARM
ISA. It is not an ML-based classifier and it is not a calibrated power model.
It is a compact SystemVerilog model for exploring this research question:

> Can a tiny hardware observer inside an ARM-like embedded processor detect pipeline phases and safely reconfigure pipeline behavior to reduce stalls, improve IPC, and bound reconfiguration overhead?

## Architecture

```text
              observer taps
                  |
                  v
+------+    +------+    +------+    +------+    +------+
|  IF  | -> |  ID  | -> |  EX  | -> | MEM  | -> |  WB  |
+------+    +------+    +------+    +------+    +------+
   |          |          |          |          |
   +----------+----------+----------+----------+
                  |
                  v
        +-------------------+
        | pipeline_observer |
        +-------------------+
                  |
                  v
       +---------------------+
       | adaptive_controller |
       +---------------------+
                  |
                  v
          +---------------+
          | reconfig_unit |
          +---------------+
                  |
                  v
       current microarchitectural mode
```

## What makes it different from combinational optimization

This project is not a combinational logic minimization exercise. The core has architectural state, pipeline valid bits, hazards, flushes, memory waits, writeback, counters, and a feedback controller. The observer classifies behavior over rolling windows and the controller requests runtime mode changes. The reconfiguration unit then gates fetch and drains the pipeline before switching modes, so the adaptive mechanism is part of the sequential machine.

## Simplified ISA

Instructions are 32-bit educational encodings inspired by ARM/RISC style:

```text
[31:28] opcode
[27:24] rd or branch condition
[23:20] rn
[19:16] rm
[15:0]  immediate or branch target
```

Supported operations:

- `ADD`, `SUB`, `AND`, `ORR`, `EOR`
- `LDR`, `STR`
- `B` with simplified `AL`, `EQ`, and `NE` conditions
- `CMP`
- `NOP`
- `HALT`, a simulation-only sentinel used by the testbench

## Adaptive modes

- `MODE_NORMAL`: default forwarding, branch handling, and memory behavior.
- `MODE_BRANCH_OPT`: resolves branches earlier in the model and reduces flush cost.
- `MODE_MEMORY_OPT`: suppresses the periodic memory wait model to represent a tiny buffer/prefetch effect.
- `MODE_HAZARD_OPT`: enables an aggressive load-result bypass path and reduces load-use stalls.
- `MODE_LOW_POWER`: reduces the activity-energy proxy during low-utilization operation.

## Baselines

The testbench evaluates six configurations:

- `static_normal`
- `fixed_branch`
- `fixed_memory`
- `fixed_hazard`
- `fixed_low_power`
- `adaptive_pipesense`

The important comparisons are adaptive versus `static_normal` and adaptive versus the best fixed mode for each benchmark. The second comparison is stricter because it asks whether adaptation can approach an oracle static choice without knowing the workload in advance.

## How to run

The repository has a no-simulator sanity path and a full HDL simulation path.

No-simulator checks:

```bash
python scripts/check_artifact.py
python scripts/estimate_hardware_cost.py
```

The easiest path is:

```bash
python scripts/run_sim.py
```

That script expects Icarus Verilog (`iverilog` and `vvp`) on your path. It compiles the SystemVerilog testbench, runs all benchmark/mode combinations, saves the simulator log, and then runs the CSV analyzer.

If the tools are installed but not on PATH, pass them explicitly:

```bash
python scripts/run_sim.py --iverilog /path/to/iverilog --vvp /path/to/vvp
```

Optional plotting:

```bash
python scripts/plot_results.py
```

Or, on systems with `make`:

```bash
make all
```

Optional parameter sweep and hardware-cost estimate:

```bash
python scripts/run_sweep.py
python scripts/run_ablations.py
python scripts/estimate_hardware_cost.py
python scripts/synth_area_report.py
```

The sweep script accepts the same `--iverilog` and `--vvp` options. It sweeps
observer window size, threshold profile, and minimum mode residency. Each
sweep setting is copied under `results/sweeps/<setting>/`.
The ablation script also accepts the simulator paths through the environment
used by `scripts/run_sim.py` and writes `results/ablation_summary.csv`.

Safety regression:

```bash
python verif/fuzz_runner.py --seeds 500
```

For a quick smoke test:

```bash
python verif/fuzz_runner.py --seeds 5
```

The safety regression generates constrained-random legal instruction streams,
binds the safety monitor and coverage counter modules, and writes pass/fail
and coverage summaries under `results/safety/`. The current 500-seed local
run produced 2,500 mode-result rows with zero assertion failures, zero safety
faults, and zero timeouts.

Generic synthesis/area proxy:

```bash
python scripts/synth_area_report.py
```

This requires Yosys. The current local run reports 1,830 cells for the
baseline core proxy and 3,087 standalone cells for the observer, controller,
and reconfiguration modules combined, or 168.69% of the baseline core proxy.
The output is a relative generic-cell area proxy, not calibrated ASIC area,
FPGA utilization, timing, or power.

Container path, on a machine with Docker:

```bash
docker build -t pipesense-arm .
docker run --rm -v "%cd%/results:/workspace/results" pipesense-arm
```

Artifact checks that do not need an HDL simulator:

```bash
python scripts/check_artifact.py
python scripts/lint_sv.py
python scripts/audit_requirements.py
python scripts/check_benchmark_parity.py
python scripts/isa_reference.py
python scripts/check_paper.py
```

## Paper draft

The `paper/` directory contains an IEEE-style 8-page extended manuscript source:

- `paper/pipesense_urtc_8page.tex`
- `paper/references.bib`
- `paper/README.md`

Run `python scripts/check_paper.py` to verify that the paper has no unresolved placeholders, cites bibliography keys that exist, preserves claim-discipline language, and matches the generated result CSVs where local results are available. Recent MIT URTC guidance has used a 5-page paper limit, so treat this as an extended/master draft unless your current submission instructions allow 8 pages.

To generate and verify an 8-page PDF preview without LaTeX:

```bash
python scripts/build_paper_preview.py
python scripts/verify_paper_preview.py
```

The preview is written to `output/pdf/pipesense_urtc_8page_preview.pdf` and rendered page images are written under `output/pdf/rendered/`.

## Expected outputs

Simulation and analysis create:

- `results/sim_output.txt`: raw simulator output with one `RESULT` line per run.
- `results/pipesense_results.csv`: benchmark, mode, cycle, IPC, stall, flush, memory wait, load-use, reconfiguration, and energy proxy metrics.
- `results/adaptive_improvement.csv`: adaptive PipeSense comparison against static normal mode.
- `results/oracle_gap.csv`: adaptive PipeSense comparison against the best fixed mode per benchmark.
- `results/ablation_summary.csv`: observer-disabled, controller-disabled, and zero-cost reconfiguration ablation summary.
- `results/ablations/<variant>/pipesense_results.csv`: per-variant ablation result tables.
- `results/sweep_runs.csv`: sweep configuration log from `scripts/run_sweep.py`.
- `results/sweep_results.csv`: all per-run simulation rows with sweep dimensions preserved.
- `results/sweep_adaptive_vs_fixed.csv`: adaptive versus every fixed baseline for every swept cell, including non-wins.
- `results/sweeps/<setting>/pipesense_results.csv`: per-setting sweep tables.
- `results/safety/fuzz_summary.csv`: constrained-random safety regression results by seed and mode.
- `results/safety/fuzz_coverage.csv`: phase, transition, and interaction coverage counters by seed.
- `results/synth/area_summary.csv`: Yosys generic-cell area proxy summary.
- `results/hardware_cost_estimate.csv`: analytical first-order observer/controller/reconfiguration cost estimate.
- `results/reference_model.csv`: sequential ISA golden-model outcomes for every benchmark.
- `results/benchmark_disassembly.txt`: disassembly of the benchmark programs used by the reference model.
- `results/cycles_by_mode.png`: optional plot, if matplotlib is installed.
- `results/ipc_by_mode.png`: optional plot, if matplotlib is installed.
- `results/energy_by_mode.png`: optional plot, if matplotlib is installed.

## Research contribution

PipeSense-ARM demonstrates a hardware-native adaptive control loop for a small embedded pipeline:

- A minimal observer classifies pipeline phases from microarchitectural taps.
- A hysteretic controller chooses runtime modes rather than relying on software policy.
- A reconfiguration unit gates fetch and commits mode changes only at the documented safe boundary.
- Safety monitors and fuzz regressions check retirement tags, fetch gating, safe mode commit, and bounded reconfiguration stalls.
- Benchmarks expose arithmetic-heavy, branch-heavy, memory-heavy, load-use-heavy, mixed-control, tiny FIR-like, Dhrystone-style, CoreMark-style, generated-style DSP, and generated-style embedded-control behavior.

The current novelty claim should stay scoped: this is a hardware-control
research scaffold that combines known ideas in a small, inspectable pipeline.
A stronger paper still needs full compiler-generated embedded benchmark ports,
deeper full-core formal proof, and calibrated timing/power evidence before
claiming a broadly new processor technique.

## Simplifications

- The ISA is educational and ARM-like, not ARM-compatible.
- Memory waits are deterministic and synthetic.
- The branch optimization is modeled as earlier branch handling, not a real predictor.
- The memory optimization models a buffer/prefetch effect by mitigating wait requests.
- The hazard optimization models an extra load-result bypass path.
- The energy number is an activity proxy, not a physical power estimate.
- The observer uses threshold logic; no machine learning is implemented.
- The benchmark suite is mostly synthetic and phase-biased, with Dhrystone/CoreMark-style toy ports and two generated-style DSP/control kernels.
- The Yosys flow is a generic-cell area proxy, not a calibrated physical implementation.
- Safety monitoring uses simulation-time tags and assertions; a minimal synthesized design would remove the tags or prove equivalent properties formally.

## Files

```text
rtl/     SystemVerilog core, observer, controller, reconfiguration, and support modules
tb/      Testbench and benchmark programs
scripts/ Simulation, CSV analysis, and plotting helpers
docs/    Research framing and paper-planning documents
formal/  Optional formal/assertion scaffolding for reconfiguration safety
verif/   Safety assertion monitors, coverage counters, and fuzz regression tools
synth/   Yosys generic synthesis scaffold and cell-mapping note
tests/   Parser fixture used by the artifact checker
paper/   IEEE-style extended manuscript source and bibliography
```

## Research Readiness Checklist

- Run the HDL simulation and confirm `safety_faults == 0` for every row.
- Run `python scripts/validate_results.py` after simulation before citing results.
- Run `python scripts/compare_reference.py` after simulation to check HDL retired counts against the ISA reference model.
- Use the Dockerfile or CI workflow when local HDL tools are not installed.
- Run `python scripts/check_artifact.py` before packaging or sharing the artifact.
- Confirm no benchmark has `timed_out == 1`.
- Compare adaptive mode to both `static_normal` and the best fixed mode in `oracle_gap.csv`.
- Run the window, threshold, and residency sweep with `scripts/run_sweep.py`.
- Run the constrained-random safety regression with `verif/fuzz_runner.py`.
- Run the Yosys area proxy with `scripts/synth_area_report.py`.
- Keep the related-work citations current as the verification and workload story evolves.
