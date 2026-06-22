#!/usr/bin/env python3
"""Build an 8-page PDF preview from the PipeSense paper source and results."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "pipesense_urtc_8page.tex"
RESULTS = ROOT / "results"
OUTPUT_DIR = ROOT / "output" / "pdf"
FIGURE_DIR = ROOT / "output" / "pdf" / "figures"
OUTPUT_PDF = OUTPUT_DIR / "pipesense_urtc_8page_preview.pdf"


SECTION_ORDER = [
    "Introduction",
    "Background and Motivation",
    "Related Work",
    "PipeSense-ARM Architecture",
    "Mode Semantics",
    "Design Alternatives",
    "Safe Reconfiguration",
    "Implementation",
    "Evaluation Methodology",
    "Results",
    "Parameter Sensitivity",
    "Discussion",
    "Threats to Validity",
    "Limitations",
    "Future Work",
    "Educational and Broader Impact",
    "Artifact and Reproducibility",
    "Conclusion",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def clean_inline(text: str) -> str:
    replacements = {
        r"\pipesense{}": "PipeSense-ARM",
        r"\pipesense": "PipeSense-ARM",
        r"\texttt{": "",
        r"\%": "%",
        r"\_": "_",
        "~": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\\cite\{([^}]+)\}", lambda m: citation_text(m.group(1)), text)
    text = re.sub(r"\\ref\{[^}]+\}", "the corresponding table or figure", text)
    text = re.sub(r"Table~", "Table ", text)
    text = re.sub(r"Fig\.~", "Fig. ", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\\[A-Za-z]+\*?", "", text)
    return " ".join(text.split())


def citation_text(keys: str) -> str:
    short = []
    for key in keys.split(","):
        key = key.strip()
        match = re.search(r"(19|20)\d\d", key)
        if match:
            short.append(match.group(0))
        else:
            short.append(key[:4])
    return "[" + ", ".join(short) + "]"


def extract_block(tex: str, env: str) -> str:
    match = re.search(rf"\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}", tex, flags=re.S)
    return clean_inline(match.group(1)) if match else ""


def strip_floats(tex: str) -> str:
    for env in ("table", "table*", "figure"):
        tex = re.sub(rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}", "", tex, flags=re.S)
    return tex


def extract_sections(tex: str) -> list[tuple[str, list[str]]]:
    body = strip_floats(tex)
    parts = re.split(r"\\section\{([^}]+)\}", body)
    sections: list[tuple[str, list[str]]] = []
    for i in range(1, len(parts), 2):
        raw_title = parts[i]
        if raw_title not in SECTION_ORDER:
            continue
        raw_body = parts[i + 1]
        paragraphs = []
        for para in re.split(r"\n\s*\n", raw_body):
            para = para.strip()
            if not para or para.startswith("\\bibliographystyle") or para.startswith("\\bibliography"):
                continue
            if para.startswith("\\begin") or para.startswith("\\end"):
                continue
            cleaned = clean_inline(para)
            if cleaned:
                paragraphs.append(cleaned)
        sections.append((clean_inline(raw_title), paragraphs))
    return sections


def make_architecture_png(path: Path) -> None:
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont

    path.parent.mkdir(parents=True, exist_ok=True)
    image = PILImage.new("RGB", (1600, 620), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 38)
        font = ImageFont.truetype("arial.ttf", 30)
        small = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        title_font = ImageFont.load_default()
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    draw.text((40, 30), "PipeSense-ARM closed-loop pipeline", fill="#111111", font=title_font)
    stages = ["IF", "ID", "EX", "MEM", "WB"]
    x0, y0, w, h, gap = 80, 155, 210, 90, 45
    centers = []
    for i, stage in enumerate(stages):
        x = x0 + i * (w + gap)
        centers.append((x + w / 2, y0 + h / 2))
        draw.rounded_rectangle((x, y0, x + w, y0 + h), radius=10, outline="#1f4e79", width=5, fill="#eaf2f8")
        draw.text((x + 78, y0 + 27), stage, fill="#111111", font=font)
        if i:
            px = x - gap
            draw.line((px + 8, y0 + h / 2, x - 8, y0 + h / 2), fill="#333333", width=5)
            draw.polygon([(x - 8, y0 + h / 2), (x - 26, y0 + h / 2 - 12), (x - 26, y0 + h / 2 + 12)], fill="#333333")

    bus_y = 310
    for cx, cy in centers:
        draw.line((cx, y0 + h, cx, bus_y), fill="#666666", width=3)
    draw.line((centers[0][0], bus_y, centers[-1][0], bus_y), fill="#666666", width=3)
    draw.text((590, bus_y + 16), "minimal observer taps", fill="#333333", font=small)

    blocks = [
        ("pipeline_observer", 460, 385, 330, 70, "#e8f5e9", "#2e7d32"),
        ("adaptive_controller", 830, 385, 350, 70, "#fff8e1", "#ef6c00"),
        ("reconfig_unit", 1220, 385, 280, 70, "#fce4ec", "#ad1457"),
    ]
    for text, x, y, bw, bh, fill, outline in blocks:
        draw.rounded_rectangle((x, y, x + bw, y + bh), radius=10, outline=outline, width=4, fill=fill)
        draw.text((x + 26, y + 22), text, fill="#111111", font=small)
    draw.line((790, 420, 830, 420), fill="#333333", width=4)
    draw.polygon([(830, 420), (812, 408), (812, 432)], fill="#333333")
    draw.line((1180, 420, 1220, 420), fill="#333333", width=4)
    draw.polygon([(1220, 420), (1202, 408), (1202, 432)], fill="#333333")
    draw.line((1360, 385, 1360, 260), fill="#ad1457", width=4)
    draw.line((1360, 260, 1180, 260), fill="#ad1457", width=4)
    draw.text((1195, 275), "current mode", fill="#ad1457", font=small)
    image.save(path)


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=15,
            leading=17,
            alignment=TA_CENTER,
            spaceAfter=5,
        ),
        "author": ParagraphStyle(
            "Author",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9,
            leading=10,
            alignment=TA_CENTER,
            spaceAfter=7,
        ),
        "abstract": ParagraphStyle(
            "Abstract",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9,
            leading=10.8,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=12.2,
            alignment=TA_JUSTIFY,
            spaceAfter=3.2,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=10.8,
            leading=12.5,
            alignment=TA_LEFT,
            spaceBefore=5,
            spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=4,
        ),
    }


def add_table(story: list, title: str, data: list[list[str]], widths: list[float]) -> None:
    styles = build_styles()
    story.append(Paragraph(title, styles["caption"]))
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.1),
                ("LEADING", (0, 0), (-1, -1), 7.1),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9edf4")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1.4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 5))


class TwoColumnDoc(SimpleDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        page_width, page_height = self.pagesize
        margin_x = 0.56 * inch
        margin_y = 0.54 * inch
        gutter = 0.18 * inch
        frame_width = (page_width - (2 * margin_x) - gutter) / 2
        frame_height = page_height - (2 * margin_y) - 0.08 * inch
        frames = [
            Frame(margin_x, margin_y, frame_width, frame_height, id="left", showBoundary=0),
            Frame(margin_x + frame_width + gutter, margin_y, frame_width, frame_height, id="right", showBoundary=0),
        ]
        self.addPageTemplates([PageTemplate(id="two-col", frames=frames, onPage=draw_page)])


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Times-Roman", 7)
    canvas.drawCentredString(letter[0] / 2, 0.28 * inch, f"{doc.page}")
    canvas.setFont("Times-Italic", 6.5)
    canvas.drawCentredString(letter[0] / 2, letter[1] - 0.27 * inch, "PipeSense-ARM extended URTC draft preview")
    canvas.restoreState()


def main() -> int:
    tex = PAPER.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    arch_png = FIGURE_DIR / "architecture.png"
    make_architecture_png(arch_png)

    styles = build_styles()
    story: list = []
    story.append(Paragraph("PipeSense-ARM: A Lightweight Hardware Observer for Safe Adaptive Pipeline Reconfiguration in Embedded ARM-Like Processors", styles["title"]))
    story.append(Paragraph("Author Name<br/>Affiliation - email@example.com", styles["author"]))
    story.append(Paragraph("<b>Abstract-</b> " + extract_block(tex, "abstract"), styles["abstract"]))
    story.append(Paragraph("<b>Index Terms-</b> computer architecture, embedded processors, adaptive microarchitecture, pipeline reconfiguration, hardware performance monitoring", styles["abstract"]))

    for title, paragraphs in extract_sections(tex):
        story.append(Paragraph(title.upper(), styles["section"]))
        if title == "PipeSense-ARM Architecture":
            story.append(Image(str(arch_png), width=3.22 * inch, height=1.25 * inch))
            story.append(Paragraph("Fig. 1. PipeSense-ARM places an observer/controller/reconfiguration loop around a small five-stage pipeline.", styles["caption"]))
        for para in paragraphs:
            story.append(Paragraph(para, styles["body"]))
        if title == "Results":
            add_results_tables(story)

    add_references(story)

    doc = TwoColumnDoc(
        str(OUTPUT_PDF),
        pagesize=letter,
        rightMargin=0.56 * inch,
        leftMargin=0.56 * inch,
        topMargin=0.54 * inch,
        bottomMargin=0.54 * inch,
    )
    doc.build(story)
    print(f"Wrote {OUTPUT_PDF}")
    return 0


def add_results_tables(story: list) -> None:
    adaptive = read_csv(RESULTS / "adaptive_improvement.csv")
    adaptive_data = [["Benchmark", "Norm", "Adapt", "Cycle", "IPC", "Energy", "Rcfg"]]
    for row in adaptive:
        adaptive_data.append(
            [
                row["bench"].replace("_", " "),
                row["normal_cycles"],
                row["adaptive_cycles"],
                row["cycle_reduction_pct"] + "%",
                row["ipc_improvement_pct"] + "%",
                row["energy_reduction_pct"] + "%",
                row["adaptive_reconfigs"],
            ]
        )
    add_table(story, "Table I. Adaptive PipeSense versus static-normal baseline.", adaptive_data, [74, 29, 32, 32, 31, 35, 25])

    oracle = read_csv(RESULTS / "oracle_gap.csv")
    oracle_data = [["Benchmark", "Best fixed", "Best", "Adapt", "Cycle gap", "Energy gap"]]
    for row in oracle:
        oracle_data.append(
            [
                row["bench"].replace("_", " "),
                row["best_fixed_mode"].replace("fixed_", ""),
                row["best_fixed_cycles"],
                row["adaptive_cycles"],
                row["adaptive_gap_to_best_fixed_pct"] + "%",
                row["adaptive_energy_gap_to_best_fixed_pct"] + "%",
            ]
        )
    add_table(story, "Table II. Adaptive mode versus best fixed-mode oracle.", oracle_data, [74, 48, 29, 32, 43, 43])

    cost = read_csv(RESULTS / "hardware_cost_estimate.csv")
    cost_data = [["Component", "FF bits", "Comp.", "Adders"]]
    for row in cost:
        cost_data.append([row["component"].replace("_", " "), row["estimated_ff_bits"], row["estimated_comparators"], row["estimated_adders"]])
    add_table(story, "Table III. Analytical hardware-cost estimate, not synthesis evidence.", cost_data, [97, 42, 34, 34])


def add_references(story: list) -> None:
    styles = build_styles()
    refs = [
        "[1] J. E. Smith, A Study of Branch Prediction Strategies, ISCA, 1981.",
        "[2] N. P. Jouppi, Improving Direct-Mapped Cache Performance by the Addition of a Small Fully-Associative Cache and Prefetch Buffers, ISCA, 1990.",
        "[3] T. Sherwood, E. Perelman, G. Hamerly, and B. Calder, Automatically Characterizing Large Scale Program Behavior, ASPLOS, 2002.",
        "[4] A. S. Dhodapkar and J. E. Smith, Managing Multi-Configuration Hardware via Dynamic Working Set Analysis, ISCA, 2002.",
        "[5] R. Balasubramonian, D. H. Albonesi, A. Buyuktosunoglu, and S. Dwarkadas, Memory Hierarchy Reconfiguration for Energy and Performance, MICRO, 2000.",
        "[6] D. Brooks, V. Tiwari, and M. Martonosi, Wattch: A Framework for Architectural-Level Power Analysis and Optimizations, ISCA, 2000.",
        "[7] T. Mudge, Power: A First-Class Architectural Design Constraint, Computer, 2001.",
        "[8] C. Isci and M. Martonosi, Runtime Power Monitoring in High-End Processors, MICRO, 2003.",
        "[9] T. Austin, E. Larson, and D. Ernst, SimpleScalar: An Infrastructure for Computer System Modeling, Computer, 2002.",
        "[10] J. L. Hennessy and D. A. Patterson, Computer Architecture: A Quantitative Approach, 6th ed., 2017.",
    ]
    story.append(Paragraph("REFERENCES", styles["section"]))
    for ref in refs:
        story.append(Paragraph(ref, ParagraphStyle("Ref", parent=styles["body"], fontSize=6.4, leading=7.2, spaceAfter=1.5)))


if __name__ == "__main__":
    raise SystemExit(main())
