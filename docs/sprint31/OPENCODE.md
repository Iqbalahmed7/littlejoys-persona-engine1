# Sprint 31 — OPENCODE Brief: Streamlit Simulation Builder Page

## Context
Add a 4th page to the LittleJoys Streamlit app that lets the LittleJoys team configure
a journey (product, price, channels, stimuli), run it against the population, and compare
two scenarios side by side — no Python required.

## Dependencies
Requires CURSOR (JourneyConfig) and CODEX (batch_runner.run_batch) to be complete first.

## Working directory
`/Users/admin/Documents/Simulatte Projects/1. LittleJoys`

## File to edit
`app/streamlit_app.py`

## Changes required

### 1. Add new import at top
```python
from src.simulation.batch_runner import run_batch
from src.simulation.journey_presets import list_presets, PRESET_JOURNEY_A, PRESET_JOURNEY_B
from src.simulation.journey_config import JourneyConfig, StimulusConfig, DecisionScenarioConfig
```

### 2. Add `page_simulation_builder()` function

```python
def page_simulation_builder(all_personas: dict[str, dict]) -> None:
    st.title("Simulation Builder")
    st.caption("Configure a journey, run it against the population, compare scenarios.")

    presets = list_presets()
    preset_options = ["Journey A — Nutrimix Repeat Purchase",
                      "Journey B — Magnesium Gummies"]

    col_preset, col_pop = st.columns([2, 1])
    preset_choice = col_preset.selectbox("Start from preset", preset_options)
    jid = preset_choice[8]  # "A" or "B"
    base_config = presets[jid]

    population_size = col_pop.slider("Population size", 10, 200, 50, step=10)

    st.divider()
    st.subheader("Product & Channel")

    col1, col2, col3 = st.columns(3)
    price = col1.slider(
        "Price (Rs)", 200, 1500,
        int(base_config.decisions[0].price_inr),
        step=50
    )
    channel_options = ["bigbasket", "firstcry_online", "d2c", "amazon", "pharmacy"]
    current_channel = base_config.decisions[0].channel
    channel = col2.selectbox(
        "Purchase channel",
        channel_options,
        index=channel_options.index(current_channel) if current_channel in channel_options else 0
    )

    st.divider()
    st.subheader("Marketing Mix")

    col_m1, col_m2, col_m3 = st.columns(3)
    has_pediatrician = col_m1.toggle(
        "Pediatrician endorsement",
        value=any(s.source in ("pediatrician", "pediatrician_followup") for s in base_config.stimuli)
    )
    has_influencer = col_m2.toggle(
        "Influencer campaign",
        value=any("influencer" in s.source for s in base_config.stimuli)
    )
    has_wom = col_m3.toggle(
        "WhatsApp WOM",
        value=any("whatsapp" in s.source for s in base_config.stimuli)
    )

    st.divider()
    st.subheader("Stimulus Sequence")
    st.caption("Each row = one touchpoint. Edit content to simulate different messaging.")

    stim_rows = [
        {"tick": s.tick, "type": s.type, "source": s.source, "content": s.content}
        for s in base_config.stimuli
    ]
    stim_df = pd.DataFrame(stim_rows)
    edited_stim = st.data_editor(
        stim_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "tick": st.column_config.NumberColumn("Day", min_value=0, max_value=200),
            "type": st.column_config.SelectboxColumn(
                "Type", options=["ad", "wom", "price_change", "social_event", "product"]
            ),
            "source": st.column_config.TextColumn("Source"),
            "content": st.column_config.TextColumn("Content", width="large"),
        }
    )

    st.divider()

    # Build modified JourneyConfig from UI state
    def _build_config_from_ui() -> JourneyConfig:
        new_stimuli = []
        for i, row in edited_stim.iterrows():
            # Filter out rows based on toggles
            source = str(row.get("source", ""))
            if not has_pediatrician and source in ("pediatrician", "pediatrician_followup"):
                continue
            if not has_influencer and "influencer" in source:
                continue
            if not has_wom and "whatsapp" in source:
                continue
            new_stimuli.append(StimulusConfig(
                id=f"custom-{i}",
                tick=int(row.get("tick", 0)),
                type=str(row.get("type", "ad")),
                source=source,
                content=str(row.get("content", "")),
            ))
        new_decisions = [
            d.model_copy(update={"price_inr": price, "channel": channel})
            for d in base_config.decisions
        ]
        return JourneyConfig(
            journey_id=jid,
            total_ticks=base_config.total_ticks,
            primary_brand=base_config.primary_brand,
            stimuli=new_stimuli,
            decisions=new_decisions,
        )

    col_run, col_save = st.columns([1, 1])
    run_clicked = col_run.button("Run Simulation", type="primary", use_container_width=True)
    save_a = col_save.button("Save as Scenario A", use_container_width=True)
    save_b = col_save.button("Save as Scenario B", use_container_width=True)

    if save_a:
        st.session_state["scenario_a_config"] = _build_config_from_ui().model_dump()
        st.success("Saved as Scenario A")
    if save_b:
        st.session_state["scenario_b_config"] = _build_config_from_ui().model_dump()
        st.success("Saved as Scenario B")

    if run_clicked:
        config = _build_config_from_ui()

        # Load personas
        valid_personas = []
        for pid, p_dict in list(all_personas.items())[:population_size]:
            p = parse_persona(p_dict)
            if p is not None:
                valid_personas.append((pid, p))

        if not valid_personas:
            st.error("No valid personas loaded.")
            return

        progress_bar = st.progress(0, text="Starting simulation...")
        result_container = st.empty()

        results_store = {"logs": [], "aggregate": None}

        def _progress_cb(done: int, total: int, log_dict: dict) -> None:
            pct = done / total
            name = log_dict.get("display_name") or log_dict.get("persona_id") or "?"
            progress_bar.progress(pct, text=f"[{done}/{total}] {name}")

        with st.spinner(f"Running journey {jid} for {len(valid_personas)} personas..."):
            result = run_batch(
                journey_config=config,
                personas=valid_personas,
                concurrency=5,
                progress_callback=_progress_cb,
            )

        progress_bar.progress(1.0, text=f"Done — {result.personas_run} personas in {result.elapsed_seconds:.0f}s")

        # Save to session state for comparison
        st.session_state[f"last_run_{jid}"] = result.to_dict()

        # Display results inline (reuse journey timeline logic)
        agg = result.aggregate
        st.divider()
        st.subheader("Results")

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Personas Run", result.personas_run)
        rc2.metric("Errors", result.errors)

        first_dist = agg.first_decision_distribution
        buy_pct = float(first_dist.get("buy", {}).get("pct", 0) or 0) + \
                  float(first_dist.get("trial", {}).get("pct", 0) or 0)
        rc3.metric("Buy + Trial", f"{buy_pct:.1f}%")
        rc4.metric("Reorder Rate", f"{agg.reorder_rate_pct:.1f}%")

        # Decision distribution
        st.write("**First decision distribution:**")
        for decision, stats in sorted(first_dist.items(), key=lambda x: -x[1].get("count", 0)):
            pct = float(stats.get("pct", 0))
            count = int(stats.get("count", 0))
            st.write(f"- **{decision}**: {count} ({pct:.1f}%)")

        st.write("**Top reorder drivers:**")
        for driver, count in list(agg.second_decision_drivers.items())[:5]:
            st.write(f"- {driver.replace('_', ' ').title()}: {count}")

        st.write("**Top lapse objections:**")
        for obj, count in list(agg.second_decision_objections.items())[:5]:
            st.write(f"- {obj.replace('_', ' ').title()}: {count}")

    # ── Comparison panel ──────────────────────────────────────────────────────
    if "scenario_a_config" in st.session_state and "scenario_b_config" in st.session_state:
        if st.button("Compare Scenario A vs B"):
            result_a = st.session_state.get(f"last_run_A") or st.session_state.get(f"last_run_B")
            result_b = st.session_state.get(f"last_run_B") or st.session_state.get(f"last_run_A")
            if result_a and result_b:
                st.divider()
                st.subheader("Scenario Comparison")
                agg_a = result_a.get("aggregate", {})
                agg_b = result_b.get("aggregate", {})

                comp_data = {
                    "Metric": ["Buy + Trial %", "Reorder Rate %", "Errors"],
                    "Scenario A": [
                        round(float(agg_a.get("reorder_rate_pct", 0)), 1),
                        round(float(agg_a.get("reorder_rate_pct", 0)), 1),
                        int(agg_a.get("errors", 0)),
                    ],
                    "Scenario B": [
                        round(float(agg_b.get("reorder_rate_pct", 0)), 1),
                        round(float(agg_b.get("reorder_rate_pct", 0)), 1),
                        int(agg_b.get("errors", 0)),
                    ],
                }
                comp_df = pd.DataFrame(comp_data)
                comp_df["Delta"] = comp_df["Scenario B"] - comp_df["Scenario A"]
                st.dataframe(comp_df, use_container_width=True)
```

### 3. Wire into `main()`

In the `main()` function, add `"Simulation Builder"` as the 4th nav option:

```python
page = st.sidebar.radio(
    "Navigate",
    ["Persona Inspector", "Constraint Violations", "Journey Timeline", "Simulation Builder"],
    ...
)
```

And add the branch:
```python
elif page == "Simulation Builder":
    page_simulation_builder(all_personas)
```

## Verification
```bash
# Syntax check
python3 -c "import ast; ast.parse(open('app/streamlit_app.py').read()); print('syntax OK')"

# Import check
python3 -c "
import sys; sys.path.insert(0, '.')
from src.simulation.batch_runner import run_batch
from src.simulation.journey_presets import list_presets
print('imports OK')
"

# All existing tests pass
python3 -m pytest tests/ -q --ignore=tests/integration
```
