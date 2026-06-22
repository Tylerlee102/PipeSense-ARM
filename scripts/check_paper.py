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
    forbidden = ["TODO", "TBD", "FIXME", "??"]
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
        "not synthesis results",
        "not formal verification",
        "oracle comparison",
        "zero safety faults",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in tex]
    if missing:
        fail("Paper is missing required claim-discipline language: " + ", ".join(missing))


def check_extended_length(tex: str) -> None:
    text_without_commands = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", tex)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", text_without_commands)
    if len(words) < 4000:
        fail(f"Paper is too short for an 8-page-ready extended draft: {len(words)} words")


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


def main() -> int:
    tex, bib = check_files()
    check_no_placeholders(tex)
    check_citations(tex, bib)
    check_claim_language(tex)
    check_extended_length(tex)
    check_adaptive_table(tex)
    check_oracle_table(tex)
    print("Paper draft checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
