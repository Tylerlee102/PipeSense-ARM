# Threats to Validity

## Internal validity

The synthetic benchmarks are designed to trigger specific phases. That makes debugging easier, but it can overstate how cleanly a real workload separates into branch, memory, hazard, and idle regions.

The current observer uses fixed thresholds. Results depend on window size, threshold profile, benchmark length, and minimum residency. Use `scripts/run_sweep.py` before claiming robustness.

## External validity

The ISA is educational and ARM-like. It does not model the full ARM ISA, exceptions, interrupts, privilege levels, memory ordering, caches, branch predictors, or realistic SoC buses.

The memory model uses deterministic waits. Real embedded memory behavior depends on cache locality, bus contention, DMA, scratchpads, and peripheral timing.

## Construct validity

IPC and cycle count are direct simulator metrics. The energy proxy is not physical energy. It should be described as an activity proxy until calibrated against synthesis or gate-level toggle data.

The Yosys hardware-cost proxy is a generic-cell result, not calibrated FPGA or ASIC implementation evidence. It is useful for transparency but should not be used as final area, timing, or power evidence.

## Conclusion validity

Adaptive speedup over static normal mode does not prove that adaptive control is better than a well-chosen fixed design. The oracle best-fixed comparison is required to make the conclusion credible.

If adaptive mode is slower on arithmetic-heavy or short benchmarks, that should be presented as evidence of reconfiguration overhead and phase-detection latency, not hidden.
