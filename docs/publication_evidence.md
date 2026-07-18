# Publication Evidence Regeneration

Run from the repository root inside the pinned Docker environment:

```text
python3 scripts/audit_standard_benchmarks.py
python3 scripts/run_sim.py
python3 scripts/run_sweep.py
python3 scripts/run_ablations.py
python3 scripts/run_adaptive_baseline.py --seeds 500
python3 scripts/synth_area_report.py
python3 scripts/run_post_synth.py
python3 scripts/generate_publication_evidence.py
python3 scripts/validate_publication_evidence.py
```

The publication generator reads only these committed source CSVs:

- `results/sweep_runs.csv`
- `results/sweep_results.csv`
- `results/ablation_summary.csv`
- `results/ablations/full_adaptive/pipesense_results.csv`

Their SHA-256 values are recorded in
`results/publication/source_manifest.csv`. The generator writes the complete
27-configuration sweep CSV, a complete four-row ablation CSV, PNG/PDF figures,
and the LaTeX tables used by the manuscript. The validator checks schemas,
required values, duplicate keys, configuration counts, failed runs, IPC/CPI
units, raw-to-summary reconciliation, source hashes, baseline seed parity,
post-synthesis status, and rendered outputs.

Warnings that must remain attached to these artifacts:

- All workload metrics are RTL simulation results.
- `energy` is an activity proxy in arbitrary units, not power or energy.
- Zero-cost reconfiguration is an analytical idealization, not a simulation.
- The ASYNC'03 baseline is an architectural control-policy approximation, not
  a reproduction of asynchronous collapsible latches.
- Generic-cell results are common-shell proxy counts.
- ECP5 timing and utilization are post-place-and-route; power is unavailable.
- Full CoreMark, Dhrystone, Embench, and MiBench are blocked and were not run.
