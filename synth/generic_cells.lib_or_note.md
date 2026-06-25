# Generic Cell Mapping Note

The synthesis flow in `synth/yosys_synth.tcl` uses Yosys generic technology
mapping and the built-in cell statistics reported by `stat`.

The CI path synthesizes `synth/yosys_area_proxy.v`, a Yosys-compatible proxy
that mirrors the major state, counter, comparator, and arithmetic structures
of the PipeSense core and adaptive-control additions. It intentionally does
not synthesize the full simulation-oriented SystemVerilog RTL, because the
Ubuntu Yosys frontend can reject the package/import style accepted by the HDL
simulator.

This is a relative area/gate-count proxy only. It is useful for checking
whether observer/controller/reconfiguration-style structures are small
compared with a baseline core proxy, but it is not:

- a calibrated ASIC area result
- an FPGA LUT/FF utilization result
- a timing closure result
- a physical power result
- full RTL synthesis evidence

For paper claims, cite the generated CSV as "generic-cell synthesis proxy" or
"Yosys generic cell-count proxy." Do not describe it as measured silicon area,
full RTL synthesis, or calibrated power.
