# Sprint 27: GTM Marketing Mix & Temporal Simulation

**Assigned to:** Cursor (1 engineer)
**Priority:** High — blocks realistic new-product simulation
**Estimated scope:** 6 files, ~300 LoC net new

---

## Problem Statement

When a user runs base simulation for a **new product** (e.g., Magnesium Gummies, ProteinMix), the result shows **0% adoption**. This is unrealistic — in reality, products are launched with a GTM strategy: paid campaigns, influencer partnerships, pediatrician outreach, word-of-mouth seeding, and awareness ramps.

**Root cause:** New products are configured with `mode=SCENARIO_MODE_STATIC` and low `awareness_budget` (0.25). Static mode runs a single-pass funnel with no temporal awareness ramp — personas either adopt on Day 1 or never. With 0.25 awareness and 0.20 base awareness_level, almost nobody crosses the awareness threshold.

The existing temporal simulation (`run_temporal_simulation()`) already models monthly awareness growth, WOM propagation, and funnel conversion — but it's only enabled for Nutrimix 2-6.

## Solution: User-Configurable GTM + Temporal for All Products

### What the user should see (Page 2 — Problem & Simulation)

After selecting a business problem, before clicking "Run Simulation", add an expandable **"GTM Strategy"** panel:

```
▸ GTM Strategy (click to configure)
  ┌──────────────────────────────────────────────────────┐
  │  Simulation Duration     [3 mo ▼] [6 mo] [12 mo]    │
  │                                                       │
  │  Awareness Budget         [━━━━━━━●━━━] 0.55         │
  │                                                       │
  │  Channel Mix                                          │
  │    Instagram    [━━━━━━●━━━━] 0.35                   │
  │    YouTube      [━━━━●━━━━━━] 0.25                   │
  │    WhatsApp     [━━━●━━━━━━━] 0.20                   │
  │    Pediatrician [━━━●━━━━━━━] 0.20                   │
  │                                                       │
  │  Campaigns & Partnerships                             │
  │    ☑ Influencer campaign                              │
  │    ☐ Pediatrician endorsement                         │
  │    ☐ School partnership                               │
  │    ☐ Sports club partnership                          │
  │                                                       │
  │  Word-of-Mouth                                        │
  │    Organic WoM (WhatsApp/forums)  [━━━━●━━] 0.15    │
  │    Referral program boost         [━━●━━━━] 0.10     │
  │                                                       │
  │  Preset: [Organic Launch ▼]                           │
  │    Options: Organic Launch | Paid Blitz |             │
  │             Doctor-Led | Influencer-Heavy |            │
  │             Balanced | Custom                         │
  └──────────────────────────────────────────────────────┘
```

### Presets (one-click GTM strategies)

| Preset | awareness_budget | Channel Mix | Partnerships | WoM Boost | Use Case |
|--------|-----------------|-------------|--------------|-----------|----------|
| **Organic Launch** | 0.35 | WA 0.45, IG 0.30, YT 0.15, Ped 0.10 | influencer | 0.20 | Low-budget launch via mom communities |
| **Paid Blitz** | 0.75 | IG 0.45, YT 0.35, WA 0.10, Ped 0.10 | influencer | 0.05 | Aggressive paid + social push |
| **Doctor-Led** | 0.50 | Ped 0.50, IG 0.20, YT 0.15, WA 0.15 | pediatrician, school | 0.10 | Trust-first via medical authority |
| **Influencer-Heavy** | 0.60 | IG 0.50, YT 0.30, WA 0.10, Ped 0.10 | influencer | 0.15 | Influencer + social proof |
| **Balanced** | 0.55 | IG 0.30, YT 0.25, WA 0.25, Ped 0.20 | influencer, pediatrician | 0.12 | Even spread across channels |

### Referral / WoM Enhancement

Add a `referral_program_boost` field to `MarketingConfig`:
- When > 0, each existing adopter has an **additional** chance (on top of organic WoM) to bring in a new user each month
- Models: referral codes, share-and-earn, WhatsApp forwarding of discount links
- Transmitted via same WoM mechanism but with higher `transmission_rate`

---

## Implementation Plan

### Task 1: Switch all scenarios to temporal mode + add GTM fields

**File:** `src/decision/scenarios.py`

1. Add new fields to `MarketingConfig`:
   ```python
   referral_program_boost: UnitInterval = 0.0  # Additional WoM from referral program
   ```

2. Change magnesium_gummies and protein_mix from `SCENARIO_MODE_STATIC` → `SCENARIO_MODE_TEMPORAL`:
   ```python
   mode=SCENARIO_MODE_TEMPORAL,
   months=6,
   ```

