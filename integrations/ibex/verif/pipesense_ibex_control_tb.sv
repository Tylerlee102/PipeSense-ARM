`timescale 1ns/1ps

module pipesense_ibex_control_tb;
  logic clk = 0;
  logic rst_n = 0;
  logic retire = 0;
  logic branch = 0;
  logic fetch_wait = 0;
  logic pipeline_empty = 0;
  logic fetch_hold;
  logic fast_branch;
  logic prefetch_enable;
  logic drain_active;
  logic current_mode;
  logic [31:0] transitions;
  logic [31:0] drain_cycles;
  logic mode_commit;

  always #5 clk = ~clk;

  pipesense_ibex_control #(
    .Policy(2),
    .ObservationWindow(8),
    .MinimumResidency(4)
  ) dut (
    .clk_i(clk),
    .rst_ni(rst_n),
    .retire_i(retire),
    .branch_i(branch),
    .fetch_wait_i(fetch_wait),
    .pipeline_empty_i(pipeline_empty),
    .fetch_hold_o(fetch_hold),
    .fast_branch_o(fast_branch),
    .prefetch_enable_o(prefetch_enable),
    .drain_active_o(drain_active),
    .current_mode_o(current_mode),
    .transition_count_o(transitions),
    .drain_cycle_count_o(drain_cycles),
    .mode_commit_o(mode_commit)
  );

  task automatic retire_one(input logic is_branch);
    begin
      @(negedge clk);
      retire = 1;
      branch = is_branch;
      @(posedge clk);
      @(negedge clk);
      retire = 0;
      branch = 0;
      @(posedge clk);
    end
  endtask

  initial begin
    repeat (2) @(posedge clk);
    @(negedge clk);
    rst_n = 1;

    // Six branch events in one eight-retirement window request branch mode.
    repeat (6) retire_one(1);
    repeat (2) retire_one(0);
    if (!drain_active || !fetch_hold) $fatal(1, "branch-mode drain was not requested");
    if (current_mode != 0) $fatal(1, "mode changed before the pipeline drained");

    @(negedge clk);
    pipeline_empty = 1;
    @(posedge clk);
    #1;
    @(negedge clk);
    pipeline_empty = 0;
    if (!mode_commit || current_mode != 1 || transitions != 1)
      $fatal(1, "branch-mode commit failed");
    if (!fast_branch || prefetch_enable) $fatal(1, "branch-mode mechanisms not visible");

    // A branch-free window requests sequential-prefetch mode.
    repeat (8) retire_one(0);
    if (!drain_active || current_mode != 1) $fatal(1, "sequential-mode drain was not requested");
    @(negedge clk);
    pipeline_empty = 1;
    @(posedge clk);
    #1;
    if (!mode_commit || current_mode != 0 || transitions != 2)
      $fatal(1, "sequential-mode commit failed");
    if (fast_branch || !prefetch_enable) $fatal(1, "sequential-mode mechanisms not visible");

    $display("PIPESENSE_IBEX_CONTROL_PASS transitions=%0d", transitions);
    $finish;
  end
endmodule
