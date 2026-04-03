# Sprint 30 — Brief: OPENCODE

**Role:** UI / lightweight tooling
**Model:** GPT-5.4 Nano
**Assignment:** Add Page 3 (Journey Timeline) to `app/streamlit_app.py`
**Est. duration:** 4-5 hours
**START:** After Cursor + Codex signal done

---

## Files to Modify

| Action | File |
|---|---|
| MODIFY | `app/streamlit_app.py` — add `page_journey_timeline()` function + wire into navigation |

## Do NOT Touch
- `src/` — any file
- `tests/` — any file
- `scripts/` — any file
- Existing Page 1 (Persona Inspector) or Page 2 (Constraint Violations) — do not modify them

---

## What to Add

A third page to the existing Streamlit app. The page reads the journey results JSON files and visualises:
1. Brand trust trajectory over time (line chart)
2. Decision points highlighted on the timeline
3. Per-persona journey drill-down
4. Aggregate reorder / conversion stats

---

## Data Loading (add to existing cached loaders)

```python
@st.cache_data
def load_journey_results(journey_id: str) -> dict:
    """Load journey results for A or B."""
    path = PROJECT_ROOT / "data" / "population" / f"journey_{journey_id}_results.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
```

---

## `page_journey_timeline()` — Full Implementation

```python
def page_journey_timeline() -> None:
    st.title("Journey Timeline")
    st.caption("Multi-tick simulation: brand trust across 60 days")

    # Journey selector
    journey_id = st.sidebar.radio("Journey", ["A — Nutrimix Repeat Purchase", "B — Magnesium Gummies"])
    jid = journey_id[0]  # "A" or "B"

    data = load_journey_results(jid)

    if not data:
        st.warning(f"Journey {jid} results not found.")
        st.code(f"ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey {jid}")
        return

    aggregate = data.get("aggregate", {})
    logs = data.get("logs", [])

    # ── Summary metrics row ────────────────────────────────────────────────
    st.subheader("Population Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Personas Run", data.get("total_personas", 0))
    col2.metric("Errors", aggregate.get("errors", 0))

    first_dist = aggregate.get("first_decision_distribution", {})
    buy_pct = first_dist.get("buy", {}).get("pct", 0) + first_dist.get("trial", {}).get("pct", 0)
    col3.metric("Buy + Trial (First Decision)", f"{buy_pct:.1f}%")

    reorder_pct = aggregate.get("reorder_rate_pct", 0)
    label = "Reorder Rate" if jid == "A" else "Continuation Rate"
    col4.metric(label, f"{reorder_pct:.1f}%",
                delta=f"{reorder_pct - buy_pct:.1f}pp vs first purchase",
                delta_color="inverse" if reorder_pct < buy_pct else "normal")

    st.divider()

    # ── Brand trust trajectory chart ──────────────────────────────────────
    st.subheader("Brand Trust Over Time (population mean)")

    trust_by_tick = aggregate.get("trust_by_tick", {})
    if trust_by_tick:
        trust_df = pd.DataFrame([
            {"Day": int(tick), "Mean Trust": round(trust, 4)}
            for tick, trust in sorted(trust_by_tick.items(), key=lambda x: int(x[0]))
        ])
        st.line_chart(trust_df.set_index("Day"))
        st.caption("Trust scale: 0.0 (no trust) → 1.0 (full trust). Each data point is the mean across all personas.")
    else:
        st.caption("No trust trajectory data available.")

    st.divider()

    # ── Decision distributions ─────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        label_first = "First Purchase (Day 20)" if jid == "A" else "First Trial (Day 35)"
        st.subheader(label_first)
        for decision, stats in first_dist.items():
            st.metric(decision.replace("_", " ").title(),
                      f"{stats.get('count', 0)} ({stats.get('pct', 0):.1f}%)")

    with col_right:
        label_second = "Reorder Decision (Day 60)" if jid == "A" else "Continuation (Day 45)"
        st.subheader(label_second)
        second_dist = aggregate.get("second_decision_distribution", {})
        for decision, stats in second_dist.items():
            st.metric(decision.replace("_", " ").title(),
                      f"{stats.get('count', 0)} ({stats.get('pct', 0):.1f}%)")

    st.divider()

    # ── Top drivers and objections ─────────────────────────────────────────
    col_d, col_o = st.columns(2)

    with col_d:
        st.subheader("Top Reorder Drivers")
        for driver, count in list(aggregate.get("second_decision_drivers", {}).items())[:5]:
            st.write(f"- **{driver.replace('_', ' ').title()}** — {count}")

    with col_o:
        st.subheader("Top Lapse Objections")
        for obj, count in list(aggregate.get("second_decision_objections", {}).items())[:5]:
            st.write(f"- **{obj.replace('_', ' ').title()}** — {count}")

    st.divider()

    # ── Per-persona drill-down ─────────────────────────────────────────────
    st.subheader("Persona Journey Drill-Down")

    if not logs:
        st.caption("No individual journey logs available.")
        return

    # Build a summary table of all personas
    persona_rows = []
    for log in logs:
        if log.get("error"):
            continue
        snapshots = log.get("snapshots", [])
        final = log.get("final_decision") or {}
        # Get trust at last tick
        last_trust = 0.0
        if snapshots:
            last_snap = snapshots[-1]
            brand_trust = last_snap.get("brand_trust", {})
            last_trust = max(brand_trust.values()) if brand_trust else 0.0

        persona_rows.append({
            "Persona": log.get("display_name", log.get("persona_id", "?")),
            "Final Decision": final.get("decision", "—"),
            "Reordered": "✅" if log.get("reordered") else "❌",
            "Final Trust": round(last_trust, 3),
            "Memories": snapshots[-1].get("memories_count", 0) if snapshots else 0,
        })

    if persona_rows:
        df = pd.DataFrame(persona_rows)

        # Filters
        col_f1, col_f2 = st.columns(2)
        reorder_filter = col_f1.selectbox("Show", ["All", "Reordered ✅", "Lapsed ❌"])
        decision_filter = col_f2.selectbox("Final Decision", ["all"] + sorted(df["Final Decision"].unique().tolist()))

        if reorder_filter == "Reordered ✅":
            df = df[df["Reordered"] == "✅"]
        elif reorder_filter == "Lapsed ❌":
            df = df[df["Reordered"] == "❌"]
        if decision_filter != "all":
            df = df[df["Final Decision"] == decision_filter]

        st.dataframe(df, use_container_width=True)
        st.caption(f"Showing {len(df)} personas.")

    # Individual persona deep-dive
    st.subheader("Individual Persona — Tick-by-Tick")
    persona_ids = [log.get("persona_id") for log in logs if not log.get("error")]
    if persona_ids:
        selected_pid = st.selectbox("Select persona", options=persona_ids)
        selected_log = next((l for l in logs if l.get("persona_id") == selected_pid), None)

        if selected_log:
            snapshots = selected_log.get("snapshots", [])
            if snapshots:
                # Trust chart for this persona
                trust_rows = []
                for snap in snapshots:
                    for brand, trust in snap.get("brand_trust", {}).items():
                        trust_rows.append({"Day": snap["tick"], "Brand": brand, "Trust": trust})
                if trust_rows:
                    trust_df = pd.DataFrame(trust_rows)
                    pivot = trust_df.pivot_table(index="Day", columns="Brand", values="Trust", aggfunc="first")
                    st.line_chart(pivot)

                # Decision points
                decision_ticks = [s for s in snapshots if s.get("decision_result")]
                if decision_ticks:
                    st.write("**Decision Points:**")
                    for snap in decision_ticks:
                        dr = snap["decision_result"]
                        if "error" not in dr:
                            st.write(f"Day {snap['tick']}: **{dr.get('decision', '?')}** "
                                     f"(confidence: {dr.get('confidence', 0):.0%})")

                # Reflection moments
                reflection_ticks = [s for s in snapshots if s.get("reflected")]
                if reflection_ticks:
                    st.write(f"**Reflection triggered:** Days {', '.join(str(s['tick']) for s in reflection_ticks)}")
```

