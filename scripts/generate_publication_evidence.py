#!/usr/bin/env python3
"""Generate publication figures, complete sweep tables, and source hashes."""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = RESULTS / "publication"
PAPER = ROOT / "paper"


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sweep_summary() -> list[dict[str, str]]:
    runs = load(RESULTS / "sweep_runs.csv")
    rows = load(RESULTS / "sweep_results.csv")
    by_tag: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["mode"] == "adaptive_pipesense":
            by_tag[row["sweep_tag"]].append(row)
    fields = [
        "configuration_id", "sweep_tag", "obs_window_cycles", "min_residency_cycles",
        "threshold_profile", "branch_threshold_events", "mem_threshold_cycles",
        "load_use_threshold_events", "frontend_threshold_cycles", "idle_retire_threshold",
        "seed", "workload_count", "total_cycles", "total_retired", "aggregate_ipc",
        "total_energy_proxy_units", "total_transitions", "total_safety_faults", "total_timeouts",
        "run_return_code",
    ]
    out: list[dict[str, str]] = []
    ordered = sorted(
        runs,
        key=lambda row: (
            int(row["obs_window"]), int(row["min_residency"]),
            {"tight": 0, "medium": 1, "loose": 2}[row["threshold_profile"]],
        ),
    )
    for index, run in enumerate(ordered, start=1):
        adaptive = by_tag[run["sweep_tag"]]
        cycles = sum(int(row["cycles"]) for row in adaptive)
        retired = sum(int(row["retired"]) for row in adaptive)
        out.append(
            {
                "configuration_id": str(index),
                "sweep_tag": run["sweep_tag"],
                "obs_window_cycles": run["obs_window"],
                "min_residency_cycles": run["min_residency"],
                "threshold_profile": run["threshold_profile"],
                "branch_threshold_events": run["branch_threshold"],
                "mem_threshold_cycles": run["mem_threshold"],
                "load_use_threshold_events": run["load_use_threshold"],
                "frontend_threshold_cycles": run["frontend_threshold"],
                "idle_retire_threshold": run["idle_threshold"],
                "seed": run["seed"],
                "workload_count": str(len(adaptive)),
                "total_cycles": str(cycles),
                "total_retired": str(retired),
                "aggregate_ipc": f"{retired / cycles:.4f}",
                "total_energy_proxy_units": str(sum(int(row["energy"]) for row in adaptive)),
                "total_transitions": str(sum(int(row["reconfigs"]) for row in adaptive)),
                "total_safety_faults": str(sum(int(row["safety_faults"]) for row in adaptive)),
                "total_timeouts": str(sum(int(row["timed_out"]) for row in adaptive)),
                "run_return_code": run["return_code"],
            }
        )
    write_csv(OUT / "sweep_configuration_summary.csv", out, fields)
    return out


def ablation_summary() -> list[dict[str, str]]:
    full_rows = [
        row for row in load(RESULTS / "ablations" / "full_adaptive" / "pipesense_results.csv")
        if row["mode"] == "adaptive_pipesense"
    ]
    source = load(RESULTS / "ablation_summary.csv")
    full_cycles = sum(int(row["cycles"]) for row in full_rows)
    full_energy = sum(int(row["energy"]) for row in full_rows)
    fields = [
        "ablation", "label", "evidence_type", "total_cycles", "cycle_change_vs_full_pct",
        "total_energy_proxy_units", "energy_change_vs_full_pct", "total_transitions",
        "total_reconfig_penalty_cycles", "total_safety_faults", "total_timeouts",
    ]
    out = [
        {
            "ablation": "full_adaptive",
            "label": "Full adaptive PipeSense",
            "evidence_type": "measured_simulation",
            "total_cycles": str(full_cycles),
            "cycle_change_vs_full_pct": "0.00",
            "total_energy_proxy_units": str(full_energy),
            "energy_change_vs_full_pct": "0.00",
            "total_transitions": str(sum(int(row["reconfigs"]) for row in full_rows)),
            "total_reconfig_penalty_cycles": str(sum(int(row["reconfig_penalty"]) for row in full_rows)),
            "total_safety_faults": str(sum(int(row["safety_faults"]) for row in full_rows)),
            "total_timeouts": str(sum(int(row["timed_out"]) for row in full_rows)),
        }
    ]
    for row in source:
        out.append(
            {
                "ablation": row["ablation"],
                "label": row["label"],
                "evidence_type": (
                    "analytical_idealization" if row["ablation"] == "zero_cost_reconfig"
                    else "measured_simulation"
                ),
                "total_cycles": row["total_adaptive_cycles"],
                "cycle_change_vs_full_pct": row["cycle_change_vs_full_pct"],
                "total_energy_proxy_units": row["total_adaptive_energy"],
                "energy_change_vs_full_pct": row["energy_change_vs_full_pct"],
                "total_transitions": row["total_reconfigs"],
                "total_reconfig_penalty_cycles": row["total_reconfig_penalty"],
                "total_safety_faults": row["total_safety_faults"],
                "total_timeouts": row["total_timeouts"],
            }
        )
    write_csv(OUT / "ablation_evidence.csv", out, fields)
    return out


