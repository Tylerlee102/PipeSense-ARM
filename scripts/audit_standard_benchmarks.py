#!/usr/bin/env python3
"""Record whether this repository can honestly run full standard benchmarks."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "standard_benchmarks"


def main() -> int:
    defines = (ROOT / "rtl" / "defines.svh").read_text(encoding="utf-8")
    core = (ROOT / "rtl" / "arm_like_core.sv").read_text(encoding="utf-8")
    required_ops = ["OP_NOP", "OP_ADD", "OP_SUB", "OP_AND", "OP_ORR", "OP_EOR",
                    "OP_LDR", "OP_STR", "OP_B", "OP_CMP", "OP_HALT"]
    facts = {
        "implemented_operations": [name for name in required_ops if name in defines],
        "operation_count": sum(name in defines for name in required_ops),
        "pc_width_bits": 8,
        "imem_words": 256,
        "dmem_words": 256,
        "word_bits": 32,
        "c_compiler": "unavailable",
        "compiler_version": "unavailable",
        "compiler_flags": "unavailable",
        "assembler": "unavailable",
        "linker": "unavailable",
        "abi_runtime": "unavailable",
        "memory_initialization": (
            "Synthesis: reset-time program_write_en interface in pipesense_fpga_top; "
            "simulation: SystemVerilog hierarchical load tasks"
        ),
        "loader_interface_present": all(
            token in core for token in ("program_write_en", "program_select_dmem", "program_addr", "program_wdata")
        ),
    }
    benchmarks = [
        {
            "benchmark": "CoreMark",
            "version": "1.0",
            "source": "https://github.com/eembc/coremark",
            "input_configuration": "official validation configuration; >=2000 timed iterations requested",
        },
        {
            "benchmark": "Dhrystone",
            "version": "2.1",
            "source": "https://www.netlib.org/benchmark/dhry-c",
            "input_configuration": "full version 2.1 source; timed iteration count not selected",
        },
        {
            "benchmark": "Embench",
            "version": "not integrated",
            "source": "https://github.com/embench/embench-iot",
            "input_configuration": "not run",
        },
        {
            "benchmark": "MiBench",
            "version": "not integrated",
            "source": "https://vhosts.eecs.umich.edu/mibench/",
            "input_configuration": "not run",
        },
    ]
    for row in benchmarks:
        row.update(
            {
                "status": "blocked_not_run",
                "actual_standard_source_executed": "no",
                "compiler_version": "unavailable",
                "compiler_flags": "unavailable",
                "iterations": "not run",
                "raw_result": "unavailable",
                "reason": "No compatible C toolchain, ABI/runtime, or sufficient ISA support",
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(benchmarks[0])
    with (OUT / "capability_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(benchmarks)
    (OUT / "capability_audit.json").write_text(
        json.dumps({"hardware_facts": facts, "benchmarks": benchmarks}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS capability audit: {len(benchmarks)} standard suites are explicitly blocked_not_run")
    print(f"Wrote {OUT / 'capability_audit.csv'}")
    print(f"Wrote {OUT / 'capability_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
