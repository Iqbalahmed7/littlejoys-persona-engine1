# Sprint 29 — Brief: OPENCODE

**Role:** UI / lightweight tooling
**Model:** GPT-5.4 Nano
**Assignment:** Streamlit debug UI — persona inspector + constraint violation dashboard
**Est. duration:** 4-5 hours
**START:** After Codex signals done (`agent.reflect()` must exist).

---

## Files to Create / Modify

| Action | File |
|---|---|
| CREATE | `app/__init__.py` (empty) |
| CREATE | `app/streamlit_app.py` |
| MODIFY | `src/agents/__init__.py` — add `ReflectionEngine` export |

## Do NOT Touch
- Any file in `src/agents/` except `__init__.py`
- Any test file
- Any script in `scripts/`

---

## Part 1: Add `ReflectionEngine` to exports

Open `src/agents/__init__.py` and add ONE line:

```python
from .reflection import ReflectionEngine, ReflectionInsight
```

Add both to `__all__`.

Verify:
```bash
python3 -c "from src.agents import ReflectionEngine; print('OK')"
```

---

## Part 2: `app/streamlit_app.py`

Two-page Streamlit app. Run with:
```bash
streamlit run app/streamlit_app.py
```

### Page 1: Persona Inspector

Pick any of the 200 personas by ID and inspect their full cognitive state.

**Sections to show:**

**Header:**
- `persona.id` + `persona.display_name` (fallback to id if None)
- Age, city tier, family structure, employment status
- Decision style, trust anchor, price sensitivity (null-safe — parent_traits/budget_profile may be None)

**Identity attributes (collapsible):**
- Show all 12 attribute categories as expandable sections
- Each attribute shown as a labelled metric — no raw field names
- Map field names to human-readable labels (e.g. `health_anxiety` → `"Health Anxiety"`)

**Episodic memory stream:**
- Table: timestamp | event_type | content (truncated 80 chars) | salience | valence
- Colour-code by event_type: stimulus=blue, decision=orange, reflection=purple, brand_touchpoint=green
- Show count: "X memories accumulated"

**Brand memories:**
- For each brand in `persona.brand_memories`:
  - Brand name, trust_level as a progress bar (0-1), purchase_count, WOM received count

**Narrative + Summary:**
- `persona.narrative` in an expander (may be None)
- `persona.first_person_summary` in an expander (may be None)

### Page 2: Constraint Violations Dashboard

Reads `data/population/constraint_violations_report.json`.

**Summary metrics row:**
- Total checked, Clean %, Hard violation %, Soft violation %

**Rule hit counts bar chart:**
- Horizontal bar chart: rule_id on y-axis, count on x-axis
- Top 15 rules
- Colour: red = hard, amber = soft

**Filterable violations table:**
- Columns: persona_id | rule_id | severity | attribute_a | attribute_b | message
- Filter by: severity (all/hard/soft), rule_id (dropdown)
- Clicking a persona_id switches to Page 1 with that persona selected

### Code skeleton

