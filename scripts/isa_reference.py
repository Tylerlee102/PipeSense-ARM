#!/usr/bin/env python3
"""Sequential golden model for the PipeSense educational ISA benchmarks."""

from __future__ import annotations

import argparse
import csv
import zlib
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

OP_NOP = 0x0
OP_ADD = 0x1
OP_SUB = 0x2
OP_AND = 0x3
OP_ORR = 0x4
OP_EOR = 0x5
OP_LDR = 0x6
OP_STR = 0x7
OP_B = 0x8
OP_CMP = 0x9
OP_HALT = 0xF

COND_AL = 0
COND_EQ = 1
COND_NE = 2

OP_NAMES = {
    OP_NOP: "NOP",
    OP_ADD: "ADD",
    OP_SUB: "SUB",
    OP_AND: "AND",
    OP_ORR: "ORR",
    OP_EOR: "EOR",
    OP_LDR: "LDR",
    OP_STR: "STR",
    OP_B: "B",
    OP_CMP: "CMP",
    OP_HALT: "HALT",
}

BENCH_ORDER = [
    "arithmetic_heavy",
    "branch_heavy",
    "memory_heavy",
    "load_use_heavy",
    "mixed_control",
    "tiny_fir",
]


def u32(value: int) -> int:
    return value & 0xFFFFFFFF


def sign16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def enc_r(opcode: int, rd: int, rn: int, rm: int) -> int:
    return u32((opcode << 28) | (rd << 24) | (rn << 20) | (rm << 16))


def enc_i(opcode: int, rd: int, rn: int, imm: int) -> int:
    return u32((opcode << 28) | (rd << 24) | (rn << 20) | (imm & 0xFFFF))


def enc_b(cond: int, target: int) -> int:
    return u32((OP_B << 28) | (cond << 24) | (target & 0xFFFF))


def enc_halt() -> int:
    return u32(OP_HALT << 28)


def decode(instr: int) -> tuple[int, int, int, int, int]:
    opcode = (instr >> 28) & 0xF
    rd = (instr >> 24) & 0xF
    rn = (instr >> 20) & 0xF
    rm = (instr >> 16) & 0xF
    imm = instr & 0xFFFF
    return opcode, rd, rn, rm, imm


def disasm(instr: int) -> str:
    opcode, rd, rn, rm, imm = decode(instr)
    name = OP_NAMES.get(opcode, f"OP{opcode:x}")
    if opcode == OP_CMP:
        return f"CMP r{rn}, r{rm}"
    if opcode in {OP_ADD, OP_SUB, OP_AND, OP_ORR, OP_EOR}:
        return f"{name} r{rd}, r{rn}, r{rm}"
    if opcode == OP_LDR:
        return f"LDR r{rd}, [r{rn}, #{sign16(imm)}]"
    if opcode == OP_STR:
        return f"STR r{rd}, [r{rn}, #{sign16(imm)}]"
    if opcode == OP_B:
        cond = {COND_AL: "AL", COND_EQ: "EQ", COND_NE: "NE"}.get(rd, f"C{rd}")
        return f"B.{cond} {imm}"
    if opcode == OP_HALT:
        return "HALT"
    return name


@dataclass
class Program:
    name: str
    max_cycles: int
    instrs: list[int] = field(default_factory=list)
    data: dict[int, int] = field(default_factory=dict)

    def load_data(self, addr: int, value: int) -> None:
        self.data[addr & 0xFF] = u32(value)

    def emit(self, instr: int) -> None:
        self.instrs.append(u32(instr))


@dataclass
class RunResult:
    bench: str
    halted: bool
    timed_out: bool
    steps: int
    retired: int
    final_pc: int
    zero_flag: bool
    program_words: int
    data_writes: int
    program_crc32: str
    state_crc32: str
    arch_hash: str
    nonzero_regs: str
    touched_memory: str


def branch_condition(cond: int, zero_flag: bool) -> bool:
    if cond == COND_EQ:
        return zero_flag
    if cond == COND_NE:
        return not zero_flag
    return True


