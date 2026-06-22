`include "defines.svh"
import pipesense_defs::*;

// Safely changes modes by stopping fetch and allowing the in-flight pipeline to
// drain before committing the new microarchitectural mode.
module reconfig_unit (
  input  logic             clk,
  input  logic             rst_n,
  input  pipesense_mode_e  boot_mode,
  input  logic             reconfig_request,
  input  pipesense_mode_e  requested_mode,
  input  logic             pipeline_empty,
  input  logic             mem_wait,
  output pipesense_mode_e  current_mode,
  output pipesense_mode_e  requested_mode_latched,
  output logic             reconfig_active,
  output logic             reconfig_done,
  output logic             stop_fetch,
  output logic [31:0]      reconfig_stall_cycles,
  output logic [31:0]      total_reconfigurations,
  output logic [31:0]      total_reconfig_penalty
);
  logic [31:0] active_counter;
  logic        start_reconfig;

  assign start_reconfig = reconfig_request &&
                          !reconfig_active &&
                          (requested_mode != current_mode);
  assign stop_fetch = reconfig_active || start_reconfig;
  assign reconfig_stall_cycles = active_counter;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      current_mode            <= boot_mode;
      requested_mode_latched  <= boot_mode;
      reconfig_active         <= 1'b0;
      reconfig_done           <= 1'b0;
      active_counter          <= '0;
      total_reconfigurations  <= '0;
      total_reconfig_penalty  <= '0;
    end else begin
      reconfig_done <= 1'b0;

      if (start_reconfig) begin
        reconfig_active        <= 1'b1;
        requested_mode_latched <= requested_mode;
        active_counter         <= 32'd1;
      end else if (reconfig_active) begin
        if (pipeline_empty && !mem_wait) begin
          current_mode           <= requested_mode_latched;
          reconfig_active        <= 1'b0;
          reconfig_done          <= 1'b1;
          total_reconfigurations <= total_reconfigurations + 1'b1;
          total_reconfig_penalty <= total_reconfig_penalty + active_counter;
          active_counter         <= '0;
        end else begin
          active_counter <= active_counter + 1'b1;
        end
      end
    end
  end
endmodule
