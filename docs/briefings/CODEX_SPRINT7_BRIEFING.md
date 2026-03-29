# Codex — Sprint 7 Briefing

**PRD**: PRD-014 Probing Tree System
**Branch**: `feat/PRD-014-probing-tree`
**Priority**: P0 — Core feature delivery

---

## Your Task: Build the Probing Tree Models, Engine, and Mock Mode

You are implementing the backend for the Probing Tree system — the intelligence layer that decomposes business problems into testable hypotheses, runs structured investigations across personas, and synthesises findings with confidence scores.

**Design doc**: `docs/designs/PROBING-TREE-SYSTEM-DESIGN.md` — read this FIRST. It has the full data model, confidence formulas, sampling strategy, and engine architecture.

---

### 1. Create `src/probing/models.py`

All Pydantic v2 models. Use `ConfigDict(extra="forbid")` on every model.

```python
"""Data models for the Probing Tree system."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Any


class ProbeType(str, Enum):
    INTERVIEW = "interview"
    SIMULATION = "simulation"
    ATTRIBUTE = "attribute"


class ProblemStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str                                    # "repeat_purchase_low"
    title: str                                 # "Why is repeat purchase low despite high NPS?"
    scenario_id: str                           # "nutrimix_2_6"
    context: str                               # Business context paragraph
    success_metric: str                        # "repeat_rate" or "adoption_rate"
    target_population_filter: dict[str, Any] = {}


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str                                    # "h1_price_memory"
    problem_id: str
    title: str
    rationale: str
    indicator_attributes: list[str]
    counterfactual_modifications: dict[str, Any] | None = None
    enabled: bool = True
    order: int = 0


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str                                    # "h1_p1_price_pause"
    hypothesis_id: str
    probe_type: ProbeType
    order: int = 0

    # INTERVIEW
    question_template: str | None = None
    target_outcome: str | None = None          # "reject" or "adopt" or None for all
    follow_up_questions: list[str] = []

    # SIMULATION
    scenario_modifications: dict[str, Any] | None = None
    comparison_metric: str | None = None

    # ATTRIBUTE
    analysis_attributes: list[str] = []
    split_by: str | None = None

    # State
    status: str = "pending"                    # "pending" | "running" | "complete"
    result: ProbeResult | None = None


class ResponseCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str                                 # "price_re_evaluation"
    description: str
    persona_count: int
    percentage: float
    representative_quotes: list[str]
    dominant_attributes: dict[str, float] = {}


class AttributeSplit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute: str
    adopter_mean: float
    rejector_mean: float
    effect_size: float                         # Cohen's d
    significant: bool


class ProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probe_id: str
    confidence: float                          # 0.0 to 1.0
    evidence_summary: str
    sample_size: int
    population_size: int | None = None         # For "30/200 sampled" display
    clustering_method: str | None = None       # "keyword" or "semantic"

    # INTERVIEW
    response_clusters: list[ResponseCluster] = []

    # SIMULATION
    baseline_metric: float | None = None
    modified_metric: float | None = None
    lift: float | None = None

    # ATTRIBUTE
    attribute_splits: list[AttributeSplit] = []


class HypothesisVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    confidence: float
    status: str                                # "confirmed" | "partially_confirmed" | "rejected" | "inconclusive"
    evidence_summary: str
    key_persona_segments: list[str] = []
    recommended_actions: list[str] = []
    consistency_score: float = 0.0


class TreeSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    hypotheses_tested: int
    hypotheses_confirmed: int
    dominant_hypothesis: str
    confidence_ranking: list[tuple[str, float]]
    synthesis_narrative: str
    recommended_actions: list[str]
    overall_confidence: float
    disabled_hypotheses: list[str] = []
    confidence_impact_of_disabled: float = 0.0
    total_cost_estimate: float = 0.0           # Estimated $ cost of the run
```

**Important**: `Probe.result` references `ProbeResult` — use `model_rebuild()` or forward reference to handle circular dependency.

---

### 2. Create `src/probing/confidence.py`

All confidence computation functions. Copy the formulas EXACTLY from the design doc.

