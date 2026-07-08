// Bounded formal model for no duplicate commit across a safe mode switch.
//
// This is an abstract token pipeline, not the full PipeSense RTL. It models the
// safety contract needed for the dual-commit risk: while a reconfiguration is
// active, fetch is gated, older tokens drain, and the visible mode changes only
// when no stage is live. Tags are unique within the bounded run.
module no_double_commit_across_mode_switch_harness;
  localparam int TAG_WIDTH = 3;
  localparam int TAG_COUNT = 1 << TAG_WIDTH;

  logic clk;
  logic fetch_req;
  logic stall;
  logic flush;
  logic mode_request;
  logic current_mode;
  logic requested_mode;
  logic reconfig_active;
  logic mode_switch_seen;
  logic if_valid;
  logic id_valid;
  logic ex_valid;
  logic mem_valid;
  logic wb_valid;
  logic [TAG_WIDTH-1:0] if_tag;
  logic [TAG_WIDTH-1:0] id_tag;
  logic [TAG_WIDTH-1:0] ex_tag;
  logic [TAG_WIDTH-1:0] mem_tag;
  logic [TAG_WIDTH-1:0] wb_tag;
  logic [TAG_WIDTH:0] fetched_count;
  logic [TAG_COUNT-1:0] committed_tags;
  logic [TAG_COUNT-1:0] committed_before_switch;
  logic [TAG_WIDTH-1:0] commit_tag;
  logic retire_valid;
  logic pipeline_empty;
  logic accepted_fetch;

  assign pipeline_empty = !if_valid && !id_valid && !ex_valid && !mem_valid && !wb_valid;
  assign accepted_fetch = fetch_req && !reconfig_active && !stall && !flush;
  assign retire_valid = wb_valid && !stall && !flush;
  assign commit_tag = wb_tag;

`ifdef FORMAL
  (* anyseq *) logic any_fetch_req;
  (* anyseq *) logic any_stall;
  (* anyseq *) logic any_flush;
  (* anyseq *) logic any_mode_request;

  always @* begin
    fetch_req    = any_fetch_req;
    stall        = any_stall;
    flush        = any_flush;
    mode_request = any_mode_request;
  end
`else
  initial begin
    fetch_req    = 1'b0;
    stall        = 1'b0;
    flush        = 1'b0;
    mode_request = 1'b0;
  end
`endif

  initial begin
    current_mode            = 1'b0;
    requested_mode          = 1'b0;
    reconfig_active         = 1'b0;
    mode_switch_seen        = 1'b0;
    if_valid                = 1'b0;
    id_valid                = 1'b0;
    ex_valid                = 1'b0;
    mem_valid               = 1'b0;
    wb_valid                = 1'b0;
    if_tag                  = '0;
    id_tag                  = '0;
    ex_tag                  = '0;
    mem_tag                 = '0;
    wb_tag                  = '0;
    fetched_count           = '0;
    committed_tags          = '0;
    committed_before_switch = '0;
  end

`ifndef FORMAL
  initial clk = 1'b0;
  always #1 clk = !clk;
`endif

  always_ff @(posedge clk) begin
`ifdef FORMAL
    assume(!(stall && flush));
    assume(!flush);
    assume(fetched_count < TAG_COUNT);
`endif

    if (retire_valid) begin
      committed_tags[commit_tag] <= 1'b1;
    end

    if (mode_request && !reconfig_active && requested_mode == current_mode) begin
      requested_mode <= !current_mode;
      reconfig_active <= 1'b1;
    end

    if (reconfig_active && pipeline_empty) begin
      current_mode <= requested_mode;
      reconfig_active <= 1'b0;
      mode_switch_seen <= 1'b1;
      committed_before_switch <= committed_tags;
    end

    if (flush) begin
      if_valid  <= 1'b0;
      id_valid  <= 1'b0;
      ex_valid  <= 1'b0;
      mem_valid <= 1'b0;
      wb_valid  <= 1'b0;
    end else if (!stall) begin
      wb_valid  <= mem_valid;
      wb_tag    <= mem_tag;
      mem_valid <= ex_valid;
      mem_tag   <= ex_tag;
      ex_valid  <= id_valid;
      ex_tag    <= id_tag;
      id_valid  <= if_valid;
      id_tag    <= if_tag;
      if_valid  <= accepted_fetch;
      if_tag    <= fetched_count[TAG_WIDTH-1:0];

      if (accepted_fetch) begin
        fetched_count <= fetched_count + {{TAG_WIDTH{1'b0}}, 1'b1};
      end
    end
  end

`ifdef FORMAL
  always_ff @(posedge clk) begin
    if (retire_valid) begin
      assert(!committed_tags[commit_tag]);
      if (mode_switch_seen) begin
        assert(!committed_before_switch[commit_tag]);
      end
    end

    if (reconfig_active) begin
      assert(!accepted_fetch);
    end

    if (mode_switch_seen) begin
      cover(retire_valid);
    end
  end
`endif
endmodule
