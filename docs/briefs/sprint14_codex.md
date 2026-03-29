# Sprint 14 Brief — Codex (GPT 5.3 Medium)
## Research Results Consolidator

### Context
Sprint 13 built the Research Design page where users run a hybrid pipeline (funnel + interviews + alternatives). The `ResearchResult` object now has all the raw data. Sprint 14 needs a backend module that **consolidates** this raw data into a structured summary ready for the Results page to render — no Streamlit code, just pure data transformation.

### Task: Build `src/analysis/research_consolidator.py`
**New file.** Transforms a `ResearchResult` into a `ConsolidatedReport` that the Results page can render directly.

#### Models

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from src.simulation.research_runner import ResearchResult, AlternativeRunSummary


class FunnelSummary(BaseModel):
    """Quantitative overview of the primary funnel run."""
    model_config = ConfigDict(extra="forbid")

    population_size: int
    adoption_count: int
    adoption_rate: float
    rejection_distribution: dict[str, int]   # stage → count
    top_barriers: list[dict[str, str | int]]  # [{stage, reason, count}] top 5
    waterfall_data: dict[str, int]           # stage → cumulative pass count


class SegmentInsight(BaseModel):
    """One segment's adoption insight."""
    model_config = ConfigDict(extra="forbid")

    segment_name: str
    segment_value: str
    adoption_rate: float
    persona_count: int
    delta_vs_population: float  # +/- vs overall adoption rate


class QualitativeCluster(BaseModel):
    """One theme from interview clustering."""
    model_config = ConfigDict(extra="forbid")

    theme: str
    description: str
    persona_count: int
    percentage: float
    representative_quotes: list[str]
    dominant_attributes: dict[str, float]


class AlternativeInsight(BaseModel):
    """Top alternative scenario with business context."""
    model_config = ConfigDict(extra="forbid")

    rank: int
    variant_id: str
    business_rationale: str
    adoption_rate: float
    delta_vs_primary: float
    parameter_changes: dict[str, object]


class ConsolidatedReport(BaseModel):
    """Complete consolidated research report ready for rendering."""
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    question_title: str
    question_description: str

    # Quantitative
    funnel: FunnelSummary
    segments_by_tier: list[SegmentInsight]
    segments_by_income: list[SegmentInsight]
    causal_drivers: list[dict[str, object]]  # [{variable, importance, direction}]

    # Qualitative
    interview_count: int
    clusters: list[QualitativeCluster]

    # Alternatives
    top_alternatives: list[AlternativeInsight]  # Top 10 by delta
    worst_alternatives: list[AlternativeInsight]  # Bottom 3 by delta

    # Metadata
    mock_mode: bool
    duration_seconds: float
    llm_calls_made: int
    estimated_cost_usd: float
```

#### Consolidator Function

```python
def consolidate_research(
    result: ResearchResult,
    population: Population,
) -> ConsolidatedReport:
    """Transform raw ResearchResult into a structured report."""
```

#### Implementation Steps

1. **Funnel summary**: Extract from `result.primary_funnel`:
   - `adoption_count`, `adoption_rate`, `rejection_distribution` directly
   - Call `compute_funnel_waterfall(result.primary_funnel.results_by_persona)` for waterfall data
   - Call `analyze_barriers(result.primary_funnel.results_by_persona)` → take top 5

2. **Segment insights**: Merge persona attributes with results (same pattern as `3_results.py` lines 71-76):
   ```python
   merged = {}
   for pid, row in result.primary_funnel.results_by_persona.items():
       merged[pid] = {**population.get_persona(pid).to_flat_dict(), **row}
   ```
   Then call `analyze_segments(merged, group_by="city_tier")` and `analyze_segments(merged, group_by="income_bracket")`. Convert each to `SegmentInsight` with `delta_vs_population = segment.adoption_rate - overall_rate`.

3. **Causal drivers**: Call `compute_variable_importance(merged)` → convert top 8 to dicts with `{variable, importance, direction}`.

4. **Qualitative clustering**: Build `(persona, response_text)` pairs from `result.interview_results`:
   ```python
   responses = []
   for ir in result.interview_results:
       persona = population.get_persona(ir.persona_id)
       combined_text = " ".join(r["answer"] for r in ir.responses)
       responses.append((persona, combined_text))
   ```
   Call `cluster_responses_mock(responses)` → convert to `QualitativeCluster` list.

5. **Alternative insights**: `result.alternative_runs` is already sorted by delta descending. Take top 10 and bottom 3:
   ```python
   top_alternatives = [AlternativeInsight(rank=i+1, ...) for i, alt in enumerate(alts[:10])]
   worst_alternatives = [AlternativeInsight(rank=i+1, ...) for i, alt in enumerate(alts[-3:])]
   ```

6. **Metadata**: Copy from `result.metadata`.

7. **Question context**: Retrieve from `result.metadata.question_id`:
   ```python
   from src.probing.question_bank import get_question
   question = get_question(result.metadata.question_id)
   ```

### Imports You'll Need
```python
from src.analysis.barriers import analyze_barriers
from src.analysis.causal import compute_variable_importance
from src.analysis.segments import analyze_segments
from src.analysis.waterfall import compute_funnel_waterfall
from src.probing.clustering import cluster_responses_mock
from src.probing.question_bank import get_question
from src.decision.scenarios import get_scenario
from src.simulation.research_runner import ResearchResult
from src.generation.population import Population
```

### Deliverables
1. `src/analysis/research_consolidator.py` — models + `consolidate_research()` function
2. Must be importable without errors
3. Quick self-test: running against a mock `ResearchResult` should produce a valid `ConsolidatedReport`

### Do NOT
- Modify existing files
- Create Streamlit pages
- Add dependencies
- Make LLM calls
