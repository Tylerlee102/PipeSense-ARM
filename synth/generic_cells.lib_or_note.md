# Generic Cell Mapping Note

The synthesis flow in `synth/yosys_synth.tcl` uses Yosys generic-cell technology
mapping and the built-in cell statistics reported by `stat`.

The baseline and integrated runs share the synthesizable core shell in
`synth/yosys_area_proxy.v`. The integrated run instantiates the production
`rtl/pipeline_observer.sv`, `rtl/adaptive_controller.sv`, and
`rtl/reconfig_unit.sv` modules. Standalone counts use the same parameters as
the executable core. The shell exists because the research core uses
testbench-loaded internal memories and simulation tasks that do not form a
meaningful standalone synthesis interface.

This removes the former hand-written adaptive proxies and their debug-only
wide outputs. The result is a fair relative count of actual PipeSense control
RTL around a common core shell, but it is still not:

- a calibrated ASIC area result
- an FPGA LUT/FF utilization result
- a timing closure result
- a physical power result
- full processor RTL synthesis evidence
- full RTL synthesis of the processor

For paper claims, cite the generated CSV as a "Yosys generic cell-count
estimate of the production adaptive RTL against a common core shell." Do not
describe it as measured silicon area, full processor synthesis, or calibrated
power.
