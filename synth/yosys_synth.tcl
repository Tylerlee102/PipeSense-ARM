# PipeSense-ARM generic Yosys area-proxy script.
#
# Usage:
#   yosys -q -s synth/yosys_synth.tcl
#
# This script intentionally reads synth/yosys_area_proxy.v instead of the full
# SystemVerilog research RTL. The full RTL uses package/import constructs and
# testbench-friendly tasks that are accepted by Icarus Verilog but are not
# consistently accepted by the older open-source Yosys package on Ubuntu CI.
# The generated numbers are therefore a generic-cell proxy, not full RTL
# synthesis evidence.

shell mkdir -p results/synth

design -reset
read_verilog synth/yosys_area_proxy.v
hierarchy -check -top arm_like_core
proc
opt
memory
opt
techmap
opt
tee -o results/synth/arm_like_core_yosys_stat.txt stat

design -reset
read_verilog synth/yosys_area_proxy.v
hierarchy -check -top pipeline_observer
proc
opt
memory
opt
techmap
opt
tee -o results/synth/pipeline_observer_yosys_stat.txt stat

design -reset
read_verilog synth/yosys_area_proxy.v
hierarchy -check -top adaptive_controller
proc
opt
memory
opt
techmap
opt
tee -o results/synth/adaptive_controller_yosys_stat.txt stat

design -reset
read_verilog synth/yosys_area_proxy.v
hierarchy -check -top reconfig_unit
proc
opt
memory
opt
techmap
opt
tee -o results/synth/reconfig_unit_yosys_stat.txt stat
