#!/usr/bin/env python3
"""Parse PipeSense simulation output and produce CSV research tables."""

from __future__ import annotations

import csv
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DEFAULT_LOG = RESULTS / "sim_output.txt"
RESULT_CSV = RESULTS / "pipesense_results.csv"
IMPROVEMENT_CSV = RESULTS / "adaptive_improvement.csv"
ORACLE_GAP_CSV = RESULTS / "oracle_gap.csv"

FIELDS = [
    "bench",
    "mode",
    "cycles",
    "retired",
    "ipc",
    "cpi",
    "ipc_x1000",
    "stalls",
    "stalls_per_inst",
    "flushes",
    "flushes_per_inst",
    "mem_wait",
    "mem_wait_per_inst",
    "load_use",
    "load_use_per_inst",
    "reconfigs",
    "reconfig_penalty",
    "reconfig_penalty_per_switch",
    "energy",
    "energy_per_inst",
    "safety_faults",
    "phase",
    "final_mode",
    "timed_out",
    "arch_hash",
]

NUMERIC_FIELDS = {
    "cycles",
    "retired",
    "ipc_x1000",
    "stalls",
    "flushes",
    "mem_wait",
    "load_use",
    "reconfigs",
    "reconfig_penalty",
    "energy",
    "safety_faults",
    "timed_out",
}


