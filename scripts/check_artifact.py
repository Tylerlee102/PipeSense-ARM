#!/usr/bin/env python3
"""Run repository-level checks that do not require an HDL simulator."""

from __future__ import annotations

import csv
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)

REQUIRED_FILES = [
    "README.md",
    "Makefile",
    "Dockerfile",
    ".github/workflows/ci.yml",
    "rtl/defines.svh",
    "rtl/arm_like_core.sv",
    "rtl/pipeline_observer.sv",
    "rtl/adaptive_controller.sv",
    "rtl/reconfig_unit.sv",
    "rtl/perf_counters.sv",
    "tb/tb_pipesense.sv",
    "tb/benchmark_programs.sv",
    "scripts/run_sim.py",
    "scripts/analyze_results.py",
    "scripts/isa_reference.py",
    "scripts/compare_reference.py",
    "scripts/check_benchmark_parity.py",
    "scripts/plot_results.py",
    "scripts/run_sweep.py",
    "scripts/sweep_params.py",
    "scripts/synth_area_report.py",
    "scripts/estimate_hardware_cost.py",
    "scripts/audit_requirements.py",
    "scripts/lint_sv.py",
    "scripts/validate_results.py",
    "scripts/check_artifact.py",
    "scripts/check_paper.py",
    "scripts/build_paper_preview.py",
    "scripts/verify_paper_preview.py",
    "paper/pipesense_urtc_8page.tex",
    "paper/references.bib",
    "paper/README.md",
    "docs/artifact_checklist.md",
    "docs/artifact_status.md",
    "docs/formal_safety_plan.md",
    "docs/reference_model.md",
    "docs/reproducibility.md",
    "docs/requirements_traceability.md",
    "docs/reviewer_critique.md",
    "docs/evaluation_plan.md",
    "docs/hardware_realism.md",
    "docs/threats_to_validity.md",
    "docs/related_work.md",
    "docs/safety_proof_sketch.md",
    "docs/limitations_and_honesty.md",
    "docs/decisions.md",
    "formal/reconfig_safety_properties.sv",
    "formal/reconfig_unit_formal_harness.sv",
    "formal/reconfig_unit.sby",
    "formal/token_conservation_properties.sv",
    "formal/token_conservation_formal_harness.sv",
    "formal/token_conservation.sby",
    "verif/sva_safety.sv",
    "verif/cov_safety.sv",
    "verif/random_seq_gen.py",
    "verif/fuzz_runner.py",
    "synth/yosys_synth.tcl",
    "synth/yosys_area_proxy.v",
    "synth/generic_cells.lib_or_note.md",
]

PYTHON_FILES = [
    "scripts/run_sim.py",
    "scripts/analyze_results.py",
    "scripts/isa_reference.py",
    "scripts/compare_reference.py",
    "scripts/check_benchmark_parity.py",
    "scripts/plot_results.py",
    "scripts/run_sweep.py",
    "scripts/sweep_params.py",
    "scripts/synth_area_report.py",
    "scripts/estimate_hardware_cost.py",
    "scripts/audit_requirements.py",
    "scripts/lint_sv.py",
    "scripts/validate_results.py",
    "scripts/check_artifact.py",
    "scripts/check_paper.py",
    "scripts/build_paper_preview.py",
    "scripts/verify_paper_preview.py",
    "verif/random_seq_gen.py",
    "verif/fuzz_runner.py",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def check_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        fail("Missing required files: " + ", ".join(missing))


def check_ascii() -> None:
    bad: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if rel.parts[0] in {".git", "build", "results", "output"} or "__pycache__" in rel.parts:
            continue
        data = path.read_bytes()
        if any(byte > 127 for byte in data):
            bad.append(str(rel))
    if bad:
        fail("Non-ASCII files found: " + ", ".join(bad))


def check_python_compile() -> None:
    for rel in PYTHON_FILES:
        py_compile.compile(str(ROOT / rel), doraise=True)


def check_sv_contracts() -> None:
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "lint_sv.py")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        fail("SystemVerilog contract lint failed:\n" + proc.stdout)


def check_requirements_audit() -> None:
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "audit_requirements.py")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        fail("Requirements audit failed:\n" + proc.stdout)


def check_benchmark_parity() -> None:
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "check_benchmark_parity.py")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        fail("Benchmark parity check failed:\n" + proc.stdout)


def check_synthesis_proxy_contract() -> None:
    tcl_path = ROOT / "synth" / "yosys_synth.tcl"
    proxy_path = ROOT / "synth" / "yosys_area_proxy.v"
    tcl = tcl_path.read_text(encoding="utf-8").replace("\\", "/")
    proxy = proxy_path.read_text(encoding="utf-8")

    if "read_verilog synth/yosys_area_proxy.v" not in tcl:
        fail("Yosys synthesis script must read synth/yosys_area_proxy.v.")
    forbidden_terms = [
        "read_verilog rtl/",
        "read_verilog -sv rtl/",
        "rtl/hazard_unit.sv",
        "rtl/arm_like_core.sv",
        "shell mkdir",
    ]
    found_forbidden = [term for term in forbidden_terms if term in tcl]
    if found_forbidden:
        fail(
            "Yosys synthesis script must not parse full SystemVerilog RTL; found "
            + ", ".join(found_forbidden)
        )

    required_modules = [
        "module arm_like_core",
        "module pipeline_observer",
        "module adaptive_controller",
        "module reconfig_unit",
    ]
    missing_modules = [module for module in required_modules if module not in proxy]
    if missing_modules:
        fail("Yosys proxy is missing expected modules: " + ", ".join(missing_modules))


