#!/usr/bin/env python3
"""Run the documented ASYNC'03 control-policy approximation and comparisons."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = RESULTS / "adaptive_baseline"
PRIMARY_FILES = [
    "pipesense_results.csv",
    "adaptive_improvement.csv",
    "oracle_gap.csv",
    "reference_model.csv",
    "benchmark_disassembly.txt",
]


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run(command: list[str]) -> None:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(command)}")


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(seeds: int, fuzz_ran: bool) -> None:
    comparison = load(OUT / "directed_comparison.csv")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "published_source": {
            "authors": "A. Efthymiou and J. D. Garside",
            "title": "Adaptive Pipeline Structures for Speculation Control",
            "venue": "ASYNC 2003",
            "doi": "10.1109/ASYNC.2003.1199165",
        },
        "implementation_scope": "architectural control-policy approximation; not an AMULET3 reproduction",
        "directed_workloads": [row["bench"] for row in comparison],
        "directed_command": ["python3", "scripts/run_adaptive_baseline.py", "--seeds", str(seeds)],
        "pipesense_policy": "adaptive PipeSense observer/controller with safe drain-before-switch",
        "comparison_policy": "CMP requests low-power; next branch requests normal; same safe drain and mode costs",
        "random_seed_range": f"1..{seeds}" if fuzz_ran else "not run",
        "shared_constraints": [
            "same RTL core, memories, workload programs, and mode timing model",
            "same directed workloads and random instruction streams",
            "same random seeds and simulation timeout",
            "same activity-energy proxy and transition counters",
        ],
        "warnings": [
            "The comparison is an architectural approximation, not a reproduction of asynchronous collapsible latches.",
            "All workload results are RTL simulation.",
            "Energy is an activity proxy in arbitrary units, not measured power or physical energy.",
        ],
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def directed_comparison(primary: list[dict[str, str]], async_rows: list[dict[str, str]]) -> None:
    by_primary = {(row["bench"], row["mode"]): row for row in primary}
    by_async = {(row["bench"], row["mode"]): row for row in async_rows}
    fields = [
        "bench", "static_normal_cycles", "fixed_branch_cycles", "fixed_memory_cycles",
        "fixed_hazard_cycles", "fixed_low_power_cycles", "oracle_mode", "oracle_cycles",
        "pipesense_cycles", "async03_approx_cycles", "pipesense_energy_proxy",
        "async03_approx_energy_proxy", "pipesense_transitions", "async03_approx_transitions",
        "pipesense_faults", "async03_approx_faults", "pipesense_timeouts", "async03_approx_timeouts",
    ]
    out: list[dict[str, str]] = []
    for bench in sorted({row["bench"] for row in primary}):
        fixed_modes = ["static_normal", "fixed_branch", "fixed_memory", "fixed_hazard", "fixed_low_power"]
        fixed = [by_primary[(bench, mode)] for mode in fixed_modes]
        oracle = min(fixed, key=lambda row: int(row["cycles"]))
        pipesense = by_primary[(bench, "adaptive_pipesense")]
        async03 = by_async[(bench, "adaptive_pipesense")]
        out.append(
            {
                "bench": bench,
                "static_normal_cycles": by_primary[(bench, "static_normal")]["cycles"],
                "fixed_branch_cycles": by_primary[(bench, "fixed_branch")]["cycles"],
                "fixed_memory_cycles": by_primary[(bench, "fixed_memory")]["cycles"],
                "fixed_hazard_cycles": by_primary[(bench, "fixed_hazard")]["cycles"],
                "fixed_low_power_cycles": by_primary[(bench, "fixed_low_power")]["cycles"],
                "oracle_mode": oracle["mode"],
                "oracle_cycles": oracle["cycles"],
                "pipesense_cycles": pipesense["cycles"],
                "async03_approx_cycles": async03["cycles"],
                "pipesense_energy_proxy": pipesense["energy"],
                "async03_approx_energy_proxy": async03["energy"],
                "pipesense_transitions": pipesense["reconfigs"],
                "async03_approx_transitions": async03["reconfigs"],
                "pipesense_faults": pipesense["safety_faults"],
                "async03_approx_faults": async03["safety_faults"],
                "pipesense_timeouts": pipesense["timed_out"],
                "async03_approx_timeouts": async03["timed_out"],
            }
        )
    write_rows(OUT / "directed_comparison.csv", out, fields)


def fuzz_comparison() -> None:
    primary_path = RESULTS / "safety" / "fuzz_summary.csv"
    async_path = OUT / "safety" / "fuzz_summary.csv"
    if not primary_path.exists() or not async_path.exists():
        raise RuntimeError("Both PipeSense and ASYNC'03 fuzz summaries are required")
    primary = {(row["seed"], row["mode"]): row for row in load(primary_path)}
    async_rows = {(row["seed"], row["mode"]): row for row in load(async_path)}
    fields = [
        "seed", "pipesense_cycles", "async03_approx_cycles", "pipesense_energy_proxy",
        "async03_approx_energy_proxy", "pipesense_transitions", "async03_approx_transitions",
        "pipesense_faults", "async03_approx_faults", "pipesense_timeouts", "async03_approx_timeouts",
    ]
    rows: list[dict[str, str]] = []
    seeds = sorted({int(seed) for seed, mode in primary if mode == "adaptive_pipesense"})
    for seed_value in seeds:
        seed = str(seed_value)
        left = primary[(seed, "adaptive_pipesense")]
        right = async_rows[(seed, "adaptive_pipesense")]
        rows.append(
            {
                "seed": seed,
                "pipesense_cycles": left["cycles"],
                "async03_approx_cycles": right["cycles"],
                "pipesense_energy_proxy": left["energy"],
                "async03_approx_energy_proxy": right["energy"],
                "pipesense_transitions": left["reconfigs"],
                "async03_approx_transitions": right["reconfigs"],
                "pipesense_faults": left["safety_faults"],
                "async03_approx_faults": right["safety_faults"],
                "pipesense_timeouts": left["timed_out"],
                "async03_approx_timeouts": right["timed_out"],
            }
        )
    write_rows(OUT / "fuzz_comparison.csv", rows, fields)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--skip-fuzz", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    run([sys.executable, str(ROOT / "scripts" / "run_sim.py"), "--tag", "baseline_primary"])
    primary = load(RESULTS / "pipesense_results.csv")
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for name in PRIMARY_FILES:
            source = RESULTS / name
            if source.exists():
                shutil.copy2(source, tmp / name)
        try:
            run(
                [sys.executable, str(ROOT / "scripts" / "run_sim.py"),
                 "--controller-policy", "async03", "--tag", "adaptive_baseline_async03"]
            )
            async_rows = load(RESULTS / "pipesense_results.csv")
            for row in async_rows:
                if row["mode"] == "adaptive_pipesense":
                    row["mode"] = "adaptive_async03_approx"
            write_rows(OUT / "directed_raw.csv", async_rows, list(async_rows[0]))
            shutil.copy2(RESULTS / "sim_output_adaptive_baseline_async03.txt", OUT / "directed_raw.log")
            directed_comparison(primary, load(RESULTS / "pipesense_results.csv"))
        finally:
            for name in PRIMARY_FILES:
                source = tmp / name
                if source.exists():
                    shutil.copy2(source, RESULTS / name)

    if not args.skip_fuzz:
        run(
            [sys.executable, str(ROOT / "verif" / "fuzz_runner.py"),
             "--seeds", str(args.seeds), "--controller-policy", "async03",
             "--output-dir", str(OUT / "safety")]
        )
        fuzz_comparison()
    write_manifest(args.seeds, not args.skip_fuzz)
    print(f"Wrote adaptive-baseline evidence under {OUT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