def parse_result_line(line: str) -> dict[str, str] | None:
    if not line.startswith("RESULT "):
        return None

    row: dict[str, str] = {}
    for token in line.strip().split()[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        row[key] = value

    for field in NUMERIC_FIELDS:
        row[field] = str(int(row.get(field, "0")))

    cycles = int(row.get("cycles", "0"))
    retired = int(row.get("retired", "0"))
    stalls = int(row.get("stalls", "0"))
    flushes = int(row.get("flushes", "0"))
    mem_wait = int(row.get("mem_wait", "0"))
    load_use = int(row.get("load_use", "0"))
    reconfigs = int(row.get("reconfigs", "0"))
    reconfig_penalty = int(row.get("reconfig_penalty", "0"))
    energy = int(row.get("energy", "0"))
    ipc = retired / cycles if cycles else 0.0
    cpi = cycles / retired if retired else 0.0
    row["ipc"] = f"{ipc:.4f}"
    row["cpi"] = f"{cpi:.4f}"
    row["stalls_per_inst"] = f"{(stalls / retired) if retired else 0.0:.4f}"
    row["flushes_per_inst"] = f"{(flushes / retired) if retired else 0.0:.4f}"
    row["mem_wait_per_inst"] = f"{(mem_wait / retired) if retired else 0.0:.4f}"
    row["load_use_per_inst"] = f"{(load_use / retired) if retired else 0.0:.4f}"
    row["reconfig_penalty_per_switch"] = f"{(reconfig_penalty / reconfigs) if reconfigs else 0.0:.4f}"
    row["energy_per_inst"] = f"{(energy / retired) if retired else 0.0:.4f}"
    return row


def load_rows(log_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_result_line(line)
        if parsed:
            rows.append(parsed)
    return rows


def pct_change(new: float, baseline: float, higher_is_better: bool = True) -> float:
    if baseline == 0:
        return 0.0
    if higher_is_better:
        return ((new - baseline) / baseline) * 100.0
    return ((baseline - new) / baseline) * 100.0


def write_results(rows: list[dict[str, str]], result_csv: Path) -> None:
    result_csv.parent.mkdir(exist_ok=True)
    with result_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_improvements(rows: list[dict[str, str]], improvement_csv: Path) -> None:
    by_bench_mode = {(row["bench"], row["mode"]): row for row in rows}
    fields = [
        "bench",
        "normal_cycles",
        "adaptive_cycles",
        "cycle_reduction_pct",
        "normal_ipc",
        "adaptive_ipc",
        "ipc_improvement_pct",
        "normal_energy",
        "adaptive_energy",
        "energy_reduction_pct",
        "adaptive_reconfigs",
        "adaptive_reconfig_penalty",
    ]

    out_rows: list[dict[str, str]] = []
    benches = sorted({row["bench"] for row in rows})
    for bench in benches:
        normal = by_bench_mode.get((bench, "static_normal"))
        adaptive = by_bench_mode.get((bench, "adaptive_pipesense"))
        if not normal or not adaptive:
            continue

        normal_cycles = float(normal["cycles"])
        adaptive_cycles = float(adaptive["cycles"])
        normal_ipc = float(normal["ipc"])
        adaptive_ipc = float(adaptive["ipc"])
        normal_energy = float(normal["energy"])
        adaptive_energy = float(adaptive["energy"])

        out_rows.append(
            {
                "bench": bench,
                "normal_cycles": f"{normal_cycles:.0f}",
                "adaptive_cycles": f"{adaptive_cycles:.0f}",
                "cycle_reduction_pct": f"{pct_change(adaptive_cycles, normal_cycles, higher_is_better=False):.2f}",
                "normal_ipc": f"{normal_ipc:.4f}",
                "adaptive_ipc": f"{adaptive_ipc:.4f}",
                "ipc_improvement_pct": f"{pct_change(adaptive_ipc, normal_ipc):.2f}",
                "normal_energy": f"{normal_energy:.0f}",
                "adaptive_energy": f"{adaptive_energy:.0f}",
                "energy_reduction_pct": f"{pct_change(adaptive_energy, normal_energy, higher_is_better=False):.2f}",
                "adaptive_reconfigs": adaptive["reconfigs"],
                "adaptive_reconfig_penalty": adaptive["reconfig_penalty"],
            }
        )

    with improvement_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)


def write_oracle_gap(rows: list[dict[str, str]], oracle_gap_csv: Path) -> None:
    fields = [
        "bench",
        "best_fixed_mode",
        "best_fixed_cycles",
        "adaptive_cycles",
        "adaptive_gap_to_best_fixed_pct",
        "best_fixed_energy",
        "adaptive_energy",
        "adaptive_energy_gap_to_best_fixed_pct",
        "adaptive_safety_faults",
        "adaptive_timed_out",
    ]
    out_rows: list[dict[str, str]] = []
    benches = sorted({row["bench"] for row in rows})

    for bench in benches:
        bench_rows = [row for row in rows if row["bench"] == bench]
        fixed_rows = [
            row for row in bench_rows
            if row["mode"].startswith("fixed_") or row["mode"] == "static_normal"
        ]
        adaptive = next((row for row in bench_rows if row["mode"] == "adaptive_pipesense"), None)
        if not fixed_rows or not adaptive:
            continue

        best_fixed = min(fixed_rows, key=lambda row: int(row["cycles"]))
        best_cycles = float(best_fixed["cycles"])
        adaptive_cycles = float(adaptive["cycles"])
        best_energy = float(best_fixed["energy"])
        adaptive_energy = float(adaptive["energy"])
        out_rows.append(
            {
                "bench": bench,
                "best_fixed_mode": best_fixed["mode"],
                "best_fixed_cycles": f"{best_cycles:.0f}",
                "adaptive_cycles": f"{adaptive_cycles:.0f}",
                "adaptive_gap_to_best_fixed_pct": f"{pct_change(adaptive_cycles, best_cycles, higher_is_better=False):.2f}",
                "best_fixed_energy": f"{best_energy:.0f}",
                "adaptive_energy": f"{adaptive_energy:.0f}",
                "adaptive_energy_gap_to_best_fixed_pct": f"{pct_change(adaptive_energy, best_energy, higher_is_better=False):.2f}",
                "adaptive_safety_faults": adaptive["safety_faults"],
                "adaptive_timed_out": adaptive["timed_out"],
            }
        )

    with oracle_gap_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", default=str(DEFAULT_LOG), help="Simulation log to parse.")
    parser.add_argument("--out-dir", default=str(RESULTS), help="Directory for generated CSV files.")
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    log_path = Path(args.log)
    out_dir = Path(args.out_dir)
    result_csv = out_dir / "pipesense_results.csv"
    improvement_csv = out_dir / "adaptive_improvement.csv"
    oracle_gap_csv = out_dir / "oracle_gap.csv"
    if not log_path.exists():
        print(f"No simulation log found at {log_path}")
        return 1

    rows = load_rows(log_path)
    if not rows:
        print(f"No RESULT lines found in {log_path}")
        return 1

    write_results(rows, result_csv)
    write_improvements(rows, improvement_csv)
    write_oracle_gap(rows, oracle_gap_csv)
    print(f"Wrote {result_csv}")
    print(f"Wrote {improvement_csv}")
    print(f"Wrote {oracle_gap_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
