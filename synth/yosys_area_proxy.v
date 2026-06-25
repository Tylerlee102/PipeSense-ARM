// Yosys-compatible generic area proxy for PipeSense-ARM.
//
// This file is not the executable research RTL. It mirrors the major state and
// comparator/addition structures used by the core, observer, controller, and
// reconfiguration unit so CI can produce a stable generic-cell proxy with
// open-source Yosys.

module arm_like_core (
  input clk,
  input rst_n,
  input [31:0] instr_in,
  input [31:0] mem_in,
  input stall,
  input flush,
  output [31:0] state_hash
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
  wire is_mem = opcode == 4'h6 || opcode == 4'h7;
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
endmodule

module pipeline_observer (
  input clk,
  input rst_n,
  input [7:0] events,
  input instruction_retired,
  output reg [2:0] phase_estimate,
  output [31:0] observer_sum
);
  reg [5:0] window_cycle;
  reg [31:0] branch_count;
  reg [31:0] mem_wait_count;
  reg [31:0] load_use_count;
  reg [31:0] frontend_count;
  reg [31:0] retire_count;
  wire window_done = window_cycle == 6'd63;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      window_cycle <= 6'd0;
      branch_count <= 32'd0;
      mem_wait_count <= 32'd0;
      load_use_count <= 32'd0;
      frontend_count <= 32'd0;
      retire_count <= 32'd0;
      phase_estimate <= 3'd0;
    end else begin
      window_cycle <= window_done ? 6'd0 : window_cycle + 6'd1;
      branch_count <= window_done ? 32'd0 : branch_count + events[0];
      mem_wait_count <= window_done ? 32'd0 : mem_wait_count + events[1];
      load_use_count <= window_done ? 32'd0 : load_use_count + events[2];
      frontend_count <= window_done ? 32'd0 : frontend_count + events[3];
      retire_count <= window_done ? 32'd0 : retire_count + instruction_retired;
      if (window_done) begin
        if (mem_wait_count >= 32'd8) phase_estimate <= 3'd2;
        else if (load_use_count >= 32'd6) phase_estimate <= 3'd3;
        else if (branch_count >= 32'd8) phase_estimate <= 3'd1;
        else if (frontend_count >= 32'd10) phase_estimate <= 3'd4;
        else if (retire_count <= 32'd8) phase_estimate <= 3'd5;
        else phase_estimate <= 3'd0;
      end
    end
  end

  assign observer_sum = branch_count + mem_wait_count + load_use_count +
                        frontend_count + retire_count + {26'd0, window_cycle};
endmodule

module adaptive_controller (
  input clk,
  input rst_n,
  input adaptive_enable,
  input [2:0] phase_estimate,
  input [2:0] current_mode,
  input reconfig_ack,
  input reconfig_active,
  output reg reconfig_request,
  output reg [2:0] requested_mode
);
  reg [7:0] residency_counter;
  reg [1:0] stable_counter;
  reg [2:0] last_phase;
  reg [2:0] desired_mode;

  always @* begin
    case (phase_estimate)
      3'd1: desired_mode = 3'd1;
      3'd2: desired_mode = 3'd2;
      3'd3: desired_mode = 3'd3;
      3'd4: desired_mode = 3'd1;
      3'd5: desired_mode = 3'd4;
      default: desired_mode = 3'd0;
    endcase
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      residency_counter <= 8'd0;
      stable_counter <= 2'd0;
      last_phase <= 3'd0;
      requested_mode <= 3'd0;
      reconfig_request <= 1'b0;
    end else begin
      residency_counter <= residency_counter + 8'd1;
      stable_counter <= (phase_estimate == last_phase) ? stable_counter + 2'd1 : 2'd0;
      last_phase <= phase_estimate;
      if (reconfig_ack) begin
        residency_counter <= 8'd0;
        reconfig_request <= 1'b0;
      end else if (adaptive_enable && !reconfig_active && !reconfig_request &&
                   desired_mode != current_mode && residency_counter >= 8'd24 &&
                   stable_counter >= 2'd1) begin
        requested_mode <= desired_mode;
        reconfig_request <= 1'b1;
      end
    end
  end
endmodule

module reconfig_unit (
  input clk,
  input rst_n,
  input [2:0] boot_mode,
  input reconfig_request,
  input [2:0] requested_mode,
  input pipeline_empty,
  input mem_wait,
  output reg [2:0] current_mode,
  output reg [2:0] requested_mode_latched,
  output reg reconfig_active,
  output reg reconfig_done,
  output stop_fetch,
  output [31:0] reconfig_stall_cycles,
  output reg [31:0] total_reconfigurations,
  output reg [31:0] total_reconfig_penalty
);
  reg [31:0] active_counter;
  wire start_reconfig = reconfig_request && !reconfig_active &&
                        requested_mode != current_mode;
  assign stop_fetch = reconfig_active || start_reconfig;
  assign reconfig_stall_cycles = active_counter;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      current_mode <= boot_mode;
      requested_mode_latched <= boot_mode;
      reconfig_active <= 1'b0;
      reconfig_done <= 1'b0;
      active_counter <= 32'd0;
      total_reconfigurations <= 32'd0;
      total_reconfig_penalty <= 32'd0;
    end else begin
      reconfig_done <= 1'b0;
      if (start_reconfig) begin
        requested_mode_latched <= requested_mode;
        reconfig_active <= 1'b1;
        active_counter <= 32'd0;
      end else if (reconfig_active) begin
        active_counter <= active_counter + 32'd1;
        if (pipeline_empty && !mem_wait) begin
          current_mode <= requested_mode_latched;
          reconfig_active <= 1'b0;
          reconfig_done <= 1'b1;
          total_reconfigurations <= total_reconfigurations + 32'd1;
          total_reconfig_penalty <= total_reconfig_penalty + active_counter;
        end
      end
    end
  end
endmodule
