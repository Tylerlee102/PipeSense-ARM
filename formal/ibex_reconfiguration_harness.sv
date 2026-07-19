module ibex_reconfiguration_harness (
  input logic clk,
  input logic rst_n
);
  (* anyseq *) logic retire;
  (* anyseq *) logic issue;
  (* anyseq *) logic branch;
  (* anyseq *) logic fetch_wait;
  logic pipeline_empty;
  logic fetch_hold;
  logic fast_branch;
  logic prefetch_enable;
  logic drain_active;
  logic current_mode;
  logic [31:0] transitions;
  logic [31:0] drain_cycles;
  logic mode_commit;
  logic [3:0] in_flight;
  logic [3:0] issued_count;
  logic [3:0] retired_count;

  assign pipeline_empty = in_flight == 0;

  pipesense_ibex_control #(
    .Policy(2),
    .ObservationWindow(4),
    .MinimumResidency(2)
  ) dut (.*,
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

  logic past_valid = 0;
  always_ff @(posedge clk) begin
    past_valid <= 1;
    if (!past_valid) assume(!rst_n);
    if (past_valid && !$past(rst_n)) assume(rst_n);

    if (!rst_n) begin
      in_flight <= 0;
      issued_count <= 0;
      retired_count <= 0;
    end else begin
      assume(!(issue && fetch_hold));
      assume(!(retire && (in_flight == 0) && !issue));
      case ({issue, retire})
        2'b10: in_flight <= in_flight + 1'b1;
        2'b01: in_flight <= in_flight - 1'b1;
        default: in_flight <= in_flight;
      endcase
      if (issue) issued_count <= issued_count + 1'b1;
      if (retire) retired_count <= retired_count + 1'b1;
    end

    if (rst_n) begin
      assert(retired_count <= issued_count);
      assert(in_flight == issued_count - retired_count);
      assert(fetch_hold == drain_active);
      assert(fast_branch == current_mode);
      assert(prefetch_enable == !current_mode);
      if (drain_active && !pipeline_empty) assert($stable(current_mode));
      if (mode_commit) begin
        assert($past(drain_active));
        assert($past(pipeline_empty));
        assert($past(in_flight) == 0);
        assert(current_mode != $past(current_mode));
      end
      if (current_mode != $past(current_mode)) begin
        assert(mode_commit);
        assert($past(in_flight) == 0);
      end
    end
  end
endmodule
