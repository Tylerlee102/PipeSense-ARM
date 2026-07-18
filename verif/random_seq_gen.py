#!/usr/bin/env python3
"""Generate a constrained-random PipeSense-ARM safety testbench."""

from __future__ import annotations

import argparse
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "verif" / "generated"

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


def enc(opcode: int, rd: int = 0, rn: int = 0, rm: int = 0, imm: int = 0) -> int:
    return (
        ((opcode & 0xF) << 28)
        | ((rd & 0xF) << 24)
        | ((rn & 0xF) << 20)
        | ((rm & 0xF) << 16)
        | (imm & 0xFFFF)
    )


def random_program(seed: int, instruction_count: int) -> list[int]:
    rng = random.Random(seed)
    regs = list(range(1, 10))
    program: list[int] = []
    i = 0
    while i < instruction_count - 1:
      choice = rng.random()
      if choice < 0.20 and i < instruction_count - 4:
          rd = rng.choice(regs)
          base = 0
          addr = rng.randrange(0, 32)
          program.append(enc(OP_LDR, rd=rd, rn=base, imm=addr))
          program.append(enc(rng.choice([OP_ADD, OP_SUB, OP_EOR]), rd=rng.choice(regs), rn=rd, rm=rng.choice(regs)))
          i += 2
      elif choice < 0.38:
          rd = rng.choice(regs)
          rn = rng.choice(regs)
          program.append(enc(rng.choice([OP_LDR, OP_STR]), rd=rd, rn=rn, imm=rng.randrange(0, 32)))
          i += 1
      elif choice < 0.54 and i < instruction_count - 4:
          rn = rng.choice(regs)
          rm = rng.choice(regs)
          target = min(instruction_count - 2, i + rng.randrange(3, 7))
          program.append(enc(OP_CMP, rn=rn, rm=rm))
          program.append(enc(OP_B, rd=rng.choice([COND_EQ, COND_NE, COND_AL]), imm=target))
          i += 2
      elif choice < 0.92:
          program.append(
              enc(
                  rng.choice([OP_ADD, OP_SUB, OP_AND, OP_ORR, OP_EOR]),
                  rd=rng.choice(regs),
                  rn=rng.choice(regs),
                  rm=rng.choice(regs),
              )
          )
          i += 1
      else:
          program.append(enc(OP_NOP))
          i += 1

    program = program[: instruction_count - 1]
    program.append(enc(OP_HALT))
    return program


def sv_word(value: int) -> str:
    return f"32'h{value & 0xFFFFFFFF:08x}"


def mode_case() -> str:
    return """
  function automatic string mode_name(input pipesense_mode_e mode, input logic adaptive);
    begin
      if (adaptive) begin
        mode_name = "adaptive_pipesense";
      end else begin
        case (mode)
          MODE_BRANCH_OPT: mode_name = "fixed_branch";
          MODE_MEMORY_OPT: mode_name = "fixed_memory";
          MODE_HAZARD_OPT: mode_name = "fixed_hazard";
          MODE_LOW_POWER:  mode_name = "fixed_low_power";
          default:         mode_name = "static_normal";
        endcase
      end
    end
  endfunction
"""


