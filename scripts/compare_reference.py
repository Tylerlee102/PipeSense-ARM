#!/usr/bin/env python3
"""Compare HDL simulation metrics against the sequential ISA reference model."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise RuntimeError(f"Missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", default=str(RESULTS / "pipesense_results.csv"))
    parser.add_argument("--reference-csv", default=str(RESULTS / "reference_model.csv"))
    parser.add_argument("--allow-subset", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sim_rows = load_csv(Path(args.results_csv))
    ref_rows = load_csv(Path(args.reference_csv))
    ref_by_bench = {row["bench"]: row for row in ref_rows}

    failures: list[str] = []
    for row in sim_rows:
        bench = row["bench"]
        ref = ref_by_bench.get(bench)
        if ref is None:
            failures.append(f"Missing reference row for bench={bench}")
            continue

        sim_retired = int(row["retired"])
        ref_retired = int(ref["retired"])
        if sim_retired != ref_retired:
            failures.append(
                f"Retired mismatch bench={bench} mode={row['mode']} "
                f"sim={sim_retired} reference={ref_retired}"
            )
        sim_arch_hash = row.get("arch_hash", "").lower()
        ref_arch_hash = ref.get("arch_hash", "").lower()
        if sim_arch_hash and ref_arch_hash and sim_arch_hash != ref_arch_hash:
            failures.append(
                f"Architectural-state mismatch bench={bench} mode={row['mode']} "
                f"sim={sim_arch_hash} reference={ref_arch_hash}"
            )
        elif not args.allow_subset and not sim_arch_hash:
            failures.append(f"Missing architectural hash bench={bench} mode={row['mode']}")

    if not args.allow_subset:
        sim_benches = {row["bench"] for row in sim_rows}
        ref_benches = set(ref_by_bench)
        missing = sorted(ref_benches - sim_benches)
        if missing:
            failures.append("Simulation results missing reference benchmarks: " + ", ".join(missing))

    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1

    print("Reference comparison passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