def benchmark_arithmetic_heavy() -> Program:
    p = Program("arithmetic_heavy", 600)
    p.load_data(1, 21)
    p.load_data(2, 9)
    p.emit(enc_i(OP_LDR, 1, 0, 1))
    p.emit(enc_i(OP_LDR, 2, 0, 2))
    p.emit(enc_r(OP_ADD, 3, 1, 2))
    p.emit(enc_r(OP_SUB, 4, 3, 2))
    p.emit(enc_r(OP_AND, 5, 3, 4))
    p.emit(enc_r(OP_ORR, 6, 5, 1))
    p.emit(enc_r(OP_EOR, 7, 6, 2))
    p.emit(enc_r(OP_ADD, 8, 7, 3))
    p.emit(enc_r(OP_SUB, 9, 8, 4))
    p.emit(enc_r(OP_AND, 10, 9, 5))
    p.emit(enc_r(OP_ORR, 11, 10, 6))
    p.emit(enc_r(OP_EOR, 12, 11, 7))
    p.emit(enc_r(OP_ADD, 13, 12, 8))
    p.emit(enc_r(OP_SUB, 14, 13, 9))
    p.emit(enc_r(OP_AND, 15, 14, 10))
    p.emit(enc_r(OP_ORR, 3, 15, 11))
    p.emit(enc_r(OP_EOR, 4, 3, 12))
    p.emit(enc_r(OP_ADD, 5, 4, 13))
    p.emit(enc_r(OP_SUB, 6, 5, 14))
    p.emit(enc_r(OP_AND, 7, 6, 15))
    p.emit(enc_r(OP_ORR, 8, 7, 1))
    p.emit(enc_r(OP_EOR, 9, 8, 2))
    p.emit(enc_halt())
    return p


def benchmark_branch_heavy() -> Program:
    p = Program("branch_heavy", 900)
    p.load_data(20, 24)
    p.load_data(21, 1)
    p.emit(enc_i(OP_LDR, 1, 0, 20))
    p.emit(enc_i(OP_LDR, 2, 0, 21))
    p.emit(enc_r(OP_SUB, 1, 1, 2))
    p.emit(enc_r(OP_CMP, 0, 1, 0))
    p.emit(enc_b(COND_NE, 2))
    p.emit(enc_halt())
    return p


def benchmark_memory_heavy() -> Program:
    p = Program("memory_heavy", 1200)
    p.load_data(80, 14)
    p.load_data(81, 1)
    p.load_data(83, 100)
    p.load_data(87, 7)
    p.emit(enc_i(OP_LDR, 1, 0, 80))
    p.emit(enc_i(OP_LDR, 2, 0, 81))
    p.emit(enc_i(OP_LDR, 3, 0, 83))
    p.emit(enc_i(OP_LDR, 4, 0, 87))
    p.emit(enc_r(OP_ADD, 5, 3, 4))
    p.emit(enc_i(OP_STR, 5, 0, 91))
    p.emit(enc_r(OP_SUB, 1, 1, 2))
    p.emit(enc_r(OP_CMP, 0, 1, 0))
    p.emit(enc_b(COND_NE, 2))
    p.emit(enc_halt())
    return p


def benchmark_load_use_heavy() -> Program:
    p = Program("load_use_heavy", 1000)
    p.load_data(100, 18)
    p.load_data(101, 1)
    p.load_data(104, 11)
    p.load_data(105, 13)
    p.emit(enc_i(OP_LDR, 1, 0, 100))
    p.emit(enc_i(OP_LDR, 2, 0, 101))
    p.emit(enc_i(OP_LDR, 3, 0, 104))
    p.emit(enc_r(OP_ADD, 4, 3, 2))
    p.emit(enc_i(OP_LDR, 5, 0, 105))
    p.emit(enc_r(OP_ADD, 6, 5, 4))
    p.emit(enc_r(OP_SUB, 1, 1, 2))
    p.emit(enc_r(OP_CMP, 0, 1, 0))
    p.emit(enc_b(COND_NE, 2))
    p.emit(enc_halt())
    return p


