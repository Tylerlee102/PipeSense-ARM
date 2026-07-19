#!/usr/bin/env python3
"""Run and archive the bounded PipeSense-Ibex reconfiguration proof."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "formal" / "results" / "ibex_reconfiguration"
RESULTS = ROOT / "results" / "ibex" / "formal"


def main() -> int:
    command = ["sby", "-f", "-d", str(WORK),
               str(ROOT / "formal" / "ibex_reconfiguration.sby")]
    print("+", subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    RESULTS.mkdir(parents=True, exist_ok=True)
    logfile = WORK / "logfile.txt"
    if logfile.is_file():
        shutil.copy2(logfile, RESULTS / "ibex_reconfiguration.log")
    summary = {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "engine": "smtbmc cvc4",
        "mode": "bounded model check",
        "depth": 8,
        "scope": [
            "drain fetch hold",
            "mode visibility",
            "empty-pipeline mode commit",
            "issued-retired token accounting under a valid-retirement assumption",
            "no in-flight token at a committed mode switch",
        ],
        "whole_core_unbounded_proof": False,
        "returncode": result.returncode,
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
