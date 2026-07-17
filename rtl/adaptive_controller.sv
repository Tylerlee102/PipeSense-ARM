`include "defines.svh"

// Converts observer phases into mode requests with mode-specific hysteresis.
module adaptive_controller #(
  parameter int MIN_MODE_RESIDENCY = 32,
  parameter int PHASE_STABLE_COUNT = 2,
  parameter int BRANCH_MIN_RESIDENCY = 12,
  parameter int MEMORY_MIN_RESIDENCY = 8,
  parameter int HAZARD_MIN_RESIDENCY = 12,
  parameter int LOW_POWER_MIN_RESIDENCY = 48,
  parameter int NORMAL_MIN_RESIDENCY = 48,
  parameter int BRANCH_STABLE_COUNT = 3,
  parameter int MEMORY_STABLE_COUNT = 0,
  parameter int HAZARD_STABLE_COUNT = 1,
  parameter int LOW_POWER_STABLE_COUNT = 3,
  parameter int NORMAL_STABLE_COUNT = 3
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
  function automatic int max_int(input int lhs, input int rhs);
    max_int = (lhs > rhs) ? lhs : rhs;
  endfunction

  localparam int MAX_RESIDENCY = max_int(
    MIN_MODE_RESIDENCY,
    max_int(BRANCH_MIN_RESIDENCY,
      max_int(MEMORY_MIN_RESIDENCY,
        max_int(HAZARD_MIN_RESIDENCY,
          max_int(LOW_POWER_MIN_RESIDENCY, NORMAL_MIN_RESIDENCY))))
  );
  localparam int MAX_STABILITY = max_int(
    PHASE_STABLE_COUNT,
    max_int(BRANCH_STABLE_COUNT,
      max_int(MEMORY_STABLE_COUNT,
        max_int(HAZARD_STABLE_COUNT,
          max_int(LOW_POWER_STABLE_COUNT, NORMAL_STABLE_COUNT))))
  );
  localparam int RESIDENCY_W = (MAX_RESIDENCY < 1) ? 1 : $clog2(MAX_RESIDENCY + 1);
  localparam int STABILITY_W = (MAX_STABILITY < 1) ? 1 : $clog2(MAX_STABILITY + 1);
  localparam logic [RESIDENCY_W-1:0] MAX_RESIDENCY_VALUE = MAX_RESIDENCY;
  localparam logic [STABILITY_W-1:0] MAX_STABILITY_VALUE = MAX_STABILITY;

  pipesense_mode_e desired_mode;
  pipesense_mode_e last_desired_mode;
  logic [RESIDENCY_W-1:0] residency_counter;
  logic [STABILITY_W-1:0] stable_counter;
  logic [RESIDENCY_W-1:0] required_residency;
  logic [STABILITY_W-1:0] required_stability;

  always_comb begin
    case (phase_estimate)
      PHASE_BRANCH_HEAVY:     desired_mode = MODE_BRANCH_OPT;
      PHASE_MEMORY_STALL:     desired_mode = MODE_MEMORY_OPT;
      PHASE_LOAD_USE_HAZARD:  desired_mode = MODE_HAZARD_OPT;
      PHASE_FRONTEND_STALL: begin
        if (current_mode == MODE_MEMORY_OPT) begin
          desired_mode = MODE_MEMORY_OPT;
        end else begin
          desired_mode = MODE_BRANCH_OPT;
        end
      end
      PHASE_IDLE_OR_LOW_UTIL: desired_mode = MODE_LOW_POWER;
      default:                desired_mode = current_mode;
    endcase
  end

  always_comb begin
    case (desired_mode)
      MODE_BRANCH_OPT: begin
        required_residency = BRANCH_MIN_RESIDENCY;
        required_stability = BRANCH_STABLE_COUNT;
      end
      MODE_MEMORY_OPT: begin
        required_residency = MEMORY_MIN_RESIDENCY;
        required_stability = MEMORY_STABLE_COUNT;
      end
      MODE_HAZARD_OPT: begin
        required_residency = HAZARD_MIN_RESIDENCY;
        required_stability = HAZARD_STABLE_COUNT;
      end
      MODE_LOW_POWER: begin
        required_residency = LOW_POWER_MIN_RESIDENCY;
        required_stability = LOW_POWER_STABLE_COUNT;
      end
      default: begin
        required_residency = NORMAL_MIN_RESIDENCY;
        required_stability = NORMAL_STABLE_COUNT;
      end
    endcase
    if (required_residency < MIN_MODE_RESIDENCY) begin
      required_residency = MIN_MODE_RESIDENCY;
    end
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
      end else if (residency_counter != MAX_RESIDENCY_VALUE) begin
        residency_counter <= residency_counter + 1'b1;
      end

      if (desired_mode == last_desired_mode) begin
        if (stable_counter != MAX_STABILITY_VALUE) begin
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
                   (residency_counter >= required_residency) &&
                   (stable_counter >= required_stability)) begin
        reconfig_request <= 1'b1;
        requested_mode   <= desired_mode;
      end
    end
  end
endmodule
