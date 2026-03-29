# Sprint 12 Brief — Codex (GPT 5.3 Medium)
## Business Question Bank + Research Run Orchestrator

### Context
We are rebuilding LittleJoys as a hybrid research engine. Each scenario needs 3-4 business questions that drive the research. The ResearchRunner orchestrates the full hybrid flow: funnel → smart sample → LLM interviews → alternative scenarios. This sprint builds both the question bank and the orchestrator.

### Task 1: Business Question Bank
**New file:** `src/probing/question_bank.py`

#### Model

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class BusinessQuestion(BaseModel):
    """A scenario-specific research question that drives the probing tree."""
    model_config = ConfigDict(extra="forbid")

    id: str
    scenario_id: str
    title: str                    # Short question, e.g. "How can we improve repeat purchase?"
    description: str              # 2-3 sentence business context
    probing_tree_id: str | None   # Maps to predefined tree ID, None if no tree yet
    success_metric: str           # e.g. "repeat_rate", "trial_openness", "barrier_reduction"
    tags: list[str] = Field(default_factory=list)  # e.g. ["retention", "pricing"]
```

#### Questions to Create

For each of the 4 scenarios, create 3-4 business questions. Map to existing probing trees where they exist.

**Existing probing trees** (in `src/probing/predefined_trees.py`):
- `repeat_purchase_low` → scenario `nutrimix_2_6`
- `nutrimix_7_14_expansion` → scenario `nutrimix_7_14`
- `magnesium_gummies_growth` → scenario `magnesium_gummies`
- `protein_mix_launch` → scenario `protein_mix`

**nutrimix_2_6** (Nutrimix toddler nutrition powder, ages 2-6, ₹599):
1. "How can we improve repeat purchase for NutriMix?" → tree: `repeat_purchase_low`
2. "What drives first-time trial among health-anxious parents?" → tree: None (create lightweight)
3. "How effective is the LJ Pass in building purchase habits?" → tree: None
4. "Which parent segments show highest untapped potential?" → tree: None

**nutrimix_7_14** (Nutrimix 7+, school-age expansion, ₹649):
1. "Can the NutriMix brand extend credibly to older children?" → tree: `nutrimix_7_14_expansion`
2. "What role do school partnerships play in building trust?" → tree: None
3. "How do taste preferences differ between age groups?" → tree: None

**magnesium_gummies** (Calm Gummies, ages 4-12, ₹499):
1. "What drives initial trial for a new gummy supplement?" → tree: `magnesium_gummies_growth`
2. "How important is pediatrician endorsement vs peer recommendation?" → tree: None
3. "Which parent concerns does this product address most effectively?" → tree: None

**protein_mix** (ProteinMix, ages 6-14, ₹799):
1. "What are the primary barriers to protein supplement adoption?" → tree: `protein_mix_launch`
2. "How does the higher price point affect consideration?" → tree: None
3. "Does sports club partnership move the needle for active families?" → tree: None

For questions with `probing_tree_id=None`, create lightweight `ProblemTreeDefinition` objects with 2-3 hypotheses and 2-3 probes each. Follow the pattern in `src/probing/predefined_trees.py`. Use the helper functions `_interview_probe()`, `_simulation_probe()`, `_attribute_probe()` from that module.

#### API Functions

```python
def get_questions_for_scenario(scenario_id: str) -> list[BusinessQuestion]:
    """Return all business questions for a scenario."""

def get_question(question_id: str) -> BusinessQuestion:
    """Return a single question by ID. Raises KeyError if not found."""

def list_all_questions() -> list[BusinessQuestion]:
    """Return all questions across all scenarios."""
```

### Task 2: Research Run Orchestrator
**New file:** `src/simulation/research_runner.py`

This is the core orchestrator that coordinates the full Option C hybrid research run.

#### Models

```python
from __future__ import annotations
from typing import Any, Callable
from pydantic import BaseModel, Field
from src.simulation.static import StaticSimulationResult
from src.probing.smart_sample import SmartSample, SampledPersona

class AlternativeRunSummary(BaseModel):
    """Summary of one alternative scenario run (funnel-only)."""
    variant_id: str
    parameter_changes: dict[str, Any]     # what was tweaked
    business_rationale: str               # plain English explanation
    adoption_count: int
    adoption_rate: float
    delta_vs_primary: float               # e.g. +0.08 means 8pp better

class ResearchMetadata(BaseModel):
    """Metadata about the research run."""
    timestamp: str
    duration_seconds: float
    scenario_id: str
    question_id: str
    population_size: int
    sample_size: int
    alternative_count: int
    llm_calls_made: int
    estimated_cost_usd: float
    mock_mode: bool

