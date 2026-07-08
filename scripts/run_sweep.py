#!/usr/bin/env python3
"""Run sweep-based PipeSense evaluation across windows, thresholds, and residency."""

from __future__ import annotations

import argparse
import csv
import itertools
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SWEEP_ROOT = RESULTS / "sweeps"
SWEEP_RUNS_CSV = RESULTS / "sweep_runs.csv"
SWEEP_RESULTS_CSV = RESULTS / "sweep_results.csv"
SWEEP_COMPARISON_CSV = RESULTS / "sweep_adaptive_vs_fixed.csv"

GENERATED_TABLES = [
    "pipesense_results.csv",
    "adaptive_improvement.csv",
    "oracle_gap.csv",
    "reference_model.csv",
]

THRESHOLD_PROFILES = {
    "tight": {
        "branch_threshold": 4,
        "mem_threshold": 4,
        "load_use_threshold": 3,
        "frontend_threshold": 6,
        "idle_threshold": 4,
    },
    "medium": {
        "branch_threshold": 8,
        "mem_threshold": 8,
        "load_use_threshold": 6,
        "frontend_threshold": 10,
        "idle_threshold": 8,
    },
    "loose": {
        "branch_threshold": 12,
        "mem_threshold": 12,
        "load_use_threshold": 9,
        "frontend_threshold": 16,
        "idle_threshold": 12,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", default=os.environ.get("IVERILOG", ""), help="Path to iverilog executable.")
    parser.add_argument("--vvp", default=os.environ.get("VVP", ""), help="Path to vvp executable.")
    parser.add_argument("--windows", default="16,32,64", help="Comma-separated observer window sizes.")
    parser.add_argument("--residencies", default="8,24,48", help="Comma-separated minimum residency depths.")
    parser.add_argument("--threshold-profiles", default="tight,medium,loose", help="Comma-separated threshold profiles.")
    parser.add_argument("--seeds", default="0", help="Comma-separated seeds for randomized cells; deterministic suite uses seed 0.")
    parser.add_argument("--max-configs", type=int, default=0, help="Optional smoke-test cap on config count.")
    parser.add_argument("--keep-going", action="store_true", help="Continue after a failing configuration.")
    return parser.parse_args()


def parse_int_list(text: str) -> list[int]:
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def parse_str_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def pct_change(new: float, baseline: float, higher_is_better: bool = True) -> float:
    if baseline == 0:
        return 0.0
    if higher_is_better:
        return ((new - baseline) / baseline) * 100.0
    return ((baseline - new) / baseline) * 100.0


def run_config(
    window: int,
    residency: int,
    profile_name: str,
    seed: int,
    args: argparse.Namespace,
) -> tuple[int, Path, str]:
    profile = THRESHOLD_PROFILES[profile_name]
    tag = f"w{window}_r{residency}_th{profile_name}_seed{seed}"
    tag_dir = SWEEP_ROOT / tag
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_sim.py"),
        "--obs-window",
        str(window),
        "--min-residency",
        str(residency),
        "--branch-threshold",
        str(profile["branch_threshold"]),
        "--mem-threshold",
        str(profile["mem_threshold"]),
        "--load-use-threshold",
        str(profile["load_use_threshold"]),
        "--frontend-threshold",
        str(profile["frontend_threshold"]),
        "--idle-threshold",
        str(profile["idle_threshold"]),
        "--tag",
        tag,
    ]
    if args.iverilog:
        cmd.extend(["--iverilog", args.iverilog])
    if args.vvp:
        cmd.extend(["--vvp", args.vvp])

    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    tag_dir.mkdir(parents=True, exist_ok=True)
    (tag_dir / "run_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    sim_log = RESULTS / f"sim_output_{tag}.txt"
    if sim_log.exists():
        shutil.copy2(sim_log, tag_dir / sim_log.name)
    for table in GENERATED_TABLES:
        table_path = RESULTS / table
        if table_path.exists():
            shutil.copy2(table_path, tag_dir / table)
    return proc.returncode, tag_dir, tag


def read_result_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def annotate_rows(
    rows: list[dict[str, str]],
    window: int,
    residency: int,
    profile_name: str,
    seed: int,
    tag: str,
) -> list[dict[str, str]]:
    out = []
    for row in rows:
        annotated = dict(row)
        annotated.update(
            {
                "sweep_tag": tag,
                "obs_window": str(window),
                "min_residency": str(residency),
                "threshold_profile": profile_name,
                "seed": str(seed),
            }
        )
        out.append(annotated)
    return out


def compare_adaptive(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    comparisons: list[dict[str, str]] = []
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (
            row["sweep_tag"],
            row["obs_window"],
            row["min_residency"],
            row["threshold_profile"],
            row["seed"],
        )
        grouped.setdefault(key, []).append(row)

    for key, config_rows in grouped.items():
        by_bench_mode = {(row["bench"], row["mode"]): row for row in config_rows}
        benches = sorted({row["bench"] for row in config_rows})
        for bench in benches:
            adaptive = by_bench_mode.get((bench, "adaptive_pipesense"))
            if not adaptive:
                continue
            for baseline_mode in [
                "static_normal",
                "fixed_branch",
                "fixed_memory",
                "fixed_hazard",
                "fixed_low_power",
            ]:
                baseline = by_bench_mode.get((bench, baseline_mode))
                if not baseline:
                    continue
                adaptive_cycles = float(adaptive["cycles"])
                baseline_cycles = float(baseline["cycles"])
                adaptive_ipc = float(adaptive["ipc"])
                baseline_ipc = float(baseline["ipc"])
                adaptive_energy = float(adaptive["energy"])
                baseline_energy = float(baseline["energy"])
                comparisons.append(
                    {
                        "sweep_tag": key[0],
                        "obs_window": key[1],
                        "min_residency": key[2],
                        "threshold_profile": key[3],
                        "seed": key[4],
                        "bench": bench,
                        "baseline_mode": baseline_mode,
                        "adaptive_cycles": f"{adaptive_cycles:.0f}",
                        "baseline_cycles": f"{baseline_cycles:.0f}",
                        "cycle_reduction_pct": f"{pct_change(adaptive_cycles, baseline_cycles, False):.2f}",
                        "adaptive_wins_cycles": str(adaptive_cycles < baseline_cycles),
                        "adaptive_ipc": f"{adaptive_ipc:.4f}",
                        "baseline_ipc": f"{baseline_ipc:.4f}",
                        "ipc_improvement_pct": f"{pct_change(adaptive_ipc, baseline_ipc):.2f}",
                        "adaptive_energy": f"{adaptive_energy:.0f}",
                        "baseline_energy": f"{baseline_energy:.0f}",
                        "energy_reduction_pct": f"{pct_change(adaptive_energy, baseline_energy, False):.2f}",
                    }
                )
    return comparisons


def write_csv(path: Path, rows: list[dict[str, str]], preferred_fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(preferred_fields)
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def snapshot_generated_tables() -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for table in GENERATED_TABLES:
        path = RESULTS / table
        if path.exists():
            snapshot[table] = path.read_bytes()
    return snapshot


def restore_generated_tables(snapshot: dict[str, bytes]) -> None:
    for table, contents in snapshot.items():
        (RESULTS / table).write_bytes(contents)


def write_tool_missing_note(iverilog: str, vvp: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    note = RESULTS / "sweep_tool_unavailable.md"
    note.write_text(
        "# Sweep Not Run\n\n"
        "Icarus Verilog was not found, so the sweep could not run in this environment.\n\n"
        f"- iverilog: `{iverilog or 'not found'}`\n"
        f"- vvp: `{vvp or 'not found'}`\n\n"
        "Install `iverilog` and `vvp`, then rerun `python scripts/run_sweep.py`.\n",
        encoding="utf-8",
    )
    print(f"Wrote {note}")


def main() -> int:
    args = parse_args()
    iverilog = args.iverilog or shutil.which("iverilog") or ""
    vvp = args.vvp or shutil.which("vvp") or ""
    if not iverilog or not vvp:
        write_tool_missing_note(iverilog, vvp)
        return 2

    windows = parse_int_list(args.windows)
    residencies = parse_int_list(args.residencies)
    profiles = parse_str_list(args.threshold_profiles)
    seeds = parse_int_list(args.seeds)
    unknown = [profile for profile in profiles if profile not in THRESHOLD_PROFILES]
    if unknown:
        print(f"Unknown threshold profiles: {', '.join(unknown)}")
        return 1

    generated_table_snapshot = snapshot_generated_tables()
    run_rows: list[dict[str, str]] = []
    all_results: list[dict[str, str]] = []
    configs = list(itertools.product(windows, residencies, profiles, seeds))
    if args.max_configs:
        configs = configs[: args.max_configs]

    for window, residency, profile_name, seed in configs:
        return_code, tag_dir, tag = run_config(window, residency, profile_name, seed, args)
        profile = THRESHOLD_PROFILES[profile_name]
        run_rows.append(
            {
                "sweep_tag": tag,
                "obs_window": str(window),
                "min_residency": str(residency),
                "threshold_profile": profile_name,
                "branch_threshold": str(profile["branch_threshold"]),
                "mem_threshold": str(profile["mem_threshold"]),
                "load_use_threshold": str(profile["load_use_threshold"]),
                "frontend_threshold": str(profile["frontend_threshold"]),
                "idle_threshold": str(profile["idle_threshold"]),
                "seed": str(seed),
                "return_code": str(return_code),
                "result_csv": str(tag_dir / "pipesense_results.csv"),
            }
        )
        rows = read_result_rows(tag_dir / "pipesense_results.csv")
        all_results.extend(annotate_rows(rows, window, residency, profile_name, seed, tag))
        print(f"{tag}: return_code={return_code} rows={len(rows)}")
        if return_code != 0 and not args.keep_going:
            break

    comparisons = compare_adaptive(all_results)
    write_csv(SWEEP_RUNS_CSV, run_rows, [
        "sweep_tag",
        "obs_window",
        "min_residency",
        "threshold_profile",
        "seed",
        "return_code",
        "result_csv",
    ])
    write_csv(SWEEP_RESULTS_CSV, all_results, [
        "sweep_tag",
        "obs_window",
        "min_residency",
        "threshold_profile",
        "seed",
    ])
    write_csv(SWEEP_COMPARISON_CSV, comparisons, [
        "sweep_tag",
        "obs_window",
        "min_residency",
        "threshold_profile",
        "seed",
        "bench",
        "baseline_mode",
    ])
    restore_generated_tables(generated_table_snapshot)

    losing = [row for row in comparisons if row["adaptive_wins_cycles"] != "True"]
    print(f"Wrote {SWEEP_RUNS_CSV}")
    print(f"Wrote {SWEEP_RESULTS_CSV}")
    print(f"Wrote {SWEEP_COMPARISON_CSV}")
    print(f"Adaptive non-win cells recorded: {len(losing)}")
    return 0 if all(row["return_code"] == "0" for row in run_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
