# Requirements Traceability

This file maps PipeSense-ARM project goals to repository evidence.

## Repository structure

- RTL modules: `rtl/`
- Testbench and benchmarks: `tb/`
- Simulation and analysis scripts: `scripts/`
- Research documentation: `docs/`
- Optional formal scaffold: `formal/`
- Safety assertions and fuzz regression: `verif/`
- Generic synthesis scaffold: `synth/`
- Parser fixture: `tests/fixtures/`

Automated check: `python scripts/audit_requirements.py`

## Processor model

Evidence:

- `rtl/arm_like_core.sv`
- `rtl/hazard_unit.sv`
- `rtl/forwarding_unit.sv`
- `rtl/perf_counters.sv`
- `rtl/simple_memory.sv`
- `rtl/defines.svh`

The core models a five-stage educational ARM-like pipeline with PC, register file, instruction/data memories, valid bits, stalls, flushes, load-use detection, forwarding, branch handling, and counters.

## Hardware observer

Evidence:

- `rtl/pipeline_observer.sv`
- phase definitions in `rtl/defines.svh`
- threshold parameters in `rtl/arm_like_core.sv`

The observer samples narrow pipeline taps and classifies rolling windows into balanced, branch-heavy, memory-stall, load-use, frontend-stall, and idle/low-utilization phases. Window and threshold settings are parameterized and swept by `scripts/run_sweep.py`.

## Adaptive controller

Evidence:

- `rtl/adaptive_controller.sv`

The controller maps phases to modes, uses stable-phase hysteresis, uses mode-specific minimum residency thresholds, and emits reconfiguration requests.

## Reconfiguration unit

Evidence:

- `rtl/reconfig_unit.sv`
- `formal/reconfig_safety_properties.sv`
- `formal/reconfig_unit_formal_harness.sv`
- `formal/token_conservation_properties.sv`
- `formal/token_conservation_formal_harness.sv`
- `verif/sva_safety.sv`
- `verif/cov_safety.sv`
- `docs/safety_proof_sketch.md`

The reconfiguration unit gates fetch, waits for an empty pipeline and no memory wait, switches modes at a safe boundary, and tracks reconfiguration penalty.

## Microarchitectural modes

Evidence:

- mode definitions in `rtl/defines.svh`
- mode behavior in `rtl/arm_like_core.sv`

Modes are normal, branch optimized, memory optimized, hazard optimized, and low power.

## Evaluation

Evidence:

- `tb/tb_pipesense.sv`
- `tb/benchmark_programs.sv`
- `scripts/run_sim.py`
- `scripts/analyze_results.py`
- `scripts/validate_results.py`
- `scripts/plot_results.py`
- `scripts/run_sweep.py`
- `scripts/sweep_params.py`
- `scripts/isa_reference.py`
- `verif/random_seq_gen.py`
- `verif/fuzz_runner.py`
- `scripts/synth_area_report.py`

The testbench runs 13 benchmarks across six configurations and emits parseable `RESULT` lines. Analysis scripts produce CSVs, oracle comparisons, plots, and validation gates. The sweep preserves observer-window, threshold-profile, residency, and seed dimensions and flags adaptive non-wins.

The ISA reference model executes the benchmark programs sequentially to provide architectural golden outputs before HDL timing is considered.

The fuzz regression generates constrained-random legal programs and records safety/coverage summaries. The synthesis script runs a Yosys generic-cell proxy when Yosys is available.

## Documentation

Evidence:

- `README.md`
- `docs/research_gap.md`
- `docs/related_work.md`
- `docs/paper_outline.md`
- `docs/methodology.md`
- `docs/safety_proof_sketch.md`
- `docs/limitations_and_honesty.md`
- `docs/decisions.md`
- `docs/results_template.md`
- `docs/nsf_grfp_angle.md`
- `docs/reviewer_critique.md`
- `docs/threats_to_validity.md`
- `docs/hardware_realism.md`
- `docs/reproducibility.md`
- `docs/artifact_status.md`

The docs keep claims scoped to an ARM-like educational embedded pipeline prototype and tie verification-related claims to real citations.