def benchmark_mixed_control() -> Program:
    p = Program("mixed_control", 1100)
    p.load_data(120, 12)
    p.load_data(121, 1)
    p.load_data(122, 5)
    p.load_data(123, 0x000000FF)
    p.emit(enc_i(OP_LDR, 1, 0, 120))
    p.emit(enc_i(OP_LDR, 2, 0, 121))
    p.emit(enc_i(OP_LDR, 3, 0, 122))
    p.emit(enc_i(OP_LDR, 4, 0, 123))
    p.emit(enc_r(OP_ADD, 5, 5, 3))
    p.emit(enc_r(OP_EOR, 6, 5, 4))
    p.emit(enc_i(OP_STR, 6, 0, 127))
    p.emit(enc_r(OP_SUB, 1, 1, 2))
    p.emit(enc_r(OP_CMP, 0, 1, 0))
    p.emit(enc_b(COND_NE, 4))
    p.emit(enc_halt())
    return p


def benchmark_tiny_fir() -> Program:
    p = Program("tiny_fir", 900)
    p.load_data(140, 8)
    p.load_data(141, 1)
    p.load_data(144, 3)
    p.load_data(145, 5)
    p.load_data(146, 8)
    p.load_data(147, 13)
    p.emit(enc_i(OP_LDR, 1, 0, 140))
    p.emit(enc_i(OP_LDR, 2, 0, 141))
    p.emit(enc_i(OP_LDR, 3, 0, 144))
    p.emit(enc_i(OP_LDR, 4, 0, 145))
    p.emit(enc_r(OP_ADD, 7, 3, 4))
    p.emit(enc_i(OP_LDR, 5, 0, 146))
    p.emit(enc_i(OP_LDR, 6, 0, 147))
    p.emit(enc_r(OP_ADD, 8, 5, 6))
    p.emit(enc_r(OP_ADD, 9, 7, 8))
    p.emit(enc_i(OP_STR, 9, 0, 151))
    p.emit(enc_r(OP_SUB, 1, 1, 2))
    p.emit(enc_r(OP_CMP, 0, 1, 0))
    p.emit(enc_b(COND_NE, 2))
    p.emit(enc_halt())
    return p


BENCHMARKS = {
    "arithmetic_heavy": benchmark_arithmetic_heavy,
    "branch_heavy": benchmark_branch_heavy,
    "memory_heavy": benchmark_memory_heavy,
    "load_use_heavy": benchmark_load_use_heavy,
    "mixed_control": benchmark_mixed_control,
    "tiny_fir": benchmark_tiny_fir,
}


def run_program(program: Program) -> RunResult:
    regs = [0] * 16
    memory = dict(program.data)
    pc = 0
    zero_flag = False
    halted = False
    retired = 0
    data_writes = 0
    steps = 0

    while steps < program.max_cycles:
        if pc < 0 or pc >= len(program.instrs):
            break
        instr = program.instrs[pc]
        opcode, rd, rn, rm, imm = decode(instr)
        next_pc = pc + 1
        steps += 1

        if opcode == OP_HALT:
            halted = True
            pc = next_pc
            break
        if opcode == OP_NOP:
            pass
        elif opcode == OP_ADD:
            regs[rd] = u32(regs[rn] + regs[rm])
        elif opcode == OP_SUB:
            regs[rd] = u32(regs[rn] - regs[rm])
        elif opcode == OP_AND:
            regs[rd] = u32(regs[rn] & regs[rm])
        elif opcode == OP_ORR:
            regs[rd] = u32(regs[rn] | regs[rm])
        elif opcode == OP_EOR:
            regs[rd] = u32(regs[rn] ^ regs[rm])
        elif opcode == OP_LDR:
            regs[rd] = u32(memory.get((regs[rn] + sign16(imm)) & 0xFF, 0))
        elif opcode == OP_STR:
            memory[(regs[rn] + sign16(imm)) & 0xFF] = u32(regs[rd])
            data_writes += 1
        elif opcode == OP_CMP:
            zero_flag = (u32(regs[rn] - regs[rm]) == 0)
        elif opcode == OP_B:
            if branch_condition(rd, zero_flag):
                next_pc = imm & 0xFF
        else:
            raise RuntimeError(f"Unsupported opcode 0x{opcode:x} at pc {pc}")

        regs[0] = 0
        pc = next_pc & 0xFF
        retired += 1

    return make_result(program, regs, memory, pc, zero_flag, halted, steps, retired, data_writes)


