#!/usr/bin/env python3
"""Run the repository's bounded SymbiYosys safety jobs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOBS = [
    ("reconfig_unit", ROOT / "formal" / "reconfig_unit.sby"),
    ("token_conservation", ROOT / "formal" / "token_conservation.sby"),
    (
        "no_double_commit_across_mode_switch",
        ROOT / "formal" / "no_double_commit_across_mode_switch.sby",
    ),
]


def main() -> int:
    sby = shutil.which("sby")
    if not sby:
        print("SymbiYosys (sby) was not found. Use the repository Docker image or install sby.")
        return 2

    for name, config in JOBS:
        output_dir = ROOT / "formal" / "results" / name
        proc = subprocess.run(
            [sby, "-f", "-d", str(output_dir), str(config)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(proc.stdout)
        if proc.returncode != 0:
            print(f"Formal job failed: {name}")
            return proc.returncode
        print(f"Formal job passed: {name}")

    print(f"Formal summary: {len(JOBS)} jobs passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
