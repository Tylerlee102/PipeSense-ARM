`include "defines.svh"

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
  input  logic             flush,
  input  logic             branch_taken,
  input  logic             load_use_hazard,
  input  logic             mem_wait,
  input  logic             instruction_retired,
  output pipesense_phase_e phase_estimate,
  output logic             window_done
);
  localparam int WINDOW_W = (WINDOW_SIZE <= 1) ? 1 : $clog2(WINDOW_SIZE);
  localparam int BRANCH_W = (BRANCH_THRESHOLD < 1) ? 1 : $clog2(BRANCH_THRESHOLD + 1);
  localparam int MEM_W = (MEM_STALL_THRESHOLD < 1) ? 1 : $clog2(MEM_STALL_THRESHOLD + 1);
  localparam int LOAD_USE_W = (LOAD_USE_THRESHOLD < 1) ? 1 : $clog2(LOAD_USE_THRESHOLD + 1);
  localparam int FRONTEND_W = (FRONTEND_STALL_THRESHOLD < 1) ? 1 : $clog2(FRONTEND_STALL_THRESHOLD + 1);
  localparam int RETIRED_LIMIT = IDLE_RETIRE_THRESHOLD + 1;
  localparam int RETIRED_W = (RETIRED_LIMIT < 1) ? 1 : $clog2(RETIRED_LIMIT + 1);
  localparam int ACTIVE_LIMIT = WINDOW_SIZE * 2;
  localparam int ACTIVE_W = (ACTIVE_LIMIT < 1) ? 1 : $clog2(ACTIVE_LIMIT + 1);

  localparam logic [BRANCH_W-1:0] BRANCH_LIMIT_VALUE = BRANCH_THRESHOLD;
  localparam logic [MEM_W-1:0] MEM_LIMIT_VALUE = MEM_STALL_THRESHOLD;
  localparam logic [LOAD_USE_W-1:0] LOAD_USE_LIMIT_VALUE = LOAD_USE_THRESHOLD;
  localparam logic [FRONTEND_W-1:0] FRONTEND_LIMIT_VALUE = FRONTEND_STALL_THRESHOLD;
  localparam logic [RETIRED_W-1:0] RETIRED_LIMIT_VALUE = RETIRED_LIMIT;
  localparam logic [ACTIVE_W-1:0] ACTIVE_LIMIT_VALUE = ACTIVE_LIMIT;

  logic [WINDOW_W-1:0] window_cycle;
  logic [BRANCH_W-1:0] branch_count;
  logic [MEM_W-1:0] mem_wait_count;
  logic [LOAD_USE_W-1:0] load_use_count;
  logic [FRONTEND_W-1:0] frontend_stall_count;
  logic [RETIRED_W-1:0] retired_count;
  logic [ACTIVE_W-1:0] active_slot_count;

  logic [2:0] valid_slots;
  logic [1:0] frontend_events;
  logic       sample_window_end;
  logic [BRANCH_W:0] branch_sample;
  logic [MEM_W:0] mem_wait_sample;
  logic [LOAD_USE_W:0] load_use_sample;
  logic [FRONTEND_W:0] frontend_stall_sample;
  logic [RETIRED_W:0] retired_sample;
  logic [ACTIVE_W:0] active_slot_sample;

  assign valid_slots = {2'b00, if_valid} +
                       {2'b00, id_valid} +
                       {2'b00, ex_valid} +
                       {2'b00, mem_valid} +
                       {2'b00, wb_valid};
  assign frontend_events = {1'b0, stall_if} + {1'b0, flush};

  assign sample_window_end = (window_cycle == WINDOW_SIZE - 1);
  assign branch_sample = {1'b0, branch_count} + branch_taken;
  assign mem_wait_sample = {1'b0, mem_wait_count} + mem_wait;
  assign load_use_sample = {1'b0, load_use_count} + load_use_hazard;
  assign frontend_stall_sample = {1'b0, frontend_stall_count} + frontend_events;
  assign retired_sample = {1'b0, retired_count} + instruction_retired;
  assign active_slot_sample = {1'b0, active_slot_count} + valid_slots;

  function automatic pipesense_phase_e classify_window(
    input logic idle_or_low_util,
    input logic memory_stall,
    input logic load_use_stall,
    input logic branch_heavy,
    input logic frontend_stall
  );
    begin
      if (idle_or_low_util) begin
        classify_window = PHASE_IDLE_OR_LOW_UTIL;
      end else if (memory_stall) begin
        classify_window = PHASE_MEMORY_STALL;
      end else if (load_use_stall) begin
        classify_window = PHASE_LOAD_USE_HAZARD;
      end else if (branch_heavy) begin
        classify_window = PHASE_BRANCH_HEAVY;
      end else if (frontend_stall) begin
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
          (retired_sample <= IDLE_RETIRE_THRESHOLD) &&
            (active_slot_sample < ACTIVE_LIMIT),
          mem_wait_sample >= MEM_STALL_THRESHOLD,
          load_use_sample >= LOAD_USE_THRESHOLD,
          branch_sample >= BRANCH_THRESHOLD,
          frontend_stall_sample >= FRONTEND_STALL_THRESHOLD
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
        branch_count         <= (branch_sample >= BRANCH_THRESHOLD) ?
                                BRANCH_LIMIT_VALUE : branch_sample[BRANCH_W-1:0];
        mem_wait_count       <= (mem_wait_sample >= MEM_STALL_THRESHOLD) ?
                                MEM_LIMIT_VALUE : mem_wait_sample[MEM_W-1:0];
        load_use_count       <= (load_use_sample >= LOAD_USE_THRESHOLD) ?
                                LOAD_USE_LIMIT_VALUE : load_use_sample[LOAD_USE_W-1:0];
        frontend_stall_count <= (frontend_stall_sample >= FRONTEND_STALL_THRESHOLD) ?
                                FRONTEND_LIMIT_VALUE : frontend_stall_sample[FRONTEND_W-1:0];
        retired_count        <= (retired_sample >= RETIRED_LIMIT) ?
                                RETIRED_LIMIT_VALUE : retired_sample[RETIRED_W-1:0];
        active_slot_count    <= (active_slot_sample >= ACTIVE_LIMIT) ?
                                ACTIVE_LIMIT_VALUE : active_slot_sample[ACTIVE_W-1:0];
      end

    end
  end
endmodule
