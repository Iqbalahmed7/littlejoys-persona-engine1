# PRD-003: Population Generator & Tier 2 Narratives

> **Sprint**: 1
> **Priority**: P0 (Critical Path)
> **Assignees**: Cursor (population orchestrator + validation report), Codex (Tier 2 narrative generation)
> **Depends On**: PRD-001 (schema + copula), PRD-000 (LLM wrapper)
> **Status**: Ready for Development
> **Estimated Effort**: 1 day

---

## Objective

Build the population orchestrator that combines demographic sampling, copula-based psychographic generation, categorical assignment, and validation into a single pipeline. Also implement Tier 2 deep narrative generation using progressive LLM attribute sampling.

---

## Deliverables

### D1: Population Orchestrator (Cursor)

**File**: `src/generation/population.py`

```python
class PopulationGenerator:
    """
    Orchestrates end-to-end population generation.
    Pipeline: Demographics → Psychographics (copula) → Categoricals → Validation → Serialize
    """

    def generate(
        self,
        size: int = 300,
        seed: int = 42,
        deep_persona_count: int = 30,
        target_filters: dict | None = None,  # e.g., {"child_age": [7, 14]}
    ) -> Population:
        """
        Generate a complete population with Tier 1 + Tier 2 personas.

        Steps:
        1. Sample demographics from distribution tables
        2. Generate correlated psychographics via Gaussian copula
        3. Apply conditional distribution rules
        4. Assign categorical behavioral attributes
        5. Validate each persona
        6. Regenerate any that fail hard validation
        7. Select top-N diverse personas for Tier 2 upgrade
        8. Generate Tier 2 narratives (async, LLM)
        9. Validate population-level distributions
        10. Serialize and save

        Returns:
            Population object with all personas + validation report
        """
        ...

    def _assign_categoricals(
        self, demographics: pd.DataFrame, psychographics: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Assign categorical attributes conditioned on demographics + psychographics.
        E.g., primary_shopping_platform conditioned on city_tier + online_preference.
        """
        ...

    def _select_for_tier2(
        self, personas: list[Persona], count: int
    ) -> list[Persona]:
        """
        Select diverse subset for Tier 2 enrichment.
        Strategy: maximize demographic + psychographic coverage.
        Use k-medoids clustering on the attribute space, pick medoids.
        """
        ...


class Population(BaseModel):
    """Container for a generated population."""
    id: str
    generation_params: GenerationParams
    tier1_personas: list[Persona]
    tier2_personas: list[Persona]
    validation_report: PopulationValidationReport
    metadata: PopulationMetadata

    def get_persona(self, persona_id: str) -> Persona: ...
    def filter(self, **kwargs) -> list[Persona]: ...
    def to_dataframe(self) -> pd.DataFrame: ...
    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> "Population": ...
```

**Requirements**:
- End-to-end pipeline: single call produces a complete validated population
- Deterministic with seed
- Filter support for target demographics (e.g., only parents of 7-14 year olds)
- Tier 2 selection maximizes diversity (not random)
- Saves to `data/populations/{population_id}/`
- Population serialization: Tier 1 as Parquet (fast columnar queries), Tier 2 as individual JSON files
- Logs progress via structlog

### D2: Tier 2 Narrative Generator (Codex)

**File**: `src/generation/tier2_generator.py`

Following DeepPersona's progressive attribute sampling:

```python
class Tier2NarrativeGenerator:
    """
    Generates biographical narratives for Tier 2 personas using progressive
    LLM attribute sampling (DeepPersona approach).

    Pipeline:
    1. Anchor: Fix core demographics + top 5 psychographics
    2. Values: LLM infers core values from anchors
    3. Life Attitude: LLM expands values into life attitude
    4. Personal Story: LLM generates 1-3 life story snippets
    5. Interests & Habits: LLM derives from story + demographics
    6. Detailed Preferences: LLM fills in granular preferences
    7. Full Narrative: LLM synthesizes everything into coherent biography
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate_narrative(self, persona: Persona) -> Persona:
        """
        Enrich a Tier 1 persona with a deep narrative.
        Returns a new Persona with tier="deep" and narrative filled.
        """
        ...

    async def generate_batch(
        self, personas: list[Persona], max_concurrency: int = 5
    ) -> list[Persona]:
        """Generate narratives for multiple personas with concurrency control."""
        ...
```

