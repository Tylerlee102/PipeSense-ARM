# Standard Benchmark Status

PipeSense-ARM does **not** currently execute full CoreMark, Dhrystone,
Embench, or MiBench. The repository's `coremark_toy` and `dhrystone_toy`
programs are synthetic ISA-level workloads and are not standard benchmarks.

## Verified blockers

- The implemented ISA has 11 operations and no multiply, divide, call,
  return, stack convention, byte access, or indirect branch.
- There is no C compiler backend, assembler, linker, ABI, startup code, or C
  library for this ISA.
- Instruction and data memories each contain 256 32-bit words (1 KiB each).
- Test programs are currently encoded by SystemVerilog tasks, not compiled
  from C.

The synthesizable FPGA boundary in `rtl/pipesense_fpga_top.sv` initializes
memory through `program_write_en`, `program_select_dmem`, `program_addr`, and
`program_wdata` while reset is asserted. This is a real loading path, but no
standard benchmark image can be produced until a compatible software
toolchain and runtime exist.

## Requested benchmark configurations

| Benchmark | Version/source | Required configuration | Status |
|---|---|---|---|
| CoreMark | EEMBC CoreMark 1.0, `eembc/coremark` | Official sources and validation rules; at least 2,000 timed iterations | Blocked, not run |
| Dhrystone | Reinhold P. Weicker Dhrystone 2.1 | Full 2.1 sources; iteration count selected for a measurable timed region | Blocked, not run |
| Embench | Current tagged release at integration time | Full speed or size suite with documented board support | Blocked by the same toolchain/runtime gaps |
| MiBench | Upstream benchmark programs and inputs | A named subset with unmodified input data | Blocked by the same toolchain/runtime gaps |

Compiler version and flags are `unavailable`, benchmark inputs and iteration
counts are `not run`, and no benchmark score is reported. Run
`python scripts/audit_standard_benchmarks.py` to regenerate the committed
capability record.