```python
import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.taxonomy.schema import Persona

# ── Data loading (cached) ─────────────────────────────────────────────────────

@st.cache_data
def load_all_personas() -> dict[str, dict]:
    """Load all personas as raw dicts, keyed by id."""
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return {str(p.get("id", i)): p for i, p in enumerate(data)}
            return {str(k): v for k, v in data.items()}
    return {}


@st.cache_data
def load_violations_report() -> dict:
    path = PROJECT_ROOT / "data" / "population" / "constraint_violations_report.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


@st.cache_data
def parse_persona(p_dict: str) -> Persona | None:
    """Parse a JSON-serialised persona dict. Cached by content string."""
    try:
        return Persona.model_validate(json.loads(p_dict))
    except Exception:
        return None


# ── Field name → human label mapping ─────────────────────────────────────────

FIELD_LABELS: dict[str, str] = {
    "health_anxiety": "Health Anxiety",
    "information_need": "Information Need",
    "risk_tolerance": "Risk Tolerance",
    "analysis_paralysis_tendency": "Analysis Paralysis",
    "decision_speed": "Decision Speed",
    "social_proof_bias": "Social Proof Bias",
    "authority_bias": "Authority Bias",
    "loss_aversion": "Loss Aversion",
    "best_for_my_child_intensity": "Best-for-Child Drive",
    "supplement_necessity_belief": "Supplement Necessity Belief",
    "food_first_belief": "Food-First Belief",
    "brand_loyalty_tendency": "Brand Loyalty",
    "guilt_sensitivity": "Guilt Sensitivity",
    "budget_consciousness": "Budget Consciousness",
    "deal_seeking_intensity": "Deal Seeking",
    "digital_payment_comfort": "Digital Payment Comfort",
    "label_reading_habit": "Label Reading Habit",
    "organic_preference": "Organic Preference",
    "ayurveda_affinity": "Ayurveda Affinity",
    "western_brand_trust": "Western Brand Trust",
    "indie_brand_openness": "Indie Brand Openness",
    "peer_influence_strength": "Peer Influence",
    "influencer_trust": "Influencer Trust",
    "pediatrician_influence": "Pediatrician Influence",
    "elder_advice_weight": "Elder Advice Weight",
    "wom_transmitter_tendency": "WOM Transmitter",
    "immunity_concern": "Immunity Concern",
    "growth_concern": "Growth Concern",
    "emotional_persuasion_susceptibility": "Emotional Ad Susceptibility",
    "fear_appeal_responsiveness": "Fear Appeal Response",
    "impulse_purchase_tendency": "Impulse Purchase Tendency",
    "perceived_time_scarcity": "Perceived Time Scarcity",
}


EVENT_COLOURS = {
    "stimulus": "#3B82F6",       # blue
    "decision": "#F97316",       # orange
    "reflection": "#8B5CF6",     # purple
    "brand_touchpoint": "#10B981", # green
    "semantic": "#6B7280",       # grey
}


# ── Pages ─────────────────────────────────────────────────────────────────────

def page_persona_inspector(all_personas: dict[str, dict]) -> None:
    st.title("Persona Inspector")

    if not all_personas:
        st.error("No personas found in data/population/.")
        return

    # Allow deep-linking from violations page
    default_id = st.session_state.get("selected_persona_id", list(all_personas.keys())[0])
    persona_id = st.selectbox(
        "Select persona", options=sorted(all_personas.keys()), index=sorted(all_personas.keys()).index(default_id)
    )
    st.session_state["selected_persona_id"] = persona_id

    p_dict = all_personas[persona_id]
    persona = parse_persona(json.dumps(p_dict))

    if persona is None:
        st.error(f"Could not parse persona {persona_id}")
        return

    # Header
    name = persona.display_name or persona.id
    st.header(f"{name}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Age", persona.demographics.parent_age)
    col2.metric("City Tier", persona.demographics.city_tier)
    col3.metric("Family", persona.demographics.family_structure)
    col4.metric("Employment", persona.career.employment_status)

    col5, col6, col7 = st.columns(3)
    decision_style = persona.parent_traits.decision_style if persona.parent_traits else "—"
    trust_anchor = persona.parent_traits.trust_anchor if persona.parent_traits else "—"
    price_sens = persona.budget_profile.price_sensitivity if persona.budget_profile else "—"
    col5.metric("Decision Style", decision_style)
    col6.metric("Trust Anchor", trust_anchor)
    col7.metric("Price Sensitivity", price_sens)

    st.divider()

    # Identity attributes
    with st.expander("Identity Attributes", expanded=False):
        for category_name in persona._IDENTITY_CATEGORY_MODELS:
            category = getattr(persona, category_name)
            st.subheader(category_name.replace("_", " ").title())
            cat_data = category.model_dump()
            cols = st.columns(3)
            for i, (field, value) in enumerate(cat_data.items()):
                label = FIELD_LABELS.get(field, field.replace("_", " ").title())
                if isinstance(value, float):
                    cols[i % 3].metric(label, f"{value:.2f}")
                else:
                    cols[i % 3].metric(label, str(value))

    # Episodic memory
    st.subheader(f"Episodic Memory ({len(persona.episodic_memory)} entries)")
    if persona.episodic_memory:
        mem_data = [
            {
                "Timestamp": m.timestamp[:19].replace("T", " "),
                "Type": m.event_type,
                "Content": m.content[:80] + ("..." if len(m.content) > 80 else ""),
                "Salience": round(m.salience, 2),
                "Valence": round(m.emotional_valence, 2),
            }
            for m in reversed(persona.episodic_memory)
        ]
        st.dataframe(pd.DataFrame(mem_data), use_container_width=True)
    else:
        st.caption("No memories yet.")

    # Brand memories
    if persona.brand_memories:
        st.subheader("Brand Memories")
        for brand, bm in persona.brand_memories.items():
            with st.expander(f"{brand.title()} — trust: {bm.trust_level:.2f}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Trust Level", f"{bm.trust_level:.2f}")
                col2.metric("Purchases", bm.purchase_count)
                col3.metric("WOM Received", len(bm.word_of_mouth_received))
                st.progress(bm.trust_level)

    # Narrative
    if persona.narrative:
        with st.expander("Narrative"):
            st.write(persona.narrative)
    if persona.first_person_summary:
        with st.expander("First Person Summary"):
            st.write(persona.first_person_summary)


def page_violations_dashboard(report: dict) -> None:
    st.title("Constraint Violations Dashboard")

    if not report:
        st.warning("No violations report found at data/population/constraint_violations_report.json")
        st.caption("Run: python3 scripts/validate_personas.py --fix-report")
        return

    summary = report.get("summary", {})

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Personas", report.get("total_personas", 0))
    col2.metric("Clean", f"{summary.get('clean', 0)} ({summary.get('pct_clean', 0)}%)")
    col3.metric("Hard Violations", summary.get("hard_violations", 0),
                delta=f"{summary.get('pct_hard', 0)}%", delta_color="inverse")
    col4.metric("Soft Only", summary.get("soft_violations", 0))

    st.divider()

    # Rule hit counts bar chart
    rule_counts = report.get("rule_hit_counts", {})
    if rule_counts:
        st.subheader("Rule Hit Counts (top 15)")
        df_rules = pd.DataFrame([
            {"Rule": k, "Count": v}
            for k, v in list(rule_counts.items())[:15]
        ])
        st.bar_chart(df_rules.set_index("Rule"))

    st.divider()

    # Violations table
    st.subheader("Violations by Persona")

    violations_by_persona = report.get("violations_by_persona", {})
    all_rows = []
    for pid, viols in violations_by_persona.items():
        for v in viols:
            all_rows.append({
                "Persona ID": pid,
                "Rule": v["rule_id"],
                "Severity": v["severity"],
                "Attribute A": v["attribute_a"],
                "Attribute B": v["attribute_b"],
                "Message": v["message"][:80],
            })

    if all_rows:
        df = pd.DataFrame(all_rows)

        # Filters
        col1, col2 = st.columns(2)
        severity_filter = col1.selectbox("Severity", ["all", "hard", "soft"])
        all_rules = sorted(df["Rule"].unique().tolist())
        rule_filter = col2.selectbox("Rule", ["all"] + all_rules)

        if severity_filter != "all":
            df = df[df["Severity"] == severity_filter]
        if rule_filter != "all":
            df = df[df["Rule"] == rule_filter]

        # Clicking persona ID → navigate to inspector
        st.dataframe(df, use_container_width=True)
        st.caption("To inspect a persona: copy its ID, go to Persona Inspector page, and select it.")
    else:
        st.success("No violations found.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="LittleJoys Persona Lab",
        page_icon="🧠",
        layout="wide",
    )

    page = st.sidebar.radio(
        "Navigate",
        ["Persona Inspector", "Constraint Violations"],
    )

    all_personas = load_all_personas()
    violations_report = load_violations_report()

    st.sidebar.divider()
    st.sidebar.caption(f"{len(all_personas)} personas loaded")
    st.sidebar.caption(
        f"{violations_report.get('summary', {}).get('clean', '?')} clean / "
        f"{violations_report.get('summary', {}).get('hard_violations', '?')} hard violations"
    )

    if page == "Persona Inspector":
        page_persona_inspector(all_personas)
    else:
        page_violations_dashboard(violations_report)


if __name__ == "__main__":
    main()
```

---

## Acceptance Criteria

**Exports:**
- [ ] `from src.agents import ReflectionEngine, ReflectionInsight` works without error

**App:**
- [ ] `streamlit run app/streamlit_app.py` launches without ImportError
- [ ] Persona Inspector loads and renders a persona header without error
- [ ] Memory table renders (empty state handled gracefully)
- [ ] Brand memories section shows for personas with brand data
- [ ] Narrative/summary expanders show (None state handled gracefully)
- [ ] Violations dashboard loads the report and shows summary metrics
- [ ] Bar chart renders for rule hit counts
- [ ] Violations table filters work (severity + rule dropdowns)
- [ ] All field accesses null-safe (`parent_traits`, `budget_profile` may be None)
- [ ] No raw field names shown to user — all mapped through `FIELD_LABELS`
