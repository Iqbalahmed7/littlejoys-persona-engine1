"""Sprint 33A — research-grade PDF renderer.

Uses ReportLab Platypus + Matplotlib to render a ReportData object as a
fully self-contained PDF (no external file dependencies at render time).
"""

from __future__ import annotations

import io
import textwrap
from io import BytesIO
from typing import Any

import matplotlib
matplotlib.use("Agg")  # headless — must be set before importing pyplot
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.reporting.report_builder import HypothesisReport, ReportData

# ── Colour palette ─────────────────────────────────────────────────────────────

NAVY = colors.HexColor("#1E3A5F")
GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#DC2626")
LIGHT_GREY = colors.HexColor("#F3F4F6")
MID_GREY = colors.HexColor("#9CA3AF")
DARK_GREY = colors.HexColor("#374151")
WHITE = colors.white
CALLOUT_BLUE = colors.HexColor("#EFF6FF")
CALLOUT_BLUE_BORDER = colors.HexColor("#3B82F6")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm


# ── StyleSheet ─────────────────────────────────────────────────────────────────

def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    s: dict[str, ParagraphStyle] = {}

    s["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=NAVY,
        spaceAfter=8,
        leading=34,
        alignment=TA_CENTER,
    )
    s["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle",
        fontName="Helvetica",
        fontSize=16,
        textColor=DARK_GREY,
        spaceAfter=6,
        leading=20,
        alignment=TA_CENTER,
    )
    s["cover_meta"] = ParagraphStyle(
        "cover_meta",
        fontName="Helvetica",
        fontSize=11,
        textColor=MID_GREY,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    s["cover_confidential"] = ParagraphStyle(
        "cover_confidential",
        fontName="Helvetica-BoldOblique",
        fontSize=11,
        textColor=RED,
        alignment=TA_CENTER,
    )
    s["section_heading"] = ParagraphStyle(
        "section_heading",
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=6,
        leading=18,
    )
    s["sub_heading"] = ParagraphStyle(
        "sub_heading",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=DARK_GREY,
        spaceBefore=8,
        spaceAfter=4,
    )
    s["body"] = ParagraphStyle(
        "body_text",
        fontName="Helvetica",
        fontSize=10,
        textColor=DARK_GREY,
        spaceAfter=6,
        leading=15,
    )
    s["body_small"] = ParagraphStyle(
        "body_small",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_GREY,
        spaceAfter=4,
        leading=13,
    )
    s["bullet"] = ParagraphStyle(
        "bullet_text",
        fontName="Helvetica",
        fontSize=10,
        textColor=DARK_GREY,
        spaceAfter=5,
        leading=15,
        leftIndent=12,
        bulletIndent=0,
    )
    s["quote"] = ParagraphStyle(
        "quote_text",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=DARK_GREY,
        leftIndent=12,
        rightIndent=8,
        spaceAfter=4,
        leading=14,
    )
    s["big_metric"] = ParagraphStyle(
        "big_metric",
        fontName="Helvetica-Bold",
        fontSize=36,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    s["metric_label"] = ParagraphStyle(
        "metric_label",
        fontName="Helvetica",
        fontSize=11,
        textColor=MID_GREY,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    s["callout"] = ParagraphStyle(
        "callout_text",
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#1D4ED8"),
        leftIndent=8,
        rightIndent=8,
        spaceAfter=4,
        leading=15,
    )
    s["table_header"] = ParagraphStyle(
        "table_header",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=WHITE,
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_GREY,
        leading=13,
    )
    return s


# ── Matplotlib chart helpers ───────────────────────────────────────────────────

def _confidence_bar_chart(hypotheses: list[HypothesisReport]) -> BytesIO:
    """Horizontal bar chart of all hypothesis confidence scores."""
    if not hypotheses:
        fig, ax = plt.subplots(figsize=(6, 1))
        ax.text(0.5, 0.5, "No hypotheses", ha="center", va="center")
        ax.axis("off")
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    labels = [f"H{i+1}: {textwrap.shorten(h.title, 45)}" for i, h in enumerate(hypotheses)]
    values = [h.confidence for h in hypotheses]
    bar_colors = []
    for v in values:
        if v >= 0.65:
            bar_colors.append("#059669")
        elif v >= 0.40:
            bar_colors.append("#D97706")
        else:
            bar_colors.append("#DC2626")

    fig_h = max(1.5, len(hypotheses) * 0.55)
    fig, ax = plt.subplots(figsize=(6.5, fig_h))
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=bar_colors, height=0.55, zorder=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Confidence", fontsize=8)
    ax.axvline(x=0.65, color="#059669", linewidth=1, linestyle="--", alpha=0.5, label="Confirmed threshold")
    ax.axvline(x=0.40, color="#D97706", linewidth=1, linestyle="--", alpha=0.5, label="Inconclusive threshold")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for bar, val in zip(bars, values):
        ax.text(
            min(val + 0.02, 0.97),
            bar.get_y() + bar.get_height() / 2,
            f"{int(val * 100)}%",
            va="center",
            fontsize=7.5,
            color="#374151",
        )
    legend_patches = [
        mpatches.Patch(color="#059669", label="Confirmed (≥65%)"),
        mpatches.Patch(color="#D97706", label="Inconclusive (40–65%)"),
        mpatches.Patch(color="#DC2626", label="Rejected (<40%)"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="lower right")
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _attribute_split_chart(splits: list[dict], title: str) -> BytesIO:
    """Side-by-side horizontal bars: adopters (blue) vs rejectors (red)."""
    if not splits:
        return None  # type: ignore[return-value]

    labels = [s["attribute"] for s in splits]
    adopter_vals = [s["adopter"] for s in splits]
    rejector_vals = [s["rejector"] for s in splits]

    fig_h = max(1.2, len(labels) * 0.5)
    fig, ax = plt.subplots(figsize=(5.5, fig_h))
    y_pos = np.arange(len(labels))
    bar_h = 0.35
    ax.barh(y_pos + bar_h / 2, adopter_vals, height=bar_h, color="#3B82F6", label="Adopters", zorder=2)
    ax.barh(y_pos - bar_h / 2, rejector_vals, height=bar_h, color="#EF4444", label="Rejectors", zorder=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([textwrap.shorten(l, 30) for l in labels], fontsize=8)
    ax.set_xlabel("Mean value", fontsize=8)
    ax.set_title(textwrap.shorten(title, 55), fontsize=9, color="#1E3A5F")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=7)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ── PDF building blocks ────────────────────────────────────────────────────────

def _status_colour(status: str) -> colors.Color:
    return {"confirmed": GREEN, "inconclusive": AMBER, "rejected": RED}.get(status, MID_GREY)


def _confidence_colour(confidence: float) -> colors.Color:
    if confidence >= 0.65:
        return GREEN
    if confidence >= 0.40:
        return AMBER
    return RED


def _buf_to_image(buf: BytesIO, max_width: float, max_height: float | None = None) -> Image:
    buf.seek(0)
    img = Image(buf)
    # Scale proportionally
    ratio = img.imageWidth / img.imageHeight
    w = min(max_width, img.imageWidth)
    h = w / ratio
    if max_height and h > max_height:
        h = max_height
        w = h * ratio
    img.drawWidth = w
    img.drawHeight = h
    return img


def _quote_table(quotes: list[str], styles: dict) -> Table | None:
    if not quotes:
        return None
    rows = []
    for q in quotes:
        rows.append([
            Paragraph(f'"{textwrap.shorten(q, 260)}"', styles["quote"])
        ])
    tbl = Table([[r[0]] for r in rows], colWidths=[PAGE_W - 2 * MARGIN - 1 * cm])
    tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#9CA3AF")),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, WHITE]),
    ]))
    return tbl


def _callout_box(text: str, styles: dict) -> Table:
    cell = Paragraph(text, styles["callout"])
    tbl = Table([[cell]], colWidths=[PAGE_W - 2 * MARGIN - 1 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CALLOUT_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBEFORE", (0, 0), (0, -1), 4, CALLOUT_BLUE_BORDER),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return tbl


def _intervention_table(interventions: list[dict], styles: dict) -> Table:
    col_w = [
        (PAGE_W - 2 * MARGIN) * 0.30,
        (PAGE_W - 2 * MARGIN) * 0.14,
        (PAGE_W - 2 * MARGIN) * 0.12,
        (PAGE_W - 2 * MARGIN) * 0.44,
    ]
    header = [
        Paragraph("Intervention", styles["table_header"]),
        Paragraph("Type", styles["table_header"]),
        Paragraph("Expected Lift", styles["table_header"]),
        Paragraph("Rationale", styles["table_header"]),
    ]
    rows: list[list[Any]] = [header]
    for i, inv in enumerate(interventions):
        rows.append([
            Paragraph(inv.get("title", ""), styles["table_cell"]),
            Paragraph(inv.get("intervention_type", ""), styles["table_cell"]),
            Paragraph(f"+{inv.get('expected_lift_pct', 0)}%", styles["table_cell"]),
            Paragraph(textwrap.shorten(inv.get("rationale", ""), 220), styles["table_cell"]),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]
    for row_idx in range(1, len(rows)):
        if row_idx % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), LIGHT_GREY))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ── Page templates ─────────────────────────────────────────────────────────────

def _page_header_footer(canvas, doc):
    """Draws a thin navy top bar and page number on every page except page 1."""
    canvas.saveState()
    if doc.page > 1:
        canvas.setFillColor(NAVY)
        canvas.rect(MARGIN, PAGE_H - 1.2 * cm, PAGE_W - 2 * MARGIN, 2, fill=1, stroke=0)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MID_GREY)
        canvas.drawString(MARGIN, 1.2 * cm, "LittleJoys Research Intelligence — Confidential")
        canvas.drawRightString(PAGE_W - MARGIN, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ── Main renderer ──────────────────────────────────────────────────────────────

def render_pdf(report_data: ReportData) -> bytes:
    """Render a ReportData as a research-grade PDF; returns raw PDF bytes."""

    buf = io.BytesIO()
    styles = _build_styles()

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 0.5 * cm,
        bottomMargin=MARGIN,
    )

    content_width = PAGE_W - 2 * MARGIN

    frame = Frame(
        MARGIN,
        MARGIN,
        content_width,
        PAGE_H - 2 * MARGIN - 0.5 * cm,
        id="main",
    )
    template = PageTemplate(id="main", frames=[frame], onPage=_page_header_footer)
    doc.addPageTemplates([template])

    story: list[Any] = []

    # ── PAGE 1: Cover ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 3.5 * cm))
    story.append(Paragraph("Research Intelligence Report", styles["cover_title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="60%", thickness=2, color=NAVY, hAlign="CENTER"))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(report_data.problem_title, styles["cover_subtitle"]))
    story.append(Spacer(1, 0.4 * cm))

    generated_dt = report_data.generated_at
    story.append(Paragraph(f"Generated: {generated_dt}", styles["cover_meta"]))
    story.append(Spacer(1, 0.2 * cm))
    if report_data.total_personas > 0:
        story.append(
            Paragraph(
                f"Synthetic population: {report_data.total_personas:,} personas",
                styles["cover_meta"],
            )
        )
    story.append(Spacer(1, 3.0 * cm))

    # LittleJoys branding block
    brand_data = [
        [Paragraph("<b>LittleJoys</b>", ParagraphStyle(
            "brand", fontName="Helvetica-Bold", fontSize=18, textColor=NAVY, alignment=TA_CENTER
        ))],
        [Paragraph(
            "Simulation-Powered Consumer Research",
            ParagraphStyle("brand_sub", fontName="Helvetica", fontSize=10, textColor=MID_GREY, alignment=TA_CENTER),
        )],
    ]
    brand_tbl = Table(brand_data, colWidths=[content_width])
    brand_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(brand_tbl)
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("Confidential — Internal Research Brief", styles["cover_confidential"]))
    story.append(PageBreak())

    # ── PAGE 2: Executive Summary ──────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.4 * cm))

    # Big metric
    overall_pct = int(report_data.overall_confidence * 100)
    story.append(Paragraph(f"{overall_pct}%", styles["big_metric"]))
    story.append(Paragraph("Overall Confidence", styles["metric_label"]))

    confirmed_count = sum(1 for h in report_data.hypotheses if h.status == "confirmed")
    total_count = len(report_data.hypotheses)
    story.append(
        Paragraph(
            f"{confirmed_count} of {total_count} hypothesis{'es' if total_count != 1 else ''} confirmed",
            styles["metric_label"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Top Findings", styles["sub_heading"]))
    for i, finding in enumerate(report_data.top_findings, 1):
        story.append(Paragraph(f"{i}. {finding}", styles["bullet"]))

    story.append(Spacer(1, 0.5 * cm))

    # Key recommendation box
    if report_data.recommended_interventions:
        top_inv = report_data.recommended_interventions[0]
        rec_text = (
            f"<b>Key Recommendation:</b> {top_inv.get('title', '')} — "
            f"Expected lift: +{top_inv.get('expected_lift_pct', 0)}%. "
            f"{textwrap.shorten(top_inv.get('rationale', ''), 200)}"
        )
        story.append(_callout_box(rec_text, styles))

    # Confidence overview chart (all hypotheses)
    if report_data.hypotheses:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Hypothesis Confidence Overview", styles["sub_heading"]))
        chart_buf = _confidence_bar_chart(report_data.hypotheses)
        img = _buf_to_image(chart_buf, content_width, max_height=12 * cm)
        story.append(img)

    story.append(PageBreak())

    # ── PAGES 3–N: Hypothesis Findings ────────────────────────────────────────
    for idx, hyp in enumerate(report_data.hypotheses):
        conf_colour = _confidence_colour(hyp.confidence)
        status_colour = _status_colour(hyp.status)

        # Section header
        story.append(
            Paragraph(
                f"H{idx + 1}: {hyp.title}",
                styles["section_heading"],
            )
        )
        story.append(HRFlowable(width="100%", thickness=1, color=conf_colour))
        story.append(Spacer(1, 0.3 * cm))

        # Status badge row
        badge_label = hyp.status.upper()
        badge_data = [
            [
                Paragraph(f"<b>{badge_label}</b>", ParagraphStyle(
                    f"badge_{hyp.id}",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=WHITE,
                    alignment=TA_CENTER,
                )),
                Paragraph(
                    f"Confidence: <b>{int(hyp.confidence * 100)}%</b>",
                    styles["body"],
                ),
            ]
        ]
        badge_tbl = Table(badge_data, colWidths=[3 * cm, content_width - 3 * cm])
        badge_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), status_colour),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(badge_tbl)
        story.append(Spacer(1, 0.3 * cm))

        # Evidence summary
        if hyp.evidence_summary:
            story.append(Paragraph("Evidence Summary", styles["sub_heading"]))
            story.append(Paragraph(hyp.evidence_summary, styles["body"]))

        # Key verbatim quotes
        if hyp.key_quotes:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph("Key Verbatim Quotes", styles["sub_heading"]))
            qt = _quote_table(hyp.key_quotes, styles)
            if qt:
                story.append(qt)

        # Attribute split chart
        if hyp.attribute_splits:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph("Attribute Splits: Adopters vs Rejectors", styles["sub_heading"]))
            split_buf = _attribute_split_chart(hyp.attribute_splits, hyp.title)
            if split_buf is not None:
                split_img = _buf_to_image(split_buf, content_width * 0.75, max_height=8 * cm)
                story.append(split_img)

        # Recommended action callout
        story.append(Spacer(1, 0.3 * cm))
        story.append(
            _callout_box(f"<b>Recommended Action:</b> {hyp.recommended_action}", styles)
        )

        story.append(Spacer(1, 0.4 * cm))
        if idx < len(report_data.hypotheses) - 1:
            story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY))
            story.append(Spacer(1, 0.3 * cm))

    if report_data.hypotheses:
        story.append(PageBreak())

    # ── LAST PAGE: Recommended Interventions ──────────────────────────────────
    story.append(Paragraph("Recommended Interventions", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.4 * cm))

    if report_data.recommended_interventions:
        story.append(_intervention_table(report_data.recommended_interventions, styles))
    else:
        story.append(Paragraph("No specific interventions identified.", styles["body"]))

    story.append(Spacer(1, 0.6 * cm))

    # Next Steps
    story.append(Paragraph("Next Steps", styles["sub_heading"]))
    next_steps_lines = [
        "1. Validate the top confirmed hypothesis with a small qualitative study (n=10 parent interviews).",
        "2. Brief the brand team on the recommended intervention with the highest expected lift.",
        "3. Set up an A/B test or piloted rollout using the intervention config parameters above.",
        "4. Re-run this probing tree after 4 weeks to measure confidence shift post-intervention.",
        "5. Archive this report and synthesis in the LittleJoys research repository.",
    ]
    for line in next_steps_lines:
        story.append(Paragraph(line, styles["bullet"]))

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "Generated by LittleJoys Research Intelligence Platform — Confidential",
            styles["cover_meta"],
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf.read()
