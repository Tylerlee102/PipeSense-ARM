#!/usr/bin/env python3
"""Independently reconcile committed PipeSense-Ibex engineering evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "ibex"
POLICIES = {"static-sequential", "static-branch", "adaptive"}


class Checks:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failures = 0

    def check(self, condition: bool, label: str, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        suffix = f": {detail}" if detail else ""
        self.lines.append(f"{status} {label}{suffix}")
        if not condition:
            self.failures += 1


def signature_bytes(path: Path) -> bytes:
    data = bytearray()
    for line in path.read_text(encoding="ascii").splitlines():
        word = line.strip()
        if word:
            data.extend(int(word, 16).to_bytes(len(word) // 2, "little"))
    return bytes(data)


def expected_marker(benchmark: str) -> str | None:
    if benchmark.startswith("embench-"):
        return "EMBENCH_PASS"
    if benchmark.startswith("coremark-"):
        return "Correct operation validated"
    if benchmark == "multiphase":
        return "PIPESENSE_MULTIPHASE_PASS DE332F10"
    if benchmark == "fuzz-500":
        return "PIPESENSE_FUZZ_PASS seeds=500 signature=6B93D2E5"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-quick", action="store_true",
                        help="validate CI's reduced benchmark set instead of committed full evidence")
    args = parser.parse_args()
    checks = Checks()

    csv_path = RESULTS / "benchmark_results.csv"
    summary_path = RESULTS / "summary.json"
    checks.check(csv_path.is_file(), "benchmark CSV exists")
    checks.check(summary_path.is_file(), "benchmark summary exists")
    if not csv_path.is_file() or not summary_path.is_file():
        print("\n".join(checks.lines))
        return 1

    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_runs = 18 if args.allow_quick else 291
    expected_arch = 1 if args.allow_quick else 75
    expected_embench = 2 if args.allow_quick else 19
    expected_coremark = "coremark-10" if args.allow_quick else "coremark-2000"

    required = {"benchmark", "policy", "cycles", "retired", "ipc", "transitions",
                "drain_cycles", "wall_seconds", "failures"}
    checks.check(set(rows[0]) == required, "benchmark CSV schema",
                 ",".join(rows[0]))
    keys = [(row["benchmark"], row["policy"]) for row in rows]
    checks.check(len(rows) == expected_runs, "run count", str(len(rows)))
    checks.check(len(keys) == len(set(keys)), "unique benchmark-policy keys")
    checks.check({row["policy"] for row in rows} == POLICIES, "all policies present")
    policy_counts = Counter(row["policy"] for row in rows)
    checks.check(len(set(policy_counts.values())) == 1, "equal run count per policy",
                 str(dict(policy_counts)))
    checks.check(all(int(row["failures"]) == 0 for row in rows), "zero run failures")
    checks.check(all(int(row["cycles"]) > 0 and int(row["retired"]) > 0 for row in rows),
                 "positive cycle and retirement counts")
    checks.check(all(math.isclose(float(row["ipc"]), int(row["retired"]) /
                                  int(row["cycles"]), rel_tol=1e-12)
                     for row in rows), "IPC reconciles with raw counters")

    by_benchmark: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_benchmark[row["benchmark"]].append(row)
    checks.check(all(len(group) == 3 for group in by_benchmark.values()),
                 "each workload has three policy runs")
    checks.check(all(len({int(row["retired"]) for row in group}) == 1
                     for group in by_benchmark.values()),
                 "retirement counts agree across policies")
    arch_names = {name for name in by_benchmark if name.startswith("arch-")}
    embench_names = {name for name in by_benchmark if name.startswith("embench-")}
    checks.check(len(arch_names) == expected_arch, "architecture-test count", str(len(arch_names)))
    checks.check(len(embench_names) == expected_embench, "Embench program count",
                 str(len(embench_names)))
    checks.check(expected_coremark in by_benchmark, "CoreMark iteration run",
                 expected_coremark)
    checks.check({"multiphase", "fuzz-500"}.issubset(by_benchmark),
                 "multi-phase and fuzz workloads present")
    adaptive_multiphase = next((row for row in by_benchmark.get("multiphase", [])
                                if row["policy"] == "adaptive"), None)
    checks.check(adaptive_multiphase is not None and
                 int(adaptive_multiphase["transitions"]) > 1,
                 "adaptive multi-phase run makes repeated transitions",
                 adaptive_multiphase["transitions"] if adaptive_multiphase else "missing")

    marker_ok = True
    signatures_ok = True
    for benchmark, group in by_benchmark.items():
        marker = expected_marker(benchmark)
        for row in group:
            program_log = RESULTS / "logs" / row["policy"] / f"{benchmark}.program.log"
            if not program_log.is_file():
                marker_ok = False
                continue
            raw = program_log.read_bytes()
            if marker is not None and marker.encode("ascii") not in raw:
                marker_ok = False
            if benchmark.startswith("arch-"):
                reference = RESULTS / "reference" / f"{benchmark}.signature"
                if not reference.is_file() or raw != signature_bytes(reference):
                    signatures_ok = False
    checks.check(marker_ok, "all self-check markers present in raw program logs")
    checks.check(signatures_ok, "all architecture signatures exactly match Spike")
    checks.check(len(list((RESULTS / "reference").glob("arch-*.signature"))) == expected_arch,
                 "Spike signature count", str(expected_arch))

    fuzz_path = ROOT / "integrations" / "ibex" / "verif" / "fuzz_expected.csv"
    with fuzz_path.open(encoding="utf-8", newline="") as stream:
        fuzz_rows = list(csv.DictReader(stream))
    fuzz_seeds = [int(row["seed"]) for row in fuzz_rows]
    checks.check(len(fuzz_rows) == 500 and len(set(fuzz_seeds)) == 500,
                 "500 unique deterministic fuzz seeds")
    checks.check(fuzz_seeds == list(range(500)), "fuzz seed sequence is complete")

    checks.check(summary.get("status") == "PASS", "summary status")
    checks.check(summary.get("runs") == len(rows), "summary run count reconciles")
    checks.check(summary.get("failures") == 0, "summary failure count reconciles")
    checks.check(summary.get("fuzz_seeds") == 500, "summary fuzz count reconciles")
    checks.check(summary.get("coremark_iterations") == (10 if args.allow_quick else 2000),
                 "summary CoreMark iteration count reconciles")
    checks.check(summary.get("architecture_tests") == expected_arch,
                 "summary architecture count reconciles")
    checks.check(summary.get("embench_programs") == expected_embench,
                 "summary Embench count reconciles")

    lock = json.loads((ROOT / "integrations" / "ibex" / "lock.json").read_text())
    revisions = json.loads((RESULTS / "source_revisions.json").read_text())
    checks.check(lock == revisions, "recorded source revisions match lock file")
    checks.check((RESULTS / "tool_versions.txt").stat().st_size > 0,
                 "tool versions recorded")

    formal_summary_path = RESULTS / "formal" / "summary.json"
    formal_log_path = RESULTS / "formal" / "ibex_reconfiguration.log"
    checks.check(formal_summary_path.is_file(), "formal summary exists")
    checks.check(formal_log_path.is_file(), "raw formal log archived")
    if formal_summary_path.is_file() and formal_log_path.is_file():
        formal_summary = json.loads(formal_summary_path.read_text(encoding="utf-8"))
        formal_log = formal_log_path.read_text(encoding="utf-8", errors="replace")
        checks.check(formal_summary.get("status") == "PASS" and
                     formal_summary.get("returncode") == 0,
                     "formal summary status")
        checks.check(formal_summary.get("whole_core_unbounded_proof") is False,
                     "formal scope limitation recorded")
        checks.check("DONE (PASS" in formal_log, "formal log reports pass")

    if not args.allow_quick:
        synth_path = RESULTS / "post_synth" / "summary.json"
        checks.check(synth_path.is_file(), "post-synthesis summary exists")
        if synth_path.is_file():
            synth = json.loads(synth_path.read_text(encoding="utf-8"))
            synth_rows = synth.get("rows", [])
            checks.check(synth.get("status") == "PASS", "post-synthesis status")
            checks.check({row.get("policy_id") for row in synth_rows} == {0, 2},
                         "matched baseline and adaptive synthesis rows")
            checks.check(len({(row.get("target"), row.get("clock_constraint_mhz"))
                              for row in synth_rows}) == 1,
                         "same synthesis target and clock constraint")
            checks.check(all(float(row.get("achieved_frequency_mhz", 0)) >=
                             float(row.get("clock_constraint_mhz", 0))
                             for row in synth_rows), "both placed designs meet constraint")
            checks.check(all(int(row.get("trellis_comb", 0)) > 0 and
                             int(row.get("trellis_ff", 0)) > 0 for row in synth_rows),
                         "nonzero placed resource counts")
            checks.check(all(row.get("power") == "unavailable" for row in synth_rows),
                         "power is explicitly unavailable")
            comparison = synth.get("adaptive_minus_baseline", {})
            if len(synth_rows) == 2:
                baseline, adaptive = synth_rows
                checks.check(comparison.get("trellis_comb_delta") ==
                             adaptive["trellis_comb"] - baseline["trellis_comb"] and
                             comparison.get("trellis_ff_delta") ==
                             adaptive["trellis_ff"] - baseline["trellis_ff"],
                             "resource deltas reconcile with placed reports")
            raw_names = {"sv2v.log", "synth.ys", "yosys.log", "nextpnr.log",
                         "nextpnr_report.json"}
            checks.check(all((RESULTS / "post_synth" / f"policy{policy}" / name).is_file()
                             for policy in (0, 2) for name in raw_names),
                         "raw synthesis and place-and-route evidence archived")

    checks.check(not any(RESULTS.rglob("coremark-10.*")) or args.allow_quick,
                 "no stale quick CoreMark artifacts in full evidence")
    checks.check(not (RESULTS / "reference" / "manual.signature").exists(),
                 "no manual debug signature in evidence")

    checks.lines.append(f"SUMMARY: {len(checks.lines) - checks.failures} PASS, "
                        f"{checks.failures} FAIL")
    output = "\n".join(checks.lines) + "\n"
    print(output, end="")
    if not args.allow_quick:
        validation_path = RESULTS / "validation.txt"
        existing = validation_path.read_bytes() if validation_path.is_file() else b""
        newline = "\r\n" if b"\r\n" in existing else "\n"
        validation_path.write_text(output, encoding="utf-8", newline=newline)
    return 1 if checks.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
