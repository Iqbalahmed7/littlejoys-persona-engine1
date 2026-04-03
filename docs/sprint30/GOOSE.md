# Sprint 30 — Brief: GOOSE

**Role:** Decision logic / analysis scripts
**Model:** Grok-4-1-fast-reasoning
**Assignment:** `scripts/analyse_journey_results.py` — reads journey output, produces insight tables for LittleJoys business problems
**Est. duration:** 3-4 hours
**START:** Immediately (reads JSON output — does not depend on Cursor or Codex finishing)

---

## Files to Create

| Action | File |
|---|---|
| CREATE | `scripts/analyse_journey_results.py` |

## Do NOT Touch
- Any `src/` file
- Any test file
- `app/streamlit_app.py`

---

## Critical: Self-Verify Before Signalling Done

**After writing the script, run ALL of these before reporting complete:**

```bash
# 1. Syntax check
python3 -c "import ast; ast.parse(open('scripts/analyse_journey_results.py').read()); print('syntax OK')"

# 2. Import check
python3 -c "from scripts.analyse_journey_results import main; print('import OK')"

# 3. Function call check — this is the one that catches f-string entity bugs
python3 -c "
from scripts.analyse_journey_results import format_pct_bar
result = format_pct_bar('buy', 62.4, 103)
print('format_pct_bar:', repr(result))
assert 'buy' in result
print('function call: OK')
"
```

**Every `&#39;` must be `'`. Every `&lt;` must be `<`. Every `\"` inside string literals must be `"`.**
Check every f-string dictionary subscript. Check every format specifier like `{var:<15}`.

---

## What to Build

A standalone analysis script that:
1. Loads `journey_A_results.json` and/or `journey_B_results.json`
2. Produces insight tables directly answering the two LittleJoys business problems
3. Writes a markdown summary report

```python
#!/usr/bin/env python3
"""
analyse_journey_results.py — Extract business insights from journey simulation results.

Usage:
    python3 scripts/analyse_journey_results.py --journey A
    python3 scripts/analyse_journey_results.py --journey B
    python3 scripts/analyse_journey_results.py --journey A --journey B   # both

Output:
    Prints insight tables to stdout
    Writes data/population/journey_A_insights.md (or B)

Business problems addressed:
    Journey A → Problem 1: Why don't Nutrimix buyers reorder?
    Journey B → Problem 3: How many touchpoints convert Magnesium Gummies?
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

---

## Functions to Implement

### `format_pct_bar(label, pct, count) -> str`
Returns a formatted bar chart line. Used in all summary tables.
```
  buy              103  (62.4%)  ##############################
```

### `analyse_journey_A(data: dict) -> None`
Analyses `journey_A_results.json`. Prints and writes:

**Section 1: First Purchase Funnel**
- Decision distribution at tick 20 (first purchase)
- Top 5 drivers among buyers
- Top 5 objections among non-buyers

**Section 2: Reorder Analysis (the key insight)**
```
REORDER RATE AMONG FIRST-TIME BUYERS
======================================
Reordered (bought again at tick 60):   XX%   ######
Lapsed (did not reorder):              XX%   ###

TOP REASONS FOR REORDER:
  1. [driver]: XX
  2. [driver]: XX

TOP REASONS FOR LAPSE:
  1. [objection]: XX
  2. [objection]: XX

INSIGHT: The drop between first purchase (XX%) and reorder (XX%) is XX percentage
points. The primary lapse driver is [top objection] — suggesting LittleJoys should
[actionable implication].
```

**Section 3: Brand Trust Journey**
Print mean trust level at key ticks:
```
BRAND TRUST TRAJECTORY (mean across all personas):
  Day 1  (tick 0):  0.00  — zero awareness
  Day 8  (tick 8):  X.XX  — after price drop
  Day 12 (tick 12): X.XX  — after pediatrician
  Day 20 (tick 20): X.XX  ← FIRST PURCHASE DECISION
  Day 32 (tick 32): X.XX  — after competitor retargeting
  Day 38 (tick 38): X.XX  — pack running low
  Day 60 (tick 60): X.XX  ← REORDER DECISION
