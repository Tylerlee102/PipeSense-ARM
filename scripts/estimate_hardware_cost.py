#!/usr/bin/env python3
"""Produce a transparent first-order hardware cost estimate for PipeSense."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = RESULTS / "hardware_cost_estimate.csv"


ROWS = [
    {
        "component": "pipeline_observer",
        "estimated_ff_bits": "35",
        "estimated_comparators": "12",
        "estimated_adders": "7",
        "notes": "Threshold-saturating counters at the integrated 32-cycle window, plus phase/window state; excludes routing and constants.",
    },
    {
        "component": "adaptive_controller",
        "estimated_ff_bits": "15",
        "estimated_comparators": "4",
        "estimated_adders": "2",
        "notes": "Six-bit residency and two-bit stability counters, mode history/request, and request state.",
    },
    {
        "component": "reconfig_unit",
        "estimated_ff_bits": "8",
        "estimated_comparators": "2",
        "estimated_adders": "0",
        "notes": "Current/latched mode and active/done state; performance counters own reconfiguration accounting.",
    },
    {
        "component": "safety_monitor_sim",
        "estimated_ff_bits": "193",
        "estimated_comparators": "4",
        "estimated_adders": "1",
        "notes": "Simulation/artifact monitor for instruction tags and safety faults; not part of a minimal synthesized design.",
    },
]


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["component", "estimated_ff_bits", "estimated_comparators", "estimated_adders", "notes"],
        )
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"Wrote {OUT}")
    print("This is an analytical estimate, not a synthesis report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