```python
"""Confidence computation for probing tree results."""

from __future__ import annotations


def compute_interview_confidence(clusters: list[ResponseCluster]) -> float:
    """Confidence = dominant cluster % × attribute coherence."""
    if not clusters:
        return 0.0
    dominant = max(clusters, key=lambda c: c.percentage)
    dominance = dominant.percentage
    coherence = _attribute_coherence(dominant)
    return dominance * 0.6 + coherence * 0.4


def _attribute_coherence(cluster: ResponseCluster) -> float:
    """How tightly cluster members share attribute patterns.

    For mock: check if dominant_attributes have low variance (all > 0.5 = coherent).
    Returns 0.0-1.0.
    """
    if not cluster.dominant_attributes:
        return 0.5  # Neutral when no attribute data
    values = list(cluster.dominant_attributes.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return max(0.0, 1.0 - variance * 4)


def compute_simulation_confidence(baseline: float, modified: float, sample_size: int) -> float:
    """Confidence = lift magnitude × sample significance."""
    lift = abs(modified - baseline)
    significance = min(1.0, sample_size / 100)
    return min(1.0, lift * 3.0) * significance


def compute_attribute_confidence(splits: list[AttributeSplit]) -> float:
    """Confidence = effect size coverage × mean effect magnitude."""
    if not splits:
        return 0.0
    significant_splits = [s for s in splits if s.significant]
    coverage = len(significant_splits) / len(splits)
    mean_effect = (
        sum(abs(s.effect_size) for s in significant_splits) / len(significant_splits)
        if significant_splits else 0.0
    )
    return coverage * 0.5 + min(1.0, mean_effect) * 0.5


def compute_hypothesis_confidence(probe_confidences: list[float]) -> tuple[float, float]:
    """Returns (final_confidence, consistency_score)."""
    if not probe_confidences:
        return 0.0, 0.0
    mean_c = sum(probe_confidences) / len(probe_confidences)
    variance = sum((c - mean_c) ** 2 for c in probe_confidences) / len(probe_confidences)
    consistency = max(0.0, 1.0 - variance * 4)
    final = mean_c * 0.8 + consistency * 0.2
    return final, consistency


def classify_hypothesis(confidence: float) -> str:
    """Map confidence to verdict status."""
    if confidence >= 0.70:
        return "confirmed"
    if confidence >= 0.50:
        return "partially_confirmed"
    if confidence >= 0.30:
        return "inconclusive"
    return "rejected"
```

---

### 3. Create `src/probing/sampling.py`

Stratified persona sampling for interview probes.

```python
"""Stratified sampling for probing tree interview probes."""

from __future__ import annotations

import hashlib
from src.taxonomy.schema import Persona

PROBE_SAMPLE_SIZE = 30
PROBE_STRATIFY_BY = ["socioeconomic_class", "city_tier"]


def sample_personas_for_probe(
    personas: list[Persona],
    outcomes: dict[str, str],
    target_outcome: str | None = None,
    sample_size: int = PROBE_SAMPLE_SIZE,
    seed: int = 42,
) -> list[Persona]:
    """Stratified sample ensuring SEC and city_tier representation.

    Args:
        personas: Full persona pool.
        outcomes: Mapping of persona_id -> "adopt"/"reject".
        target_outcome: If set, only sample from this outcome group.
        sample_size: Target sample size.
        seed: Deterministic seed.

    Returns:
        Sampled list of personas.
    """
    pool = personas
    if target_outcome:
        pool = [p for p in personas if outcomes.get(p.id) == target_outcome]

    if len(pool) <= sample_size:
        return list(pool)

    # Build strata: group by SEC × city_tier
    strata: dict[str, list[Persona]] = {}
    for p in pool:
        flat = p.to_flat_dict()
        key = f"{flat.get('socioeconomic_class', 'unknown')}_{flat.get('city_tier', 'unknown')}"
        strata.setdefault(key, []).append(p)

    # Proportional allocation
    sampled: list[Persona] = []
    for stratum_key, stratum_personas in strata.items():
        proportion = len(stratum_personas) / len(pool)
        n = max(1, round(proportion * sample_size))
        # Deterministic selection using hash
        sorted_personas = sorted(
            stratum_personas,
            key=lambda p: hashlib.md5(f"{seed}_{p.id}".encode()).hexdigest(),
        )
        sampled.extend(sorted_personas[:n])

    # Trim to exact sample_size if overallocated
    if len(sampled) > sample_size:
        sampled = sorted(
            sampled,
            key=lambda p: hashlib.md5(f"{seed}_trim_{p.id}".encode()).hexdigest(),
        )[:sample_size]

    return sampled
```

