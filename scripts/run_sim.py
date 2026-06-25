#!/usr/bin/env python3
"""Compile and run the PipeSense-ARM SystemVerilog testbench."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
RESULTS = ROOT / "results"
VVP_OUT = BUILD / "pipesense_tb.vvp"

SOURCES = [
    ROOT / "rtl" / "pipeline_registers.sv",
    ROOT / "rtl" / "hazard_unit.sv",
    ROOT / "rtl" / "forwarding_unit.sv",
    ROOT / "rtl" / "pipeline_observer.sv",
    ROOT / "rtl" / "adaptive_controller.sv",
    ROOT / "rtl" / "reconfig_unit.sv",
    ROOT / "rtl" / "perf_counters.sv",
    ROOT / "rtl" / "simple_memory.sv",
    ROOT / "rtl" / "arm_like_core.sv",
    ROOT / "tb" / "tb_pipesense.sv",
]


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def find_msys_bash(tool_path: str) -> Path | None:
    path = Path(tool_path)
    for parent in path.parents:
        candidate = parent / "usr" / "bin" / "bash.exe"
        if candidate.exists():
            return candidate
    return None


def to_msys_path(path: str | Path) -> str:
    text = str(path)
    text = text.replace("\\", "/")
    if len(text) >= 2 and text[1] == ":":
        return f"/{text[0].lower()}{text[2:]}"
    return text


def maybe_msys_arg(arg: str) -> str:
    if len(arg) >= 2 and arg[1] == ":":
        return to_msys_path(arg)
    if "\\" in arg:
        return to_msys_path(arg)
    return arg


def run_msys(bash: Path, cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    tmp_dir = cwd / "build" / "tmp"
    command = " ".join(shlex.quote(maybe_msys_arg(arg)) for arg in cmd)
    bash_cmd = (
        f"cd {shlex.quote(to_msys_path(cwd))} && "
        "mkdir -p build/tmp && "
        "export PATH=/ucrt64/bin:$PATH && "
        f"export TMP={shlex.quote(to_msys_path(tmp_dir))} && "
        f"export TEMP={shlex.quote(to_msys_path(tmp_dir))} && "
        f"export TMPDIR={shlex.quote(to_msys_path(tmp_dir))} && "
        f"{command}"
    )
    return run([str(bash), "-lc", bash_cmd], cwd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs-window", type=int, default=None, help="Override observer window size.")
    parser.add_argument("--min-residency", type=int, default=None, help="Override minimum mode residency.")
    parser.add_argument("--data-wait-cycles", type=int, default=None, help="Override synthetic data wait cycles.")
    parser.add_argument("--branch-threshold", type=int, default=None, help="Override branch-heavy classification threshold.")
    parser.add_argument("--mem-threshold", type=int, default=None, help="Override memory-stall classification threshold.")
    parser.add_argument("--load-use-threshold", type=int, default=None, help="Override load-use classification threshold.")
    parser.add_argument("--frontend-threshold", type=int, default=None, help="Override frontend-stall classification threshold.")
    parser.add_argument("--idle-threshold", type=int, default=None, help="Override idle/low-retire classification threshold.")
    parser.add_argument("--tag", default="", help="Optional suffix for the simulator log name.")
    parser.add_argument("--iverilog", default=os.environ.get("IVERILOG", ""), help="Path to iverilog executable.")
    parser.add_argument("--vvp", default=os.environ.get("VVP", ""), help="Path to vvp executable.")
    return parser.parse_args()


def safe_log_name(tag: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in tag)
    return f"sim_output_{cleaned}.txt" if cleaned else "sim_output.txt"


def main() -> int:
    args = parse_args()
    iverilog = args.iverilog or shutil.which("iverilog")
    vvp = args.vvp or shutil.which("vvp")
    sim_log = RESULTS / safe_log_name(args.tag)

    if not iverilog or not vvp or not Path(iverilog).exists() or not Path(vvp).exists():
        print("Icarus Verilog was not found.")
        print("Install iverilog/vvp, then rerun: python scripts/run_sim.py")
        print("Or pass explicit paths: python scripts/run_sim.py --iverilog <path> --vvp <path>")
        print("The HDL and analysis scripts remain available for review and offline checks.")
        return 2
    msys_bash = find_msys_bash(iverilog)

    BUILD.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    tmp_dir = BUILD / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    tool_env = os.environ.copy()
    tool_env["TMP"] = str(tmp_dir).replace("\\", "/")
    tool_env["TEMP"] = str(tmp_dir).replace("\\", "/")
    tool_env["TMPDIR"] = str(tmp_dir).replace("\\", "/")

    compile_cmd = [
        iverilog,
        "-g2012",
        "-Wall",
        "-I",
        str(ROOT / "rtl"),
        "-I",
        str(ROOT / "tb"),
        "-o",
        str(VVP_OUT),
    ]
    if args.obs_window is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.OBS_WINDOW={args.obs_window}"])
    if args.min_residency is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.MIN_MODE_RESIDENCY={args.min_residency}"])
    if args.data_wait_cycles is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.DATA_WAIT_CYCLES={args.data_wait_cycles}"])
    if args.branch_threshold is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.OBS_BRANCH_THRESHOLD={args.branch_threshold}"])
    if args.mem_threshold is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.OBS_MEM_STALL_THRESHOLD={args.mem_threshold}"])
    if args.load_use_threshold is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.OBS_LOAD_USE_THRESHOLD={args.load_use_threshold}"])
    if args.frontend_threshold is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.OBS_FRONTEND_STALL_THRESHOLD={args.frontend_threshold}"])
    if args.idle_threshold is not None:
        compile_cmd.extend(["-P", f"tb_pipesense.dut.OBS_IDLE_RETIRE_THRESHOLD={args.idle_threshold}"])
    compile_cmd.extend(str(source) for source in SOURCES)
    if msys_bash:
        compile_proc = run_msys(msys_bash, compile_cmd, ROOT)
    else:
        compile_proc = run(compile_cmd, ROOT, env=tool_env)
    if compile_proc.returncode != 0:
        print(compile_proc.stdout)
        return compile_proc.returncode

    if msys_bash:
        sim_proc = run_msys(msys_bash, [vvp, str(VVP_OUT)], ROOT)
    else:
        sim_proc = run([vvp, str(VVP_OUT)], ROOT, env=tool_env)
    sim_log.write_text(sim_proc.stdout, encoding="utf-8")
    print(sim_proc.stdout)

    if sim_proc.returncode != 0:
        return sim_proc.returncode

    analyze_proc = run(
        [sys.executable, str(ROOT / "scripts" / "analyze_results.py"), str(sim_log)],
        ROOT,
    )
    print(analyze_proc.stdout)
    if analyze_proc.returncode != 0:
        return analyze_proc.returncode

    validate_proc = run([sys.executable, str(ROOT / "scripts" / "validate_results.py")], ROOT)
    print(validate_proc.stdout)
    if validate_proc.returncode != 0:
        return validate_proc.returncode

    reference_proc = run([sys.executable, str(ROOT / "scripts" / "isa_reference.py")], ROOT)
    print(reference_proc.stdout)
    if reference_proc.returncode != 0:
        return reference_proc.returncode

    compare_proc = run([sys.executable, str(ROOT / "scripts" / "compare_reference.py")], ROOT)
    print(compare_proc.stdout)
    return compare_proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
