# Sprint 28 — Brief: OPENCODE

**Role:** Utility scripting / lightweight tooling
**Model:** GPT-5.4 Nano
**Assignment:** Two scripts only. Part 1 (exports) is already done.
**Est. duration:** 2-3 hours

---

## Status

| Part | Status | Notes |
|---|---|---|
| Part 1 — `src/agents/__init__.py` | ✅ DONE | Already written and verified. Do not touch. |
| Part 2 — `scripts/validate_personas.py` | 🔴 TODO | Run immediately |
| Part 3 — `scripts/run_perception_sample.py` | 🔴 TODO | Needs `ANTHROPIC_API_KEY` |

---

## Files to Create

| Action | File |
|---|---|
| CREATE | `scripts/validate_personas.py` |
| CREATE | `scripts/run_perception_sample.py` |

## Do NOT Touch

- `src/agents/__init__.py` — already done, do not overwrite
- Any file in `src/agents/`
- `src/taxonomy/schema.py`
- Any test file

---

## Verify imports first (sanity check before starting)

```bash
python3 -c "from src.agents import CognitiveAgent, MemoryManager, PerceptionResult, DecisionResult, ConstraintChecker, ConstraintViolation, EmbeddingCache; print('All 7 OK')"
python3 -c "from src.agents import ConstraintChecker; print(len(ConstraintChecker()._rules), 'rules')"
```

Both must print OK / 30 before proceeding.

---

## Part 2: `scripts/validate_personas.py`

Runs `ConstraintChecker` against every persona in `data/population/` and writes a
violations report to `data/population/constraint_violations_report.json`.

**This is the Sprint 28 gate output.** The hard-violation count determines whether
Sprint 29 starts on clean data or needs a regeneration pass first.