def generate_harness(seed: int, instruction_count: int, out_path: Path, reconfig_bound: int = 32) -> Path:
    program = random_program(seed, instruction_count)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    load_lines = [
        "      dut.clear_all();",
        "      for (int i = 0; i < 32; i++) begin",
        f"        dut.load_data(i, 32'h{(seed * 2654435761) & 0xFFFFFFFF:08x} ^ i);",
        "      end",
        "      for (int r = 1; r < 10; r++) begin",
        f"        dut.set_reg(r, 32'd{(seed % 17) + 3} + r);",
        "      end",
    ]
    for addr, instr in enumerate(program):
        load_lines.append(f"      dut.load_instr({addr}, {sv_word(instr)});")

    text = f"""`timescale 1ns/1ps
`include "defines.svh"

module tb_random_seed_{seed};
  logic clk;
  logic rst_n;
  logic adaptive_enable;
  pipesense_mode_e fixed_mode;
  pipesense_mode_e current_mode;
  pipesense_phase_e observed_phase;
  logic halted;
  logic [31:0] cycle_count;
  logic [31:0] retired_count;
  logic [31:0] stall_cycles;
  logic [31:0] flush_cycles;
  logic [31:0] mem_wait_cycles;
  logic [31:0] load_use_stalls;
  logic [31:0] reconfigurations;
  logic [31:0] reconfig_penalty;
  logic [31:0] energy_proxy;
  logic [31:0] safety_faults;
  logic [31:0] phases_seen_mask;
  logic [31:0] transitions_seen;
  logic [31:0] hazard_during_reconfig;
  logic [31:0] back_to_back_reconfig_requests;
  logic [31:0] reconfig_then_branch;
  logic [31:0] reconfig_then_load_use;
  int failed_cases;

  arm_like_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .adaptive_enable(adaptive_enable),
    .fixed_mode(fixed_mode),
    .program_write_en(1'b0),
    .program_select_dmem(1'b0),
    .program_addr(8'b0),
    .program_wdata(32'b0),
    .current_mode(current_mode),
    .observed_phase(observed_phase),
    .halted(halted),
    .cycle_count(cycle_count),
    .retired_count(retired_count),
    .stall_cycles(stall_cycles),
    .flush_cycles(flush_cycles),
    .mem_wait_cycles(mem_wait_cycles),
    .load_use_stalls(load_use_stalls),
    .reconfigurations(reconfigurations),
    .reconfig_penalty(reconfig_penalty),
    .energy_proxy(energy_proxy),
    .safety_faults(safety_faults)
  );

  pipesense_core_sva #(.RECONFIG_STALL_BOUND({reconfig_bound})) safety_mon (
    .clk(clk),
    .rst_n(rst_n),
    .if_id_valid(dut.if_id_valid),
    .id_ex_valid(dut.id_ex_valid),
    .ex_mem_valid(dut.ex_mem_valid),
    .mem_wb_valid(dut.mem_wb_valid),
    .if_id_tag(dut.if_id_tag),
    .id_ex_tag(dut.id_ex_tag),
    .ex_mem_tag(dut.ex_mem_tag),
    .mem_wb_tag(dut.mem_wb_tag),
    .instruction_retired(dut.instruction_retired),
    .branch_flush_event(dut.branch_flush_event),
    .pipeline_empty(dut.pipeline_empty),
    .mem_wait_signal(dut.mem_wait_signal),
    .reconfig_request(dut.reconfig_request),
    .reconfig_active(dut.reconfig_active),
    .reconfig_done(dut.reconfig_done),
    .reconfig_stop_fetch(dut.reconfig_stop_fetch),
    .current_mode(current_mode),
    .requested_mode(dut.requested_mode)
  );

  pipesense_safety_coverage cov_mon (
    .clk(clk),
    .rst_n(rst_n),
    .observed_phase(observed_phase),
    .current_mode(current_mode),
    .requested_mode(dut.requested_mode),
    .reconfig_request(dut.reconfig_request),
    .reconfig_active(dut.reconfig_active),
    .reconfig_done(dut.reconfig_done),
    .branch_flush_event(dut.branch_flush_event),
    .load_use_hazard(dut.hazard_raw),
    .mem_wait_signal(dut.mem_wait_signal),
    .phases_seen_mask(phases_seen_mask),
    .transitions_seen(transitions_seen),
    .hazard_during_reconfig(hazard_during_reconfig),
    .back_to_back_reconfig_requests(back_to_back_reconfig_requests),
    .reconfig_then_branch(reconfig_then_branch),
    .reconfig_then_load_use(reconfig_then_load_use)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

{mode_case()}

  task automatic load_random_program();
    begin
{chr(10).join(load_lines)}
    end
  endtask

  task automatic run_case(input logic adaptive, input pipesense_mode_e requested_fixed_mode);
    int guard_cycles;
    begin
      adaptive_enable = adaptive;
      fixed_mode = requested_fixed_mode;
      rst_n = 1'b1;
      @(negedge clk);
      rst_n = 1'b0;
      load_random_program();
      repeat (4) @(posedge clk);
      rst_n = 1'b1;

      guard_cycles = 0;
      while (!halted && guard_cycles < {instruction_count * 20}) begin
        @(posedge clk);
        guard_cycles++;
      end
      repeat (2) @(posedge clk);

      $display("FUZZ_RESULT seed={seed} mode=%s cycles=%0d retired=%0d stalls=%0d flushes=%0d mem_wait=%0d load_use=%0d reconfigs=%0d reconfig_penalty=%0d energy=%0d safety_faults=%0d timed_out=%0d",
        mode_name(requested_fixed_mode, adaptive),
        cycle_count,
        retired_count,
        stall_cycles,
        flush_cycles,
        mem_wait_cycles,
        load_use_stalls,
        reconfigurations,
        reconfig_penalty,
        energy_proxy,
        safety_faults,
        !halted);

      if (!halted || (safety_faults != 0) || (retired_count == 0)) begin
        failed_cases++;
        $error("FUZZ_CASE_FAIL seed={seed} mode=%s halted=%0d retired=%0d safety_faults=%0d",
          mode_name(requested_fixed_mode, adaptive), halted, retired_count, safety_faults);
      end
    end
  endtask

  initial begin
    rst_n = 1'b0;
    adaptive_enable = 1'b0;
    fixed_mode = MODE_NORMAL;
    failed_cases = 0;
    repeat (2) @(posedge clk);

    run_case(1'b0, MODE_NORMAL);
    run_case(1'b0, MODE_BRANCH_OPT);
    run_case(1'b0, MODE_MEMORY_OPT);
    run_case(1'b0, MODE_HAZARD_OPT);
    run_case(1'b1, MODE_NORMAL);

    $display("FUZZ_COVERAGE seed={seed} phases_seen=0x%08x transitions_seen=0x%08x hazard_during_reconfig=%0d back_to_back_reconfig_requests=%0d reconfig_then_branch=%0d reconfig_then_load_use=%0d",
      phases_seen_mask,
      transitions_seen,
      hazard_during_reconfig,
      back_to_back_reconfig_requests,
      reconfig_then_branch,
      reconfig_then_load_use);

    if (failed_cases != 0) begin
      $fatal(1, "Random safety regression failed %0d cases for seed {seed}", failed_cases);
    end
    $finish;
  end
endmodule
"""
    out_path.write_text(text, encoding="utf-8")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="Random seed.")
    parser.add_argument("--instructions", type=int, default=96, help="Instruction count including HALT.")
    parser.add_argument("--reconfig-bound", type=int, default=32, help="Assertion bound for reconfiguration stalls.")
    parser.add_argument("--out", default="", help="Output SystemVerilog testbench path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out) if args.out else GENERATED / f"tb_random_seed_{args.seed}.sv"
    generated = generate_harness(args.seed, args.instructions, out_path, args.reconfig_bound)
    print(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
