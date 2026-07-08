#!/usr/bin/env python3
"""Paper2Agent-style MCP server for the PipeSense-ARM paper artifact.

This file intentionally keeps the agent wrapper separate from the core HDL,
paper, and result scripts. The helper functions are plain Python so they can be
self-tested without an MCP client; the MCP registration layer is loaded only
when the server is started.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("PIPESENSE_ROOT", Path(__file__).resolve().parents[3])).resolve()
REPORTS_DIR = ROOT / ".agents" / "pipesense_paper_agent" / "reports"
MAX_STDOUT_CHARS = 14000
MAX_FILE_CHARS = 24000
MAX_SEARCH_FILE_BYTES = 600_000
BLOCKED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
TEXT_SUFFIXES = {
    ".bib",
    ".csv",
    ".json",
    ".lib",
    ".md",
    ".py",
    ".sby",
    ".sv",
    ".svh",
    ".tcl",
    ".tex",
    ".txt",
    ".v",
    ".yml",
    ".yaml",
}


WORKFLOWS: dict[str, dict[str, Any]] = {
    "artifact_check": {
        "description": "Run the no-simulator repository checks, including paper checks where result CSVs exist.",
        "command": ["scripts/check_artifact.py"],
        "timeout_seconds": 180,
        "requires": "Python only",
        "evidence": ["README.md", "docs/artifact_status.md", "scripts/check_artifact.py"],
    },
    "research_audit": {
        "description": "Run a paper-facing research audit across checks, result evidence, claim boundaries, and known risks.",
        "command": ["agent_tool", "audit_research_package"],
        "timeout_seconds": 240,
        "requires": "Python only by default; optional heavy checks need HDL/synthesis tools",
        "evidence": [
            "paper/pipesense_urtc_8page.tex",
            "results/pipesense_results.csv",
            "results/safety/fuzz_summary.csv",
            "results/synth/area_summary.csv",
        ],
    },
    "limit_closure": {
        "description": "Assess whether the known research limits are mitigated, still open, or externally blocked.",
        "command": ["agent_tool", "assess_research_limit_closure"],
        "timeout_seconds": 120,
        "requires": "Existing result, sweep, synth, fuzz, and formal-result evidence",
        "evidence": [
            "results/sweep_results.csv",
            "results/sweep_runs.csv",
            "results/safety/fuzz_summary.csv",
            "results/synth/area_summary.csv",
            "formal/results/no_double_commit_across_mode_switch/PASS",
        ],
    },
    "paper_check": {
        "description": "Check manuscript placeholders, citations, claim language, and table-to-CSV alignment.",
        "command": ["scripts/check_paper.py"],
        "timeout_seconds": 90,
        "requires": "Python only",
        "evidence": ["paper/pipesense_urtc_8page.tex", "paper/references.bib", "scripts/check_paper.py"],
    },
    "result_validation": {
        "description": "Validate generated simulation CSVs before treating them as paper evidence.",
        "command": ["scripts/validate_results.py"],
        "timeout_seconds": 90,
        "requires": "Generated results/pipesense_results.csv and results/oracle_gap.csv",
        "evidence": ["results/pipesense_results.csv", "results/oracle_gap.csv"],
    },
    "simulation": {
        "description": "Compile and run the full SystemVerilog benchmark matrix, then analyze and validate results.",
        "command": ["scripts/run_sim.py"],
        "timeout_seconds": 420,
        "requires": "Icarus Verilog: iverilog and vvp",
        "evidence": ["results/sim_output.txt", "results/pipesense_results.csv"],
    },
    "safety_smoke": {
        "description": "Run a quick constrained-random safety regression.",
        "command": ["verif/fuzz_runner.py", "--seeds", "5"],
        "timeout_seconds": 300,
        "requires": "Icarus Verilog: iverilog and vvp",
        "evidence": ["results/safety/fuzz_summary.csv", "verif/sva_safety.sv"],
    },
    "paper_preview": {
        "description": "Build and verify the generated 8-page PDF preview without LaTeX.",
        "command": ["scripts/build_paper_preview.py", "&&", "scripts/verify_paper_preview.py"],
        "timeout_seconds": 180,
        "requires": "reportlab, Pillow, PyMuPDF",
        "evidence": ["output/pdf/pipesense_urtc_8page_preview.pdf"],
    },
    "hardware_cost": {
        "description": "Regenerate the transparent first-order hardware cost estimate CSV.",
        "command": ["scripts/estimate_hardware_cost.py"],
        "timeout_seconds": 60,
        "requires": "Python only",
        "evidence": ["results/hardware_cost_estimate.csv"],
    },
    "synth_area": {
        "description": "Run or parse the Yosys generic-cell area proxy.",
        "command": ["scripts/synth_area_report.py"],
        "timeout_seconds": 180,
        "requires": "Yosys unless using parse-only reports",
        "evidence": ["results/synth/area_summary.csv", "synth/yosys_area_proxy.v"],
    },
}


AGENT_INSTRUCTIONS = """You are the PipeSense-ARM paper agent.