```python
#!/usr/bin/env python3
"""
validate_personas.py — Run ConstraintChecker against all 200 generated personas.

Usage:
    python3 scripts/validate_personas.py
    python3 scripts/validate_personas.py --input data/population/personas.json
    python3 scripts/validate_personas.py --hard-only
    python3 scripts/validate_personas.py --fix-report

Output:
    data/population/constraint_violations_report.json   (always)
    data/population/personas_to_regenerate.json         (with --fix-report)
    Summary table printed to stdout
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.constraint_checker import ConstraintChecker
from src.taxonomy.schema import Persona


def load_personas(input_path: Path | None) -> list[tuple[str, Persona]]:
    """
    Load all personas from disk. Returns list of (persona_id, Persona) tuples.

    Tries in order:
      1. --input path if provided
      2. data/population/personas.json
      3. data/population/personas_generated.json
      4. data/population/personas/ directory (individual .json files)
    """
    candidates = [
        input_path,
        PROJECT_ROOT / "data" / "population" / "personas.json",
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists() and Path(candidate).is_file():
            print(f"Loading from: {candidate}")
            with open(candidate) as f:
                data = json.load(f)
            return _parse_persona_data(data)

    persona_dir = PROJECT_ROOT / "data" / "population" / "personas"
    if persona_dir.exists() and persona_dir.is_dir():
        print(f"Loading from directory: {persona_dir}")
        results = []
        for json_file in sorted(persona_dir.glob("*.json")):
            with open(json_file) as f:
                p_dict = json.load(f)
            pid = json_file.stem
            try:
                results.append((pid, Persona.model_validate(p_dict)))
            except Exception as e:
                print(f"  [SKIP] {pid}: {e}")
        return results

    print("ERROR: No persona files found. Tried:")
    for c in candidates:
        print(f"  {c}")
    print(f"  {PROJECT_ROOT / 'data' / 'population' / 'personas'}/")
    sys.exit(1)


def _parse_persona_data(data: list | dict) -> list[tuple[str, Persona]]:
    results = []
    items = enumerate(data) if isinstance(data, list) else data.items()
    for idx, p_dict in items:
        if isinstance(data, list):
            pid = p_dict.get("id", p_dict.get("persona_id", f"persona_{idx:03d}"))
        else:
            pid = idx
        try:
            results.append((str(pid), Persona.model_validate(p_dict)))
        except Exception as e:
            print(f"  [SKIP] {pid}: {e}")
    return results


def run_validation(personas: list[tuple[str, Persona]], hard_only: bool = False) -> dict:
    checker = ConstraintChecker()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_personas": len(personas),
        "hard_only_mode": hard_only,
        "summary": {},
        "rule_hit_counts": defaultdict(int),
        "personas_with_hard_violations": [],
        "personas_with_soft_violations": [],
        "personas_clean": [],
        "violations_by_persona": {},
    }

    hard_count = 0
    soft_count = 0

    for pid, persona in personas:
        violations = checker.check_hard_only(persona) if hard_only else checker.check(persona)

        if not violations:
            report["personas_clean"].append(pid)
            continue

        hard_viols = [v for v in violations if v.severity == "hard"]
        soft_viols = [v for v in violations if v.severity == "soft"]

        if hard_viols:
            hard_count += 1
            report["personas_with_hard_violations"].append(pid)

        if soft_viols and not hard_only:
            soft_count += 1
            if pid not in report["personas_with_hard_violations"]:
                report["personas_with_soft_violations"].append(pid)

        report["violations_by_persona"][pid] = [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "message": v.message,
                "attribute_a": v.attribute_a,
                "attribute_b": v.attribute_b,
                "values": v.values,
            }
            for v in violations
        ]

        for v in violations:
            report["rule_hit_counts"][v.rule_id] += 1

    report["rule_hit_counts"] = dict(
        sorted(report["rule_hit_counts"].items(), key=lambda x: x[1], reverse=True)
    )
    report["summary"] = {
        "clean": len(report["personas_clean"]),
        "hard_violations": hard_count,
        "soft_violations": soft_count,
        "pct_clean": round(len(report["personas_clean"]) / len(personas) * 100, 1),
        "pct_hard": round(hard_count / len(personas) * 100, 1),
        "top_violated_rule": next(iter(report["rule_hit_counts"]), "none"),
    }
    return report


def print_summary(report: dict) -> None:
    s = report["summary"]
    total = report["total_personas"]

    print("\n" + "=" * 60)
    print("CONSTRAINT VALIDATION REPORT")
    print("=" * 60)
    print(f"Personas checked:      {total}")
    print(f"Clean (no violations): {s['clean']} ({s['pct_clean']}%)")
    print(f"Hard violations:       {s['hard_violations']} ({s['pct_hard']}%)")
    print(f"Soft violations only:  {s['soft_violations']}")
    print()

    if report["rule_hit_counts"]:
        print("Top 10 rules violated:")
        for i, (rule_id, count) in enumerate(list(report["rule_hit_counts"].items())[:10], 1):
            pct = round(count / total * 100, 1)
            print(f"  {i:2}. {rule_id:<15} {count:>4} personas ({pct}%)")

    if report["personas_with_hard_violations"]:
        print(f"\nPersonas needing regeneration ({len(report['personas_with_hard_violations'])}):")
        for pid in report["personas_with_hard_violations"][:20]:
            viols = report["violations_by_persona"][pid]
            hard = [v for v in viols if v["severity"] == "hard"]
            print(f"  {pid}: {', '.join(v['rule_id'] for v in hard)}")
        if len(report["personas_with_hard_violations"]) > 20:
            print(f"  ... and {len(report['personas_with_hard_violations']) - 20} more")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--hard-only", action="store_true")
    parser.add_argument("--fix-report", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    print("Loading personas...")
    personas = load_personas(args.input)
    print(f"Loaded {len(personas)} personas.")

    print("Running constraint checks...")
    report = run_validation(personas, hard_only=args.hard_only)
    print_summary(report)

    output_dir = PROJECT_ROOT / "data" / "population"
    output_path = args.output or output_dir / "constraint_violations_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written: {output_path}")

    if args.fix_report:
        fix_path = output_dir / "personas_to_regenerate.json"
        fix_data = {
            "generated_at": report["generated_at"],
            "reason": "hard constraint violations",
            "persona_ids": report["personas_with_hard_violations"],
            "violations": {
                pid: [v["rule_id"] for v in viols if v["severity"] == "hard"]
                for pid, viols in report["violations_by_persona"].items()
                if any(v["severity"] == "hard" for v in viols)
            },
        }
        with open(fix_path, "w") as f:
            json.dump(fix_data, f, indent=2)
        print(f"Fix list written: {fix_path}")

    sys.exit(1 if report["personas_with_hard_violations"] else 0)


if __name__ == "__main__":
    main()
```

