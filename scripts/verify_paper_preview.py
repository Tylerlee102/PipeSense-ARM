#!/usr/bin/env python3
"""Verify the generated 5-page paper preview PDF."""

from __future__ import annotations

from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output" / "pdf" / "pipesense_urtc_5page_preview.pdf"
RENDER_DIR = ROOT / "output" / "pdf" / "rendered"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    if not PDF.exists():
        fail(f"Missing preview PDF: {PDF}")

    doc = fitz.open(PDF)
    if doc.page_count != 5:
        fail(f"Expected exactly 5 pages, found {doc.page_count}")

    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if len(text.split()) < 40:
            fail(f"Page {index} appears too sparse or blank")
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            fail(f"Page {index} has invalid dimensions")
        pix = page.get_pixmap(matrix=fitz.Matrix(0.6, 0.6), alpha=False)
        samples = pix.samples
        if samples.count(255) == len(samples):
            fail(f"Page {index} rendered as a blank white page")
        pix.save(RENDER_DIR / f"page_{index:02d}.png")

    print(f"Preview PDF verification passed: {PDF} ({doc.page_count} pages)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