```

**Section 4: Reorderer vs Lapser Profile**
Compare decision styles, trust anchors, price sensitivity between those who reordered vs those who didn't.
```
REORDERER vs LAPSER PROFILE
  Decision style:
    Reorderers:  analytical=XX%  intuitive=XX%  social=XX%
    Lapsers:     analytical=XX%  intuitive=XX%  social=XX%
  Price sensitivity:
    Reorderers:  low=XX%  medium=XX%  high=XX%
    Lapsers:     low=XX%  medium=XX%  high=XX%
```

---

### `analyse_journey_B(data: dict) -> None`
Analyses `journey_B_results.json`. Prints and writes:

**Section 1: Conversion Funnel**
- How many personas reached the tick-35 decision?
- Decision distribution at tick 35 (first purchase)
- Top drivers + objections

**Section 2: Conversion Tick Analysis (the key insight)**
Which stimuli were most commonly cited in the reasoning trace just before the buy decision?
```
WHAT TIPPED THE DECISION (most cited stimulus in reasoning traces):
  Pediatrician follow-up (tick 32):  XX personas
  Mom influencer reel (tick 27):     XX personas
  Instagram ad (tick 22):            XX personas
  Google search (tick 18):           XX personas
  WhatsApp forward (tick 10):        XX personas
```

**Section 3: Post-trial Continuation Rate**
- Of those who bought at tick 35, how many continued at tick 45?
- Top reasons for continuation vs stopping

**Section 4: Non-converter Profile**
- What does a persona who didn't buy look like?
- Top objections from non-buyers

---

## Markdown Report Format

Write the full insight output to a markdown file:
- Journey A → `data/population/journey_A_insights.md`
- Journey B → `data/population/journey_B_insights.md`

Include a one-paragraph executive summary at the top of each:

**Journey A executive summary template:**
```
## Executive Summary

LittleJoys Nutrimix achieved a XX% first-purchase rate after a 20-day stimulus
sequence. However, only XX% of first-time buyers reordered at day 60 — a drop
of XX percentage points. The primary driver of lapse was [top objection]. Reorderers
were disproportionately [decision_style] personas with [trust_anchor] as their
primary trust source. The brand trust trajectory shows a XX-point decline between
day 20 and day 32, coinciding with competitor retargeting. Recommendation: introduce
a post-purchase reinforcement stimulus between days 25-35 to defend the trust level
before the reorder window opens.
```

**Journey B executive summary template:**
```
## Executive Summary

LittleJoys Magnesium Gummies converted XX% of personas to first trial after a
35-day awareness sequence. The most decisive stimulus was [top cited stimulus],
cited in XX% of buy decisions. Non-converters' primary objection was [top objection].
Of trial purchasers, XX% continued at day 45, suggesting [taste/outcome/price]
is [a barrier / not a barrier]. The minimum effective touchpoint sequence appears
to be [X] stimuli — personas who converted had encountered at least X awareness
touchpoints before the purchase decision.
```

Fill in the `[placeholders]` with actual computed values from the data.

---

## Handling Missing Output Files

If a journey results file doesn't exist yet (batch hasn't been run), print a clear message:
```
Journey A results not found at data/population/journey_A_results.json
Run: ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey A
```
And exit cleanly (exit code 0 — not an error, just not ready yet).

---

## Acceptance Criteria

- [ ] Syntax OK: `ast.parse()` passes
- [ ] Import OK: `from scripts.analyse_journey_results import main` works
- [ ] Function call OK: `format_pct_bar()` callable and returns correct string
- [ ] `--journey A` prints all 4 sections for Journey A
- [ ] `--journey B` prints all 4 sections for Journey B
- [ ] Reorder rate computed correctly (reorderers / first-time buyers × 100)
- [ ] Brand trust trajectory table shows values at key ticks
- [ ] Reorderer vs lapser profile comparison printed
- [ ] Markdown report written to correct path
- [ ] Executive summary filled with computed values (not placeholders)
- [ ] Missing results file handled gracefully
- [ ] No raw field names in user-facing output — human-readable labels only
- [ ] Exit code 0 on success
