// SPDX-License-Identifier: Apache-2.0
// PipeSense policy and drain-before-switch control for the pinned Ibex integration.
module pipesense_ibex_control #(
  parameter int unsigned Policy = 0,
  parameter int unsigned ObservationWindow = 64,
  parameter int unsigned MinimumResidency = 64
) (
  input  logic        clk_i,
  input  logic        rst_ni,
  input  logic        retire_i,
  input  logic        branch_i,
  input  logic        fetch_wait_i,
  input  logic        pipeline_empty_i,
  output logic        fetch_hold_o,
  output logic        fast_branch_o,
  output logic        prefetch_enable_o,
  output logic        drain_active_o,
  output logic        current_mode_o,
  output logic [31:0] transition_count_o,
  output logic [31:0] drain_cycle_count_o,
  output logic        mode_commit_o
);
  localparam logic ModeSequential = 1'b0;
  localparam logic ModeBranch = 1'b1;

  logic current_mode_q;
  logic requested_mode_q;
  logic drain_active_q;
  logic [31:0] window_cycle_q;
  logic [31:0] branch_count_q;
  logic [31:0] retire_count_q;
  logic [31:0] fetch_wait_count_q;
  logic [31:0] total_branch_count_q;
  logic [31:0] total_fetch_wait_count_q;
  logic [31:0] residency_q;
  logic [31:0] transition_count_q;
  logic [31:0] drain_cycle_count_q;
  logic mode_commit_q;
  logic classified_mode;
  logic branch_seen_q;
  logic branch_event;

  assign branch_event = branch_i & ~branch_seen_q;

  // A branch-dense window selects the physical branch-target path. Other
  // windows select sequential prefetching. Both modes use real Ibex datapaths.
  assign classified_mode = current_mode_q == ModeSequential ?
                           (branch_count_q >= 32'd6) :
                           (branch_count_q >= 32'd3);

  assign fetch_hold_o = drain_active_q;
  assign drain_active_o = drain_active_q;
  assign current_mode_o = current_mode_q;
  assign transition_count_o = transition_count_q;
  assign drain_cycle_count_o = drain_cycle_count_q;
  assign mode_commit_o = mode_commit_q;

  always_comb begin
    unique case (Policy)
      0: begin
        fast_branch_o = 1'b0;
        prefetch_enable_o = 1'b1;
      end
      1: begin
        fast_branch_o = 1'b1;
        prefetch_enable_o = 1'b0;
      end
      default: begin
        fast_branch_o = current_mode_q == ModeBranch;
        prefetch_enable_o = current_mode_q == ModeSequential;
      end
    endcase
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      current_mode_q <= Policy == 1 ? ModeBranch : ModeSequential;
      requested_mode_q <= ModeSequential;
      drain_active_q <= 1'b0;
      window_cycle_q <= '0;
      branch_count_q <= '0;
      retire_count_q <= '0;
      fetch_wait_count_q <= '0;
      total_branch_count_q <= '0;
      total_fetch_wait_count_q <= '0;
      residency_q <= '0;
      transition_count_q <= '0;
      drain_cycle_count_q <= '0;
      mode_commit_q <= 1'b0;
      branch_seen_q <= 1'b0;
    end else begin
      mode_commit_q <= 1'b0;
      branch_seen_q <= branch_i;

      if (Policy >= 2) begin
        if (retire_i && residency_q != 32'hffff_ffff) begin
          residency_q <= residency_q + 1'b1;
        end

        if (drain_active_q) begin
          drain_cycle_count_q <= drain_cycle_count_q + 1'b1;
          if (pipeline_empty_i) begin
            current_mode_q <= requested_mode_q;
            drain_active_q <= 1'b0;
            residency_q <= '0;
            transition_count_q <= transition_count_q + 1'b1;
            mode_commit_q <= 1'b1;
          end
        end else begin
          if (retire_i) begin
            window_cycle_q <= window_cycle_q + 1'b1;
            retire_count_q <= retire_count_q + 1'b1;
          end
          if (branch_event) begin
            branch_count_q <= branch_count_q + 1'b1;
            total_branch_count_q <= total_branch_count_q + 1'b1;
          end
          if (fetch_wait_i) begin
            fetch_wait_count_q <= fetch_wait_count_q + 1'b1;
            total_fetch_wait_count_q <= total_fetch_wait_count_q + 1'b1;
          end

          if (retire_i && (window_cycle_q == ObservationWindow - 1)) begin
            window_cycle_q <= '0;
            branch_count_q <= '0;
            retire_count_q <= '0;
            fetch_wait_count_q <= '0;
            if ((classified_mode != current_mode_q) &&
                (residency_q >= MinimumResidency)) begin
              requested_mode_q <= classified_mode;
              drain_active_q <= 1'b1;
`ifndef SYNTHESIS
              $display("PIPESENSE_REQUEST from=%0d to=%0d branches=%0d retired=%0d",
                       current_mode_q, classified_mode, branch_count_q, retire_count_q);
`endif
            end
          end
        end
      end
    end
  end

`ifndef SYNTHESIS
  final begin
    $display("PIPESENSE_STATS policy=%0d mode=%0d transitions=%0d drain_cycles=%0d branches=%0d fetch_waits=%0d window_branches=%0d window_retired=%0d",
             Policy, current_mode_q, transition_count_q, drain_cycle_count_q,
             total_branch_count_q, total_fetch_wait_count_q, branch_count_q, retire_count_q);
  end
`endif

endmodule