def plot_sweep(rows: list[dict[str, str]]) -> None:
    profiles = ["tight", "medium", "loose"]
    windows = [16, 32, 64]
    colors = {16: "#0072B2", 32: "#D55E00", 64: "#009E73"}
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 5.2), sharex=True)
    for column, profile in enumerate(profiles):
        for window in windows:
            selected = sorted(
                [row for row in rows if row["threshold_profile"] == profile and int(row["obs_window_cycles"]) == window],
                key=lambda row: int(row["min_residency_cycles"]),
            )
            x = [int(row["min_residency_cycles"]) for row in selected]
            axes[0, column].plot(
                x, [int(row["total_cycles"]) for row in selected], marker="o",
                color=colors[window], linewidth=1.5, label=f"W={window}",
            )
            axes[1, column].plot(
                x, [int(row["total_energy_proxy_units"]) for row in selected], marker="s",
                color=colors[window], linewidth=1.5,
            )
            for row in selected:
                axes[1, column].annotate(
                    row["total_transitions"],
                    (int(row["min_residency_cycles"]), int(row["total_energy_proxy_units"])),
                    textcoords="offset points", xytext=(0, 5), ha="center", fontsize=6,
                )
        axes[0, column].set_title(profile.capitalize(), fontsize=9)
        axes[1, column].set_xlabel("Minimum residency (cycles)")
        axes[0, column].grid(axis="y", alpha=0.25)
        axes[1, column].grid(axis="y", alpha=0.25)
        axes[1, column].set_xticks([8, 24, 48])
    axes[0, 0].set_ylabel("Total cycles")
    axes[1, 0].set_ylabel("Energy proxy (units)")
    axes[0, 2].legend(frameon=False, fontsize=7, loc="best")
    fig.text(0.5, 0.01, "Numbers above lower-panel points are total mode transitions.", ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    for suffix in ("png", "pdf"):
        fig.savefig(OUT / f"sweep_evidence.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_ablation(rows: list[dict[str, str]]) -> None:
    labels = ["Full", "Observer off", "Controller off", "Zero-cost"]
    full_cycles = int(rows[0]["total_cycles"])
    full_energy = int(rows[0]["total_energy_proxy_units"])
    cycles = [100 * int(row["total_cycles"]) / full_cycles for row in rows]
    energy = [100 * int(row["total_energy_proxy_units"]) / full_energy for row in rows]
    x = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    width = 0.36
    left = ax.bar([value - width / 2 for value in x], cycles, width, label="Cycles", color="#0072B2")
    right = ax.bar([value + width / 2 for value in x], energy, width, label="Energy proxy", color="#E69F00")
    right[-1].set_hatch("//")
    left[-1].set_hatch("//")
    ax.axhline(100, color="#333333", linewidth=0.8)
    ax.set_ylabel("Normalized to full PipeSense (%)")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, max(cycles + energy) * 1.16)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    for index, row in enumerate(rows):
        ax.text(index, max(cycles[index], energy[index]) + 2, f"{row['total_transitions']} transitions", ha="center", fontsize=7)
    fig.tight_layout()
    for suffix in ("png", "pdf"):
        fig.savefig(OUT / f"ablation_evidence.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_performance_table(rows: list[dict[str, str]]) -> None:
    labels = [
        ("arithmetic_heavy", "Arithmetic"),
        ("branch_heavy", "Branch"),
        ("coremark_toy", "CoreMark-toy"),
        ("dhrystone_toy", "Dhrystone-toy"),
        ("dsp_fir_codegen", "DSP-FIR"),
        ("load_use_heavy", "Load-use"),
        ("long_fir_stress", "Long-FIR"),
        ("memory_heavy", "Memory"),
        ("mixed_control", "Mixed-control"),
        ("pid_control_codegen", "PID-codegen"),
        ("pid_phase_stress", "PID-phase"),
        ("random_mem_latency_stress", "Random-memory"),
        ("tiny_fir", "Tiny-FIR"),
    ]
    by_bench: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_bench[row["bench"]][row["mode"]] = row

    table_rows: list[tuple[str, int, int, float, float]] = []
    for bench, label in labels:
        modes = by_bench[bench]
        normal = int(modes["static_normal"]["cycles"])
        adaptive = int(modes["adaptive_pipesense"]["cycles"])
        best_fixed = min(int(row["cycles"]) for mode, row in modes.items() if mode.startswith("fixed_"))
        reduction = 100.0 * (normal - adaptive) / normal
        oracle_gap = 100.0 * (best_fixed - adaptive) / best_fixed
        table_rows.append((label, normal, adaptive, reduction, oracle_gap))

    total_normal = sum(row[1] for row in table_rows)
    total_adaptive = sum(row[2] for row in table_rows)
    total_reduction = 100.0 * (total_normal - total_adaptive) / total_normal
    mean_oracle_gap = sum(row[4] for row in table_rows) / len(table_rows)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Adaptive cycle results. Oracle gap is relative to the best fixed mode; the final oracle entry is the mean of per-workload gaps.}",
        r"\label{tab:performance}",
        r"\footnotesize",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Workload & Normal & Adapt. & Red. (\%) & Oracle (\%) \\",
        r"\midrule",
    ]
    for label, normal, adaptive, reduction, oracle_gap in table_rows:
        lines.append(f"{label} & {normal} & {adaptive} & {reduction:.2f} & {oracle_gap:.2f}" + r" \\")
    lines.extend(
        [
            r"\midrule",
            f"Total / mean & {total_normal} & {total_adaptive} & {total_reduction:.2f} & {mean_oracle_gap:.2f}" + r" \\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    (PAPER / "generated_performance_table.tex").write_text("\n".join(lines), encoding="utf-8")


def write_latex_tables(sweep: list[dict[str, str]], ablations: list[dict[str, str]]) -> None:
    sweep_lines = [
        r"\begin{table*}[t]",
        r"\caption{Complete 27-configuration sweep. IPC is aggregate retired instructions divided by aggregate cycles; energy is a simulation proxy.}",
        r"\label{tab:complete-sweep}",
        r"\centering\scriptsize",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{rrrrlrrrrrrr}",
        r"\toprule",
        r"ID & $W$ & $R$ & Seed & Profile & Thresholds (B/M/L/F/I) & Cycles & IPC & Energy & Trans. & Faults & TO \\",
        r"\midrule",
    ]
    for row in sweep:
        thresholds = "/".join(
            row[key] for key in (
                "branch_threshold_events", "mem_threshold_cycles", "load_use_threshold_events",
                "frontend_threshold_cycles", "idle_retire_threshold",
            )
        )
        sweep_lines.append(
            f"{row['configuration_id']} & {row['obs_window_cycles']} & {row['min_residency_cycles']} & "
            f"{row['seed']} & {row['threshold_profile']} & {thresholds} & {row['total_cycles']} & "
            f"{row['aggregate_ipc']} & {row['total_energy_proxy_units']} & {row['total_transitions']} & "
            f"{row['total_safety_faults']} & {row['total_timeouts']} \\\\"
        )
    sweep_lines.extend([r"\bottomrule", r"\end{tabular}}", r"\end{table*}", ""])
    (PAPER / "generated_sweep_table.tex").write_text("\n".join(sweep_lines), encoding="utf-8")

    ablation_lines = [
        r"\begin{table}[t]",
        r"\caption{Ablation evidence over all 13 directed workloads. Energy is the simulation activity proxy. Zero-cost reconfiguration is analytical; other rows are measured simulation.}",
        r"\label{tab:ablation-evidence}",
        r"\centering\scriptsize",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Variant & Cycles & Energy proxy & Trans. & Penalty \\",
        r"\midrule",
    ]
    for row in ablations:
        label = {
            "full_adaptive": "Full PipeSense",
            "observer_disabled": "Observer off",
            "controller_disabled": "Controller off",
            "zero_cost_reconfig": "Zero-cost ideal",
        }[row["ablation"]]
        ablation_lines.append(
            f"{label} & {row['total_cycles']} & {row['total_energy_proxy_units']} & "
            f"{row['total_transitions']} & {row['total_reconfig_penalty_cycles']} \\\\"
        )
    ablation_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (PAPER / "generated_ablation_table.tex").write_text("\n".join(ablation_lines), encoding="utf-8")


def write_manifest() -> None:
    sources = [
        RESULTS / "sweep_runs.csv",
        RESULTS / "sweep_results.csv",
        RESULTS / "ablation_summary.csv",
        RESULTS / "ablations" / "full_adaptive" / "pipesense_results.csv",
        RESULTS / "pipesense_results.csv",
    ]
    rows = []
    for path in sources:
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "role": "committed_source_csv",
            }
        )
    write_csv(OUT / "source_manifest.csv", rows, ["path", "sha256", "role"])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sweep = sweep_summary()
    ablations = ablation_summary()
    directed = load(RESULTS / "pipesense_results.csv")
    plot_sweep(sweep)
    plot_ablation(ablations)
    write_performance_table(directed)
    write_latex_tables(sweep, ablations)
    write_manifest()
    print(f"Wrote {len(sweep)} sweep configurations and {len(ablations)} ablation rows under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
