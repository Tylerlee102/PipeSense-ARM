#!/usr/bin/env python3
"""Build and validate the pinned PipeSense-Ibex engineering integration."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IBEX = ROOT / "build" / "ibex-final"
EMBENCH = ROOT / "build" / "embench-final"
RESULTS = ROOT / "results" / "ibex"
IMAGE = "pipesense-arm-ibex-v2"
POLICIES = {0: "static-sequential", 1: "static-branch", 2: "adaptive"}
SIM_OPTIONS = [
    "--RV32E=0", "--RV32M=ibex_pkg::RV32MFast", "--RV32B=ibex_pkg::RV32BNone",
    "--RV32ZC=ibex_pkg::RV32ZcaZcbZcmp", "--RegFile=ibex_pkg::RegFileFF",
    "--BranchTargetALU=1", "--WritebackStage=1", "--INSTR_CYCLE_DELAY=3",
]


def run(command: list[str], *, cwd: Path = ROOT, timeout: int | None = None,
        capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=cwd, timeout=timeout, check=True, text=True,
                          capture_output=capture)


def docker(command: list[str], *, cwd: str = "/workspace", timeout: int | None = None,
           capture: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["docker", "run", "--rm", "-v", f"{ROOT}:/workspace", "-w", cwd,
                IMAGE, *command], timeout=timeout, capture=capture)


def prepare(clean: bool) -> None:
    command = [sys.executable, str(ROOT / "scripts" / "prepare_ibex.py"),
               "--dest", str(IBEX), "--embench-dest", str(EMBENCH)]
    if clean:
        command.append("--clean")
    run(command)


def build_simulators() -> None:
    def build(policy: int) -> None:
        docker([
            "fusesoc", "--cores-root=.", "run", f"--build-root=build/policy{policy}",
            "--target=sim", "--setup", "--build", "lowrisc:ibex:ibex_simple_system",
            *SIM_OPTIONS, f"--PIPESENSE_POLICY={policy}",
        ], cwd="/workspace/build/ibex-final", timeout=900)
    with ThreadPoolExecutor(max_workers=len(POLICIES)) as executor:
        list(executor.map(build, POLICIES))


def build_simple_program(name: str) -> Path:
    docker(["make", "distclean"], cwd=f"/workspace/build/ibex-final/examples/sw/simple_system/{name}")
    docker(["make", "ARCH=rv32imc_zicsr"],
           cwd=f"/workspace/build/ibex-final/examples/sw/simple_system/{name}")
    return IBEX / "examples" / "sw" / "simple_system" / name / f"{name}.elf"


def build_coremark(iterations: int) -> Path:
    directory = "/workspace/build/ibex-final/examples/sw/benchmarks/coremark"
    docker(["make", "clean"], cwd=directory)
    docker(["make", f"ITERATIONS={iterations}", "RV_ISA=rv32imc_zicsr"],
           cwd=directory, timeout=300)
    return IBEX / "examples" / "sw" / "benchmarks" / "coremark" / "coremark.elf"


def build_embench(quick: bool) -> list[tuple[str, Path]]:
    output = EMBENCH / "build" / "ibex"
    output.mkdir(parents=True, exist_ok=True)
    names = sorted(path.name for path in (EMBENCH / "src").iterdir() if path.is_dir())
    if quick:
        names = [name for name in names if name in {"crc32", "edn"}]
    programs: list[tuple[str, Path]] = []
    for name in names:
        sources = sorted((EMBENCH / "src" / name).glob("*.c"))
        container_sources = [f"/workspace/{path.relative_to(ROOT).as_posix()}" for path in sources]
        elf = output / f"{name}.elf"
        docker([
            "riscv32-unknown-elf-gcc", "-march=rv32imc_zicsr", "-mabi=ilp32", "-O2",
            "-static", "-mcmodel=medany", "-fvisibility=hidden", "-nostdlib",
            "-nostartfiles", "-ffreestanding", "-DWARMUP_HEAT=1", "-DGLOBAL_SCALE_FACTOR=1",
            f"-DEMBENCH_NAME={name}", "-I/workspace/build/embench-final/support",
            "-I/workspace/integrations/ibex/embench/include",
            "-I/workspace/integrations/ibex/embench",
            "-I/workspace/build/ibex-final/examples/sw/simple_system/common",
            *container_sources,
            "/workspace/build/embench-final/support/beebsc.c",
            "/workspace/integrations/ibex/embench/main.c",
            "/workspace/integrations/ibex/embench/boardsupport.c",
            "/workspace/integrations/ibex/embench/minilib.c",
            "/workspace/build/ibex-final/examples/sw/simple_system/common/simple_system_common.c",
            "/workspace/build/ibex-final/examples/sw/simple_system/common/crt0.S",
            "-Wl,-T,/workspace/build/ibex-final/examples/sw/simple_system/common/link.ld",
            "-lgcc", "-o", f"/workspace/{elf.relative_to(ROOT).as_posix()}",
        ], timeout=120)
        programs.append((f"embench-{name}", elf))
    return programs


def architecture_sources(quick: bool) -> list[Path]:
    suite = IBEX / "vendor" / "riscv-arch-tests" / "riscv-test-suite" / "rv32i_m"
    extensions = ["I"] if quick else ["I", "M", "C", "Zifencei"]
    sources = [source for extension in extensions
               for source in sorted((suite / extension / "src").glob("*.S"))]
    return sources[:1] if quick else sources


def build_architecture_tests(quick: bool) -> list[tuple[str, Path]]:
    output = IBEX / "build" / "arch-tests"
    output.mkdir(parents=True, exist_ok=True)
    programs = []
    for source in architecture_sources(quick):
        extension = source.parent.parent.name
        name = f"arch-{extension}-{source.stem}"
        elf = output / f"{name}.elf"
        docker([
            "riscv32-unknown-elf-gcc", "-march=rv32imc_zicsr", "-mabi=ilp32", "-static",
            "-mcmodel=medany", "-fvisibility=hidden", "-nostdlib", "-nostartfiles",
            "-I/workspace/integrations/ibex/arch_test",
            "-I/workspace/build/ibex-final/vendor/riscv-arch-tests/riscv-test-suite/env",
            f"/workspace/{source.relative_to(ROOT).as_posix()}",
            "-Wl,-T,/workspace/integrations/ibex/arch_test/link.ld", "-lgcc",
            "-o", f"/workspace/{elf.relative_to(ROOT).as_posix()}",
        ], timeout=60)
        programs.append((name, elf))
    return programs


def simulator_path(policy: int) -> str:
    return (f"/workspace/build/ibex-final/build/policy{policy}/"
            "lowrisc_ibex_ibex_simple_system_0/"
            "sim-verilator/Vibex_simple_system")


def parse_stats(output: str) -> dict[str, int | float]:
    def number(pattern: str, default: int = 0) -> int:
        match = re.search(pattern, output)
        return int(match.group(1)) if match else default
    cycles = number(r"Cycles:\s+(\d+)", number(r"Executed cycles:\s+(\d+)"))
    retired = number(r"Instructions Retired:\s+(\d+)")
    return {
        "cycles": cycles,
        "retired": retired,
        "ipc": retired / cycles if cycles else 0.0,
        "transitions": number(r"PIPESENSE_STATS.*transitions=(\d+)"),
        "drain_cycles": number(r"PIPESENSE_STATS.*drain_cycles=(\d+)"),
    }


def run_spike(name: str, elf: Path, signature: bool) -> Path | None:
    ref_dir = RESULTS / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)
    signature_path = ref_dir / f"{name}.signature"
    command = ["spike", "--isa=rv32imc_zicsr", "-m0x100000:0x38000,0x20000:0x1000"]
    if signature:
        command.append(f"+signature=/workspace/{signature_path.relative_to(ROOT).as_posix()}")
        command.append("+signature-granularity=4")
    command.append(f"/workspace/{elf.relative_to(ROOT).as_posix()}")
    result = docker(command, timeout=300, capture=True)
    (ref_dir / f"{name}.log").write_text(result.stdout + result.stderr,
                                           encoding="utf-8", newline="\n")
    return signature_path if signature else None


def signature_bytes(path: Path) -> bytes:
    data = bytearray()
    for line in path.read_text(encoding="ascii").splitlines():
        word = line.strip()
        if word:
            data.extend(int(word, 16).to_bytes(len(word) // 2, "little"))
    return bytes(data)


def run_program(name: str, elf: Path, policy: int, reference_signature: Path | None) -> dict:
    log_dir = RESULTS / "logs" / POLICIES[policy]
    log_dir.mkdir(parents=True, exist_ok=True)
    run_dir = RESULTS / "work" / POLICIES[policy] / name
    run_dir.mkdir(parents=True, exist_ok=True)
    elf_arg = f"/workspace/{elf.relative_to(ROOT).as_posix()}"
    started = time.monotonic()
    result = docker(["timeout", "3600s", simulator_path(policy),
                     "+ibex_tracer_enable=0", f"--meminit=ram,{elf_arg}"],
                    cwd=f"/workspace/{run_dir.relative_to(ROOT).as_posix()}",
                    timeout=3700, capture=True)
    elapsed = time.monotonic() - started
    stdout = result.stdout + result.stderr
    (log_dir / f"{name}.sim.log").write_text(stdout, encoding="utf-8", newline="\n")
    program_log = run_dir / "ibex_simple_system.log"
    raw = program_log.read_bytes()
    (log_dir / f"{name}.program.log").write_bytes(raw)
    for trace in run_dir.glob("trace_core_*.log"):
        trace.unlink()
    text = raw.decode("latin1")
    expected_marker = None
    if name.startswith("embench-"):
        expected_marker = "EMBENCH_PASS"
    elif name.startswith("coremark-"):
        expected_marker = "Correct operation validated"
    elif name == "multiphase":
        expected_marker = "PIPESENSE_MULTIPHASE_PASS DE332F10"
    elif name == "fuzz-500":
        expected_marker = "PIPESENSE_FUZZ_PASS seeds=500 signature=6B93D2E5"
    if "EMBENCH_FAIL" in text or ("PIPESENSE_" in text and "_FAIL" in text):
        raise RuntimeError(f"self-check failed for {name} policy {policy}")
    if expected_marker is not None and expected_marker not in text:
        raise RuntimeError(f"missing validation marker for {name} policy {policy}")
    if reference_signature is not None and raw != signature_bytes(reference_signature):
        raise RuntimeError(f"architecture signature mismatch for {name} policy {policy}")
    stats = parse_stats(stdout)
    return {"benchmark": name, "policy": POLICIES[policy], **stats,
            "wall_seconds": round(elapsed, 3), "failures": 0}


def validate(coremark_iterations: int, quick: bool) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "integrations" / "ibex" / "lock.json").read_text())
    versions = docker(["sh", "-lc", "verilator --version; fusesoc --version; riscv32-unknown-elf-gcc --version | head -1; spike --help 2>&1 | head -1"], capture=True)
    (RESULTS / "tool_versions.txt").write_text(versions.stdout + versions.stderr,
                                                encoding="utf-8", newline="\n")
    (RESULTS / "source_revisions.json").write_text(json.dumps(lock, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")

    programs = [("multiphase", build_simple_program("pipesense_multiphase")),
                ("fuzz-500", build_simple_program("pipesense_fuzz")),
                (f"coremark-{coremark_iterations}", build_coremark(coremark_iterations))]
    programs.extend(build_embench(quick))
    arch_programs = build_architecture_tests(quick)

    rows = []
    for name, elf in programs:
        run_spike(name, elf, False)
        with ThreadPoolExecutor(max_workers=len(POLICIES)) as executor:
            rows.extend(executor.map(lambda policy: run_program(name, elf, policy, None), POLICIES))
    for name, elf in arch_programs:
        signature = run_spike(name, elf, True)
        with ThreadPoolExecutor(max_workers=len(POLICIES)) as executor:
            rows.extend(executor.map(
                lambda policy: run_program(name, elf, policy, signature), POLICIES))

    csv_path = RESULTS / "benchmark_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "PASS",
        "policies": list(POLICIES.values()),
        "coremark_iterations": coremark_iterations,
        "embench_programs": sum(name.startswith("embench-") for name, _ in programs),
        "architecture_tests": len(arch_programs),
        "fuzz_seeds": 500,
        "runs": len(rows),
        "failures": sum(int(row["failures"]) for row in rows),
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-prepare", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--quick", action="store_true",
                        help="run two Embench programs, one architecture test, and 10 CoreMark iterations")
    parser.add_argument("--coremark-iterations", type=int, default=2000)
    args = parser.parse_args()
    iterations = 10 if args.quick else args.coremark_iterations
    if not args.skip_prepare:
        prepare(clean=True)
    if not args.skip_build:
        build_simulators()
    validate(iterations, args.quick)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
