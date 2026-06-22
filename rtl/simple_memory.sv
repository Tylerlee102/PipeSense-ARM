`include "defines.svh"

// Small simulation-friendly word memory. Reads are combinational and writes are
// synchronous, which keeps the educational pipeline easy to inspect.
module simple_memory #(
  parameter int ADDR_WIDTH  = 8,
  parameter int DATA_WIDTH  = 32,
  parameter int WAIT_PERIOD = 0
) (
  input  logic                  clk,
  input  logic                  read_en,
  input  logic                  write_en,
  input  logic                  mitigate_wait,
  input  logic [ADDR_WIDTH-1:0] addr,
  input  logic [DATA_WIDTH-1:0] wdata,
  output logic [DATA_WIDTH-1:0] rdata,
  output logic                  wait_request
);
  localparam int DEPTH = 1 << ADDR_WIDTH;

  logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];

  assign rdata = mem[addr];

  generate
    if (WAIT_PERIOD == 0) begin : no_wait_model
      assign wait_request = 1'b0;
    end else begin : periodic_wait_model
      always_comb begin
        wait_request = (read_en || write_en) &&
                       !mitigate_wait &&
                       ((addr % WAIT_PERIOD) == (WAIT_PERIOD - 1));
      end
    end
  endgenerate

  always_ff @(posedge clk) begin
    if (write_en) begin
      mem[addr] <= wdata;
    end
  end

  task automatic clear();
    int i;
    begin
      for (i = 0; i < DEPTH; i++) begin
        mem[i] = '0;
      end
    end
  endtask

  task automatic write_word(input int unsigned index, input logic [DATA_WIDTH-1:0] value);
    begin
      if (index < DEPTH) begin
        mem[index] = value;
      end
    end
  endtask

  task automatic read_word(input int unsigned index, output logic [DATA_WIDTH-1:0] value);
    begin
      if (index < DEPTH) begin
        value = mem[index];
      end else begin
        value = '0;
      end
    end
  endtask
endmodule