---

## Part 3: `scripts/run_perception_sample.py`

Smoke-tests `CognitiveAgent.perceive()` on 5 randomly sampled personas using **real LLM calls**.
Requires `ANTHROPIC_API_KEY` in environment. Run after Part 2 completes.

**Known field names to use (verified by Antigravity):**
- Persona ID: `persona.id` (not `persona.demographics.parent_name` — that field does not exist)
- Age: `persona.demographics.parent_age`
- Decision style: `persona.parent_traits.decision_style`
- Trust anchor: `persona.parent_traits.trust_anchor`
- Health anxiety: `persona.psychology.health_anxiety`

```python
#!/usr/bin/env python3
"""
run_perception_sample.py — Live smoke-test of CognitiveAgent.perceive() on real personas.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_perception_sample.py
    python3 scripts/run_perception_sample.py --n 3 --seed 99

Output:
    data/population/perception_smoke_test.json
"""
import argparse
import json
import random
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import CognitiveAgent
from src.taxonomy.schema import Persona


# 5 standard stimuli — fixed across all runs for comparability
TEST_STIMULI = [
    {
        "type": "ad",
        "source": "instagram_feed",
        "brand": "littlejoys",
        "content": "LittleJoys: India's first clean-label nutrition drink for kids. No artificial colours, no preservatives. Trusted by 50,000 moms.",
        "simulation_tick": 1,
    },
    {
        "type": "wom",
        "source": "friend_whatsapp",
        "brand": "littlejoys",
        "content": "My friend Ritu sent me a WhatsApp: 'Yaar try karo LittleJoys, Aarav ki immunity bahut improve hui hai, no side effects'",
        "simulation_tick": 5,
    },
    {
        "type": "price_change",
        "source": "amazon_listing",
        "brand": "littlejoys",
        "content": "LittleJoys 500g pack now Rs 649 (was Rs 799). Limited time offer. Subscribe & Save for additional 10% off.",
        "simulation_tick": 8,
    },
    {
        "type": "product",
        "source": "pediatrician_office",
        "brand": "littlejoys",
        "content": "Pediatrician mentioned: 'I've been recommending LittleJoys to parents whose kids have low iron. The absorption rate is better than most alternatives.'",
        "simulation_tick": 12,
    },
    {
        "type": "social_event",
        "source": "school_whatsapp_group",
        "brand": "horlicks",
        "content": "School WhatsApp group: 'Which health drink does everyone give? My son refuses everything except Horlicks. Thinking of switching to something cleaner.'",
        "simulation_tick": 15,
    },
]


def load_sample_personas(n: int, seed: int) -> list[tuple[str, Persona]]:
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas.json",
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
    ]
    all_personas = []
    for candidate in candidates:
        if candidate.exists():
            with open(candidate) as f:
                data = json.load(f)
            if isinstance(data, list):
                for i, p_dict in enumerate(data):
                    pid = p_dict.get("id", p_dict.get("persona_id", f"persona_{i:03d}"))
                    try:
                        all_personas.append((str(pid), Persona.model_validate(p_dict)))
                    except Exception:
                        pass
            break

    if not all_personas:
        persona_dir = PROJECT_ROOT / "data" / "population" / "personas"
        if persona_dir.exists():
            for json_file in sorted(persona_dir.glob("*.json")):
                with open(json_file) as f:
                    p_dict = json.load(f)
                try:
                    all_personas.append((json_file.stem, Persona.model_validate(p_dict)))
                except Exception:
                    pass

    if not all_personas:
        print("ERROR: No personas found.")
        sys.exit(1)

    rng = random.Random(seed)
    return rng.sample(all_personas, min(n, len(all_personas)))


def run_smoke_test(personas: list[tuple[str, Persona]]) -> dict:
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stimuli_count": len(TEST_STIMULI),
        "personas_tested": len(personas),
        "results": [],
    }

    for pid, persona in personas:
        print(f"\n{'='*55}")
        # Use persona.id — parent_name field does not exist on this schema
        print(f"Persona: {pid}")
        print(f"  Age: {persona.demographics.parent_age}")
        print(f"  Decision style: {persona.parent_traits.decision_style}")
        print(f"  Trust anchor:   {persona.parent_traits.trust_anchor}")
        print(f"  Health anxiety: {persona.psychology.health_anxiety:.2f}")
        print()

        agent = CognitiveAgent(persona)
        persona_result = {
            "persona_id": pid,
            "age": persona.demographics.parent_age,
            "decision_style": persona.parent_traits.decision_style,
            "trust_anchor": persona.parent_traits.trust_anchor,
            "perception_results": [],
            "memory_entries_written": 0,
        }

        for stimulus in TEST_STIMULI:
            print(f"  [{stimulus['type']:12}] {stimulus['content'][:65]}...")
            try:
                result = agent.perceive(stimulus)
                print(f"    importance={result.importance:.2f}  valence={result.emotional_valence:+.2f}  reflect={result.reflection_trigger_candidate}")
                print(f"    → {result.interpretation[:110]}")
                if result.dominant_attributes:
                    print(f"    activated: {', '.join(result.dominant_attributes)}")

                persona_result["perception_results"].append({
                    "stimulus_type": stimulus["type"],
                    "stimulus_source": stimulus["source"],
                    "importance": result.importance,
                    "emotional_valence": result.emotional_valence,
                    "reflection_trigger_candidate": result.reflection_trigger_candidate,
                    "interpretation": result.interpretation,
                    "dominant_attributes": result.dominant_attributes,
                })
            except Exception as e:
                print(f"    ERROR: {e}")
                persona_result["perception_results"].append({
                    "stimulus_type": stimulus["type"],
                    "error": str(e),
                })

        persona_result["memory_entries_written"] = len(persona.episodic_memory)
        print(f"\n  Memory entries written: {persona_result['memory_entries_written']}")
        results["results"].append(persona_result)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Loading {args.n} personas (seed={args.seed})...")
    personas = load_sample_personas(args.n, args.seed)
    print(f"Loaded {len(personas)} personas.")

    print(f"\nRunning perception smoke test ({len(TEST_STIMULI)} stimuli × {len(personas)} personas)...")
    results = run_smoke_test(personas)

    output_path = PROJECT_ROOT / "data" / "population" / "perception_smoke_test.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*55}")
    print(f"Done. Output: {output_path}")

    errors = sum(
        1 for r in results["results"]
        for pr in r["perception_results"]
        if "error" in pr
    )
    if errors:
        print(f"Errors: {errors} — check output file")
        sys.exit(1)
    else:
        print(f"All {len(TEST_STIMULI) * len(personas)} perception calls succeeded.")


if __name__ == "__main__":
    main()
```

