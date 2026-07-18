`include "defines.svh"

`ifndef PIPESENSE_OBS_WINDOW
`define PIPESENSE_OBS_WINDOW 32
`endif
`ifndef PIPESENSE_DATA_WAIT_CYCLES
`define PIPESENSE_DATA_WAIT_CYCLES 2
`endif
`ifndef PIPESENSE_MIN_MODE_RESIDENCY
`define PIPESENSE_MIN_MODE_RESIDENCY 8
`endif
`ifdef PIPESENSE_ASYNC03_BASELINE
`define PIPESENSE_CONTROLLER_POLICY_VALUE 1
`else
`define PIPESENSE_CONTROLLER_POLICY_VALUE 0
`endif
`ifndef PIPESENSE_OBS_BRANCH_THRESHOLD
`define PIPESENSE_OBS_BRANCH_THRESHOLD 8
`endif
`ifndef PIPESENSE_OBS_MEM_STALL_THRESHOLD
`define PIPESENSE_OBS_MEM_STALL_THRESHOLD 8
`endif
`ifndef PIPESENSE_OBS_LOAD_USE_THRESHOLD
`define PIPESENSE_OBS_LOAD_USE_THRESHOLD 6
`endif
`ifndef PIPESENSE_OBS_FRONTEND_STALL_THRESHOLD
`define PIPESENSE_OBS_FRONTEND_STALL_THRESHOLD 10
`endif
`ifndef PIPESENSE_OBS_IDLE_RETIRE_THRESHOLD
`define PIPESENSE_OBS_IDLE_RETIRE_THRESHOLD 8
`endif
`ifdef PIPESENSE_DISABLE_OBSERVER
`define PIPESENSE_DISABLE_OBSERVER_VALUE 1
`else
`define PIPESENSE_DISABLE_OBSERVER_VALUE 0
`endif
`ifdef PIPESENSE_DISABLE_CONTROLLER
`define PIPESENSE_DISABLE_CONTROLLER_VALUE 1
`else
`define PIPESENSE_DISABLE_CONTROLLER_VALUE 0
`endif

