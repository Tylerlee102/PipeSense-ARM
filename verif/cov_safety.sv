`timescale 1ns/1ps
`include "defines.svh"

// Lightweight functional coverage counters for safety-oriented regressions.
// These counters are simulator-portable and are printed by generated fuzz
// harnesses even when the simulator does not support covergroups.
module pipesense_safety_coverage (
  input logic            clk,
  input logic            rst_n,
  input pipesense_phase_e observed_phase,
  input pipesense_mode_e  current_mode,
  input pipesense_mode_e  requested_mode,
  input logic            reconfig_request,
  input logic            reconfig_active,
  input logic            reconfig_done,
  input logic            branch_flush_event,
  input logic            load_use_hazard,
  input logic            mem_wait_signal,
  output logic [31:0]    phases_seen_mask,
  output logic [31:0]    transitions_seen,
  output logic [31:0]    hazard_during_reconfig,
  output logic [31:0]    back_to_back_reconfig_requests,
  output logic [31:0]    reconfig_then_branch,
  output logic [31:0]    reconfig_then_load_use
);
  logic prior_reconfig_request;
  logic prior_reconfig_done;

  function automatic logic [4:0] transition_bit(
    input pipesense_mode_e from_mode,
    input pipesense_mode_e to_mode
  );
    transition_bit = (from_mode * 5) + to_mode;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      phases_seen_mask              <= 32'd0;
      transitions_seen              <= 32'd0;
      hazard_during_reconfig        <= 32'd0;
      back_to_back_reconfig_requests <= 32'd0;
      reconfig_then_branch          <= 32'd0;
      reconfig_then_load_use        <= 32'd0;
      prior_reconfig_request        <= 1'b0;
      prior_reconfig_done           <= 1'b0;
    end else begin
      phases_seen_mask[observed_phase] <= 1'b1;

      if (reconfig_request && (requested_mode != current_mode)) begin
        transitions_seen[transition_bit(current_mode, requested_mode)] <= 1'b1;
      end
      if (reconfig_active && (load_use_hazard || mem_wait_signal)) begin
        hazard_during_reconfig <= hazard_during_reconfig + 1'b1;
      end
      if (reconfig_request && prior_reconfig_request) begin
        back_to_back_reconfig_requests <= back_to_back_reconfig_requests + 1'b1;
      end
      if (prior_reconfig_done && branch_flush_event) begin
        reconfig_then_branch <= reconfig_then_branch + 1'b1;
      end
      if (prior_reconfig_done && load_use_hazard) begin
        reconfig_then_load_use <= reconfig_then_load_use + 1'b1;
      end

      prior_reconfig_request <= reconfig_request;
      prior_reconfig_done    <= reconfig_done;
    end
  end
endmodule
