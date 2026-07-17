`include "defines.svh"

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
  output logic             stop_fetch
);
  logic        start_reconfig;

  assign start_reconfig = reconfig_request &&
                          !reconfig_active &&
                          (requested_mode != current_mode);
  assign stop_fetch = reconfig_active || start_reconfig;

  // boot_mode is configurable, so reset is sampled synchronously instead of
  // being used as a data-dependent asynchronous reset value.
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      current_mode            <= boot_mode;
      requested_mode_latched  <= boot_mode;
      reconfig_active         <= 1'b0;
      reconfig_done           <= 1'b0;
    end else begin
      reconfig_done <= 1'b0;

      if (start_reconfig) begin
        reconfig_active        <= 1'b1;
        requested_mode_latched <= requested_mode;
      end else if (reconfig_active) begin
        if (pipeline_empty && !mem_wait) begin
          current_mode    <= requested_mode_latched;
          reconfig_active <= 1'b0;
          reconfig_done   <= 1'b1;
        end
      end
    end
  end
endmodule
