# Sprint 13 Brief — Cursor (Claude)
## Research Design Page

### Context
Sprint 13 replaces three existing pages (Scenario Configurator, Probing Tree, Explorer) with a single unified **Research Design** page. This page is the core UX for Option C: users pick a scenario, choose a business question, review the probing tree, and run the full hybrid research pipeline with one button.

### Task: Build `app/pages/2_research.py`
**New file** that replaces `app/pages/2_scenario.py`. Do NOT delete the old file — we'll clean up in Sprint 15.

### Page Structure

The page has 3 collapsible sections, top to bottom.

#### Section A — Scenario & Question (always visible)

```python
st.header("Research Design")
st.caption("Design your research: pick a scenario, choose a business question, and run the hybrid pipeline.")

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()
```

**Scenario selector:**
```python
from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario

scenario_id = st.selectbox(
    "Select Scenario",
    SCENARIO_IDS,
    format_func=lambda sid: f"{get_scenario(sid).name} ({sid})",
)
scenario = get_scenario(scenario_id)
st.markdown(f"**{scenario.description}**")
st.caption(f"Product: {scenario.product.name} · ₹{scenario.product.price_inr:.0f} · Ages {scenario.target_age_range[0]}-{scenario.target_age_range[1]}")
```

**Business question selector:**
```python
from src.probing.question_bank import get_questions_for_scenario

questions = get_questions_for_scenario(scenario_id)
question = st.selectbox(
    "Business Question",
    questions,
    format_func=lambda q: q.title,
)
if question:
    st.info(question.description)
```

**Advanced parameters** (collapsed by default):
```python
with st.expander("Advanced: Tune Parameters", expanded=False):
    # Reuse the product + marketing sliders from 2_scenario.py
    # Copy the slider blocks for: price, taste_appeal, effort_to_acquire,
    # clean_label_score, health_relevance, lj_pass_available,
    # awareness_budget, awareness_level, trust_signal, social_proof,
    # expert_endorsement, discount_available
    # Channel mix (3 sliders: instagram, youtube, whatsapp)
    # Campaign toggles (pediatrician, school, sports_club, influencer)
    # Store modified scenario in session state
```

Use the same slider code from `app/pages/2_scenario.py` lines 56-251. Copy it into the expander. Store the custom scenario in `st.session_state[f"research_scenario_{scenario_id}"]` with the same reset-to-defaults pattern.

#### Section B — Probing Tree (collapsible)

```python
from src.probing.question_bank import get_tree_for_question

st.subheader("Probing Tree")
st.caption("Review the hypotheses that will be tested. Toggle branches to include/exclude.")
```

Load the tree for the selected question:
```python
tree = get_tree_for_question(question.id)
```

Display hypotheses as toggleable cards:
```python
enabled_hypotheses = []
for hyp in tree.hypotheses:
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        enabled = st.checkbox("", value=hyp.enabled, key=f"hyp_{hyp.id}")
    with col2:
        st.markdown(f"**{hyp.title}**")
        st.caption(hyp.rationale)
        # Count probes for this hypothesis
        probe_count = sum(1 for p in tree.probes if p.hypothesis_id == hyp.id)
        st.caption(f"{probe_count} probes")
    if enabled:
        enabled_hypotheses.append(hyp)
```

Show summary:
```python
st.caption(f"{len(enabled_hypotheses)} of {len(tree.hypotheses)} hypotheses enabled")
```

#### Section C — Run Research (bottom)

**Pre-run summary:**
```python
st.subheader("Run Research")

pop = st.session_state.population
n_personas = len(pop.personas)

# Estimate sample size and alternatives
sample_size = 18
alternative_count = 50

summary_cols = st.columns(3)
summary_cols[0].metric("Personas", f"{n_personas}")
summary_cols[1].metric("Deep Interviews", f"~{sample_size}")
summary_cols[2].metric("Alternative Scenarios", f"{alternative_count}")
```

**API key and cost awareness:**
```python
# Reuse the _has_api_key() / _resolve_api_key() pattern from 5_interviews.py or 6_report.py
api_available = _has_api_key()
if api_available:
    mock_mode = st.toggle("Mock Mode", value=False, help="Use real LLM for deep interviews")
    if not mock_mode:
        st.caption(f"Estimated cost: ~$0.15-0.30 for {sample_size} interviews")
else:
    mock_mode = True
    st.info("No API key configured. Running in mock mode.")
```

**Run button:**
```python
if st.button("Run Research", type="primary", use_container_width=True):
    from src.simulation.research_runner import ResearchRunner
    from src.utils.llm import LLMClient
    from src.config import Config

    llm = LLMClient(Config(
        llm_mock_enabled=mock_mode,
        llm_cache_enabled=not mock_mode,
        anthropic_api_key="" if mock_mode else _resolve_api_key(),
    ))

    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def on_progress(message: str, progress: float):
        progress_bar.progress(min(progress, 1.0))
        status_text.caption(message)

    runner = ResearchRunner(
        population=pop,
        scenario=custom_scenario,  # from the advanced params or base scenario
        question=question,
        llm_client=llm,
        mock_mode=mock_mode,
        alternative_count=alternative_count,
        sample_size=sample_size,
        progress_callback=on_progress,
    )

    result = runner.run()
    st.session_state["research_result"] = result
    progress_bar.progress(1.0)
    status_text.empty()

    # Completion metrics
    done_cols = st.columns(4)
    done_cols[0].metric("Decision Pathway", f"{n_personas} personas")
    done_cols[1].metric("Deep Interviews", f"{len(result.interview_results)} personas")
    done_cols[2].metric("Alternatives", f"{len(result.alternative_runs)} scenarios")
    done_cols[3].metric("Duration", f"{result.metadata.duration_seconds:.1f}s")

    st.success("Research complete!")
    # Navigation hint
    st.page_link("app/pages/3_results.py", label="View Results →", icon="📊")
```

**Display previous result if exists:**
```python
# Below the run button, if a previous result exists, show summary
prev = st.session_state.get("research_result")
if prev and not run_clicked:
    st.divider()
    st.caption(f"Previous run: {prev.metadata.scenario_id} · {prev.metadata.question_id} · {prev.metadata.timestamp}")
    st.page_link("app/pages/3_results.py", label="View Previous Results →", icon="📊")
```

### Reference Files
- `app/pages/2_scenario.py` — copy slider blocks from here (lines 56-251)
- `app/pages/5_interviews.py` — `_resolve_api_key()` and `_has_api_key()` patterns
- `src/probing/question_bank.py` — `get_questions_for_scenario()`, `get_tree_for_question()`
- `src/simulation/research_runner.py` — `ResearchRunner` class
- `src/utils/display.py` — `CHANNEL_HELP`, `display_name()`

### Page Numbering
Name the file `app/pages/2_research.py`. Streamlit sorts pages alphabetically, so `2_research.py` will appear where `2_scenario.py` currently is. Both will show in the sidebar temporarily — that's fine, we clean up in Sprint 15.

### Deliverables
1. `app/pages/2_research.py` — complete Research Design page with all 3 sections
2. Must run without errors when navigated to in Streamlit
3. Must successfully execute a mock research run and store result in session state

### Do NOT
- Delete existing pages (Sprint 15 cleanup)
- Modify existing source modules
- Create new backend modules (all Sprint 12 components are ready)
- Add dependencies
