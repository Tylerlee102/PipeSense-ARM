# PipeSense-ARM Research Limit Closure

Generated: 2026-07-08T00:51:04.383628+00:00
Overall status: actionable_limits_closed_for_current_scope

## Bottom Line
The agent can close the audit findings for the current prototype-paper scope by verifying and reporting the existing evidence. It cannot honestly erase the need for real workload ports, target hardware calibration, or a full-core proof if the claims expand.

## Limits

### Workload validity
- Status: mitigated_for_current_paper_scope
- What the agent can fix: Run and summarize the benchmark matrix, preserve negative cases, verify reference-model parity, and use the 27-configuration sensitivity sweep as robustness evidence.
- What remains external: A publication-standard workload suite or compiler-generated embedded benchmark ports would still be needed for broad architecture claims.
- Next action: Keep claims scoped to the current 10-benchmark prototype suite, or add real/compiler-generated benchmark ports before making broad workload claims.
- Evidence:
  - 10 benchmark rows summarized from results/pipesense_results.csv
  - 27 sweep configurations in results/sweep_runs.csv
  - results/sweep_adaptive_vs_fixed.csv records adaptive wins and non-wins
  - results/ablation_summary.csv separates observer/controller/reconfiguration effects

### Hardware realism
- Status: proxy_evidence_complete
- What the agent can fix: Regenerate the analytical hardware-cost estimate, parse the Yosys generic-cell proxy, and enforce wording that labels energy and area as proxies.
- What remains external: Calibrated power, timing, FPGA utilization, or ASIC area requires a target toolchain and target technology.
- Next action: Use the proxy numbers for transparent overhead discussion, then run an FPGA or ASIC flow if the paper needs physical implementation claims.
- Evidence:
  - baseline core cells: 1830
  - observer/controller/reconfiguration cells: 2819
  - proxy overhead vs core: 154.04%
  - 4 analytical cost rows in results/hardware_cost_estimate.csv

### Formal coverage
- Status: bounded_safety_evidence_complete
- What the agent can fix: Run simulation assertions, summarize the 500-seed safety fuzz evidence, and track the bounded no-double-commit proof result.
- What remains external: A full-core formal proof bound directly to arm_like_core is still a research task, not a report-generation step.
- Next action: Present bounded safety evidence honestly now; implement a reduced full-core formal harness before claiming complete processor correctness.
- Evidence:
  - 500 fuzz seeds in results/safety/fuzz_summary.csv
  - 0 fuzz failures
  - no-double-commit bounded proof PASS: True
  - docs/safety_proof_sketch.md maps invariants to monitors and formal jobs