Use repository evidence first. Distinguish measured HDL simulation results from
analytical estimates, generated previews, generic synthesis proxies, and unrun
workflows. When a user asks for a claim, cite the source file or generated CSV
that supports it. Prefer quick no-simulator checks before launching HDL, fuzz,
or synthesis workflows.
"""


def _clip(text: str, limit: int = MAX_STDOUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return f"{head}\n\n[... clipped {len(text) - limit} characters ...]\n\n{tail}"


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _resolve_repo_path(rel_path: str) -> Path:
    if not rel_path or rel_path.strip() in {".", "/"}:
        return ROOT
    cleaned = rel_path.replace("\\", "/").strip().lstrip("/")
    target = (ROOT / cleaned).resolve()
    if target != ROOT and ROOT not in target.parents:
        raise ValueError(f"Path escapes repository root: {rel_path}")
    if BLOCKED_PARTS.intersection(target.parts):
        raise ValueError(f"Path is not exposed through the paper agent: {rel_path}")
    return target


def _load_csv(rel_path: str) -> list[dict[str, str]]:
    path = _resolve_repo_path(rel_path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _file_info(rel_path: str) -> dict[str, Any]:
    path = _resolve_repo_path(rel_path)
    if not path.exists():
        return {"path": rel_path, "exists": False}
    stat = path.stat()
    return {
        "path": _repo_relative(path),
        "exists": True,
        "bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _format_command(args: list[str]) -> str:
    return " ".join(args)


def _python_command(script: str, *extra: str) -> list[str]:
    return [sys.executable, str(ROOT / script), *extra]


def _run_command(args: list[str], timeout_seconds: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "ok": False,
            "returncode": None,
            "timed_out": True,
            "command": _format_command(args),
            "stdout": _clip(output),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "returncode": 127,
            "timed_out": False,
            "command": _format_command(args),
            "stdout": str(exc),
        }

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "timed_out": False,
        "command": _format_command(args),
        "stdout": _clip(proc.stdout),
    }


def paper_agent_manifest() -> dict[str, Any]:
    """Return the paper-agent identity, exposed workflows, and main evidence files."""
    return {
        "name": "pipesense-arm-paper-agent",
        "paper": "PipeSense-ARM IEEE-style extended manuscript",
        "repository_root": str(ROOT),
        "paper2agent_mapping": {
            "tools": sorted(WORKFLOWS),
            "resources": [
                "README.md",
                "paper/pipesense_urtc_8page.tex",
                "docs/artifact_status.md",
                "docs/requirements_traceability.md",
                "results/*.csv",
            ],
            "prompt": "Act as a paper-specific research assistant that can inspect evidence and run artifact workflows.",
        },
        "instructions": AGENT_INSTRUCTIONS,
        "workflows": WORKFLOWS,
    }


def summarize_pipesense_paper() -> dict[str, Any]:
    """Summarize the paper contribution and the boundaries of supported claims."""
    result_csv = ROOT / "results" / "pipesense_results.csv"
    area_csv = ROOT / "results" / "synth" / "area_summary.csv"
    preview_pdf = ROOT / "output" / "pdf" / "pipesense_urtc_8page_preview.pdf"
    return {
        "research_question": (
            "Can a small hardware observer in an ARM-like educational embedded pipeline "
            "detect pipeline phases and safely reconfigure behavior to reduce stalls, "
            "improve IPC, and bound reconfiguration overhead?"
        ),
        "core_contributions": [
            "A five-stage ARM-like educational pipeline with observer taps and adaptive modes.",
            "A hardware-resident observer, adaptive controller, and reconfiguration unit.",
            "A benchmark/mode evaluation matrix comparing adaptive PipeSense with static and fixed modes.",
            "Safety and reproducibility scaffolding: checks, reference model, random safety regression, formal-property stubs, and paper validation.",
        ],
        "claim_boundaries": [
            "The design is ARM-like, not an ARM-compatible commercial processor.",
            "Energy values are an activity proxy, not calibrated power.",
            "Yosys output is a generic-cell area proxy, not ASIC or FPGA signoff.",
            "The generated PDF preview is for readability and page-count inspection; the LaTeX source remains canonical.",
        ],
        "available_evidence": {
            "simulation_results": result_csv.exists(),
            "synth_area_proxy": area_csv.exists(),
            "paper_preview_pdf": preview_pdf.exists(),
            "paper_source": (ROOT / "paper" / "pipesense_urtc_8page.tex").exists(),
        },
        "start_here": [
            "paper_agent_manifest",
            "list_artifact_workflows",
            "assess_research_limit_closure",
            "summarize_results",
            "search_project",
            "run_artifact_checks",
        ],
    }


def list_artifact_workflows() -> dict[str, Any]:
    """List workflows the agent can run and note which ones need external HDL tools."""
    return {"workflows": WORKFLOWS}


def run_artifact_checks() -> dict[str, Any]:
    """Run no-simulator artifact checks for repository, paper, and fixtures."""
    return _run_command(_python_command("scripts/check_artifact.py"), WORKFLOWS["artifact_check"]["timeout_seconds"])


def run_paper_check() -> dict[str, Any]:
    """Validate manuscript citations, claim discipline, placeholders, and result-table alignment."""
    return _run_command(_python_command("scripts/check_paper.py"), WORKFLOWS["paper_check"]["timeout_seconds"])


def run_result_validation() -> dict[str, Any]:
    """Validate existing generated CSVs in the results directory."""
    return _run_command(_python_command("scripts/validate_results.py"), WORKFLOWS["result_validation"]["timeout_seconds"])


def run_simulation(iverilog: str = "", vvp: str = "", timeout_seconds: int = 420) -> dict[str, Any]:
    """Run the full HDL benchmark workflow, optionally with explicit Icarus Verilog paths."""
    args = _python_command("scripts/run_sim.py")
    if iverilog:
        args.extend(["--iverilog", iverilog])
    if vvp:
        args.extend(["--vvp", vvp])
    timeout = max(30, min(int(timeout_seconds), 1800))
    return _run_command(args, timeout)


def run_safety_smoke(seeds: int = 5, timeout_seconds: int = 300) -> dict[str, Any]:
    """Run a bounded constrained-random safety regression."""
    safe_seeds = max(1, min(int(seeds), 500))
    timeout = max(30, min(int(timeout_seconds), 1800))
    return _run_command(_python_command("verif/fuzz_runner.py", "--seeds", str(safe_seeds)), timeout)


def build_and_verify_paper_preview() -> dict[str, Any]:
    """Build the generated PDF preview and verify page count/readability outputs."""
    build = _run_command(_python_command("scripts/build_paper_preview.py"), 120)
    if not build["ok"]:
        return {"ok": False, "stage": "build", "build": build}
    verify = _run_command(_python_command("scripts/verify_paper_preview.py"), 120)
    return {"ok": verify["ok"], "stage": "verify", "build": build, "verify": verify}


def run_hardware_cost_estimate() -> dict[str, Any]:
    """Regenerate the transparent analytical hardware-cost estimate."""
    return _run_command(_python_command("scripts/estimate_hardware_cost.py"), WORKFLOWS["hardware_cost"]["timeout_seconds"])


def run_synth_area_proxy(parse_only: bool = False, timeout_seconds: int = 180) -> dict[str, Any]:
    """Run or parse the Yosys generic-cell area proxy."""
    args = _python_command("scripts/synth_area_report.py")
    if parse_only:
        args.append("--parse-only")
    timeout = max(30, min(int(timeout_seconds), 900))
    return _run_command(args, timeout)


def summarize_results() -> dict[str, Any]:
    """Summarize generated result CSVs into paper-facing evidence."""
    results = _load_csv("results/pipesense_results.csv")
    improvements = _load_csv("results/adaptive_improvement.csv")
    oracle = _load_csv("results/oracle_gap.csv")
    ablations = _load_csv("results/ablation_summary.csv")
    area = _load_csv("results/synth/area_summary.csv")

    if not results:
        return {
            "status": "missing_results",
            "message": "No results/pipesense_results.csv found. Run run_simulation or scripts/run_sim.py first.",
            "available_files": {
                "adaptive_improvement.csv": bool(improvements),
                "oracle_gap.csv": bool(oracle),
                "ablation_summary.csv": bool(ablations),
                "area_summary.csv": bool(area),
            },
        }

    benches = sorted({row.get("bench", "") for row in results if row.get("bench")})
    modes = sorted({row.get("mode", "") for row in results if row.get("mode")})
    safety_faults = sum(int(row.get("safety_faults", "0") or 0) for row in results)
    timeouts = sum(int(row.get("timed_out", "0") or 0) for row in results)

    mode_totals: dict[str, dict[str, float]] = {}
    for row in results:
        mode = row.get("mode", "unknown")
        entry = mode_totals.setdefault(mode, {"cycles": 0.0, "energy": 0.0, "retired": 0.0})
        entry["cycles"] += float(row.get("cycles", 0) or 0)
        entry["energy"] += float(row.get("energy", 0) or 0)
        entry["retired"] += float(row.get("retired", 0) or 0)

    def _avg(rows: list[dict[str, str]], field: str) -> float | None:
        values = [float(row[field]) for row in rows if row.get(field) not in {"", None}]
        if not values:
            return None
        return round(sum(values) / len(values), 3)

    return {
        "status": "ok",
        "result_rows": len(results),
        "benchmarks": benches,
        "modes": modes,
        "safety_faults": safety_faults,
        "timeouts": timeouts,
        "mode_totals": mode_totals,
        "adaptive_vs_static_normal": {
            "rows": len(improvements),
            "avg_cycle_reduction_pct": _avg(improvements, "cycle_reduction_pct"),
            "avg_ipc_improvement_pct": _avg(improvements, "ipc_improvement_pct"),
            "avg_energy_reduction_pct": _avg(improvements, "energy_reduction_pct"),
        },
        "adaptive_vs_best_fixed": {
            "rows": len(oracle),
            "avg_cycle_gap_pct": _avg(oracle, "adaptive_gap_to_best_fixed_pct"),
            "avg_energy_gap_pct": _avg(oracle, "adaptive_energy_gap_to_best_fixed_pct"),
        },
        "ablation_rows": len(ablations),
        "area_rows": len(area),
        "evidence_files": [
            "results/pipesense_results.csv",
            "results/adaptive_improvement.csv",
            "results/oracle_gap.csv",
            "results/ablation_summary.csv",
            "results/synth/area_summary.csv",
        ],
    }


def _summarize_fuzz_results() -> dict[str, Any]:
    rows = _load_csv("results/safety/fuzz_summary.csv")
    coverage = _load_csv("results/safety/fuzz_coverage.csv")
    if not rows:
        return {
            "status": "missing",
            "message": "No results/safety/fuzz_summary.csv found.",
            "evidence_files": ["results/safety/fuzz_summary.csv", "results/safety/fuzz_coverage.csv"],
        }

    failures = [
        row for row in rows
        if row.get("return_code") != "0"
        or row.get("safety_faults") != "0"
        or row.get("timed_out") != "0"
        or row.get("assertion_failures") != "0"
    ]
    seeds = sorted({row.get("seed", "") for row in rows if row.get("seed")})
    modes = sorted({row.get("mode", "") for row in rows if row.get("mode")})
    return {
        "status": "ok" if not failures else "failures_present",
        "rows": len(rows),
        "seed_count": len(seeds),
        "modes": modes,
        "failures": len(failures),
        "coverage_rows": len(coverage),
        "evidence_files": ["results/safety/fuzz_summary.csv", "results/safety/fuzz_coverage.csv"],
    }


def _summarize_sweep_results() -> dict[str, Any]:
    runs = _load_csv("results/sweep_runs.csv")
    results = _load_csv("results/sweep_results.csv")
    comparisons = _load_csv("results/sweep_adaptive_vs_fixed.csv")
    if not runs and not results:
        return {
            "status": "missing",
            "message": "No sweep evidence found.",
            "evidence_files": [
                "results/sweep_runs.csv",
                "results/sweep_results.csv",
                "results/sweep_adaptive_vs_fixed.csv",
            ],
        }

    failed_runs = [row for row in runs if row.get("return_code") not in {"0", 0}]
    windows = sorted({row.get("obs_window", "") for row in runs if row.get("obs_window")})
    residencies = sorted({row.get("min_residency", "") for row in runs if row.get("min_residency")})
    profiles = sorted({row.get("threshold_profile", "") for row in runs if row.get("threshold_profile")})
    seeds = sorted({row.get("seed", "") for row in runs if row.get("seed")})
    benches = sorted({row.get("bench", "") for row in results if row.get("bench")})
    non_wins = [row for row in comparisons if row.get("adaptive_wins_cycles") not in {"True", "true", "1"}]

    return {
        "status": "ok" if not failed_runs else "failures_present",
        "run_count": len(runs),
        "result_rows": len(results),
        "comparison_rows": len(comparisons),
        "failed_runs": len(failed_runs),
        "windows": windows,
        "residencies": residencies,
        "threshold_profiles": profiles,
        "seeds": seeds,
        "benchmarks": benches,
        "adaptive_non_win_cells": len(non_wins),
        "evidence_files": [
            "results/sweep_runs.csv",
            "results/sweep_results.csv",
            "results/sweep_adaptive_vs_fixed.csv",
        ],
    }


def _summarize_area_proxy() -> dict[str, Any]:
    rows = _load_csv("results/synth/area_summary.csv")
    cost = _load_csv("results/hardware_cost_estimate.csv")
    if not rows:
        return {
            "status": "missing",
            "message": "No generic-cell area proxy summary found.",
            "evidence_files": ["results/synth/area_summary.csv", "results/hardware_cost_estimate.csv"],
        }

    by_module = {row.get("module", ""): row for row in rows}
    core = by_module.get("arm_like_core", {})
    total = by_module.get("observer_controller_reconfig_total", {})
    return {
        "status": "ok" if core and total else "partial",
        "rows": len(rows),
        "cost_rows": len(cost),
        "core_cells": core.get("number_of_cells"),
        "observer_controller_reconfig_cells": total.get("number_of_cells"),
        "overhead_vs_core_pct": total.get("overhead_vs_core_pct"),
        "proxy_statuses": sorted({row.get("status", "") for row in rows if row.get("status")}),
        "evidence_files": ["results/synth/area_summary.csv", "results/hardware_cost_estimate.csv"],
    }


def _summarize_formal_evidence() -> dict[str, Any]:
    no_double_dir = ROOT / "formal" / "results" / "no_double_commit_across_mode_switch"
    no_double_pass = no_double_dir / "PASS"
    no_double_status = no_double_dir / "status"
    token_pass = ROOT / "formal" / "results" / "token_conservation" / "PASS"
    status_text = ""
    if no_double_status.exists():
        status_text = no_double_status.read_text(encoding="utf-8", errors="replace").strip()
    return {
        "status": "ok" if no_double_pass.exists() else "partial",
        "no_double_commit_pass": no_double_pass.exists(),
        "no_double_commit_status": status_text,
        "token_conservation_pass": token_pass.exists(),
        "sby_files": [
            _repo_relative(path)
            for path in sorted((ROOT / "formal").glob("*.sby"))
        ],
        "evidence_files": [
            "formal/results/no_double_commit_across_mode_switch/PASS",
            "formal/results/no_double_commit_across_mode_switch/status",
            "formal/no_double_commit_across_mode_switch.sby",
            "formal/token_conservation.sby",
            "docs/safety_proof_sketch.md",
        ],
    }


def _summarize_evidence_files() -> dict[str, Any]:
    expected = [
        "README.md",
        "paper/pipesense_urtc_8page.tex",
        "paper/references.bib",
        "docs/artifact_status.md",
        "docs/threats_to_validity.md",
        "docs/limitations_and_honesty.md",
        "results/pipesense_results.csv",
        "results/adaptive_improvement.csv",
        "results/oracle_gap.csv",
        "results/ablation_summary.csv",
        "results/sweep_results.csv",
        "results/safety/fuzz_summary.csv",
        "results/synth/area_summary.csv",
        "output/pdf/pipesense_urtc_8page_preview.pdf",
    ]
    files = [_file_info(path) for path in expected]
    return {
        "files": files,
        "missing": [item["path"] for item in files if not item["exists"]],
    }


def _scan_research_claims() -> dict[str, Any]:
    targets = [
        "README.md",
        "paper/pipesense_urtc_8page.tex",
        "docs/artifact_status.md",
        "docs/threats_to_validity.md",
        "docs/limitations_and_honesty.md",
        "docs/hardware_realism.md",
        "docs/formal_safety_plan.md",
        "docs/safety_proof_sketch.md",
        "docs/results_template.md",
    ]
    placeholder_re = re.compile(r"\b(TODO|TBD|FIXME)\b|\?\?")
    strong_claim_re = re.compile(
        r"\b(guarantee[sd]?|prove[sn]?|proven|optimal|state-of-the-art|"
        r"ARM-compatible|real power|ASIC|FPGA)\b",
        re.IGNORECASE,
    )
    strong_claim_context_ok = (
        "not ",
        "not a ",
        "not an ",
        "not calibrated",
        "not arm-compatible",
        "bounded",
        "abstract",
        "does not prove",
        "proof path",
        "scaffold",
        "should not",
        "should prove",
        "target technology",
        "would ",
        "could prove",
        "could report",
        "future",
        "threat",
        "limitation",
    )

    placeholders: list[dict[str, Any]] = []
    review_flags: list[dict[str, Any]] = []
    for rel_path in targets:
        path = _resolve_repo_path(rel_path)
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(lines, start=1):
            stripped = re.sub(r"\s+", " ", line).strip()
            if placeholder_re.search(stripped):
                placeholders.append({"path": rel_path, "line": line_no, "snippet": stripped[:240]})
            if strong_claim_re.search(stripped):
                context_lines = lines[max(0, line_no - 4): min(len(lines), line_no + 2)]
                lowered = " ".join(context_lines).lower()
                if not any(marker in lowered for marker in strong_claim_context_ok):
                    review_flags.append({"path": rel_path, "line": line_no, "snippet": stripped[:240]})

    return {
        "placeholders": placeholders,
        "strong_claims_to_review": review_flags[:50],
        "strong_claims_truncated": len(review_flags) > 50,
    }


def _limit_status(ok: bool, mitigated: str, open_status: str) -> str:
    return mitigated if ok else open_status


def _write_limit_closure_reports(closure: dict[str, Any]) -> dict[str, str]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "research_limit_closure.json"
    md_path = REPORTS_DIR / "research_limit_closure.md"
    json_path.write_text(json.dumps(closure, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# PipeSense-ARM Research Limit Closure",
        "",
        f"Generated: {closure['generated_utc']}",
        f"Overall status: {closure['overall_status']}",
        "",
        "## Bottom Line",
        closure["bottom_line"],
        "",
        "## Limits",
    ]
    for item in closure["limits"]:
        lines.extend(
            [
                "",
                f"### {item['area']}",
                f"- Status: {item['status']}",
                f"- What the agent can fix: {item['agent_can_fix']}",
                f"- What remains external: {item['external_limit']}",
                f"- Next action: {item['next_action']}",
                "- Evidence:",
            ]
        )
        for evidence in item["evidence"]:
            lines.append(f"  - {evidence}")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def assess_research_limit_closure(write_report: bool = True) -> dict[str, Any]:
    """Assess how far the agent can close the known research limitations.

    The result distinguishes limits that are now mitigated for the current
    paper scope from limits that require new external evidence, such as a
    target FPGA/ASIC flow or a full-core formal proof.
    """
    result_summary = summarize_results()
    sweep_summary = _summarize_sweep_results()
    fuzz_summary = _summarize_fuzz_results()
    area_proxy = _summarize_area_proxy()
    formal = _summarize_formal_evidence()

    benchmark_count = len(result_summary.get("benchmarks", [])) if result_summary.get("status") == "ok" else 0
    workload_ok = (
        result_summary.get("status") == "ok"
        and benchmark_count >= 10
        and sweep_summary.get("status") == "ok"
        and int(sweep_summary.get("run_count", 0)) >= 27
    )
    hardware_ok = (
        area_proxy.get("status") == "ok"
        and bool(area_proxy.get("core_cells"))
        and bool(area_proxy.get("observer_controller_reconfig_cells"))
        and int(area_proxy.get("cost_rows", 0)) > 0
    )
    formal_ok = (
        fuzz_summary.get("status") == "ok"
        and int(fuzz_summary.get("seed_count", 0)) >= 500
        and bool(formal.get("no_double_commit_pass"))
    )

    limits = [
        {
            "area": "Workload validity",
            "status": _limit_status(workload_ok, "mitigated_for_current_paper_scope", "needs_more_evidence"),
            "agent_can_fix": (
                "Run and summarize the benchmark matrix, preserve negative cases, verify reference-model parity, "
                "and use the 27-configuration sensitivity sweep as robustness evidence."
            ),
            "external_limit": (
                "A publication-standard workload suite or compiler-generated embedded benchmark ports would still "
                "be needed for broad architecture claims."
            ),
            "next_action": (
                "Keep claims scoped to the current 10-benchmark prototype suite, or add real/compiler-generated "
                "benchmark ports before making broad workload claims."
            ),
            "evidence": [
                f"{benchmark_count} benchmark rows summarized from results/pipesense_results.csv",
                f"{sweep_summary.get('run_count', 0)} sweep configurations in results/sweep_runs.csv",
                "results/sweep_adaptive_vs_fixed.csv records adaptive wins and non-wins",
                "results/ablation_summary.csv separates observer/controller/reconfiguration effects",
            ],
        },
        {
            "area": "Hardware realism",
            "status": _limit_status(hardware_ok, "proxy_evidence_complete", "needs_proxy_or_calibrated_evidence"),
            "agent_can_fix": (
                "Regenerate the analytical hardware-cost estimate, parse the Yosys generic-cell proxy, "
                "and enforce wording that labels energy and area as proxies."
            ),
            "external_limit": (
                "Calibrated power, timing, FPGA utilization, or ASIC area requires a target toolchain and target technology."
            ),
            "next_action": (
                "Use the proxy numbers for transparent overhead discussion, then run an FPGA or ASIC flow if the paper "
                "needs physical implementation claims."
            ),
            "evidence": [
                f"baseline core cells: {area_proxy.get('core_cells', 'n/a')}",
                f"observer/controller/reconfiguration cells: {area_proxy.get('observer_controller_reconfig_cells', 'n/a')}",
                f"proxy overhead vs core: {area_proxy.get('overhead_vs_core_pct', 'n/a')}%",
                f"{area_proxy.get('cost_rows', 0)} analytical cost rows in results/hardware_cost_estimate.csv",
            ],
        },
        {
            "area": "Formal coverage",
            "status": _limit_status(formal_ok, "bounded_safety_evidence_complete", "needs_stronger_formal_evidence"),
            "agent_can_fix": (
                "Run simulation assertions, summarize the 500-seed safety fuzz evidence, and track the bounded "
                "no-double-commit proof result."
            ),
            "external_limit": (
                "A full-core formal proof bound directly to arm_like_core is still a research task, not a report-generation step."
            ),
            "next_action": (
                "Present bounded safety evidence honestly now; implement a reduced full-core formal harness before claiming "
                "complete processor correctness."
            ),
            "evidence": [
                f"{fuzz_summary.get('seed_count', 0)} fuzz seeds in results/safety/fuzz_summary.csv",
                f"{fuzz_summary.get('failures', 'n/a')} fuzz failures",
                f"no-double-commit bounded proof PASS: {formal.get('no_double_commit_pass')}",
                "docs/safety_proof_sketch.md maps invariants to monitors and formal jobs",
            ],
        },
    ]

    externally_open = [item for item in limits if "complete" not in item["status"] and "mitigated" not in item["status"]]
    closure = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(ROOT),
        "overall_status": "actionable_limits_closed_for_current_scope" if not externally_open else "limits_need_attention",
        "bottom_line": (
            "The agent can close the audit findings for the current prototype-paper scope by verifying and reporting "
            "the existing evidence. It cannot honestly erase the need for real workload ports, target hardware "
            "calibration, or a full-core proof if the claims expand."
        ),
        "limits": limits,
        "evidence_summaries": {
            "results": result_summary,
            "sweeps": sweep_summary,
            "fuzz": fuzz_summary,
            "area_proxy": area_proxy,
            "formal": formal,
        },
    }
    if write_report:
        closure["report_paths"] = _write_limit_closure_reports(closure)
    return closure


def _known_research_risks(audit: dict[str, Any]) -> list[dict[str, str]]:
    closure = audit.get("limit_closure") or assess_research_limit_closure(write_report=False)
    risks: list[dict[str, str]] = []
    for item in closure.get("limits", []):
        status = item.get("status", "")
        priority = "P3" if "complete" in status or "mitigated" in status else "P2"
        risks.append(
            {
                "priority": priority,
                "area": item["area"],
                "finding": f"{status}: {item['external_limit']}",
                "evidence": "; ".join(item["evidence"][:2]),
            }
        )
    return risks



def _build_research_findings(audit: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for name, result in audit.get("checks", {}).items():
        if not result.get("ok"):
            findings.append(
                {
                    "priority": "P1",
                    "area": "Executable check",
                    "finding": f"{name} failed or did not complete.",
                    "evidence": result.get("command", name),
                }
            )

    result_summary = audit.get("result_summary", {})
    if result_summary.get("status") == "missing_results":
        findings.append(
            {
                "priority": "P1",
                "area": "Result evidence",
                "finding": "Simulation result CSVs are missing, so performance claims are not currently backed by local generated evidence.",
                "evidence": "results/pipesense_results.csv",
            }
        )
    elif result_summary.get("status") == "ok":
        if int(result_summary.get("safety_faults", 0)) != 0 or int(result_summary.get("timeouts", 0)) != 0:
            findings.append(
                {
                    "priority": "P1",
                    "area": "Result evidence",
                    "finding": "Simulation results contain safety faults or timeouts.",
                    "evidence": "results/pipesense_results.csv",
                }
            )

    fuzz = audit.get("fuzz_summary", {})
    if fuzz.get("status") == "missing":
        findings.append(
            {
                "priority": "P2",
                "area": "Safety evidence",
                "finding": "Constrained-random safety summary is missing.",
                "evidence": "results/safety/fuzz_summary.csv",
            }
        )
    elif fuzz.get("failures", 0):
        findings.append(
            {
                "priority": "P1",
                "area": "Safety evidence",
                "finding": "Constrained-random safety summary contains failures.",
                "evidence": "results/safety/fuzz_summary.csv",
            }
        )

    missing = audit.get("evidence_files", {}).get("missing", [])
    important_missing = [path for path in missing if not path.startswith("output/pdf/")]
    if important_missing:
        findings.append(
            {
                "priority": "P2",
                "area": "Evidence files",
                "finding": "Expected research evidence files are missing: " + ", ".join(important_missing),
                "evidence": ".agents/pipesense_paper_agent/reports/research_audit.json",
            }
        )

    claims = audit.get("claim_scan", {})
    if claims.get("placeholders"):
        findings.append(
            {
                "priority": "P1",
                "area": "Manuscript hygiene",
                "finding": "Unresolved placeholders were found in research-facing text.",
                "evidence": "claim_scan.placeholders",
            }
        )
    if claims.get("strong_claims_to_review"):
        findings.append(
            {
                "priority": "P3",
                "area": "Claim wording",
                "finding": "Potentially strong claim wording should be reviewed for evidence scope.",
                "evidence": "claim_scan.strong_claims_to_review",
            }
        )

    findings.extend(_known_research_risks(audit))
    return findings


def _write_research_audit_reports(audit: dict[str, Any]) -> dict[str, str]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "research_audit.json"
    md_path = REPORTS_DIR / "research_audit.md"

    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")

    checks = audit.get("checks", {})
    findings = audit.get("findings", [])
    result_summary = audit.get("result_summary", {})
    fuzz = audit.get("fuzz_summary", {})
    evidence = audit.get("evidence_files", {})
    limit_closure = audit.get("limit_closure", {})
    lines = [
        "# PipeSense-ARM Research Audit",
        "",
        f"Generated: {audit['generated_utc']}",
        f"Overall status: {audit['overall_status']}",
        "",
        "## Check Results",
    ]
    for name, result in checks.items():
        status = "PASS" if result.get("ok") else "FAIL"
        lines.append(f"- {status} {name}: `{result.get('command', name)}`")
    lines.extend(
        [
            "",
            "## Result Evidence",
            f"- Simulation rows: {result_summary.get('result_rows', 'n/a')}",
            f"- Benchmarks: {len(result_summary.get('benchmarks', [])) if isinstance(result_summary.get('benchmarks'), list) else 'n/a'}",
            f"- Safety faults: {result_summary.get('safety_faults', 'n/a')}",
            f"- Timeouts: {result_summary.get('timeouts', 'n/a')}",
            f"- Fuzz seeds: {fuzz.get('seed_count', 'n/a')}",
            f"- Fuzz failures: {fuzz.get('failures', 'n/a')}",
            "",
            "## Limit Closure",
            f"- Status: {limit_closure.get('overall_status', 'n/a')}",
            f"- Summary: {limit_closure.get('bottom_line', 'n/a')}",
            "",
            "## Findings",
        ]
    )
    if findings:
        for finding in findings:
            lines.append(
                f"- {finding['priority']} {finding['area']}: {finding['finding']} "
                f"(evidence: {finding['evidence']})"
            )
    else:
        lines.append("- No findings.")
    lines.extend(["", "## Missing Evidence Files"])
    missing = evidence.get("missing", [])
    if missing:
        for path in missing:
            lines.append(f"- {path}")
    else:
        lines.append("- None")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def audit_research_package(
    run_checks: bool = True,
    include_heavy: bool = False,
    write_report: bool = True,
) -> dict[str, Any]:
    """Audit the research package for evidence, claim discipline, and reproducibility.

    By default this uses fast checks and existing result files. Set
    include_heavy=True to also run a five-seed safety smoke test and parse the
    Yosys area proxy, which may require external tools depending on the machine.
    """
    audit: dict[str, Any] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(ROOT),
        "checks": {},
        "include_heavy": bool(include_heavy),
    }

    if run_checks:
        audit["checks"]["paper_check"] = run_paper_check()
        audit["checks"]["artifact_check"] = run_artifact_checks()
        if (ROOT / "results" / "pipesense_results.csv").exists():
            audit["checks"]["result_validation"] = run_result_validation()

    if include_heavy:
        audit["checks"]["safety_smoke"] = run_safety_smoke(seeds=5)
        audit["checks"]["synth_area_parse"] = run_synth_area_proxy(parse_only=True)

    audit["result_summary"] = summarize_results()
    audit["fuzz_summary"] = _summarize_fuzz_results()
    audit["evidence_files"] = _summarize_evidence_files()
    audit["claim_scan"] = _scan_research_claims()
    audit["limit_closure"] = assess_research_limit_closure(write_report=False)
    audit["findings"] = _build_research_findings(audit)
    blocking = [finding for finding in audit["findings"] if finding["priority"] == "P1"]
    closure_status = audit["limit_closure"].get("overall_status")
    if blocking:
        audit["overall_status"] = "needs_attention"
    elif closure_status == "actionable_limits_closed_for_current_scope":
        audit["overall_status"] = "usable_with_mitigated_limits"
    else:
        audit["overall_status"] = "usable_with_known_limits"

    if write_report:
        audit["report_paths"] = _write_research_audit_reports(audit)
    return audit


def read_project_file(rel_path: str, max_chars: int = MAX_FILE_CHARS) -> dict[str, Any]:
    """Read a repository text file with path safety and output clipping."""
    path = _resolve_repo_path(rel_path)
    if not path.exists():
        return {"ok": False, "error": f"File does not exist: {rel_path}"}
    if not path.is_file():
        return {"ok": False, "error": f"Path is not a file: {rel_path}"}
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return {"ok": False, "error": f"Unsupported non-text suffix: {path.suffix}"}
    limit = max(1000, min(int(max_chars), 100_000))
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "ok": True,
        "path": _repo_relative(path),
        "chars": len(text),
        "contents": _clip(text, limit),
    }


def search_project(query: str, max_matches: int = 30) -> dict[str, Any]:
    """Search repository text files for a literal query and return file/line snippets."""
    needle = query.strip()
    if len(needle) < 2:
        return {"ok": False, "error": "Search query must be at least two characters."}

    matches: list[dict[str, Any]] = []
    lowered = needle.lower()
    limit = max(1, min(int(max_matches), 100))
    for path in sorted(ROOT.rglob("*")):
        if len(matches) >= limit:
            break
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel_parts = set(path.relative_to(ROOT).parts)
        if BLOCKED_PARTS.intersection(rel_parts):
            continue
        if path.stat().st_size > MAX_SEARCH_FILE_BYTES:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            if lowered in line.lower():
                snippet = re.sub(r"\s+", " ", line).strip()
                matches.append({"path": _repo_relative(path), "line": line_no, "snippet": snippet[:280]})
                if len(matches) >= limit:
                    break
    return {"ok": True, "query": needle, "matches": matches, "truncated": len(matches) >= limit}


def run_named_workflow(name: str) -> dict[str, Any]:
    """Run a workflow by name for clients that prefer a single dispatch tool."""
    normalized = name.strip().lower().replace("-", "_")
    if normalized == "artifact_check":
        return run_artifact_checks()
    if normalized == "research_audit":
        return audit_research_package()
    if normalized in {"limit_closure", "research_limit_closure"}:
        return assess_research_limit_closure()
    if normalized == "paper_check":
        return run_paper_check()
    if normalized == "result_validation":
        return run_result_validation()
    if normalized == "simulation":
        return run_simulation()
    if normalized == "safety_smoke":
        return run_safety_smoke()
    if normalized == "paper_preview":
        return build_and_verify_paper_preview()
    if normalized == "hardware_cost":
        return run_hardware_cost_estimate()
    if normalized == "synth_area":
        return run_synth_area_proxy()
    return {"ok": False, "error": f"Unknown workflow: {name}", "available": sorted(WORKFLOWS)}


def _register_tool(mcp: Any, func: Any) -> None:
    try:
        mcp.tool()(func)
    except TypeError:
        mcp.tool(func)


def create_mcp() -> Any:
    """Create the FastMCP server and register paper tools."""
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "fastmcp is required to run this server. Install with: "
            "python -m pip install -r .agents/pipesense_paper_agent/requirements.txt"
        ) from exc

    try:
        mcp = FastMCP("pipesense-arm-paper-agent", instructions=AGENT_INSTRUCTIONS)
    except TypeError:
        mcp = FastMCP("pipesense-arm-paper-agent")

    for func in [
        paper_agent_manifest,
        summarize_pipesense_paper,
        list_artifact_workflows,
        audit_research_package,
        assess_research_limit_closure,
        run_artifact_checks,
        run_paper_check,
        run_result_validation,
        run_simulation,
        run_safety_smoke,
        build_and_verify_paper_preview,
        run_hardware_cost_estimate,
        run_synth_area_proxy,
        summarize_results,
        read_project_file,
        search_project,
        run_named_workflow,
    ]:
        _register_tool(mcp, func)
    return mcp


def self_test() -> int:
    """Run light checks that do not require FastMCP or HDL tools."""
    checks = {
        "root_exists": ROOT.exists(),
        "readme_exists": (ROOT / "README.md").exists(),
        "paper_exists": (ROOT / "paper" / "pipesense_urtc_8page.tex").exists(),
        "manifest_has_workflows": bool(paper_agent_manifest()["workflows"]),
        "summary_has_question": bool(summarize_pipesense_paper()["research_question"]),
        "limit_closure_has_three_areas": len(assess_research_limit_closure(write_report=False)["limits"]) == 3,
        "search_finds_adaptive": bool(search_project("adaptive", max_matches=3)["matches"]),
    }
    print(json.dumps(checks, indent=2, sort_keys=True))
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("Paper agent self-test passed.")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run light checks without starting MCP.")
    parser.add_argument("--manifest", action="store_true", help="Print the agent manifest as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_test:
        return self_test()
    if args.manifest:
        print(json.dumps(paper_agent_manifest(), indent=2, sort_keys=True))
        return 0
    mcp = create_mcp()
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
