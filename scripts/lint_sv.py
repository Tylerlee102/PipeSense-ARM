#!/usr/bin/env python3
"""Lightweight repository-specific SystemVerilog contract checks."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SV_FILES = [
    *sorted((ROOT / "rtl").glob("*.sv")),
    *sorted((ROOT / "tb").glob("*.sv")),
    *sorted((ROOT / "formal").glob("*.sv")),
    *sorted((ROOT / "verif").glob("*.sv")),
]
SVH_FILES = sorted((ROOT / "rtl").glob("*.svh"))

REQUIRED_MODULES = {
    "arm_like_core",
    "pipeline_register",
    "hazard_unit",
    "forwarding_unit",
    "pipeline_observer",
    "adaptive_controller",
    "async03_speculation_controller",
    "pipesense_fpga_top",
    "reconfig_unit",
    "perf_counters",
    "simple_memory",
    "tb_pipesense",
    "reconfig_safety_properties",
    "reconfig_unit_formal_harness",
    "token_conservation_properties",
    "token_conservation_formal_harness",
    "pipesense_core_sva",
    "pipesense_safety_coverage",
}

RESULT_FIELDS = {
    "bench",
    "mode",
    "cycles",
    "retired",
    "ipc_x1000",
    "stalls",
    "flushes",
    "mem_wait",
    "load_use",
    "reconfigs",
    "reconfig_penalty",
    "energy",
    "safety_faults",
    "phase",
    "final_mode",
    "timed_out",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    source = re.sub(r"//.*", "", source)
    return source


def check_balanced_keywords(path: Path) -> None:
    source = strip_comments(text(path))
    pairs = [
        ("module", "endmodule"),
        ("package", "endpackage"),
        ("function", "endfunction"),
        ("task", "endtask"),
        ("generate", "endgenerate"),
    ]
    for start, end in pairs:
        starts = len(re.findall(rf"\b{start}\b", source))
        ends = len(re.findall(rf"\b{end}\b", source))
        if starts != ends:
            fail(f"{path.relative_to(ROOT)} has {starts} {start} and {ends} {end}")


def check_required_modules() -> None:
    found: set[str] = set()
    for path in SV_FILES:
        found.update(re.findall(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)", strip_comments(text(path))))
    missing = sorted(REQUIRED_MODULES - found)
    if missing:
        fail("Missing modules: " + ", ".join(missing))


def check_result_contract() -> None:
    tb = text(ROOT / "tb" / "tb_pipesense.sv")
    match = re.search(r'\$display\("RESULT\s+([^"]+)"', tb, flags=re.S)
    if not match:
        fail("tb_pipesense.sv does not contain a RESULT display contract")
    fields = set(re.findall(r"([A-Za-z0-9_]+)=%", match.group(1)))
    missing = sorted(RESULT_FIELDS - fields)
    if missing:
        fail("RESULT line missing fields: " + ", ".join(missing))

    analyzer = text(ROOT / "scripts" / "analyze_results.py")
    missing_from_analyzer = sorted(field for field in RESULT_FIELDS if f'"{field}"' not in analyzer)
    if missing_from_analyzer:
        fail("Analyzer missing RESULT fields: " + ", ".join(missing_from_analyzer))


def check_core_contract() -> None:
    core = text(ROOT / "rtl" / "arm_like_core.sv")
    for term in [
        "pipeline_observer",
        "adaptive_controller",
        "async03_speculation_controller",
        "reconfig_unit",
        "perf_counters",
        "safety_faults",
        "MODE_BRANCH_OPT",
        "MODE_MEMORY_OPT",
        "MODE_HAZARD_OPT",
        "MODE_LOW_POWER",
        "OBS_BRANCH_THRESHOLD",
        "OBS_MEM_STALL_THRESHOLD",
        "OBS_LOAD_USE_THRESHOLD",
        "OBS_FRONTEND_STALL_THRESHOLD",
        "OBS_IDLE_RETIRE_THRESHOLD",
        "program_write_en",
    ]:
        if term not in core:
            fail(f"arm_like_core.sv missing expected term {term}")


def check_defines_contract() -> None:
    defines = text(ROOT / "rtl" / "defines.svh")
    for term in [
        "PHASE_BALANCED",
        "PHASE_BRANCH_HEAVY",
        "PHASE_MEMORY_STALL",
        "PHASE_LOAD_USE_HAZARD",
        "MODE_NORMAL",
        "MODE_BRANCH_OPT",
        "MODE_MEMORY_OPT",
        "MODE_HAZARD_OPT",
        "MODE_LOW_POWER",
    ]:
        if term not in defines:
            fail(f"defines.svh missing {term}")


def main() -> int:
    for path in [*SV_FILES, *SVH_FILES]:
        check_balanced_keywords(path)
    check_required_modules()
    check_result_contract()
    check_core_contract()
    check_defines_contract()
    print("SystemVerilog contract checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
