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
        "estimated_ff_bits": "228",
        "estimated_comparators": "5",
        "estimated_adders": "7",
        "notes": "Seven 32-bit counters plus phase/window bits; excludes routing and threshold constants.",
    },
    {
        "component": "adaptive_controller",
        "estimated_ff_bits": "31",
        "estimated_comparators": "4",
        "estimated_adders": "2",
        "notes": "Residency counter, stable counter, desired/requested modes, and request state.",
    },
    {
        "component": "reconfig_unit",
        "estimated_ff_bits": "104",
        "estimated_comparators": "2",
        "estimated_adders": "3",
        "notes": "Mode registers, active counter, total reconfiguration count, and penalty counter.",
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
