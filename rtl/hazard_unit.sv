`include "defines.svh"

// Detects the classic load-use dependency between ID and EX.
module hazard_unit (
  input  logic             id_valid,
  input  logic [31:0]      id_instr,
  input  logic             ex_valid,
  input  logic [3:0]       ex_opcode,
  input  logic [3:0]       ex_rd,
  input  logic             hazard_opt_mode,
  output logic             load_use_hazard,
  output logic             stall_if,
  output logic             stall_id,
  output logic             bubble_ex
);
  logic [3:0] id_opcode;
  logic [3:0] id_rd;
  logic [3:0] id_rn;
  logic [3:0] id_rm;
  logic       uses_rn;
  logic       uses_rm;
  logic       uses_rd_as_src;
  logic       depends_on_ex_load;

  assign id_opcode = id_instr[31:28];
  assign id_rd     = id_instr[27:24];
  assign id_rn     = id_instr[23:20];
  assign id_rm     = id_instr[19:16];

  always_comb begin
    uses_rn        = 1'b0;
    uses_rm        = 1'b0;
    uses_rd_as_src = 1'b0;

    case (id_opcode)
      OP_ADD, OP_SUB, OP_AND, OP_ORR, OP_EOR: begin
        uses_rn = 1'b1;
        uses_rm = 1'b1;
      end
      OP_LDR: begin
        uses_rn = 1'b1;
      end
      OP_STR: begin
        uses_rn        = 1'b1;
        uses_rd_as_src = 1'b1;
      end
      OP_CMP: begin
        uses_rn = 1'b1;
        uses_rm = 1'b1;
      end
      default: begin
        uses_rn        = 1'b0;
        uses_rm        = 1'b0;
        uses_rd_as_src = 1'b0;
      end
    endcase
  end

  assign depends_on_ex_load =
      ex_valid &&
      (ex_opcode == OP_LDR) &&
      (ex_rd != 4'd0) &&
      ((uses_rn && (id_rn == ex_rd)) ||
       (uses_rm && (id_rm == ex_rd)) ||
       (uses_rd_as_src && (id_rd == ex_rd)));

  assign load_use_hazard = id_valid && depends_on_ex_load;
  // MODE_HAZARD_OPT models an additional load-result bypass path, so the raw
  // dependence is still reported to the observer but not converted into a stall.
  assign stall_if  = load_use_hazard && !hazard_opt_mode;
  assign stall_id  = load_use_hazard && !hazard_opt_mode;
  assign bubble_ex = load_use_hazard && !hazard_opt_mode;
endmodule
