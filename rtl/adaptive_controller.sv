`include "defines.svh"
import pipesense_defs::*;

// Converts observer phases into mode requests with simple hysteresis.
module adaptive_controller #(
  parameter int MIN_MODE_RESIDENCY = 32,
  parameter int PHASE_STABLE_COUNT = 2
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             adaptive_enable,
  input  pipesense_phase_e phase_estimate,
  input  pipesense_mode_e  current_mode,
  input  logic             reconfig_ack,
  input  logic             reconfig_active,
  output logic             reconfig_request,
  output pipesense_mode_e  requested_mode
);
  pipesense_mode_e desired_mode;
  pipesense_mode_e last_desired_mode;
  logic [15:0] residency_counter;
  logic [7:0]  stable_counter;

  always_comb begin
    case (phase_estimate)
      PHASE_BRANCH_HEAVY:     desired_mode = MODE_BRANCH_OPT;
      PHASE_MEMORY_STALL:     desired_mode = MODE_MEMORY_OPT;
      PHASE_LOAD_USE_HAZARD:  desired_mode = MODE_HAZARD_OPT;
      PHASE_FRONTEND_STALL:   desired_mode = MODE_BRANCH_OPT;
      PHASE_IDLE_OR_LOW_UTIL: desired_mode = MODE_LOW_POWER;
      default:                desired_mode = MODE_NORMAL;
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      residency_counter <= '0;
      stable_counter    <= '0;
      last_desired_mode <= MODE_NORMAL;
      requested_mode    <= MODE_NORMAL;
      reconfig_request  <= 1'b0;
    end else begin
      if (reconfig_ack) begin
        residency_counter <= '0;
        reconfig_request  <= 1'b0;
      end else if (residency_counter != 16'hffff) begin
        residency_counter <= residency_counter + 1'b1;
      end

      if (desired_mode == last_desired_mode) begin
        if (stable_counter != 8'hff) begin
          stable_counter <= stable_counter + 1'b1;
        end
      end else begin
        stable_counter    <= '0;
        last_desired_mode <= desired_mode;
      end

      if (!adaptive_enable) begin
        reconfig_request <= 1'b0;
        requested_mode   <= current_mode;
      end else if (!reconfig_request && !reconfig_active &&
                   (desired_mode != current_mode) &&
                   (residency_counter >= MIN_MODE_RESIDENCY) &&
                   (stable_counter >= PHASE_STABLE_COUNT)) begin
        reconfig_request <= 1'b1;
        requested_mode   <= desired_mode;
      end
    end
  end
endmodule
