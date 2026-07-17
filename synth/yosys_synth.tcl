# PipeSense-ARM relative generic-cell synthesis.
#
# The baseline and integrated runs share synth/yosys_area_proxy.v as their core
# shell. PipeSense overhead is synthesized from the production adaptive RTL.

design -reset
read_verilog -sv -Irtl rtl/pipeline_observer.sv rtl/adaptive_controller.sv rtl/reconfig_unit.sv synth/yosys_area_proxy.v
hierarchy -check -top arm_like_core
proc
opt
memory
opt
techmap
opt
tee -o results/synth/arm_like_core_yosys_stat.txt stat

design -reset
read_verilog -sv -Irtl rtl/pipeline_observer.sv rtl/adaptive_controller.sv rtl/reconfig_unit.sv synth/yosys_area_proxy.v
chparam -set WINDOW_SIZE 32 pipeline_observer
hierarchy -check -top pipeline_observer
proc
opt
memory
opt
techmap
opt
tee -o results/synth/pipeline_observer_yosys_stat.txt stat

design -reset
read_verilog -sv -Irtl rtl/pipeline_observer.sv rtl/adaptive_controller.sv rtl/reconfig_unit.sv synth/yosys_area_proxy.v
chparam -set MIN_MODE_RESIDENCY 8 -set PHASE_STABLE_COUNT 1 adaptive_controller
hierarchy -check -top adaptive_controller
proc
opt
memory
opt
techmap
opt
tee -o results/synth/adaptive_controller_yosys_stat.txt stat

design -reset
read_verilog -sv -Irtl rtl/pipeline_observer.sv rtl/adaptive_controller.sv rtl/reconfig_unit.sv synth/yosys_area_proxy.v
hierarchy -check -top reconfig_unit
proc
opt
memory
opt
techmap
opt
tee -o results/synth/reconfig_unit_yosys_stat.txt stat

design -reset
read_verilog -sv -Irtl rtl/pipeline_observer.sv rtl/adaptive_controller.sv rtl/reconfig_unit.sv synth/yosys_area_proxy.v
hierarchy -check -top pipesense_integrated_core
proc
opt
memory
opt
techmap
opt
flatten
opt
tee -o results/synth/pipesense_integrated_core_yosys_stat.txt stat
