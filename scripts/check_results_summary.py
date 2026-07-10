#!/usr/bin/env python3
"""Check the public results summary against generated evidence files."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SUMMARY = RESULTS / "SUMMARY.md"


def load_csv(relative_path: str) -> list[dict[str, str]]:
    path = RESULTS / relative_path
    if not path.exists():
        raise RuntimeError(f"Missing generated evidence: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def percent_reduction(baseline: float, candidate: float) -> float:
    return ((baseline - candidate) / baseline) * 100.0


def require(summary: str, expected: str, errors: list[str]) -> None:
    if expected not in summary:
        errors.append(f"Missing or stale summary line: {expected}")


def main() -> int:
    if not SUMMARY.exists():
        print(f"FAIL Missing checked-in summary: {SUMMARY}")
        return 1

    summary = SUMMARY.read_text(encoding="utf-8")
    errors: list[str] = []

    raw = load_csv("pipesense_results.csv")
    adaptive = load_csv("adaptive_improvement.csv")
    oracle = load_csv("oracle_gap.csv")
    fuzz = load_csv("safety/fuzz_summary.csv")
    sweep_runs = load_csv("sweep_runs.csv")
    sweep_results = load_csv("sweep_results.csv")
    sweep_compare = load_csv("sweep_adaptive_vs_fixed.csv")
    ablations = load_csv("ablation_summary.csv")
    area = load_csv("synth/area_summary.csv")

    benches = {row["bench"] for row in raw}
    modes = {row["mode"] for row in raw}
    require(
        summary,
        f"- Main simulation: {len(benches)} benchmarks x {len(modes)} modes = {len(raw)} rows.",
        errors,
    )
    require(
        summary,
        f"- Simulation safety faults: {sum(int(row['safety_faults']) for row in raw)}.",
        errors,
    )
    require(
        summary,
        f"- Simulation timeouts: {sum(int(row['timed_out']) for row in raw)}.",
        errors,
    )

    normal_cycles = sum(int(row["normal_cycles"]) for row in adaptive)
    adaptive_cycles = sum(int(row["adaptive_cycles"]) for row in adaptive)
    normal_energy = sum(int(row["normal_energy"]) for row in adaptive)
    adaptive_energy = sum(int(row["adaptive_energy"]) for row in adaptive)
    avg_cycle_reduction = sum(float(row["cycle_reduction_pct"]) for row in adaptive) / len(adaptive)
    avg_ipc_improvement = sum(float(row["ipc_improvement_pct"]) for row in adaptive) / len(adaptive)
    avg_energy_reduction = sum(float(row["energy_reduction_pct"]) for row in adaptive) / len(adaptive)
    require(
        summary,
        f"- Adaptive vs static normal, total cycles: {adaptive_cycles:,} adaptive vs {normal_cycles:,} static.",
        errors,
    )
    require(
        summary,
        f"- Adaptive vs static normal, total cycle reduction: {percent_reduction(normal_cycles, adaptive_cycles):.2f}%.",
        errors,
    )
    require(
        summary,
        f"- Adaptive vs static normal, average per-benchmark cycle reduction: {avg_cycle_reduction:.2f}%.",
        errors,
    )
    require(
        summary,
        f"- Adaptive vs static normal, average IPC improvement: {avg_ipc_improvement:.2f}%.",
        errors,
    )
    require(
        summary,
        f"- Adaptive vs static normal, total activity-energy proxy reduction: {percent_reduction(normal_energy, adaptive_energy):.2f}%.",
        errors,
    )
    require(
        summary,
        f"- Adaptive vs static normal, average per-benchmark activity-energy proxy reduction: {avg_energy_reduction:.2f}%.",
        errors,
    )

    improved = [row for row in adaptive if float(row["cycle_reduction_pct"]) > 0]
    tied = [row for row in adaptive if float(row["cycle_reduction_pct"]) == 0]
    regressed = [row for row in adaptive if float(row["cycle_reduction_pct"]) < 0]
    require(
        summary,
        f"- Adaptive cycle outcomes: {len(improved)} improved, {len(tied)} tied, {len(regressed)} regressed.",
        errors,
    )
    if len(regressed) == 1:
        row = regressed[0]
        require(
            summary,
            f"- Regressed adaptive workload: `{row['bench']}` at {float(row['cycle_reduction_pct']):.2f}% cycles vs static normal.",
            errors,
        )

    avg_oracle_cycle = sum(float(row["adaptive_gap_to_best_fixed_pct"]) for row in oracle) / len(oracle)
    avg_oracle_energy = sum(float(row["adaptive_energy_gap_to_best_fixed_pct"]) for row in oracle) / len(oracle)
    require(
        summary,
        f"- Adaptive vs best fixed mode, average cycle gap: {avg_oracle_cycle:.2f}%.",
        errors,
    )
    require(
        summary,
        f"- Adaptive vs best fixed mode, average activity-energy proxy gap: {avg_oracle_energy:.2f}%.",
        errors,
    )

    fuzz_seeds = {row["seed"] for row in fuzz}
    fuzz_faults = sum(int(row["safety_faults"]) for row in fuzz)
    fuzz_assertions = sum(int(row["assertion_failures"]) for row in fuzz)
    fuzz_timeouts = sum(int(row["timed_out"]) for row in fuzz)
    fuzz_nonzero = sum(int(row["return_code"]) != 0 for row in fuzz)
    require(
        summary,
        "- Safety fuzz: "
        f"{len(fuzz_seeds)} seeds, {len(fuzz):,} mode-result rows, "
        f"{fuzz_faults} safety faults, {fuzz_assertions} assertion failures, "
        f"{fuzz_timeouts} timeouts, {fuzz_nonzero} nonzero return codes.",
        errors,
    )

    sweep_failed = sum(int(row["return_code"]) != 0 for row in sweep_runs)
    sweep_wins = sum(row["adaptive_wins_cycles"].lower() == "true" for row in sweep_compare)
    sweep_nonwins = len(sweep_compare) - sweep_wins
    require(
        summary,
        "- Sweep: "
        f"{len(sweep_runs)} configurations, {len(sweep_results):,} result rows, "
        f"{sweep_failed} failed configurations, {sweep_wins:,} adaptive win cells, "
        f"{sweep_nonwins:,} adaptive non-win cells.",
        errors,
    )

    ablation_by_name = {row["ablation"]: row for row in ablations}
    for key, label in [
        ("observer_disabled", "observer disabled"),
        ("controller_disabled", "controller disabled"),
    ]:
        row = ablation_by_name[key]
        require(
            summary,
            f"- Ablation, {label}: {int(row['total_adaptive_cycles']):,} adaptive cycles, "
            f"{float(row['cycle_change_vs_full_pct']):+.2f}% cycles vs full adaptive, "
            f"{int(row['total_safety_faults'])} safety faults, {int(row['total_timeouts'])} timeouts.",
            errors,
        )
    zero_cost = ablation_by_name["zero_cost_reconfig"]
    require(
        summary,
        "- Ablation, zero-cost reconfiguration idealization: "
        f"{int(zero_cost['total_adaptive_cycles']):,} adaptive cycles, "
        f"{float(zero_cost['cycle_change_vs_full_pct']):+.2f}% cycles vs full adaptive.",
        errors,
    )

    area_by_module = {row["module"]: row for row in area}
    core = area_by_module["arm_like_core"]
    total = area_by_module["observer_controller_reconfig_total"]
    integrated = area_by_module["pipesense_integrated_core"]
    require(
        summary,
        f"- Yosys generic-cell area proxy: baseline core proxy {int(core['number_of_cells']):,} cells.",
        errors,
    )
    require(
        summary,
        "- Yosys generic-cell area proxy: observer/controller/reconfiguration standalone sum "
        f"{int(total['number_of_cells']):,} cells, {float(total['overhead_vs_core_pct']):.2f}% of baseline core proxy.",
        errors,
    )
    require(
        summary,
        "- Yosys integrated generic-cell proxy: "
        f"{int(integrated['number_of_cells']):,} cells, "
        f"{float(integrated['overhead_vs_core_pct']):.2f}% delta over baseline core proxy.",
        errors,
    )

    forbidden_stale_claims = ["Paper check", "Paper preview", "exactly 5 generated pages"]
    for claim in forbidden_stale_claims:
        if claim in summary:
            errors.append(f"Stale manuscript claim remains in results summary: {claim}")

    for error in errors:
        print(f"FAIL {error}")
    if errors:
        print(f"Results summary is stale: {len(errors)} mismatch(es).")
        return 1
    print("Results summary matches generated simulation, sweep, fuzz, ablation, and synthesis evidence.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
