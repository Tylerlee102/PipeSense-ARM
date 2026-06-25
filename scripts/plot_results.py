#!/usr/bin/env python3
"""Generate simple comparison plots from PipeSense CSV output."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RESULT_CSV = RESULTS / "pipesense_results.csv"
SWEEP_COMPARISON_CSV = RESULTS / "sweep_adaptive_vs_fixed.csv"
SWEEP_RESULTS_CSV = RESULTS / "sweep_results.csv"


def load_rows() -> list[dict[str, str]]:
    with RESULT_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grouped(rows: list[dict[str, str]], metric: str) -> tuple[list[str], list[str], dict[str, list[float]]]:
    benches = sorted({row["bench"] for row in rows})
    modes = [
        "static_normal",
        "fixed_branch",
        "fixed_memory",
        "fixed_hazard",
        "fixed_low_power",
        "adaptive_pipesense",
    ]
    values: dict[str, list[float]] = {mode: [] for mode in modes}
    by_key = {(row["bench"], row["mode"]): row for row in rows}
    for mode in modes:
        for bench in benches:
            row = by_key.get((bench, mode))
            values[mode].append(float(row[metric]) if row else 0.0)
    return benches, modes, values


def pyplot():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    return plt


def plot_metric(rows: list[dict[str, str]], metric: str, ylabel: str, filename: str) -> None:
    plt = pyplot()

    benches, modes, values = grouped(rows, metric)
    width = 0.13
    xs = list(range(len(benches)))

    plt.figure(figsize=(12, 5))
    for i, mode in enumerate(modes):
        shifted = [x + (i - 2.5) * width for x in xs]
        plt.bar(shifted, values[mode], width=width, label=mode)

    plt.xticks(xs, benches, rotation=20, ha="right")
    plt.ylabel(ylabel)
    plt.title(f"PipeSense {ylabel} by benchmark")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS / filename, dpi=160)
    plt.close()


def write_text_fallback(rows: list[dict[str, str]]) -> None:
    path = RESULTS / "plot_results.txt"
    with path.open("w", encoding="utf-8") as f:
        f.write("matplotlib is not installed; CSV data is available for plotting.\n\n")
        for row in rows:
            f.write(
                f"{row['bench']:18s} {row['mode']:20s} "
                f"cycles={row['cycles']:>5s} ipc={row['ipc']:>6s} energy={row['energy']:>6s}\n"
            )
    print(f"Wrote {path}")


def load_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def plot_sensitivity(rows: list[dict[str, str]], field: str, filename: str, title: str) -> None:
    plt = pyplot()

    filtered = [row for row in rows if row["baseline_mode"] == "static_normal"]
    grouped_values: dict[str, list[float]] = defaultdict(list)
    for row in filtered:
        grouped_values[row[field]].append(float(row["cycle_reduction_pct"]))

    labels = sorted(grouped_values, key=lambda value: int(value) if value.isdigit() else value)
    means = [average(grouped_values[label]) for label in labels]

    plt.figure(figsize=(7, 4))
    plt.plot(labels, means, marker="o")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.ylabel("Adaptive cycle reduction vs static normal (%)")
    plt.xlabel(field)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(RESULTS / filename, dpi=160)
    plt.close()


def plot_overhead_scatter(compare_rows: list[dict[str, str]], result_rows: list[dict[str, str]]) -> None:
    plt = pyplot()

    adaptive_by_key = {
        (
            row["sweep_tag"],
            row["obs_window"],
            row["min_residency"],
            row["threshold_profile"],
            row["seed"],
            row["bench"],
        ): row
        for row in result_rows
        if row["mode"] == "adaptive_pipesense"
    }

    xs: list[float] = []
    ys: list[float] = []
    for row in compare_rows:
        if row["baseline_mode"] != "static_normal":
            continue
        key = (
            row["sweep_tag"],
            row["obs_window"],
            row["min_residency"],
            row["threshold_profile"],
            row["seed"],
            row["bench"],
        )
        adaptive = adaptive_by_key.get(key)
        if not adaptive:
            continue
        xs.append(float(adaptive["reconfig_penalty"]))
        ys.append(float(row["cycle_reduction_pct"]))

    if not xs:
        return

    plt.figure(figsize=(7, 4))
    plt.scatter(xs, ys, alpha=0.75)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xlabel("Adaptive reconfiguration penalty cycles")
    plt.ylabel("Cycle reduction vs static normal (%)")
    plt.title("Reconfiguration overhead versus benefit")
    plt.tight_layout()
    plt.savefig(RESULTS / "reconfig_overhead_vs_benefit.png", dpi=160)
    plt.close()


def plot_seed_distribution(compare_rows: list[dict[str, str]]) -> None:
    plt = pyplot()

    filtered = [row for row in compare_rows if row["baseline_mode"] == "static_normal"]
    by_seed: dict[str, list[float]] = defaultdict(list)
    for row in filtered:
        by_seed[row["seed"]].append(float(row["cycle_reduction_pct"]))

    labels = sorted(by_seed, key=lambda value: int(value) if value.isdigit() else value)
    if not labels:
        return
    data = [by_seed[label] for label in labels]

    plt.figure(figsize=(max(7, len(labels) * 0.35), 4))
    try:
        plt.boxplot(data, tick_labels=labels, showmeans=True)
    except TypeError:
        plt.boxplot(data, labels=labels, showmeans=True)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xlabel("Seed")
    plt.ylabel("Cycle reduction vs static normal (%)")
    plt.title("Distribution across seeds")
    plt.tight_layout()
    plt.savefig(RESULTS / "seed_distribution.png", dpi=160)
    plt.close()


def main() -> int:
    if not RESULT_CSV.exists():
        print(f"No CSV found at {RESULT_CSV}. Run scripts/analyze_results.py first.")
        return 1

    rows = load_rows()
    RESULTS.mkdir(exist_ok=True)
    try:
        import matplotlib  # noqa: F401
    except Exception:
        write_text_fallback(rows)
        return 0

    plot_metric(rows, "cycles", "Cycles", "cycles_by_mode.png")
    plot_metric(rows, "ipc", "IPC", "ipc_by_mode.png")
    plot_metric(rows, "energy", "Activity-energy proxy", "energy_by_mode.png")
    compare_rows = load_optional_csv(SWEEP_COMPARISON_CSV)
    sweep_rows = load_optional_csv(SWEEP_RESULTS_CSV)
    if compare_rows:
        plot_sensitivity(compare_rows, "obs_window", "sensitivity_obs_window.png", "Sensitivity to observer window")
        plot_sensitivity(compare_rows, "min_residency", "sensitivity_min_residency.png", "Sensitivity to mode residency")
        plot_sensitivity(compare_rows, "threshold_profile", "sensitivity_threshold_profile.png", "Sensitivity to threshold profile")
        plot_overhead_scatter(compare_rows, sweep_rows)
        plot_seed_distribution(compare_rows)
    print(f"Wrote {RESULTS / 'cycles_by_mode.png'}")
    print(f"Wrote {RESULTS / 'ipc_by_mode.png'}")
    print(f"Wrote {RESULTS / 'energy_by_mode.png'}")
    if compare_rows:
        print(f"Wrote {RESULTS / 'sensitivity_obs_window.png'}")
        print(f"Wrote {RESULTS / 'sensitivity_min_residency.png'}")
        print(f"Wrote {RESULTS / 'sensitivity_threshold_profile.png'}")
        print(f"Wrote {RESULTS / 'reconfig_overhead_vs_benefit.png'}")
        print(f"Wrote {RESULTS / 'seed_distribution.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