def check_fuzz_runner_contract() -> None:
    fuzz_path = ROOT / "verif" / "fuzz_runner.py"
    text = fuzz_path.read_text(encoding="utf-8")
    required_terms = [
        '"ERROR:" in line',
        '"assertion_failures"',
        'or row["assertion_failures"] != "0"',
    ]
    missing = [term for term in required_terms if term not in text]
    if missing:
        fail(
            "Fuzz runner must count simulator assertion errors and fail on them; missing "
            + ", ".join(missing)
        )


def run_analyzer_fixture() -> None:
    fixture = ROOT / "tests" / "fixtures" / "sample_sim_output.txt"
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir)
        proc = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "scripts" / "analyze_results.py"),
                str(fixture),
                "--out-dir",
                str(out_dir),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        if proc.returncode != 0:
            fail("Analyzer fixture failed:\n" + proc.stdout)

        result_csv = out_dir / "pipesense_results.csv"
        oracle_csv = out_dir / "oracle_gap.csv"
        if not result_csv.exists() or not oracle_csv.exists():
            fail("Analyzer did not write expected CSV outputs.")

        with result_csv.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 6:
            fail(f"Expected 6 fixture rows, found {len(rows)}")
        if any(row["safety_faults"] != "0" for row in rows):
            fail("Fixture unexpectedly contains safety faults.")

        with oracle_csv.open(newline="", encoding="utf-8") as f:
            oracle_rows = list(csv.DictReader(f))
        if len(oracle_rows) != 1:
            fail(f"Expected 1 oracle fixture row, found {len(oracle_rows)}")
        if oracle_rows[0]["best_fixed_mode"] != "fixed_hazard":
            fail("Oracle fixture did not select fixed_hazard as best fixed mode.")

        validate_proc = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "scripts" / "validate_results.py"),
                "--results-dir",
                str(out_dir),
                "--allow-subset",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if validate_proc.returncode != 0:
            fail("Result validator failed on fixture:\n" + validate_proc.stdout)


def run_reference_model_fixture() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir)
        csv_path = out_dir / "reference_model.csv"
        disasm_path = out_dir / "benchmark_disassembly.txt"
        proc = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "scripts" / "isa_reference.py"),
                "--out",
                str(csv_path),
                "--disasm",
                str(disasm_path),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if proc.returncode != 0:
            fail("ISA reference model failed:\n" + proc.stdout)
        if not csv_path.exists() or not disasm_path.exists():
            fail("ISA reference model did not write expected outputs.")
        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 8:
            fail(f"Expected 8 reference-model rows, found {len(rows)}")
        if any(row["timed_out"] != "False" for row in rows):
            fail("Reference model reported a benchmark timeout.")
        if any(int(row["retired"]) <= 0 for row in rows):
            fail("Reference model produced a nonpositive retired count.")

        fixture = ROOT / "tests" / "fixtures" / "sample_sim_output.txt"
        analyze_proc = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "scripts" / "analyze_results.py"),
                str(fixture),
                "--out-dir",
                str(out_dir),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if analyze_proc.returncode != 0:
            fail("Analyzer failed during reference comparison fixture:\n" + analyze_proc.stdout)

        compare_proc = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "scripts" / "compare_reference.py"),
                "--results-csv",
                str(out_dir / "pipesense_results.csv"),
                "--reference-csv",
                str(csv_path),
                "--allow-subset",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if compare_proc.returncode != 0:
            fail("Reference comparison failed on fixture:\n" + compare_proc.stdout)


def check_docs_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required_terms = [
        "safety_faults",
        "oracle_gap.csv",
        "hardware_cost_estimate.csv",
        "generic-cell area proxy",
        "fuzz_runner.py",
        "synth_area_report.py",
        "ARM-like",
    ]
    missing = [term for term in required_terms if term not in readme]
    if missing:
        fail("README is missing required research-contract terms: " + ", ".join(missing))


def check_paper_draft() -> None:
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "check_paper.py")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        fail("Paper draft check failed in check_paper.py:\n" + proc.stdout)

    preview_inputs = [
        ROOT / "results" / "adaptive_improvement.csv",
        ROOT / "results" / "oracle_gap.csv",
        ROOT / "results" / "hardware_cost_estimate.csv",
    ]
    if not all(path.exists() for path in preview_inputs):
        print("WARN skipped paper preview build; generated result CSVs are not present yet")
        return

    for script_name in ("build_paper_preview.py", "verify_paper_preview.py"):
        proc = subprocess.run(
            [str(PYTHON), str(ROOT / "scripts" / script_name)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"Paper draft check failed in {script_name}:\n" + proc.stdout)


def main() -> int:
    checks = [
        ("required files", check_required_files),
        ("ASCII", check_ascii),
        ("Python syntax", check_python_compile),
        ("SystemVerilog contracts", check_sv_contracts),
        ("requirements audit", check_requirements_audit),
        ("benchmark parity", check_benchmark_parity),
        ("synthesis proxy contract", check_synthesis_proxy_contract),
        ("fuzz runner contract", check_fuzz_runner_contract),
        ("analysis fixture", run_analyzer_fixture),
        ("ISA reference model", run_reference_model_fixture),
        ("documentation contract", check_docs_contract),
        ("paper draft", check_paper_draft),
    ]

    for name, check in checks:
        check()
        print(f"PASS {name}")

    print("No-simulator artifact checks passed. Run scripts/run_sim.py for full HDL validation.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
