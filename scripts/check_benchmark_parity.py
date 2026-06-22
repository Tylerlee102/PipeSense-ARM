#!/usr/bin/env python3
"""Check that Python ISA-reference benchmarks match tb/benchmark_programs.sv."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import isa_reference as ref  # noqa: E402


TASK_TO_BENCH = {
    "load_arithmetic_heavy": "arithmetic_heavy",
    "load_branch_heavy": "branch_heavy",
    "load_memory_heavy": "memory_heavy",
    "load_load_use_heavy": "load_use_heavy",
    "load_mixed_control": "mixed_control",
    "load_tiny_fir": "tiny_fir",
}

OPCODES = {
    "OP_NOP": ref.OP_NOP,
    "OP_ADD": ref.OP_ADD,
    "OP_SUB": ref.OP_SUB,
    "OP_AND": ref.OP_AND,
    "OP_ORR": ref.OP_ORR,
    "OP_EOR": ref.OP_EOR,
    "OP_LDR": ref.OP_LDR,
    "OP_STR": ref.OP_STR,
    "OP_B": ref.OP_B,
    "OP_CMP": ref.OP_CMP,
    "OP_HALT": ref.OP_HALT,
}

CONDS = {
    "COND_AL": ref.COND_AL,
    "COND_EQ": ref.COND_EQ,
    "COND_NE": ref.COND_NE,
}


def parse_sv_int(token: str) -> int:
    token = token.strip()
    match = re.fullmatch(r"(\d+)'([dDhH])([0-9a-fA-F_]+)", token)
    if match:
        _width, base, value = match.groups()
        return int(value.replace("_", ""), 16 if base.lower() == "h" else 10)
    return int(token, 0)


def split_args(arg_text: str) -> list[str]:
    return [arg.strip() for arg in arg_text.split(",") if arg.strip()]


def parse_instr(expr: str) -> int:
    expr = expr.strip()
    if expr == "enc_halt()":
        return ref.enc_halt()
    match = re.fullmatch(r"(enc_[rib])\((.*)\)", expr)
    if not match:
        raise RuntimeError(f"Unsupported instruction expression: {expr}")
    fn_name, args_text = match.groups()
    args = split_args(args_text)

    if fn_name == "enc_r":
        opcode = OPCODES[args[0]]
        rd = parse_sv_int(args[1])
        rn = parse_sv_int(args[2])
        rm = parse_sv_int(args[3])
        return ref.enc_r(opcode, rd, rn, rm)
    if fn_name == "enc_i":
        opcode = OPCODES[args[0]]
        rd = parse_sv_int(args[1])
        rn = parse_sv_int(args[2])
        imm = parse_sv_int(args[3])
        return ref.enc_i(opcode, rd, rn, imm)
    if fn_name == "enc_b":
        cond = CONDS[args[0]]
        target = parse_sv_int(args[1])
        return ref.enc_b(cond, target)
    raise RuntimeError(f"Unsupported encoder: {fn_name}")


def parse_sv_benchmarks() -> dict[str, tuple[list[int], dict[int, int]]]:
    source = (ROOT / "tb" / "benchmark_programs.sv").read_text(encoding="utf-8")
    parsed: dict[str, tuple[list[int], dict[int, int]]] = {}

    for task_name, bench_name in TASK_TO_BENCH.items():
        match = re.search(
            rf"task automatic {task_name}\(.*?\);\s*(.*?)\nendtask",
            source,
            flags=re.S,
        )
        if not match:
            raise RuntimeError(f"Could not find task {task_name}")
        body = match.group(1)
        data: dict[int, int] = {}
        instrs: list[int] = []

        for data_match in re.finditer(r"dut\.load_data\(([^,]+),\s*([^)]+)\);", body):
            addr = parse_sv_int(data_match.group(1))
            value = parse_sv_int(data_match.group(2))
            data[addr & 0xFF] = ref.u32(value)

        for instr_match in re.finditer(r"dut\.load_instr\(p(?:\+\+)?,\s*(.*?)\);", body):
            instrs.append(parse_instr(instr_match.group(1)))

        parsed[bench_name] = (instrs, data)

    return parsed


def main() -> int:
    sv_programs = parse_sv_benchmarks()
    failures: list[str] = []

    for bench_name in ref.BENCH_ORDER:
        py_program = ref.BENCHMARKS[bench_name]()
        sv_instrs, sv_data = sv_programs[bench_name]

        if py_program.instrs != sv_instrs:
            failures.append(
                f"instruction mismatch for {bench_name}: "
                f"python={len(py_program.instrs)} sv={len(sv_instrs)}"
            )
        if py_program.data != sv_data:
            failures.append(f"data mismatch for {bench_name}: python={py_program.data} sv={sv_data}")

    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1

    print("Benchmark parity check passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
