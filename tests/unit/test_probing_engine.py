"""Unit tests for the probing tree execution engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

import src.probing.engine as engine_module
from src.config import Config
from src.decision.funnel import DecisionResult
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.probing import ProbingTreeEngine, get_problem_tree
from src.probing.models import AttributeSplit, ProbeType, TreeSynthesis
from src.taxonomy.schema import (
    CareerAttributes,
    HealthAttributes,
    MediaAttributes,
    PsychologyAttributes,
    RelationshipAttributes,
    ValueAttributes,
)
from src.utils.llm import LLMClient

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def _mock_llm_client() -> LLMClient:
    return LLMClient(Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key=""))


def _persona_variant(
    template: Persona,
    *,
    persona_id: str,
    socioeconomic_class: str,
    city_tier: str,
    city_name: str,
    income: float,
    adopter_like: bool,
) -> Persona:
    return template.model_copy(
        update={
            "id": persona_id,
            "display_name": city_name,
            "demographics": template.demographics.model_copy(
                update={
                    "socioeconomic_class": socioeconomic_class,
                    "city_tier": city_tier,
                    "city_name": city_name,
                    "household_income_lpa": income,
                }
            ),
            "health": HealthAttributes(
                child_health_status=template.health.child_health_status,
                child_nutrition_concerns=template.health.child_nutrition_concerns,
                child_dietary_restrictions=template.health.child_dietary_restrictions,
                pediatrician_visit_frequency=template.health.pediatrician_visit_frequency,
                vaccination_attitude=template.health.vaccination_attitude,
                own_supplement_usage=template.health.own_supplement_usage,
                fitness_engagement=0.75 if adopter_like else 0.25,
                diet_consciousness=0.8 if adopter_like else 0.3,
                organic_preference=template.health.organic_preference,
                health_info_sources=template.health.health_info_sources,
                medical_authority_trust=0.82 if adopter_like else 0.28,
                self_research_tendency=template.health.self_research_tendency,
                child_health_proactivity=0.85 if adopter_like else 0.25,
                immunity_concern=0.8 if adopter_like else 0.25,
                growth_concern=0.8 if adopter_like else 0.25,
                nutrition_gap_awareness=0.85 if adopter_like else 0.2,
            ),
            "psychology": PsychologyAttributes(
                decision_speed=template.psychology.decision_speed,
                information_need=template.psychology.information_need,
                risk_tolerance=template.psychology.risk_tolerance,
                analysis_paralysis_tendency=template.psychology.analysis_paralysis_tendency,
                regret_sensitivity=template.psychology.regret_sensitivity,
                authority_bias=template.psychology.authority_bias,
                social_proof_bias=template.psychology.social_proof_bias,
                anchoring_bias=template.psychology.anchoring_bias,
                status_quo_bias=template.psychology.status_quo_bias,
                loss_aversion=template.psychology.loss_aversion,
                halo_effect_susceptibility=template.psychology.halo_effect_susceptibility,
                health_anxiety=0.85 if adopter_like else 0.2,
                comparison_anxiety=template.psychology.comparison_anxiety,
                guilt_sensitivity=template.psychology.guilt_sensitivity,
                control_need=template.psychology.control_need,
                mental_bandwidth=template.psychology.mental_bandwidth,
                decision_fatigue_level=template.psychology.decision_fatigue_level,
                simplicity_preference=0.35 if adopter_like else 0.8,
            ),
            "relationships": RelationshipAttributes(
                primary_decision_maker=template.relationships.primary_decision_maker,
                peer_influence_strength=0.6 if adopter_like else 0.4,
                influencer_trust=template.relationships.influencer_trust,
                elder_advice_weight=template.relationships.elder_advice_weight,
                pediatrician_influence=template.relationships.pediatrician_influence,
                wom_receiver_openness=template.relationships.wom_receiver_openness,
                wom_transmitter_tendency=template.relationships.wom_transmitter_tendency,
                negative_wom_amplification=template.relationships.negative_wom_amplification,
                child_pester_power=template.relationships.child_pester_power,
                child_taste_veto=0.25 if adopter_like else 0.82,
                child_autonomy_given=template.relationships.child_autonomy_given,
                partner_involvement=template.relationships.partner_involvement,
            ),
            "career": CareerAttributes(
                employment_status=template.career.employment_status,
                work_hours_per_week=template.career.work_hours_per_week,
                work_from_home=template.career.work_from_home,
                career_ambition=template.career.career_ambition,
                perceived_time_scarcity=0.75 if adopter_like else 0.35,
                morning_routine_complexity=0.7 if adopter_like else 0.4,
                cooking_time_available=0.35 if adopter_like else 0.75,
            ),
            "daily_routine": template.daily_routine.model_copy(
                update={
                    "budget_consciousness": 0.2 if adopter_like else 0.92,
                    "health_spend_priority": 0.82 if adopter_like else 0.25,
                    "deal_seeking_intensity": 0.25 if adopter_like else 0.88,
                    "impulse_purchase_tendency": 0.65 if adopter_like else 0.2,
                    "subscription_comfort": 0.78 if adopter_like else 0.18,
                    "price_reference_point": 850.0 if adopter_like else 240.0,
                    "milk_supplement_current": "littlejoys" if adopter_like else "horlicks",
                    "snacking_pattern": "structured" if adopter_like else "grazing",
                }
            ),
            "values": ValueAttributes(
                supplement_necessity_belief=0.8 if adopter_like else 0.2,
                natural_vs_synthetic_preference=template.values.natural_vs_synthetic_preference,
                food_first_belief=0.2 if adopter_like else 0.85,
                preventive_vs_reactive_health=template.values.preventive_vs_reactive_health,
                brand_loyalty_tendency=0.65 if adopter_like else 0.4,
                indie_brand_openness=0.6 if adopter_like else 0.3,
                transparency_importance=template.values.transparency_importance,
                made_in_india_preference=template.values.made_in_india_preference,
                best_for_my_child_intensity=0.88 if adopter_like else 0.4,
                guilt_driven_spending=template.values.guilt_driven_spending,
                peer_comparison_drive=template.values.peer_comparison_drive,
            ),
            "media": MediaAttributes(
                primary_social_platform=template.media.primary_social_platform,
                daily_social_media_hours=template.media.daily_social_media_hours,
                content_format_preference=template.media.content_format_preference,
                ad_receptivity=0.78 if adopter_like else 0.22,
                product_discovery_channel=template.media.product_discovery_channel,
                review_platform_trust=template.media.review_platform_trust,
                search_behavior=template.media.search_behavior,
                app_download_willingness=0.82 if adopter_like else 0.2,
                wallet_topup_comfort=template.media.wallet_topup_comfort,
                digital_payment_comfort=0.85 if adopter_like else 0.18,
            ),
        },
        deep=True,
    )


def _probing_population(template: Persona) -> Population:
    personas: list[Persona] = []
    sec_income_pairs = [("A1", 24.0), ("B1", 14.0), ("C1", 7.0)]
    tier_cities = [("Tier1", "Mumbai"), ("Tier2", "Indore"), ("Tier3", "Nashik")]
    for sec_index, (sec, income) in enumerate(sec_income_pairs):
        for tier_index, (tier, city) in enumerate(tier_cities):
            for repeat in range(4):
                adopter_like = (sec_index + tier_index + repeat) % 2 == 0
                personas.append(
                    _persona_variant(
                        template,
                        persona_id=f"{sec.lower()}-{tier.lower()}-{repeat}",
                        socioeconomic_class=sec,
                        city_tier=tier,
                        city_name=f"{city}-{repeat}",
                        income=income + repeat,
                        adopter_like=adopter_like,
                    )
                )

    return Population(
        id="probing-population",
        generation_params=GenerationParams(size=len(personas), seed=42, deep_persona_count=0),
        tier1_personas=personas,
        tier2_personas=[],
        validation_report=None,
        metadata=PopulationMetadata(
            generation_timestamp="2026-03-29T00:00:00Z",
            generation_duration_seconds=0.01,
            engine_version="test",
        ),
    )


def _prime_engine_outcomes(engine: ProbingTreeEngine) -> None:
    engine._outcomes = {}
    engine._decisions = {}
    for index, persona in enumerate(engine.population.tier1_personas):
        outcome = "adopt" if index % 2 == 0 else "reject"
        engine._outcomes[persona.id] = outcome
        engine._decisions[persona.id] = DecisionResult(
            persona_id=persona.id,
            need_score=0.82 if outcome == "adopt" else 0.21,
            awareness_score=0.8 if outcome == "adopt" else 0.32,
            consideration_score=0.78 if outcome == "adopt" else 0.28,
            purchase_score=0.76 if outcome == "adopt" else 0.22,
            outcome=outcome,
            rejection_stage=None if outcome == "adopt" else "purchase",
            rejection_reason=None if outcome == "adopt" else "price hesitation",
        )


def test_engine_runs_predefined_tree_mock(sample_persona: Persona, monkeypatch) -> None:
    """Full tree execution in mock mode completes without error."""

    monkeypatch.setattr(engine_module, "PROBE_SAMPLE_SIZE", 8)
    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    problem, hypotheses, probes = get_problem_tree("repeat_purchase_low")

    synthesis = engine.execute_tree(problem, hypotheses, probes)

    assert isinstance(synthesis, TreeSynthesis)
    assert synthesis.problem_id == problem.id
    assert synthesis.hypotheses_tested == len(hypotheses)
    assert synthesis.confidence_ranking
    assert 0.0 <= synthesis.overall_confidence <= 1.0


def test_engine_interview_probe_samples(sample_persona: Persona) -> None:
    """Interview probe uses sample_size, not full population."""

    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    _problem, _hypotheses, probes = get_problem_tree("repeat_purchase_low")
    probe = next(
        probe
        for probe in probes
        if probe.probe_type == ProbeType.INTERVIEW and probe.target_outcome is None
    )

    result = engine.execute_probe(probe)

    assert result.sample_size == 30
    assert result.population_size == len(population.tier1_personas)
    assert len(result.interview_responses) == 30


def test_engine_simulation_probe_full_population(sample_persona: Persona) -> None:
    """Simulation probe runs against all personas."""

    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    _problem, _hypotheses, probes = get_problem_tree("repeat_purchase_low")
    probe = next(probe for probe in probes if probe.probe_type == ProbeType.SIMULATION)

    result = engine.execute_probe(probe)

    assert result.sample_size == len(population.tier1_personas)
    assert result.baseline_metric is not None
    assert result.modified_metric is not None


def test_engine_attribute_probe_computes_splits(sample_persona: Persona) -> None:
    """Attribute probe produces AttributeSplit objects."""

    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    _problem, _hypotheses, probes = get_problem_tree("repeat_purchase_low")
    probe = next(probe for probe in probes if probe.probe_type == ProbeType.ATTRIBUTE)

    result = engine.execute_probe(probe)

    assert result.attribute_splits
    assert all(isinstance(split, AttributeSplit) for split in result.attribute_splits)


def test_engine_hypothesis_verdict_computed(sample_persona: Persona, monkeypatch) -> None:
    """After probes, hypothesis gets a verdict."""

    monkeypatch.setattr(engine_module, "PROBE_SAMPLE_SIZE", 6)
    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    problem, hypotheses, probes = get_problem_tree("repeat_purchase_low")
    for hypothesis in hypotheses[1:]:
        hypothesis.enabled = False

    engine.execute_tree(problem, hypotheses, probes)

    verdict = engine.verdicts[hypotheses[0].id]
    assert verdict.hypothesis_id == hypotheses[0].id
    assert verdict.status in {"confirmed", "partially_confirmed", "inconclusive", "rejected"}


def test_engine_disabled_hypothesis_skipped(sample_persona: Persona, monkeypatch) -> None:
    """Disabled hypotheses are not executed."""

    monkeypatch.setattr(engine_module, "PROBE_SAMPLE_SIZE", 6)
    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    problem, hypotheses, probes = get_problem_tree("repeat_purchase_low")
    hypotheses[1].enabled = False
    skipped_probe_ids = {probe.id for probe in probes if probe.hypothesis_id == hypotheses[1].id}

    synthesis = engine.execute_tree(problem, hypotheses, probes)

    assert hypotheses[1].id not in engine.verdicts
    assert hypotheses[1].id in synthesis.disabled_hypotheses
    assert all(probe.status == "pending" for probe in probes if probe.id in skipped_probe_ids)


def test_engine_tree_synthesis_ranking(sample_persona: Persona, monkeypatch) -> None:
    """Synthesis ranks hypotheses by confidence."""

    monkeypatch.setattr(engine_module, "PROBE_SAMPLE_SIZE", 6)
    population = _probing_population(sample_persona)
    engine = ProbingTreeEngine(population, "nutrimix_2_6", _mock_llm_client())
    _prime_engine_outcomes(engine)
    problem, hypotheses, probes = get_problem_tree("repeat_purchase_low")

    synthesis = engine.execute_tree(problem, hypotheses, probes)

    confidences = [confidence for _, confidence in synthesis.confidence_ranking]
    assert confidences == sorted(confidences, reverse=True)
    assert synthesis.dominant_hypothesis == synthesis.confidence_ranking[0][0]
