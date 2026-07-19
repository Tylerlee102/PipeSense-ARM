#!/usr/bin/env python3
"""Run matched ECP5 synthesis and place-and-route for PipeSense-Ibex policies."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IBEX = ROOT / "build" / "ibex-final"
BUILD = ROOT / "output" / "ibex_post_synth"
RESULTS = ROOT / "results" / "ibex" / "post_synth"


def run(command: list[str], log: Path, cwd: Path = ROOT) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout, encoding="utf-8", newline="\n")
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}); see {log}")


def version(command: list[str]) -> str:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    return result.stdout.strip().splitlines()[0]


def convert(policy: int, directory: Path) -> Path:
    synthesis_excludes = {"ibex_top_tracing.sv", "ibex_tracer.sv"}
    rtl = [path for path in sorted((IBEX / "rtl").glob("*.sv"))
           if path.name not in synthesis_excludes]
    prim = IBEX / "vendor" / "lowrisc_ip" / "ip" / "prim"
    generic = IBEX / "vendor" / "lowrisc_ip" / "ip" / "prim_generic" / "rtl"
    sources = [
        prim / "rtl" / "prim_count_pkg.sv",
        prim / "rtl" / "prim_cipher_pkg.sv",
        generic / "prim_ram_1p_pkg.sv",
        prim / "rtl" / "prim_secded_pkg.sv",
        prim / "rtl" / "prim_util_pkg.sv",
        prim / "rtl" / "prim_count.sv",
        prim / "rtl" / "prim_secded_inv_39_32_dec.sv",
        prim / "rtl" / "prim_secded_inv_39_32_enc.sv",
        prim / "rtl" / "prim_lfsr.sv",
        generic / "prim_and2.sv",
        generic / "prim_buf.sv",
        ROOT / "integrations" / "ibex" / "synth" / "prim_clock_gating.sv",
        generic / "prim_clock_mux2.sv",
        generic / "prim_flop.sv",
        *rtl,
    ]
    converted = directory / "ibex.v"
    command = [
        "sv2v", "--define=SYNTHESIS", "--define=YOSYS",
        f"--define=PIPESENSE_POLICY={policy}", f"-I{prim / 'rtl'}",
        f"-I{IBEX / 'vendor/lowrisc_ip/dv/sv/dv_utils'}",
        *map(str, sources),
    ]
    result = subprocess.run(command, cwd=IBEX, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    (directory / "sv2v.log").write_text(result.stderr, encoding="utf-8", newline="\n")
    if result.returncode:
        raise RuntimeError(f"sv2v failed for policy {policy}; see {directory / 'sv2v.log'}")
    converted.write_text(result.stdout, encoding="utf-8", newline="\n")
    return converted


def parse_report(policy: int, report_path: Path, log_path: Path, frequency: float) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    utilization = report.get("utilization", {})
    fmax = report.get("fmax", {})
    achieved = max((float(item.get("achieved", 0)) for item in fmax.values()), default=0)
    log = log_path.read_text(encoding="utf-8", errors="replace")
    slack_match = re.search(r"Max frequency for clock.*?:\s*([0-9.]+) MHz", log)
    return {
        "policy": "baseline-static-sequential" if policy == 0 else "adaptive",
        "policy_id": policy,
        "target": "LFE5U-85F-6BG756C",
        "clock_constraint_mhz": frequency,
        "achieved_frequency_mhz": achieved or (float(slack_match.group(1)) if slack_match else ""),
        "trellis_comb": utilization.get("TRELLIS_COMB", {}).get("used", ""),
        "trellis_ff": utilization.get("TRELLIS_FF", {}).get("used", ""),
        "block_ram": utilization.get("DP16KD", {}).get("used", ""),
        "power": "unavailable",
        "failures": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency-mhz", type=float, default=25.0)
    parser.add_argument("--reuse-reports", action="store_true",
                        help="rebuild summaries from existing raw reports")
    args = parser.parse_args()
    tools = {name: shutil.which(name) for name in ("sv2v", "yosys", "nextpnr-ecp5")}
    if not all(tools.values()):
        print("Missing tools:", tools)
        return 2
    if not IBEX.exists():
        print(f"Missing prepared Ibex checkout: {IBEX}")
        return 2

    rows = []
    for policy in (0, 2):
        directory = BUILD / f"policy{policy}"
        directory.mkdir(parents=True, exist_ok=True)
        if not args.reuse_reports:
            converted = convert(policy, directory)
            json_path = directory / "ibex_top.json"
            yosys_script = directory / "synth.ys"
            yosys_script.write_text(
                f"read_verilog {converted.as_posix()}\n"
                "read_verilog " + (ROOT / "integrations" / "ibex" / "synth" /
                                    "ibex_fpga_top.v").as_posix() + "\n"
                "hierarchy -check -top pipesense_ibex_fpga_top\n"
                "synth_ecp5 -top pipesense_ibex_fpga_top -json " + json_path.as_posix() + "\n"
                "stat\n", encoding="ascii", newline="\n")
            run(["yosys", "-s", str(yosys_script)], directory / "yosys.log")
        report = directory / "nextpnr_report.json"
        nextpnr_log = directory / "nextpnr.log"
        if not args.reuse_reports:
            run([
                "nextpnr-ecp5", "--85k", "--package", "CABGA756", "--speed", "6",
                "--freq", str(args.frequency_mhz), "--json", str(json_path),
                "--textcfg", str(directory / "ibex_top.config"), "--report", str(report),
                "--detailed-timing-report", "--lpf-allow-unconstrained",
            ], nextpnr_log)
        elif not report.is_file() or not nextpnr_log.is_file():
            raise RuntimeError(f"missing reusable reports for policy {policy}")
        rows.append(parse_report(policy, report, nextpnr_log, args.frequency_mhz))

        evidence_dir = RESULTS / f"policy{policy}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        for artifact in ("sv2v.log", "synth.ys", "yosys.log", "nextpnr.log",
                         "nextpnr_report.json"):
            shutil.copy2(directory / artifact, evidence_dir / artifact)

    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    baseline, adaptive = rows
    comparison = {
        "trellis_comb_delta": adaptive["trellis_comb"] - baseline["trellis_comb"],
        "trellis_comb_delta_percent":
            100 * (adaptive["trellis_comb"] - baseline["trellis_comb"]) /
            baseline["trellis_comb"],
        "trellis_ff_delta": adaptive["trellis_ff"] - baseline["trellis_ff"],
        "trellis_ff_delta_percent":
            100 * (adaptive["trellis_ff"] - baseline["trellis_ff"]) /
            baseline["trellis_ff"],
        "frequency_delta_mhz": adaptive["achieved_frequency_mhz"] -
                               baseline["achieved_frequency_mhz"],
        "frequency_delta_percent":
            100 * (adaptive["achieved_frequency_mhz"] -
                   baseline["achieved_frequency_mhz"]) /
            baseline["achieved_frequency_mhz"],
    }
    manifest = {
        "status": "PASS",
        "tools": {name: version([path, "--version"]) for name, path in tools.items()},
        "same_target_and_constraint": True,
        "power": "unavailable: no characterized ECP5 power model or switching activity",
        "adaptive_minus_baseline": comparison,
        "rows": rows,
    }
    (RESULTS / "summary.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
