`include "defines.svh"

// Architectural approximation of Efthymiou and Garside's ASYNC'03 policy.
// Their asynchronous core collapses pipeline latches after a condition-setting
// instruction. This synchronous core instead requests its low-activity mode
// after CMP and returns to normal after the following branch is decoded.
module async03_speculation_controller (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             adaptive_enable,
  input  logic             condition_setting_detected,
  input  logic             branch_detected,
  input  pipesense_mode_e  current_mode,
  input  logic             reconfig_ack,
  input  logic             reconfig_active,
  output logic             reconfig_request,
  output pipesense_mode_e  requested_mode
);
  logic anticipating_branch;
  pipesense_mode_e desired_mode;

  always_comb begin
    if (anticipating_branch) begin
      desired_mode = MODE_LOW_POWER;
    end else begin
      desired_mode = MODE_NORMAL;
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      anticipating_branch <= 1'b0;
      reconfig_request     <= 1'b0;
      requested_mode       <= MODE_NORMAL;
    end else begin
      if (!adaptive_enable) begin
        anticipating_branch <= 1'b0;
        reconfig_request     <= 1'b0;
        requested_mode       <= current_mode;
      end else begin
        if (condition_setting_detected) begin
          anticipating_branch <= 1'b1;
        end
        if (branch_detected) begin
          anticipating_branch <= 1'b0;
        end

        if (reconfig_ack) begin
          reconfig_request <= 1'b0;
        end else if (!reconfig_request && !reconfig_active &&
                     (desired_mode != current_mode)) begin
          reconfig_request <= 1'b1;
          requested_mode   <= desired_mode;
        end
      end
    end
  end
endmodule
