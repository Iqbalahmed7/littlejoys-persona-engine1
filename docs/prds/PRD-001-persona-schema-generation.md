# PRD-001: Persona Schema & Tier 1 Generation

> **Sprint**: 1
> **Priority**: P0 (Critical Path)
> **Assignees**: Codex (schema + distributions), Cursor (copula + conditional rules), Antigravity (validation)
> **Depends On**: PRD-000
> **Status**: Ready for Development
> **Estimated Effort**: 2 days

---

## Objective

Implement the complete persona data model (all 145 attributes from ARCHITECTURE.md §4.3) and the Tier 1 statistical generation engine that produces correlated, validated populations.

---

## Deliverables

### D1: Complete Pydantic Schema (Codex)

**File**: `src/taxonomy/schema.py`

Implement ALL models from ARCHITECTURE.md §5.1:

```python
# Top-level categories (12 total from taxonomy)
class DemographicAttributes(BaseModel): ...      # 1. Demographic Information
class HealthAttributes(BaseModel): ...           # 2. Physical and Health
class PsychologyAttributes(BaseModel): ...       # 3. Psychological and Cognitive
class CulturalAttributes(BaseModel): ...         # 4. Cultural and Social Context
class RelationshipAttributes(BaseModel): ...     # 5. Relationships and Social Networks
class CareerAttributes(BaseModel): ...           # 6. Career and Work Identity
class EducationAttributes(BaseModel): ...        # 7. Education and Learning
class LifestyleInterestAttributes(BaseModel): ...# 8. Hobbies, Interests, Lifestyle
class DailyRoutineAttributes(BaseModel): ...     # 9. Lifestyle and Daily Routine
class ValueAttributes(BaseModel): ...            # 10. Core Values, Beliefs, Philosophy
class EmotionalAttributes(BaseModel): ...        # 11. Emotional and Relational Skills
class MediaAttributes(BaseModel): ...            # 12. Media Consumption and Engagement

# Memory and state models
class MemoryEntry(BaseModel): ...
class BrandMemory(BaseModel): ...
class PurchaseEvent(BaseModel): ...
class TemporalState(BaseModel): ...

# Top-level persona
class Persona(BaseModel):
    id: str
    generation_seed: int
    generation_timestamp: str
    tier: Literal["statistical", "deep"]
    # All 12 category models
    demographics: DemographicAttributes
    health: HealthAttributes
    # ... etc
    # Tier 2 only
    narrative: str | None = None
    # Memory layer
    episodic_memory: list[MemoryEntry] = []
    semantic_memory: dict[str, Any] = {}
    brand_memories: dict[str, BrandMemory] = {}
    # State layer
    current_awareness: dict[str, float] = {}
    # ... etc
```

**Requirements**:
- Every attribute from ARCHITECTURE.md §4.3 taxonomy tree MUST be present
- All continuous attributes (0-1 scale) use `confloat(ge=0, le=1)`
- All categorical attributes use `Literal` types with exact enum values
- All list attributes typed with specific element types
- Custom validators for cross-field constraints (e.g., parent_age >= child_age + 18)
- `model_config = ConfigDict(frozen=True)` for identity fields (enforce immutability)
- `to_flat_dict()` method that flattens all nested attributes to a single-level dict (for copula generation)
- `from_flat_dict()` classmethod that reconstructs from flat dict

### D2: Demographic Distribution Tables (Codex)

**File**: `src/taxonomy/distributions.py`

Implement ALL distribution tables from ARCHITECTURE.md §5.3:

```python
class DistributionTables:
    """
    Real-world distributions for Indian urban parent demographics.
    Sources: Census 2021, NFHS-5, D2C market reports.
    All distributions are tier-conditional where applicable.
    """

    CITY_TIER: dict[str, float]
    HOUSEHOLD_INCOME: dict[str, DistributionParams]  # Tier-conditional lognormal
    PARENT_AGE: DistributionParams  # Truncated normal
    CHILD_AGE: DistributionParams   # Uniform 2-14
    NUM_CHILDREN: dict[int, float]
    EDUCATION_LEVEL: dict[str, dict[str, float]]  # Tier-conditional
    EMPLOYMENT_STATUS: dict[str, float]
    DIETARY_CULTURE: dict[str, dict[str, float]]  # Region-conditional
    JOINT_VS_NUCLEAR: dict[str, dict[str, float]]  # Tier-conditional
    MILK_SUPPLEMENT_CURRENT: dict[str, float]

    def sample_demographics(self, n: int, seed: int) -> pd.DataFrame:
        """Sample n rows of demographic attributes from distribution tables."""
        ...
```

**Requirements**:
- All distributions match ARCHITECTURE.md §5.3 exactly
- Sampling is seeded and deterministic
- Returns a DataFrame with one row per persona, columns = demographic attribute names
- Tier-conditional distributions are properly handled (sample tier first, then conditional on tier)

### D3: Gaussian Copula Generator (Cursor)

**File**: `src/taxonomy/correlations.py`

Implement the correlation enforcement engine:

```python
class GaussianCopulaGenerator:
    """
    Generates correlated continuous (0-1) attributes using a Gaussian copula.
    Enforces all correlation rules from ARCHITECTURE.md §5.2.
    """

    def __init__(self, correlation_rules: dict[tuple[str, str], float]):
        self.correlation_matrix = self._build_correlation_matrix(correlation_rules)
        ...

    def generate(
        self,
        n: int,
        demographics: pd.DataFrame,
        seed: int,
    ) -> pd.DataFrame:
        """
        Generate correlated psychographic attributes.

        Args:
            n: Number of personas
            demographics: Pre-sampled demographic attributes (used for conditional correlations)
            seed: Random seed

        Returns:
            DataFrame with all continuous (0-1) psychographic attributes, correlated per rules.
        """
        ...

    def _build_correlation_matrix(self, rules: dict) -> np.ndarray:
        """Build positive semi-definite correlation matrix from pairwise rules."""
        # Must ensure PSD (use nearest PSD approximation if needed)
        ...

    def _apply_demographic_conditioning(
        self, base_psychographics: pd.DataFrame, demographics: pd.DataFrame
    ) -> pd.DataFrame:
        """Shift psychographic distributions based on demographic values."""
        # E.g., Tier3 personas get authority_bias shifted up by 0.1
        ...
```

**Requirements**:
- All 50+ correlation rules from ARCHITECTURE.md §5.2 implemented
- Correlation matrix is always positive semi-definite (use `scipy.linalg.nearPD` if needed)
- Demographic-conditional rules applied AFTER base copula generation (as shifts)
- Output values always clipped to [0, 1]
- Seeded and deterministic
- Log the actual vs. target correlation matrix for validation

### D4: Conditional Distribution Rules (Cursor)

**File**: `src/taxonomy/correlations.py` (extend)

Implement CONDITIONAL_RULES from ARCHITECTURE.md §5.2:

```python
class ConditionalRuleEngine:
    """Applies non-linear conditional shifts after copula generation."""

    RULES: list[ConditionalRule]  # From ARCHITECTURE.md

    def apply(self, population: pd.DataFrame) -> pd.DataFrame:
        """Apply all conditional rules to shift attribute values."""
        ...
```

### D5: Persona Validation Framework (Antigravity)

**File**: `src/taxonomy/validation.py`

```python
class PersonaValidator:
    """
    Validates individual personas and populations against consistency rules.
    See ARCHITECTURE.md §6.3.
    """

    def validate_persona(self, persona: Persona) -> ValidationResult:
        """Check a single persona for logical consistency."""
        ...

    def validate_population(self, population: list[Persona]) -> PopulationValidationReport:
        """Check population-level distribution compliance."""
        ...

class ValidationResult(BaseModel):
    is_valid: bool
    hard_failures: list[str]    # Logical impossibilities → reject
    soft_warnings: list[str]    # Unlikely but possible → flag

class PopulationValidationReport(BaseModel):
    total_personas: int
    valid_count: int
    invalid_count: int
    distribution_checks: dict[str, DistributionCheckResult]
    correlation_checks: dict[str, CorrelationCheckResult]
    overall_pass: bool
```

**Requirements**:
- All validation rules from ARCHITECTURE.md §6.3 implemented
- Hard failures: child_age > parent_age - 18, attributes outside valid range, NaN/Inf
- Soft warnings: unusual but possible combinations (Tier3 + high digital comfort)
- Population checks: chi-square test for categorical distributions, KS test for continuous
- Correlation checks: actual vs target correlation, flag if deviation > 0.15
- Generate a human-readable report

---

## Acceptance Criteria

- [ ] All 145 attributes from ARCHITECTURE.md §4.3 present in Pydantic schema
- [ ] `Persona.model_validate(data)` works for a complete persona dict
- [ ] `generate_population(n=300, seed=42)` produces 300 valid Tier 1 personas
- [ ] Population distributions match targets (chi-square p > 0.05 for categoricals)
- [ ] Correlation matrix matches specification (all pairwise correlations within 0.15 of target)
- [ ] All conditional rules applied correctly (spot-check 5 rules manually)
- [ ] Deterministic: same seed → identical population
- [ ] No NaN, Inf, or out-of-range values in any persona
- [ ] Validation report generated and saved to `data/populations/validation_report.json`
- [ ] Unit tests pass for: schema validation, copula generation, conditional rules, population validation
- [ ] Test coverage >= 80% for all new code

---

## Test Plan

```
tests/unit/
  test_schema.py           # Schema validation, serialization, immutability
  test_distributions.py    # Demographic sampling correctness
  test_correlations.py     # Copula output, PSD matrix, correlation accuracy
  test_conditional.py      # Conditional rule application
  test_validation.py       # Persona + population validation
```

Key tests (from QA_AGENT_SPEC.md Suite 1):
- Determinism tests
- Distribution validation tests
- Correlation enforcement tests
- Edge case tests
- All validation rule tests

---

## Reference Documents

- ARCHITECTURE.md §4 (Taxonomy), §5 (Schema), §6 (Generation Engine)
- QA_AGENT_SPEC.md Suite 1 (Persona Generation Tests)
- DEVELOPMENT_PRACTICES.md (code standards)