---

## Run Commands

```bash
# Part 2 — no API key needed, run now
python3 scripts/validate_personas.py --fix-report

# Part 3 — needs real API key
ANTHROPIC_API_KEY=sk-... python3 scripts/run_perception_sample.py --n 5 --seed 42
```

---

## What to Report Back

**From Part 2, report these exact numbers:**
```
Personas checked:      200
Clean (no violations): ___  (___%)
Hard violations:       ___  (___%)
Soft violations only:  ___
Top violated rule:     ___
```

This output is the Sprint 28 close gate. It also determines whether Sprint 29 needs
a Tier 1 regeneration pass before simulation work begins.

**From Part 3, report:**
- Any errors (should be zero)
- Confirm `perception_smoke_test.json` written

---

## Acceptance Criteria

- [ ] `python3 scripts/validate_personas.py` runs without error
- [ ] `constraint_violations_report.json` written to `data/population/`
- [ ] Summary table printed to stdout with clean/hard/soft counts
- [ ] `--fix-report` writes `personas_to_regenerate.json`
- [ ] `run_perception_sample.py` runs without error with valid API key
- [ ] `perception_smoke_test.json` written to `data/population/`
- [ ] Zero errors across 25 perception calls (5 stimuli × 5 personas)
- [ ] Exit code 0 on both scripts if no errors / no hard violations
