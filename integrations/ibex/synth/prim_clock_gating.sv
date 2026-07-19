// SPDX-License-Identifier: Apache-2.0
// FPGA mapping: keep the clock on and let sequential enables implement idling.
module prim_clock_gating #(
  parameter bit NoFpgaGate = 1'b0,
  parameter bit FpgaBufGlobal = 1'b1
) (
  input  logic clk_i,
  input  logic en_i,
  input  logic test_en_i,
  output logic clk_o
);
  logic unused_enable;
  assign unused_enable = en_i | test_en_i | NoFpgaGate | FpgaBufGlobal;
  assign clk_o = clk_i;
endmodule
