`timescale 1ns/1ps
`include "defines.svh"

// Bindable safety monitor for PipeSense-ARM simulations.
//
// Invariant map used by docs/safety_proof_sketch.md:
// I1: dynamic instruction tags retire monotonically, so writeback is not
//     duplicated for the same instruction.
// I2: a mode update is committed only at the concrete safe-boundary predicate:
//     the pipeline is empty and no memory wait is active.
// I3: fetch remains gated while reconfiguration is active.
// I4: the visible mode is stable while a reconfiguration drain is in flight.
// I5: reconfiguration stall time is bounded by RECONFIG_STALL_BOUND cycles.
module pipesense_core_sva #(
  parameter int RECONFIG_STALL_BOUND = 16
) (
  input logic            clk,
  input logic            rst_n,
  input logic            if_id_valid,
  input logic            id_ex_valid,
  input logic            ex_mem_valid,
  input logic            mem_wb_valid,
  input logic [31:0]     if_id_tag,
  input logic [31:0]     id_ex_tag,
  input logic [31:0]     ex_mem_tag,
  input logic [31:0]     mem_wb_tag,
  input logic            instruction_retired,
  input logic            branch_flush_event,
  input logic            pipeline_empty,
  input logic            mem_wait_signal,
  input logic            reconfig_request,
  input logic            reconfig_active,
  input logic            reconfig_done,
  input logic            reconfig_stop_fetch,
  input pipesense_mode_e current_mode,
  input pipesense_mode_e requested_mode
);
  localparam int RECONFIG_COUNT_W =
    (RECONFIG_STALL_BOUND < 1) ? 1 : $clog2(RECONFIG_STALL_BOUND + 2);

  logic safe_boundary;
  logic [31:0] last_retired_tag;
  logic [RECONFIG_COUNT_W-1:0] reconfig_duration;
  logic retire_seen;
  pipesense_mode_e mode_at_reconfig_start;
  pipesense_mode_e prev_current_mode;
  logic past_valid;

  assign safe_boundary = pipeline_empty && !mem_wait_signal;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      last_retired_tag       <= 32'd0;
      retire_seen            <= 1'b0;
      mode_at_reconfig_start <= MODE_NORMAL;
      prev_current_mode      <= MODE_NORMAL;
      past_valid             <= 1'b0;
      reconfig_duration      <= '0;
    end else begin
      if (instruction_retired && retire_seen) begin
        assert (mem_wb_tag > last_retired_tag)
          else $error("SVA_I1_DUPLICATE_OR_BACKWARD_RETIRE");
      end
      if (if_id_valid && id_ex_valid) begin
        assert (if_id_tag != id_ex_tag)
          else $error("SVA_I1_DUPLICATE_TAG_IF_ID_EX");
      end
      if (if_id_valid && ex_mem_valid) begin
        assert (if_id_tag != ex_mem_tag)
          else $error("SVA_I1_DUPLICATE_TAG_IF_ID_MEM");
      end
      if (if_id_valid && mem_wb_valid) begin
        assert (if_id_tag != mem_wb_tag)
          else $error("SVA_I1_DUPLICATE_TAG_IF_ID_WB");
      end
      if (id_ex_valid && ex_mem_valid) begin
        assert (id_ex_tag != ex_mem_tag)
          else $error("SVA_I1_DUPLICATE_TAG_ID_EX_MEM");
      end
      if (id_ex_valid && mem_wb_valid) begin
        assert (id_ex_tag != mem_wb_tag)
          else $error("SVA_I1_DUPLICATE_TAG_ID_EX_WB");
      end
      if (ex_mem_valid && mem_wb_valid) begin
        assert (ex_mem_tag != mem_wb_tag)
          else $error("SVA_I1_DUPLICATE_TAG_EX_MEM_WB");
      end
      if (past_valid && (current_mode != prev_current_mode)) begin
        assert (safe_boundary && reconfig_done)
          else $error("SVA_I2_MODE_CHANGE_OUTSIDE_SAFE_BOUNDARY");
      end
      if (reconfig_active) begin
        assert (reconfig_stop_fetch)
          else $error("SVA_I3_FETCH_NOT_GATED_DURING_RECONFIG");
        assert (current_mode == mode_at_reconfig_start)
          else $error("SVA_I4_MODE_TORN_DURING_RECONFIG");
        assert (reconfig_duration < RECONFIG_STALL_BOUND)
          else $error("SVA_I5_RECONFIG_STALL_BOUND_EXCEEDED");
        if (reconfig_duration <= RECONFIG_STALL_BOUND) begin
          reconfig_duration <= reconfig_duration + 1'b1;
        end
      end else begin
        reconfig_duration <= '0;
      end
      if (reconfig_request && !reconfig_active) begin
        mode_at_reconfig_start <= current_mode;
      end
      if (instruction_retired) begin
        last_retired_tag <= mem_wb_tag;
        retire_seen      <= 1'b1;
      end
      prev_current_mode  <= current_mode;
      past_valid         <= 1'b1;
    end
  end
endmodule
