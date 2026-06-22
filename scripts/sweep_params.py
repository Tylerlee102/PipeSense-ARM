#!/usr/bin/env python3
"""Run a small PipeSense parameter sweep through scripts/run_sim.py."""

from __future__ import annotations

import csv
import itertools
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SWEEP_CSV = RESULTS / "sweep_summary.csv"
DEFAULT_LOG = RESULTS / "sim_output.txt"
SWEEP_DIR = RESULTS / "sweeps"
GENERATED_TABLES = [
    "pipesense_results.csv",
    "adaptive_improvement.csv",
    "oracle_gap.csv",
    "reference_model.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", default=os.environ.get("IVERILOG", ""), help="Path to iverilog executable.")
    parser.add_argument("--vvp", default=os.environ.get("VVP", ""), help="Path to vvp executable.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    iverilog = args.iverilog or shutil.which("iverilog")
    vvp = args.vvp or shutil.which("vvp")

    if not iverilog or not vvp:
        print("Icarus Verilog was not found; install iverilog/vvp before running sweeps.")
        print("Or pass explicit paths: python scripts/sweep_params.py --iverilog <path> --vvp <path>")
        return 2

    windows = [16, 32, 64]
    residencies = [8, 24, 48]
    summary_rows: list[dict[str, str]] = []
    restore_default_tables = DEFAULT_LOG.exists()

    for window, residency in itertools.product(windows, residencies):
        tag = f"w{window}_r{residency}"
        tag_dir = SWEEP_DIR / tag
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_sim.py"),
            "--obs-window",
            str(window),
            "--min-residency",
            str(residency),
            "--tag",
            tag,
        ]
        if args.iverilog:
            cmd.extend(["--iverilog", args.iverilog])
        if args.vvp:
            cmd.extend(["--vvp", args.vvp])
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        print(proc.stdout)
        if proc.returncode == 0:
            tag_dir.mkdir(parents=True, exist_ok=True)
            sim_log = RESULTS / f"sim_output_{tag}.txt"
            if sim_log.exists():
                shutil.copy2(sim_log, tag_dir / sim_log.name)
            for table in GENERATED_TABLES:
                table_path = RESULTS / table
                if table_path.exists():
                    shutil.copy2(table_path, tag_dir / table)
        summary_rows.append(
            {
                "obs_window": str(window),
                "min_residency": str(residency),
                "return_code": str(proc.returncode),
                "log": str(RESULTS / f"sim_output_{tag}.txt"),
                "result_csv": str(tag_dir / "pipesense_results.csv"),
            }
        )
        if proc.returncode != 0:
            break

    RESULTS.mkdir(exist_ok=True)
    with SWEEP_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["obs_window", "min_residency", "return_code", "log", "result_csv"],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    if restore_default_tables:
        restore_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "analyze_results.py"),
            str(DEFAULT_LOG),
        ]
        restore_proc = subprocess.run(
            restore_cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(restore_proc.stdout)
        if restore_proc.returncode != 0:
            print("Default result-table restore failed after sweep.")
            return 1

    print(f"Wrote {SWEEP_CSV}")
    return 0 if all(row["return_code"] == "0" for row in summary_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
