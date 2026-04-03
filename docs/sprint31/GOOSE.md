# Sprint 31 — GOOSE Brief: journey_comparison.py

## Context
After running two different journey configurations, the LittleJoys team needs a script that
produces a clean side-by-side comparison — first purchase delta, reorder delta, top driver
shifts, trust trajectory overlay. This runs from CLI and writes a markdown report.

## Working directory
`/Users/admin/Documents/Simulatte Projects/1. LittleJoys`

## Task — Create `scripts/journey_comparison.py`

### File structure

```python
#!/usr/bin/env python3
"""
journey_comparison.py — Compare two journey simulation results side by side.

Usage:
    python3 scripts/journey_comparison.py \
        --file-a data/population/journey_A_results.json \
        --file-b data/population/journey_B_results.json \
        --label-a "Nutrimix Rs649" \
        --label-b "Nutrimix Rs549"

Output:
    Prints comparison table to stdout
    Writes data/population/comparison_{label_a}_vs_{label_b}.md
"""
```

### `ComparisonReport` dataclass

```python
@dataclass
class ComparisonReport:
    label_a: str
    label_b: str
    first_purchase_pct_a: float
    first_purchase_pct_b: float
    first_purchase_delta: float
    reorder_pct_a: float
    reorder_pct_b: float
    reorder_delta: float
    top_drivers_a: list[tuple[str, int]]   # top 5 (driver, count) for scenario A reorder
    top_drivers_b: list[tuple[str, int]]
    top_objections_a: list[tuple[str, int]]
    top_objections_b: list[tuple[str, int]]
    trust_trajectory_a: dict[int, float]   # tick -> mean trust
    trust_trajectory_b: dict[int, float]
    personas_a: int
    personas_b: int
    errors_a: int
    errors_b: int
```

### `compare_journeys(result_a, result_b, label_a, label_b) -> ComparisonReport`

Extracts from the `aggregate` key of each result dict:
- `first_decision_distribution` → sum `buy` + `trial` pcts for first_purchase_pct
- `reorder_rate_pct` → reorder_pct
- `second_decision_drivers` → top_drivers (sorted by count desc, top 5)
- `second_decision_objections` → top_objections (sorted by count desc, top 5)
- `trust_by_tick` → trust_trajectory (keys cast to int)

### `print_comparison(report: ComparisonReport) -> None`

Print this exact layout:

```
============================================================
JOURNEY COMPARISON
============================================================
                         Nutrimix Rs649   Nutrimix Rs549   Delta
------------------------------------------------------------
Personas run                        200              200       0
Errors                                0                0       0
First purchase %                   46.0%            52.3%  +6.3pp
Reorder rate %                     82.6%            91.2%  +8.6pp
------------------------------------------------------------
TOP REORDER DRIVERS
  Scenario A (Nutrimix Rs649):
    1. within budget comfort zone: 9
    2. habit formation after 5 weeks: 5
    ...
  Scenario B (Nutrimix Rs549):
    1. lower price removes friction: 12
    ...
------------------------------------------------------------
TOP LAPSE OBJECTIONS
  Scenario A:
    1. no discount available: 5
    ...
  Scenario B:
    1. results only okay: 3
    ...
============================================================
```

Use f-strings with proper alignment. Delta is formatted as `+X.Xpp` or `-X.Xpp`.

### `write_markdown(report: ComparisonReport, out_path: Path) -> None`

Write the same content as markdown with `##` headers. Include an executive summary paragraph:

> "Reducing price from Rs {A_price} to Rs {B_price} moved the first purchase rate by
> {delta:+.1f}pp and reorder rate by {reorder_delta:+.1f}pp. The primary driver shift
> was from '{top_driver_a}' to '{top_driver_b}'."

Note: prices are inferred from the label strings if not available in the data.

### `main() -> int`

```python
parser.add_argument("--file-a", required=True)
parser.add_argument("--file-b", required=True)
parser.add_argument("--label-a", default="Scenario A")
parser.add_argument("--label-b", default="Scenario B")
```

Load both JSON files, call `compare_journeys`, call `print_comparison`, call `write_markdown`,
return 0.

## Self-verify requirements (MANDATORY)

Add a `--self-verify` flag. When passed:

```python
if args.self_verify:
    import ast
    ast.parse(open(__file__).read())
    print("syntax OK")

    # ComparisonReport instantiates with empty/zero values
    report = ComparisonReport(
        label_a="A", label_b="B",
        first_purchase_pct_a=0.0, first_purchase_pct_b=0.0, first_purchase_delta=0.0,
        reorder_pct_a=0.0, reorder_pct_b=0.0, reorder_delta=0.0,
        top_drivers_a=[], top_drivers_b=[],
        top_objections_a=[], top_objections_b=[],
        trust_trajectory_a={}, trust_trajectory_b={},
        personas_a=0, personas_b=0, errors_a=0, errors_b=0,
    )
    print("ComparisonReport instantiation OK")

    # print_comparison runs without error on empty report
    print_comparison(report)
    print("print_comparison OK")

    print("ALL SELF-VERIFY CHECKS PASSED")
    return 0
```

Run before delivery: `python3 scripts/journey_comparison.py --self-verify`

## CRITICAL: No HTML entities
Write all strings using real Python quotes (" and ').
Do NOT use &quot; &#39; &lt; &gt; anywhere in the file.
After writing, verify: `python3 -c "import ast; ast.parse(open('scripts/journey_comparison.py').read()); print('OK')"`