---

### 4. Create `src/probing/clustering.py`

Mock keyword clustering for POC. Real LLM clustering is a future enhancement.

```python
"""Response clustering for interview probes."""

from __future__ import annotations

from src.probing.models import ResponseCluster
from src.taxonomy.schema import Persona


# Keyword groups for mock clustering
CLUSTER_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "price_sensitivity": {
        "keywords": ["price", "cost", "expensive", "afford", "worth", "budget", "₹", "money", "spend"],
        "description": "Concerns about price or value for money",
    },
    "forgetfulness": {
        "keywords": ["forgot", "busy", "remind", "remember", "slipped", "routine", "hectic"],
        "description": "Product exited working memory amid busy schedules",
    },
    "taste_decline": {
        "keywords": ["taste", "refused", "didn't like", "boring", "same", "flavour", "enjoy"],
        "description": "Child's taste preferences or fatigue with the product",
    },
    "trust_concern": {
        "keywords": ["trust", "safe", "doctor", "pediatrician", "natural", "chemical", "ingredient"],
        "description": "Safety and trust concerns about the product",
    },
    "alternatives": {
        "keywords": ["switched", "horlicks", "homemade", "another", "alternative", "pediasure", "bournvita"],
        "description": "Switched to or considering competitor products",
    },
    "convenience": {
        "keywords": ["easy", "convenient", "time", "prepare", "cook", "mix", "effort", "morning"],
        "description": "Convenience and effort required to use the product",
    },
    "positive_experience": {
        "keywords": ["love", "great", "happy", "enjoy", "continue", "reorder", "subscribe", "regular"],
        "description": "Positive experience driving continued use",
    },
}


def cluster_responses_mock(
    responses: list[tuple[Persona, str]],
) -> list[ResponseCluster]:
    """Cluster responses using keyword matching (mock mode).

    Args:
        responses: List of (persona, response_text) tuples.

    Returns:
        List of ResponseCluster objects, sorted by persona_count descending.
    """
    if not responses:
        return []

    # Assign each response to best-matching cluster
    assignments: dict[str, list[tuple[Persona, str]]] = {}

    for persona, text in responses:
        text_lower = text.lower()
        best_cluster = "other"
        best_score = 0

        for cluster_id, cluster_def in CLUSTER_KEYWORDS.items():
            score = sum(1 for kw in cluster_def["keywords"] if kw in text_lower)
            if score > best_score:
                best_score = score
                best_cluster = cluster_id

        assignments.setdefault(best_cluster, []).append((persona, text))

    # Build ResponseCluster objects
    total = len(responses)
    clusters: list[ResponseCluster] = []

    for cluster_id, members in assignments.items():
        if cluster_id == "other" and len(members) < 2:
            continue  # Skip tiny "other" cluster

        # Pick representative quotes (up to 3)
        quotes = [text[:200] for _, text in members[:3]]

        # Compute dominant attributes from cluster members
        dominant_attrs: dict[str, float] = {}
        if members:
            flat_dicts = [p.to_flat_dict() for p, _ in members]
            # Find attributes with high mean values across cluster
            sample_keys = [
                k for k in flat_dicts[0]
                if isinstance(flat_dicts[0].get(k), (int, float))
                and not k.startswith("_")
                and k not in ("parent_age", "num_children", "household_income_lpa")
            ]
            for key in sample_keys[:20]:  # Limit to avoid huge dicts
                vals = [d[key] for d in flat_dicts if key in d and isinstance(d[key], (int, float))]
                if vals:
                    mean_val = sum(vals) / len(vals)
                    if mean_val > 0.6 or mean_val < 0.3:  # Only notable attributes
                        dominant_attrs[key] = round(mean_val, 2)

        description = CLUSTER_KEYWORDS.get(cluster_id, {}).get(
            "description", "Responses that did not match a specific theme"
        )

        clusters.append(ResponseCluster(
            theme=cluster_id,
            description=description,
            persona_count=len(members),
            percentage=round(len(members) / total, 3),
            representative_quotes=quotes,
            dominant_attributes=dominant_attrs,
        ))

    # Sort by count descending
    clusters.sort(key=lambda c: c.persona_count, reverse=True)
    return clusters
```

