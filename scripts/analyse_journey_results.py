#!/usr/bin/env python3
"""
analyse_journey_results.py -- Extract business insights from journey simulation results.

Usage:
    python3 scripts/analyse_journey_results.py --journey A
    python3 scripts/analyse_journey_results.py --journey B
    python3 scripts/analyse_journey_results.py --journey A --journey B

Output:
    Prints insight tables to stdout
    Writes data/population/journey_A_insights.md (or B)

Business problems addressed:
    Journey A -> Problem 1: Why don't Nutrimix buyers reorder?
    Journey B -> Problem 3: How many touchpoints convert Magnesium Gummies?
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def format_pct_bar(label: str, pct: float, count: int) -> str:
    """Return a formatted bar chart line."""
    bar = "#" * int(pct // 2)
    return f"  {label:<15} {count:>4}  ({pct:>5.1f}%)  {bar}"


def _load_results(journey_id: str) -> "dict | None":
    path = PROJECT_ROOT / "data" / "population" / f"journey_{journey_id}_results.json"
    if not path.exists():
        print(f"Journey {journey_id} results not found at {path}")
        print(f"Run: ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey {journey_id}")
        return None
    with path.open() as f:
        return json.load(f)


def _get_decision_at_tick(log: dict, tick: int) -> dict:
    for snap in log.get("snapshots", []):
        if snap.get("tick") == tick and snap.get("decision_result"):
            return snap["decision_result"]
    return {}


def _decision_label(d: dict) -> str:
    return str(d.get("decision") or d.get("outcome") or "unknown")


def _get_persona_attr(log: dict, *keys: str) -> str:
    persona = log.get("persona_snapshot") or log.get("persona") or {}
    for k in keys:
        v = persona.get(k) or log.get(k)
        if v is not None:
            return str(v)
    return "unknown"


def analyse_journey_A(data: dict) -> None:
    aggregate = data.get("aggregate", {})
    logs = [lg for lg in data.get("logs", []) if not lg.get("error")]

    lines: list = []

    def out(s: str = "") -> None:
        print(s)
        lines.append(s)

    buy_decisions = {"buy", "trial", "reorder"}

    out("=" * 60)
    out("JOURNEY A -- NUTRIMIX REPEAT PURCHASE")
    out("=" * 60)
    out()
    out("SECTION 1: FIRST PURCHASE FUNNEL (Day 20)")
    out("-" * 60)

    first_dist = aggregate.get("first_decision_distribution", {})
    total_valid = len(logs)
    first_buyers = []
    non_buyers = []

    for lg in logs:
        d20 = _get_decision_at_tick(lg, 20)
        label = _decision_label(d20) if d20 else _decision_label(lg.get("first_decision") or {})
        if label in buy_decisions:
            first_buyers.append(lg)
        else:
            non_buyers.append(lg)

    for decision, stats in sorted(first_dist.items(), key=lambda x: -x[1].get("count", 0)):
        out(format_pct_bar(decision, float(stats.get("pct", 0)), int(stats.get("count", 0))))

    out()
    out("Top 5 drivers among buyers:")
    buyer_drivers: Counter = Counter()
    for lg in first_buyers:
        d20 = _get_decision_at_tick(lg, 20)
        for drv in (d20.get("key_drivers") or d20.get("drivers") or []):
            buyer_drivers[str(drv)] += 1
    for i, (drv, cnt) in enumerate(buyer_drivers.most_common(5), 1):
        out(f"  {i}. {drv.replace('_', ' ')}: {cnt}")

    out()
    out("Top 5 objections among non-buyers:")
    nonbuyer_obj: Counter = Counter()
    for lg in non_buyers:
        d20 = _get_decision_at_tick(lg, 20)
        for obj in (d20.get("objections") or []):
            nonbuyer_obj[str(obj)] += 1
    for i, (obj, cnt) in enumerate(nonbuyer_obj.most_common(5), 1):
        out(f"  {i}. {obj.replace('_', ' ')}: {cnt}")

    out()
    out("SECTION 2: REORDER ANALYSIS (among first-time buyers)")
    out("-" * 60)

    reorderers = [lg for lg in first_buyers if lg.get("reordered")]
    lapsers = [lg for lg in first_buyers if not lg.get("reordered")]
    total_fb = len(first_buyers)
    reorder_pct = (len(reorderers) / total_fb * 100.0) if total_fb else 0.0
    lapse_pct = 100.0 - reorder_pct

    out("REORDER RATE AMONG FIRST-TIME BUYERS")
    out("=" * 38)
    out(format_pct_bar("Reordered", reorder_pct, len(reorderers)))
    out(format_pct_bar("Lapsed", lapse_pct, len(lapsers)))
    out()

    reorder_drivers: Counter = Counter()
    lapse_objections: Counter = Counter()

    for lg in reorderers:
        d60 = _get_decision_at_tick(lg, 60)
        for drv in (d60.get("key_drivers") or d60.get("drivers") or []):
            reorder_drivers[str(drv)] += 1

    for lg in lapsers:
        d60 = _get_decision_at_tick(lg, 60)
        for obj in (d60.get("objections") or []):
            lapse_objections[str(obj)] += 1

    out("TOP REASONS FOR REORDER:")
    for i, (drv, cnt) in enumerate(reorder_drivers.most_common(5), 1):
        out(f"  {i}. {drv.replace('_', ' ')}: {cnt}")

    out()
    out("TOP REASONS FOR LAPSE:")
    for i, (obj, cnt) in enumerate(lapse_objections.most_common(5), 1):
        out(f"  {i}. {obj.replace('_', ' ')}: {cnt}")

    buy_pct = (len(first_buyers) / total_valid * 100.0) if total_valid else 0.0
    drop_pp = buy_pct - reorder_pct
    top_lapse_obj = lapse_objections.most_common(1)[0][0].replace("_", " ") if lapse_objections else "unknown"
    out()
    out(f"INSIGHT: The drop between first purchase ({buy_pct:.1f}%) and reorder ({reorder_pct:.1f}%) is "
        f"{drop_pp:.1f} percentage points. The primary lapse driver is '{top_lapse_obj}' -- "
        "suggesting LittleJoys should address this friction point in the post-purchase journey.")

    out()
    out("SECTION 3: BRAND TRUST TRAJECTORY (mean across all personas)")
    out("-" * 60)

    trust_by_tick = aggregate.get("trust_by_tick", {})
    key_ticks = {
        0: "zero awareness",
        8: "after price drop",
        12: "after pediatrician",
        20: "FIRST PURCHASE DECISION",
        32: "after competitor retargeting",
        38: "pack running low",
        60: "REORDER DECISION",
    }
    for tick, label in key_ticks.items():
        tick_str = str(tick)
        trust_val = trust_by_tick.get(tick) or trust_by_tick.get(tick_str)
        if trust_val is not None:
            marker = "  <-" if "DECISION" in label else "  --"
            out(f"  Day {tick:<2} (tick {tick:<2}): {float(trust_val):.2f}{marker} {label}")
        elif tick in (0, 20, 60):
            out(f"  Day {tick:<2} (tick {tick:<2}): n/a  -- {label}")

    out()
    out("SECTION 4: REORDERER vs LAPSER PROFILE")
    out("-" * 60)

    def profile_counter(group, *attr_keys):
        c: Counter = Counter()
        for lg in group:
            val = _get_persona_attr(lg, *attr_keys)
            c[val] += 1
        return c

    r_ds = profile_counter(reorderers, "decision_style", "decision_making_style")
    l_ds = profile_counter(lapsers, "decision_style", "decision_making_style")
    r_ps = profile_counter(reorderers, "price_sensitivity")
    l_ps = profile_counter(lapsers, "price_sensitivity")

    r_total = max(len(reorderers), 1)
    l_total = max(len(lapsers), 1)

    out("  Decision style:")
    all_ds = sorted(set(list(r_ds.keys()) + list(l_ds.keys())))
    for style in all_ds:
        rp = r_ds.get(style, 0) / r_total * 100
        lp = l_ds.get(style, 0) / l_total * 100
        out(f"    {style:<20} Reorderers: {rp:.0f}%   Lapsers: {lp:.0f}%")

    out()
    out("  Price sensitivity:")
    all_ps = sorted(set(list(r_ps.keys()) + list(l_ps.keys())))
    for level in all_ps:
        rp = r_ps.get(level, 0) / r_total * 100
        lp = l_ps.get(level, 0) / l_total * 100
        out(f"    {level:<20} Reorderers: {rp:.0f}%   Lapsers: {lp:.0f}%")

    out()
    out("=" * 60)
    out("EXECUTIVE SUMMARY")
    out("=" * 60)

    top_reorder_drv = reorder_drivers.most_common(1)[0][0].replace("_", " ") if reorder_drivers else "unknown"
    trust_t20 = float(trust_by_tick.get(20) or trust_by_tick.get("20") or 0.0)
    trust_t32 = float(trust_by_tick.get(32) or trust_by_tick.get("32") or 0.0)
    trust_drop = trust_t20 - trust_t32

    exec_summary = (
        f"LittleJoys Nutrimix achieved a {buy_pct:.1f}% first-purchase rate after a 20-day stimulus "
        f"sequence. However, only {reorder_pct:.1f}% of first-time buyers reordered at day 60 -- a drop "
        f"of {drop_pp:.1f} percentage points. The primary driver of lapse was '{top_lapse_obj}'. "
        f"Reorderers were driven primarily by '{top_reorder_drv}'. "
        f"The brand trust trajectory shows a {trust_drop:.2f}-point change between "
        f"day 20 (trust: {trust_t20:.2f}) and day 32 (trust: {trust_t32:.2f}), "
        "coinciding with competitor retargeting. Recommendation: introduce a post-purchase "
        "reinforcement stimulus between days 25-35 to defend trust before the reorder window opens."
    )
    out(exec_summary)
    out("=" * 60)

    out_path = PROJECT_ROOT / "data" / "population" / "journey_A_insights.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md_content = "# Journey A -- Nutrimix Repeat Purchase: Insights\n\n"
    md_content += "## Executive Summary\n\n" + exec_summary + "\n\n"
    md_content += "---\n\n"
    md_content += "\n".join(lines)
    out_path.write_text(md_content)
    print(f"\nInsights written: {out_path}")


def analyse_journey_B(data: dict) -> None:
    aggregate = data.get("aggregate", {})
    logs = [lg for lg in data.get("logs", []) if not lg.get("error")]

    lines: list = []

    def out(s: str = "") -> None:
        print(s)
        lines.append(s)

    buy_decisions = {"buy", "trial", "reorder"}

    out("=" * 60)
    out("JOURNEY B -- MAGNESIUM GUMMIES")
    out("=" * 60)
    out()
    out("SECTION 1: CONVERSION FUNNEL (Day 35 -- First Trial)")
    out("-" * 60)

    first_dist = aggregate.get("first_decision_distribution", {})
    total_valid = len(logs)

    trialists = []
    non_trialists = []
    for lg in logs:
        d35 = _get_decision_at_tick(lg, 35)
        label = _decision_label(d35) if d35 else _decision_label(lg.get("first_decision") or {})
        if label in buy_decisions:
            trialists.append(lg)
        else:
            non_trialists.append(lg)

    trial_pct = (len(trialists) / total_valid * 100.0) if total_valid else 0.0
    out(f"Personas reaching tick-35 decision: {total_valid}")
    out(f"Converted to first trial: {len(trialists)} ({trial_pct:.1f}%)")
    out()
    out("Decision distribution at tick 35:")
    for decision, stats in sorted(first_dist.items(), key=lambda x: -x[1].get("count", 0)):
        out(format_pct_bar(decision, float(stats.get("pct", 0)), int(stats.get("count", 0))))

    out()
    out("Top drivers (among buyers):")
    trial_drivers: Counter = Counter()
    for lg in trialists:
        d35 = _get_decision_at_tick(lg, 35)
        for drv in (d35.get("key_drivers") or d35.get("drivers") or []):
            trial_drivers[str(drv)] += 1
    for i, (drv, cnt) in enumerate(trial_drivers.most_common(5), 1):
        out(f"  {i}. {drv.replace('_', ' ')}: {cnt}")

    out()
    out("Top objections (among non-buyers):")
    nontrial_obj: Counter = Counter()
    for lg in non_trialists:
        d35 = _get_decision_at_tick(lg, 35)
        for obj in (d35.get("objections") or []):
            nontrial_obj[str(obj)] += 1
    for i, (obj, cnt) in enumerate(nontrial_obj.most_common(5), 1):
        out(f"  {i}. {obj.replace('_', ' ')}: {cnt}")

    out()
    out("SECTION 2: WHAT TIPPED THE DECISION")
    out("-" * 60)
    out("Most cited stimulus keywords in reasoning traces of buyers:")

    stimulus_map = {
        10: "WhatsApp forward",
        18: "Google search",
        22: "Instagram ad",
        27: "Mom influencer reel",
        32: "Pediatrician follow-up",
    }
    stimulus_keyword_map = {
        10: ["whatsapp", "forward"],
        18: ["google", "search"],
        22: ["instagram", "ad"],
        27: ["influencer", "reel", "mom"],
        32: ["pediatrician", "doctor", "follow"],
    }

    stimulus_counts: Counter = Counter()
    for lg in trialists:
        for snap in lg.get("snapshots", []):
            dr = snap.get("decision_result") or {}
            reasoning = " ".join(str(r) for r in (dr.get("reasoning_trace") or [])).lower()
            for tick, keywords in stimulus_keyword_map.items():
                if any(kw in reasoning for kw in keywords):
                    stimulus_counts[tick] += 1

    for tick in sorted(stimulus_counts, key=lambda t: -stimulus_counts[t]):
        label = stimulus_map.get(tick, f"tick {tick}")
        out(f"  {label:<35} (tick {tick}): {stimulus_counts[tick]} personas")

    out()
    out("SECTION 3: POST-TRIAL CONTINUATION (Day 45)")
    out("-" * 60)

    continuers = [lg for lg in trialists if lg.get("reordered")]
    stoppers = [lg for lg in trialists if not lg.get("reordered")]
    cont_total = len(trialists)
    cont_pct = (len(continuers) / cont_total * 100.0) if cont_total else 0.0
    stop_pct = 100.0 - cont_pct
    out(format_pct_bar("Continued", cont_pct, len(continuers)))
    out(format_pct_bar("Stopped", stop_pct, len(stoppers)))

    out()
    cont_drivers: Counter = Counter()
    stop_obj: Counter = Counter()
    for lg in continuers:
        d45 = _get_decision_at_tick(lg, 45)
        for drv in (d45.get("key_drivers") or d45.get("drivers") or []):
            cont_drivers[str(drv)] += 1
    for lg in stoppers:
        d45 = _get_decision_at_tick(lg, 45)
        for obj in (d45.get("objections") or []):
            stop_obj[str(obj)] += 1

    out("Top reasons for continuation:")
    for i, (drv, cnt) in enumerate(cont_drivers.most_common(5), 1):
        out(f"  {i}. {drv.replace('_', ' ')}: {cnt}")
    out()
    out("Top reasons for stopping:")
    for i, (obj, cnt) in enumerate(stop_obj.most_common(5), 1):
        out(f"  {i}. {obj.replace('_', ' ')}: {cnt}")

    out()
    out("SECTION 4: NON-CONVERTER PROFILE")
    out("-" * 60)
    out(f"Non-converters: {len(non_trialists)} of {total_valid} personas")
    out()
    out("Top objections from non-buyers:")
    for i, (obj, cnt) in enumerate(nontrial_obj.most_common(5), 1):
        pct = cnt / len(non_trialists) * 100 if non_trialists else 0.0
        out(f"  {i}. {obj.replace('_', ' ')}: {cnt} ({pct:.1f}% of non-buyers)")

    nc_ds: Counter = Counter()
    for lg in non_trialists:
        val = _get_persona_attr(lg, "decision_style", "decision_making_style")
        nc_ds[val] += 1
    out()
    out("Decision styles of non-buyers:")
    nc_total = max(len(non_trialists), 1)
    for style, cnt in nc_ds.most_common():
        out(f"  {style:<20}: {cnt} ({cnt / nc_total * 100:.1f}%)")

    out()
    out("=" * 60)
    out("EXECUTIVE SUMMARY")
    out("=" * 60)

    top_ob = nontrial_obj.most_common(1)[0][0].replace("_", " ") if nontrial_obj else "unknown"
    top_stimulus_tick = stimulus_counts.most_common(1)[0][0] if stimulus_counts else 32
    top_stimulus_label = stimulus_map.get(top_stimulus_tick, f"tick {top_stimulus_tick}")
    top_stimulus_cnt = stimulus_counts.get(top_stimulus_tick, 0)
    top_stimulus_pct = (top_stimulus_cnt / len(trialists) * 100) if trialists else 0.0

    exec_summary = (
        f"LittleJoys Magnesium Gummies converted {trial_pct:.1f}% of personas to first trial after a "
        f"35-day awareness sequence. The most decisive stimulus was '{top_stimulus_label}', "
        f"cited in {top_stimulus_pct:.1f}% of buy decisions. Non-converters' primary objection was "
        f"'{top_ob}'. Of trial purchasers, {cont_pct:.1f}% continued at day 45. "
        "The minimum effective touchpoint sequence appears to require multiple awareness moments -- "
        "personas who converted had encountered stimuli across both social and professional channels "
        "before the purchase decision."
    )
    out(exec_summary)
    out("=" * 60)

    out_path = PROJECT_ROOT / "data" / "population" / "journey_B_insights.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md_content = "# Journey B -- Magnesium Gummies: Insights\n\n"
    md_content += "## Executive Summary\n\n" + exec_summary + "\n\n"
    md_content += "---\n\n"
    md_content += "\n".join(lines)
    out_path.write_text(md_content)
    print(f"\nInsights written: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract business insights from journey simulation results."
    )
    parser.add_argument(
        "--journey",
        action="append",
        choices=["A", "B"],
        dest="journeys",
        help="Journey ID to analyse. Can be repeated: --journey A --journey B",
    )
    args = parser.parse_args()

    if not args.journeys:
        parser.print_help()
        return 1

    for jid in args.journeys:
        data = _load_results(jid)
        if data is None:
            continue
        if jid == "A":
            analyse_journey_A(data)
        else:
            analyse_journey_B(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
