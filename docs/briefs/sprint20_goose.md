# Sprint 20 Brief — Goose
## Persona CSV Export

### Context

The Personas page (`app/pages/1_personas.py`) lets users browse and filter personas, but there's no way to download them. Add a CSV export button that respects the active filters.

### Task: Add CSV Export to Personas Page

In `app/pages/1_personas.py`, after the persona browser section, add a download button:

```python
import csv
import io

# After the persona cards section (wherever filtered_personas is computed):

if filtered_personas:
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=[
        "persona_id", "city_tier", "income_bracket", "education_level",
        "family_structure", "youngest_child_age", "employment_status",
        "health_anxiety", "nutrition_gap_awareness", "budget_consciousness",
        "social_proof_bias", "risk_tolerance", "ad_receptivity",
        "brand_loyalty_tendency", "child_taste_veto_power",
        "science_literacy", "medical_authority_trust",
        "narrative_summary",
    ])
    writer.writeheader()

    for persona in filtered_personas:
        flat = persona.to_flat_dict()
        row = {
            "persona_id": persona.id,
            "city_tier": flat.get("city_tier", ""),
            "income_bracket": _income_bracket(flat),
            "education_level": flat.get("education_level", ""),
            "family_structure": flat.get("family_structure", ""),
            "youngest_child_age": flat.get("youngest_child_age", ""),
            "employment_status": flat.get("employment_status", ""),
            "health_anxiety": flat.get("health_anxiety", ""),
            "nutrition_gap_awareness": flat.get("nutrition_gap_awareness", ""),
            "budget_consciousness": flat.get("budget_consciousness", ""),
            "social_proof_bias": flat.get("social_proof_bias", ""),
            "risk_tolerance": flat.get("risk_tolerance", ""),
            "ad_receptivity": flat.get("ad_receptivity", ""),
            "brand_loyalty_tendency": flat.get("brand_loyalty_tendency", ""),
            "child_taste_veto_power": flat.get("child_taste_veto_power", ""),
            "science_literacy": flat.get("science_literacy", ""),
            "medical_authority_trust": flat.get("medical_authority_trust", ""),
            "narrative_summary": (persona.narrative or "")[:200],
        }
        writer.writerow(row)

    st.download_button(
        "Export Filtered Personas (CSV)",
        data=csv_buffer.getvalue(),
        file_name="littlejoys_personas.csv",
        mime="text/csv",
    )
```

### Helper function

If `_income_bracket` doesn't exist in the personas page, add it:

```python
def _income_bracket(flat: dict) -> str:
    income = flat.get("household_income_lpa", 0)
    if not isinstance(income, (int, float)):
        return "unknown"
    if income <= 8.0:
        return "low_income"
    if income <= 15.0:
        return "middle_income"
    return "high_income"
```

### Placement

Put the download button:
- After the filter section and persona count display
- Before the individual persona cards
- So users see: Filters → "Showing N personas" → [Export CSV button] → Persona cards

### Files to Modify
- `app/pages/1_personas.py`

### Constraints
- UI-only change — do NOT modify any backend `src/` files
- Only export the currently filtered set (not the full population)
- Limit narrative to 200 characters to keep CSV manageable
- If `persona.narrative` is None, use empty string
- All existing tests must pass
- Run `uv run ruff check .` before delivery
