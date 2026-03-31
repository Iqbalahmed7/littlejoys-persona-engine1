"""Generate stakeholder-ready PDF exports from consolidated research reports."""

from __future__ import annotations

import io
import re
from datetime import UTC, datetime
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio
from fpdf import FPDF

from src.analysis.research_consolidator import ConsolidatedReport  # noqa: TC001
from src.decision.scenarios import ScenarioConfig  # noqa: TC001

_FUNNEL_STAGES: tuple[str, ...] = (
    "need_recognition",
    "awareness",
    "consideration",
    "purchase",
)


def _snap_val(row: dict[str, Any], *keys: str, default: Any = 0) -> Any:
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def _safe_txt(s: str, max_len: int | None = None) -> str:
    """Keep Latin-1-friendly text for core PDF fonts."""
    t = re.sub(r"[\u201c\u201d]", '"', s)
    t = re.sub(r"[\u2019]", "'", t)
    t = t.encode("latin-1", "replace").decode("latin-1")
    if max_len is not None and len(t) > max_len:
        return t[: max_len - 3] + "..."
    return t


def _waterfall_rows(report: ConsolidatedReport) -> list[tuple[str, int, int]]:
    wd = report.funnel.waterfall_data
    n = report.funnel.population_size
    entered = n
    rows: list[tuple[str, int, int]] = []
    for stage in _FUNNEL_STAGES:
        passed = int(wd.get(stage, 0))
        dropped = max(0, entered - passed)
        rows.append((stage, passed, dropped))
        entered = passed
    return rows


def _monthly_trajectory_rows(report: ConsolidatedReport) -> list[dict[str, Any]] | None:
    rows = report.event_monthly_rollup or report.temporal_snapshots
    return rows if rows else None


def _figure_trajectory(report: ConsolidatedReport) -> go.Figure | None:
    monthly_rows = _monthly_trajectory_rows(report)
    if not monthly_rows:
        return None

    months = [int(_snap_val(s, "month")) for s in monthly_rows]
    total_active = [float(_snap_val(s, "total_active", "active")) for s in monthly_rows]
    new_adopters = [float(_snap_val(s, "new_adopters")) for s in monthly_rows]
    churned_s = [float(_snap_val(s, "churned")) for s in monthly_rows]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=total_active,
            mode="lines+markers",
            name="Total active",
            line={"color": "#1f77b4", "width": 3},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=new_adopters,
            mode="lines+markers",
            name="New adopters",
            line={"color": "#2ca02c", "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=churned_s,
            mode="lines+markers",
            name="Churned",
            line={"color": "#d62728", "width": 2},
        )
    )
    fig.update_layout(
        title="Monthly trajectory",
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Month",
        yaxis_title="Personas",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _figure_retention_rate(report: ConsolidatedReport) -> go.Figure | None:
    monthly_rows = _monthly_trajectory_rows(report)
    pop = report.funnel.population_size
    if not monthly_rows or pop <= 0:
        return None

    months = [int(_snap_val(s, "month")) for s in monthly_rows]
    total_active = [float(_snap_val(s, "total_active", "active")) for s in monthly_rows]
    rates = [100.0 * t / float(pop) for t in total_active]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=rates,
            mode="lines+markers",
            name="Active rate",
            line={"color": "#ff7f0e", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(255, 127, 14, 0.15)",
        )
    )
    fig.update_layout(
        title="Retention curve (active / population)",
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Month",
        yaxis_title="Active (%)",
        yaxis=dict(range=[0, max(100.0, max(rates) * 1.1) if rates else 100.0]),
    )
    return fig


def _fig_to_png(fig: go.Figure) -> bytes | None:
    try:
        return pio.to_image(fig, format="png", width=700, height=350, scale=1, engine="kaleido")
    except Exception:
        return None


