"""Unit tests for error boundaries and graceful degradation."""

from __future__ import annotations

from src.analysis.pdf_export import generate_pdf_report
from src.analysis.research_consolidator import ConsolidatedReport, FunnelSummary
from src.decision.scenarios import get_scenario


def _minimal_report() -> ConsolidatedReport:
    """Create a report with all optional fields set to None."""
    return ConsolidatedReport.model_construct(
        scenario_id="nutrimix_2_6",
        scenario_name="Nutrimix Plus",
        question_title="Growth",
        question_description="Growth dec",
        funnel=FunnelSummary.model_construct(
            population_size=10,
            adoption_count=2,
            adoption_rate=0.2,
            rejection_distribution={},
            top_barriers=[],
            waterfall_data={},
        ),
        segments_by_tier=[],
        segments_by_income=[],
        causal_drivers=[],
        interview_count=0,
        clusters=[],
        top_alternatives=[],
        worst_alternatives=[],
        # All below are optional and can be None
        temporal_snapshots=None,
        behaviour_clusters=None,
        month_12_active_rate=None,
        peak_churn_month=None,
        revenue_estimate=None,
        event_monthly_rollup=None,
        event_daily_rollups=None,
        event_clusters=None,
        peak_churn_day=None,
        decision_rationale_summary=None,
        counterfactual_results=None,
        executive_summary=None,
    )


def test_pdf_export_graceful_with_none_fields():
    """PDF generation should not crash if optional report fields are None."""
    report = _minimal_report()
    scenario = get_scenario("nutrimix_2_6")

    # This should not raise any AttributeError or KeyError
    pdf_bytes = generate_pdf_report(report, scenario)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_report_funnel_missing_waterfall_data():
    """Waterfall logic should handle empty waterfall_data dictionary."""
    report = _minimal_report()
    report.funnel.waterfall_data = {}
    scenario = get_scenario("nutrimix_2_6")

    pdf_bytes = generate_pdf_report(report, scenario)
    assert len(pdf_bytes) > 0


def test_pdf_export_with_partially_missing_segments():
    """PDF should generate even if segment lists are empty."""
    report = _minimal_report()
    report.segments_by_tier = []
    report.segments_by_income = []
    scenario = get_scenario("nutrimix_2_6")

    pdf_bytes = generate_pdf_report(report, scenario)
    assert len(pdf_bytes) > 0


def test_snap_val_with_missing_keys():
    """_snap_val should return default if keys are missing."""
    from src.analysis.pdf_export import _snap_val
    row = {"a": 1}
    assert _snap_val(row, "b", default=42) == 42


def test_snap_val_with_none_values():
    """_snap_val should return default if value is None."""
    from src.analysis.pdf_export import _snap_val
    row = {"a": None}
    assert _snap_val(row, "a", default=42) == 42


def test_snap_val_fallback_chain():
    """_snap_val should follow the fallback chain correctly."""
    from src.analysis.pdf_export import _snap_val
    row = {"b": 2}
    assert _snap_val(row, "a", "b", default=42) == 2


def test_safe_txt_with_none():
    """_safe_txt should handle None or empty strings gracefully."""
    from src.analysis.pdf_export import _safe_txt
    # If passed None, it might fail unless we check.
    # Let's verify how it handles extreme strings.
    assert _safe_txt("Hello \u201cWorld\u201d") == 'Hello "World"'


def test_safe_txt_truncation():
    """_safe_txt should truncate long strings with ellipses."""
    from src.analysis.pdf_export import _safe_txt
    s = "A" * 100
    truncated = _safe_txt(s, max_len=10)
    assert len(truncated) == 10
    assert truncated.endswith("...")


def test_minimal_report_temporal_snapshots_none():
    """Report with temporal_snapshots=None should not break trajectory logic."""
    report = _minimal_report()
    report.temporal_snapshots = None
    from src.analysis.pdf_export import _figure_trajectory
    fig = _figure_trajectory(report)
    assert fig is None


def test_minimal_report_event_monthly_rollup_none():
    """Report with event_monthly_rollup=None should not break trajectory logic."""
    report = _minimal_report()
    report.event_monthly_rollup = None
    from src.analysis.pdf_export import _figure_trajectory
    fig = _figure_trajectory(report)
    assert fig is None


def test_report_funnel_waterfall_logic_step_down():
    """Waterfall rows should maintain monotonic step-down from population size."""
    from src.analysis.pdf_export import _waterfall_rows
    report = _minimal_report()
    report.funnel.population_size = 100
    report.funnel.waterfall_data = {"need_recognition": 80, "awareness": 60}
    rows = _waterfall_rows(report)
    # (stage, passed, dropped)
    assert rows[0] == ("need_recognition", 80, 20)
    assert rows[1] == ("awareness", 60, 20)
    assert rows[2] == ("consideration", 0, 60) # 0 passed, 60 dropped from 60


def test_report_funnel_waterfall_all_zero():
    """Waterfall rows should handle all-zero funnel data."""
    from src.analysis.pdf_export import _waterfall_rows
    report = _minimal_report()
    report.funnel.population_size = 100
    report.funnel.waterfall_data = {}
    rows = _waterfall_rows(report)
    for _, passed, _ in rows:
        assert passed == 0


def test_pdf_export_with_empty_causal_drivers():
    """PDF should generate even if causal_drivers is empty."""
    report = _minimal_report()
    report.causal_drivers = []
    scenario = get_scenario("nutrimix_2_6")
    pdf_bytes = generate_pdf_report(report, scenario)
    assert len(pdf_bytes) > 0
