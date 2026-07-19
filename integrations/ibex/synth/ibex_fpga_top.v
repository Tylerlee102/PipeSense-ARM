// SPDX-License-Identifier: Apache-2.0
// Physical-implementation harness for the complete Ibex core interface.
module pipesense_ibex_fpga_top (
  input  wire clk_i,
  input  wire rst_ni,
  output wire activity_o
);
  reg [63:0] stimulus_q;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni)
      stimulus_q <= 64'h1;
    else
      stimulus_q <= {stimulus_q[62:0], stimulus_q[63] ^ stimulus_q[62] ^
                     stimulus_q[60] ^ stimulus_q[59]};
  end

  wire [1:0] ram_cfg_icache_tag_o;
  wire [1:0] ram_cfg_icache_data_o;
  wire instr_req_o;
  wire [31:0] instr_addr_o;
  wire data_req_o;
  wire data_we_o;
  wire [3:0] data_be_o;
  wire [31:0] data_addr_o;
  wire [31:0] data_wdata_o;
  wire [6:0] data_wdata_intg_o;
  wire scramble_req_o;
  wire [159:0] crash_dump_o;
  wire double_fault_seen_o;
  wire alert_minor_o;
  wire alert_major_internal_o;
  wire alert_major_bus_o;
  wire core_sleep_o;
  wire [3:0] lockstep_cmp_en_o;
  wire data_req_shadow_o;
  wire data_we_shadow_o;
  wire [3:0] data_be_shadow_o;
  wire [31:0] data_addr_shadow_o;
  wire [31:0] data_wdata_shadow_o;
  wire [6:0] data_wdata_intg_shadow_o;
  wire instr_req_shadow_o;
  wire [31:0] instr_addr_shadow_o;

  ibex_top #(
    .BranchTargetALU(1'b1),
    .WritebackStage(1'b1)
  ) u_ibex_top (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .test_en_i(1'b0),
    .ram_cfg_icache_tag_i(24'b0),
    .ram_cfg_icache_tag_o(ram_cfg_icache_tag_o),
    .ram_cfg_icache_data_i(24'b0),
    .ram_cfg_icache_data_o(ram_cfg_icache_data_o),
    .hart_id_i(32'b0),
    .boot_addr_i(32'h00100000),
    .instr_req_o(instr_req_o),
    .instr_gnt_i(stimulus_q[0]),
    .instr_rvalid_i(stimulus_q[1]),
    .instr_addr_o(instr_addr_o),
    .instr_rdata_i(stimulus_q[33:2]),
    .instr_rdata_intg_i(7'b0),
    .instr_err_i(1'b0),
    .data_req_o(data_req_o),
    .data_gnt_i(stimulus_q[34]),
    .data_rvalid_i(stimulus_q[35]),
    .data_we_o(data_we_o),
    .data_be_o(data_be_o),
    .data_addr_o(data_addr_o),
    .data_wdata_o(data_wdata_o),
    .data_wdata_intg_o(data_wdata_intg_o),
    .data_rdata_i(stimulus_q[63:32]),
    .data_rdata_intg_i(7'b0),
    .data_err_i(1'b0),
    .irq_software_i(stimulus_q[36]),
    .irq_timer_i(stimulus_q[37]),
    .irq_external_i(stimulus_q[38]),
    .irq_fast_i(stimulus_q[53:39]),
    .irq_nm_i(1'b0),
    .scramble_key_valid_i(1'b0),
    .scramble_key_i({2{stimulus_q}}),
    .scramble_nonce_i(stimulus_q),
    .scramble_req_o(scramble_req_o),
    .debug_req_i(1'b0),
    .crash_dump_o(crash_dump_o),
    .double_fault_seen_o(double_fault_seen_o),
    .fetch_enable_i(4'h5),
    .mcounteren_writable_i(4'h5),
    .alert_minor_o(alert_minor_o),
    .alert_major_internal_o(alert_major_internal_o),
    .alert_major_bus_o(alert_major_bus_o),
    .core_sleep_o(core_sleep_o),
    .scan_rst_ni(rst_ni),
    .lockstep_cmp_en_o(lockstep_cmp_en_o),
    .data_req_shadow_o(data_req_shadow_o),
    .data_we_shadow_o(data_we_shadow_o),
    .data_be_shadow_o(data_be_shadow_o),
    .data_addr_shadow_o(data_addr_shadow_o),
    .data_wdata_shadow_o(data_wdata_shadow_o),
    .data_wdata_intg_shadow_o(data_wdata_intg_shadow_o),
    .instr_req_shadow_o(instr_req_shadow_o),
    .instr_addr_shadow_o(instr_addr_shadow_o)
  );

  assign activity_o = instr_req_o ^ ^instr_addr_o ^ data_req_o ^ data_we_o ^
      ^data_be_o ^ ^data_addr_o ^ ^data_wdata_o ^ core_sleep_o ^
      alert_minor_o ^ alert_major_internal_o ^ alert_major_bus_o;
endmodule
