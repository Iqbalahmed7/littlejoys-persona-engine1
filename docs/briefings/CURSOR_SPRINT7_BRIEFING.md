# Cursor — Sprint 7 Briefing

**PRD**: PRD-014a UX Clarity Pass
**Branch**: `feat/PRD-014a-ux-clarity`
**Priority**: P1 — UX polish (parallel to Codex's probing tree work)

---

## Your Task: Add Tooltips, Fix Labels, Add Context Headers

The app works, but a non-technical user can't understand what the parameters mean, why the scatter plot matters, or how the scenario config relates to counterfactuals. Fix all of these.

---

### 1. Scenario Config Page — Add `help=` Tooltips to Every Widget

**File**: `app/pages/2_scenario.py`

Add the `help=` parameter to every `st.slider()` and `st.toggle()`. The help text appears as an ℹ️ icon that shows a tooltip on hover.

**Product Parameters** (lines 53-70):

```python
# BEFORE:
custom_scenario.product.price_inr = st.slider(
    "Price (INR)", 100.0, 1500.0, float(custom_scenario.product.price_inr), step=50.0
)

# AFTER:
custom_scenario.product.price_inr = st.slider(
    "Price (INR)", 100.0, 1500.0, float(custom_scenario.product.price_inr), step=50.0,
    help="Retail price of the product. Lower prices reduce the purchase barrier, "
         "especially for budget-conscious (SEC B2+) families. "
         "Reference: Nutrimix ₹599, Gummies ₹499, Protein Mix ₹699.",
)
```

Here are ALL the tooltips to add:

| Widget | `help=` text |
|--------|-------------|
| **Price (INR)** | `"Retail price of the product. Lower prices reduce the purchase barrier, especially for budget-conscious (SEC B2+) families. Reference: Nutrimix ₹599, Gummies ₹499, Protein Mix ₹699."` |
| **Taste Appeal** | `"How likely children are to accept the taste and format. 0.0 = most kids refuse, 1.0 = kids ask for it. Gummy formats score 0.8+, powders 0.4–0.6."` |
| **Effort to Acquire** | `"Friction to obtain AND use the product. 0.0 = buy and consume instantly (ready-to-drink), 1.0 = requires multiple steps (cook into a recipe). High effort hurts busy parents most."` |
| **Clean Label Score** | `"How 'natural' the ingredient list looks to a parent scanning the pack. 0.0 = synthetic-looking (E-numbers, preservatives), 1.0 = recognisable whole ingredients."` |
| **Health Relevance** | `"How clearly this product solves a perceived health need. 0.0 = nice-to-have wellness, 1.0 = doctor-recommended for a specific condition."` |
| **LJ Pass Available** | `"Whether a subscription/loyalty pass is offered. Reduces repeat-purchase friction and increases retention for habit-forming products."` |
| **Awareness Budget** | `"Marketing spend reaching target parents. 0.0 = no marketing, 1.0 = saturated coverage. New products typically start at 0.2–0.3."` |
| **Awareness Level** | `"What fraction of target parents have heard of this product. Distinct from budget — a viral moment can create high awareness at low budget."` |
| **Trust Signal** | `"Overall brand credibility. Combines packaging quality, brand story, certifications, and social proof. New D2C brands start around 0.3–0.4."` |
| **Social Proof** | `"Visible evidence that other parents use this product. Reviews, ratings, 'X mothers trust us' claims. Strongly influences community-oriented parents."` |
| **Expert Endorsement** | `"Professional credibility signals — doctor recommendations, clinical studies cited on packaging, dietitian partnerships."` |
| **Discount Available** | `"Active promotional discount (0.0 = full price, 0.5 = 50% off). Temporary discounts boost trial but may not sustain repeat purchase."` |
| **School Partnership** | `"Product distributed or endorsed through schools. High-trust channel that bypasses digital ad skepticism. Especially effective for 7-14 age group."` |
| **Pediatrician Endorsement** | `"Formal endorsement from pediatricians. The single strongest trust signal for health-anxious parents."` |
| **Influencer Campaign** | `"Parenting influencer partnerships on Instagram/YouTube. Effective for digitally-active Tier 1 parents, less impact in Tier 2-3."` |

For the **channel mix sliders** (Instagram, YouTube, WhatsApp — lines 107-114), add help inside the loop:

```python
CHANNEL_HELP = {
    "instagram": "Visual storytelling channel. Strongest with SEC A1-A2 urban mothers aged 25-35.",
    "youtube": "Long-form educational content. Reaches all SEC classes. Best for building trust via expert reviews.",
    "whatsapp": "Community-driven sharing. Highest trust signal in Tier 2-3 cities. Low cost, high conversion when organic.",
}

for ch in channels:
    val = st.slider(
        ch.title(), 0.0, 1.0,
        float(custom_scenario.marketing.channel_mix.get(ch, 0.0)),
        step=0.05,
        key=f"slider_{ch}",
        help=CHANNEL_HELP.get(ch, ""),
    )
```

**Also add a context header** at the top of the page (after `st.title()`):

```python
st.caption(
    "Configure the market conditions for your product. These become the **baseline** "
    "that the Results and Counterfactual pages analyse. Adjust parameters to model "
    "different launch strategies."
)
```

---

### 2. Counterfactual Page — Add Rationale and Context Header

**File**: `app/pages/4_counterfactual.py`

**A. Add context header** (after line 12, after `st.title()`):

```python
st.caption(
    "Your current scenario defines the baseline. Here, test what happens when you "
    "change **one variable** while keeping everything else constant. This isolates "
    "the impact of specific interventions."
)
```

**B. Add rationale text to predefined interventions** (lines 33-48):

Create a rationale dictionary and display it under each intervention name:

```python
INTERVENTION_RATIONALE: dict[str, dict[str, str]] = {
    "nutrimix_2_6": {
        "price_reduction_20": "Tests whether a 20% price cut moves price-sensitive SEC B2 parents past the purchase barrier.",
        "school_partnership": "Tests whether institutional trust drives adoption among parents sceptical of social media ads.",
        "free_trial": "Tests whether reducing first-purchase friction through free trials builds the habit loop.",
        "influencer_blitz": "Tests whether aggressive awareness spend reaches parents who simply haven't heard of the product.",
    },
    "nutrimix_7_14": {
        "taste_improvement": "Tests whether older kids' taste preferences are the primary barrier to adoption.",
        "age_specific_branding": "Tests whether repositioning away from 'toddler brand' changes parent perception for school-age kids.",
        "pediatrician_push": "Tests whether doctor endorsement overcomes the 'my older kid doesn't need supplements' belief.",
    },
    "magnesium_gummies": {
        "awareness_campaign": "Tests whether the primary barrier is simply that parents don't know kids need magnesium.",
        "price_premium_reduction": "Tests price elasticity in a category where parents have no reference price.",
        "doctor_endorsement": "Tests whether clinical credibility makes 'gummy supplement' feel like real medicine.",
    },
    "protein_mix": {
        "convenience_format": "Tests whether eliminating the cooking requirement (powder → ready-to-drink) unlocks adoption.",
        "taste_improvement": "Tests whether kids rejecting the taste in cooked food is the core blocker.",
        "school_sports_partnership": "Tests whether embedding the product in a sports/activity context drives relevance.",
    },
}
```

Then in the intervention display loop:

```python
for i, (cf_name, mods) in enumerate(predefined.items()):
    with cols[i], st.container(border=True):
        st.markdown(f"**{cf_name.replace('_', ' ').title()}**")
        # Add rationale
        rationale = INTERVENTION_RATIONALE.get(scenario_id, {}).get(cf_name, "")
        if rationale:
            st.caption(rationale)
        st.caption(f"Changes: {list(mods.keys())}")
        # ... rest of button code unchanged
```

**C. Expand the Custom What-If section** to include more parameters. Currently only price and awareness budget are exposed. Add taste_appeal and effort_to_acquire:

```python
with st.expander("Configure Custom Intervention"):
    c1, c2 = st.columns(2)
    with c1:
        custom_price = st.number_input(
            "Override Price (INR)", value=0.0, step=10.0,
            help="Set to 0 to keep original price. Any positive value overrides the scenario price.",
        )
        custom_taste = st.number_input(
            "Override Taste Appeal", value=-1.0, min_value=-1.0, max_value=1.0, step=0.05,
            help="Set to -1 to keep original. 0.0–1.0 overrides taste appeal.",
        )
    with c2:
        custom_budget = st.number_input(
            "Override Awareness Budget", value=-1.0, step=0.1,
            help="Set to -1 to keep original. 0.0–1.0 overrides awareness budget.",
        )
        custom_effort = st.number_input(
            "Override Effort to Acquire", value=-1.0, min_value=-1.0, max_value=1.0, step=0.05,
            help="Set to -1 to keep original. 0.0 = instant, 1.0 = high friction.",
        )

    if st.button("Run Custom Counterfactual", type="secondary"):
        mods = {}
        if custom_price > 0:
            mods["product.price_inr"] = custom_price
        if custom_budget >= 0.0:
            mods["marketing.awareness_budget"] = custom_budget
        if custom_taste >= 0.0:
            mods["product.taste_appeal"] = custom_taste
        if custom_effort >= 0.0:
            mods["product.effort_to_acquire"] = custom_effort
        # ... rest unchanged
```

---

### 3. Psychographic Scatter — Clearer Labels and Insights

**File**: `app/pages/1_population.py` (lines 153-234)

**A. Change legend labels** from "Adopted"/"Not adopted" to "Would buy"/"Wouldn't buy":

Find the `outcome_label` function or the lambda that maps outcomes. Update:

```python
# Replace current outcome mapping with clearer labels
OUTCOME_LABELS = {"adopt": "Would buy", "reject": "Wouldn't buy"}

plot_df = df.assign(
    _outcome_display=df["outcome"].map(
        lambda v: OUTCOME_LABELS.get(str(v), str(v)) if v is not None else "No simulation"
    )
)
```

**B. Add axis explanations** — append scale description to axis titles:

```python
fig_s.update_xaxes(title=f"{display_name(x_attr)} (0 = low, 1 = high)")
fig_s.update_yaxes(title=f"{display_name(y_attr)} (0 = low, 1 = high)")
```

**C. Make quadrant insight the headline**, not a caption:

```python
# BEFORE:
if insight_parts:
    st.caption(" · ".join(insight_parts))

# AFTER:
if insight_parts:
    st.info(" · ".join(insight_parts))
```

**D. Improve the "no simulation" state** message:

```python
# BEFORE:
if color_col is None:
    st.info("Run a simulation from the Home page to see how these attributes relate to adoption decisions.")

# AFTER:
if color_col is None:
    st.info(
        "🔍 Run a scenario from the **Home** page first. Once you do, this chart will colour "
        "each persona by whether they **would buy** or **wouldn't buy** — revealing which "
        "attribute combinations predict purchase behaviour."
    )
```

**E. Add a question-driven subtitle** to the chart:

```python
# After the title line in px.scatter:
title_text = f"Do parents with high {display_name(x_attr)} and {display_name(y_attr)} buy more?"
subtitle_text = f"{display_name(x_attr)} vs {display_name(y_attr)}"

fig_s = px.scatter(
    plot_df,
    x=x_attr,
    y=y_attr,
    color=color_key,
    opacity=0.65,
    title=title_text if color_col else subtitle_text,
)
```

---

### 4. Results Page — Tooltip on What-If Sliders

**File**: `app/pages/3_results.py` (lines 159-184)

Add `help=` to the three what-if sliders:

```python
with w1:
    price = st.slider(
        "Price (INR)",
        min_value=float(base.product.price_inr) * 0.5,
        max_value=float(base.product.price_inr) * 1.5,
        value=float(base.product.price_inr),
        step=1.0,
        key="whatif_price",
        help="Drag to test how price changes affect adoption. This runs a quick simulation on a subset of personas.",
    )
with w2:
    taste = st.slider(
        "Taste Appeal",
        0.0, 1.0,
        float(base.product.taste_appeal),
        0.01,
        key="whatif_taste",
        help="How likely kids accept the taste. 0 = refuse, 1 = love it. Try 0.8+ for gummy formats.",
    )
with w3:
    ab = st.slider(
        "Awareness Budget",
        0.0, 1.0,
        float(base.marketing.awareness_budget),
        0.01,
        key="whatif_ab",
        help="Marketing reach. 0 = no spend, 1 = saturated. See how awareness scaling changes adoption.",
    )
```

---

### 5. Tests

**File**: `tests/unit/test_ux_tooltips.py` (new)

Verify that tooltips exist and are non-empty. This is a structural test:

```python
"""Test that UX tooltip constants are complete and non-empty."""

from __future__ import annotations


def test_intervention_rationale_covers_all_scenarios():
    """Every scenario's predefined interventions have rationale text."""
    # Import the rationale dict from counterfactual page
    # or define it in a shared location
    from app.pages import _4_counterfactual as cf_page

    # If rationale is module-level, check it covers scenarios
    from src.decision.scenarios import get_predefined_counterfactuals
    for scenario_id in ["nutrimix_2_6", "nutrimix_7_14", "magnesium_gummies", "protein_mix"]:
        predefined = get_predefined_counterfactuals(scenario_id)
        for cf_name in predefined:
            rationale = cf_page.INTERVENTION_RATIONALE.get(scenario_id, {}).get(cf_name, "")
            assert rationale, f"Missing rationale for {scenario_id}/{cf_name}"


def test_channel_help_covers_all_channels():
    """Every channel has help text."""
    from app.pages._2_scenario import CHANNEL_HELP  # adjust import path
    for ch in ["instagram", "youtube", "whatsapp"]:
        assert ch in CHANNEL_HELP
        assert len(CHANNEL_HELP[ch]) > 10


def test_outcome_labels_defined():
    """Outcome labels use user-friendly terms."""
    OUTCOME_LABELS = {"adopt": "Would buy", "reject": "Wouldn't buy"}
    assert "adopt" not in OUTCOME_LABELS["adopt"].lower()
    assert "reject" not in OUTCOME_LABELS["reject"].lower()
```

**Note**: Adjust import paths to match the actual module structure. If Streamlit page imports are tricky, move the constants (INTERVENTION_RATIONALE, CHANNEL_HELP, OUTCOME_LABELS) into `src/utils/display.py` so they're testable from unit tests.

---

## Standards

- `from __future__ import annotations`
- Every user-facing widget must have `help=` text
- No raw field names anywhere (use `display_name()`)
- Help text should be 1-2 sentences, written for a marketing executive, not a developer
- No jargon: say "Would buy" not "Adopted", say "marketing reach" not "awareness budget coefficient"

## Run

```bash
uv run pytest tests/ -x -q
uv run ruff check app/pages/
```
