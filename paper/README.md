# PipeSense-ARM Paper Package

This directory contains a six-page IEEE-style workshop manuscript source for the
PipeSense-ARM research prototype.

## Files

- `pipesense_urtc_8page.tex`: six-page workshop manuscript draft.
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

This repo can also generate a checked six-page PDF preview through ReportLab:

```bash
python scripts/build_paper_preview.py
python scripts/verify_paper_preview.py
```

The preview is written to:

```text
output/pdf/pipesense_urtc_6page_preview.pdf
```

This preview is for page-count and readability inspection. The canonical
submission source remains `paper/pipesense_urtc_8page.tex`.

## URTC note

Treat this source as a six-page workshop draft unless the current venue gives a
different page limit or template. If a stricter limit applies, compress
discussion, future-work, and artifact prose before cutting the architecture
description or result tables.

## Before submission

1. Replace `Author Name` and affiliation placeholders.
2. Confirm the current URTC page limit and template instructions.
3. Re-run `python scripts/run_sim.py` before freezing paper numbers.
4. Re-run `python scripts/check_paper.py`.
5. Build the PDF with LaTeX and inspect page count, figure/table placement, and references.
