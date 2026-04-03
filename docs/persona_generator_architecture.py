"""
Simulatte Persona Generator -- Architecture Diagram
Synthesises: DeepPersona (taxonomy + progressive sampling) +
             Generative Agents (memory stream, reflection, planning) +
             MiroFish (knowledge graph, environment ontology, behavioral params)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

# ── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0D1117"
PANEL    = "#161B22"
BORDER   = "#30363D"

C_DATA   = "#1A3A4A"   # teal – data / input
C_TAX    = "#1A2A4A"   # indigo – taxonomy
C_SYNTH  = "#2A1A4A"   # purple – synthesis
C_MEM    = "#3A2A1A"   # amber – memory
C_ENV    = "#1A3A2A"   # green – environment
C_LOOP   = "#3A1A2A"   # rose – runtime loop
C_OUT    = "#2A3A1A"   # olive – output

T_DATA   = "#58A6FF"
T_TAX    = "#79C0FF"
T_SYNTH  = "#D2A8FF"
T_MEM    = "#E3B341"
T_ENV    = "#56D364"
T_LOOP   = "#F78166"
T_OUT    = "#7EE787"

WHITE    = "#E6EDF3"
GREY     = "#8B949E"
DKGREY   = "#484F58"

ARROW    = "#58A6FF"

# ── Canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(22, 32))
ax.set_xlim(0, 22)
ax.set_ylim(0, 32)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# ── Helpers ───────────────────────────────────────────────────────────────────
def box(ax, x, y, w, h, fc, ec, lw=1.5, radius=0.3):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radius}",
                       linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(p)
    return p

def label(ax, x, y, txt, size=9, color=WHITE, bold=False, ha="center", va="center", zorder=3):
    weight = "bold" if bold else "normal"
    ax.text(x, y, txt, fontsize=size, color=color, ha=ha, va=va,
            fontweight=weight, zorder=zorder, wrap=False,
            fontfamily="monospace")

def section_header(ax, x, y, w, h, fc, ec, tc, title, subtitle=""):
    box(ax, x, y, w, h, fc, ec, lw=2)
    label(ax, x + w/2, y + h - 0.32, title, size=11, color=tc, bold=True)
    if subtitle:
        label(ax, x + w/2, y + h - 0.65, subtitle, size=7.5, color=GREY)

def chip(ax, x, y, w, h, fc, ec, tc, text, size=8):
    box(ax, x, y, w, h, fc, ec, lw=1, radius=0.2)
    label(ax, x + w/2, y + h/2, text, size=size, color=tc)

def arrow(ax, x1, y1, x2, y2, color=ARROW, lw=1.8, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle="arc3,rad=0.0"),
                zorder=4)

def dotted_arrow(ax, x1, y1, x2, y2, color=T_MEM):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=1.4,
                                linestyle="dashed",
                                connectionstyle="arc3,rad=0.0"),
                zorder=4)

def divider(ax, y, color=BORDER):
    ax.plot([0.5, 21.5], [y, y], color=color, lw=0.8, zorder=1, linestyle="--")

# ═══════════════════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 30.8, 21.2, 1.0, "#161B22", T_DATA, lw=2)
label(ax, 11, 31.45, "SIMULATTE  PERSONA  GENERATOR  --  ARCHITECTURE", size=15, color=WHITE, bold=True)
label(ax, 11, 31.1,
      "DeepPersona Taxonomy  x  Generative Agents Memory  x  MiroFish Environment",
      size=9, color=GREY)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 0 -- INPUTS  (y 29.4 – 30.6)
# ═══════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 29.4, 21.2, 1.2, C_DATA, T_DATA, lw=2)
label(ax, 11, 30.45, "[1] INPUT LAYER", size=10, color=T_DATA, bold=True)

chip(ax, 0.7, 29.55, 5.2, 0.7, PANEL, T_DATA, T_DATA,
     "[A]  Business Problem Statement\n     (domain, goals, target users)", size=7.5)
chip(ax, 6.3, 29.55, 5.2, 0.7, PANEL, T_DATA, T_DATA,
     "[B]  Scraped Forum Data\n     (Reddit, niche communities, QA sites)", size=7.5)
chip(ax, 11.9, 29.55, 4.5, 0.7, PANEL, T_DATA, T_DATA,
     "[C]  Anchor Traits (optional)\n     (age, role, context seed)", size=7.5)
chip(ax, 16.8, 29.55, 4.5, 0.7, PANEL, T_DATA, T_DATA,
     "[D]  Cohort Parameters\n     (N personas, diversity targets)", size=7.5)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 -- TAXONOMY ENGINE  (y 26.8 – 29.2)
# ═══════════════════════════════════════════════════════════════════════════════
section_header(ax, 0.4, 26.8, 21.2, 2.4, C_TAX, T_TAX, T_TAX,
               "[2] TAXONOMY CONSTRUCTION ENGINE",
               "DeepPersona Stage 1 -- data-driven, hierarchically organised, semantically validated")

# Sub-boxes
chip(ax, 0.7, 27.0, 4.5, 1.5, PANEL, T_TAX, T_TAX,
     "QA Pair Extraction\n──────────────────\n• Classify: Personalizable /\n  Partial / Non-personal\n• 62k+ labelled QA pairs", size=7.5)
chip(ax, 5.5, 27.0, 4.5, 1.5, PANEL, T_TAX, T_TAX,
     "Attribute Tree Build\n──────────────────\n• 12 root categories\n• Recursive LLM expansion\n• 8000+ unique nodes (3 levels)", size=7.5)
chip(ax, 10.3, 27.0, 4.5, 1.5, PANEL, T_TAX, T_TAX,
     "Semantic Validation\n──────────────────\n• Filter non-personal nodes\n• Merge >70% similar siblings\n• Bottom-up path validation", size=7.5)
chip(ax, 15.1, 27.0, 6.2, 1.5, PANEL, T_TAX, T_TAX,
     "Domain Specialisation\n──────────────────────\n• Business problem biases taxonomy\n• Relevant subtrees weighted higher\n• Custom anchor traits injected\n→ Output: T  (domain-tuned taxonomy)", size=7.5)

# Arrows within layer
arrow(ax, 5.2,  27.75, 5.5,  27.75)
arrow(ax, 10.0, 27.75, 10.3, 27.75)
arrow(ax, 14.8, 27.75, 15.1, 27.75)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 -- PERSONA SYNTHESIS  (y 23.6 – 26.6)
# ═══════════════════════════════════════════════════════════════════════════════
section_header(ax, 0.4, 23.6, 21.2, 3.0, C_SYNTH, T_SYNTH, T_SYNTH,
               "[3] PERSONA SYNTHESIS ENGINE",
               "DeepPersona Stage 2 -- progressive attribute sampling → narrative-complete personas")

chip(ax, 0.7, 23.8, 3.8, 2.5, PANEL, T_SYNTH, T_SYNTH,
     "Anchor Core\n────────────\n• Age, gender, location\n  from bias-free tables\n• Occupation sampled\n  by domain relevance\n• Values orientation\n  (pos / neg / neutral)", size=7.5)

chip(ax, 4.8, 23.8, 3.8, 2.5, PANEL, T_SYNTH, T_SYNTH,
     "Life Story Gen\n───────────────\n• 3 salient life-story\n  snippets (150–200 w)\n• Controversies allowed\n• Country-grounded\n  narrative realism", size=7.5)

chip(ax, 8.9, 23.8, 3.8, 2.5, PANEL, T_SYNTH, T_SYNTH,
     "Progressive Fill\n────────────────\n• Stochastic BFS on T\n• near/mid/far strata\n  5:3:2 diversity ratio\n• Each attr conditioned\n  on P_<i (coherence)\n• Target: 200–250 attrs", size=7.5)

chip(ax, 13.0, 23.8, 3.8, 2.5, PANEL, T_SYNTH, T_SYNTH,
     "Interests Inference\n────────────────────\n• Hobbies inferred from\n  life story (not stated)\n• MBTI + Big Five mapped\n• Coping mechanism\n• Relationship patterns", size=7.5)

chip(ax, 17.1, 23.8, 4.2, 2.5, PANEL, T_SYNTH, T_SYNTH,
     "Narrative Summary\n──────────────────\n• Narr(P) -- 2000-char\n  first-person narrative\n• JSON structured profile\n• Persona ID assigned\n→ Output: Deep Persona P", size=7.5)

arrow(ax, 4.5,  25.05, 4.8,  25.05)
arrow(ax, 8.6,  25.05, 8.9,  25.05)
arrow(ax, 12.7, 25.05, 13.0, 25.05)
arrow(ax, 16.8, 25.05, 17.1, 25.05)

# Down arrow from Taxonomy → Synthesis
arrow(ax, 11, 26.8, 11, 26.62, color=T_TAX)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3 -- CORE MEMORY  (y 20.8 – 23.4)
# ═══════════════════════════════════════════════════════════════════════════════
section_header(ax, 0.4, 20.8, 10.0, 2.6, C_MEM, T_MEM, T_MEM,
               "[4] CORE MEMORY",
               "Immutable identity seeded from DeepPersona profile")

chip(ax, 0.7, 21.0, 4.5, 1.2, PANEL, T_MEM, T_MEM,
     "Identity Store\n───────────────\n• Demographics + values\n• Key life episodes (timestamped)\n• Relationship map (seeded)", size=7.5)
chip(ax, 5.5, 21.0, 4.5, 1.2, PANEL, T_MEM, T_MEM,
     "Immutable Traits\n──────────────────\n• MBTI / Big Five scores\n• Cultural worldview\n• Long-term goals & fears\n• Deeply-held beliefs", size=7.5)

# LAYER 3b -- ENVIRONMENT ENGINE  (y 20.8 – 23.4, right side)
section_header(ax, 10.8, 20.8, 10.8, 2.6, C_ENV, T_ENV, T_ENV,
               "[5] ENVIRONMENT ENGINE",
               "MiroFish-inspired -- business problem → grounded world")

chip(ax, 11.1, 21.0, 4.8, 1.2, PANEL, T_ENV, T_ENV,
     "Ontology Generation\n────────────────────\n• LLM reads business problem\n• 8–12 entity types (social actors)\n• 6–10 relationship types", size=7.5)
chip(ax, 16.2, 21.0, 4.9, 1.2, PANEL, T_ENV, T_ENV,
     "Space / Object Tree\n────────────────────\n• Areas → subareas → objects\n• Agent environment subgraph\n• Rendered as natural language", size=7.5)

# Arrows persona → core memory and → environment
arrow(ax, 7, 23.6, 5.4, 23.42, color=T_SYNTH)
arrow(ax, 14, 23.6, 16, 23.42, color=T_SYNTH)

label(ax, 5.4, 23.5, "seeds →", size=7, color=GREY)
label(ax, 16.0, 23.5, "← grounds", size=7, color=GREY)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4 -- KNOWLEDGE GRAPH / MEMORY BACKEND  (y 18.6 – 20.6)
# ═══════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 18.6, 21.2, 2.0, "#1A1A2E", T_MEM, lw=2)
label(ax, 11, 20.3, "[6] KNOWLEDGE GRAPH  (Unified Memory Backend -- inspired by MiroFish / Zep)", size=10, color=T_MEM, bold=True)
label(ax, 11, 19.95, "Single source of truth for persona attributes, episode memory, relationships, and world state", size=8, color=GREY)

chip(ax, 0.7, 18.8, 4.0, 1.0, PANEL, T_MEM, T_MEM,
     "Persona Node\n(attribute tree)", size=7.5)
chip(ax, 5.0, 18.8, 4.0, 1.0, PANEL, T_MEM, T_MEM,
     "Episode Nodes\n(timestamped obs)", size=7.5)
chip(ax, 9.3, 18.8, 4.0, 1.0, PANEL, T_MEM, T_MEM,
     "Reflection Nodes\n(synthesised insights)", size=7.5)
chip(ax, 13.6, 18.8, 4.0, 1.0, PANEL, T_ENV, T_ENV,
     "World / Environment\n(space + object graph)", size=7.5)
chip(ax, 17.9, 18.8, 3.4, 1.0, PANEL, T_MEM, T_MEM,
     "Relationship\nEdges", size=7.5)

# Arrows down from Core Memory and Environment into KG
arrow(ax, 5.4, 20.8, 3.7, 20.6, color=T_MEM)
arrow(ax, 16.2, 20.8, 15.6, 20.6, color=T_ENV)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5 -- RUNTIME LOOP  (y 12.8 – 18.4)
# ═══════════════════════════════════════════════════════════════════════════════
section_header(ax, 0.4, 12.8, 21.2, 5.6, C_LOOP, T_LOOP, T_LOOP,
               "[7] OPERATIONAL RUNTIME LOOP",
               "Generative Agents architecture -- Perceive → Store → Retrieve → Reflect → Plan → Act")

# ── PERCEIVE ──────────────────────────────────────────────
box(ax, 0.7, 13.0, 3.5, 5.0, PANEL, T_LOOP, lw=1.5)
label(ax, 2.45, 17.7, "PERCEIVE", size=9, color=T_LOOP, bold=True)
label(ax, 2.45, 17.35, "Environment signals", size=7.5, color=GREY)
chip(ax, 0.9, 16.6, 3.1, 0.6, C_LOOP, T_LOOP, WHITE, "Space / object state changes", size=7)
chip(ax, 0.9, 15.9, 3.1, 0.6, C_LOOP, T_LOOP, WHITE, "Agent-to-agent communications", size=7)
chip(ax, 0.9, 15.2, 3.1, 0.6, C_LOOP, T_LOOP, WHITE, "User / researcher injections", size=7)
chip(ax, 0.9, 14.5, 3.1, 0.6, C_LOOP, T_LOOP, WHITE, "Business event triggers", size=7)
chip(ax, 0.9, 13.8, 3.1, 0.6, C_LOOP, T_LOOP, WHITE, "Own action outcomes", size=7)
chip(ax, 0.9, 13.1, 3.1, 0.6, C_LOOP, T_LOOP, WHITE, "Time / context signals", size=7)

# ── OPERATIONAL MEMORY STREAM ─────────────────────────────
box(ax, 4.5, 13.0, 4.0, 5.0, PANEL, T_MEM, lw=1.5)
label(ax, 6.5, 17.7, "OPERATIONAL", size=9, color=T_MEM, bold=True)
label(ax, 6.5, 17.35, "MEMORY STREAM", size=9, color=T_MEM, bold=True)
label(ax, 6.5, 16.95, "chronological observation log", size=7.5, color=GREY)

for i, (txt, imp) in enumerate([
    ("[obs] Noticed Sarah looking distressed",    "imp=7"),
    ("[obs] Product demo triggered confusion",    "imp=5"),
    ("[obs] Competitor mentioned 3x in 1hr",      "imp=8"),
    ("[plan] Follow up with Sarah tmrw",          "imp=6"),
    ("[reflect] Users fear change, not product",  "imp=9"),
]):
    yy = 16.5 - i * 0.7
    box(ax, 4.7, yy, 3.6, 0.58, "#1A1218", T_MEM, lw=0.8, radius=0.1)
    label(ax, 4.9, yy + 0.38, txt,  size=6.5, color=WHITE, ha="left")
    label(ax, 4.9, yy + 0.13, imp, size=6,   color=T_MEM, ha="left")

label(ax, 6.5, 13.2, "↑ grows continuously · scored on recency,", size=7, color=GREY)
label(ax, 6.5, 12.95, "  importance, relevance (embedding cosine)", size=7, color=GREY)

# ── RETRIEVAL ─────────────────────────────────────────────
box(ax, 8.8, 13.0, 3.5, 5.0, PANEL, T_MEM, lw=1.5)
label(ax, 10.55, 17.7, "RETRIEVE", size=9, color=T_MEM, bold=True)
label(ax, 10.55, 17.35, "relevance-weighted recall", size=7.5, color=GREY)

label(ax, 10.55, 16.9, "score =", size=8, color=WHITE)
label(ax, 10.55, 16.55,
      "α·recency\n+ β·importance\n+ γ·relevance",
      size=8, color=T_MEM, ha="center")
label(ax, 10.55, 15.6, "Recency: exp decay", size=7, color=GREY)
label(ax, 10.55, 15.3, "Importance: LLM 1–10", size=7, color=GREY)
label(ax, 10.55, 15.0, "Relevance: cosine sim", size=7, color=GREY)

box(ax, 9.0, 14.3, 3.1, 0.55, PANEL, T_MEM, lw=0.8)
label(ax, 10.55, 14.58, "Top-K retrieved memories", size=7.5, color=WHITE)
label(ax, 10.55, 14.38, "injected into LLM context", size=7, color=GREY)

box(ax, 9.0, 13.6, 3.1, 0.55, PANEL, T_MEM, lw=0.8)
label(ax, 10.55, 13.88, "Core memory always", size=7.5, color=WHITE)
label(ax, 10.55, 13.68, "present in context window", size=7, color=GREY)

box(ax, 9.0, 13.0, 3.1, 0.55, PANEL, T_MEM, lw=0.8)
label(ax, 10.55, 13.28, "KG graph query for", size=7.5, color=WHITE)
label(ax, 10.55, 13.08, "entity-relationship context", size=7, color=GREY)

# ── REFLECT ───────────────────────────────────────────────
box(ax, 12.6, 13.0, 3.5, 5.0, PANEL, T_SYNTH, lw=1.5)
label(ax, 14.35, 17.7,  "REFLECT", size=9, color=T_SYNTH, bold=True)
label(ax, 14.35, 17.35, "periodic synthesis", size=7.5, color=GREY)

label(ax, 14.35, 16.85, "Trigger: Σ importance > θ", size=7.5, color=WHITE)
label(ax, 14.35, 16.55, "(≈ 2–3x per session)", size=7, color=GREY)

for step, txt in [
    ("[1]", "Query last 100 obs from stream"),
    ("[2]", "Ask: 3 salient high-level insights?"),
    ("[3]", "Generate reflection nodes w/ citations"),
    ("[4]", "Store reflections back to stream"),
    ("[5]", "Promote to Core Memory if imp>8"),
]:
    step_list = ["[1]", "[2]", "[3]", "[4]", "[5]"]
    yy = 16.0 - step_list.index(step) * 0.62
    label(ax, 12.9, yy, step, size=7.5, color=T_SYNTH, ha="left")
    label(ax, 13.25, yy, txt, size=7,   color=WHITE,   ha="left")

label(ax, 14.35, 13.25, "→ builds reflection tree", size=7, color=GREY)
label(ax, 14.35, 13.05, "  (observations → inferences)", size=7, color=GREY)

# ── PLAN + ACT ────────────────────────────────────────────
box(ax, 16.4, 13.0, 4.9, 5.0, PANEL, T_LOOP, lw=1.5)
label(ax, 18.85, 17.7,  "PLAN  &  ACT", size=9, color=T_LOOP, bold=True)
label(ax, 18.85, 17.35, "goal-directed behaviour", size=7.5, color=GREY)

chip(ax, 16.6, 16.6, 4.5, 0.65, C_LOOP, T_LOOP, WHITE, "Broad day/session plan (top-down)", size=7.5)
chip(ax, 16.6, 15.8, 4.5, 0.65, C_LOOP, T_LOOP, WHITE, "Decompose → 5–15 min action chunks", size=7.5)
chip(ax, 16.6, 15.0, 4.5, 0.65, C_LOOP, T_LOOP, WHITE, "Observe → decide: continue or react?", size=7.5)
chip(ax, 16.6, 14.2, 4.5, 0.65, C_LOOP, T_LOOP, WHITE, "Dialogue generation (conditioned on mem)", size=7.5)
chip(ax, 16.6, 13.4, 4.5, 0.65, C_LOOP, T_LOOP, WHITE, "Action logged → env state update", size=7.5)

# Arrows inside runtime loop
arrow(ax, 4.2, 15.5, 4.5, 15.5, color=T_LOOP)   # perceive → stream
arrow(ax, 8.5, 15.5, 8.8, 15.5, color=T_MEM)    # stream → retrieve
arrow(ax, 12.3, 15.5, 12.6, 15.5, color=T_MEM)  # retrieve → reflect
arrow(ax, 16.1, 15.5, 16.4, 15.5, color=T_SYNTH) # reflect → plan

# Feedback loop arrow (act → perceive) -- curved
ax.annotate("", xy=(0.7, 14.0), xytext=(21.2, 14.0),
            arrowprops=dict(arrowstyle="->", color=T_LOOP, lw=1.4,
                            connectionstyle="arc3,rad=-0.35"),
            zorder=4)
label(ax, 11, 12.88, "← feedback: actions update environment & generate new perceptions", size=7.5, color=T_LOOP)

# Arrow KG → runtime loop (retrieval)
arrow(ax, 10.5, 18.6, 10.5, 18.1, color=T_MEM)

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 6 -- MEMORY PROMOTION  (annotation)
# ═══════════════════════════════════════════════════════════════════════════════
# Dotted arrow from reflect → core memory
ax.annotate("", xy=(5.4, 20.8), xytext=(14.35, 18.0),
            arrowprops=dict(arrowstyle="->", color=T_MEM, lw=1.4,
                            linestyle="dashed",
                            connectionstyle="arc3,rad=0.25"),
            zorder=4)
label(ax, 10.5, 20.3, "promote high-importance\nreflections to Core Memory", size=7, color=T_MEM, ha="center")

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 7 -- OUTPUTS  (y 10.4 – 12.6)
# ═══════════════════════════════════════════════════════════════════════════════
section_header(ax, 0.4, 10.4, 21.2, 2.2, C_OUT, T_OUT, T_OUT,
               "[8] OUTPUT INTERFACES",
               "What downstream consumers receive")

chip(ax, 0.7,  10.6, 4.0, 1.5, PANEL, T_OUT, T_OUT,
     "Dialogue Engine\n────────────────\n• In-character conversation\n• Memory-conditioned utterances\n• Tone / register consistent\n  with Big Five + life story", size=7.5)
chip(ax, 5.0,  10.6, 4.0, 1.5, PANEL, T_OUT, T_OUT,
     "Behavioural Sim\n────────────────\n• Daily routine output\n• Decision traces\n• Action JSONL stream\n• Cross-persona interaction log", size=7.5)
chip(ax, 9.3,  10.6, 4.0, 1.5, PANEL, T_OUT, T_OUT,
     "Insight Extraction\n──────────────────\n• ReACT report agent\n• KG panorama search\n• Cluster analysis across\n  N-persona population", size=7.5)
chip(ax, 13.6, 10.6, 4.0, 1.5, PANEL, T_OUT, T_OUT,
     "Persona Interview\n──────────────────\n• Live IPC mid-simulation\n• Post-sim deep interviews\n• Memory verification probes\n• Believability scoring", size=7.5)
chip(ax, 17.9, 10.6, 3.4, 1.5, PANEL, T_OUT, T_OUT,
     "Population Export\n──────────────────\n• JSON persona store\n• Survey simulation\n• World Values test\n• Big Five benchmark", size=7.5)

arrow(ax, 11, 12.8, 11, 12.62, color=T_LOOP)

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FRAMEWORK  (y 7.4 – 10.2)
# ═══════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 7.4, 21.2, 2.8, "#0D1A0D", T_OUT, lw=2)
label(ax, 11, 9.95, "[9] VALIDITY TESTING FRAMEWORK", size=10, color=T_OUT, bold=True)

chip(ax, 0.7,  7.6, 3.8, 2.0, PANEL, T_OUT, T_OUT,
     "INTRINSIC\n──────────\n• Mean # attributes (>50)\n• Uniqueness score (LLM judge)\n• Actionability potential\n• Consistency checks", size=7.5)
chip(ax, 4.8,  7.6, 3.8, 2.0, PANEL, T_OUT, T_OUT,
     "BEHAVIOURAL\n────────────\n• Big Five distribution vs\n  real national survey data\n• World Values Survey fit\n• KS / Wasserstein dist.", size=7.5)
chip(ax, 8.9,  7.6, 3.8, 2.0, PANEL, T_OUT, T_OUT,
     "MEMORY VALIDITY\n────────────────\n• Hallucination rate <2%\n• Retrieval relevance@K\n• Reflection citation acc.\n• Core↔Operational coherence", size=7.5)
chip(ax, 13.0, 7.6, 3.8, 2.0, PANEL, T_OUT, T_OUT,
     "BELIEVABILITY\n──────────────\n• Human ranker study\n• TrueSkill rank vs ablations\n• Full arch vs no-reflection\n  vs no-planning baselines", size=7.5)
chip(ax, 17.1, 7.6, 4.2, 2.0, PANEL, T_OUT, T_OUT,
     "BUSINESS FIT\n─────────────\n• Domain-specific Q&A acc.\n• Personalization-Fit score\n• Stakeholder blind review\n• Insight novelty rating", size=7.5)

# ═══════════════════════════════════════════════════════════════════════════════
# LEGEND  (y 5.4 – 7.2)
# ═══════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 5.4, 21.2, 1.8, PANEL, BORDER, lw=1)
label(ax, 11, 7.0, "COMPONENT LEGEND", size=8.5, color=GREY, bold=True)

legend_items = [
    (C_DATA,  T_DATA,  "Input / Data Sources"),
    (C_TAX,   T_TAX,   "Taxonomy Engine"),
    (C_SYNTH, T_SYNTH, "Persona Synthesis"),
    (C_MEM,   T_MEM,   "Memory (Core + Stream)"),
    (C_ENV,   T_ENV,   "Environment Engine"),
    (C_LOOP,  T_LOOP,  "Runtime Behaviour Loop"),
    (C_OUT,   T_OUT,   "Outputs + Validation"),
]
for i, (fc, ec, lbl) in enumerate(legend_items):
    xstart = 0.8 + i * 3.0
    box(ax, xstart, 5.6, 0.45, 0.45, fc, ec, lw=1.5, radius=0.1)
    label(ax, xstart + 0.6, 5.83, lbl, size=7.5, color=WHITE, ha="left")

# ═══════════════════════════════════════════════════════════════════════════════
# KEY INNOVATIONS callout  (y 0.5 – 5.2)
# ═══════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 0.5, 21.2, 4.7, PANEL, BORDER, lw=1)
label(ax, 11, 4.95, "KEY ARCHITECTURAL INNOVATIONS vs PRIOR WORK", size=10, color=WHITE, bold=True)

innovations = [
    (T_DATA,  "FORUM → TAXONOMY",
               "Unlike DeepPersona (ChatGPT convos), we mine domain-specific online forums (Reddit, Mumsnet,\n"
               "niche communities) grounding the taxonomy in real human discourse about the exact problem space."),
    (T_SYNTH, "BUSINESS-BIASED SYNTHESIS",
               "The taxonomy is domain-weighted at construction time (business problem statement acts as a prior),\n"
               "so personas are narrative-complete AND contextually relevant without post-hoc filtering."),
    (T_MEM,   "DUAL MEMORY ARCHITECTURE",
               "Core Memory (immutable DeepPersona identity) + Operational Stream (live episodes) -- reflections\n"
               "can promote from stream to core, mimicking how formative experiences reshape identity over time."),
    (T_ENV,   "GROUNDED ENVIRONMENT",
               "MiroFish-style ontology built from business problem → persona perceives a domain-relevant world\n"
               "(e.g., nursery, GP waiting room, WhatsApp group) rather than a generic sandbox town."),
]

for i, (color, title, body) in enumerate(innovations):
    yy = 4.5 - i * 0.98
    label(ax, 0.8, yy, f"> {title}", size=8.5, color=color, bold=True, ha="left")
    label(ax, 0.9, yy - 0.38, body, size=7.5, color=WHITE, ha="left")

# ── Footer ────────────────────────────────────────────────────────────────────
label(ax, 11, 0.25,
      "Simulatte  ·  Persona Generator Architecture  ·  Synthesises: DeepPersona (NeurIPS 2025)  x  "
      "Generative Agents (UIST 2023)  x  MiroFish (2024)",
      size=7, color=DKGREY)

plt.tight_layout(pad=0)
out = "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/docs/persona_generator_architecture.png"
plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG)
print(f"Saved → {out}")
plt.close()
