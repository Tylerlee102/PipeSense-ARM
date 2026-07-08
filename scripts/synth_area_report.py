#!/usr/bin/env python3
"""Run/parse a generic Yosys area proxy for PipeSense-ARM."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "synth"
TCL = ROOT / "synth" / "yosys_synth.tcl"
SUMMARY_CSV = RESULTS / "area_summary.csv"

REPORTS = {
    "arm_like_core": RESULTS / "arm_like_core_yosys_stat.txt",
    "pipeline_observer": RESULTS / "pipeline_observer_yosys_stat.txt",
    "adaptive_controller": RESULTS / "adaptive_controller_yosys_stat.txt",
    "reconfig_unit": RESULTS / "reconfig_unit_yosys_stat.txt",
    "pipesense_integrated_core": RESULTS / "pipesense_integrated_core_yosys_stat.txt",
}

NUMBER_RE = re.compile(r"^\s*(?P<name>Number of \S+(?: \S+)*)\s*:\s*(?P<value>[0-9]+)")
COUNT_RE = re.compile(
    r"^\s*(?P<value>[0-9]+)\s+"
    r"(?P<name>wires|wire bits|public wires|public wire bits|memories|memory bits|processes|cells)\s*$"
)
CELL_RE = re.compile(r"^\s*(?P<cell>\$_?[A-Za-z0-9_]+)\s+(?P<count>[0-9]+)\s*$")


def validate_synth_script() -> None:
    if not TCL.exists():
        raise RuntimeError(f"Missing Yosys script: {TCL}")
    tcl = TCL.read_text(encoding="utf-8").replace("\\", "/")
    if "read_verilog synth/yosys_area_proxy.v" not in tcl:
        raise RuntimeError("Yosys script must read synth/yosys_area_proxy.v.")
    forbidden_terms = [
        "read_verilog rtl/",
        "read_verilog -sv rtl/",
        "rtl/hazard_unit.sv",
        "rtl/arm_like_core.sv",
        "shell mkdir",
    ]
    found_forbidden = [term for term in forbidden_terms if term in tcl]
    if found_forbidden:
        raise RuntimeError(
            "Yosys script must not parse full SystemVerilog RTL; found "
            + ", ".join(found_forbidden)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yosys", default=os.environ.get("YOSYS", ""), help="Path to yosys executable.")
    parser.add_argument("--parse-only", action="store_true", help="Parse existing reports without running Yosys.")
    return parser.parse_args()


def run_yosys(yosys: str) -> tuple[int, str]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [yosys, "-q", "-s", str(TCL)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (RESULTS / "yosys_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    return proc.returncode, proc.stdout


def parse_report(path: Path) -> dict[str, int]:
    metrics: dict[str, int] = {}
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        number = NUMBER_RE.match(line)
        if number:
            key = number.group("name").lower().replace(" ", "_")
            metrics[key] = int(number.group("value"))
            continue
        count = COUNT_RE.match(line)
        if count:
            key = "number_of_" + count.group("name").lower().replace(" ", "_")
            metrics[key] = int(count.group("value"))
            continue
        cell = CELL_RE.match(line)
        if cell:
            metrics[f"cell_{cell.group('cell')}"] = int(cell.group("count"))
    return metrics


def write_tool_missing_note(yosys: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    note = RESULTS / "yosys_tool_unavailable.md"
    note.write_text(
        "# Yosys Synthesis Not Run\n\n"
        "Yosys was not found, so the generic synthesis pass could not run in "
        "this environment.\n\n"
        f"- yosys: `{yosys or 'not found'}`\n\n"
        "Install Yosys, then rerun `python scripts/synth_area_report.py`.\n",
        encoding="utf-8",
    )
    print(f"Wrote {note}")


def write_yosys_failure_summary(stdout: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    failure_note = RESULTS / "yosys_failed.md"
    failure_note.write_text(
        "# Yosys Synthesis Proxy Failed\n\n"
        "Yosys was available, but the generic synthesis proxy did not complete. "
        "The workflow records this as an explicit artifact limitation instead "
        "of silently omitting synthesis evidence.\n\n"
        "See `yosys_stdout.txt` for the full log.\n\n"
        "Last log lines:\n\n"
        "```text\n"
        + "\n".join(stdout.splitlines()[-40:])
        + "\n```\n",
        encoding="utf-8",
    )
    fields = [
        "module",
        "report",
        "number_of_wires",
        "number_of_wire_bits",
        "number_of_public_wires",
        "number_of_public_wire_bits",
        "number_of_memories",
        "number_of_memory_bits",
        "number_of_processes",
        "number_of_cells",
        "overhead_vs_core_pct",
        "status",
    ]
    rows = [
        {
            "module": "yosys_area_proxy",
            "report": str(RESULTS / "yosys_stdout.txt"),
            "number_of_wires": "0",
            "number_of_wire_bits": "0",
            "number_of_public_wires": "0",
            "number_of_public_wire_bits": "0",
            "number_of_memories": "0",
            "number_of_memory_bits": "0",
            "number_of_processes": "0",
            "number_of_cells": "0",
            "overhead_vs_core_pct": "0.00",
            "status": "yosys_failed",
        }
    ]
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {failure_note}")
    print(f"Wrote {SUMMARY_CSV}")


def main() -> int:
    args = parse_args()
    validate_synth_script()
    yosys = args.yosys or shutil.which("yosys") or ""
    if not args.parse_only:
        if not yosys:
            write_tool_missing_note(yosys)
            return 2
        return_code, stdout = run_yosys(yosys)
        if return_code != 0:
            print(stdout)
            print(f"Yosys failed; partial log written to {RESULTS / 'yosys_stdout.txt'}")
            write_yosys_failure_summary(stdout)
            return 1

    rows: list[dict[str, str]] = []
    baseline_cells = 0
    parsed: dict[str, dict[str, int]] = {}
    for module, report in REPORTS.items():
        parsed[module] = parse_report(report)
        num_cells = parsed[module].get("number_of_cells", 0)
        if module == "arm_like_core":
            baseline_cells = num_cells
        rows.append(
            {
                "module": module,
                "report": str(report),
                "number_of_wires": str(parsed[module].get("number_of_wires", 0)),
                "number_of_wire_bits": str(parsed[module].get("number_of_wire_bits", 0)),
                "number_of_public_wires": str(parsed[module].get("number_of_public_wires", 0)),
                "number_of_public_wire_bits": str(parsed[module].get("number_of_public_wire_bits", 0)),
                "number_of_memories": str(parsed[module].get("number_of_memories", 0)),
                "number_of_memory_bits": str(parsed[module].get("number_of_memory_bits", 0)),
                "number_of_processes": str(parsed[module].get("number_of_processes", 0)),
                "number_of_cells": str(num_cells),
                "overhead_vs_core_pct": "0.00",
                "status": "parsed" if report.exists() else "missing_report",
            }
        )

    for row in rows:
        if row["module"] == "arm_like_core":
            row["overhead_vs_core_pct"] = "100.00"
            continue
        cells = float(row["number_of_cells"])
        if row["module"] == "pipesense_integrated_core":
            row["overhead_vs_core_pct"] = f"{(((cells - baseline_cells) / baseline_cells) * 100.0) if baseline_cells else 0.0:.2f}"
            row["status"] = "integrated_proxy" if row["status"] == "parsed" else row["status"]
        else:
            row["overhead_vs_core_pct"] = f"{((cells / baseline_cells) * 100.0) if baseline_cells else 0.0:.2f}"

    addition_cells = sum(parsed[module].get("number_of_cells", 0) for module in [
        "pipeline_observer",
        "adaptive_controller",
        "reconfig_unit",
    ])
    rows.append(
        {
            "module": "observer_controller_reconfig_total",
            "report": "standalone module sum",
            "number_of_wires": "",
            "number_of_wire_bits": "",
            "number_of_public_wires": "",
            "number_of_public_wire_bits": "",
            "number_of_memories": "",
            "number_of_memory_bits": "",
            "number_of_processes": "",
            "number_of_cells": str(addition_cells),
            "overhead_vs_core_pct": f"{((addition_cells / baseline_cells) * 100.0) if baseline_cells else 0.0:.2f}",
            "status": "proxy_sum",
        }
    )

    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "module",
        "report",
        "number_of_wires",
        "number_of_wire_bits",
        "number_of_public_wires",
        "number_of_public_wire_bits",
        "number_of_memories",
        "number_of_memory_bits",
        "number_of_processes",
        "number_of_cells",
        "overhead_vs_core_pct",
        "status",
    ]
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {SUMMARY_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