3. Raise their default `awareness_budget` to 0.45 (still modest but non-zero adoption).

### Task 2: Add referral WoM to temporal simulation

**File:** `src/simulation/temporal.py`

In the monthly loop, after `propagate_wom()`:
```python
# Referral program boost (on top of organic WoM)
if scenario.marketing.referral_program_boost > 0:
    referral_deltas = propagate_wom(
        population, adopter_ids, month,
        transmission_rate=scenario.marketing.referral_program_boost,
        reach_min=1, reach_max=3,
    )
    for pid, delta in referral_deltas.items():
        awareness_boosts[pid] = min(1.0, awareness_boosts.get(pid, 0) + delta)
```

### Task 3: Add GTM configuration UI panel

**File:** `app/pages/2_problem.py`

After the user selects a business problem and before "Run Simulation", insert an `st.expander("GTM Strategy")` with:

1. **Duration selector**: `st.select_slider("Simulation Duration", [3, 6, 12], value=6)` → overrides `scenario.months`
2. **Awareness budget slider**: `st.slider("Awareness Budget", 0.0, 1.0, value=scenario.marketing.awareness_budget)`
3. **Channel mix sliders**: 4 sliders (Instagram, YouTube, WhatsApp, Pediatrician) with auto-normalization
4. **Campaign checkboxes**: influencer, pediatrician endorsement, school, sports club
5. **WoM sliders**: organic WoM strength, referral program boost
6. **Preset dropdown**: Populate from `GTM_PRESETS` dict, auto-fills all sliders on change

The UI values override the scenario's `MarketingConfig` before passing to `run_temporal_simulation()`.

### Task 4: Auto-normalize channel mix

**File:** `app/pages/2_problem.py` (helper function)

```python
def normalize_channel_mix(raw: dict[str, float]) -> dict[str, float]:
    total = sum(raw.values())
    if total == 0:
        return {k: 1.0 / len(raw) for k in raw}
    return {k: v / total for k, v in raw.items()}
```

Display a warning if user has all channels at 0.

### Task 5: Update cohort classifier for temporal mode

**File:** `src/analysis/cohort_classifier.py`

Ensure `classify_population()` uses temporal results (not just static funnel) when `mode=SCENARIO_MODE_TEMPORAL`. The current code already branches on mode — verify it works for magnesium_gummies after the mode switch.

### Task 6: Surface GTM config in Compare page context

**File:** `app/pages/9_compare.py`

When comparing two scenarios, show the GTM strategy used for each (awareness_budget, channel_mix, duration) so the user can see how different GTM strategies led to different adoption rates.

---

## File Change Matrix

| File | Changes | LoC |
|------|---------|-----|
| `src/decision/scenarios.py` | Add `referral_program_boost` to MarketingConfig, switch mag/protein to temporal, bump awareness_budget | ~15 |
| `src/simulation/temporal.py` | Add referral WoM propagation in monthly loop | ~20 |
| `app/pages/2_problem.py` | GTM Strategy expander with sliders, checkboxes, presets, normalization | ~150 |
| `src/analysis/cohort_classifier.py` | Verify temporal path for new scenarios (likely no changes needed) | ~5 |
| `app/pages/9_compare.py` | Show GTM config in comparison context | ~30 |
| `src/constants.py` | Add `GTM_PRESETS` dict with 5 preset configs | ~40 |
| **Total** | | **~260** |

---

## Acceptance Criteria

1. **User can configure GTM before simulation**: Expandable panel on Page 2 with presets and manual sliders
2. **Magnesium Gummies shows non-zero adoption**: With "Balanced" preset, expect 15-30% awareness and 5-15% trial after 6 months
3. **Channel mix normalizes**: Sliders auto-normalize to sum to 1.0
4. **Referral program works**: Setting referral_program_boost > 0 produces measurably higher adoption than 0
5. **Duration is configurable**: 3/6/12 month options produce visibly different funnel shapes
6. **Compare page shows GTM context**: Side-by-side GTM configs visible when comparing scenarios
7. **Existing Nutrimix flow unchanged**: Default GTM for nutrimix_2_6 matches current behavior (backward-compatible)

---

## What This Does NOT Include (Future Sprints)

- Campaign phasing/sequencing (Phase 1: organic → Phase 2: paid → Phase 3: partnerships)
- Budget allocation in rupees (CAC/LTV modeling)
- Competitor response modeling
- Seasonality effects
- A/B testing of GTM strategies within the simulation
- Offline campaign modeling (retail activations, sampling)
