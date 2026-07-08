# Hardware Realism Notes

PipeSense-ARM is a research prototype, not a production-quality embedded core. This document separates what is hardware-relevant from what is currently modeled.

## Hardware-relevant parts

- Sequential five-stage pipeline state
- Program counter and register file
- Pipeline valid bits
- Load-use hazard detection
- Forwarding paths
- Writeback-to-decode bypass for same-cycle register reads after load stalls
- Branch flush behavior
- Memory-stage wait behavior
- Rolling-window observer counters
- Hysteretic mode controller
- Drain-before-switch reconfiguration protocol
- Performance counters

## Simplified or synthetic parts

- Instruction encoding is educational and ARM-like, not ARM-compatible.
- Data memory has deterministic periodic waits rather than a cache, bus, or DRAM model.
- Branch optimization is modeled as earlier resolution, not as a realistic predictor with state and misprediction recovery.
- Memory optimization suppresses synthetic waits to represent a tiny buffer/prefetch effect.
- Hazard optimization represents an extra bypass path rather than a fully timed forwarding network.
- The baseline register file assumes a small-core bypass from WB into ID rather than modeling half-cycle write/read timing.
- Low-power mode changes an activity proxy, not clock-tree or power-gate cells.
- Safety tags are simulation monitors and should not be counted as a minimal synthesized design.

## Cost reporting discipline

Use `scripts/estimate_hardware_cost.py` for an analytical first-order estimate. Label it clearly as an estimate.

Use `scripts/synth_area_report.py` for the Yosys generic-cell proxy. The
current local run reports 1,830 cells for the baseline core proxy and 2,885
standalone cells for the observer, controller, and reconfiguration modules
combined, or 157.65% of the baseline core proxy. It also reports a 4,850-cell
integrated proxy, a 165.03% delta over the baseline core proxy. Label this
clearly as a proxy, not a calibrated implementation result. The cell-mapping
caveat is documented in `synth/generic_cells.lib_or_note.md`.

For a stronger paper after the generic proxy, add:

- target technology or FPGA family
- area/LUT/register count
- critical path impact
- dynamic power estimate or toggle-based proxy
- observer/controller/reconfiguration overhead as a percent of the baseline core

## Timing realism questions

A reviewer may ask:

- Does `MODE_HAZARD_OPT` lengthen the EX/MEM critical path?
- Does early branch handling move compare logic into ID and affect decode timing?
- Does memory mitigation require storage, tags, or ordering logic?
- Does drain-based reconfiguration overpay penalty compared with safe in-place switching?
- Can the observer classify phases early enough for short embedded loops?

The current prototype does not answer these fully. It makes them visible so future iterations can measure them.