---

### 5. Create `src/probing/predefined_trees.py`

Define all 4 problem trees from the design doc. This is data, not logic.

```python
"""Predefined probing trees for the 4 LittleJoys business scenarios."""

from __future__ import annotations

from src.probing.models import Hypothesis, Probe, ProbeType, ProblemStatement


def get_problem_tree(problem_id: str) -> tuple[ProblemStatement, list[Hypothesis], list[Probe]]:
    """Return (problem, hypotheses, probes) for a predefined problem tree.

    Raises KeyError if problem_id is unknown.
    """
    catalog = _build_catalog()
    if problem_id not in catalog:
        raise KeyError(f"Unknown problem tree: {problem_id}. Available: {list(catalog.keys())}")
    return catalog[problem_id]


def list_problem_ids() -> list[str]:
    """Return all available problem tree IDs."""
    return list(_build_catalog().keys())


def _build_catalog() -> dict[str, tuple[ProblemStatement, list[Hypothesis], list[Probe]]]:
    return {
        "repeat_purchase_low": _tree_repeat_purchase(),
        "nutrimix_7_14_expansion": _tree_nutrimix_7_14(),
        "magnesium_gummies_growth": _tree_magnesium_gummies(),
        "protein_mix_launch": _tree_protein_mix(),
    }
```

**Then implement each `_tree_*()` function** translating the YAML in the design doc into Python objects. Example for Problem 1:

```python
def _tree_repeat_purchase() -> tuple[ProblemStatement, list[Hypothesis], list[Probe]]:
    problem = ProblemStatement(
        id="repeat_purchase_low",
        title="Why is repeat purchase low despite high NPS?",
        scenario_id="nutrimix_2_6",
        context=(
            "LittleJoys Nutrimix has strong first-purchase adoption and high customer "
            "satisfaction scores. But month-over-month repeat rates are below target. "
            "Something breaks between 'I liked it' and 'I bought it again.'"
        ),
        success_metric="repeat_rate",
    )

    h1 = Hypothesis(
        id="h1_price_reeval",
        problem_id="repeat_purchase_low",
        title="Price feels different on repeat vs. first purchase",
        rationale=(
            "First purchase is driven by curiosity and emotional appeal. Second "
            "purchase faces rational cost-benefit re-evaluation against alternatives."
        ),
        indicator_attributes=["budget_consciousness", "price_reference_point", "deal_seeking_intensity", "value_perception_driver"],
        order=1,
    )
    # ... h2, h3, h4 ...

    probes = [
        Probe(
            id="h1_p1_pause_reason",
            hypothesis_id="h1_price_reeval",
            probe_type=ProbeType.INTERVIEW,
            question_template="After finishing the first pack, what made you hesitate before reordering?",
            target_outcome="reject",
            order=1,
        ),
        Probe(
            id="h1_p2_price_comparison",
            hypothesis_id="h1_price_reeval",
            probe_type=ProbeType.INTERVIEW,
            question_template="Did you compare the price to alternatives before your second purchase?",
            order=2,
        ),
        Probe(
            id="h1_p3_price_cut_sim",
            hypothesis_id="h1_price_reeval",
            probe_type=ProbeType.SIMULATION,
            scenario_modifications={"product.price_inr": 479},
            comparison_metric="repeat_rate",
            order=3,
        ),
        Probe(
            id="h1_p4_budget_split",
            hypothesis_id="h1_price_reeval",
            probe_type=ProbeType.ATTRIBUTE,
            analysis_attributes=["budget_consciousness", "deal_seeking_intensity", "price_reference_point"],
            split_by="repeat_status",
            order=4,
        ),
        # ... probes for h2, h3, h4
    ]

    return problem, [h1, h2, h3, h4], probes
```

**Do this for ALL 4 trees.** Every hypothesis and every probe from the design doc's YAML must be translated. Don't skip any.

---

### 6. Create `src/probing/engine.py`