**Prompt Design** (Codex to implement):

Step 1 — Anchor Prompt:
```
You are creating a detailed biographical profile for a synthetic person.
Here are their core attributes:
{demographics + psychographics as structured data}

Based on these attributes, infer:
1. Their core personal values (3-5 values)
2. Their life attitude / worldview (2-3 sentences)
3. Their primary motivations as a parent

Output as JSON.
```

Step 2 — Life Story Prompt:
```
Given this person's profile and values:
{anchor attributes + inferred values}

Generate 2-3 specific life story snippets that shaped who they are today.
These should be concrete, specific events — not generic.
They should be consistent with their demographics and values.
Include at least one story related to their parenting journey.

Output as JSON array of story objects.
```

Step 3 — Full Narrative Prompt:
```
You are writing a first-person biographical narrative for this person:
{all attributes + values + stories}

Write a 300-500 word narrative in third person that:
- Naturally incorporates their demographics, values, and life stories
- Describes their daily routine and parenting approach
- Mentions their relationship with health/nutrition for their children
- Includes specific details (not generic filler)
- Feels like a real person, not a marketing persona
- Uses natural language (Hindi-English code-mixing if appropriate for the persona)

Do NOT list attributes. Weave them into a flowing narrative.
```

**Requirements**:
- Narrative must reference at least 10 specific persona attributes
- Narrative must be coherent with ALL numerical attributes (no contradictions)
- Each narrative is unique — no template phrases shared across personas
- Use Claude Sonnet for cost efficiency (not Opus)
- Cache all generated narratives
- Validate narrative consistency with attributes (automated check)

### D3: Population Validation Report (Cursor)

**File**: `src/generation/population.py` (extend)

Generate a comprehensive validation report saved as JSON:

```python
class PopulationValidationReport(BaseModel):
    timestamp: str
    population_size: int
    seed: int
    tier1_count: int
    tier2_count: int

    # Distribution checks
    distribution_checks: dict[str, DistributionCheckResult]
    # e.g., {"city_tier": {target: {T1: 0.45, T2: 0.35, T3: 0.20},
    #                       actual: {T1: 0.43, T2: 0.37, T3: 0.20},
    #                       p_value: 0.87, pass: True}}

    # Correlation checks
    correlation_checks: dict[str, CorrelationCheckResult]
    # e.g., {"income_vs_budget_consciousness": {target: -0.55, actual: -0.52, pass: True}}

    # Hard validation failures
    invalid_personas_regenerated: int
    hard_failure_types: dict[str, int]  # e.g., {"child_older_than_parent": 3}

    # Soft warnings
    soft_warnings: list[str]

    overall_pass: bool
```

---

## Acceptance Criteria

- [ ] `PopulationGenerator.generate(size=300, seed=42)` runs in < 2 minutes (Tier 1 only)
- [ ] Tier 2 generation (30 personas) runs in < 10 minutes
- [ ] All 300 Tier 1 personas pass hard validation
- [ ] Population distributions match targets (all chi-square p > 0.05)
- [ ] At least 40 of 50 correlation checks pass (within 0.15 of target)
- [ ] 30 Tier 2 narratives are generated, each referencing 10+ persona attributes
- [ ] Tier 2 narratives are unique (pairwise similarity < 0.7)
- [ ] Population serialized to disk and loadable
- [ ] Same seed always produces identical Tier 1 population
- [ ] Unit tests for: orchestrator pipeline, categorical assignment, Tier 2 selection, narrative consistency

---

## Reference Documents

- ARCHITECTURE.md §6 (Persona Generation Engine)
- DeepPersona paper §3.2 (Progressive Attribute Sampling)
- QA_AGENT_SPEC.md Suite 1 (Persona Generation Tests)