class ReportPDF(FPDF):
    """PDF document with branded header/footer."""

    def __init__(self, export_date: str) -> None:
        super().__init__()
        self._export_date = export_date
        self.set_auto_page_break(auto=True, margin=15)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "LittleJoys Research Report", new_x="LMARGIN", new_y="NEXT", align="R")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-18)
        self.set_font("Helvetica", "I", 8)
        self.cell(
            0,
            5,
            _safe_txt(f"Generated by LittleJoys Persona Engine - {self._export_date}"),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.cell(0, 5, f"Page {self.page_no()}", align="C")


def _para(pdf: FPDF, text: str, h: float = 5, align: str = "L") -> None:
    """Full-width paragraph; resets X so width is never zero after a ``cell`` call."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, h, text, align=align)


def _table_row(pdf: FPDF, cells: list[str], col_widths: list[float], bold: bool = False) -> None:
    pdf.set_font("Helvetica", "B" if bold else "", 9)
    h = 7
    for w, txt in zip(col_widths, cells, strict=True):
        pdf.cell(w, h, _safe_txt(txt, 120), border=1, align="L")
    pdf.ln()


def generate_pdf_report(report: ConsolidatedReport, scenario: ScenarioConfig) -> bytes:
    """Generate a professional PDF report from consolidated research results."""

    export_date = datetime.now(UTC).strftime("%Y-%m-%d UTC")
    pdf = ReportPDF(export_date)

    # --- Cover ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    _para(pdf, _safe_txt("LittleJoys Persona Engine - Research Report"), h=12, align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 14)
    _para(pdf, _safe_txt(scenario.name), h=10, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    _para(pdf, _safe_txt(scenario.description or ""), h=6, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, _safe_txt(f"Date: {export_date}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        8,
        _safe_txt(f"Population: {report.funnel.population_size:,} personas"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    headline = (
        f"Trial rate: {report.funnel.adoption_rate:.1%}"
        + (
            f"  |  Final active rate: {report.month_12_active_rate:.1%}"
            if report.month_12_active_rate is not None
            else ""
        )
    )
    _para(pdf, _safe_txt(headline), h=8, align="C")

    # --- Executive summary ---
    if report.executive_summary is not None:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 11)
        _para(pdf, _safe_txt(report.executive_summary.headline), h=6)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        _para(pdf, _safe_txt(report.executive_summary.trajectory_summary), h=5)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Key Drivers", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for item in report.executive_summary.key_drivers:
            _para(pdf, _safe_txt(f"- {item}"), h=5)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Recommendations", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for item in report.executive_summary.recommendations:
            _para(pdf, _safe_txt(f"- {item}"), h=5)
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Risk Factors", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for item in report.executive_summary.risk_factors:
            _para(pdf, _safe_txt(f"- {item}"), h=5)

    # --- Funnel ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Funnel Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Waterfall: Stage | Passed | Dropped", new_x="LMARGIN", new_y="NEXT")
    wcols = [55, 40, 40]
    _table_row(pdf, ["Stage", "Passed", "Dropped"], wcols, bold=True)
    pdf.set_font("Helvetica", "", 9)
    for stage, passed, dropped in _waterfall_rows(report):
        _table_row(pdf, [stage, str(passed), str(dropped)], wcols)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Top barriers", new_x="LMARGIN", new_y="NEXT")
    bw = [35, 110, 25]
    _table_row(pdf, ["Stage", "Barrier", "Count"], bw, bold=True)
    for b in report.funnel.top_barriers[:10]:
        _table_row(
            pdf,
            [str(b.get("stage", "")), str(b.get("reason", "")), str(b.get("count", ""))],
            bw,
        )

    # --- Segments ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Segment Analysis", new_x="LMARGIN", new_y="NEXT")
    sw = [42, 42, 38, 38]
    _table_row(pdf, ["Segment type", "Value", "Adoption rate", "Delta vs pop."], sw, bold=True)
    for seg in report.segments_by_tier + report.segments_by_income:
        _table_row(
            pdf,
            [
                _safe_txt(seg.segment_name, 35),
                _safe_txt(seg.segment_value, 35),
                f"{seg.adoption_rate:.1%}",
                f"{seg.delta_vs_population:+.1%}",
            ],
            sw,
        )

    # --- Temporal charts ---
    fig_traj = _figure_trajectory(report)
    fig_ret = _figure_retention_rate(report)
    if fig_traj is not None or fig_ret is not None:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Temporal Trajectory", new_x="LMARGIN", new_y="NEXT")
        for label, fig in (
            ("Monthly dynamics", fig_traj),
            ("Retention", fig_ret),
        ):
            if fig is None:
                continue
            png = _fig_to_png(fig)
            if png:
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 7, _safe_txt(label), new_x="LMARGIN", new_y="NEXT")
                pdf.image(io.BytesIO(png), w=180)
                pdf.ln(4)
            else:
                pdf.set_font("Helvetica", "I", 9)
                _para(
                    pdf,
                    _safe_txt(f"{label}: chart export unavailable (Kaleido)."),
                    h=5,
                )

    # --- Counterfactuals ---
    if report.counterfactual_results:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Counterfactual Analysis", new_x="LMARGIN", new_y="NEXT")
        cw = [52, 28, 28, 22, 40]
        _table_row(
            pdf,
            ["Intervention", "Baseline", "With change", "Lift %", "Revenue (INR)"],
            cw,
            bold=True,
        )
        for cf in report.counterfactual_results:
            label = cf.label or cf.counterfactual_name or cf.scenario_id or "?"
            base = cf.baseline_active_rate
            alt = cf.counterfactual_active_rate
            lift = cf.lift_pct
            rev = cf.revenue_lift
            _table_row(
                pdf,
                [
                    _safe_txt(str(label), 40),
                    f"{float(base):.1%}" if base is not None else "-",
                    f"{float(alt):.1%}" if alt is not None else "-",
                    f"{float(lift):+.1f}" if lift is not None else "-",
                    f"{float(rev):+,.0f}" if rev is not None else "-",
                ],
                cw,
            )

    # --- Interview themes ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Interview Themes", new_x="LMARGIN", new_y="NEXT")
    tw = [45, 22, 22, 101]
    _table_row(pdf, ["Theme", "Personas", "Pct", "Top quote"], tw, bold=True)
    for cl in report.clusters[:20]:
        quote = cl.representative_quotes[0] if cl.representative_quotes else ""
        quote = quote[:100] + ("..." if len(quote) > 100 else "")
        _table_row(
            pdf,
            [
                _safe_txt(cl.theme.replace("_", " "), 35),
                str(cl.persona_count),
                f"{cl.percentage:.0%}",
                _safe_txt(quote, 200),
            ],
            tw,
        )

    return bytes(pdf.output())


def export_synthesis_pdf(
    core_finding: dict,
    cohort_summary: dict,
    scenario_id: str,
    top_interventions: list[dict],
) -> bytes:
    """Generate a 2-page professional synthesis brief PDF from investigation results."""

    export_date = datetime.now(UTC).strftime("%Y-%m-%d UTC")
    pdf = ReportPDF(export_date)
    pdf.add_page()

    # --- Header / Title ---
    pdf.set_font("Helvetica", "B", 18)
    _para(pdf, _safe_txt("LittleJoys Persona Engine — Synthesis Report"), h=10, align="C")
    pdf.ln(5)

    # --- Business Problem ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Business Problem", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    # Human-readable labels (mirroring app/pages/8_synthesis_report.py)
    _problem_labels = {
        "nutrimix_2_6": "Why is repeat purchase low despite high NPS? (Nutrimix 2-6)",
        "nutrimix_7_14": "How do we expand Nutrimix from 2-6 to the 7-14 age group?",
        "magnesium_gummies": "How do we grow sales of a supplement? (Magnesium Gummies)",
        "protein_mix": "The product requires cooking — how do we overcome the effort barrier?",
    }
    _label = _problem_labels.get(scenario_id, scenario_id)
    _para(pdf, _safe_txt(str(_label)), h=6)
    pdf.ln(4)

    # --- Population Baseline ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Population Baseline", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    _total = sum(cohort_summary.values()) or 1
    _table_row(pdf, ["Cohort", "Count", "Percentage"], [60, 40, 40], bold=True)
    for cid, cnt in cohort_summary.items():
        _label = cid.replace("_", " ").title()
        _table_row(pdf, [_label, f"{cnt:,}", f"{cnt/_total:.1%}"], [60, 40, 40])
    pdf.ln(6)

    # --- Core Finding ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "3. Core Finding", new_x="LMARGIN", new_y="NEXT")
    
    _statement = core_finding.get("dominant_hypothesis_title") or core_finding.get("dominant_hypothesis", "N/A")
    _conf = core_finding.get("overall_confidence", 0.0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(254, 249, 231)  # Light yellow background for finding
    pdf.multi_cell(pdf.epw, 7, _safe_txt(f"{_statement} (Confidence: {_conf:.0%})"), border=1, fill=True)
    pdf.ln(4)
    
    # Supporting evidence snippets
    confirmed = core_finding.get("confirmed_hypotheses", [])
    if confirmed:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, "Supporting evidence:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for hyp in confirmed:
            _htitle = hyp.get("title", "?")
            _hconf = hyp.get("confidence", 0.0)
            _para(pdf, _safe_txt(f"- {_htitle} ({_hconf:.0%})"), h=5)
    pdf.ln(6)

    # --- Interventions ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "4. Recommended Interventions", new_x="LMARGIN", new_y="NEXT")
    if top_interventions:
        icols = [70, 35, 35]
        _table_row(pdf, ["Intervention", "Projection", "Lift"], icols, bold=True)
        for row in top_interventions[:5]:
            _name = row.get("name", "Unknown")
            _rate = row.get("adoption_rate", 0.0)
            _lift = row.get("lift", 0.0)
            _table_row(pdf, [_name, f"{_rate:.1%} adoption", f"{_lift:+.1%}"], icols)
    else:
        pdf.set_font("Helvetica", "I", 9)
        _para(pdf, "No intervention data available for this report.")

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    _para(pdf, "Professional synthesis generated by LittleJoys Persona Engine. Confirmatory research based on 200-persona population distribution.", align="C")

    return bytes(pdf.output())