The orchestrator. Key design decisions:

```python
"""Probing tree execution engine."""

from __future__ import annotations

import structlog
from src.analysis.interviews import PersonaInterviewer
from src.decision.funnel import run_funnel
from src.decision.scenarios import get_scenario
from src.probing.clustering import cluster_responses_mock
from src.probing.confidence import (
    classify_hypothesis,
    compute_attribute_confidence,
    compute_hypothesis_confidence,
    compute_interview_confidence,
    compute_simulation_confidence,
)
from src.probing.models import (
    AttributeSplit,
    Hypothesis,
    HypothesisVerdict,
    Probe,
    ProbeResult,
    ProbeType,
    ProblemStatement,
    TreeSynthesis,
)
from src.probing.sampling import sample_personas_for_probe
from src.taxonomy.schema import Persona

log = structlog.get_logger()
```

**The engine class must:**

1. Accept `population`, `scenario_id`, and `llm_client` in `__init__`
2. Pre-compute funnel outcomes for ALL personas once in `__init__` and cache in `self._outcomes: dict[str, str]`
3. `execute_tree(problem, hypotheses, probes)` → runs all probes for enabled hypotheses, returns `TreeSynthesis`
4. `execute_probe(probe)` → dispatches to `_run_interview_probe`, `_run_simulation_probe`, `_run_attribute_probe`
5. Interview probes use `sample_personas_for_probe()` with `PROBE_SAMPLE_SIZE=30`
6. Interview probes call `self.interviewer.interview()` for each sampled persona (use `_run_async` helper since `interview()` is async)
7. Interview probes cluster responses using `cluster_responses_mock()` (mock mode for POC)
8. Simulation probes import and call `run_counterfactual()` with `probe.scenario_modifications`
9. Attribute probes use `persona.to_flat_dict()` and compute `AttributeSplit` for each attribute
10. After all probes complete, compute `HypothesisVerdict` for each hypothesis
11. After all verdicts, compute `TreeSynthesis`

**Key interfaces you'll call:**

```python
# Interview (async)
from src.analysis.interviews import PersonaInterviewer
interviewer = PersonaInterviewer(llm_client)
turn = await interviewer.interview(
    persona=persona,
    question=probe.question_template,
    scenario_id=self.scenario.id,
    decision_result=decision.to_dict(),   # DecisionResult.to_dict()
)
# turn.content is the response string

# Counterfactual
from src.simulation.counterfactual import run_counterfactual
result = run_counterfactual(
    population=self.population,
    baseline_scenario=self.scenario,
    modifications=probe.scenario_modifications,
    counterfactual_name=probe.id,
    seed=42,
)
# result.baseline_adoption_rate, result.counterfactual_adoption_rate, result.absolute_lift

# Funnel
from src.decision.funnel import run_funnel
decision = run_funnel(persona, self.scenario)
# decision.outcome is "adopt" or "reject"
# decision.to_dict() returns full dict

# Async helper (already exists in codebase)
import asyncio
def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)
```

---

### 7. Create `src/probing/__init__.py`

```python
"""Probing Tree System — hypothesis-driven investigation of synthetic personas."""

from src.probing.engine import ProbingTreeEngine
from src.probing.models import (
    AttributeSplit,
    Hypothesis,
    HypothesisVerdict,
    Probe,
    ProbeResult,
    ProbeType,
    ProblemStatement,
    ResponseCluster,
    TreeSynthesis,
)
from src.probing.predefined_trees import get_problem_tree, list_problem_ids

__all__ = [
    "AttributeSplit",
    "Hypothesis",
    "HypothesisVerdict",
    "Probe",
    "ProbeResult",
    "ProbeType",
    "ProblemStatement",
    "ProbingTreeEngine",
    "ResponseCluster",
    "TreeSynthesis",
    "get_problem_tree",
    "list_problem_ids",
]
```

---

### 8. Tests

Create these test files:

**`tests/unit/test_probing_models.py`**

```python
def test_problem_statement_creation():
    """ProblemStatement with all required fields."""

def test_hypothesis_enabled_by_default():
    """New hypothesis is enabled."""

def test_probe_types_enum():
    """All 3 probe types exist."""

def test_probe_result_with_clusters():
    """ProbeResult accepts interview cluster data."""

def test_probe_result_with_splits():
    """ProbeResult accepts attribute split data."""

def test_tree_synthesis_creation():
    """TreeSynthesis with full data."""

def test_extra_fields_forbidden():
    """Models reject unknown fields."""
```

