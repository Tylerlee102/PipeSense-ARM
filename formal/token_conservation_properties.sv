// Formal instruction-token conservation properties for a five-stage pipeline.
//
// This module is intentionally independent of the full PipeSense core. It
// captures the token-level obligations used by the safety proof sketch:
// live tokens are unique, younger tokens stay in earlier stages, retirement
// consumes the writeback token, and every fetched token is either live,
// retired, or flushed.
module token_conservation_properties #(
  parameter int TAG_WIDTH = 8,
  parameter int COUNT_WIDTH = 8
) (
  input logic                   clk,
  input logic                   rst_n,
  input logic                   if_valid,
  input logic                   id_valid,
  input logic                   ex_valid,
  input logic                   mem_valid,
  input logic                   wb_valid,
  input logic [TAG_WIDTH-1:0]   if_tag,
  input logic [TAG_WIDTH-1:0]   id_tag,
  input logic [TAG_WIDTH-1:0]   ex_tag,
  input logic [TAG_WIDTH-1:0]   mem_tag,
  input logic [TAG_WIDTH-1:0]   wb_tag,
  input logic                   retire_valid,
  input logic [TAG_WIDTH-1:0]   retire_tag,
  input logic [COUNT_WIDTH-1:0] fetched_count,
  input logic [COUNT_WIDTH-1:0] retired_count,
  input logic [COUNT_WIDTH-1:0] flushed_count
);
  logic past_valid;
  logic [COUNT_WIDTH-1:0] live_count;
  logic [COUNT_WIDTH-1:0] accounted_count;
  logic [TAG_WIDTH-1:0] last_retire_tag;
  logic retire_seen;

  always @* begin
    live_count = {{(COUNT_WIDTH-1){1'b0}}, if_valid} +
                 {{(COUNT_WIDTH-1){1'b0}}, id_valid} +
                 {{(COUNT_WIDTH-1){1'b0}}, ex_valid} +
                 {{(COUNT_WIDTH-1){1'b0}}, mem_valid} +
                 {{(COUNT_WIDTH-1){1'b0}}, wb_valid};
    accounted_count = live_count + retired_count + flushed_count;
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      past_valid      <= 1'b0;
      last_retire_tag <= '0;
      retire_seen     <= 1'b0;
    end else begin
      past_valid <= 1'b1;
      if (retire_valid) begin
        last_retire_tag <= retire_tag;
        retire_seen     <= 1'b1;
      end
    end
  end

`ifdef FORMAL
  always @(posedge clk) begin
    if (rst_n && past_valid) begin
      assert(accounted_count == fetched_count);

      if (if_valid && id_valid) begin
        assert(if_tag != id_tag);
        assert(if_tag > id_tag);
      end
      if (if_valid && ex_valid) begin
        assert(if_tag != ex_tag);
        assert(if_tag > ex_tag);
      end
      if (if_valid && mem_valid) begin
        assert(if_tag != mem_tag);
        assert(if_tag > mem_tag);
      end
      if (if_valid && wb_valid) begin
        assert(if_tag != wb_tag);
        assert(if_tag > wb_tag);
      end
      if (id_valid && ex_valid) begin
        assert(id_tag != ex_tag);
        assert(id_tag > ex_tag);
      end
      if (id_valid && mem_valid) begin
        assert(id_tag != mem_tag);
        assert(id_tag > mem_tag);
      end
      if (id_valid && wb_valid) begin
        assert(id_tag != wb_tag);
        assert(id_tag > wb_tag);
      end
      if (ex_valid && mem_valid) begin
        assert(ex_tag != mem_tag);
        assert(ex_tag > mem_tag);
      end
      if (ex_valid && wb_valid) begin
        assert(ex_tag != wb_tag);
        assert(ex_tag > wb_tag);
      end
      if (mem_valid && wb_valid) begin
        assert(mem_tag != wb_tag);
        assert(mem_tag > wb_tag);
      end

      if (retire_valid) begin
        assert(wb_valid);
        assert(retire_tag == wb_tag);
        if (retire_seen) begin
          assert(retire_tag > last_retire_tag);
        end
      end

      cover(fetched_count >= 8'd4 && retired_count >= 8'd2 && flushed_count >= 8'd1);
    end
  end
`endif
endmodule