class InterviewResult(BaseModel):
    """One persona's interview responses."""
    persona_id: str
    persona_name: str
    selection_reason: str
    responses: list[dict[str, str]]  # [{question: ..., answer: ...}]

class ResearchResult(BaseModel):
    """Complete output of a hybrid research run."""
    primary_funnel: StaticSimulationResult
    smart_sample: SmartSample
    interview_results: list[InterviewResult]
    alternative_runs: list[AlternativeRunSummary]
    metadata: ResearchMetadata
```

#### Orchestrator

```python
class ResearchRunner:
    """Orchestrates the full hybrid research flow."""

    def __init__(
        self,
        population: Population,
        scenario: ScenarioConfig,
        question: BusinessQuestion,
        llm_client: LLMClient,
        *,
        mock_mode: bool = True,
        alternative_count: int = 50,
        sample_size: int = 18,
        seed: int = 42,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> None:
        ...

    def run(self) -> ResearchResult:
        """Execute the full research pipeline."""
        # Step 1: Run static funnel on all personas
        #   - Use run_static_simulation() from src.simulation.static
        #   - Call progress_callback("Running decision pathway on all personas...", 0.1)

        # Step 2: Smart sample selection
        #   - Use select_smart_sample() from src.probing.smart_sample
        #   - Call progress_callback("Selecting personas for deep interviews...", 0.2)

        # Step 3: LLM interviews on sampled personas
        #   - For each sampled persona, load the probing tree for the question
        #   - Use PersonaInterviewer from src.analysis.interviews to ask questions
        #   - Get the probes of type INTERVIEW from the probing tree
        #   - For each interview probe, ask the question_template to the persona
        #   - Collect responses into InterviewResult objects
        #   - Call progress_callback("Interviewing persona {name}...", 0.2 + i/n * 0.5)
        #   - If mock_mode: PersonaInterviewer handles mock responses internally

        # Step 4: Generate alternative scenario variants
        #   - Use generate_smart_variants() from src.simulation.explorer
        #   - Generate `alternative_count` variants
        #   - Call progress_callback("Generating alternative scenarios...", 0.75)

        # Step 5: Run funnel-only on all alternatives
        #   - For each variant, run run_static_simulation()
        #   - Compare adoption_rate to primary run
        #   - Build AlternativeRunSummary with delta and business_rationale
        #   - Call progress_callback("Evaluating alternatives...", 0.75 + i/n * 0.2)

        # Step 6: Assemble ResearchResult
        #   - Call progress_callback("Compiling results...", 0.98)
        #   - Return complete ResearchResult
```

#### Important Implementation Details

1. **PersonaInterviewer usage** (see `src/analysis/interviews.py`):
   ```python
   interviewer = PersonaInterviewer(llm_client)
   # To ask a question:
   response = await interviewer.ask(persona, question_text, context={...})
   # Returns a string response
   ```
   Since `ask()` is async, you'll need the `_run_async()` pattern used in `src/probing/engine.py`.

2. **Probing tree loading** (see `src/probing/predefined_trees.py`):
   ```python
   from src.probing.predefined_trees import get_problem_tree
   problem, hypotheses, probes = get_problem_tree(tree_id)
   interview_probes = [p for p in probes if p.probe_type == ProbeType.INTERVIEW and p.status != "disabled"]
   ```

3. **Variant generation** (see `src/simulation/explorer.py`):
   ```python
   from src.simulation.explorer import generate_variants, VariantStrategy
   variants = generate_variants(scenario, count=50, strategy=VariantStrategy.SMART)
   ```

4. **Progress callback signature:** `callback(message: str, progress: float)` where progress is 0.0-1.0.

5. **Error handling:** If LLM interviews fail for a persona, log the error and continue with remaining personas. Don't abort the entire run.

6. **Mock mode:** When `mock_mode=True`, the PersonaInterviewer will return mock responses automatically. The ResearchRunner doesn't need special mock handling — just pass the llm_client configured for mock.

### Deliverables
1. `src/probing/question_bank.py` — BusinessQuestion model, 13 questions across 4 scenarios, lightweight probing trees for new questions
2. `src/simulation/research_runner.py` — ResearchRunner class, ResearchResult model, full orchestration pipeline
3. Both files must be importable without errors

### Do NOT
- Modify existing files (this sprint is additive only)
- Create Streamlit pages or UI components
- Change the funnel engine or calibration model
- Add dependencies beyond what's in pyproject.toml
