#!/usr/bin/env python3
"""Generate simple comparison plots from PipeSense CSV output."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RESULT_CSV = RESULTS / "pipesense_results.csv"


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


def plot_metric(rows: list[dict[str, str]], metric: str, ylabel: str, filename: str) -> None:
    import matplotlib.pyplot as plt

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
    print(f"Wrote {RESULTS / 'cycles_by_mode.png'}")
    print(f"Wrote {RESULTS / 'ipc_by_mode.png'}")
    print(f"Wrote {RESULTS / 'energy_by_mode.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
