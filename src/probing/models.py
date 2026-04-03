"""Data models for the Probing Tree system."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProbeType(StrEnum):
    """Supported probe execution modes."""

    INTERVIEW = "interview"
    SIMULATION = "simulation"
    ATTRIBUTE = "attribute"
    ATTRIBUTE_ANALYSIS = "attribute"


class ProblemStatement(BaseModel):
    """A business question that the probing tree investigates."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    scenario_id: str
    context: str
    success_metric: str
    target_population_filter: dict[str, Any] = Field(default_factory=dict)


class Hypothesis(BaseModel):
    """One testable explanation for a problem statement.

    Supports 5-WHY tree depth via ``why_level`` and ``parent_hypothesis_id``.
    Each hypothesis carries a Bayesian ``confidence_prior`` (0.0–1.0) that
    represents how likely this driver is before probing, plus a
    ``real_world_analogy`` anchoring it to known Indian FMCG market evidence.
    ``cohort_filter`` restricts probe execution to a specific slice of the
    population (e.g. lapsed buyers, middle-income tier, specific age band).
    ``edge_case`` flags low-probability but strategically important hypotheses.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    problem_id: str
    title: str
    rationale: str
    signals: list[str] = Field(default_factory=list)
    indicator_attributes: list[str]
    counterfactual_modifications: dict[str, Any] | None = None

    # ── Sprint 1a additions ────────────────────────────────────────────────
    confidence_prior: float = Field(default=0.5, ge=0.0, le=1.0)
    """Bayesian prior: 0.0 = very unlikely driver, 1.0 = almost certainly a driver."""

    real_world_analogy: str = ""
    """Grounding reference from Indian FMCG market data.
    E.g. 'Horlicks North India: price sensitivity doubled on reorder vs trial (IRI 2019)'."""

    why_level: int = Field(default=1, ge=1, le=5)
    """5-WHY depth: 1 = top-level WHY, 2 = sub-WHY, 3 = sub-sub-WHY."""

    parent_hypothesis_id: str | None = None
    """Links to the parent hypothesis ID for sub-WHY tree structure."""

    cohort_filter: dict[str, Any] = Field(default_factory=dict)
    """Restrict probe to a population slice.
    E.g. {'outcome': 'lapsed'} or {'tier': ['tier1']} or {'child_age_band': '7-10'}."""

    edge_case: bool = False
    """True if this is a low-probability but strategically important hypothesis."""
    # ── End Sprint 1a additions ────────────────────────────────────────────

    is_custom: bool = False
    enabled: bool = True
    order: int = 0


class Probe(BaseModel):
    """A single investigation step within a hypothesis."""

    model_config = ConfigDict(extra="forbid")

    id: str
    hypothesis_id: str
    probe_type: ProbeType
    order: int = 0

    question_template: str | None = None
    target_outcome: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list)

    scenario_modifications: dict[str, Any] | None = None
    comparison_metric: str | None = None

    analysis_attributes: list[str] = Field(default_factory=list)
    split_by: str | None = None

    status: str = "pending"
    result: ProbeResult | None = None


class InterviewResponse(BaseModel):
    """One persona-level response captured during an interview probe."""

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    persona_name: str
    outcome: str
    content: str


class ResponseCluster(BaseModel):
    """A thematic cluster of interview responses."""

    model_config = ConfigDict(extra="forbid")

    theme: str
    description: str
    persona_count: int
    percentage: float
    representative_quotes: list[str] = Field(default_factory=list)
    dominant_attributes: dict[str, float] = Field(default_factory=dict)


class AttributeSplit(BaseModel):
    """Statistical comparison of an attribute between adopters and rejectors."""

    model_config = ConfigDict(extra="forbid")

    attribute: str
    adopter_mean: float
    rejector_mean: float
    effect_size: float
    significant: bool


class ProbeResult(BaseModel):
    """Result of executing a single probe."""

    model_config = ConfigDict(extra="forbid")

    probe_id: str
    confidence: float
    evidence_summary: str
    sample_size: int
    population_size: int | None = None
    clustering_method: str | None = None

    interview_responses: list[InterviewResponse] = Field(default_factory=list)
    response_clusters: list[ResponseCluster] = Field(default_factory=list)

    baseline_metric: float | None = None
    modified_metric: float | None = None
    lift: float | None = None

    attribute_splits: list[AttributeSplit] = Field(default_factory=list)


class HypothesisVerdict(BaseModel):
    """Synthesized conclusion for one hypothesis."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    confidence: float
    status: str
    evidence_summary: str
    key_persona_segments: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    consistency_score: float = 0.0


class TreeSynthesis(BaseModel):
    """Final synthesis across all hypotheses for a problem statement."""

    model_config = ConfigDict(extra="forbid")

    problem_id: str
    hypotheses_tested: int
    hypotheses_confirmed: int
    dominant_hypothesis: str
    confidence_ranking: list[tuple[str, float]]
    synthesis_narrative: str
    recommended_actions: list[str]
    overall_confidence: float
    disabled_hypotheses: list[str] = Field(default_factory=list)
    confidence_impact_of_disabled: float = 0.0
    total_cost_estimate: float = 0.0


class ProblemTreeDefinition(BaseModel):
    """Serializable definition of a predefined probing tree."""

    model_config = ConfigDict(extra="forbid")

    problem: ProblemStatement
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    probes: list[Probe] = Field(default_factory=list)


class TreeExecutionSnapshot(BaseModel):
    """Minimal persistence payload for saving a probing-tree run."""

    model_config = ConfigDict(extra="forbid")

    problem: ProblemStatement
    hypothesis_verdicts: list[HypothesisVerdict] = Field(default_factory=list)
    completed_probe_ids: list[str] = Field(default_factory=list)
    synthesis: TreeSynthesis | None = None


Probe.model_rebuild()
ProblemTreeDefinition.model_rebuild()
TreeExecutionSnapshot.model_rebuild()
