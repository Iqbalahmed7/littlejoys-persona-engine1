# Codex — Sprint 6 Briefing

**PRD**: PRD-013 Persona Depth & UX Overhaul
**Branch**: `feat/PRD-013-persona-depth`
**Priority**: P0 — **WAVE 2** (send after OpenCode completes — depends on name generation)

---

## Your Task: Wire Narrative Generation for All Personas

### 1. Update `src/generation/population.py`

**Goal**: Every persona gets a narrative, not just 10 Tier 2 personas.

In `PopulationGenerator.generate()`:

**After** all personas are created (line ~290-310 area), add narrative generation:

```python
from src.generation.tier2_generator import Tier2NarrativeGenerator

# Generate narratives for ALL personas
narrative_generator = Tier2NarrativeGenerator(llm_client)
for persona in tier1_personas:
    enriched = _run_async(narrative_generator.generate_narrative(persona))
    # Update persona with narrative and semantic_memory
    persona = persona.model_copy(update={
        "narrative": enriched.narrative,
        "semantic_memory": enriched.semantic_memory,
        "tier": "deep",
    })
```

**Key decisions:**
- The `PopulationGenerator` currently doesn't take an LLM client. Add an optional `llm_client` parameter to `generate()`. When `None`, create a mock LLM client.
- Set `tier="deep"` for ALL personas — remove the Tier 1/Tier 2 distinction.
- Remove the separate `tier2_personas` list generation (lines 316-327). ALL personas go into `tier1_personas` with `tier="deep"`.
- Keep `tier2_personas` as an empty list for backwards compatibility, or alias it to `tier1_personas`.

### 2. Improve mock narrative templates in `src/generation/tier2_generator.py`

The current `_generate_mock_narrative()` (lines 245-306) generates the same structure for all personas. Improve it:

**A. Use persona's `display_name` field** (set by OpenCode's name generator):
```python
name = persona.display_name or persona.id
```
Reference the name naturally: "Priya is a 32-year-old mother of two..."

**B. Add variety** using seed-based template selection:
Create 4-5 narrative opening templates and select based on `hash(persona.id) % 5`:
- Template A: Starts with daily routine ("Every morning at 6 AM, {name} begins...")
- Template B: Starts with background ("Growing up in {region}, {name} always...")
- Template C: Starts with parenting philosophy ("{name} believes that...")
- Template D: Starts with a turning point ("When {name}'s {child_age}-year-old...")
- Template E: Starts with community context ("In {city_name}'s {urban/periurban} neighborhoods...")

**C. Weave in anchor traits naturally:**
The top 5 psychographic extremes should appear as character details, not raw numbers:
- `health_anxiety=0.85` → "She worries constantly about whether her children are getting the right nutrition"
- `budget_consciousness=0.72` → "Every purchase goes through a mental cost-benefit analysis"
- `social_proof_bias=0.90` → "She trusts recommendations from other parents in her WhatsApp groups more than any advertisement"

Use `src/utils/display.py`'s `describe_attribute_value()` function (from Cursor's delivery) if available, or create an inline version.

**D. Include 3-4 paragraphs:**
1. Background (city, family, work)
2. Daily life and routines (breakfast, shopping, digital habits)
3. Parenting approach and health attitudes
4. Purchase decision style

### 3. Update Tier references across UI pages

Replace all Tier 1/Tier 2 distinctions:

**`app/pages/5_interviews.py`** (line 118):
```python
# BEFORE:
persona_pool = population.tier2_personas if population.tier2_personas else population.tier1_personas

# AFTER:
persona_pool = population.tier1_personas
```

**`app/streamlit_app.py`** (lines 58-61):
```python
# BEFORE:
c1.metric("Tier 1 (Statistical) Personas", len(pop.tier1_personas))
c2.metric("Tier 2 (Deep) Personas", len(pop.tier2_personas))

# AFTER:
c1.metric("Total Personas", len(pop.tier1_personas))
c2.metric("With Narratives", sum(1 for p in pop.tier1_personas if p.narrative))
```

**`app/pages/1_population.py`**: Cursor will handle this page — just ensure your changes to `population.py` don't break the page's expectations.

### 4. Handle LLM client plumbing

`PopulationGenerator.generate()` currently has no LLM dependency. Add it cleanly:

```python
def generate(
    self,
    *,
    size: int = DEFAULT_POPULATION_SIZE,
    seed: int = DEFAULT_SEED,
    deep_persona_count: int = DEFAULT_DEEP_PERSONA_COUNT,
    llm_client: LLMClient | None = None,
) -> Population:
```

When `llm_client is None`, create a default mock client:
```python
if llm_client is None:
    from src.config import Config
    from src.utils.llm import LLMClient
    llm_client = LLMClient(Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key=""))
```

### 5. Tests

**File**: `tests/unit/test_narrative_generation.py` (new)

```python
def test_all_personas_get_narratives():
    """Population generation produces narratives for every persona."""
    pop = PopulationGenerator().generate(size=10, seed=42)
    for persona in pop.tier1_personas:
        assert persona.narrative is not None
        assert len(persona.narrative) > 50

def test_narrative_references_persona_name():
    """Mock narrative includes the persona's display name."""
    pop = PopulationGenerator().generate(size=5, seed=42)
    for persona in pop.tier1_personas:
        if persona.display_name:
            assert persona.display_name in persona.narrative

def test_narrative_variety():
    """Different personas get different narrative openings."""
    pop = PopulationGenerator().generate(size=10, seed=42)
    openings = {p.narrative[:50] for p in pop.tier1_personas}
    assert len(openings) > 1  # Not all identical

def test_all_personas_are_deep():
    """All personas have tier='deep'."""
    pop = PopulationGenerator().generate(size=10, seed=42)
    for persona in pop.tier1_personas:
        assert persona.tier == "deep"
```

---

## Standards
- `from __future__ import annotations`
- `structlog` for logging
- Constants from `src.constants`
- Mock narratives must NEVER include raw field names or decimal values like "0.74"
- Narratives should read like a real person's backstory
- Target: 4+ new tests

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check src/generation/
```
