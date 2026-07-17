#!/usr/bin/env python3
"""Audit the repository against the PipeSense-ARM deliverables."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_PATHS = [
    "rtl/arm_like_core.sv",
    "rtl/pipeline_registers.sv",
    "rtl/hazard_unit.sv",
    "rtl/forwarding_unit.sv",
    "rtl/pipeline_observer.sv",
    "rtl/adaptive_controller.sv",
    "rtl/reconfig_unit.sv",
    "rtl/perf_counters.sv",
    "rtl/simple_memory.sv",
    "rtl/defines.svh",
    "tb/tb_pipesense.sv",
    "tb/benchmark_programs.sv",
    "scripts/run_sim.py",
    "scripts/analyze_results.py",
    "scripts/plot_results.py",
    "scripts/run_sweep.py",
    "scripts/run_ablations.py",
    "scripts/synth_area_report.py",
    "scripts/run_formal.py",
    "scripts/isa_reference.py",
    "scripts/compare_reference.py",
    "scripts/check_benchmark_parity.py",
    "docs/methodology.md",
    "docs/safety_proof_sketch.md",
    "docs/limitations_and_honesty.md",
    "docs/decisions.md",
    "docs/results_template.md",
    "formal/reconfig_safety_properties.sv",
    "formal/reconfig_unit_formal_harness.sv",
    "formal/reconfig_unit.sby",
    "formal/token_conservation_properties.sv",
    "formal/token_conservation_formal_harness.sv",
    "formal/token_conservation.sby",
    "verif/sva_safety.sv",
    "verif/cov_safety.sv",
    "verif/random_seq_gen.py",
    "verif/fuzz_runner.py",
    "synth/yosys_synth.tcl",
    "synth/yosys_area_proxy.v",
    "synth/generic_cells.lib_or_note.md",
    "README.md",
    "Makefile",
]

CHECKS = {
    "ISA opcodes": ("rtl/defines.svh", ["OP_ADD", "OP_SUB", "OP_AND", "OP_ORR", "OP_EOR", "OP_LDR", "OP_STR", "OP_B", "OP_CMP", "OP_NOP"]),
    "Pipeline stages": ("README.md", ["IF", "ID", "EX", "MEM", "WB"]),
    "Observer taps": ("rtl/pipeline_observer.sv", ["if_valid", "id_valid", "ex_valid", "mem_valid", "wb_valid", "stall_if", "flush", "branch_taken", "load_use_hazard", "mem_wait", "instruction_retired"]),
    "Observer threshold parameters": ("rtl/arm_like_core.sv", ["OBS_BRANCH_THRESHOLD", "OBS_MEM_STALL_THRESHOLD", "OBS_LOAD_USE_THRESHOLD", "OBS_FRONTEND_STALL_THRESHOLD", "OBS_IDLE_RETIRE_THRESHOLD"]),
    "Phase classes": ("rtl/defines.svh", ["PHASE_BALANCED", "PHASE_BRANCH_HEAVY", "PHASE_MEMORY_STALL", "PHASE_LOAD_USE_HAZARD", "PHASE_FRONTEND_STALL", "PHASE_IDLE_OR_LOW_UTIL"]),
    "Mode classes": ("rtl/defines.svh", ["MODE_NORMAL", "MODE_BRANCH_OPT", "MODE_MEMORY_OPT", "MODE_HAZARD_OPT", "MODE_LOW_POWER"]),
    "Controller hysteresis": ("rtl/adaptive_controller.sv", ["MIN_MODE_RESIDENCY", "PHASE_STABLE_COUNT", "residency_counter", "stable_counter"]),
    "Reconfiguration safety": ("rtl/reconfig_unit.sv", ["pipeline_empty", "mem_wait", "stop_fetch", "reconfig_active", "reconfig_done", "requested_mode_latched"]),
    "Performance metrics": ("tb/tb_pipesense.sv", ["cycles", "retired", "ipc_x1000", "stalls", "flushes", "mem_wait", "load_use", "reconfigs", "reconfig_penalty", "energy", "safety_faults"]),
    "Reference model": ("scripts/isa_reference.py", ["BENCH_ORDER", "run_program", "reference_model.csv", "benchmark_disassembly.txt"]),
    "Reference comparison": ("scripts/compare_reference.py", ["Retired mismatch", "Reference comparison passed"]),
    "Benchmark parity": ("scripts/check_benchmark_parity.py", ["parse_sv_benchmarks", "Benchmark parity check passed"]),
    "Sweep methodology": ("scripts/run_sweep.py", ["THRESHOLD_PROFILES", "sweep_adaptive_vs_fixed.csv", "adaptive_wins_cycles"]),
    "Ablation methodology": ("scripts/run_ablations.py", ["observer_disabled", "controller_disabled", "zero_cost_reconfig", "ablation_summary.csv"]),
    "Safety assertions": ("verif/sva_safety.sv", ["SVA_I1", "SVA_I2", "SVA_I3", "SVA_I4", "SVA_I5"]),
    "Token conservation formal checks": ("formal/token_conservation_properties.sv", ["accounted_count == fetched_count", "retire_tag == wb_tag", "token-level obligations"]),
    "Safety coverage": ("verif/cov_safety.sv", ["phases_seen_mask", "transitions_seen", "hazard_during_reconfig", "back_to_back_reconfig_requests"]),
    "Random safety regression": ("verif/fuzz_runner.py", ["--seeds", "fuzz_summary.csv", "fuzz_coverage.csv"]),
    "Synthesis proxy": ("synth/generic_cells.lib_or_note.md", ["yosys_area_proxy.v", "generic-cell", "full RTL synthesis"]),
    "Honesty log": ("docs/limitations_and_honesty.md", ["Toy ISA", "Energy Proxy", "Safety Claim"]),
    "Benchmarks": ("tb/benchmark_programs.sv", ["load_arithmetic_heavy", "load_branch_heavy", "load_memory_heavy", "load_load_use_heavy", "load_mixed_control", "load_tiny_fir", "load_dhrystone_toy", "load_coremark_toy", "load_dsp_fir_codegen", "load_pid_control_codegen", "load_long_fir_stress", "load_pid_phase_stress", "load_random_mem_latency_stress"]),
    "Baselines": ("tb/tb_pipesense.sv", ["MODE_NORMAL", "MODE_BRANCH_OPT", "MODE_MEMORY_OPT", "MODE_HAZARD_OPT", "MODE_LOW_POWER", "adaptive_pipesense"]),
    "Research docs": ("README.md", ["not a commercial ARM processor", "not an ML-based classifier", "Research contribution", "Simplifications"]),
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail(f"Missing file for requirement check: {rel}")
    return path.read_text(encoding="utf-8")


def check_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        fail("Missing required paths: " + ", ".join(missing))


def check_terms() -> None:
    for name, (rel, terms) in CHECKS.items():
        body = read(rel)
        missing = [term for term in terms if term not in body]
        if missing:
            fail(f"{name} check failed in {rel}; missing " + ", ".join(missing))


def main() -> int:
    check_paths()
    check_terms()
    print("Requirement audit passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
