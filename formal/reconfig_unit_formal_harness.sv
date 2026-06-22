`include "defines.svh"
import pipesense_defs::*;

module reconfig_unit_formal_harness;
  logic clk;
  logic rst_n;
  pipesense_mode_e boot_mode;
  logic reconfig_request;
  pipesense_mode_e requested_mode;
  logic pipeline_empty;
  logic mem_wait;
  pipesense_mode_e current_mode;
  pipesense_mode_e requested_mode_latched;
  logic reconfig_active;
  logic reconfig_done;
  logic stop_fetch;
  logic [31:0] reconfig_stall_cycles;
  logic [31:0] total_reconfigurations;
  logic [31:0] total_reconfig_penalty;

`ifdef FORMAL
  (* anyseq *) logic any_reconfig_request;
  (* anyseq *) pipesense_mode_e any_requested_mode;
  (* anyseq *) logic any_pipeline_empty;
  (* anyseq *) logic any_mem_wait;

  always @* begin
    reconfig_request = any_reconfig_request;
    requested_mode   = any_requested_mode;
    pipeline_empty   = any_pipeline_empty;
    mem_wait         = any_mem_wait;
    boot_mode        = MODE_NORMAL;
  end
`endif

  initial clk = 1'b0;
  always #1 clk = ~clk;

  reconfig_unit dut (
    .clk(clk),
    .rst_n(rst_n),
    .boot_mode(boot_mode),
    .reconfig_request(reconfig_request),
    .requested_mode(requested_mode),
    .pipeline_empty(pipeline_empty),
    .mem_wait(mem_wait),
    .current_mode(current_mode),
    .requested_mode_latched(requested_mode_latched),
    .reconfig_active(reconfig_active),
    .reconfig_done(reconfig_done),
    .stop_fetch(stop_fetch),
    .reconfig_stall_cycles(reconfig_stall_cycles),
    .total_reconfigurations(total_reconfigurations),
    .total_reconfig_penalty(total_reconfig_penalty)
  );

  reconfig_safety_properties props (
    .clk(clk),
    .rst_n(rst_n),
    .reconfig_request(reconfig_request),
    .requested_mode(requested_mode),
    .pipeline_empty(pipeline_empty),
    .mem_wait(mem_wait),
    .current_mode(current_mode),
    .requested_mode_latched(requested_mode_latched),
    .reconfig_active(reconfig_active),
    .reconfig_done(reconfig_done),
    .stop_fetch(stop_fetch)
  );

`ifdef FORMAL
  initial begin
    rst_n = 1'b0;
  end

  always @(posedge clk) begin
    rst_n <= 1'b1;
    assume((requested_mode == MODE_NORMAL) ||
           (requested_mode == MODE_BRANCH_OPT) ||
           (requested_mode == MODE_MEMORY_OPT) ||
           (requested_mode == MODE_HAZARD_OPT) ||
           (requested_mode == MODE_LOW_POWER));

    if (reconfig_done) begin
      assert(pipeline_empty && !mem_wait);
    end

    if (reconfig_active) begin
      assert(stop_fetch);
    end
  end
`endif
endmodule
