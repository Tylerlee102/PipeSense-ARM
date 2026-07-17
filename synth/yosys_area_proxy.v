// Common synthesizable core shell for relative PipeSense area measurements.
//
// The baseline and integrated tops use this identical shell. The integrated
// top instantiates the production observer, controller, and reconfiguration
// RTL from rtl/; this file does not replicate those modules.

module arm_like_core (
  input         clk,
  input         rst_n,
  input  [31:0] instr_in,
  input  [31:0] mem_in,
  input         stall,
  input         flush,
  output [31:0] state_hash,
  output        if_valid,
  output        id_valid,
  output        ex_valid,
  output        mem_valid,
  output        wb_valid,
  output        stall_if,
  output        branch_taken,
  output        load_use_hazard,
  output        mem_wait,
  output        instruction_retired,
  output        pipeline_empty
);
  reg [7:0] pc;
  reg [31:0] r1;
  reg [31:0] r2;
  reg [31:0] r3;
  reg [31:0] r4;
  reg [31:0] if_id_instr;
  reg [31:0] id_ex_instr;
  reg [31:0] ex_mem_instr;
  reg [31:0] mem_wb_instr;
  reg if_id_valid;
  reg id_ex_valid;
  reg ex_mem_valid;
  reg mem_wb_valid;

  wire [3:0] opcode = id_ex_instr[31:28];
  wire [31:0] alu_add = r1 + r2;
  wire [31:0] alu_sub = r1 - r2;
  wire [31:0] alu_logic = (r1 & r2) ^ (r3 | r4);
  wire is_mem = (opcode == 4'h6) || (opcode == 4'h7);
  wire is_load = opcode == 4'h6;
  wire is_branch = opcode == 4'h8;
  wire [31:0] ex_result = is_mem ? (alu_add + mem_in) :
                           (is_branch ? {24'd0, pc} :
                            ((opcode == 4'h2) ? alu_sub : alu_logic));

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      pc <= 8'd0;
      r1 <= 32'd1;
      r2 <= 32'd2;
      r3 <= 32'd3;
      r4 <= 32'd4;
      if_id_instr <= 32'd0;
      id_ex_instr <= 32'd0;
      ex_mem_instr <= 32'd0;
      mem_wb_instr <= 32'd0;
      if_id_valid <= 1'b0;
      id_ex_valid <= 1'b0;
      ex_mem_valid <= 1'b0;
      mem_wb_valid <= 1'b0;
    end else if (!stall) begin
      pc <= flush ? instr_in[7:0] : pc + 8'd1;
      if_id_instr <= flush ? 32'd0 : instr_in;
      id_ex_instr <= if_id_instr;
      ex_mem_instr <= id_ex_instr ^ ex_result;
      mem_wb_instr <= ex_mem_instr;
      if_id_valid <= !flush;
      id_ex_valid <= if_id_valid && !flush;
      ex_mem_valid <= id_ex_valid;
      mem_wb_valid <= ex_mem_valid;
      if (mem_wb_valid) begin
        r1 <= r2 + ex_result;
        r2 <= r3 ^ mem_wb_instr;
        r3 <= r4 + {24'd0, pc};
        r4 <= r1 ^ mem_in;
      end
    end
  end

  assign state_hash = r1 ^ r2 ^ r3 ^ r4 ^ if_id_instr ^ id_ex_instr ^
                      ex_mem_instr ^ mem_wb_instr ^ {24'd0, pc};
  assign if_valid = !stall && !flush;
  assign id_valid = if_id_valid;
  assign ex_valid = id_ex_valid;
  assign mem_valid = ex_mem_valid;
  assign wb_valid = mem_wb_valid;
  assign stall_if = stall;
  assign branch_taken = flush;
  assign load_use_hazard = id_ex_valid && is_load && if_id_valid;
  assign mem_wait = stall && is_mem;
  assign instruction_retired = mem_wb_valid;
  assign pipeline_empty = !(if_id_valid || id_ex_valid || ex_mem_valid || mem_wb_valid);
endmodule

module pipesense_integrated_core (
  input         clk,
  input         rst_n,
  input         adaptive_enable,
  input  [31:0] instr_in,
  input  [31:0] mem_in,
  input         stall,
  input         flush,
  output [31:0] state_hash,
  output [2:0]  phase_estimate,
  output [2:0]  current_mode,
  output        reconfig_active,
  output        reconfig_done
);
  wire if_valid;
  wire id_valid;
  wire ex_valid;
  wire mem_valid;
  wire wb_valid;
  wire stall_if;
  wire branch_taken;
  wire load_use_hazard;
  wire mem_wait;
  wire instruction_retired;
  wire pipeline_empty;
  wire window_done;
  wire reconfig_request;
  wire [2:0] requested_mode;
  wire [2:0] requested_mode_latched;
  wire stop_fetch;

  arm_like_core core (
    .clk(clk),
    .rst_n(rst_n),
    .instr_in(instr_in),
    .mem_in(mem_in),
    .stall(stall || stop_fetch),
    .flush(flush),
    .state_hash(state_hash),
    .if_valid(if_valid),
    .id_valid(id_valid),
    .ex_valid(ex_valid),
    .mem_valid(mem_valid),
    .wb_valid(wb_valid),
    .stall_if(stall_if),
    .branch_taken(branch_taken),
    .load_use_hazard(load_use_hazard),
    .mem_wait(mem_wait),
    .instruction_retired(instruction_retired),
    .pipeline_empty(pipeline_empty)
  );

  pipeline_observer #(
    .WINDOW_SIZE(32)
  ) observer (
    .clk(clk),
    .rst_n(rst_n),
    .if_valid(if_valid),
    .id_valid(id_valid),
    .ex_valid(ex_valid),
    .mem_valid(mem_valid),
    .wb_valid(wb_valid),
    .stall_if(stall_if),
    .flush(flush),
    .branch_taken(branch_taken),
    .load_use_hazard(load_use_hazard),
    .mem_wait(mem_wait),
    .instruction_retired(instruction_retired),
    .phase_estimate(phase_estimate),
    .window_done(window_done)
  );

  adaptive_controller #(
    .MIN_MODE_RESIDENCY(8),
    .PHASE_STABLE_COUNT(1)
  ) controller (
    .clk(clk),
    .rst_n(rst_n),
    .adaptive_enable(adaptive_enable),
    .phase_estimate(phase_estimate),
    .current_mode(current_mode),
    .reconfig_ack(reconfig_done),
    .reconfig_active(reconfig_active),
    .reconfig_request(reconfig_request),
    .requested_mode(requested_mode)
  );

  reconfig_unit reconfig (
    .clk(clk),
    .rst_n(rst_n),
    .boot_mode(3'd0),
    .reconfig_request(reconfig_request),
    .requested_mode(requested_mode),
    .pipeline_empty(pipeline_empty),
    .mem_wait(mem_wait),
    .current_mode(current_mode),
    .requested_mode_latched(requested_mode_latched),
    .reconfig_active(reconfig_active),
    .reconfig_done(reconfig_done),
    .stop_fetch(stop_fetch)
  );
endmodule
