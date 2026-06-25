# PipeSense-ARM generic Yosys synthesis script.
#
# Usage:
#   yosys -q -s synth/yosys_synth.tcl
#
# The script emits text reports under results/synth/. The companion Python
# parser scripts/synth_area_report.py converts them to CSV.

proc synth_one {top report_path} {
  design -reset
  read_verilog -sv rtl/defines.svh
  read_verilog -sv rtl/pipeline_registers.sv
  read_verilog -sv rtl/hazard_unit.sv
  read_verilog -sv rtl/forwarding_unit.sv
  read_verilog -sv rtl/pipeline_observer.sv
  read_verilog -sv rtl/adaptive_controller.sv
  read_verilog -sv rtl/reconfig_unit.sv
  read_verilog -sv rtl/perf_counters.sv
  read_verilog -sv rtl/simple_memory.sv
  read_verilog -sv rtl/arm_like_core.sv
  hierarchy -check -top $top
  proc
  opt
  memory
  opt
  techmap
  opt
  tee -o $report_path stat
}

shell mkdir -p results/synth
synth_one arm_like_core results/synth/arm_like_core_yosys_stat.txt
synth_one pipeline_observer results/synth/pipeline_observer_yosys_stat.txt
synth_one adaptive_controller results/synth/adaptive_controller_yosys_stat.txt
synth_one reconfig_unit results/synth/reconfig_unit_yosys_stat.txt
