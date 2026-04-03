# Simulatte Persona Generator — Validity Framework

## Architecture Summary

The design synthesises three research sources into a single coherent engine:

| Layer | Source | What it contributes |
|---|---|---|
| Taxonomy Construction | DeepPersona (NeurIPS 2025) | Data-driven 8000-node attribute tree mined from real human discourse |
| Persona Synthesis | DeepPersona | Progressive, coherent filling of 200–250 attributes + 2000-char narrative |
| Core + Operational Memory | Generative Agents (UIST 2023) | Memory stream, retrieval scoring, reflection trees, planning |
| Environment Engine | MiroFish (2024) | Business-problem-derived world ontology, space/object hierarchy |
| Knowledge Graph | MiroFish | Single memory backend (nodes: persona, episodes, reflections, world) |

---

## Why This Approach is Valid

### 1. Empirical backing for each component

**DeepPersona (2025):**
- 32% higher attribute coverage vs PersonaHub baseline
- 44% improvement in uniqueness
- 31.7% reduction in deviation from real World Values Survey distributions
- Big Five personality distributions 17% closer to ground-truth vs LLM-only citizens

**Generative Agents (2023):**
- Full architecture (observe + reflect + plan) produced believability TrueSkill of 29.89
- Ablating reflection alone drops to 26.88 (significant degradation)
- Ablating all memory drops to 21.21 — below human crowdworker baseline
- Effect size vs no-memory baseline: **8 standard deviations**

**MiroFish (2024):**
- Ontology-first design prevents abstract, non-social entity types
- Continuous memory write-back enables emergent relationship tracking
- ReACT reporting agent provides structured insight extraction

### 2. The novel combination addresses gaps each paper leaves open

| Gap in prior work | Our resolution |
|---|---|
| DeepPersona personas are static — no runtime behaviour | Add Generative Agents memory loop |
| Generative Agents use shallow 1-para persona seeds | Replace with DeepPersona 200-attr depth |
| MiroFish personas are socially-typed (Twitter/Reddit archetypes) | Replace with narrative-complete individuals |
| Generative Agents environment is hand-crafted | Auto-generate from business problem (MiroFish) |
| DeepPersona taxonomy is general-purpose | Domain-weight taxonomy using business problem as prior |

### 3. The memory promotion mechanism is the key differentiator

The dual memory architecture (Core + Operational Stream) with reflection-triggered promotion creates the analogue of **formative experience**:
- Ordinary interactions stay in the operational stream
- When importance accumulates above threshold, reflection synthesises insights
- Sufficiently important reflections promote to Core Memory — permanently shaping the persona's identity
- This mirrors how real people update their worldview based on repeated exposure or pivotal events

---

## Validity Test Plan

### Test 1 — Intrinsic Quality (can run immediately, no infra needed)
1. Generate 10 personas for a test domain (e.g. first-time parent buying baby products)
2. LLM-as-judge evaluation:
   - Mean # distinct attributes extracted (target: >50 per persona)
   - Uniqueness score 1–5 (target: >3.5 average)
   - Internal consistency check (no contradictions)
3. Compare against: a flat GPT prompt persona (baseline)

### Test 2 — Behavioural Distribution (requires 50+ personas)
1. Generate 50–100 domain personas
2. Run 6 World Values Survey questions (ref: DeepPersona §4.3)
3. Measure KS statistic and Wasserstein distance vs real survey data
4. Target: KS < 0.35 (DeepPersona achieved 0.30 on average)

### Test 3 — Memory Coherence (requires runtime loop)
1. Run a persona through 20 simulated interaction turns
2. At turn 20, ask questions about turns 3, 7, 14 (memory retrieval test)
3. Check: does retrieved memory match actual stored observation?
4. Hallucination rate target: < 2% (Generative Agents achieved 1.3%)

### Test 4 — Reflection Validity (requires runtime loop)
1. Run persona through interactions with escalating importance scores
2. Trigger reflection when Σ importance > 150
3. Check: do generated reflections cite the correct source observations?
4. Check: are reflections higher-level inferences (not just summaries)?

### Test 5 — Believability (requires human evaluators)
1. Generate 5 personas with full architecture
2. Generate 5 personas with flat prompt (no taxonomy, no memory)
3. Human rankers: watch simulated session transcript, rank by believability
4. Target: full architecture beats baseline with statistical significance
5. Bonus: TrueSkill ranking against no-reflection ablation

### Test 6 — Business Fit (domain-specific)
1. Domain: LittleJoys (parent buying journey for children's products)
2. Have stakeholders read 3 generated persona transcripts (blind)
3. Rate on: realism, insight novelty, actionability for product decisions
4. Score 1–5; target average > 4.0

---

## Immediate Proof-of-Concept (< 1 day of work)

To validate the core claim before building the full engine:

```
Step 1: Pick a business problem (e.g. "parents discovering new children's activity products")
Step 2: Scrape 200 Reddit threads from r/Parenting, r/beyondthebump, r/Mommit
Step 3: Extract 500 QA pairs, classify as personalizable/non-personal
Step 4: Build a mini taxonomy (50 nodes, 3 levels) — just the parenting domain
Step 5: Generate 3 personas using progressive filling
Step 6: Compare narrative depth and uniqueness vs 3 flat-prompt personas
Step 7: Run each persona through 5 dialogue turns using the memory loop
Step 8: Check coherence across turns
```

Expected outcome: personas generated with the taxonomy approach will score
measurably higher on attribute count, uniqueness, and behavioural consistency.

---

## Key Architectural Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Taxonomy construction too expensive (many LLM calls) | Medium | Cache taxonomy per domain; reuse across persona generations |
| Memory stream becomes too large to fit in context | Medium | Retrieval scoring ensures only top-K memories used; reflection compresses |
| Reflection hallucinations corrupt Core Memory | Low-Medium | Require citation pointers; validate against source observations |
| Environment ontology doesn't match real user spaces | Low | Human review step; ontology editable before simulation starts |
| Personas drift toward stereotypes despite taxonomy | Low | Balanced attribute diversification (near/mid/far strata, 5:3:2 ratio) |

---

*Architecture diagram: `docs/persona_generator_architecture.png`*
*Generated: 2026-04-01*
