#!/usr/bin/env python3
"""Run constrained-random PipeSense safety simulations."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from random_seq_gen import generate_harness


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_sim import find_msys_bash, run_msys  # noqa: E402

BUILD = Path(
    os.environ.get(
        "PIPESENSE_FUZZ_BUILD_DIR",
        str(Path(tempfile.gettempdir()) / "pipesense_arm_fuzz"),
    )
)
RESULTS = ROOT / "results" / "safety"
GENERATED = ROOT / "verif" / "generated"

RTL_SOURCES = [
    ROOT / "rtl" / "pipeline_registers.sv",
    ROOT / "rtl" / "hazard_unit.sv",
    ROOT / "rtl" / "forwarding_unit.sv",
    ROOT / "rtl" / "pipeline_observer.sv",
    ROOT / "rtl" / "adaptive_controller.sv",
    ROOT / "rtl" / "async03_speculation_controller.sv",
    ROOT / "rtl" / "reconfig_unit.sv",
    ROOT / "rtl" / "perf_counters.sv",
    ROOT / "rtl" / "simple_memory.sv",
    ROOT / "rtl" / "arm_like_core.sv",
    ROOT / "verif" / "sva_safety.sv",
    ROOT / "verif" / "cov_safety.sv",
]

FUZZ_RE = re.compile(
    r"FUZZ_RESULT seed=(?P<seed>\d+) mode=(?P<mode>\S+) cycles=(?P<cycles>\d+) "
    r"retired=(?P<retired>\d+) stalls=(?P<stalls>\d+) flushes=(?P<flushes>\d+) "
    r"mem_wait=(?P<mem_wait>\d+) load_use=(?P<load_use>\d+) reconfigs=(?P<reconfigs>\d+) "
    r"reconfig_penalty=(?P<reconfig_penalty>\d+) energy=(?P<energy>\d+) "
    r"safety_faults=(?P<safety_faults>\d+) timed_out=(?P<timed_out>\d+)"
)

COV_RE = re.compile(
    r"FUZZ_COVERAGE seed=(?P<seed>\d+) phases_seen=0x(?P<phases_seen>[0-9a-fA-F]+) "
    r"transitions_seen=0x(?P<transitions_seen>[0-9a-fA-F]+) "
    r"hazard_during_reconfig=(?P<hazard_during_reconfig>\d+) "
    r"back_to_back_reconfig_requests=(?P<back_to_back_reconfig_requests>\d+) "
    r"reconfig_then_branch=(?P<reconfig_then_branch>\d+) "
    r"reconfig_then_load_use=(?P<reconfig_then_load_use>\d+)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=500, help="Number of seeds to run.")
    parser.add_argument("--start-seed", type=int, default=1, help="First seed.")
    parser.add_argument("--instructions", type=int, default=96, help="Instructions per generated program.")
    parser.add_argument("--obs-window", type=int, default=None, help="Override observer window size.")
    parser.add_argument("--min-residency", type=int, default=None, help="Override minimum mode residency.")
    parser.add_argument("--reconfig-bound", type=int, default=32, help="Safety assertion bound in cycles.")
    parser.add_argument("--iverilog", default=os.environ.get("IVERILOG", ""), help="Path to iverilog.")
    parser.add_argument("--vvp", default=os.environ.get("VVP", ""), help="Path to vvp.")
    parser.add_argument("--keep-going", action="store_true", help="Continue after a failing seed.")
    parser.add_argument(
        "--controller-policy",
        choices=("pipesense", "async03"),
        default="pipesense",
        help="Controller policy under test.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS,
        help="Directory for logs and summary CSV files.",
    )
    return parser.parse_args()


def compile_and_run(
    seed: int,
    harness: Path,
    iverilog: str,
    vvp: str,
    obs_window: int | None,
    min_residency: int | None,
    controller_policy: str,
) -> tuple[int, str]:
    # Compiler products are disposable and can be large. Keep policy-specific
    # copies in local temporary storage so synchronized workspaces only receive
    # the raw text logs and CSV evidence.
    policy_build = BUILD / controller_policy
    policy_build.mkdir(parents=True, exist_ok=True)
    vvp_out = policy_build / f"tb_random_seed_{seed}.vvp"
    msys_bash = find_msys_bash(iverilog)
    compile_cmd = [
        iverilog,
        "-g2012",
        "-Wall",
        "-I",
        str(ROOT / "rtl"),
        "-I",
        str(ROOT / "verif"),
        "-o",
        str(vvp_out),
    ]
    if obs_window is not None:
        compile_cmd.extend(["-P", f"tb_random_seed_{seed}.dut.OBS_WINDOW={obs_window}"])
    if min_residency is not None:
        compile_cmd.extend(["-P", f"tb_random_seed_{seed}.dut.MIN_MODE_RESIDENCY={min_residency}"])
    if controller_policy == "async03":
        compile_cmd.append("-DPIPESENSE_ASYNC03_BASELINE")
    compile_cmd.extend(str(path) for path in RTL_SOURCES)
    compile_cmd.append(str(harness))

    if msys_bash:
        compile_proc = run_msys(msys_bash, compile_cmd, ROOT)
    else:
        compile_proc = subprocess.run(
            compile_cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if compile_proc.returncode != 0:
        return compile_proc.returncode, compile_proc.stdout

    if msys_bash:
        sim_proc = run_msys(msys_bash, [vvp, str(vvp_out)], ROOT)
    else:
        sim_proc = subprocess.run(
            [vvp, str(vvp_out)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return sim_proc.returncode, sim_proc.stdout


def parse_output(seed: int, text: str, return_code: int) -> tuple[list[dict[str, str]], dict[str, str]]:
    result_rows = [match.groupdict() for match in FUZZ_RE.finditer(text)]
    assertion_failures = sum(
        1
        for line in text.splitlines()
        if "ERROR:" in line and ("SVA_" in line or "SAFETY:" in line)
    )
    for row in result_rows:
        row["return_code"] = str(return_code)
        row["assertion_failures"] = str(assertion_failures)

    cov_match = COV_RE.search(text)
    if cov_match:
        coverage = cov_match.groupdict()
    else:
        coverage = {
            "seed": str(seed),
            "phases_seen": "0",
            "transitions_seen": "0",
            "hazard_during_reconfig": "0",
            "back_to_back_reconfig_requests": "0",
            "reconfig_then_branch": "0",
            "reconfig_then_load_use": "0",
        }
    coverage["return_code"] = str(return_code)
    coverage["assertion_failures"] = str(assertion_failures)
    return result_rows, coverage


def write_tool_missing_note(iverilog: str, vvp: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    note = output_dir / "fuzz_tool_unavailable.md"
    note.write_text(
        "# Fuzz Regression Not Run\n\n"
        "Icarus Verilog was not found, so the constrained-random safety "
        "regression could not run in this environment.\n\n"
        f"- iverilog: `{iverilog or 'not found'}`\n"
        f"- vvp: `{vvp or 'not found'}`\n\n"
        "Install `iverilog` and `vvp`, then rerun "
        "`python verif/fuzz_runner.py --seeds 500`.\n",
        encoding="utf-8",
    )
    print(f"Wrote {note}")


def main() -> int:
    args = parse_args()
    iverilog = args.iverilog or shutil.which("iverilog") or ""
    vvp = args.vvp or shutil.which("vvp") or ""
    if not iverilog or not vvp:
        write_tool_missing_note(iverilog, vvp, args.output_dir)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    GENERATED.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, str]] = []
    coverage_rows: list[dict[str, str]] = []

    for offset in range(args.seeds):
        seed = args.start_seed + offset
        harness = GENERATED / f"tb_random_seed_{seed}.sv"
        generate_harness(seed, args.instructions, harness, args.reconfig_bound)
        return_code, output = compile_and_run(
            seed,
            harness,
            iverilog,
            vvp,
            args.obs_window,
            args.min_residency,
            args.controller_policy,
        )
        log_path = args.output_dir / f"fuzz_seed_{seed}.log"
        log_path.write_text(output, encoding="utf-8")
        rows, coverage = parse_output(seed, output, return_code)
        for row in rows:
            row["log"] = str(log_path)
        coverage["log"] = str(log_path)
        all_results.extend(rows)
        coverage_rows.append(coverage)
        print(f"seed={seed} return_code={return_code} results={len(rows)} log={log_path}")
        if return_code != 0 and not args.keep_going:
            break

    result_fields = [
        "seed",
        "mode",
        "cycles",
        "retired",
        "stalls",
        "flushes",
        "mem_wait",
        "load_use",
        "reconfigs",
        "reconfig_penalty",
        "energy",
        "safety_faults",
        "timed_out",
        "return_code",
        "assertion_failures",
        "log",
    ]
    coverage_fields = [
        "seed",
        "phases_seen",
        "transitions_seen",
        "hazard_during_reconfig",
        "back_to_back_reconfig_requests",
        "reconfig_then_branch",
        "reconfig_then_load_use",
        "return_code",
        "assertion_failures",
        "log",
    ]

    with (args.output_dir / "fuzz_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=result_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_results)
    with (args.output_dir / "fuzz_coverage.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=coverage_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(coverage_rows)

    failed = [
        row for row in all_results
        if row["return_code"] != "0"
        or row["safety_faults"] != "0"
        or row["timed_out"] != "0"
        or row["assertion_failures"] != "0"
    ]
    print(f"Wrote {args.output_dir / 'fuzz_summary.csv'}")
    print(f"Wrote {args.output_dir / 'fuzz_coverage.csv'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
