function automatic logic [31:0] enc_r(
  input logic [3:0] opcode,
  input logic [3:0] rd,
  input logic [3:0] rn,
  input logic [3:0] rm
);
  begin
    enc_r = {opcode, rd, rn, rm, 16'h0000};
  end
endfunction

function automatic logic [31:0] enc_i(
  input logic [3:0] opcode,
  input logic [3:0] rd,
  input logic [3:0] rn,
  input logic [15:0] imm
);
  begin
    enc_i = {opcode, rd, rn, 4'h0, imm};
  end
endfunction

function automatic logic [31:0] enc_b(
  input logic [3:0] cond,
  input logic [15:0] target
);
  begin
    enc_b = {OP_B, cond, 4'h0, 4'h0, target};
  end
endfunction

function automatic logic [31:0] enc_halt();
  begin
    enc_halt = {OP_HALT, 28'd0};
  end
endfunction

task automatic load_arithmetic_heavy(output int max_cycles);
  int p;
  begin
    max_cycles = 600;
    p = 0;
    dut.load_data(1, 32'd21);
    dut.load_data(2, 32'd9);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd1));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd3, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd4, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd5, 4'd3, 4'd4));
    p++;
    dut.load_instr(p, enc_r(OP_ORR, 4'd6, 4'd5, 4'd1));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd7, 4'd6, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd8, 4'd7, 4'd3));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd9, 4'd8, 4'd4));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd10, 4'd9, 4'd5));
    p++;
    dut.load_instr(p, enc_r(OP_ORR, 4'd11, 4'd10, 4'd6));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd12, 4'd11, 4'd7));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd13, 4'd12, 4'd8));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd14, 4'd13, 4'd9));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd15, 4'd14, 4'd10));
    p++;
    dut.load_instr(p, enc_r(OP_ORR, 4'd3, 4'd15, 4'd11));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd4, 4'd3, 4'd12));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd5, 4'd4, 4'd13));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd6, 4'd5, 4'd14));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd7, 4'd6, 4'd15));
    p++;
    dut.load_instr(p, enc_r(OP_ORR, 4'd8, 4'd7, 4'd1));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd9, 4'd8, 4'd2));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_branch_heavy(output int max_cycles);
  int p;
  begin
    max_cycles = 900;
    p = 0;
    dut.load_data(20, 32'd24);
    dut.load_data(21, 32'd1);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd20));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd21));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd2));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_memory_heavy(output int max_cycles);
  int p;
  begin
    max_cycles = 1200;
    p = 0;
    dut.load_data(80, 32'd14);
    dut.load_data(81, 32'd1);
    dut.load_data(83, 32'd100);
    dut.load_data(87, 32'd7);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd80));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd81));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd83));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd87));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd5, 4'd3, 4'd4));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd5, 4'd0, 16'd91));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd2));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_load_use_heavy(output int max_cycles);
  int p;
  begin
    max_cycles = 1000;
    p = 0;
    dut.load_data(100, 32'd18);
    dut.load_data(101, 32'd1);
    dut.load_data(104, 32'd11);
    dut.load_data(105, 32'd13);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd100));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd101));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd104));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd4, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd0, 16'd105));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd5, 4'd4));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd2));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_mixed_control(output int max_cycles);
  int p;
  begin
    max_cycles = 1100;
    p = 0;
    dut.load_data(120, 32'd12);
    dut.load_data(121, 32'd1);
    dut.load_data(122, 32'd5);
    dut.load_data(123, 32'h000000ff);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd120));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd121));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd122));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd123));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd5, 4'd5, 4'd3));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd6, 4'd5, 4'd4));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd6, 4'd0, 16'd127));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd4));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_tiny_fir(output int max_cycles);
  int p;
  begin
    max_cycles = 900;
    p = 0;
    dut.load_data(140, 32'd8);
    dut.load_data(141, 32'd1);
    dut.load_data(144, 32'd3);
    dut.load_data(145, 32'd5);
    dut.load_data(146, 32'd8);
    dut.load_data(147, 32'd13);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd140));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd141));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd144));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd145));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd7, 4'd3, 4'd4));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd0, 16'd146));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd6, 4'd0, 16'd147));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd8, 4'd5, 4'd6));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd9, 4'd7, 4'd8));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd9, 4'd0, 16'd151));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd2));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_dhrystone_toy(output int max_cycles);
  int p;
  begin
    max_cycles = 1400;
    p = 0;
    dut.load_data(160, 32'd10);
    dut.load_data(161, 32'd1);
    dut.load_data(162, 32'd3);
    dut.load_data(163, 32'd5);
    dut.load_data(164, 32'h00ff00ff);
    dut.load_data(165, 32'h0f0f0f0f);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd160));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd161));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd162));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd163));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd10, 4'd0, 16'd164));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd11, 4'd0, 16'd165));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd5, 4'd3, 4'd4));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd6, 4'd5, 4'd10));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd7, 4'd6, 4'd11));
    p++;
    dut.load_instr(p, enc_r(OP_ORR, 4'd8, 4'd7, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd3, 4'd8, 4'd4));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd4, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd4, 4'd0, 16'd170));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd6));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_coremark_toy(output int max_cycles);
  int p;
  begin
    max_cycles = 1600;
    p = 0;
    dut.load_data(180, 32'd12);
    dut.load_data(181, 32'd1);
    dut.load_data(182, 32'd200);
    dut.load_data(183, 32'h0000ace1);
    dut.load_data(200, 32'd37);
    dut.load_data(201, 32'd19);
    dut.load_data(202, 32'd91);
    dut.load_data(203, 32'd44);
    dut.load_data(204, 32'd12);
    dut.load_data(205, 32'd73);
    dut.load_data(206, 32'd5);
    dut.load_data(207, 32'd128);
    dut.load_data(208, 32'd64);
    dut.load_data(209, 32'd23);
    dut.load_data(210, 32'd17);
    dut.load_data(211, 32'd99);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd180));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd181));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd182));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd183));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd3, 16'd0));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd5, 4'd4));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd4, 4'd6, 4'd1));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd7, 4'd4, 4'd5));
    p++;
    dut.load_instr(p, enc_r(OP_ORR, 4'd4, 4'd4, 4'd7));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd3, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd4));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd4, 4'd0, 16'd220));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_dsp_fir_codegen(output int max_cycles);
  int p;
  begin
    max_cycles = 1800;
    p = 0;
    dut.load_data(190, 32'd8);
    dut.load_data(191, 32'd1);
    dut.load_data(192, 32'd200);
    dut.load_data(193, 32'd220);
    dut.load_data(194, 32'h000000ff);
    dut.load_data(200, 32'd3);
    dut.load_data(201, 32'd5);
    dut.load_data(202, 32'd8);
    dut.load_data(203, 32'd13);
    dut.load_data(204, 32'd21);
    dut.load_data(205, 32'd34);
    dut.load_data(206, 32'd55);
    dut.load_data(207, 32'd89);
    dut.load_data(208, 32'd144);
    dut.load_data(209, 32'd233);
    dut.load_data(210, 32'd377);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd190));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd191));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd192));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd11, 4'd0, 16'd193));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd10, 4'd0, 16'd194));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd3, 16'd0));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd3, 16'd1));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd4, 4'd5));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd7, 4'd3, 16'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd6, 4'd7));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd8, 4'd3, 16'd3));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd6, 4'd8));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd9, 4'd6, 4'd10));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd9, 4'd9, 4'd6));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd9, 4'd11, 16'd0));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd3, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd11, 4'd11, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd5));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_pid_control_codegen(output int max_cycles);
  int p;
  begin
    max_cycles = 1800;
    p = 0;
    dut.load_data(56, 32'd12);
    dut.load_data(57, 32'd1);
    dut.load_data(58, 32'd100);
    dut.load_data(59, 32'd64);
    dut.load_data(60, 32'h000000ff);
    dut.load_data(64, 32'd93);
    dut.load_data(65, 32'd97);
    dut.load_data(66, 32'd104);
    dut.load_data(67, 32'd99);
    dut.load_data(68, 32'd88);
    dut.load_data(69, 32'd101);
    dut.load_data(70, 32'd109);
    dut.load_data(71, 32'd95);
    dut.load_data(72, 32'd98);
    dut.load_data(73, 32'd106);
    dut.load_data(74, 32'd91);
    dut.load_data(75, 32'd100);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd56));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd57));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd58));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd59));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd10, 4'd0, 16'd60));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd4, 16'd0));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd6, 4'd3, 4'd5));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd7, 4'd7, 4'd6));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd8, 4'd6, 4'd7));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd8, 4'd8, 4'd10));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd8, 4'd8, 4'd10));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd8, 4'd4, 16'd32));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd4, 4'd4, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd5));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_long_fir_stress(output int max_cycles);
  int p;
  begin
    max_cycles = 6000;
    p = 0;
    dut.load_data(30, 32'd48);
    dut.load_data(31, 32'd1);
    dut.load_data(32, 32'd64);
    dut.load_data(33, 32'd144);
    dut.load_data(34, 32'h000000ff);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd30));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd31));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd32));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd11, 4'd0, 16'd33));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd10, 4'd0, 16'd34));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd3, 16'd3));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd3, 16'd7));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd4, 4'd5));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd7, 4'd3, 16'd11));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd6, 4'd7));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd8, 4'd6, 4'd10));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd8, 4'd11, 16'd3));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd3, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd11, 4'd11, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd5));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_pid_phase_stress(output int max_cycles);
  int p;
  begin
    max_cycles = 6000;
    p = 0;
    dut.load_data(40, 32'd40);
    dut.load_data(41, 32'd1);
    dut.load_data(42, 32'd100);
    dut.load_data(43, 32'd80);
    dut.load_data(44, 32'd180);
    dut.load_data(45, 32'h000000ff);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd40));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd41));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd42));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd0, 16'd43));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd11, 4'd0, 16'd44));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd10, 4'd0, 16'd45));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd4, 16'd3));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd6, 4'd3, 4'd5));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd7, 4'd7, 4'd6));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd8, 4'd6, 4'd7));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd8, 4'd8, 4'd10));
    p++;
    dut.load_instr(p, enc_r(OP_AND, 4'd8, 4'd8, 4'd10));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd8, 4'd11, 16'd3));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd4, 4'd4, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd11, 4'd11, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd6));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_random_mem_latency_stress(output int max_cycles);
  int p;
  begin
    max_cycles = 6000;
    p = 0;
    dut.load_data(50, 32'd36);
    dut.load_data(51, 32'd3);
    dut.load_data(52, 32'd16);
    dut.load_data(53, 32'd140);
    dut.load_instr(p, enc_i(OP_LDR, 4'd1, 4'd0, 16'd50));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd2, 4'd0, 16'd51));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd3, 4'd0, 16'd52));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd11, 4'd0, 16'd53));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd4, 4'd3, 16'd3));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd5, 4'd3, 16'd11));
    p++;
    dut.load_instr(p, enc_r(OP_EOR, 4'd6, 4'd4, 4'd5));
    p++;
    dut.load_instr(p, enc_i(OP_LDR, 4'd7, 4'd3, 16'd19));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd6, 4'd6, 4'd7));
    p++;
    dut.load_instr(p, enc_i(OP_STR, 4'd6, 4'd11, 16'd7));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd3, 4'd3, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_ADD, 4'd11, 4'd11, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_SUB, 4'd1, 4'd1, 4'd2));
    p++;
    dut.load_instr(p, enc_r(OP_CMP, 4'd0, 4'd1, 4'd0));
    p++;
    dut.load_instr(p, enc_b(COND_NE, 16'd4));
    p++;
    dut.load_instr(p, enc_halt());
    p++;
  end
endtask

task automatic load_benchmark(input int bench_id, output int max_cycles);
  begin
    case (bench_id)
      0: load_arithmetic_heavy(max_cycles);
      1: load_branch_heavy(max_cycles);
      2: load_memory_heavy(max_cycles);
      3: load_load_use_heavy(max_cycles);
      4: load_mixed_control(max_cycles);
      5: load_tiny_fir(max_cycles);
      6: load_dhrystone_toy(max_cycles);
      7: load_coremark_toy(max_cycles);
      8: load_dsp_fir_codegen(max_cycles);
      9: load_pid_control_codegen(max_cycles);
      10: load_long_fir_stress(max_cycles);
      11: load_pid_phase_stress(max_cycles);
      default: load_random_mem_latency_stress(max_cycles);
    endcase
  end
endtask

