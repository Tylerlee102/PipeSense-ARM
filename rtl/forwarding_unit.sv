`include "defines.svh"
import pipesense_defs::*;

// Two-source forwarding network for EX-stage operands.
module forwarding_unit (
  input  logic        hazard_opt_mode,
  input  logic [3:0]  src_a,
  input  logic [3:0]  src_b,
  input  logic [31:0] reg_a,
  input  logic [31:0] reg_b,
  input  logic        ex_mem_valid,
  input  logic        ex_mem_reg_write,
  input  logic        ex_mem_mem_read,
  input  logic [3:0]  ex_mem_rd,
  input  logic [31:0] ex_mem_data,
  input  logic        mem_wb_valid,
  input  logic        mem_wb_reg_write,
  input  logic [3:0]  mem_wb_rd,
  input  logic [31:0] mem_wb_data,
  output logic [31:0] operand_a,
  output logic [31:0] operand_b
);
  logic can_forward_ex_mem;

  assign can_forward_ex_mem = ex_mem_valid &&
                              ex_mem_reg_write &&
                              (ex_mem_rd != 4'd0) &&
                              (!ex_mem_mem_read || hazard_opt_mode);

  always_comb begin
    operand_a = reg_a;
    operand_b = reg_b;

    if (can_forward_ex_mem && (ex_mem_rd == src_a)) begin
      operand_a = ex_mem_data;
    end else if (mem_wb_valid && mem_wb_reg_write && (mem_wb_rd != 4'd0) &&
                 (mem_wb_rd == src_a)) begin
      operand_a = mem_wb_data;
    end

    if (can_forward_ex_mem && (ex_mem_rd == src_b)) begin
      operand_b = ex_mem_data;
    end else if (mem_wb_valid && mem_wb_reg_write && (mem_wb_rd != 4'd0) &&
                 (mem_wb_rd == src_b)) begin
      operand_b = mem_wb_data;
    end
  end
endmodule
