# Generic Cell Mapping Note

The synthesis flow in `synth/yosys_synth.tcl` uses Yosys generic
technology mapping and the built-in cell statistics reported by `stat`.

This is a relative area/gate-count proxy only. It is useful for checking
whether the observer/controller/reconfiguration logic is small compared with
the baseline core, but it is not:

- a calibrated ASIC area result
- an FPGA LUT/FF utilization result
- a timing closure result
- a physical power result

For paper claims, cite the generated CSV as "generic-cell synthesis proxy" or
"Yosys generic cell-count proxy." Do not describe it as measured silicon area
or calibrated power.
