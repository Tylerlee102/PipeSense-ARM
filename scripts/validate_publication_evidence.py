#!/usr/bin/env python3
"""Validate schemas, units, uniqueness, reconciliations, and rendered evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = RESULTS / "publication"
MESSAGES: list[str] = []
ERRORS: list[str] = []


def note(message: str) -> None:
    MESSAGES.append(f"PASS {message}")


def fail(message: str) -> None:
    ERRORS.append(f"FAIL {message}")


def load(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        fail(f"missing CSV {path.relative_to(ROOT)}")
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            fail(f"{path.relative_to(ROOT)} missing schema fields {sorted(missing)}")
        rows = list(reader)
    for index, row in enumerate(rows, start=2):
        empty = [key for key in required if row.get(key, "") == ""]
        if empty:
            fail(f"{path.relative_to(ROOT)} row {index} has missing values {empty}")
    note(f"schema and required values: {path.relative_to(ROOT)} ({len(rows)} rows)")
    return rows


def validate_sweep() -> None:
    runs = load(
        RESULTS / "sweep_runs.csv",
        {"sweep_tag", "obs_window", "min_residency", "threshold_profile", "seed", "return_code",
         "branch_threshold", "mem_threshold", "load_use_threshold", "frontend_threshold", "idle_threshold"},
    )
    results = load(
        RESULTS / "sweep_results.csv",
        {"sweep_tag", "bench", "mode", "cycles", "retired", "ipc", "cpi", "energy", "reconfigs",
         "safety_faults", "timed_out", "obs_window", "min_residency", "threshold_profile", "seed"},
    )
    configurations = {
        (row["obs_window"], row["min_residency"], row["threshold_profile"], row["seed"])
        for row in runs
    }
    if len(runs) != 27 or len(configurations) != 27:
        fail(f"sweep must contain exactly 27 unique configurations; rows={len(runs)} unique={len(configurations)}")
    else:
        note("sweep contains exactly 27 unique configurations")
    failed = [row["sweep_tag"] for row in runs if row["return_code"] != "0"]
    if failed:
        fail(f"failed sweep configurations: {failed}")
    else:
        note("failed sweep configurations: none")
    tags = [row["sweep_tag"] for row in runs]
    if len(tags) != len(set(tags)):
        fail("duplicate sweep tags")
    keys = [(row["sweep_tag"], row["bench"], row["mode"]) for row in results]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        fail(f"duplicate sweep result keys: {duplicates[:5]}")
    else:
        note("no duplicate sweep result rows")
    by_tag: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in results:
        by_tag[row["sweep_tag"]].append(row)
        cycles = int(row["cycles"])
        retired = int(row["retired"])
        if abs(float(row["ipc"]) - retired / cycles) > 0.00011:
            fail(f"IPC unit mismatch at {row['sweep_tag']}/{row['bench']}/{row['mode']}")
        if abs(float(row["cpi"]) - cycles / retired) > 0.00011:
            fail(f"CPI unit mismatch at {row['sweep_tag']}/{row['bench']}/{row['mode']}")
    bad_shapes = {tag: len(rows) for tag, rows in by_tag.items() if len(rows) != 78}
    if bad_shapes:
        fail(f"sweep configurations without 78 directed rows: {bad_shapes}")
    else:
        note("all sweep configurations contain 13 workloads x 6 modes")
    if not any("IPC unit mismatch" in error or "CPI unit mismatch" in error for error in ERRORS):
        note("IPC/CPI units reconcile with retired instructions and cycles")

    summary = load(
        OUT / "sweep_configuration_summary.csv",
        {"configuration_id", "sweep_tag", "workload_count", "total_cycles", "total_retired", "aggregate_ipc",
         "total_energy_proxy_units", "total_transitions", "total_safety_faults", "total_timeouts", "run_return_code"},
    )
    for row in summary:
        adaptive = [item for item in by_tag[row["sweep_tag"]] if item["mode"] == "adaptive_pipesense"]
        expected = {
            "workload_count": len(adaptive),
            "total_cycles": sum(int(item["cycles"]) for item in adaptive),
            "total_retired": sum(int(item["retired"]) for item in adaptive),
            "total_energy_proxy_units": sum(int(item["energy"]) for item in adaptive),
            "total_transitions": sum(int(item["reconfigs"]) for item in adaptive),
            "total_safety_faults": sum(int(item["safety_faults"]) for item in adaptive),
            "total_timeouts": sum(int(item["timed_out"]) for item in adaptive),
        }
        for key, value in expected.items():
            if int(row[key]) != value:
                fail(f"sweep summary mismatch {row['sweep_tag']} field={key}: {row[key]} != {value}")
        ipc = expected["total_retired"] / expected["total_cycles"]
        if abs(float(row["aggregate_ipc"]) - ipc) > 0.00011:
            fail(f"aggregate IPC mismatch {row['sweep_tag']}")
    if len(summary) == 27 and not any("sweep summary mismatch" in error or "aggregate IPC mismatch" in error for error in ERRORS):
        note("all 27 sweep summaries reconcile with raw adaptive rows")


def validate_other_evidence() -> None:
    ablations = load(
        OUT / "ablation_evidence.csv",
        {"ablation", "evidence_type", "total_cycles", "total_energy_proxy_units", "total_transitions",
         "total_reconfig_penalty_cycles", "total_safety_faults", "total_timeouts"},
    )
    expected = {"full_adaptive", "observer_disabled", "controller_disabled", "zero_cost_reconfig"}
    names = [row["ablation"] for row in ablations]
    if set(names) != expected or len(names) != len(set(names)):
        fail(f"ablation rows must be unique and complete: {names}")
    else:
        note("ablation includes full, observer-off, controller-off, and zero-cost rows")
    zero = next((row for row in ablations if row["ablation"] == "zero_cost_reconfig"), None)
    if not zero or zero["evidence_type"] != "analytical_idealization":
        fail("zero-cost reconfiguration must be labeled analytical_idealization")
    else:
        note("zero-cost reconfiguration is visibly labeled analytical")

    ablation_raw = load(
        RESULTS / "ablation_summary.csv",
        {"ablation", "total_adaptive_cycles", "total_adaptive_energy", "total_reconfigs",
         "total_reconfig_penalty", "total_safety_faults", "total_timeouts"},
    )
    raw_by_name = {row["ablation"]: row for row in ablation_raw}
    for row in ablations:
        if row["ablation"] == "full_adaptive":
            continue
        raw = raw_by_name.get(row["ablation"])
        mapping = {
            "total_cycles": "total_adaptive_cycles",
            "total_energy_proxy_units": "total_adaptive_energy",
            "total_transitions": "total_reconfigs",
            "total_reconfig_penalty_cycles": "total_reconfig_penalty",
            "total_safety_faults": "total_safety_faults",
            "total_timeouts": "total_timeouts",
        }
        if not raw or any(row[left] != raw[right] for left, right in mapping.items()):
            fail(f"ablation publication row does not reconcile with raw summary: {row['ablation']}")
    if not any("ablation publication row" in error for error in ERRORS):
        note("ablation publication rows reconcile with raw ablation summary")

    baseline = load(
        RESULTS / "adaptive_baseline" / "directed_comparison.csv",
        {"bench", "static_normal_cycles", "fixed_branch_cycles", "fixed_memory_cycles", "fixed_hazard_cycles",
         "fixed_low_power_cycles", "oracle_mode", "oracle_cycles", "pipesense_cycles", "async03_approx_cycles",
         "pipesense_faults", "async03_approx_faults", "pipesense_timeouts", "async03_approx_timeouts"},
    )
    if len(baseline) != 13 or len({row["bench"] for row in baseline}) != 13:
        fail("adaptive baseline directed comparison must contain 13 unique workloads")
    else:
        note("adaptive baseline comparison contains the same 13 unique workloads")

    primary_directed = load(
        RESULTS / "pipesense_results.csv",
        {"bench", "mode", "cycles", "energy", "reconfigs", "safety_faults", "timed_out"},
    )
    approx_directed = load(
        RESULTS / "adaptive_baseline" / "directed_raw.csv",
        {"bench", "mode", "cycles", "energy", "reconfigs", "safety_faults", "timed_out"},
    )
    primary_map = {(row["bench"], row["mode"]): row for row in primary_directed}
    approx_map = {(row["bench"], row["mode"]): row for row in approx_directed}
    for row in baseline:
        pipe = primary_map.get((row["bench"], "adaptive_pipesense"))
        approx = approx_map.get((row["bench"], "adaptive_async03_approx"))
        if not pipe or not approx:
            fail(f"adaptive baseline raw row missing for {row['bench']}")
            continue
        pairs = [
            ("pipesense_cycles", pipe, "cycles"),
            ("pipesense_energy_proxy", pipe, "energy"),
            ("pipesense_transitions", pipe, "reconfigs"),
            ("pipesense_faults", pipe, "safety_faults"),
            ("pipesense_timeouts", pipe, "timed_out"),
            ("async03_approx_cycles", approx, "cycles"),
            ("async03_approx_energy_proxy", approx, "energy"),
            ("async03_approx_transitions", approx, "reconfigs"),
            ("async03_approx_faults", approx, "safety_faults"),
            ("async03_approx_timeouts", approx, "timed_out"),
        ]
        if any(row[field] != source[source_field] for field, source, source_field in pairs):
            fail(f"adaptive baseline directed comparison mismatch for {row['bench']}")
    if not any("adaptive baseline directed comparison mismatch" in error or "raw row missing" in error for error in ERRORS):
        note("adaptive baseline directed comparison reconciles with both raw policies")

    fuzz = load(
        RESULTS / "adaptive_baseline" / "fuzz_comparison.csv",
        {"seed", "pipesense_cycles", "async03_approx_cycles", "pipesense_energy_proxy",
         "async03_approx_energy_proxy", "pipesense_transitions", "async03_approx_transitions",
         "pipesense_faults", "async03_approx_faults", "pipesense_timeouts", "async03_approx_timeouts"},
    )
    seeds = {int(row["seed"]) for row in fuzz}
    if len(fuzz) != 500 or seeds != set(range(1, 501)):
        fail("adaptive baseline fuzz comparison must contain identical seeds 1..500")
    elif any(
        int(row[field]) != 0
        for row in fuzz
        for field in ("pipesense_faults", "async03_approx_faults", "pipesense_timeouts", "async03_approx_timeouts")
    ):
        fail("adaptive baseline fuzz comparison contains a fault or timeout")
    else:
        note("adaptive baseline uses identical seeds 1..500 with zero faults/timeouts")

    primary_fuzz = load(
        RESULTS / "safety" / "fuzz_summary.csv",
        {"seed", "mode", "cycles", "energy", "reconfigs", "safety_faults", "timed_out"},
    )
    approx_fuzz = load(
        RESULTS / "adaptive_baseline" / "safety" / "fuzz_summary.csv",
        {"seed", "mode", "cycles", "energy", "reconfigs", "safety_faults", "timed_out"},
    )
    primary_fuzz_map = {(row["seed"], row["mode"]): row for row in primary_fuzz}
    approx_fuzz_map = {(row["seed"], row["mode"]): row for row in approx_fuzz}
    for row in fuzz:
        pipe = primary_fuzz_map.get((row["seed"], "adaptive_pipesense"))
        approx = approx_fuzz_map.get((row["seed"], "adaptive_pipesense"))
        if not pipe or not approx:
            fail(f"adaptive baseline fuzz source row missing for seed {row['seed']}")
            continue
        pairs = [
            ("pipesense_cycles", pipe, "cycles"),
            ("pipesense_energy_proxy", pipe, "energy"),
            ("pipesense_transitions", pipe, "reconfigs"),
            ("async03_approx_cycles", approx, "cycles"),
            ("async03_approx_energy_proxy", approx, "energy"),
            ("async03_approx_transitions", approx, "reconfigs"),
        ]
        if any(row[field] != source[source_field] for field, source, source_field in pairs):
            fail(f"adaptive baseline fuzz comparison mismatch for seed {row['seed']}")
    if not any("adaptive baseline fuzz" in error for error in ERRORS):
        note("adaptive baseline per-seed comparison reconciles with both raw policies")

    manifest_path = RESULTS / "adaptive_baseline" / "run_manifest.json"
    if not manifest_path.exists():
        fail("adaptive baseline run manifest is missing")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "approximation" not in manifest.get("implementation_scope", "") or manifest.get("random_seed_range") != "1..500":
            fail("adaptive baseline manifest does not disclose approximation scope and seeds")
        else:
            note("adaptive baseline manifest discloses approximation scope and identical seed range")

    synth = load(
        RESULTS / "post_synth" / "summary.csv",
        {"status", "design", "target_part", "clock_constraint_mhz", "achieved_frequency_mhz", "worst_slack_ns",
         "trellis_comb_used", "dffs_used", "distributed_ram_write_ports_used", "power", "power_reason"},
    )
    if not synth or synth[0]["status"] != "pass" or synth[0]["power"] != "unavailable":
        fail("post-synthesis summary must pass and report power unavailable")
    else:
        note("complete-design post-synthesis passed; power is explicitly unavailable")

    standard = load(
        RESULTS / "standard_benchmarks" / "capability_audit.csv",
        {"benchmark", "status", "actual_standard_source_executed", "compiler_version", "compiler_flags", "raw_result"},
    )
    if any(row["status"] != "blocked_not_run" or row["actual_standard_source_executed"] != "no" for row in standard):
        fail("standard benchmark audit contains an unsupported execution claim")
    else:
        note("standard benchmark audit contains no fabricated execution result")


def validate_manifest_and_figures() -> None:
    manifest = load(OUT / "source_manifest.csv", {"path", "sha256", "role"})
    for row in manifest:
        path = ROOT / row["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"
        if digest != row["sha256"]:
            fail(f"source hash mismatch: {row['path']}")
    if manifest and not any("source hash mismatch" in error for error in ERRORS):
        note("plot/table source hashes match committed source CSV bytes")
    for name in ("sweep_evidence.png", "sweep_evidence.pdf", "ablation_evidence.png", "ablation_evidence.pdf"):
        path = OUT / name
        if not path.exists() or path.stat().st_size < 1000:
            fail(f"missing or empty rendered figure: {name}")
        else:
            note(f"rendered figure exists: {name} ({path.stat().st_size} bytes)")
    for name in ("generated_sweep_table.tex", "generated_ablation_table.tex"):
        path = ROOT / "paper" / name
        if not path.exists() or path.stat().st_size < 100:
            fail(f"missing generated LaTeX table: {name}")
        else:
            note(f"generated LaTeX table exists: {name}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    validate_sweep()
    validate_other_evidence()
    validate_manifest_and_figures()
    lines = MESSAGES + ERRORS + [
        f"SUMMARY pass_checks={len(MESSAGES)} failures={len(ERRORS)}",
        "FAILED_CONFIGURATIONS none" if not any("failed sweep configurations:" in error for error in ERRORS)
        else "FAILED_CONFIGURATIONS present",
    ]
    text = "\n".join(lines) + "\n"
    (OUT / "validation.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
