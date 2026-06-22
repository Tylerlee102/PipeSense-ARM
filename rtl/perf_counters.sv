`include "defines.svh"
import pipesense_defs::*;

// Aggregates the events exported by the pipeline into testbench-visible metrics.
module perf_counters (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        instruction_retired,
  input  logic        stall_any,
  input  logic [1:0]  flush_slots,
  input  logic        mem_wait,
  input  logic        load_use_stall,
  input  logic        reconfig_active,
  input  logic        reconfig_done,
  input  logic [3:0]  activity_units,
  output logic [31:0] cycle_count,
  output logic [31:0] retired_count,
  output logic [31:0] stall_cycles,
  output logic [31:0] flush_cycles,
  output logic [31:0] mem_wait_cycles,
  output logic [31:0] load_use_stalls,
  output logic [31:0] reconfigurations,
  output logic [31:0] reconfig_penalty,
  output logic [31:0] energy_proxy
);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cycle_count       <= '0;
      retired_count     <= '0;
      stall_cycles      <= '0;
      flush_cycles      <= '0;
      mem_wait_cycles   <= '0;
      load_use_stalls   <= '0;
      reconfigurations  <= '0;
      reconfig_penalty  <= '0;
      energy_proxy      <= '0;
    end else begin
      cycle_count      <= cycle_count + 1'b1;
      retired_count    <= retired_count + instruction_retired;
      stall_cycles     <= stall_cycles + stall_any;
      flush_cycles     <= flush_cycles + flush_slots;
      mem_wait_cycles  <= mem_wait_cycles + mem_wait;
      load_use_stalls  <= load_use_stalls + load_use_stall;
      reconfigurations <= reconfigurations + reconfig_done;
      reconfig_penalty <= reconfig_penalty + reconfig_active;
      energy_proxy     <= energy_proxy + activity_units;
    end
  end
endmodule