def crc_words(words: list[int]) -> str:
    data = b"".join(word.to_bytes(4, byteorder="little", signed=False) for word in words)
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"


def fnv_word(seed: int, word: int) -> int:
    value = seed
    for byte_index in range(4):
        value ^= (word >> (byte_index * 8)) & 0xFF
        value = u32(value * 0x01000193)
    return value


def architectural_hash(regs: list[int], memory: dict[int, int], zero_flag: bool) -> str:
    value = 0x811C9DC5
    value = fnv_word(value, int(zero_flag))
    for reg_value in regs:
        value = fnv_word(value, reg_value)
    for addr in range(256):
        value = fnv_word(value, memory.get(addr, 0))
    return f"0x{value:08x}"


def make_result(
    program: Program,
    regs: list[int],
    memory: dict[int, int],
    pc: int,
    zero_flag: bool,
    halted: bool,
    steps: int,
    retired: int,
    data_writes: int,
) -> RunResult:
    program_crc = crc_words(program.instrs)
    mem_items = sorted((addr, value) for addr, value in memory.items() if value != 0)
    state_words = regs + [pc, int(zero_flag), int(halted), retired, data_writes]
    for addr, value in mem_items:
        state_words.extend([addr, value])
    state_crc = crc_words(state_words)
    arch_hash = architectural_hash(regs, memory, zero_flag)
    nonzero_regs = ";".join(f"r{idx}={value}" for idx, value in enumerate(regs) if value != 0)
    touched_memory = ";".join(f"m{addr}={value}" for addr, value in mem_items)
    return RunResult(
        bench=program.name,
        halted=halted,
        timed_out=not halted,
        steps=steps,
        retired=retired,
        final_pc=pc,
        zero_flag=zero_flag,
        program_words=len(program.instrs),
        data_writes=data_writes,
        program_crc32=program_crc,
        state_crc32=state_crc,
        arch_hash=arch_hash,
        nonzero_regs=nonzero_regs,
        touched_memory=touched_memory,
    )


def write_csv(results: list[RunResult], out_path: Path) -> None:
    out_path.parent.mkdir(exist_ok=True)
    fields = list(RunResult.__dataclass_fields__.keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow({field: getattr(result, field) for field in fields})


def write_disassembly(programs: list[Program], out_path: Path) -> None:
    out_path.parent.mkdir(exist_ok=True)
    lines: list[str] = []
    for program in programs:
        lines.append(f"# {program.name}")
        for pc, instr in enumerate(program.instrs):
            lines.append(f"{pc:03d}: 0x{instr:08x}  {disasm(instr)}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(RESULTS / "reference_model.csv"), help="CSV output path.")
    parser.add_argument("--disasm", default=str(RESULTS / "benchmark_disassembly.txt"), help="Disassembly output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    programs = [BENCHMARKS[name]() for name in BENCH_ORDER]
    results = [run_program(program) for program in programs]
    write_csv(results, Path(args.out))
    write_disassembly(programs, Path(args.disasm))

    failures = [result for result in results if result.timed_out or result.retired <= 0]
    if failures:
        for result in failures:
            print(f"FAIL bench={result.bench} timed_out={int(result.timed_out)} retired={result.retired}")
        return 1

    print(f"Wrote {args.out}")
    print(f"Wrote {args.disasm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
