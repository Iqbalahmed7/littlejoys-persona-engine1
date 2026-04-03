# LittleJoys Persona Engine — System Overview
### From Static Profiles to Living Minds

---

## 1. What Was the Old System?

The original LittleJoys Persona Engine was a **profile generator**.

- You put in parameters (city, age, income, family type)
- You got back a detailed description of a person
- That person was **frozen in time** — a snapshot, not a simulation

Think of it like a very detailed character sheet in a role-playing game. The character has a backstory, traits, and preferences — but they don't *do* anything. They don't react. They don't remember. They don't change.

**What you could do with it:**
- Read about a persona
- Manually imagine how they'd respond to a campaign
- Use it as a reference for creative work

**What you couldn't do:**
- Run a stimulus through it and get a response
- Show it an ad and see if it paid attention
- Ask it whether it would buy something — and get a reasoned answer
- Run the same scenario across 200 personas and get a distribution

---

## 2. What Is the New System?

The new system is a **behavioural simulation engine**.

Each persona is now a living agent — a mind that can:

### See things
When a persona encounters a stimulus (an ad, a WhatsApp message, a pediatrician's comment, a price drop), it processes that stimulus through its own psychological lens. A health-anxious mom in a Tier 2 city notices a doctor's endorsement very differently than a price-conscious dad in a metro who trusts peer reviews over authority.

### Remember things
Every experience a persona has gets stored in an episodic memory. Not a flat list — a weighted one. Memories fade with time. High-salience experiences stick. The system mirrors how human memory actually works: you remember the things that mattered, not everything in order.

### Reflect on things
After accumulating enough experiences, a persona can step back and form higher-order insights — "I'm noticing I keep being drawn to products doctors mention" or "I'm suspicious of brands I've only seen in ads." These reflections then shape future decisions.

### Decide things
When put in front of a purchase scenario, the persona doesn't just return a label. It reasons through the decision in five steps — gut reaction, information processing, budget check, social signal check, final call. The output is a decision with a confidence score, a list of what drove the decision, a list of objections, and a willingness-to-pay number.

---

## 3. What Are We Trying to Change?

The deeper problem this system is solving is not about personas. It's about **how consumer insight is generated**.

### The current industry approach
A brand like LittleJoys would typically:
- Run focus groups (expensive, small sample, socially biased)
- Commission surveys (people say what they think you want to hear)
- A/B test in market (real cost, real risk, slow feedback loops)
- Rely on agency intuition ("our experience says moms in Tier 2 respond to...")

All of these approaches share the same flaw: **they tell you what happened, not why, and they can't run forward.**

### What we're building instead
A synthetic population of psychologically grounded consumers that you can run scenarios through *before* you spend money in market.

- Want to know if a pediatrician endorsement outperforms a price drop for your target segment? Run it on 165 personas in 17 minutes.
- Want to know which personas are in your "research more" bucket and what would tip them to buy? Ask the system.
- Want to know how a Muslim mom in Ranchi weighs the same product differently than a working dad in Bangalore? The system already has both of them, and they'll give you different answers for different reasons.

**The goal is to make market testing fast, cheap, and repeatable — before a single rupee of media budget is spent.**

---

## 4. The A/B Test — What We Proved

We ran a direct comparison between two approaches on the exact same stimuli:

### The question
Does a psychologically rich persona system actually produce *different* behaviour across different personas — or does it just produce different-sounding text that all means the same thing?

### The test
- **Our system:** Each persona processes a stimulus through its full psychological profile, memory, and values
- **Naive baseline:** A generic prompt — "you are a 28-year-old Indian parent, rate this stimulus"
- **Metric:** How much do the scores *vary* across personas for the same stimulus? (Higher variance = more differentiated = more useful)

### The result

| Stimulus | Our System | Naive Baseline |
|---|---|---|
| Instagram Ad | 0.124 | 0.000 |
| WhatsApp WOM | 0.047 | 0.000 |
| Price Drop | 0.087 | 0.000 |
| Pediatrician Mention | 0.096 | 0.000 |
| School WhatsApp Group | 0.067 | 0.059 |
| **Average** | **0.084** | **0.012** |

**Our personas are 607% more distinct than generic LLM sampling.**

The naive approach gives you the same response with different names attached. Our system gives you genuinely different people making genuinely different decisions — because they have different psychologies, different memories, and different values.

---

## 5. The Full Population Run — What the Personas Said

We ran all 165 psychologically clean personas through the same scenario:
- They had seen 5 stimuli (Instagram ad → WhatsApp WOM → price drop → pediatrician → school group chat)
- Then they were shown LittleJoys on BigBasket at Rs 649

### Decision distribution

| Decision | % of Population |
|---|---|
| Buy immediately | 62.4% |
| Want to research more first | 15.8% |
| Buy a trial pack | 11.5% |
| Defer for now | 9.1% |
| Reject outright | 1.2% |

**73.9% buy or trial** after the 5-stimulus sequence. Only 2 personas out of 165 said no outright.

### What drove the decisions

- **#1 driver by far:** Pediatrician recommendation — cited by 42% of personas as the primary reason to buy
- **#2 driver:** The price drop from Rs 799 to Rs 649 — created urgency and reduced trial risk
- **Top objection:** "I want to do my own research first" — the holdout group, not resistant, just cautious

### What this tells LittleJoys
- Doctor credibility is your most powerful acquisition channel — outweighs social proof, price, and advertising combined
- The price point at Rs 649 is right at willingness-to-pay (median WTP = Rs 649)
- The 15.8% "research more" segment is your retargeting pool — they're interested, they just need one more touch

---

## 6. What Has Been Built

### The Population
- 200 personas generated across Indian cities, family structures, income levels, and psychographic profiles
- Every persona has a full cognitive profile: psychology, values, decision style, trust anchors, cultural background, media habits
- Each persona has a narrative and a first-person voice
- 165 are fully clean and simulation-ready; 35 need targeted regeneration

### The Simulation Engine
- **Perceive:** Any stimulus → importance score + emotional response, personalised per persona
- **Memory:** Experiences accumulate, decay over time, high-salience moments stick
- **Reflect:** After enough experiences, personas form higher-order insights about their own patterns
- **Decide:** Purchase scenarios → 5-step reasoning → decision + confidence + WTP + drivers + objections

### The Validation Layer
- 30 constraint rules to catch psychological inconsistencies in persona profiles
- Automated violation reports with severity levels
- Post-generation enforcement to prevent anti-correlation errors

### The Tooling
- Streamlit debug UI — inspect any persona's full cognitive state, memory stream, brand relationships
- Scenario batch runner — run any stimulus set across the full population
- A/B test harness — benchmark against naive baselines
- 109 automated tests covering all core components

---

## 7. What Is Yet to Be Done

### Immediate (before client demo)
- Regenerate the 35 hard-violation personas to reach a clean population of 200
- Polish the Streamlit UI for external viewing
- Build a one-page output report from scenario results (decision distribution chart, top drivers, persona segments)

### Near-term (Sprint 30-31)
- **Multi-tick simulation:** Run a persona through 30 days of stimuli and watch brand trust build (or erode) over time
- **Competitive scenarios:** LittleJoys vs Horlicks vs Complan — who wins which persona segment and why
- **WOM propagation:** Model one persona's word-of-mouth influencing another's decision (the social graph layer)
- **Segment reporting:** Automatically cluster personas by decision outcome and surface what differentiates buyers from deferral

### Longer term
- Campaign optimisation: Given a media budget, which stimulus sequence maximises conversion across the population?
- Channel attribution: Which touchpoint — doctor, friend, ad, price — is doing the most work for which segment?
- Generalise to other brands and product categories beyond child nutrition

---

## 8. Research Intelligence Platform (Sprint 32, April 2026)

The simulation layer has been extended into a full research intelligence platform. The app now has 5 pages:

### Investigate (new)
A hypothesis-driven research flow. The PM picks a business problem, sees a structured tree of hypotheses — each grounded in real Indian FMCG market evidence (Horlicks, PediaSure, Dabur, Complan, Mamaearth) — and runs probes against the synthetic population. Results surface as interview response clusters, attribute split charts, simulation before/after comparisons, and a synthesis with ranked hypotheses and recommended actions.

Custom problems use `dynamic_generator.py` — Claude Sonnet generates a full hypothesis tree for any business question in plain English.

### Run Scenario (upgraded)
12 purchase channels, 6 marketing mix toggles (with live stimulus injection), LP Pass Rate metric, interactive persona table with decision reasoning deep-dive.

---

## The One-Line Summary

We built a population of 200 psychologically distinct Indian parents who can experience marketing, remember it, reflect on it, and make purchase decisions — and gave product managers a research intelligence platform to investigate why, intervene with hypotheses, and compare outcomes across scenarios.

That's the foundation. Everything else is built on top of it.
