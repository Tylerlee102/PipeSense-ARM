#!/usr/bin/env python3
"""Validate the paper draft against local evidence where possible."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "pipesense_urtc_8page.tex"
BIB = ROOT / "paper" / "references.bib"
RESULTS = ROOT / "results"


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latex_name(value: str) -> str:
    return value.replace("_", "\\_")


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def check_files() -> tuple[str, str]:
    if not PAPER.exists():
        fail(f"Missing paper source: {PAPER}")
    if not BIB.exists():
        fail(f"Missing bibliography: {BIB}")
    return PAPER.read_text(encoding="utf-8"), BIB.read_text(encoding="utf-8")


def check_no_placeholders(tex: str) -> None:
    forbidden = [
        "TODO",
        "TBD",
        "FIXME",
        "??",
        "Author Name",
        "email@example.com",
        "City, State",
    ]
    found = [token for token in forbidden if token in tex]
    if found:
        fail("Paper contains unresolved placeholders: " + ", ".join(found))


def check_citations(tex: str, bib: str) -> None:
    cited: set[str] = set()
    for match in re.finditer(r"\\cite\{([^}]+)\}", tex):
        cited.update(key.strip() for key in match.group(1).split(",") if key.strip())
    defined = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing = sorted(cited - defined)
    unused = sorted(defined - cited)
    if missing:
        fail("Paper cites keys missing from references.bib: " + ", ".join(missing))
    if len(cited) < 8:
        fail(f"Expected at least 8 cited references, found {len(cited)}")
    if unused:
        print("WARN unused bibliography keys: " + ", ".join(unused))


def check_claim_language(tex: str) -> None:
    required_phrases = [
        "not an ARM-compatible processor",
        "not calibrated synthesis results",
        "not formal verification",
        "oracle comparison",
        "zero safety faults",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in tex]
    if missing:
        fail("Paper is missing required claim-discipline language: " + ", ".join(missing))


def check_workshop_length(tex: str) -> None:
    text_without_commands = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", tex)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", text_without_commands)
    if len(words) < 1800:
        fail(f"Paper is too short for a five-page workshop draft: {len(words)} words")
    if len(words) > 3900:
        fail(f"Paper is too long for a five-page workshop draft proxy: {len(words)} words")


def check_adaptive_table(tex: str) -> None:
    path = RESULTS / "adaptive_improvement.csv"
    if not path.exists():
        print("WARN adaptive_improvement.csv not found; skipped table-data check")
        return
    rows = load_csv(path)
    compact_tex = compact(tex)
    for row in rows:
        expected = (
            f"{latex_name(row['bench'])} & {row['normal_cycles']} & "
            f"{row['adaptive_cycles']} & {row['cycle_reduction_pct']}\\% & "
            f"{row['ipc_improvement_pct']}\\% & {row['energy_reduction_pct']}\\% & "
            f"{row['adaptive_reconfigs']} & {row['adaptive_reconfig_penalty']}"
        )
        if compact(expected) not in compact_tex:
            fail(f"Adaptive table does not match CSV for {row['bench']}")


def check_oracle_table(tex: str) -> None:
    path = RESULTS / "oracle_gap.csv"
    if not path.exists():
        print("WARN oracle_gap.csv not found; skipped oracle-data check")
        return
    rows = load_csv(path)
    compact_tex = compact(tex)
    for row in rows:
        expected = (
            f"{latex_name(row['bench'])} & "
            f"{latex_name(row['best_fixed_mode'])} & "
            f"{row['best_fixed_cycles']} & {row['adaptive_cycles']} & "
            f"{row['adaptive_gap_to_best_fixed_pct']}\\% & "
            f"{row['best_fixed_energy']} & "
            f"{row['adaptive_energy_gap_to_best_fixed_pct']}\\%"
        )
        if compact(expected) not in compact_tex:
            fail(f"Oracle table does not match CSV for {row['bench']}")


def check_ablation_table(tex: str) -> None:
    path = RESULTS / "ablation_summary.csv"
    if not path.exists():
        print("WARN ablation_summary.csv not found; skipped ablation-data check")
        return
    rows = load_csv(path)
    compact_tex = compact(tex)
    for row in rows:
        expected = (
            f"{latex_name(row['ablation'])} & "
            f"{row['total_adaptive_cycles']} & "
            f"{row['cycle_change_vs_full_pct']}\\% & "
            f"{row['total_adaptive_energy']} & "
            f"{row['total_reconfigs']} & "
            f"{row['total_reconfig_penalty']}"
        )
        if compact(expected) not in compact_tex:
            fail(f"Ablation table does not match CSV for {row['ablation']}")


def check_area_table(tex: str) -> None:
    path = RESULTS / "synth" / "area_summary.csv"
    if not path.exists():
        print("WARN area_summary.csv not found; skipped area-data check")
        return
    rows = {row["module"]: row for row in load_csv(path)}
    compact_tex = compact(tex)
    core = rows.get("arm_like_core")
    total = rows.get("observer_controller_reconfig_total")
    integrated = rows.get("pipesense_integrated_core")
    if not core:
        fail("Area CSV missing arm_like_core row")
    if not total:
        fail("Area CSV missing observer_controller_reconfig_total row")
    if not integrated:
        fail("Area CSV missing pipesense_integrated_core row")
    expected_core = f"baseline core proxy & {core['number_of_cells']} & 100.00\\%"
    baseline_cells = float(core["number_of_cells"])
    module_expectations = []
    for module in ["pipeline_observer", "adaptive_controller", "reconfig_unit"]:
        row = rows.get(module)
        if not row:
            fail(f"Area CSV missing {module} row")
        pct = (float(row["number_of_cells"]) / baseline_cells) * 100.0
        module_expectations.append(
            f"{latex_name(module)} & {row['number_of_cells']} & {pct:.2f}\\%"
        )
    expected_total = (
        "observer/controller/reconfig sum & "
        f"{total['number_of_cells']} & {total['overhead_vs_core_pct']}\\%"
    )
    expected_integrated = (
        "integrated core proxy & "
        f"{integrated['number_of_cells']} & {integrated['overhead_vs_core_pct']}\\%"
    )
    if compact(expected_core) not in compact_tex:
        fail("Area table does not match CSV for arm_like_core")
    for expected in module_expectations:
        if compact(expected) not in compact_tex:
            fail(f"Area table does not match CSV for {expected.split(' & ', 1)[0]}")
    if compact(expected_total) not in compact_tex:
        fail("Area table does not match CSV for observer/controller/reconfig sum")
    if compact(expected_integrated) not in compact_tex:
        fail("Area table does not match CSV for integrated core proxy")


def main() -> int:
    tex, bib = check_files()
    check_no_placeholders(tex)
    check_citations(tex, bib)
    check_claim_language(tex)
    check_workshop_length(tex)
    check_adaptive_table(tex)
    check_oracle_table(tex)
    check_ablation_table(tex)
    check_area_table(tex)
    print("Paper draft checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
