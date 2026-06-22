#!/usr/bin/env python3
"""Validate PipeSense simulation CSVs before using them as paper evidence."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

EXPECTED_BENCHES = {
    "arithmetic_heavy",
    "branch_heavy",
    "memory_heavy",
    "load_use_heavy",
    "mixed_control",
    "tiny_fir",
}

EXPECTED_MODES = {
    "static_normal",
    "fixed_branch",
    "fixed_memory",
    "fixed_hazard",
    "fixed_low_power",
    "adaptive_pipesense",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise RuntimeError(f"Missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def int_field(row: dict[str, str], field: str) -> int:
    try:
        return int(row[field])
    except Exception as exc:
        raise RuntimeError(f"Invalid integer field {field} in row {row}") from exc


def validate_results(rows: list[dict[str, str]], allow_subset: bool) -> None:
    benches = {row["bench"] for row in rows}
    modes = {row["mode"] for row in rows}

    if allow_subset:
        missing_modes = sorted(EXPECTED_MODES - modes)
        if missing_modes:
            raise RuntimeError("Subset validation still requires all modes; missing " + ", ".join(missing_modes))
    else:
        missing_benches = sorted(EXPECTED_BENCHES - benches)
        missing_modes = sorted(EXPECTED_MODES - modes)
        if missing_benches:
            raise RuntimeError("Missing benchmarks: " + ", ".join(missing_benches))
        if missing_modes:
            raise RuntimeError("Missing modes: " + ", ".join(missing_modes))

    expected_rows = len(benches) * len(EXPECTED_MODES)
    if len(rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} result rows, found {len(rows)}")

    by_key = {(row["bench"], row["mode"]): row for row in rows}
    for bench in benches:
        for mode in EXPECTED_MODES:
            if (bench, mode) not in by_key:
                raise RuntimeError(f"Missing row for bench={bench} mode={mode}")

    for row in rows:
        if int_field(row, "timed_out") != 0:
            raise RuntimeError(f"Timed out row: {row}")
        if int_field(row, "safety_faults") != 0:
            raise RuntimeError(f"Safety fault row: {row}")
        if not allow_subset and not row.get("arch_hash"):
            raise RuntimeError(f"Missing architectural hash in row: {row}")
        if int_field(row, "retired") <= 0:
            raise RuntimeError(f"No retired instructions in row: {row}")
        if int_field(row, "cycles") <= 0:
            raise RuntimeError(f"Nonpositive cycle count in row: {row}")


def validate_oracle(rows: list[dict[str, str]], benches: set[str]) -> None:
    oracle_benches = {row["bench"] for row in rows}
    if oracle_benches != benches:
        raise RuntimeError(
            "Oracle rows do not match result benches: "
            f"results={sorted(benches)} oracle={sorted(oracle_benches)}"
        )
    for row in rows:
        if row["best_fixed_mode"] not in EXPECTED_MODES - {"adaptive_pipesense"}:
            raise RuntimeError(f"Invalid oracle best fixed mode: {row}")
        if row["adaptive_safety_faults"] != "0":
            raise RuntimeError(f"Oracle row contains adaptive safety fault: {row}")
        if row["adaptive_timed_out"] != "0":
            raise RuntimeError(f"Oracle row contains adaptive timeout: {row}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default=str(RESULTS), help="Directory containing result CSV files.")
    parser.add_argument("--allow-subset", action="store_true", help="Allow a subset of benchmarks for fixtures.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = Path(args.results_dir)
    rows = load_csv(results_dir / "pipesense_results.csv")
    oracle_rows = load_csv(results_dir / "oracle_gap.csv")
    validate_results(rows, allow_subset=args.allow_subset)
    validate_oracle(oracle_rows, {row["bench"] for row in rows})
    print("Result CSV validation passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
