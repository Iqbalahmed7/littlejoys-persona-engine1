# PRD-013: Persona Depth & UX Overhaul

**Sprint**: 6
**Status**: Draft
**Goal**: Make every persona feel real — human-readable IDs with Indian names, LLM-generated backstories for all personas, polished attribute presentation, and insight-driven visualizations.

---

## 1. Human-Readable Persona IDs with Indian Names (P0)

### 1.1 Indian name pool
Create `src/generation/names.py` with:
- 100 female Indian first names (Priya, Ananya, Meera, Kavita, Sunita, Deepa, Asha, Ritu, Neha, Pooja, etc.)
- 100 male Indian first names (Rahul, Amit, Vikram, Suresh, Rajesh, Arun, Kiran, Sanjay, etc.)
- Selection is deterministic: `names[hash(seed, index) % len(names)]`

### 1.2 ID format
Replace `9d8c8c3e467ee4782a53adf3b61a2ba7-t1-00042` with:
```
Priya-Mumbai-Mom-32
Vikram-Pune-Dad-38
```
Format: `{FirstName}-{CityName}-{Mom|Dad}-{ParentAge}`

If duplicates occur (two Priyas in Mumbai), append a digit: `Priya-Mumbai-Mom-32-2`

### 1.3 Schema changes
Add to `Persona`:
```python
display_name: str | None = None  # "Priya Sharma"
```
The `id` field becomes the human-readable slug. The old hash-based ID is no longer needed.

### 1.4 Where to change
- `src/generation/population.py`: ID generation in `generate()` method (lines 289, 322)
- `src/generation/names.py`: New file with name pools
- `src/taxonomy/schema.py`: Add `display_name` field to Persona

---

## 2. Narratives for All Personas (P0)

### 2.1 Wire `Tier2NarrativeGenerator` into population pipeline
`src/generation/tier2_generator.py` already has the full narrative generation pipeline (anchor inference → life stories → narrative synthesis). It's never called.

**Change `PopulationGenerator.generate()`** to:
1. Generate all 200 personas as before (statistical attributes)
2. Run `Tier2NarrativeGenerator.generate_narrative()` on **every** persona
3. In mock mode: use the existing `_generate_mock_narrative()` template (lines 245-306)
4. Remove the Tier 1/Tier 2 split — all personas get `tier="deep"`

### 2.2 Improve mock narrative quality
The current mock template in `_generate_mock_narrative()` is decent but needs:
- Reference the persona's generated Indian name naturally
- Vary sentence structure using seed-based randomization (not the same template for all 200)
- Include the persona's anchor traits (top 5 psychographic extremes) as character details
- 3-4 paragraph format: background → daily life → parenting approach → health/nutrition attitudes

### 2.3 Remove Tier language from UI
- `app/pages/1_population.py`: Remove "Tier 1 (statistical)" / "Tier 2 (deep)" labels. Show "Population Size" and "Deep Personas with Narratives" or just the total.
- `app/pages/5_interviews.py`: Remove `tier2_personas` filter — all personas are interviewable
- `app/streamlit_app.py`: Update metrics

---

## 3. Attribute Display Layer (P0)

### 3.1 Display name mapping
Create `src/utils/display.py` with:

```python
ATTRIBUTE_DISPLAY_NAMES: dict[str, str] = {
    "household_income_lpa": "Household Income (₹ Lakhs/year)",
    "budget_consciousness": "Price Sensitivity",
    "social_proof_susceptibility": "Peer Influence",
    "health_anxiety": "Health Worry Level",
    "diet_consciousness": "Dietary Awareness",
    "brand_loyalty_tendency": "Brand Loyalty",
    "city_tier": "City Classification",
    "socioeconomic_class": "SEC Class (NCCS)",
    "parent_age": "Parent's Age",
    "num_children": "Number of Children",
    "employment_status": "Work Status",
    "family_structure": "Family Type",
    ...  # all 92 continuous + key categorical attributes
}
```

