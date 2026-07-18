#!/usr/bin/env python3
"""Verify the rendered workshop manuscript PDF and page images."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "pipesense_urtc_5page.tex"
BIB = ROOT / "paper" / "references.bib"
OUTPUT_DIR = ROOT / "output" / "paper_preview"
PDF = OUTPUT_DIR / "pipesense_urtc_5page.pdf"
LOG = OUTPUT_DIR / "pipesense_urtc_5page.log"
PAGES_DIR = OUTPUT_DIR / "pages"
MAX_PAGES = 5
LETTER_WIDTH = 612.0
LETTER_HEIGHT = 792.0

PLACEHOLDERS = [
    "Paper Title",
    "Author Name",
    "Affiliation",
    "City, Country",
    "email@example.com",
]


def dereference(value):
    return value.get_object() if hasattr(value, "get_object") else value


def font_is_embedded(font) -> bool:
    font = dereference(font)
    if str(font.get("/Subtype", "")) == "/Type3":
        return True
    descriptor = font.get("/FontDescriptor")
    if descriptor:
        descriptor = dereference(descriptor)
        if any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")):
            return True
    descendants = font.get("/DescendantFonts") or []
    return bool(descendants) and all(font_is_embedded(item) for item in descendants)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not PDF.exists():
        print(f"FAIL Missing rendered PDF: {PDF}")
        return 1
    if PAPER.exists() and PDF.stat().st_mtime < PAPER.stat().st_mtime:
        errors.append("Rendered PDF is older than the manuscript source.")
    if BIB.exists() and PDF.stat().st_mtime < BIB.stat().st_mtime:
        errors.append("Rendered PDF is older than the bibliography.")

    reader = PdfReader(PDF)
    page_count = len(reader.pages)
    if page_count == 0:
        errors.append("Rendered PDF contains no pages.")
    if page_count > MAX_PAGES:
        errors.append(f"Rendered PDF has {page_count} pages; the venue maximum is {MAX_PAGES}.")

    document_text: list[str] = []
    unembedded_fonts: set[str] = set()
    for index, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - LETTER_WIDTH) > 1 or abs(height - LETTER_HEIGHT) > 1:
            errors.append(f"Page {index} is {width:.1f} x {height:.1f} pt, not US Letter.")

        page_text = page.extract_text() or ""
        document_text.append(page_text)
        resources = dereference(page.get("/Resources") or {})
        xobjects = resources.get("/XObject") or {}
        if len(page_text.strip()) < 20 and not xobjects:
            errors.append(f"Page {index} appears blank or nearly blank.")
        for _, font_ref in (resources.get("/Font") or {}).items():
            font = dereference(font_ref)
            if not font_is_embedded(font):
                unembedded_fonts.add(str(font.get("/BaseFont", "unknown")))
    if unembedded_fonts:
        errors.append("Unembedded PDF fonts: " + ", ".join(sorted(unembedded_fonts)))

    combined_text = "\n".join(document_text)
    remaining_placeholders = [token for token in PLACEHOLDERS if token in combined_text]
    if remaining_placeholders:
        errors.append("Rendered PDF contains placeholders: " + ", ".join(remaining_placeholders))

    rendered_pages = sorted(PAGES_DIR.glob("page-*.png"))
    if len(rendered_pages) != page_count:
        errors.append(
            f"Expected {page_count} rendered page image(s), found {len(rendered_pages)} under {PAGES_DIR}."
        )
    for path in rendered_pages:
        if path.stat().st_size < 10_000:
            warnings.append(f"Rendered page image is unexpectedly small: {path.name}")

    if LOG.exists():
        log = LOG.read_text(encoding="utf-8", errors="replace")
        if re.search(r"LaTeX Warning:.*(?:undefined|Citation)", log, flags=re.IGNORECASE):
            errors.append("LaTeX log contains undefined citations or references.")
        if "Overfull \\hbox" in log or "Overfull \\vbox" in log:
            errors.append("LaTeX log contains overfull boxes that may clip or cross margins.")
        underfull_count = len(re.findall(r"Underfull \\[hv]box", log))
        if underfull_count:
            warnings.append(f"LaTeX log contains {underfull_count} underfull box warning(s).")
    else:
        warnings.append("No LaTeX log was copied beside the PDF.")

    for message in warnings:
        print(f"WARN {message}")
    for message in errors:
        print(f"FAIL {message}")
    if errors:
        print(f"Paper preview is not submission-ready: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"Paper preview checks passed: {page_count} page(s), embedded fonts, US Letter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
