`timescale 1ns/1ps
`include "defines.svh"
import pipesense_defs::*;

module tb_pipesense;
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
  int total_cases;
  int failed_cases;

  arm_like_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .adaptive_enable(adaptive_enable),
    .fixed_mode(fixed_mode),
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

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  `include "benchmark_programs.sv"

  function automatic string bench_name(input int bench_id);
    begin
      case (bench_id)
        0: bench_name = "arithmetic_heavy";
        1: bench_name = "branch_heavy";
        2: bench_name = "memory_heavy";
        3: bench_name = "load_use_heavy";
        4: bench_name = "mixed_control";
        5: bench_name = "tiny_fir";
        6: bench_name = "dhrystone_toy";
        7: bench_name = "coremark_toy";
        8: bench_name = "dsp_fir_codegen";
        default: bench_name = "pid_control_codegen";
      endcase
    end
  endfunction

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

  function automatic string phase_name(input pipesense_phase_e phase);
    begin
      case (phase)
        PHASE_BRANCH_HEAVY:     phase_name = "branch_heavy";
        PHASE_MEMORY_STALL:     phase_name = "memory_stall";
        PHASE_LOAD_USE_HAZARD:  phase_name = "load_use_hazard";
        PHASE_FRONTEND_STALL:   phase_name = "frontend_stall";
        PHASE_IDLE_OR_LOW_UTIL: phase_name = "idle_or_low_util";
        default:                phase_name = "balanced";
      endcase
    end
  endfunction

  function automatic string current_mode_name(input pipesense_mode_e mode);
    begin
      case (mode)
        MODE_BRANCH_OPT: current_mode_name = "branch_opt";
        MODE_MEMORY_OPT: current_mode_name = "memory_opt";
        MODE_HAZARD_OPT: current_mode_name = "hazard_opt";
        MODE_LOW_POWER:  current_mode_name = "low_power";
        default:         current_mode_name = "normal";
      endcase
    end
  endfunction

  function automatic logic [31:0] fnv_word(input logic [31:0] seed, input logic [31:0] word);
    logic [31:0] value;
    begin
      value = seed;
      for (int byte_index = 0; byte_index < 4; byte_index++) begin
        value = value ^ {24'd0, word[byte_index * 8 +: 8]};
        value = value * 32'h01000193;
      end
      fnv_word = value;
    end
  endfunction

  function automatic logic [31:0] architectural_hash();
    logic [31:0] value;
    logic [31:0] word;
    begin
      value = 32'h811c9dc5;
      word = {31'd0, dut.zero_flag};
      value = fnv_word(value, word);

      for (int reg_index = 0; reg_index < REG_COUNT; reg_index++) begin
        value = fnv_word(value, dut.regfile[reg_index]);
      end
      for (int mem_index = 0; mem_index < 256; mem_index++) begin
        value = fnv_word(value, dut.dmem.mem[mem_index]);
      end

      architectural_hash = value;
    end
  endfunction

  task automatic run_case(
    input int bench_id,
    input logic adaptive,
    input pipesense_mode_e requested_fixed_mode
  );
    int guard_cycles;
    int max_cycles;
    int ipc_x1000;
    logic [31:0] debug_instr0;
    logic [31:0] debug_instr1;
    logic [31:0] debug_mem127;
    begin
      adaptive_enable = adaptive;
      fixed_mode = requested_fixed_mode;

      rst_n = 1'b1;
      @(negedge clk);
      rst_n = 1'b0;
      dut.clear_all();
      load_benchmark(bench_id, max_cycles);
`ifdef PIPESENSE_DEBUG_LOAD
      dut.imem.read_word(0, debug_instr0);
      dut.imem.read_word(1, debug_instr1);
      $display("LOAD_CHECK bench=%s instr0=0x%08x instr1=0x%08x",
        bench_name(bench_id), debug_instr0, debug_instr1);
`endif
      repeat (4) @(posedge clk);
      rst_n = 1'b1;

      guard_cycles = 0;
      while (!halted && guard_cycles < max_cycles) begin
        @(posedge clk);
        guard_cycles++;
      end

      repeat (2) @(posedge clk);

      if (cycle_count == 0) begin
        ipc_x1000 = 0;
      end else begin
        ipc_x1000 = (retired_count * 1000) / cycle_count;
      end

      $display("RESULT bench=%s mode=%s cycles=%0d retired=%0d ipc_x1000=%0d stalls=%0d flushes=%0d mem_wait=%0d load_use=%0d reconfigs=%0d reconfig_penalty=%0d energy=%0d safety_faults=%0d phase=%s final_mode=%s timed_out=%0d arch_hash=0x%08x",
        bench_name(bench_id),
        mode_name(requested_fixed_mode, adaptive),
        cycle_count,
        retired_count,
        ipc_x1000,
        stall_cycles,
        flush_cycles,
        mem_wait_cycles,
        load_use_stalls,
        reconfigurations,
        reconfig_penalty,
        energy_proxy,
        safety_faults,
        phase_name(observed_phase),
        current_mode_name(current_mode),
        !halted,
        architectural_hash()
      );
`ifdef PIPESENSE_DEBUG_LOAD
      dut.dmem.read_word(127, debug_mem127);
      $display("STATE_CHECK bench=%s mode=%s pc=%0d r1=%0d r2=%0d zero=%0d halted=%0d",
        bench_name(bench_id),
        mode_name(requested_fixed_mode, adaptive),
        dut.pc,
        dut.regfile[1],
        dut.regfile[2],
        dut.zero_flag,
        halted);
      $display("STATE_DETAIL bench=%s mode=%s r3=%0d r4=%0d r5=%0d r6=%0d m127=%0d arch_hash=0x%08x",
        bench_name(bench_id),
        mode_name(requested_fixed_mode, adaptive),
        dut.regfile[3],
        dut.regfile[4],
        dut.regfile[5],
        dut.regfile[6],
        debug_mem127,
        architectural_hash());
`endif

      total_cases++;
      if (!halted || (safety_faults != 0) || (retired_count == 0)) begin
        failed_cases++;
        $error("CASE_FAIL bench=%s mode=%s halted=%0d retired=%0d safety_faults=%0d",
          bench_name(bench_id),
          mode_name(requested_fixed_mode, adaptive),
          halted,
          retired_count,
          safety_faults
        );
      end
    end
  endtask

  initial begin
    rst_n = 1'b0;
    adaptive_enable = 1'b0;
    fixed_mode = MODE_NORMAL;
    total_cases = 0;
    failed_cases = 0;

    repeat (2) @(posedge clk);

    for (int bench = 0; bench < 10; bench++) begin
      run_case(bench, 1'b0, MODE_NORMAL);
      run_case(bench, 1'b0, MODE_BRANCH_OPT);
      run_case(bench, 1'b0, MODE_MEMORY_OPT);
      run_case(bench, 1'b0, MODE_HAZARD_OPT);
      run_case(bench, 1'b0, MODE_LOW_POWER);
      run_case(bench, 1'b1, MODE_NORMAL);
    end

    $display("SUMMARY total_cases=%0d failed_cases=%0d", total_cases, failed_cases);
    if (failed_cases != 0) begin
      $fatal(1, "PipeSense testbench failed %0d of %0d cases", failed_cases, total_cases);
    end

    $finish;
  end
endmodule
