#!/usr/bin/env python3
"""Run PipeSense ablation variants and summarize adaptive-mode effects."""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
ABLATIONS = RESULTS / "ablations"

CSV_FILES = [
    "pipesense_results.csv",
    "adaptive_improvement.csv",
    "oracle_gap.csv",
    "reference_model.csv",
    "benchmark_disassembly.txt",
]


@dataclass(frozen=True)
class Variant:
    key: str
    label: str
    args: tuple[str, ...]


VARIANTS = [
    Variant("full_adaptive", "Full adaptive PipeSense", ()),
    Variant("observer_disabled", "Observer disabled", ("--disable-observer",)),
    Variant("controller_disabled", "Controller disabled", ("--disable-controller",)),
]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_variant(variant: Variant) -> dict[str, float | int | str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_sim.py"),
        "--tag",
        f"ablation_{variant.key}",
        *variant.args,
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Ablation {variant.key} failed with exit code {proc.returncode}")
    for line in proc.stdout.splitlines():
        if (
            line.startswith("SUMMARY ")
            or line.startswith("Wrote ")
            or line.endswith("passed.")
        ):
            print(f"{variant.key}: {line}")

    variant_dir = ABLATIONS / variant.key
    variant_dir.mkdir(parents=True, exist_ok=True)
    for filename in CSV_FILES:
        source = RESULTS / filename
        if source.exists():
            shutil.copy2(source, variant_dir / filename)

    rows = load_csv(RESULTS / "pipesense_results.csv")
    adaptive = [row for row in rows if row["mode"] == "adaptive_pipesense"]
    return {
        "ablation": variant.key,
        "label": variant.label,
        "total_adaptive_cycles": sum(int(row["cycles"]) for row in adaptive),
        "total_adaptive_energy": sum(int(row["energy"]) for row in adaptive),
        "total_reconfigs": sum(int(row["reconfigs"]) for row in adaptive),
        "total_reconfig_penalty": sum(int(row["reconfig_penalty"]) for row in adaptive),
        "total_safety_faults": sum(int(row["safety_faults"]) for row in adaptive),
        "total_timeouts": sum(int(row["timed_out"]) for row in adaptive),
    }


def pct_change(value: float, baseline: float) -> str:
    if baseline == 0:
        return "0.00"
    return f"{((value - baseline) / baseline) * 100.0:.2f}"


def write_summary(metrics: list[dict[str, float | int | str]]) -> None:
    baseline = metrics[0]
    baseline_cycles = float(baseline["total_adaptive_cycles"])
    baseline_energy = float(baseline["total_adaptive_energy"])
    fields = [
        "ablation",
        "label",
        "total_adaptive_cycles",
        "cycle_change_vs_full_pct",
        "total_adaptive_energy",
        "energy_change_vs_full_pct",
        "total_reconfigs",
        "total_reconfig_penalty",
        "total_safety_faults",
        "total_timeouts",
    ]
    out_rows: list[dict[str, str]] = []
    for row in metrics[1:]:
        out_rows.append(
            {
                "ablation": str(row["ablation"]),
                "label": str(row["label"]),
                "total_adaptive_cycles": str(row["total_adaptive_cycles"]),
                "cycle_change_vs_full_pct": pct_change(float(row["total_adaptive_cycles"]), baseline_cycles),
                "total_adaptive_energy": str(row["total_adaptive_energy"]),
                "energy_change_vs_full_pct": pct_change(float(row["total_adaptive_energy"]), baseline_energy),
                "total_reconfigs": str(row["total_reconfigs"]),
                "total_reconfig_penalty": str(row["total_reconfig_penalty"]),
                "total_safety_faults": str(row["total_safety_faults"]),
                "total_timeouts": str(row["total_timeouts"]),
            }
        )
    zero_cost_cycles = int(baseline["total_adaptive_cycles"]) - int(baseline["total_reconfig_penalty"])
    out_rows.append(
        {
            "ablation": "zero_cost_reconfig",
            "label": "Zero-cost reconfiguration idealization",
            "total_adaptive_cycles": str(zero_cost_cycles),
            "cycle_change_vs_full_pct": pct_change(float(zero_cost_cycles), baseline_cycles),
            "total_adaptive_energy": str(baseline["total_adaptive_energy"]),
            "energy_change_vs_full_pct": "0.00",
            "total_reconfigs": str(baseline["total_reconfigs"]),
            "total_reconfig_penalty": "0",
            "total_safety_faults": str(baseline["total_safety_faults"]),
            "total_timeouts": str(baseline["total_timeouts"]),
        }
    )

    out_path = RESULTS / "ablation_summary.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {out_path}")

    for row in out_rows:
        print(
            "{ablation}: cycles={total_adaptive_cycles} "
            "cycle_change={cycle_change_vs_full_pct}% "
            "reconfigs={total_reconfigs} penalty={total_reconfig_penalty} "
            "safety_faults={total_safety_faults} timeouts={total_timeouts}".format(**row)
        )


def restore_baseline() -> None:
    baseline_dir = ABLATIONS / "full_adaptive"
    for filename in CSV_FILES:
        source = baseline_dir / filename
        if source.exists():
            shutil.copy2(source, RESULTS / filename)


def main() -> int:
    ABLATIONS.mkdir(parents=True, exist_ok=True)
    metrics = [run_variant(variant) for variant in VARIANTS]
    write_summary(metrics)
    restore_baseline()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