**`tests/unit/test_probing_confidence.py`**

```python
def test_interview_confidence_single_dominant_cluster():
    """High confidence when one cluster dominates."""

def test_interview_confidence_no_clusters():
    """Zero confidence when no clusters."""

def test_interview_confidence_even_split():
    """Lower confidence when clusters are evenly split."""

def test_simulation_confidence_large_lift():
    """High confidence with large lift and sufficient sample."""

def test_simulation_confidence_zero_lift():
    """Zero confidence when no lift."""

def test_attribute_confidence_all_significant():
    """High confidence when all splits significant."""

def test_attribute_confidence_none_significant():
    """Low confidence when no splits significant."""

def test_hypothesis_confidence_consistent_probes():
    """High consistency bonus when probes agree."""

def test_hypothesis_confidence_inconsistent_probes():
    """Low consistency when probes disagree."""

def test_classify_hypothesis_thresholds():
    """Correct status for each confidence range."""
```

**`tests/unit/test_probing_sampling.py`**

```python
def test_sample_size_respected():
    """Returns exactly sample_size personas when pool is larger."""

def test_sample_smaller_pool_returns_all():
    """Returns full pool when pool < sample_size."""

def test_sample_target_outcome_filters():
    """Only returns personas matching target outcome."""

def test_sample_is_deterministic():
    """Same seed produces same sample."""

def test_sample_covers_strata():
    """Sample includes personas from multiple SEC classes."""
```

**`tests/unit/test_probing_engine.py`**

```python
def test_engine_runs_predefined_tree_mock():
    """Full tree execution in mock mode completes without error."""
    # Use get_problem_tree("repeat_purchase_low")
    # Create engine with mock LLM client
    # Execute tree
    # Assert TreeSynthesis is returned with valid fields

def test_engine_interview_probe_samples():
    """Interview probe uses sample_size, not full population."""

def test_engine_simulation_probe_full_population():
    """Simulation probe runs against all personas."""

def test_engine_attribute_probe_computes_splits():
    """Attribute probe produces AttributeSplit objects."""

def test_engine_hypothesis_verdict_computed():
    """After probes, hypothesis gets a verdict."""

def test_engine_disabled_hypothesis_skipped():
    """Disabled hypotheses are not executed."""

def test_engine_tree_synthesis_ranking():
    """Synthesis ranks hypotheses by confidence."""
```

**`tests/unit/test_probing_clustering.py`**

```python
def test_mock_clustering_price_keywords():
    """Response mentioning price clusters into price_sensitivity."""

def test_mock_clustering_multiple_themes():
    """Multiple distinct responses produce multiple clusters."""

def test_mock_clustering_empty_responses():
    """Empty response list returns empty clusters."""

def test_mock_clustering_percentages_sum_to_one():
    """Cluster percentages sum to approximately 1.0."""
```

Target: **25+ tests total**, all passing.

---

### 9. File Structure Summary

```
src/probing/
    __init__.py
    models.py              # ~120 lines
    confidence.py          # ~70 lines
    sampling.py            # ~60 lines
    clustering.py          # ~100 lines
    predefined_trees.py    # ~300 lines (4 trees, all probes)
    engine.py              # ~200 lines

tests/unit/
    test_probing_models.py
    test_probing_confidence.py
    test_probing_sampling.py
    test_probing_engine.py
    test_probing_clustering.py
```

---

## Standards

- `from __future__ import annotations` in every file
- `structlog` for logging
- Constants from `src.constants` where applicable
- `ConfigDict(extra="forbid")` on every Pydantic model
- No raw field names in any evidence_summary or synthesis text — use `display_name()` from `src.utils.display`
- All async code must be callable from sync context (use `_run_async` helper pattern)
- Deterministic: same seed → same results

## Run

```bash
uv run pytest tests/unit/test_probing_*.py -x -q -v
uv run ruff check src/probing/
uv run pytest tests/ -x -q  # Full suite must still pass
```
