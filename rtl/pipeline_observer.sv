`include "defines.svh"
import pipesense_defs::*;

// Tiny hardware-resident observer. It samples a narrow set of pipeline taps,
// accumulates a rolling window, and emits a threshold-based phase estimate.
module pipeline_observer #(
  parameter int WINDOW_SIZE              = 64,
  parameter int BRANCH_THRESHOLD         = 8,
  parameter int MEM_STALL_THRESHOLD      = 8,
  parameter int LOAD_USE_THRESHOLD       = 6,
  parameter int FRONTEND_STALL_THRESHOLD = 10,
  parameter int IDLE_RETIRE_THRESHOLD    = 8
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             if_valid,
  input  logic             id_valid,
  input  logic             ex_valid,
  input  logic             mem_valid,
  input  logic             wb_valid,
  input  logic             stall_if,
  input  logic             stall_id,
  input  logic             stall_ex,
  input  logic             flush,
  input  logic             branch_taken,
  input  logic             load_use_hazard,
  input  logic             mem_wait,
  input  logic             instruction_retired,
  input  logic [31:0]      cycle_count,
  output pipesense_phase_e phase_estimate,
  output logic             window_done
);
  localparam int COUNT_W = 32;

  logic [COUNT_W-1:0] window_cycle;
  logic [COUNT_W-1:0] branch_count;
  logic [COUNT_W-1:0] mem_wait_count;
  logic [COUNT_W-1:0] load_use_count;
  logic [COUNT_W-1:0] frontend_stall_count;
  logic [COUNT_W-1:0] retired_count;
  logic [COUNT_W-1:0] active_slot_count;

  logic [2:0] valid_slots;
  logic       sample_window_end;

  assign valid_slots = {2'b00, if_valid} +
                       {2'b00, id_valid} +
                       {2'b00, ex_valid} +
                       {2'b00, mem_valid} +
                       {2'b00, wb_valid};

  assign sample_window_end = (window_cycle == WINDOW_SIZE - 1);

  function automatic pipesense_phase_e classify_window(
    input logic [COUNT_W-1:0] branches,
    input logic [COUNT_W-1:0] mem_waits,
    input logic [COUNT_W-1:0] load_uses,
    input logic [COUNT_W-1:0] frontend_stalls,
    input logic [COUNT_W-1:0] retired,
    input logic [COUNT_W-1:0] active_slots
  );
    begin
      if (retired <= IDLE_RETIRE_THRESHOLD && active_slots < (WINDOW_SIZE * 2)) begin
        classify_window = PHASE_IDLE_OR_LOW_UTIL;
      end else if (mem_waits >= MEM_STALL_THRESHOLD) begin
        classify_window = PHASE_MEMORY_STALL;
      end else if (load_uses >= LOAD_USE_THRESHOLD) begin
        classify_window = PHASE_LOAD_USE_HAZARD;
      end else if (branches >= BRANCH_THRESHOLD) begin
        classify_window = PHASE_BRANCH_HEAVY;
      end else if (frontend_stalls >= FRONTEND_STALL_THRESHOLD) begin
        classify_window = PHASE_FRONTEND_STALL;
      end else begin
        classify_window = PHASE_BALANCED;
      end
    end
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      window_cycle        <= '0;
      branch_count        <= '0;
      mem_wait_count      <= '0;
      load_use_count      <= '0;
      frontend_stall_count <= '0;
      retired_count       <= '0;
      active_slot_count   <= '0;
      phase_estimate      <= PHASE_BALANCED;
      window_done         <= 1'b0;
    end else begin
      window_done <= sample_window_end;

      if (sample_window_end) begin
        phase_estimate <= classify_window(
          branch_count + branch_taken,
          mem_wait_count + mem_wait,
          load_use_count + load_use_hazard,
          frontend_stall_count + stall_if + flush,
          retired_count + instruction_retired,
          active_slot_count + valid_slots
        );

        window_cycle         <= '0;
        branch_count         <= '0;
        mem_wait_count       <= '0;
        load_use_count       <= '0;
        frontend_stall_count <= '0;
        retired_count        <= '0;
        active_slot_count    <= '0;
      end else begin
        window_cycle         <= window_cycle + 1'b1;
        branch_count         <= branch_count + branch_taken;
        mem_wait_count       <= mem_wait_count + mem_wait;
        load_use_count       <= load_use_count + load_use_hazard;
        frontend_stall_count <= frontend_stall_count + stall_if + flush;
        retired_count        <= retired_count + instruction_retired;
        active_slot_count    <= active_slot_count + valid_slots;
      end

    end
  end
endmodule
