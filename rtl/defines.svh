`timescale 1ns/1ps

`ifndef PIPESENSE_DEFINES_SVH
`define PIPESENSE_DEFINES_SVH

package pipesense_defs;
  localparam int XLEN = 32;
  localparam int REG_COUNT = 16;

  typedef enum logic [3:0] {
    OP_NOP  = 4'h0,
    OP_ADD  = 4'h1,
    OP_SUB  = 4'h2,
    OP_AND  = 4'h3,
    OP_ORR  = 4'h4,
    OP_EOR  = 4'h5,
    OP_LDR  = 4'h6,
    OP_STR  = 4'h7,
    OP_B    = 4'h8,
    OP_CMP  = 4'h9,
    OP_HALT = 4'hf
  } pipesense_opcode_e;

  localparam logic [3:0] COND_AL = 4'd0;
  localparam logic [3:0] COND_EQ = 4'd1;
  localparam logic [3:0] COND_NE = 4'd2;

  typedef enum logic [2:0] {
    PHASE_BALANCED         = 3'd0,
    PHASE_BRANCH_HEAVY     = 3'd1,
    PHASE_MEMORY_STALL     = 3'd2,
    PHASE_LOAD_USE_HAZARD  = 3'd3,
    PHASE_FRONTEND_STALL   = 3'd4,
    PHASE_IDLE_OR_LOW_UTIL = 3'd5
  } pipesense_phase_e;

  typedef enum logic [2:0] {
    MODE_NORMAL     = 3'd0,
    MODE_BRANCH_OPT = 3'd1,
    MODE_MEMORY_OPT = 3'd2,
    MODE_HAZARD_OPT = 3'd3,
    MODE_LOW_POWER  = 3'd4
  } pipesense_mode_e;
endpackage

`endif
