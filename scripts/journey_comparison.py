#!/usr/bin/env python3
"""
journey_comparison.py -- Compare two journey simulation results side by side.

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
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


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
    top_drivers_a: list
    top_drivers_b: list
    top_objections_a: list
    top_objections_b: list
    trust_trajectory_a: dict
    trust_trajectory_b: dict
    personas_a: int
    personas_b: int
    errors_a: int
    errors_b: int


def _parse_price_from_label(label: str) -> int:
    """Infer price from label like 'Nutrimix Rs649' -> 649."""
    match = re.search(r'Rs(\d+)', label)
    return int(match.group(1)) if match else 0


def _fp_pct(agg: dict) -> float:
    """Sum buy + trial percentages from first_decision_distribution."""
    dist = agg.get("first_decision_distribution", {})
    buy = dist.get("buy") or {}
    trial = dist.get("trial") or {}
    if isinstance(buy, dict):
        return float(buy.get("pct", 0) or 0) + float((trial.get("pct", 0) or 0))
    # Fallback: already a float
    return float(buy) + float(trial)


def _top_items(d, n: int = 5) -> list:
    """Convert dict[str, int] or list to sorted list of (key, count) tuples."""
    if isinstance(d, dict):
        return sorted(d.items(), key=lambda x: -x[1])[:n]
    if isinstance(d, list):
        return d[:n]
    return []


def compare_journeys(
    result_a: dict, result_b: dict, label_a: str, label_b: str
) -> ComparisonReport:
    agg_a = result_a.get("aggregate", {}) or {}
    agg_b = result_b.get("aggregate", {}) or {}

    fp_a = _fp_pct(agg_a)
    fp_b = _fp_pct(agg_b)

    reorder_a = float(agg_a.get("reorder_rate_pct", 0) or 0)
    reorder_b = float(agg_b.get("reorder_rate_pct", 0) or 0)

    trust_a = {int(k): float(v) for k, v in (agg_a.get("trust_by_tick") or {}).items()}
    trust_b = {int(k): float(v) for k, v in (agg_b.get("trust_by_tick") or {}).items()}

    return ComparisonReport(
        label_a=label_a,
        label_b=label_b,
        first_purchase_pct_a=fp_a,
        first_purchase_pct_b=fp_b,
        first_purchase_delta=fp_b - fp_a,
        reorder_pct_a=reorder_a,
        reorder_pct_b=reorder_b,
        reorder_delta=reorder_b - reorder_a,
        top_drivers_a=_top_items(agg_a.get("second_decision_drivers", {})),
        top_drivers_b=_top_items(agg_b.get("second_decision_drivers", {})),
        top_objections_a=_top_items(agg_a.get("second_decision_objections", {})),
        top_objections_b=_top_items(agg_b.get("second_decision_objections", {})),
        trust_trajectory_a=trust_a,
        trust_trajectory_b=trust_b,
        personas_a=int(agg_a.get("total_personas", result_a.get("total_personas", 0)) or 0),
        personas_b=int(agg_b.get("total_personas", result_b.get("total_personas", 0)) or 0),
        errors_a=int(agg_a.get("errors", 0) or 0),
        errors_b=int(agg_b.get("errors", 0) or 0),
    )


def _delta_str(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}pp"


def print_comparison(report: ComparisonReport) -> None:
    w = 16
    print("=" * 62)
    print("JOURNEY COMPARISON")
    print("=" * 62)
    print(f"  {'Metric':<28} {report.label_a:>14} {report.label_b:>14}  Delta")
    print("-" * 62)
    print(f"  {'Personas run':<28} {report.personas_a:>14} {report.personas_b:>14}")
    print(f"  {'Errors':<28} {report.errors_a:>14} {report.errors_b:>14}")
    print(f"  {'First purchase %':<28} {report.first_purchase_pct_a:>13.1f}% {report.first_purchase_pct_b:>13.1f}%  {_delta_str(report.first_purchase_delta)}")
    print(f"  {'Reorder rate %':<28} {report.reorder_pct_a:>13.1f}% {report.reorder_pct_b:>13.1f}%  {_delta_str(report.reorder_delta)}")
    print("-" * 62)

    print()
    print("TOP REORDER DRIVERS")
    print(f"  {report.label_a}:")
    if report.top_drivers_a:
        for i, (driver, count) in enumerate(report.top_drivers_a, 1):
            print(f"    {i}. {driver.replace('_', ' ')}: {count}")
    else:
        print("    (none)")
    print(f"  {report.label_b}:")
    if report.top_drivers_b:
        for i, (driver, count) in enumerate(report.top_drivers_b, 1):
            print(f"    {i}. {driver.replace('_', ' ')}: {count}")
    else:
        print("    (none)")

    print()
    print("TOP LAPSE OBJECTIONS")
    print(f"  {report.label_a}:")
    if report.top_objections_a:
        for i, (obj, count) in enumerate(report.top_objections_a, 1):
            print(f"    {i}. {obj.replace('_', ' ')}: {count}")
    else:
        print("    (none)")
    print(f"  {report.label_b}:")
    if report.top_objections_b:
        for i, (obj, count) in enumerate(report.top_objections_b, 1):
            print(f"    {i}. {obj.replace('_', ' ')}: {count}")
    else:
        print("    (none)")

    print()
    if report.trust_trajectory_a or report.trust_trajectory_b:
        print("TRUST TRAJECTORY (key ticks)")
        all_ticks = sorted(set(report.trust_trajectory_a) | set(report.trust_trajectory_b))
        for t in all_ticks:
            ta = report.trust_trajectory_a.get(t)
            tb = report.trust_trajectory_b.get(t)
            ta_s = f"{ta:.2f}" if ta is not None else "n/a"
            tb_s = f"{tb:.2f}" if tb is not None else "n/a"
            print(f"  Day {t:<3}: {report.label_a}={ta_s}  {report.label_b}={tb_s}")

    print("=" * 62)


def write_markdown(report: ComparisonReport, out_path: Path) -> None:
    price_a = _parse_price_from_label(report.label_a)
    price_b = _parse_price_from_label(report.label_b)
    top_driver_a = report.top_drivers_a[0][0].replace("_", " ") if report.top_drivers_a else "unknown"
    top_driver_b = report.top_drivers_b[0][0].replace("_", " ") if report.top_drivers_b else "unknown"

    if price_a and price_b and price_a != price_b:
        exec_summary = (
            f"Reducing price from Rs {price_a} to Rs {price_b} moved the first purchase rate by "
            f"{report.first_purchase_delta:+.1f}pp and reorder rate by {report.reorder_delta:+.1f}pp. "
            f"The primary driver shift was from '{top_driver_a}' to '{top_driver_b}'."
        )
    else:
        exec_summary = (
            f"Comparing {report.label_a} vs {report.label_b}: "
            f"first purchase delta {report.first_purchase_delta:+.1f}pp, "
            f"reorder delta {report.reorder_delta:+.1f}pp."
        )

    lines = [
        f"# Journey Comparison: {report.label_a} vs {report.label_b}",
        "",
        "## Executive Summary",
        "",
        f"> {exec_summary}",
        "",
        "## Metrics",
        "",
        f"| Metric | {report.label_a} | {report.label_b} | Delta |",
        "|--------|---------|---------|-------|",
        f"| Personas run | {report.personas_a} | {report.personas_b} | -- |",
        f"| Errors | {report.errors_a} | {report.errors_b} | -- |",
        f"| First purchase % | {report.first_purchase_pct_a:.1f}% | {report.first_purchase_pct_b:.1f}% | {_delta_str(report.first_purchase_delta)} |",
        f"| Reorder rate % | {report.reorder_pct_a:.1f}% | {report.reorder_pct_b:.1f}% | {_delta_str(report.reorder_delta)} |",
        "",
        "## Top Reorder Drivers",
        "",
        f"**{report.label_a}:**",
    ]
    for i, (drv, cnt) in enumerate(report.top_drivers_a, 1):
        lines.append(f"{i}. {drv.replace('_', ' ')}: {cnt}")
    lines += ["", f"**{report.label_b}:**"]
    for i, (drv, cnt) in enumerate(report.top_drivers_b, 1):
        lines.append(f"{i}. {drv.replace('_', ' ')}: {cnt}")

    lines += ["", "## Top Lapse Objections", "", f"**{report.label_a}:**"]
    for i, (obj, cnt) in enumerate(report.top_objections_a, 1):
        lines.append(f"{i}. {obj.replace('_', ' ')}: {cnt}")
    lines += ["", f"**{report.label_b}:**"]
    for i, (obj, cnt) in enumerate(report.top_objections_b, 1):
        lines.append(f"{i}. {obj.replace('_', ' ')}: {cnt}")

    if report.trust_trajectory_a or report.trust_trajectory_b:
        lines += ["", "## Trust Trajectory", "",
                  f"| Tick | {report.label_a} | {report.label_b} |",
                  "|------|---------|---------|"]
        for t in sorted(set(report.trust_trajectory_a) | set(report.trust_trajectory_b)):
            ta = report.trust_trajectory_a.get(t)
            tb = report.trust_trajectory_b.get(t)
            lines.append(f"| {t} | {ta:.2f if ta is not None else 'n/a'} | {tb:.2f if tb is not None else 'n/a'} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    print(f"\nMarkdown report written: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two journey simulation results.")
    parser.add_argument("--file-a", required=False, help="Path to scenario A results JSON")
    parser.add_argument("--file-b", required=False, help="Path to scenario B results JSON")
    parser.add_argument("--label-a", default="Scenario A")
    parser.add_argument("--label-b", default="Scenario B")
    parser.add_argument("--self-verify", action="store_true")
    args = parser.parse_args()

    if args.self_verify:
        import ast
        ast.parse(open(__file__).read())
        print("syntax OK")

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

        print_comparison(report)
        print("print_comparison OK")

        print("ALL SELF-VERIFY CHECKS PASSED")
        return 0

    if not args.file_a or not args.file_b:
        parser.print_help()
        return 1

    path_a = Path(args.file_a).resolve()
    path_b = Path(args.file_b).resolve()
    if not path_a.exists():
        print(f"File A not found: {path_a}")
        return 1
    if not path_b.exists():
        print(f"File B not found: {path_b}")
        return 1

    result_a = json.loads(path_a.read_text())
    result_b = json.loads(path_b.read_text())

    report = compare_journeys(result_a, result_b, args.label_a, args.label_b)
    print_comparison(report)

    safe_a = re.sub(r"[^a-zA-Z0-9]", "_", args.label_a.lower())
    safe_b = re.sub(r"[^a-zA-Z0-9]", "_", args.label_b.lower())
    out_path = PROJECT_ROOT / "data" / "population" / f"comparison_{safe_a}_vs_{safe_b}.md"
    write_markdown(report, out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
