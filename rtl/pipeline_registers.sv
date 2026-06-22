`include "defines.svh"

// Generic valid/data pipeline register used as a small reusable building block.
module pipeline_register #(
  parameter int WIDTH = 32
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             enable,
  input  logic             flush,
  input  logic             valid_in,
  input  logic [WIDTH-1:0] data_in,
  output logic             valid_out,
  output logic [WIDTH-1:0] data_out
);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      valid_out <= 1'b0;
      data_out  <= '0;
    end else if (flush) begin
      valid_out <= 1'b0;
      data_out  <= '0;
    end else if (enable) begin
      valid_out <= valid_in;
      data_out  <= data_in;
    end
  end
endmodule
