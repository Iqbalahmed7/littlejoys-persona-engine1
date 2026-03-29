"""Tests for exploration consolidation and insight generation."""

import pytest

try:
    from src.decision.scenarios import get_scenario
    from src.simulation.consolidation import (
        ExplorationConsolidator,
        ExplorationReport,
        ParameterSensitivity,
        VariantResult,
    )
except ImportError:
    pytest.skip("Sprint 10 modules not merged", allow_module_level=True)


def _make_result(variant_id, name, rate, mods=None, is_baseline=False):
    return VariantResult(
        variant_id=variant_id,
        variant_name=name,
        adoption_rate=rate,
        adoption_count=int(rate * 200),
        population_size=200,
        rejection_distribution={"awareness": 50, "purchase": 30},
        modifications=mods or {},
        is_baseline=is_baseline,
        rank=0,
    )


@pytest.fixture
def sample_results():
    results = [
        _make_result("baseline", "Baseline", 0.40, is_baseline=True),
        _make_result("v001", "Price ₹399", 0.65, {"product.price_inr": 399}),
        _make_result("v002", "Price ₹799", 0.20, {"product.price_inr": 799}),
        _make_result("v003", "High Awareness", 0.55, {"marketing.awareness_budget": 0.8}),
        _make_result("v004", "Low Awareness", 0.25, {"marketing.awareness_budget": 0.2}),
        _make_result("v005", "School ON", 0.48, {"marketing.school_partnership": True}),
    ]
    results.sort(key=lambda x: x.adoption_rate, reverse=True)
    return results


class TestConsolidator:
    def test_report_has_all_fields(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        assert isinstance(report, ExplorationReport)
        assert report.total_variants == len(sample_results)
        assert report.baseline_result.is_baseline
        assert report.best_result.adoption_rate >= report.worst_result.adoption_rate

    def test_sensitivities_sorted_by_impact(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        if len(report.parameter_sensitivities) >= 2:
            scores = [s.sensitivity_score for s in report.parameter_sensitivities]
            assert scores == sorted(scores, reverse=True)

    def test_missed_insights_have_positive_lift(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        for insight in report.missed_insights:
            assert insight.lift_over_baseline > 0
            assert insight.adoption_rate > report.baseline_result.adoption_rate

    def test_missed_insights_limited(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        assert len(report.missed_insights) <= 10

    def test_missed_insights_have_explanations(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        for insight in report.missed_insights:
            assert len(insight.explanation) > 20
            assert len(insight.key_differences) >= 1


class TestVariantResultModel:
    def test_variant_result_creation(self):
        result = _make_result("test", "Test", 0.5)
        assert result.variant_id == "test"
        assert result.adoption_rate == 0.5

    def test_variant_result_extra_forbidden(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VariantResult(
                variant_id="x",
                variant_name="x",
                adoption_rate=0.5,
                adoption_count=100,
                population_size=200,
                rejection_distribution={},
                modifications={},
                extra_field="bad",
            )


class TestParameterSensitivityModel:
    def test_creation(self):
        ps = ParameterSensitivity(
            parameter_path="product.price_inr",
            parameter_display_name="Price",
            min_value=399,
            max_value=799,
            adoption_rate_at_min=0.65,
            adoption_rate_at_max=0.20,
            sensitivity_score=0.45,
        )
        assert ps.sensitivity_score == 0.45