// PipeSense-ARM research core: a compact ARM-like five-stage pipeline with a
// hardware observer/controller/reconfiguration loop.
module arm_like_core #(
  parameter int PC_WIDTH            = 8,
  parameter int OBS_WINDOW          = `PIPESENSE_OBS_WINDOW,
  parameter int DATA_WAIT_CYCLES    = `PIPESENSE_DATA_WAIT_CYCLES,
  parameter int MIN_MODE_RESIDENCY  = `PIPESENSE_MIN_MODE_RESIDENCY,
  parameter int OBS_BRANCH_THRESHOLD = `PIPESENSE_OBS_BRANCH_THRESHOLD,
  parameter int OBS_MEM_STALL_THRESHOLD = `PIPESENSE_OBS_MEM_STALL_THRESHOLD,
  parameter int OBS_LOAD_USE_THRESHOLD = `PIPESENSE_OBS_LOAD_USE_THRESHOLD,
  parameter int OBS_FRONTEND_STALL_THRESHOLD = `PIPESENSE_OBS_FRONTEND_STALL_THRESHOLD,
  parameter int OBS_IDLE_RETIRE_THRESHOLD = `PIPESENSE_OBS_IDLE_RETIRE_THRESHOLD,
  parameter int DISABLE_OBSERVER = `PIPESENSE_DISABLE_OBSERVER_VALUE,
  parameter int DISABLE_CONTROLLER = `PIPESENSE_DISABLE_CONTROLLER_VALUE,
  parameter int CONTROLLER_POLICY = `PIPESENSE_CONTROLLER_POLICY_VALUE
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             adaptive_enable,
  input  pipesense_mode_e  fixed_mode,
  input  logic             program_write_en,
  input  logic             program_select_dmem,
  input  logic [PC_WIDTH-1:0] program_addr,
  input  logic [31:0]      program_wdata,
  output pipesense_mode_e  current_mode,
  output pipesense_phase_e observed_phase,
  output logic             halted,
  output logic [31:0]      cycle_count,
  output logic [31:0]      retired_count,
  output logic [31:0]      stall_cycles,
  output logic [31:0]      flush_cycles,
  output logic [31:0]      mem_wait_cycles,
  output logic [31:0]      load_use_stalls,
  output logic [31:0]      reconfigurations,
  output logic [31:0]      reconfig_penalty,
  output logic [31:0]      energy_proxy,
  output logic [31:0]      safety_faults
);
  logic [31:0] regfile [0:REG_COUNT-1];
  logic [PC_WIDTH-1:0] pc;
  logic zero_flag;

  logic if_id_valid;
  logic [31:0] if_id_instr;
  logic [PC_WIDTH-1:0] if_id_pc;

  logic id_ex_valid;
  logic [31:0] id_ex_instr;
  logic [PC_WIDTH-1:0] id_ex_pc;
  logic [3:0] id_ex_opcode;
  logic [3:0] id_ex_rd;
  logic [3:0] id_ex_rn;
  logic [3:0] id_ex_rm;
  logic [15:0] id_ex_imm;
  logic [31:0] id_ex_rn_val;
  logic [31:0] id_ex_rm_val;
  logic [31:0] id_ex_rd_val;
  logic id_ex_reg_write;
  logic id_ex_mem_read;
  logic id_ex_mem_write;
  logic id_ex_branch;
  logic id_ex_cmp;
  logic id_ex_halt;
  logic id_ex_branch_resolved;
  logic id_ex_early_branch_taken;
  logic [PC_WIDTH-1:0] id_ex_early_branch_target;

  logic ex_mem_valid;
  logic [3:0] ex_mem_opcode;
  logic [3:0] ex_mem_rd;
  logic [31:0] ex_mem_alu_result;
  logic [31:0] ex_mem_store_data;
  logic ex_mem_reg_write;
  logic ex_mem_mem_read;
  logic ex_mem_mem_write;
  logic ex_mem_branch_taken;
  logic [PC_WIDTH-1:0] ex_mem_branch_target;
  logic ex_mem_cmp;
  logic ex_mem_cmp_zero;
  logic ex_mem_halt;

  logic mem_wb_valid;
  logic [3:0] mem_wb_opcode;
  logic [3:0] mem_wb_rd;
  logic [31:0] mem_wb_data;
  logic mem_wb_reg_write;
  logic mem_wb_halt;

  logic [31:0] imem_rdata;
  logic [31:0] dmem_rdata;
  logic program_write_active;
  logic [PC_WIDTH-1:0] imem_addr;
  logic [PC_WIDTH-1:0] dmem_port_addr;
  logic dmem_wait_request;
  logic dmem_read_en;
  logic dmem_write_en;
  logic [PC_WIDTH-1:0] dmem_addr;
  logic [31:0] dmem_wdata;

  logic [31:0] ex_operand_a;
  logic [31:0] ex_operand_b_raw;
  logic [31:0] ex_operand_b;
  logic [31:0] ex_store_data;
  logic [31:0] ex_alu_result;
  logic ex_cmp_zero;
  logic visible_zero_flag;
  logic ex_branch_taken;
  logic [PC_WIDTH-1:0] ex_branch_target;

  logic id_is_branch;
  logic id_branch_condition_met;
  logic id_early_branch_taken;
  logic [PC_WIDTH-1:0] id_early_branch_target;
  logic id_branch_resolved;
  logic [3:0] id_opcode;
  logic [3:0] id_rd;
  logic [3:0] id_rn;
  logic [3:0] id_rm;
  logic [15:0] id_imm;
  logic [31:0] id_rn_val;
  logic [31:0] id_rm_val;
  logic [31:0] id_rd_val;

  logic hazard_raw;
  logic hazard_stall_if;
  logic hazard_stall_id;
  logic hazard_bubble_ex;

  logic mem_wait_active;
  logic start_mem_wait;
  logic mem_wait_signal;
  logic mem_wait_served;
  logic [7:0] mem_wait_remaining;

  logic reconfig_request;
  pipesense_mode_e requested_mode;
  logic controller_reconfig_request;
  pipesense_mode_e controller_requested_mode;
  logic async03_reconfig_request;
  pipesense_mode_e async03_requested_mode;
  pipesense_mode_e reconfig_latched_mode;
  logic reconfig_active;
  logic reconfig_done;
  logic reconfig_stop_fetch;

  logic pipeline_empty;
  logic fetch_blocked_by_halt;
  logic can_fetch;
  logic branch_flush_event;
  logic [1:0] flush_slots;
  logic stall_if_event;
  logic stall_id_event;
  logic stall_ex_event;
  logic load_use_stall_event;
  logic instruction_retired;
  logic [3:0] activity_units;
  logic [3:0] active_slots;
  logic [31:0] ex_mem_forward_data;
  logic [31:0] fetch_tag;
  logic [31:0] if_id_tag;
  logic [31:0] id_ex_tag;
  logic [31:0] ex_mem_tag;
  logic [31:0] mem_wb_tag;
  logic [31:0] last_retired_tag;
  logic retire_seen;
  pipesense_phase_e observer_phase;
  pipesense_mode_e prev_current_mode;
  logic safety_history_valid;
  logic safety_bad_mode_change;
  logic safety_bad_reconfig_done;
  logic safety_bad_fetch_gate;
  logic safety_bad_duplicate_retire;
  logic [31:0] safety_fault_increment;

  simple_memory #(
    .ADDR_WIDTH(PC_WIDTH),
    .DATA_WIDTH(32),
    .WAIT_PERIOD(0)
  ) imem (
    .clk(clk),
    .read_en(1'b1),
    .write_en(program_write_active && !program_select_dmem),
    .wait_access(1'b0),
    .mitigate_wait(1'b1),
    .addr(imem_addr),
    .wdata(program_wdata),
    .rdata(imem_rdata),
    .wait_request()
  );

  simple_memory #(
    .ADDR_WIDTH(PC_WIDTH),
    .DATA_WIDTH(32),
    .WAIT_PERIOD(4)
  ) dmem (
    .clk(clk),
    .read_en(dmem_read_en),
    .write_en(dmem_write_en || (program_write_active && program_select_dmem)),
    .wait_access(ex_mem_valid && (ex_mem_mem_read || ex_mem_mem_write)),
    .mitigate_wait(current_mode == MODE_MEMORY_OPT),
    .addr(dmem_port_addr),
    .wdata((program_write_active && program_select_dmem) ? program_wdata : dmem_wdata),
    .rdata(dmem_rdata),
    .wait_request(dmem_wait_request)
  );

  hazard_unit hazard (
    .id_valid(if_id_valid),
    .id_instr(if_id_instr),
    .ex_valid(id_ex_valid),
    .ex_opcode(id_ex_opcode),
    .ex_rd(id_ex_rd),
    .hazard_opt_mode(current_mode == MODE_HAZARD_OPT),
    .load_use_hazard(hazard_raw),
    .stall_if(hazard_stall_if),
    .stall_id(hazard_stall_id),
    .bubble_ex(hazard_bubble_ex)
  );

  forwarding_unit fwd (
    .hazard_opt_mode(current_mode == MODE_HAZARD_OPT),
    .src_a(id_ex_rn),
    .src_b(id_ex_mem_write ? id_ex_rd : id_ex_rm),
    .reg_a(id_ex_rn_val),
    .reg_b(id_ex_mem_write ? id_ex_rd_val : id_ex_rm_val),
    .ex_mem_valid(ex_mem_valid),
    .ex_mem_reg_write(ex_mem_reg_write),
    .ex_mem_mem_read(ex_mem_mem_read),
    .ex_mem_rd(ex_mem_rd),
    .ex_mem_data(ex_mem_forward_data),
    .mem_wb_valid(mem_wb_valid),
    .mem_wb_reg_write(mem_wb_reg_write),
    .mem_wb_rd(mem_wb_rd),
    .mem_wb_data(mem_wb_data),
    .operand_a(ex_operand_a),
    .operand_b(ex_operand_b_raw)
  );

  pipeline_observer #(
    .WINDOW_SIZE(OBS_WINDOW),
    .BRANCH_THRESHOLD(OBS_BRANCH_THRESHOLD),
    .MEM_STALL_THRESHOLD(OBS_MEM_STALL_THRESHOLD),
    .LOAD_USE_THRESHOLD(OBS_LOAD_USE_THRESHOLD),
    .FRONTEND_STALL_THRESHOLD(OBS_FRONTEND_STALL_THRESHOLD),
    .IDLE_RETIRE_THRESHOLD(OBS_IDLE_RETIRE_THRESHOLD)
  ) observer (
    .clk(clk),
    .rst_n(rst_n),
    .if_valid(can_fetch),
    .id_valid(if_id_valid),
    .ex_valid(id_ex_valid),
    .mem_valid(ex_mem_valid),
    .wb_valid(mem_wb_valid),
    .stall_if(stall_if_event),
    .flush(branch_flush_event),
    .branch_taken(branch_flush_event),
    .load_use_hazard(hazard_raw),
    .mem_wait(mem_wait_signal),
    .instruction_retired(instruction_retired),
    .phase_estimate(observer_phase),
    .window_done()
  );

  assign observed_phase = (DISABLE_OBSERVER != 0) ?
                          PHASE_BALANCED : observer_phase;

  adaptive_controller #(
    .MIN_MODE_RESIDENCY(MIN_MODE_RESIDENCY),
    .PHASE_STABLE_COUNT(1)
  ) controller (
    .clk(clk),
    .rst_n(rst_n),
    .adaptive_enable(adaptive_enable),
    .phase_estimate(observed_phase),
    .current_mode(current_mode),
    .reconfig_ack(reconfig_done),
    .reconfig_active(reconfig_active),
    .reconfig_request(controller_reconfig_request),
    .requested_mode(controller_requested_mode)
  );

  async03_speculation_controller async03_controller (
    .clk(clk),
    .rst_n(rst_n),
    .adaptive_enable(adaptive_enable),
    .condition_setting_detected(if_id_valid && (id_opcode == OP_CMP) &&
                                !hazard_stall_id && !mem_wait_signal),
    .branch_detected(id_is_branch && !hazard_stall_id && !mem_wait_signal),
    .current_mode(current_mode),
    .reconfig_ack(reconfig_done),
    .reconfig_active(reconfig_active),
    .reconfig_request(async03_reconfig_request),
    .requested_mode(async03_requested_mode)
  );

  assign reconfig_request = (DISABLE_CONTROLLER != 0) ? 1'b0 :
                            ((CONTROLLER_POLICY == 1) ? async03_reconfig_request :
                                                       controller_reconfig_request);
  assign requested_mode = (DISABLE_CONTROLLER != 0) ? current_mode :
                          ((CONTROLLER_POLICY == 1) ? async03_requested_mode :
                                                     controller_requested_mode);

  reconfig_unit reconfig (
    .clk(clk),
    .rst_n(rst_n),
    .boot_mode(fixed_mode),
    .reconfig_request(reconfig_request),
    .requested_mode(requested_mode),
    .pipeline_empty(pipeline_empty),
    .mem_wait(mem_wait_signal),
    .current_mode(current_mode),
    .requested_mode_latched(reconfig_latched_mode),
    .reconfig_active(reconfig_active),
    .reconfig_done(reconfig_done),
    .stop_fetch(reconfig_stop_fetch)
  );

  perf_counters perf (
    .clk(clk),
    .rst_n(rst_n),
    .instruction_retired(instruction_retired),
    .stall_any(stall_if_event || stall_id_event || stall_ex_event),
    .flush_slots(flush_slots),
    .mem_wait(mem_wait_signal),
    .load_use_stall(load_use_stall_event),
    .reconfig_active(reconfig_active),
    .reconfig_done(reconfig_done),
    .activity_units(activity_units),
    .cycle_count(cycle_count),
    .retired_count(retired_count),
    .stall_cycles(stall_cycles),
    .flush_cycles(flush_cycles),
    .mem_wait_cycles(mem_wait_cycles),
    .load_use_stalls(load_use_stalls),
    .reconfigurations(reconfigurations),
    .reconfig_penalty(reconfig_penalty),
    .energy_proxy(energy_proxy)
  );

  assign id_opcode = if_id_instr[31:28];
  assign id_rd     = if_id_instr[27:24];
  assign id_rn     = if_id_instr[23:20];
  assign id_rm     = if_id_instr[19:16];
  assign id_imm    = if_id_instr[15:0];
  assign id_rn_val = (mem_wb_valid && mem_wb_reg_write && (mem_wb_rd != 4'd0) &&
                      (mem_wb_rd == id_rn)) ? mem_wb_data : regfile[id_rn];
  assign id_rm_val = (mem_wb_valid && mem_wb_reg_write && (mem_wb_rd != 4'd0) &&
                      (mem_wb_rd == id_rm)) ? mem_wb_data : regfile[id_rm];
  assign id_rd_val = (mem_wb_valid && mem_wb_reg_write && (mem_wb_rd != 4'd0) &&
                      (mem_wb_rd == id_rd)) ? mem_wb_data : regfile[id_rd];

  assign dmem_addr     = ex_mem_alu_result[PC_WIDTH-1:0];
  assign dmem_wdata    = ex_mem_store_data;
  assign program_write_active = program_write_en && !rst_n;
  assign imem_addr = (program_write_active && !program_select_dmem) ? program_addr : pc;
  assign dmem_port_addr = (program_write_active && program_select_dmem) ? program_addr : dmem_addr;
  assign dmem_read_en  = ex_mem_valid && (ex_mem_mem_read || ex_mem_mem_write);
  assign dmem_write_en = ex_mem_valid && ex_mem_mem_write && !mem_wait_signal;

  assign ex_mem_forward_data = ex_mem_mem_read ? dmem_rdata : ex_mem_alu_result;
  assign ex_operand_b = (id_ex_mem_read || id_ex_mem_write) ?
                        {{16{id_ex_imm[15]}}, id_ex_imm} :
                        ex_operand_b_raw;
  assign ex_store_data = ex_operand_b_raw;

  always_comb begin
    ex_alu_result = 32'b0;
    case (id_ex_opcode)
      OP_ADD: ex_alu_result = ex_operand_a + ex_operand_b;
      OP_SUB: ex_alu_result = ex_operand_a - ex_operand_b;
      OP_AND: ex_alu_result = ex_operand_a & ex_operand_b;
      OP_ORR: ex_alu_result = ex_operand_a | ex_operand_b;
      OP_EOR: ex_alu_result = ex_operand_a ^ ex_operand_b;
      OP_LDR: ex_alu_result = ex_operand_a + ex_operand_b;
      OP_STR: ex_alu_result = ex_operand_a + ex_operand_b;
      OP_CMP: ex_alu_result = ex_operand_a - ex_operand_b;
      default: ex_alu_result = 32'b0;
    endcase
  end

  assign ex_cmp_zero = (ex_alu_result == 32'b0);
  assign visible_zero_flag = (id_ex_valid && id_ex_cmp) ? ex_cmp_zero :
                             ((ex_mem_valid && ex_mem_cmp) ? ex_mem_cmp_zero : zero_flag);

  function automatic logic branch_condition(input logic [3:0] cond, input logic zflag);
    begin
      case (cond)
        COND_EQ: branch_condition = zflag;
        COND_NE: branch_condition = !zflag;
        default: branch_condition = 1'b1;
      endcase
    end
  endfunction

  assign ex_branch_taken = id_ex_valid &&
                           id_ex_branch &&
                           !id_ex_branch_resolved &&
                           branch_condition(id_ex_rd, visible_zero_flag);
  assign ex_branch_target = id_ex_imm[PC_WIDTH-1:0];

  assign id_is_branch = if_id_valid && (id_opcode == OP_B);
  assign id_branch_condition_met = branch_condition(id_rd, visible_zero_flag);
  assign id_early_branch_taken = (current_mode == MODE_BRANCH_OPT) &&
                                 id_is_branch &&
                                 id_branch_condition_met;
  assign id_early_branch_target = id_imm[PC_WIDTH-1:0];
  assign id_branch_resolved = (current_mode == MODE_BRANCH_OPT) && id_is_branch;

  assign mem_wait_active = (mem_wait_remaining != 8'd0);
  assign start_mem_wait = ex_mem_valid &&
                          (ex_mem_mem_read || ex_mem_mem_write) &&
                          !mem_wait_active &&
                          !mem_wait_served &&
                          dmem_wait_request;
  assign mem_wait_signal = mem_wait_active || start_mem_wait;

  assign fetch_blocked_by_halt = halted ||
                                 (if_id_valid && (id_opcode == OP_HALT)) ||
                                 (id_ex_valid && id_ex_halt) ||
                                 (ex_mem_valid && ex_mem_halt) ||
                                 (mem_wb_valid && mem_wb_halt);

  assign pipeline_empty = !if_id_valid && !id_ex_valid && !ex_mem_valid && !mem_wb_valid;
  assign can_fetch = !halted &&
                     !fetch_blocked_by_halt &&
                     !hazard_stall_if &&
                     !mem_wait_signal &&
                     !reconfig_stop_fetch;

  assign branch_flush_event = (ex_branch_taken && !mem_wait_signal) ||
                              (id_early_branch_taken && !hazard_stall_id && !mem_wait_signal);
  assign flush_slots = (ex_branch_taken && !mem_wait_signal) ? 2'd2 :
                       ((id_early_branch_taken && !hazard_stall_id && !mem_wait_signal) ? 2'd1 : 2'd0);
  assign stall_if_event = hazard_stall_if || mem_wait_signal || reconfig_stop_fetch || fetch_blocked_by_halt;
  assign stall_id_event = hazard_stall_id || mem_wait_signal;
  assign stall_ex_event = mem_wait_signal;
  assign load_use_stall_event = hazard_raw && (current_mode != MODE_HAZARD_OPT);
  assign instruction_retired = mem_wb_valid &&
                               (mem_wb_opcode != OP_NOP) &&
                               (mem_wb_opcode != OP_HALT);
  assign safety_bad_mode_change = safety_history_valid &&
                                  (current_mode != prev_current_mode) &&
                                  !(pipeline_empty && !mem_wait_signal);
  assign safety_bad_reconfig_done = reconfig_done &&
                                    !(pipeline_empty && !mem_wait_signal);
  assign safety_bad_fetch_gate = reconfig_active && !reconfig_stop_fetch;
  assign safety_bad_duplicate_retire = instruction_retired &&
                                       retire_seen &&
                                       (mem_wb_tag <= last_retired_tag);
  assign safety_fault_increment =
      {31'b0, safety_bad_mode_change} +
      {31'b0, safety_bad_reconfig_done} +
      {31'b0, safety_bad_fetch_gate} +
      {31'b0, safety_bad_duplicate_retire};

  always_comb begin
    active_slots = {3'b000, can_fetch} +
                   {3'b000, if_id_valid} +
                   {3'b000, id_ex_valid} +
                   {3'b000, ex_mem_valid} +
                   {3'b000, mem_wb_valid};
    if (current_mode == MODE_LOW_POWER) begin
      activity_units = active_slots;
    end else begin
      activity_units = active_slots + 4'd2;
    end
  end

  task automatic clear_all();
    int i;
    begin
      imem.clear();
      dmem.clear();
      for (i = 0; i < REG_COUNT; i++) begin
        regfile[i] = '0;
      end
    end
  endtask

  task automatic load_instr(input int unsigned addr, input logic [31:0] instr);
    begin
      imem.write_word(addr, instr);
    end
  endtask

  task automatic load_data(input int unsigned addr, input logic [31:0] data);
    begin
      dmem.write_word(addr, data);
    end
  endtask

  task automatic set_reg(input int unsigned reg_index, input logic [31:0] value);
    begin
      if (reg_index < REG_COUNT) begin
        regfile[reg_index] = value;
      end
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    int i;
    if (!rst_n) begin
      pc                         <= '0;
      zero_flag                  <= 1'b0;
      halted                     <= 1'b0;
      if_id_valid                <= 1'b0;
      if_id_instr                <= 32'b0;
      if_id_pc                   <= '0;
      id_ex_valid                <= 1'b0;
      id_ex_instr                <= 32'b0;
      id_ex_pc                   <= '0;
      id_ex_opcode               <= OP_NOP;
      id_ex_rd                   <= 4'd0;
      id_ex_rn                   <= 4'd0;
      id_ex_rm                   <= 4'd0;
      id_ex_imm                  <= 16'd0;
      id_ex_rn_val               <= 32'b0;
      id_ex_rm_val               <= 32'b0;
      id_ex_rd_val               <= 32'b0;
      id_ex_reg_write            <= 1'b0;
      id_ex_mem_read             <= 1'b0;
      id_ex_mem_write            <= 1'b0;
      id_ex_branch               <= 1'b0;
      id_ex_cmp                  <= 1'b0;
      id_ex_halt                 <= 1'b0;
      id_ex_branch_resolved      <= 1'b0;
      id_ex_early_branch_taken   <= 1'b0;
      id_ex_early_branch_target  <= '0;
      ex_mem_valid               <= 1'b0;
      ex_mem_opcode              <= OP_NOP;
      ex_mem_rd                  <= 4'd0;
      ex_mem_alu_result          <= 32'b0;
      ex_mem_store_data          <= 32'b0;
      ex_mem_reg_write           <= 1'b0;
      ex_mem_mem_read            <= 1'b0;
      ex_mem_mem_write           <= 1'b0;
      ex_mem_branch_taken        <= 1'b0;
      ex_mem_branch_target       <= '0;
      ex_mem_cmp                 <= 1'b0;
      ex_mem_cmp_zero            <= 1'b0;
      ex_mem_halt                <= 1'b0;
      mem_wb_valid               <= 1'b0;
      mem_wb_opcode              <= OP_NOP;
      mem_wb_rd                  <= 4'd0;
      mem_wb_data                <= 32'b0;
      mem_wb_reg_write           <= 1'b0;
      mem_wb_halt                <= 1'b0;
      mem_wait_remaining         <= 8'd0;
      mem_wait_served            <= 1'b0;
      fetch_tag                  <= 32'd1;
      if_id_tag                  <= 32'd0;
      id_ex_tag                  <= 32'd0;
      ex_mem_tag                 <= 32'd0;
      mem_wb_tag                 <= 32'd0;
      last_retired_tag           <= 32'd0;
      retire_seen                <= 1'b0;
      prev_current_mode          <= MODE_NORMAL;
      safety_history_valid       <= 1'b0;
      safety_faults              <= 32'd0;

      for (i = 0; i < REG_COUNT; i++) begin
        regfile[i] <= 32'b0;
      end
    end else begin
      regfile[0] <= 32'b0;
      prev_current_mode <= current_mode;
      safety_history_valid <= 1'b1;
      safety_faults <= safety_faults + safety_fault_increment;

      if (mem_wb_valid && mem_wb_reg_write && (mem_wb_rd != 4'd0)) begin
        regfile[mem_wb_rd] <= mem_wb_data;
      end

      if (instruction_retired) begin
        last_retired_tag <= mem_wb_tag;
        retire_seen      <= 1'b1;
      end

      if (mem_wb_valid && mem_wb_halt) begin
        halted <= 1'b1;
      end

      if (id_ex_valid && id_ex_cmp && !mem_wait_signal) begin
        zero_flag <= ex_cmp_zero;
      end

      if (mem_wait_active) begin
        mem_wait_remaining <= mem_wait_remaining - 1'b1;
      end else if (start_mem_wait) begin
        mem_wait_remaining <= (DATA_WAIT_CYCLES == 0) ? 8'd0 : (DATA_WAIT_CYCLES - 1);
        mem_wait_served    <= 1'b1;
      end else if (!mem_wait_signal && ex_mem_valid && (ex_mem_mem_read || ex_mem_mem_write)) begin
        mem_wait_served <= 1'b0;
      end

      if (mem_wait_signal) begin
        mem_wb_valid     <= 1'b0;
        mem_wb_opcode    <= OP_NOP;
        mem_wb_rd        <= 4'd0;
        mem_wb_data      <= 32'b0;
        mem_wb_reg_write <= 1'b0;
        mem_wb_halt      <= 1'b0;
        mem_wb_tag       <= 32'd0;

        if (id_ex_valid) begin
          id_ex_rn_val <= ex_operand_a;
          if (id_ex_mem_write) begin
            id_ex_rd_val <= ex_operand_b_raw;
          end else begin
            id_ex_rm_val <= ex_operand_b_raw;
          end
        end
      end else begin
        mem_wb_valid     <= ex_mem_valid;
        mem_wb_opcode    <= ex_mem_opcode;
        mem_wb_rd        <= ex_mem_rd;
        mem_wb_data      <= ex_mem_mem_read ? dmem_rdata : ex_mem_alu_result;
        mem_wb_reg_write <= ex_mem_reg_write;
        mem_wb_halt      <= ex_mem_halt;
        mem_wb_tag       <= ex_mem_tag;

        ex_mem_valid         <= id_ex_valid;
        ex_mem_opcode        <= id_ex_opcode;
        ex_mem_rd            <= id_ex_rd;
        ex_mem_alu_result    <= ex_alu_result;
        ex_mem_store_data    <= ex_store_data;
        ex_mem_reg_write     <= id_ex_reg_write;
        ex_mem_mem_read      <= id_ex_mem_read;
        ex_mem_mem_write     <= id_ex_mem_write;
        ex_mem_branch_taken  <= ex_branch_taken || id_ex_early_branch_taken;
        ex_mem_branch_target <= id_ex_early_branch_taken ? id_ex_early_branch_target : ex_branch_target;
        ex_mem_cmp           <= id_ex_cmp;
        ex_mem_cmp_zero      <= ex_cmp_zero;
        ex_mem_halt          <= id_ex_halt;
        ex_mem_tag           <= id_ex_tag;

        if (ex_branch_taken) begin
          id_ex_valid <= 1'b0;
          id_ex_tag   <= 32'd0;
        end else if (hazard_bubble_ex) begin
          id_ex_valid <= 1'b0;
          id_ex_tag   <= 32'd0;
        end else begin
          id_ex_valid               <= if_id_valid;
          id_ex_instr               <= if_id_instr;
          id_ex_pc                  <= if_id_pc;
          id_ex_opcode              <= id_opcode;
          id_ex_rd                  <= id_rd;
          id_ex_rn                  <= id_rn;
          id_ex_rm                  <= id_rm;
          id_ex_imm                 <= id_imm;
          id_ex_rn_val              <= id_rn_val;
          id_ex_rm_val              <= id_rm_val;
          id_ex_rd_val              <= id_rd_val;
          id_ex_reg_write           <= (id_opcode == OP_ADD) || (id_opcode == OP_SUB) ||
                                       (id_opcode == OP_AND) || (id_opcode == OP_ORR) ||
                                       (id_opcode == OP_EOR) || (id_opcode == OP_LDR);
          id_ex_mem_read            <= (id_opcode == OP_LDR);
          id_ex_mem_write           <= (id_opcode == OP_STR);
          id_ex_branch              <= (id_opcode == OP_B);
          id_ex_cmp                 <= (id_opcode == OP_CMP);
          id_ex_halt                <= (id_opcode == OP_HALT);
          id_ex_branch_resolved     <= id_branch_resolved;
          id_ex_early_branch_taken  <= id_early_branch_taken;
          id_ex_early_branch_target <= id_early_branch_target;
          id_ex_tag                 <= if_id_tag;
        end

        if (ex_branch_taken || id_early_branch_taken) begin
          if_id_valid <= 1'b0;
          if_id_instr <= 32'b0;
          if_id_pc    <= '0;
          if_id_tag   <= 32'd0;
        end else if (!hazard_stall_id) begin
          if_id_valid <= can_fetch;
          if_id_instr <= can_fetch ? imem_rdata : 32'b0;
          if_id_pc    <= pc;
          if_id_tag   <= can_fetch ? fetch_tag : 32'd0;
        end

        if (ex_branch_taken) begin
          pc <= ex_branch_target;
        end else if (id_early_branch_taken) begin
          pc <= id_early_branch_target;
        end else if (can_fetch) begin
          pc <= pc + 1'b1;
          fetch_tag <= fetch_tag + 1'b1;
        end
      end
    end
  end

`ifndef SYNTHESIS
  always @(posedge clk) begin
    if (rst_n) begin
      if (safety_bad_mode_change) begin
        $error("SAFETY: mode changed outside an empty-pipeline boundary");
      end
      if (safety_bad_reconfig_done) begin
        $error("SAFETY: reconfiguration acknowledged before drain completed");
      end
      if (safety_bad_fetch_gate) begin
        $error("SAFETY: fetch was not gated during active reconfiguration");
      end
      if (safety_bad_duplicate_retire) begin
        $error("SAFETY: retired instruction tag duplicated or moved backward");
      end
    end
  end
`endif
endmodule
