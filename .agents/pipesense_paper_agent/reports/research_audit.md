# PipeSense-ARM Research Audit

Generated: 2026-07-08T00:51:04.384629+00:00
Overall status: usable_with_mitigated_limits

## Check Results
- PASS paper_check: `C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\tyboy\OneDrive\Documents\mit_2026\scripts\check_paper.py`
- PASS artifact_check: `C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\tyboy\OneDrive\Documents\mit_2026\scripts\check_artifact.py`
- PASS result_validation: `C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\tyboy\OneDrive\Documents\mit_2026\scripts\validate_results.py`

## Result Evidence
- Simulation rows: 60
- Benchmarks: 10
- Safety faults: 0
- Timeouts: 0
- Fuzz seeds: 500
- Fuzz failures: 0

## Limit Closure
- Status: actionable_limits_closed_for_current_scope
- Summary: The agent can close the audit findings for the current prototype-paper scope by verifying and reporting the existing evidence. It cannot honestly erase the need for real workload ports, target hardware calibration, or a full-core proof if the claims expand.

## Findings
- P3 Workload validity: mitigated_for_current_paper_scope: A publication-standard workload suite or compiler-generated embedded benchmark ports would still be needed for broad architecture claims. (evidence: 10 benchmark rows summarized from results/pipesense_results.csv; 27 sweep configurations in results/sweep_runs.csv)
- P3 Hardware realism: proxy_evidence_complete: Calibrated power, timing, FPGA utilization, or ASIC area requires a target toolchain and target technology. (evidence: baseline core cells: 1830; observer/controller/reconfiguration cells: 2819)
- P3 Formal coverage: bounded_safety_evidence_complete: A full-core formal proof bound directly to arm_like_core is still a research task, not a report-generation step. (evidence: 500 fuzz seeds in results/safety/fuzz_summary.csv; 0 fuzz failures)

## Missing Evidence Files
- None
