# Complete-Design Post-Synthesis Evidence

## Scope

`synth/production_ecp5.ys` synthesizes `pipesense_fpga_top`, which contains the
complete production `arm_like_core`, both 256 x 32-bit memories, observer,
PipeSense controller, safe reconfiguration unit, performance counters, and a
compact debug mux. The selectable ASYNC'03 baseline controller is compiled out
of the default production policy by constant propagation.

Programs and initial data are loaded while `rst_n` is low through
`program_write_en`, `program_select_dmem`, `program_addr`, and
`program_wdata`. This loader is synthesizable and prevents the memories from
being optimized as unspecified constants. The asynchronous-read educational
memories map to distributed ECP5 RAM resources, not block RAM.

## Reproduced flow

```text
docker build -t pipesense-arm .
docker run --rm -v "${PWD}:/workspace" -w /workspace pipesense-arm python3 scripts/run_post_synth.py
```

- Target: Lattice LFE5U-85F, CABGA756, speed grade 6
- Constraint: 25.000 MHz
- Yosys: 0.33 (`2584903a060`)
- nextpnr-ecp5: 0.6-3build5
- Achieved maximum frequency: 34.124 MHz
- Worst setup slack at 25 MHz: +10.695 ns
- TRELLIS_COMB: 7,480 / 83,640
- TRELLIS_FF: 1,396 / 83,640
- TRELLIS_RAMW distributed-memory write resources: 256 / 10,455
- DP16KD block RAM: 0 / 208
- I/O: 91 / 365
- Power: **unavailable**

Power is not estimated because this flow has no characterized LFE5U-85F power
model and no switching-activity trace. The simulation energy proxy is not
converted to watts or joules.

Raw Yosys and nextpnr logs, the detailed nextpnr JSON report, the parsed CSV,
the exact command manifest, and the explicit power status are in
`results/post_synth/`. Yosys emits one significant mapping warning: the
16-entry register file is implemented as registers. ABC also labels its input
network combinational during mapping; it completes successfully. nextpnr
reports timing PASS at the requested constraint.

The earlier `results/synth/` common-shell generic-cell comparison remains a
**proxy** for relative adaptive-control overhead. It is not FPGA utilization,
ASIC area, timing, or power.