### 3.2 SEC class explanations
```python
SEC_DESCRIPTIONS: dict[str, str] = {
    "A1": "Urban Affluent — highest disposable income, premium brand affinity",
    "A2": "Upper Middle — professional households, quality-conscious spending",
    "B1": "Middle Class — stable salaried, value-for-money seekers",
    "B2": "Lower Middle — budget-conscious, need-based purchasing",
    "C1": "Economy — price-driven, essential spending focus",
    "C2": "Value Segment — bare essentials, highly price-sensitive",
}
```

### 3.3 Utility function
```python
def display_name(field: str) -> str:
    """Convert raw field name to human-readable label."""
    return ATTRIBUTE_DISPLAY_NAMES.get(field, field.replace("_", " ").title())
```

Apply this function in:
- Population page axis labels and legends
- Persona card field names
- Interview responses (replace raw field references)
- Report sections
- Barrier distribution labels
- Variable importance chart labels

---

## 4. Insight-Driven Psychographic Scatter (P1)

### 4.1 Quadrant annotations
When simulation results exist (adopt/reject colors visible):
- Divide scatter into 4 quadrants at median X and median Y
- Annotate each quadrant with adoption rate: "Adoption: 62%" / "Adoption: 18%"
- Add a text insight below the chart: "Parents with high {X} and high {Y} adopt at {ratio}× the overall rate"

### 4.2 When no simulation results
Show a clear message: "Run a simulation from the Home page to see how these attributes relate to adoption decisions."

### 4.3 Attribute grouping
Add a selectbox "Attribute Category" above the X/Y selectors:
- Health & Nutrition (9 attrs)
- Psychology & Decision-Making (18 attrs)
- Cultural & Social (5 attrs)
- Values & Beliefs (9 attrs)
- Media & Digital (4 attrs)
- Lifestyle & Routine (8 attrs)

This makes it easier to explore meaningfully rather than scrolling through 92 raw options.

---

## 5. Interview Mock Response Cleanup (P1)

### 5.1 Natural language translation
Replace raw attribute references in `src/analysis/interviews.py` mock builder:

**Before**: "my budget_consciousness sitting around 0.74"
**After**: "I'm quite careful about what we spend"

Create a mapping in `src/utils/display.py`:
```python
def describe_attribute_value(field: str, value: float) -> str:
    """Natural language description of a 0-1 attribute value."""
    if value >= 0.8: return f"very high {display_name(field).lower()}"
    if value >= 0.6: return f"fairly strong {display_name(field).lower()}"
    if value >= 0.4: return f"moderate {display_name(field).lower()}"
    if value >= 0.2: return f"somewhat low {display_name(field).lower()}"
    return f"low {display_name(field).lower()}"
```

### 5.2 Use persona name in responses
Replace "As a parent in {city}" with "As {display_name}, a {age}-year-old {Mom/Dad} in {city}..."

---

## Engineer Assignments

| Task | Engineer | Priority | Key Files |
|---|---|---|---|
| 2.1-2.3 Narrative pipeline + remove tier language | Codex | P0 | `population.py`, `tier2_generator.py`, page files |
| 1.1-1.4 Indian names + persona ID format | OpenCode | P0 | `names.py` (new), `population.py`, `schema.py` |
| 3.1-3.3 Display name mapping + SEC explanations | Cursor | P0 | `display.py` (new), `1_population.py`, `persona_card.py` |
| 4.1-4.3 Scatter insights + 5.1-5.2 Interview cleanup | Antigravity | P1 | `1_population.py`, `interviews.py`, `display.py` |

**Dependency**: OpenCode's name generation (Task 1) must complete before Codex's narrative pipeline (Task 2) can reference names. Cursor's display mapping (Task 3) must complete before Antigravity's interview cleanup (Task 5) can use `describe_attribute_value()`.

**Recommended send order**: OpenCode + Cursor first (parallel). Then Codex + Antigravity (parallel, after first pair completes).

---

## Acceptance Criteria
- Every persona has a human-readable ID like `Priya-Mumbai-Mom-32`
- Every persona has a 3-4 paragraph narrative (mock mode)
- No raw field names visible anywhere in the UI (no underscores)
- SEC classes have explanatory tooltips
- Psychographic scatter shows quadrant adoption rates when simulation results exist
- Interview mock responses use natural language, not raw attribute values
- All tests pass, ruff clean
