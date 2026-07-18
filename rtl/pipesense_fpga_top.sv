`include "defines.svh"

// Synthesizable FPGA boundary for the complete core. Program words are loaded
// while rst_n is low; debug_select retains every performance counter through a
// compact output mux instead of exposing hundreds of top-level pins.
module pipesense_fpga_top (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             adaptive_enable,
  input  pipesense_mode_e  fixed_mode,
  input  logic             program_write_en,
  input  logic             program_select_dmem,
  input  logic [7:0]       program_addr,
  input  logic [31:0]      program_wdata,
  input  logic [3:0]       debug_select,
  output logic [31:0]      debug_data,
  output pipesense_mode_e  current_mode,
  output pipesense_phase_e observed_phase,
  output logic             halted
);
  logic [31:0] cycle_count;
  logic [31:0] retired_count;
  logic [31:0] stall_cycles;
  logic [31:0] flush_cycles;
  logic [31:0] mem_wait_cycles;
  logic [31:0] load_use_stalls;
  logic [31:0] reconfigurations;
  logic [31:0] reconfig_penalty;
  logic [31:0] energy_proxy;
  logic [31:0] safety_faults;

  arm_like_core core (
    .clk(clk),
    .rst_n(rst_n),
    .adaptive_enable(adaptive_enable),
    .fixed_mode(fixed_mode),
    .program_write_en(program_write_en),
    .program_select_dmem(program_select_dmem),
    .program_addr(program_addr),
    .program_wdata(program_wdata),
    .current_mode(current_mode),
    .observed_phase(observed_phase),
    .halted(halted),
    .cycle_count(cycle_count),
    .retired_count(retired_count),
    .stall_cycles(stall_cycles),
    .flush_cycles(flush_cycles),
    .mem_wait_cycles(mem_wait_cycles),
    .load_use_stalls(load_use_stalls),
    .reconfigurations(reconfigurations),
    .reconfig_penalty(reconfig_penalty),
    .energy_proxy(energy_proxy),
    .safety_faults(safety_faults)
  );

  always_comb begin
    case (debug_select)
      4'd0: debug_data = cycle_count;
      4'd1: debug_data = retired_count;
      4'd2: debug_data = stall_cycles;
      4'd3: debug_data = flush_cycles;
      4'd4: debug_data = mem_wait_cycles;
      4'd5: debug_data = load_use_stalls;
      4'd6: debug_data = reconfigurations;
      4'd7: debug_data = reconfig_penalty;
      4'd8: debug_data = energy_proxy;
      4'd9: debug_data = safety_faults;
      default: debug_data = 32'b0;
    endcase
  end
endmodule
