`include "defines.svh"

// Optional assertion module for formal or assertion-enabled simulation flows.
// The assertions are written in a conservative immediate-assert style so common
// open-source formal tools can parse the scaffold.
module reconfig_safety_properties (
  input logic            clk,
  input logic            rst_n,
  input logic            reconfig_request,
  input pipesense_mode_e requested_mode,
  input logic            pipeline_empty,
  input logic            mem_wait,
  input pipesense_mode_e current_mode,
  input pipesense_mode_e requested_mode_latched,
  input logic            reconfig_active,
  input logic            reconfig_done,
  input logic            stop_fetch
);
  logic past_valid;
  logic saw_reconfig_request;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      past_valid          <= 1'b0;
      saw_reconfig_request <= 1'b0;
    end else begin
      past_valid <= 1'b1;
      if (reconfig_request && (requested_mode != current_mode)) begin
        saw_reconfig_request <= 1'b1;
      end
      if (reconfig_done) begin
        saw_reconfig_request <= 1'b0;
      end
    end
  end

`ifdef FORMAL
  always @(posedge clk) begin
    if (rst_n && past_valid) begin
      if (reconfig_done) begin
        assert($past(pipeline_empty && !mem_wait));
      end

      if (reconfig_active) begin
        assert(stop_fetch);
      end

      if ($past(reconfig_active) && reconfig_active) begin
        assert(current_mode == $past(current_mode));
      end

      if ($past(reconfig_active) && !$past(reconfig_done)) begin
        assert(requested_mode_latched == $past(requested_mode_latched));
      end

      if ($past(reconfig_done)) begin
        assert(current_mode == $past(requested_mode_latched));
      end

      cover(saw_reconfig_request && reconfig_done);
    end
  end
`endif
endmodule
