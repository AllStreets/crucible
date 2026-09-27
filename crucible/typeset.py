"""Typeset a verified paper as a PDF.

The PDF is rendered from the exact text the verifier passed. Nothing is added
at this stage except page furniture: a running header with the title, a
footer with the engine commit and the dataset digest, and page numbers. The
markdown subset is the one the generators emit, so a construct this typesetter
does not know cannot appear.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.platypus.flowables import Flowable

INK = colors.HexColor("#1A1A1A"); SOFT = colors.HexColor("#5C5C5C"); RULE = colors.HexColor("#BFBFBF")
ACCENT = colors.HexColor("#C2481C"); EARNED = colors.HexColor("#1F7A6B"); ARTIFACT = colors.HexColor("#6C56A6")

S = {
    "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=22, leading=27, spaceAfter=6, textColor=INK),
    "standfirst": ParagraphStyle("standfirst", fontName="Times-Italic", fontSize=11, leading=15, textColor=SOFT, spaceAfter=14),
    "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=13.5, leading=17, spaceBefore=14, spaceAfter=5, textColor=INK),
    "h3": ParagraphStyle("h3", fontName="Times-BoldItalic", fontSize=11.5, leading=15, spaceBefore=9, spaceAfter=3, textColor=INK),
    "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=10.5, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=7, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="Times-Roman", fontSize=10.5, leading=14, leftIndent=14, bulletIndent=2, spaceAfter=3, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.2, leading=10.5, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=7.6, leading=10, textColor=SOFT),
    "caption": ParagraphStyle("caption", fontName="Times-Italic", fontSize=9, leading=12, textColor=SOFT, spaceBefore=3, spaceAfter=10),
}


def _inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.6">\1</font>', text)
    return text


class BarFigure(Flowable):
    """A bar chart drawn from labelled counts. Values are printed on the bars,
    so the figure never shows a magnitude the text does not state."""
    def __init__(self, rows: list[tuple[str, int, colors.Color]], width: float = 6.2 * inch):
        super().__init__()
        self.rows, self.width = rows, width
        self.height = 16 * len(rows) + 10

    def draw(self) -> None:
        c = self.canv
        maxv = max([v for _, v, _ in self.rows] + [1])
        label_w, bar_w = 1.55 * inch, self.width - 1.55 * inch - 0.5 * inch
        y = self.height - 12
        for label, value, color in self.rows:
            c.setFillColor(SOFT); c.setFont("Helvetica", 7.6)
            c.drawRightString(label_w - 6, y + 2, label)
            c.setFillColor(colors.HexColor("#EEEEEE")); c.rect(label_w, y - 1, bar_w, 9, stroke=0, fill=1)
            c.setFillColor(color); c.rect(label_w, y - 1, bar_w * value / maxv, 9, stroke=0, fill=1)
            c.setFillColor(INK); c.setFont("Helvetica-Bold", 7.6)
            c.drawString(label_w + bar_w * value / maxv + 4, y + 1, str(value))
            y -= 16


def _table(rows: list[list[str]]) -> Table:
    head = [Paragraph(_inline(h), S["cellh"]) for h in rows[0]]
    body = [[Paragraph(_inline(c), S["cell"]) for c in r] for r in rows[1:]]
    t = Table([head] + body, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _figure_for(name: str, figures: dict[str, list[tuple[str, int, str]]]) -> list[Flowable]:
    rows = figures.get(name)
    if not rows:
        return []
    palette = {"earned": EARNED, "artifact": ARTIFACT, "accent": ACCENT, "soft": SOFT}
    return [BarFigure([(l, v, palette.get(tone, SOFT)) for l, v, tone in rows])]


def render_pdf(document: str, out: Path, *, engine_commit: str, dataset_sha256: str,
               figures: dict[str, list[tuple[str, int, str]]] | None = None) -> int:
    """Typeset `document` to `out`. Returns the page count."""
    figures = figures or {}
    lines = document.splitlines()
    title = next((l[2:] for l in lines if l.startswith("# ")), "Untitled")
    flow: list[Flowable] = []
    table: list[list[str]] = []
    i = 0

    def flush_table() -> None:
        nonlocal table
        if table:
            rows = [r for r in table if not set("".join(r)) <= set("-: ")]
            flow.append(_table(rows)); flow.append(Spacer(1, 8))
            table = []

    while i < len(lines):
        line = lines[i]; i += 1
        if line.startswith("|"):
            table.append([c.strip() for c in line.strip().strip("|").split("|")]); continue
        flush_table()
        if not line.strip():
            continue
        if line.startswith("# "):
            flow.append(Paragraph(_inline(line[2:]), S["title"]))
        elif line.startswith("## "):
            head = line[3:]
            flow.append(Paragraph(_inline(head), S["h2"]))
            flow.extend(_figure_for(head, figures))
        elif line.startswith("### "):
            flow.append(Paragraph(_inline(line[4:]), S["h3"]))
        elif line.startswith("- "):
            flow.append(Paragraph(_inline(line[2:]), S["bullet"], bulletText="•"))
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            flow.append(Paragraph(_inline(line.strip("*")), S["standfirst"]))
        elif line.startswith("Figure "):
            flow.append(Paragraph(_inline(line), S["caption"]))
        else:
            flow.append(Paragraph(_inline(line), S["body"]))
    flush_table()

    def furniture(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7); canvas.setFillColor(SOFT)
        canvas.drawString(0.9 * inch, letter[1] - 0.6 * inch, title[:90])
        canvas.drawRightString(letter[0] - 0.9 * inch, letter[1] - 0.6 * inch, "CRUCIBLE, generated from run records")
        canvas.setStrokeColor(RULE); canvas.line(0.9 * inch, letter[1] - 0.66 * inch, letter[0] - 0.9 * inch, letter[1] - 0.66 * inch)
        canvas.drawString(0.9 * inch, 0.55 * inch, f"engine {engine_commit[:12]}  dataset sha256 {dataset_sha256[:24]}")
        canvas.drawRightString(letter[0] - 0.9 * inch, 0.55 * inch, f"{doc.page}")
        canvas.restoreState()

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=letter, leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                            topMargin=0.95 * inch, bottomMargin=0.85 * inch, title=title,
                            author="CRUCIBLE", subject="generated from run records")
    doc.build(flow, onFirstPage=furniture, onLaterPages=furniture)
    return doc.page
