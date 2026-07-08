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
  reg [2:0] last_desired_mode;
  reg [2:0] desired_mode;
  reg [7:0] required_residency;
  reg [1:0] required_stability;

  always @* begin
    case (phase_estimate)
      3'd1: desired_mode = 3'd1;
      3'd2: desired_mode = 3'd2;
      3'd3: desired_mode = 3'd3;
      3'd4: desired_mode = (current_mode == 3'd2) ? 3'd2 : 3'd1;
      3'd5: desired_mode = 3'd4;
      default: desired_mode = current_mode;
    endcase
  end

  always @* begin
    case (desired_mode)
      3'd1: begin
        required_residency = 8'd12;
        required_stability = 2'd3;
      end
      3'd2: begin
        required_residency = 8'd8;
        required_stability = 2'd0;
      end
      3'd3: begin
        required_residency = 8'd12;
        required_stability = 2'd1;
      end
      3'd4: begin
        required_residency = 8'd48;
        required_stability = 2'd3;
      end
      default: begin
        required_residency = 8'd48;
        required_stability = 2'd3;
      end
    endcase
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      residency_counter <= 8'd0;
      stable_counter <= 2'd0;
      last_desired_mode <= 3'd0;
      requested_mode <= 3'd0;
      reconfig_request <= 1'b0;
    end else begin
      if (residency_counter != 8'hff) residency_counter <= residency_counter + 8'd1;
      if (desired_mode == last_desired_mode) begin
        if (stable_counter != 2'd3) stable_counter <= stable_counter + 2'd1;
      end else begin
        stable_counter <= 2'd0;
        last_desired_mode <= desired_mode;
      end
      if (reconfig_ack) begin
        residency_counter <= 8'd0;
        reconfig_request <= 1'b0;
      end else if (adaptive_enable && !reconfig_active && !reconfig_request &&
                   desired_mode != current_mode &&
                   residency_counter >= required_residency &&
                   stable_counter >= required_stability) begin
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

module pipesense_integrated_core (
  input clk,
  input rst_n,
  input adaptive_enable,
  input [31:0] instr_in,
  input [31:0] mem_in,
  input [7:0] events,
  input stall,
  input flush,
  input pipeline_empty,
  input mem_wait,
  input instruction_retired,
  output [31:0] state_hash
);
  wire [31:0] core_hash;
  wire [2:0] phase_estimate;
  wire [31:0] observer_sum;
  wire reconfig_request;
  wire [2:0] requested_mode;
  wire [2:0] current_mode;
  wire [2:0] requested_mode_latched;
  wire reconfig_active;
  wire reconfig_done;
  wire stop_fetch;
  wire [31:0] reconfig_stall_cycles;
  wire [31:0] total_reconfigurations;
  wire [31:0] total_reconfig_penalty;

  arm_like_core core (
    .clk(clk),
    .rst_n(rst_n),
    .instr_in(instr_in),
    .mem_in(mem_in),
    .stall(stall | stop_fetch),
    .flush(flush),
    .state_hash(core_hash)
  );

  pipeline_observer observer (
    .clk(clk),
    .rst_n(rst_n),
    .events(events),
    .instruction_retired(instruction_retired),
    .phase_estimate(phase_estimate),
    .observer_sum(observer_sum)
  );

  adaptive_controller controller (
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
    .stop_fetch(stop_fetch),
    .reconfig_stall_cycles(reconfig_stall_cycles),
    .total_reconfigurations(total_reconfigurations),
    .total_reconfig_penalty(total_reconfig_penalty)
  );

  assign state_hash = core_hash ^ observer_sum ^
                      {29'd0, current_mode} ^
                      {29'd0, requested_mode_latched} ^
                      reconfig_stall_cycles ^
                      total_reconfigurations ^
                      total_reconfig_penalty;
endmodule
