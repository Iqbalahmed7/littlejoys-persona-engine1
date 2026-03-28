# Cursor — Sprint 5 Briefing

**PRD**: PRD-012 Hardening, QA & Demo Prep
**Branch**: `feat/PRD-012-hardening`
**Priority**: P0

---

## Your Tasks

### 1. Fix `app/components/persona_card.py` (P0 — RUNTIME BUG)

The current file references fields that **do not exist** on the Persona schema. It will crash at runtime. Rewrite to use actual fields.

**Current broken references → Correct fields:**
| Broken | Correct |
|---|---|
| `persona.demographics.name` | `persona.id` |
| `persona.demographics.age` | `persona.demographics.parent_age` |
| `persona.demographics.location.city` | `persona.demographics.city_name` |
| `persona.financials.household_income_lpa` | `persona.demographics.household_income_lpa` |
| `persona.financials.work_environment` | `persona.career.employment_status` |
| `persona.psychology.social_proof_bias` | `persona.psychographics.social_proof_susceptibility` |
| `persona.psychology.perceived_time_scarcity` | `persona.psychographics.time_scarcity` |
| `persona.financials.deal_seeking_behavior` | `persona.psychographics.deal_seeking_tendency` |
| `decision_result.outcome` | `decision_result.get("outcome")` (it's a dict) |
| `decision_result.rejection_stage` | `decision_result.get("rejection_stage")` |
| `decision_result.rejection_reason` | `decision_result.get("rejection_reason")` |

**Reference the schema**: `src/taxonomy/schema.py` — classes `DemographicAttributes`, `PsychographicAttributes`, `CareerAttributes`, `Persona`.

**Updated card layout:**
```
Header: persona.id — persona.demographics.city_name (persona.demographics.city_tier)

Column 1 — Demographics:
- Income: household_income_lpa LPA
- Parent age: parent_age
- Children: num_children
- Region: region

Column 2 — Psychographics:
- Health consciousness: health_consciousness
- Brand loyalty: brand_loyalty_tendency
- Social proof: social_proof_susceptibility

Decision result (if provided):
- Use dict .get() — decision_result is a dict, not a model
```

### 2. Fix component wrappers
Review `app/components/funnel_chart.py` and `app/components/heatmap.py`. Ensure they correctly delegate to `src/utils/viz.create_funnel_chart` and `src/utils/viz.create_segment_heatmap`. Fix any signature mismatches.

### 3. Error state consistency (P1)
Audit all 6 pages in `app/pages/`. Every page that requires `st.session_state.population` should:
- Check for it at the top
- Show `st.warning("Load or generate a population from the home page first.")` + `st.stop()`
- Pages 1, 3 already do this. Verify pages 2, 4, 5, 6 have equivalent guards.

### 4. Tests
**File**: `tests/unit/test_persona_card.py` (new)

Test `render_persona_card()` by mocking `streamlit` and passing a real Persona object + decision dict. Verify no `AttributeError` is raised.

---

## Standards
- `from __future__ import annotations`
- Use `persona.to_flat_dict()` as reference for available fields if unsure
- No `print()` — use `structlog` if logging needed
- Target: persona_card fix + 3 tests

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check app/components/ app/pages/
```
