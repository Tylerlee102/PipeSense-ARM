#!/usr/bin/env python3
"""Run complete-core ECP5 synthesis/place-and-route and record raw evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "output" / "post_synth"
RESULTS = ROOT / "results" / "post_synth"
YOSYS_SCRIPT = ROOT / "synth" / "production_ecp5.ys"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yosys", default="", help="Path to Yosys.")
    parser.add_argument("--nextpnr", default="", help="Path to nextpnr-ecp5.")
    parser.add_argument("--frequency-mhz", type=float, default=25.0)
    parser.add_argument("--device", choices=("85k",), default="85k")
    parser.add_argument("--part", default="LFE5U-85F")
    parser.add_argument("--package", default="CABGA756")
    parser.add_argument("--speed", default="6")
    return parser.parse_args()


def run(command: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8")
    return proc


def tool_version(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else "unavailable"


def utilization(report: dict[str, object], name: str) -> tuple[str, str]:
    util = report.get("utilization", {})
    if not isinstance(util, dict):
        return "", ""
    entry = util.get(name, {})
    if not isinstance(entry, dict):
        return "", ""
    return str(entry.get("used", "")), str(entry.get("available", ""))


def first_float(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def main() -> int:
    args = parse_args()
    yosys = args.yosys or shutil.which("yosys") or ""
    nextpnr = args.nextpnr or shutil.which("nextpnr-ecp5") or ""
    if not yosys or not nextpnr:
        print(f"Missing tool: yosys={yosys or 'not found'} nextpnr={nextpnr or 'not found'}")
        return 2

    BUILD.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    yosys_log = RESULTS / "yosys.log"
    nextpnr_log = RESULTS / "nextpnr.log"
    report_path = RESULTS / "nextpnr_report.json"

    yosys_cmd = [yosys, "-s", str(YOSYS_SCRIPT)]
    yosys_proc = run(yosys_cmd, yosys_log)
    if yosys_proc.returncode != 0:
        print(f"Yosys failed; see {yosys_log}")
        return yosys_proc.returncode

    nextpnr_cmd = [
        nextpnr,
        f"--{args.device}",
        "--package", args.package,
        "--speed", args.speed,
        "--freq", str(args.frequency_mhz),
        "--json", str(BUILD / "pipesense_fpga_top_ecp5.json"),
        "--textcfg", str(BUILD / "pipesense_fpga_top_ecp5.config"),
        "--sdf", str(BUILD / "pipesense_fpga_top_ecp5.sdf"),
        "--report", str(report_path),
        "--detailed-timing-report",
        "--lpf-allow-unconstrained",
    ]
    nextpnr_proc = run(nextpnr_cmd, nextpnr_log)

    report: dict[str, object] = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    log_text = nextpnr_log.read_text(encoding="utf-8", errors="replace")
    comb_used, comb_available = utilization(report, "TRELLIS_COMB")
    dffs_used, dffs_available = utilization(report, "TRELLIS_FF")
    bram_used, bram_available = utilization(report, "DP16KD")
    distributed_ram_used, distributed_ram_available = utilization(report, "TRELLIS_RAMW")
    io_used, io_available = utilization(report, "TRELLIS_IO")
    fmax = report.get("fmax", {})
    fmax_entry = next(iter(fmax.values()), {}) if isinstance(fmax, dict) else {}
    achieved = float(fmax_entry.get("achieved", 0.0)) if isinstance(fmax_entry, dict) else 0.0
    worst_slack = (
        (1000.0 / args.frequency_mhz) - (1000.0 / achieved)
        if achieved > 0.0 else None
    )
    summary = {
        "status": "pass" if nextpnr_proc.returncode == 0 else "fail",
        "design": "pipesense_fpga_top (complete production RTL and load interface)",
        "target_part": args.part,
        "package": args.package,
        "speed_grade": args.speed,
        "clock_constraint_mhz": f"{args.frequency_mhz:.3f}",
        "achieved_frequency_mhz": f"{achieved:.3f}" if achieved else "",
        "worst_slack_ns": f"{worst_slack:.3f}" if worst_slack is not None else "",
        "trellis_comb_used": comb_used,
        "trellis_comb_available": comb_available,
        "dffs_used": dffs_used,
        "dffs_available": dffs_available,
        "block_ram_used": bram_used,
        "block_ram_available": bram_available,
        "distributed_ram_write_ports_used": distributed_ram_used,
        "distributed_ram_write_ports_available": distributed_ram_available,
        "io_used": io_used,
        "io_available": io_available,
        "power": "unavailable",
        "power_reason": "No characterized ECP5 power model and no switching-activity trace in Yosys/nextpnr flow.",
        "yosys_version": tool_version([yosys, "-V"]),
        "nextpnr_version": tool_version([nextpnr, "--version"]),
        "nextpnr_return_code": str(nextpnr_proc.returncode),
    }
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "yosys_command": yosys_cmd,
        "nextpnr_command": nextpnr_cmd,
        "inputs": [
            "synth/production_ecp5.ys",
            "rtl/arm_like_core.sv",
            "rtl/pipesense_fpga_top.sv",
            "rtl/simple_memory.sv",
            "rtl/pipeline_observer.sv",
            "rtl/adaptive_controller.sv",
            "rtl/async03_speculation_controller.sv",
            "rtl/reconfig_unit.sv",
            "rtl/perf_counters.sv",
        ],
        "summary": summary,
    }
    (RESULTS / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (RESULTS / "power_status.md").write_text(
        "# Post-Synthesis Power Status\n\n"
        "Power is **unavailable**, not zero. The committed open-source flow has "
        "neither a characterized LFE5U-85F power model nor a switching-activity "
        "trace. No power value is inferred from the repository's simulation "
        "energy proxy.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return nextpnr_proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