---

## Wire into Navigation

In `main()`, add "Journey Timeline" to the sidebar radio and call `page_journey_timeline()`:

```python
page = st.sidebar.radio(
    "Navigate",
    ["Persona Inspector", "Constraint Violations", "Journey Timeline"],
)
...
elif page == "Journey Timeline":
    page_journey_timeline()
```

Also update the sidebar caption to include journey data if available:
```python
journey_a = load_journey_results("A")
if journey_a:
    reorder_pct = journey_a.get("aggregate", {}).get("reorder_rate_pct", "?")
    st.sidebar.caption(f"Journey A reorder rate: {reorder_pct}%")
```

---

## Null-Safety Rules

All of these may be None, empty, or missing — handle gracefully:
- `data.get("aggregate", {})` — always use `.get()` with default
- `trust_by_tick` may be empty dict
- `snapshots` may be empty list
- `final_decision` may be None
- `brand_trust` dict may be empty
- `log.get("error")` — skip these logs in the persona table

---

## Acceptance Criteria

- [ ] `streamlit run app/streamlit_app.py` launches without ImportError
- [ ] "Journey Timeline" appears as third page in sidebar navigation
- [ ] When no results file exists: shows clear warning + run command
- [ ] When results exist: summary metrics, trust chart, decision distributions all render
- [ ] Per-persona drill-down table renders with filter controls
- [ ] Individual persona tick-by-tick trust chart renders
- [ ] Decision points listed per persona
- [ ] Reflection moments shown per persona
- [ ] No raw field names shown to user
- [ ] All None/empty states handled without crash
- [ ] Page 1 and Page 2 still work — no regressions
