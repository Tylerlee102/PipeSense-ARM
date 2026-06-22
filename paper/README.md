# PipeSense-ARM Paper Package

This directory contains an 8-page-ready IEEE-style manuscript source for the
PipeSense-ARM research prototype.

## Files

- `pipesense_urtc_8page.tex`: extended 8-page manuscript draft.
- `references.bib`: real related-work references used by the manuscript.

## Build

On a machine with a LaTeX distribution installed:

```bash
pdflatex pipesense_urtc_8page.tex
bibtex pipesense_urtc_8page
pdflatex pipesense_urtc_8page.tex
pdflatex pipesense_urtc_8page.tex
```

## Preview Without LaTeX

This repo can also generate a checked 8-page PDF preview through ReportLab:

```bash
python scripts/build_paper_preview.py
python scripts/verify_paper_preview.py
```

The preview is written to:

```text
output/pdf/pipesense_urtc_8page_preview.pdf
```

This preview is for page-count and readability inspection. The canonical
submission source remains `paper/pipesense_urtc_8page.tex`.

## URTC note

MIT URTC public submission guidance has listed a 5-page manuscript limit in
recent cycles. Treat this 8-page file as an extended/master draft unless your
specific submission instructions allow 8 pages. If a 5-page limit applies,
compress by removing the detailed hardware-cost table, shortening related work,
moving the oracle table into prose, and trimming limitations/future work.

## Before submission

1. Replace `Author Name` and affiliation placeholders.
2. Confirm the current URTC page limit and template instructions.
3. Re-run `python scripts/run_sim.py` before freezing paper numbers.
4. Re-run `python scripts/check_paper.py`.
5. Build the PDF with LaTeX and inspect page count, figure/table placement, and references.
