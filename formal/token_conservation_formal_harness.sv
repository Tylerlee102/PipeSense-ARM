// Symbolic five-stage token pipeline used to prove conservation properties.
//
// The harness abstracts away opcode semantics and models only token movement.
// A token is created on accepted fetch, shifts through IF/ID/EX/MEM/WB when the
// pipe is not stalled, can be flushed before retirement, and retires from WB.
module token_conservation_formal_harness;
  localparam int TAG_WIDTH = 8;
  localparam int COUNT_WIDTH = 8;

  logic clk;
  logic rst_n;
  logic fetch_valid;
  logic stall;
  logic flush;
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
  logic retire_valid;
  logic [TAG_WIDTH-1:0] retire_tag;
  logic [COUNT_WIDTH-1:0] fetched_count;
  logic [COUNT_WIDTH-1:0] retired_count;
  logic [COUNT_WIDTH-1:0] flushed_count;
  logic [COUNT_WIDTH-1:0] live_count_before_flush;
  logic [TAG_WIDTH-1:0] next_tag;

  assign retire_valid = rst_n && !flush && !stall && wb_valid;
  assign retire_tag = wb_tag;

`ifdef FORMAL
  (* anyseq *) logic any_fetch_valid;
  (* anyseq *) logic any_stall;
  (* anyseq *) logic any_flush;

  always @* begin
    fetch_valid = any_fetch_valid;
    stall       = any_stall;
    flush       = any_flush;
  end
`else
  initial begin
    fetch_valid = 1'b0;
    stall       = 1'b0;
    flush       = 1'b0;
  end
`endif

  initial clk = 1'b0;
  always #1 clk = ~clk;

  always @* begin
    live_count_before_flush = {{(COUNT_WIDTH-1){1'b0}}, if_valid} +
                              {{(COUNT_WIDTH-1){1'b0}}, id_valid} +
                              {{(COUNT_WIDTH-1){1'b0}}, ex_valid} +
                              {{(COUNT_WIDTH-1){1'b0}}, mem_valid} +
                              {{(COUNT_WIDTH-1){1'b0}}, wb_valid};
    next_tag = fetched_count + {{(TAG_WIDTH-1){1'b0}}, fetch_valid};
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      if_valid      <= 1'b0;
      id_valid      <= 1'b0;
      ex_valid      <= 1'b0;
      mem_valid     <= 1'b0;
      wb_valid      <= 1'b0;
      if_tag        <= '0;
      id_tag        <= '0;
      ex_tag        <= '0;
      mem_tag       <= '0;
      wb_tag        <= '0;
      fetched_count <= '0;
      retired_count <= '0;
      flushed_count <= '0;
    end else begin
      if (flush) begin
        flushed_count <= flushed_count + live_count_before_flush;
        if_valid      <= 1'b0;
        id_valid      <= 1'b0;
        ex_valid      <= 1'b0;
        mem_valid     <= 1'b0;
        wb_valid      <= 1'b0;
      end else if (!stall) begin
        if (retire_valid) begin
          retired_count <= retired_count + {{(COUNT_WIDTH-1){1'b0}}, wb_valid};
        end

        wb_valid  <= mem_valid;
        wb_tag    <= mem_tag;
        mem_valid <= ex_valid;
        mem_tag   <= ex_tag;
        ex_valid  <= id_valid;
        ex_tag    <= id_tag;
        id_valid  <= if_valid;
        id_tag    <= if_tag;
        if_valid  <= fetch_valid;
        if_tag    <= next_tag;

        if (fetch_valid) begin
          fetched_count <= fetched_count + {{(COUNT_WIDTH-1){1'b0}}, fetch_valid};
        end
      end
    end
  end

  token_conservation_properties #(
    .TAG_WIDTH(TAG_WIDTH),
    .COUNT_WIDTH(COUNT_WIDTH)
  ) props (
    .clk(clk),
    .rst_n(rst_n),
    .if_valid(if_valid),
    .id_valid(id_valid),
    .ex_valid(ex_valid),
    .mem_valid(mem_valid),
    .wb_valid(wb_valid),
    .if_tag(if_tag),
    .id_tag(id_tag),
    .ex_tag(ex_tag),
    .mem_tag(mem_tag),
    .wb_tag(wb_tag),
    .retire_valid(retire_valid),
    .retire_tag(retire_tag),
    .fetched_count(fetched_count),
    .retired_count(retired_count),
    .flushed_count(flushed_count)
  );

`ifdef FORMAL
  initial begin
    rst_n = 1'b0;
  end

  always @(posedge clk) begin
    rst_n <= 1'b1;
    assume(!(flush && stall));
    assume(fetched_count < 8'd120);
  end
`endif
endmodule
