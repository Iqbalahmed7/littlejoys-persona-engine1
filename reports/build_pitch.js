"use strict";
const pptxgen = require("pptxgenjs");
const path    = require("path");

const OUT = path.resolve(__dirname, "Simulatte_LittleJoys_PitchDeck.pptx");

// ── Simulatte Brand Tokens ────────────────────────────────────────────────────
const B = {
  void:      "050505",   // all backgrounds
  layer:     "111111",   // card surfaces
  parchment: "E9E6DF",   // primary text
  signal:    "A8FF3E",   // ONE accent per slide
  static:    "5E5E5E",   // secondary/dimmed text
  dim:       "82817D",   // ~55% parchment on void
  faint:     "2A2A2A",   // very subtle dividers/borders
};

const HEADING  = "Barlow Condensed";
const BODY     = "Barlow";
const MONO     = "IBM Plex Mono";

const W = 10, H = 5.625;

// ── Helpers ───────────────────────────────────────────────────────────────────
function footer(slide, n) {
  // Divider
  slide.addShape("rect", { x: 0.5, y: H - 0.42, w: W - 1, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
  slide.addText("Simulatte / Confidential", { x: 0.5, y: H - 0.38, w: 4, h: 0.25, fontSize: 8, color: B.static, fontFace: MONO, margin: 0 });
  slide.addText(String(n).padStart(2, "0"), { x: W - 1.0, y: H - 0.38, w: 0.5, h: 0.25, fontSize: 8, color: B.static, fontFace: MONO, align: "right", margin: 0 });
}

function sectionLabel(slide, text) {
  slide.addText(text, { x: 0.5, y: 0.38, w: 5, h: 0.22, fontSize: 10, bold: false, color: B.signal, fontFace: HEADING, charSpacing: 2, margin: 0 });
}

function headline(slide, text, y = 0.75, size = 34) {
  slide.addText(text, { x: 0.5, y, w: W - 1, h: (size / 72) * 1.5 + 0.2, fontSize: size, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
}

function body(slide, text, x, y, w, h, color = null, size = 13.5) {
  slide.addText(text, { x, y, w, h, fontSize: size, color: color || B.dim, fontFace: BODY, margin: 0, valign: "top" });
}

function monoLabel(slide, text, x, y, w, color = null) {
  slide.addText(text, { x, y, w, h: 0.22, fontSize: 8.5, color: color || B.static, fontFace: MONO, margin: 0, charSpacing: 1 });
}

function divider(slide, y) {
  slide.addShape("rect", { x: 0.5, y, w: W - 1, h: 0.008, fill: { color: B.faint }, line: { color: B.faint } });
}

function card(slide, x, y, w, h) {
  slide.addShape("rect", { x, y, w, h, fill: { color: B.layer }, line: { color: B.faint, pt: 0.75 } });
}

function bigMetric(slide, value, label, x, y, w, green = false) {
  card(slide, x, y, w, 1.45);
  monoLabel(slide, label.toUpperCase(), x + 0.2, y + 0.18, w - 0.4, B.static);
  slide.addText(value, { x: x + 0.1, y: y + 0.42, w: w - 0.2, h: 0.82,
    fontSize: 44, bold: true, color: green ? B.signal : B.parchment, fontFace: HEADING, margin: 0 });
}

// ── Build ─────────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout  = "LAYOUT_16x9";
  pres.author  = "Simulatte";
  pres.title   = "Simulatte — Consumer Decision Infrastructure";

  let n = 0;

  // ─── SLIDE 1 · COVER ────────────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };

    // Subtle grid
    for (let r = 0; r < 9; r++) {
      s.addShape("line", { x: 0, y: r * 0.7, w: W, h: 0, line: { color: "0D0D0D", pt: 0.5 } });
    }
    for (let c = 0; c < 15; c++) {
      s.addShape("line", { x: c * 0.72, y: 0, w: 0, h: H, line: { color: "0D0D0D", pt: 0.5 } });
    }

    monoLabel(s, "SIMULATTE / SALES / 2026", 0.5, 0.35, 5, B.static);

    s.addText("Simulate reality.\nDecide better.", {
      x: 0.5, y: 1.1, w: 8.5, h: 2.4,
      fontSize: 68, bold: true, color: B.parchment, fontFace: HEADING, margin: 0,
    });

    // Green signal dot
    s.addShape("oval", { x: 8.6, y: H - 0.55, w: 0.12, h: 0.12, fill: { color: B.signal }, line: { color: B.signal } });

    monoLabel(s, "DECISION INFRASTRUCTURE", W - 3.8, H - 0.56, 3.3, B.static);
    monoLabel(s, "simulatte.ai", 0.5, H - 0.56, 3, B.static);
  }

  // ─── SLIDE 2 · THE PROBLEM ───────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE PROBLEM");
    headline(s, "Research gives you opinions.\nDecisions need behaviour.", 0.72, 40);
    divider(s, 2.3);

    const pains = [
      { t: "Surveys",      b: "People report intentions, not actions. Response bias, social desirability, and recall errors are baked in systematically." },
      { t: "Focus groups", b: "One loud voice shapes the room. You hear the group average, not the individual who will actually buy — or not." },
      { t: "A/B tests",    b: "Six to twelve weeks for a single signal. By the time you have an answer, the campaign has already run." },
    ];
    pains.forEach((p, i) => {
      const px = 0.5 + i * 3.15;
      card(s, px, 2.5, 2.88, 2.5);
      s.addText(p.t, { x: px + 0.18, y: 2.68, w: 2.5, h: 0.38, fontSize: 16, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      body(s, p.b, px + 0.18, 3.1, 2.52, 1.7, B.dim, 11.5);
    });

    // Callout
    s.addText("By the time you have an answer, the moment has passed.", {
      x: 0.5, y: H - 0.8, w: 9, h: 0.3, fontSize: 12, color: B.signal, fontFace: BODY, italic: true, margin: 0,
    });
    footer(s, n);
  }

  // ─── SLIDE 3 · WHAT SIMULATTE IS ────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "WHAT WE ARE");

    // Statement
    s.addText("This is not research.\nThis is infrastructure.", {
      x: 0.5, y: 0.72, w: 9, h: 1.9, fontSize: 52, bold: true, color: B.parchment, fontFace: HEADING, margin: 0,
    });
    divider(s, 2.72);

    body(s,
      "Simulatte creates synthetic consumers — each with their own psychology, memory, values, and decision style — and runs them through simulated real-world scenarios. Every decision is explained, step by step, in the persona's own voice.",
      0.5, 2.88, 5.8, 1.1, B.parchment, 13);

    // 3 differentiators on right
    const diffs = [
      "No surveys. No sample bias. No fieldwork latency.",
      "Every persona is a complete person with a consistent decision architecture across time.",
      "Results in hours. Hypotheses tested before a single rupee of media spend.",
    ];
    diffs.forEach((d, i) => {
      s.addShape("line", { x: 7.0, y: 2.9 + i * 0.72, w: 2.6, h: 0, line: { color: B.faint, pt: 0.75 } });
      monoLabel(s, `0${i + 1}`, 7.0, 2.92 + i * 0.72, 0.4, B.signal);
      body(s, d, 7.45, 2.9 + i * 0.72, 2.15, 0.62, B.dim, 10.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 4 · PERSONA ARCHITECTURE ─────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE SCIENCE");
    headline(s, "9-layer persona architecture.\nBuilt on behaviour research.", 0.72, 30);
    divider(s, 1.65);

    const layers = [
      { n: "01", label: "DEMOGRAPHICS",    desc: "Age, city tier, income, family structure, employment" },
      { n: "02", label: "PSYCHOLOGY",      desc: "20+ validated attributes — health anxiety, social proof bias, authority bias, loss aversion" },
      { n: "03", label: "VALUES",          desc: "Best-for-my-child intensity, supplement necessity belief, nutrition gap awareness" },
      { n: "04", label: "RELATIONSHIPS",   desc: "Child pester power, elder advice weight, spouse decision-sharing" },
      { n: "05", label: "DAILY ROUTINE",   desc: "Shopping platform, morning complexity, deal-seeking intensity" },
      { n: "06", label: "CAREER",          desc: "Work hours, time scarcity, career ambition" },
      { n: "07", label: "MEMORY",          desc: "Episodic memory (event-by-event) + semantic memory (long-term beliefs)" },
      { n: "08", label: "DECISION ARCH.",  desc: "Decision style, trust anchor, risk appetite, coping mechanisms" },
      { n: "09", label: "NARRATIVE",       desc: "First-person voice, biographical backstory, purchase decision bullets" },
    ];

    const colBreak = 5;
    layers.forEach((l, i) => {
      const col = i < colBreak ? 0 : 1;
      const row = i < colBreak ? i : i - colBreak;
      const lx = 0.5 + col * 4.85;
      const ly = 1.78 + row * 0.68;
      s.addShape("rect", { x: lx, y: ly, w: 0.36, h: 0.36, fill: { color: B.layer }, line: { color: B.faint, pt: 0.75 } });
      monoLabel(s, l.n, lx + 0.06, ly + 0.09, 0.28, l.n === "01" ? B.signal : B.static);
      s.addText(l.label, { x: lx + 0.46, y: ly + 0.0, w: 1.6, h: 0.22, fontSize: 10.5, bold: true, color: B.parchment, fontFace: HEADING, margin: 0, charSpacing: 1 });
      body(s, l.desc, lx + 0.46, ly + 0.2, 4.0, 0.42, B.dim, 9);
    });

    body(s, "Sampled via Gaussian copula with empirically validated correlation structures. Not made up. Not guessed.", 0.5, H - 0.78, 9, 0.28, B.static, 9.5);
    footer(s, n);
  }

  // ─── SLIDE 5 · 5-STEP COGNITIVE TRACE ───────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE ENGINE");
    headline(s, "Every decision leaves\na complete reasoning trace.", 0.72, 30);
    divider(s, 1.65);

    const steps = [
      { n: "01", t: "GUT REACTION",          b: "Initial emotional response based on personality and past experience" },
      { n: "02", t: "INFO PROCESSING",        b: "What information does this persona focus on, given their specific attributes?" },
      { n: "03", t: "CONSTRAINT CHECK",       b: "Budget, non-negotiables, and trust requirements" },
      { n: "04", t: "SOCIAL SIGNAL CHECK",    b: "What would the people in their trust network say?" },
      { n: "05", t: "FINAL DECISION",         b: "buy / trial / research_more / defer / reject" },
    ];

    steps.forEach((st, i) => {
      const sx = 0.5 + i * 1.83;
      card(s, sx, 1.78, 1.72, 3.12);
      // Number
      s.addShape("rect", { x: sx, y: 1.78, w: 1.72, h: 0.32, fill: { color: i === 4 ? B.signal : B.faint }, line: { color: B.faint } });
      monoLabel(s, st.n, sx + 0.08, 1.86, 1.56, i === 4 ? B.void : B.static);
      s.addText(st.t, { x: sx + 0.1, y: 2.22, w: 1.52, h: 0.55, fontSize: 12, bold: true, color: B.parchment, fontFace: HEADING, charSpacing: 1, margin: 0 });
      body(s, st.b, sx + 0.1, 2.82, 1.52, 1.85, B.dim, 10.5);
      // Arrow
      if (i < 4) s.addShape("line", { x: sx + 1.72, y: 2.34, w: 0.11, h: 0, line: { color: B.faint, pt: 1 } });
    });

    body(s, "You don't get an outcome. You get the complete reasoning — auditable, explainable, challengeable.", 0.5, H - 0.78, 9, 0.28, B.static, 9.5);
    footer(s, n);
  }

  // ─── SLIDE 6 · JOURNEY SIMULATION ───────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE ENGINE");
    headline(s, "A journey simulates real\nconsumer time — tick by tick.", 0.72, 30);
    divider(s, 1.65);

    // Left column: explanation
    body(s, "A journey is a sequence of 45–61 simulation ticks. Each tick can fire a stimulus, a reflection, or a decision. Between ticks, the persona accumulates episodic memories, builds brand trust, and updates their internal state — exactly as a real consumer does over days and weeks.", 0.5, 1.82, 4.4, 2.1, B.parchment, 12.5);
    body(s, "The result is not a snapshot. It is a film of a consumer's complete decision path.", 0.5, 4.1, 4.4, 0.55, B.signal, 12);

    // Right column: tick types
    const ticks = [
      { label: "STIMULUS", desc: "Instagram ad · WhatsApp WOM · Pediatrician visit · Price drop · Retargeting" },
      { label: "REFLECTION", desc: "Persona processes accumulated memories into updated beliefs and brand trust score" },
      { label: "DECISION", desc: "buy · trial · research_more · defer · reject — each with full 5-step reasoning trace" },
    ];
    ticks.forEach((t, i) => {
      const ty = 1.82 + i * 1.06;
      card(s, 5.2, ty, 4.3, 0.92);
      monoLabel(s, t.label, 5.38, ty + 0.14, 3, B.signal);
      body(s, t.desc, 5.38, ty + 0.36, 3.9, 0.46, B.dim, 10);
    });

    footer(s, n);
  }

  // ─── SLIDE 7 · 4 PILLARS ────────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE ADVANTAGE");
    headline(s, "Four structural advantages\nno survey can replicate.", 0.72, 30);
    divider(s, 1.65);

    const pillars = [
      { metric: "2–24h",  label: "TIME TO INSIGHT",  desc: "From business question to result. No fieldwork, no sample recruitment, no waiting." },
      { metric: "5-step", label: "REASONING DEPTH",  desc: "Every persona's reasoning is auditable. You see the WHY, not just the outcome." },
      { metric: "200×",   label: "PARALLEL SCALE",   desc: "Run every persona simultaneously. Segment any dimension — city, income, decision style." },
      { metric: "∞",      label: "REPEATABILITY",    desc: "Change one variable. Re-run. Compare scenarios head-to-head without a new study." },
    ];
    pillars.forEach((p, i) => {
      const px = 0.5 + i * 2.32;
      card(s, px, 1.82, 2.12, 3.2);
      s.addText(p.metric, { x: px + 0.12, y: 2.0, w: 1.88, h: 1.0, fontSize: 46, bold: true, color: i === 0 ? B.signal : B.parchment, fontFace: HEADING, margin: 0 });
      monoLabel(s, p.label, px + 0.12, 2.98, 1.88, B.static);
      s.addShape("line", { x: px + 0.12, y: 3.2, w: 1.88, h: 0, line: { color: B.faint, pt: 0.75 } });
      body(s, p.desc, px + 0.12, 3.3, 1.88, 1.5, B.dim, 10.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 8 · PLATFORM FEATURES ────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE PLATFORM");
    headline(s, "Six capabilities. One system.", 0.72, 30);
    divider(s, 1.38);

    const features = [
      { n: "01", t: "Persona Explorer",        d: "Browse 200 psychographic profiles. Filter by city tier, age, decision style. Read full narrative and first-person voice." },
      { n: "02", t: "Journey Simulator",       d: "Run any business problem as a simulation. Define the stimuli, set decision ticks, fire the engine." },
      { n: "03", t: "Decision Drill-Down",     d: "Click any persona. See the complete 5-step reasoning trace for every decision moment in their journey." },
      { n: "04", t: "Brand Trust Trajectory",  d: "Watch brand trust build tick-by-tick. See exactly where it spikes and where it stalls." },
      { n: "05", t: "Probing Trees",           d: "Test competing hypotheses. Get an evidence-based verdict: Confirmed / Rejected / Partial." },
      { n: "06", t: "Conversational Probing",  d: "Talk directly to any persona. Ask why they decided what they decided. Get answers in their own voice." },
    ];
    features.forEach((f, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const fx = 0.5 + col * 3.1;
      const fy = 1.55 + row * 1.82;
      card(s, fx, fy, 2.9, 1.65);
      monoLabel(s, f.n, fx + 0.15, fy + 0.16, 0.5, f.n === "01" ? B.signal : B.static);
      s.addText(f.t, { x: fx + 0.15, y: fy + 0.42, w: 2.6, h: 0.42, fontSize: 13.5, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      body(s, f.d, fx + 0.15, fy + 0.9, 2.6, 0.65, B.dim, 9.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 9 · PLATFORM IN ACTION ───────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "THE PLATFORM");
    headline(s, "The system, running.", 0.72, 30);
    divider(s, 1.38);

    // Simulated terminal / UI panels
    const panels = [
      {
        label: "PERSONA CARD",
        lines: [
          { t: "Manisha-Bhubaneswar-Mom-40", mono: true, c: B.signal },
          { t: "Decision style:  analytical", mono: true },
          { t: "Trust anchor:    self", mono: true },
          { t: "Health anxiety:  0.61 / 1.0", mono: true },
          { t: "Nutrition budget: ₹2,862 / month", mono: true },
          { t: "3 children · joint household · Tier-3", mono: false, c: B.dim },
        ],
      },
      {
        label: "DECISION TRACE",
        lines: [
          { t: "Day 28 → research_more  (conf: 0.72)", mono: true, c: B.parchment },
          { t: "\"I need to see the ingredient list.", mono: false, c: B.dim },
          { t: " ₹250/month extra is manageable.", mono: false, c: B.dim },
          { t: " But I won't commit blind.\"", mono: false, c: B.dim },
          { t: "Day 60 → buy            (conf: 0.78)", mono: true, c: B.signal },
          { t: "\"The child asked for it by name.", mono: false, c: B.dim },
          { t: " That's the only evidence I trust.\"", mono: false, c: B.dim },
        ],
      },
      {
        label: "PROBING TREE",
        lines: [
          { t: "HYPOTHESIS:", mono: true, c: B.static },
          { t: "Placebo concern = measurement gap", mono: false, c: B.parchment },
          { t: "", mono: false },
          { t: "VERDICT:", mono: true, c: B.static },
          { t: "CONFIRMED", mono: true, c: B.signal },
          { t: "", mono: false },
          { t: "Tracked-behaviour reorder rate:", mono: false, c: B.dim },
          { t: "2× vs vague-improvement group", mono: false, c: B.parchment },
        ],
      },
    ];

    panels.forEach((p, i) => {
      const px = 0.5 + i * 3.12;
      card(s, px, 1.55, 2.9, 3.65);
      // Panel top bar
      s.addShape("rect", { x: px, y: 1.55, w: 2.9, h: 0.28, fill: { color: B.faint }, line: { color: B.faint } });
      monoLabel(s, p.label, px + 0.12, 1.6, 2.65, B.static);
      p.lines.forEach((l, j) => {
        if (!l.t) return;
        s.addText(l.t, {
          x: px + 0.12, y: 1.97 + j * 0.38, w: 2.65, h: 0.35,
          fontSize: l.mono ? 8.5 : 10, color: l.c || B.dim,
          fontFace: l.mono ? MONO : BODY, margin: 0,
        });
      });
    });

    footer(s, n);
  }

  // ─── SLIDE 10 · CASE STUDY INTRO ────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };

    monoLabel(s, "CASE STUDY", 0.5, 0.38, 4, B.static);
    s.addText("LittleJoys", { x: 0.5, y: 0.62, w: 5, h: 0.48,
      fontSize: 34, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
    s.addShape("line", { x: 0.5, y: 1.18, w: 9, h: 0, line: { color: B.faint, pt: 0.75 } });

    body(s, "Indian D2C child nutrition brand. Three live business problems. Three simulation journeys. 200 psychographic personas. Every decision reasoned step by step.", 0.5, 1.3, 5.5, 0.65, B.dim, 11);

    // 3 problem cards — full detail
    const probs = [
      {
        label: "01",
        product: "Nutrimix · Age 2–6",
        title: "Increasing Nutrimix\nRepeat Purchase",
        context: "Strong trial rates and positive NPS. Near-universal reorder. But 2% of buyers lapsed at cycle 2 with no discount trigger. What was the precise mechanism — and what stimulus would protect it at scale?",
        metric: "98.0%",
        metricLabel: "REORDER RATE",
      },
      {
        label: "02",
        product: "Magnesium Gummies · Age 3–8",
        title: "Increasing Magnesium\nGummies Sales",
        context: "New category — near-zero awareness. 67.5% of parents never trial at all. The pediatrician actively discouraged it. What single signal converts a skeptical parent into a first-time buyer?",
        metric: "32.5%",
        metricLabel: "BASELINE TRIAL RATE",
      },
      {
        label: "03",
        product: "Nutrimix · Age 7–14",
        title: "Expanding Nutrimix\ninto the 7–14 Age Segment",
        context: "Competing against Bournvita at a Rs 250 premium. Only 37.2% trialled. Of first-time buyers, 72.7% lapsed. Family pack + child preference signal drove reorder rate from 27.3% to 93.8%.",
        metric: "93.8%",
        metricLabel: "REORDER AFTER INTERVENTION",
      },
    ];

    probs.forEach((p, i) => {
      const px = 0.5 + i * 3.12;
      card(s, px, 2.08, 2.98, 3.1);

      // Number + product tag
      monoLabel(s, p.label, px + 0.18, 2.22, 0.4, B.signal);
      monoLabel(s, p.product, px + 0.55, 2.22, 2.25, B.static);

      // Title
      s.addText(p.title, { x: px + 0.18, y: 2.46, w: 2.62, h: 0.72,
        fontSize: 13, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });

      // Divider
      s.addShape("rect", { x: px, y: 3.22, w: 2.98, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });

      // Context
      body(s, p.context, px + 0.18, 3.3, 2.62, 1.08, B.dim, 9);

      // Metric
      s.addText(p.metric, { x: px + 0.18, y: 4.42, w: 1.4, h: 0.42,
        fontSize: 22, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      monoLabel(s, p.metricLabel, px + 0.18, 4.84, 2.62, B.dim);
    });

    footer(s, n);
  }

  // ─── SLIDE 11 · COHORT STATS ─────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / COHORT");
    headline(s, "200 Indian parents.\nFully simulated.", 0.72, 34);
    divider(s, 1.72);

    const stats = [
      { v: "200",   l: "PERSONAS",          sub: "Tier 1 · 2 · 3 cities" },
      { v: "₹2.7L", l: "MIN INCOME",        sub: "to ₹54L per annum" },
      { v: "56%",   l: "NUCLEAR FAMILIES",  sub: "33% joint · 11% single parent" },
      { v: "30%",   l: "HABITUAL BUYERS",   sub: "24% analytical · 26% emotional · 21% social" },
    ];
    stats.forEach((st, i) => {
      const sx = 0.5 + i * 2.32;
      card(s, sx, 1.88, 2.12, 1.8);
      monoLabel(s, st.l, sx + 0.15, 2.02, 1.82, B.static);
      s.addText(st.v, { x: sx + 0.1, y: 2.22, w: 1.92, h: 0.82, fontSize: 40, bold: true,
        color: i === 0 ? B.signal : B.parchment, fontFace: HEADING, margin: 0 });
      body(s, st.sub, sx + 0.12, 3.02, 1.88, 0.52, B.dim, 9.5);
    });

    s.addText("These are not demographic buckets. Each persona has a name, a city, a family, and a reason they might say yes — or no.", {
      x: 0.5, y: 4.0, w: 9, h: 0.45,
      fontSize: 13.5, color: B.dim, fontFace: BODY, italic: true, margin: 0,
    });

    footer(s, n);
  }

  // ─── SLIDE 12 · PROBLEM A — FINDING ─────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / PROBLEM A  ·  NUTRIMIX REPEAT PURCHASE");
    headline(s, "Increasing Nutrimix\nrepeat purchase.", 0.72, 30);
    divider(s, 1.58);

    // Metrics (left)
    bigMetric(s, "99.0%", "TRIAL RATE", 0.5, 1.74, 2.1);
    bigMetric(s, "98.0%", "REORDER RATE", 2.72, 1.74, 2.1, true);

    monoLabel(s, "2.0% OF BUYERS DID NOT REORDER AT FULL PRICE  ·  61-DAY JOURNEY  ·  AGE 2–6 COHORT", 0.5, 3.32, 9, B.static);

    // Key finding card (right)
    card(s, 5.08, 1.74, 4.42, 2.45);
    monoLabel(s, "WHAT THE SIMULATION FOUND", 5.26, 1.9, 4.1, B.static);
    s.addShape("rect", { x: 5.08, y: 2.12, w: 0.03, h: 1.85, fill: { color: B.signal }, line: { color: B.signal } });
    body(s, "98% came back. The 2% who didn't had no reorder trigger at Day 60. The discount that drove trial had vanished. No nudge. No renewal cue. WOM from Priya created a near-unbreakable purchase habit — the lapse is a trigger absence, not satisfaction failure.", 5.2, 2.12, 4.18, 1.32, B.parchment, 10.5);
    monoLabel(s, "CONFIRMED: No reorder trigger (Day 55–60) · Price sensitivity at full price", 5.26, 3.62, 4.1, B.dim);

    // Bottom hypotheses row
    card(s, 0.5, 3.55, 4.42, 0.75);
    monoLabel(s, "HYPOTHESIS TREE", 0.68, 3.68, 4.0, B.static);
    const hA = [
      { v: "REJECTED", t: "Habit not formed" },
      { v: "CONFIRMED", t: "No reorder trigger" },
      { v: "CONFIRMED", t: "Price at full rate" },
    ];
    hA.forEach((h, i) => {
      const hx = 0.68 + i * 1.45;
      s.addText(h.v, { x: hx, y: 3.88, w: 1.38, h: 0.2, fontSize: 7.5, bold: true,
        color: h.v === "CONFIRMED" ? B.signal : B.dim, fontFace: MONO, charSpacing: 0.5, margin: 0 });
      body(s, h.t, hx, 4.06, 1.38, 0.2, B.dim, 8.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 13 · PROBLEM A — INTERVENTIONS + RE-SIMULATION ────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / PROBLEM A  ·  INTERVENTION SIMULATION");
    headline(s, "We re-ran the journey with\nthe fix coded in.", 0.72, 30);
    divider(s, 1.58);

    // 3 intervention cards (left column)
    const ivsA = [
      { n: "01", title: "Loyalty Pricing at Reorder",     detail: "₹599 on second pack via app push at Day 55. \"Here's your loyalty price.\"",     impact: "+10pp reorder rate" },
      { n: "02", title: "Social Proof Nudge at Day 50",   detail: "WhatsApp: \"3,400 parents reordered this month.\" Peer signal at the decision window.", impact: "+5pp reorder rate" },
      { n: "03", title: "LJ Pass Subscription Offer",     detail: "Post-trial: ₹579/month, cancel anytime, delivered before the pack runs out.",         impact: "Churn 29% → 18%" },
    ];
    ivsA.forEach((iv, i) => {
      card(s, 0.5, 1.74 + i * 1.0, 5.55, 0.88);
      monoLabel(s, iv.n, 0.68, 1.88 + i * 1.0, 0.4, B.signal);
      s.addText(iv.title, { x: 1.05, y: 1.82 + i * 1.0, w: 3.0, h: 0.28, fontSize: 11.5, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      body(s, iv.detail, 1.05, 2.1 + i * 1.0, 2.95, 0.38, B.dim, 9);
      monoLabel(s, iv.impact, 4.08, 1.88 + i * 1.0, 1.8, B.static);
    });

    // Re-simulation outcome (right column)
    card(s, 6.25, 1.74, 3.25, 2.88);
    monoLabel(s, "RE-SIMULATION OUTCOME", 6.42, 1.9, 3.0, B.static);
    s.addShape("rect", { x: 6.25, y: 2.12, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });

    // Before / After
    s.addText("98.0%", { x: 6.32, y: 2.22, w: 1.45, h: 0.72, fontSize: 34, bold: true, color: B.dim, fontFace: HEADING, margin: 0 });
    monoLabel(s, "BASELINE", 6.32, 2.94, 1.45, B.dim);
    s.addText("→", { x: 7.72, y: 2.3, w: 0.5, h: 0.6, fontSize: 22, color: B.static, fontFace: HEADING, align: "center", margin: 0 });
    s.addText("99%+", { x: 8.18, y: 2.22, w: 1.22, h: 0.72, fontSize: 34, bold: true, color: B.signal, fontFace: HEADING, margin: 0 });
    monoLabel(s, "PROJECTED", 8.18, 2.94, 1.22, B.static);

    s.addShape("rect", { x: 6.25, y: 3.18, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
    body(s, "Baseline already near-saturated. Interventions lock in subscription conversion and protect against drift at scale — subscription target: 25–30% of reorderers.", 6.38, 3.28, 3.0, 0.88, B.dim, 9.5);
    s.addShape("rect", { x: 6.25, y: 4.22, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
    body(s, "Test the fix in simulation before spending a rupee.", 6.38, 4.3, 3.0, 0.3, B.parchment, 10.5);

    footer(s, n);
  }

  // ─── SLIDE 14 · PROBLEM B — FINDING ──────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / PROBLEM B  ·  MAGNESIUM GUMMIES — INCREASING SALES");
    headline(s, "Increasing Magnesium\nGummies sales.", 0.72, 30);
    divider(s, 1.58);

    bigMetric(s, "32.5%", "TRIAL RATE", 0.5, 1.74, 2.1);
    bigMetric(s, "67.5%", "NON-BUYER RATE", 2.72, 1.74, 2.1, true);

    monoLabel(s, "67.5% NEVER TRIAL  ·  61-DAY JOURNEY  ·  200 PERSONAS  ·  AGE 3–8 COHORT", 0.5, 3.32, 9, B.static);

    card(s, 5.08, 1.74, 4.42, 2.45);
    monoLabel(s, "WHAT THE SIMULATION FOUND", 5.26, 1.9, 4.1, B.static);
    s.addShape("rect", { x: 5.08, y: 2.12, w: 0.03, h: 1.85, fill: { color: B.signal }, line: { color: B.signal } });
    body(s, "67.5% of parents never trialed. The #1 blocker: the pediatrician said 'magnesium deficiency is rare — focus on routine.' Community outcome data had 0% conversion effect. Only one signal broke through: explicit pediatrician validation.", 5.2, 2.12, 4.18, 1.32, B.parchment, 10.5);
    monoLabel(s, "B-P3 (pediatrician endorsement): 90.0% trial. B-P2 (community data): 0.0% trial. The validator, not the data, is the lever.", 5.26, 3.62, 4.1, B.dim);

    card(s, 0.5, 3.55, 4.42, 0.75);
    monoLabel(s, "HYPOTHESIS TREE", 0.68, 3.68, 4.0, B.static);
    const hB = [
      { v: "REJECTED",  t: "Community data drives trial" },
      { v: "PARTIAL",   t: "Extended trial window" },
      { v: "CONFIRMED", t: "Pediatrician voice" },
    ];
    hB.forEach((h, i) => {
      const hx = 0.68 + i * 1.45;
      s.addText(h.v, { x: hx, y: 3.88, w: 1.38, h: 0.2, fontSize: 7.5, bold: true,
        color: h.v === "CONFIRMED" ? B.signal : B.dim, fontFace: MONO, charSpacing: 0.5, margin: 0 });
      body(s, h.t, hx, 4.06, 1.38, 0.2, B.dim, 8.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 15 · PROBLEM B — INTERVENTIONS + RE-SIMULATION ────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / PROBLEM B  ·  INTERVENTION SIMULATION");
    headline(s, "Remove the pediatrician's veto.\nWatch trial — and reorders — follow.", 0.72, 30);
    divider(s, 1.58);

    const ivsB = [
      { n: "01", title: "Pediatrician Explicit Endorsement",    detail: "Partner with pediatricians to recommend magnesium gummies for sleep-routine parents. One positive recommendation converts 90% of skeptics (B-P3: 90.0%).", impact: "+57.5pp trial rate" },
      { n: "02", title: "In-App Sleep Outcome Tracking",        detail: "On-pack QR → app nightly log (3 questions, 60 seconds). Converts efficacy uncertainty into self-verified proof. 93.3% of trackers reordered (B-P1).", impact: "+70.2pp reorder rate" },
      { n: "03", title: "60-Day Extended Trial Window",         detail: "30 days is too short to attribute sleep changes to gummies. A 60-day 'see-for-yourself' trial period resolves the causation objection for 66.7% of deferring parents (B-P4).", impact: "+34.2pp trial rate" },
    ];
    ivsB.forEach((iv, i) => {
      card(s, 0.5, 1.74 + i * 1.0, 5.55, 0.88);
      monoLabel(s, iv.n, 0.68, 1.88 + i * 1.0, 0.4, B.signal);
      s.addText(iv.title, { x: 1.05, y: 1.82 + i * 1.0, w: 3.0, h: 0.28, fontSize: 11.5, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      body(s, iv.detail, 1.05, 2.1 + i * 1.0, 2.95, 0.38, B.dim, 9);
      monoLabel(s, iv.impact, 4.08, 1.88 + i * 1.0, 1.8, B.static);
    });

    card(s, 6.25, 1.74, 3.25, 2.88);
    monoLabel(s, "RE-SIMULATION OUTCOME", 6.42, 1.9, 3.0, B.static);
    s.addShape("rect", { x: 6.25, y: 2.12, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });

    s.addText("32.5%", { x: 6.32, y: 2.22, w: 1.45, h: 0.72, fontSize: 34, bold: true, color: B.dim, fontFace: HEADING, margin: 0 });
    monoLabel(s, "TRIAL BASELINE", 6.32, 2.94, 1.45, B.dim);
    s.addText("→", { x: 7.72, y: 2.3, w: 0.5, h: 0.6, fontSize: 22, color: B.static, fontFace: HEADING, align: "center", margin: 0 });
    s.addText("90.0%", { x: 8.18, y: 2.22, w: 1.22, h: 0.72, fontSize: 34, bold: true, color: B.signal, fontFace: HEADING, margin: 0 });
    monoLabel(s, "PROJECTED", 8.18, 2.94, 1.22, B.static);

    s.addShape("rect", { x: 6.25, y: 3.18, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
    body(s, "Pediatrician endorsement closes the acquisition gap. Among trialists, sleep tracking lifts reorder from 23.1% → 93.3% — resolving both the conversion and retention problem in one motion.", 6.38, 3.28, 3.0, 0.88, B.dim, 9.5);
    s.addShape("rect", { x: 6.25, y: 4.22, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
    body(s, "One endorsed recommendation costs less than one month of paid media.", 6.38, 4.3, 3.0, 0.3, B.parchment, 10.5);

    footer(s, n);
  }

  // ─── SLIDE 16 · PROBLEM C — FINDING ──────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / PROBLEM C  ·  EXPANDING NUTRIMIX INTO AGE 7–14");
    headline(s, "Expanding Nutrimix into\nthe school-age segment.", 0.72, 30);
    divider(s, 1.58);

    bigMetric(s, "37.2%", "TRIAL RATE", 0.5, 1.74, 2.1);
    bigMetric(s, "27.3%", "REORDER RATE", 2.72, 1.74, 2.1, true);

    monoLabel(s, "72.7% DID NOT REORDER  ·  148 PERSONAS  ·  RS 549 VS BOURNVITA RS 399  ·  AGE 7–14 COHORT", 0.5, 3.32, 9, B.static);

    card(s, 5.08, 1.74, 4.42, 2.45);
    monoLabel(s, "WHAT THE SIMULATION FOUND", 5.26, 1.9, 4.1, B.static);
    s.addShape("rect", { x: 5.08, y: 2.12, w: 0.03, h: 1.85, fill: { color: B.signal }, line: { color: B.signal } });
    body(s, "72.7% of trialists lapsed. Ingredient comparison (C-P1) had only 20% uptake — parents couldn't engage with nutrition data at the reorder moment. Family pack format (76.7%) and the child asking by name (73.3%) converted lapsers. Format, not facts.", 5.2, 2.12, 4.18, 1.32, B.parchment, 10.5);
    monoLabel(s, "The child asked for it by name. The parent hesitated at Rs 549. A Rs 1,099 family pack changed the mental accounting entirely.", 5.26, 3.62, 4.1, B.dim);

    card(s, 0.5, 3.55, 4.42, 0.75);
    monoLabel(s, "HYPOTHESIS TREE", 0.68, 3.68, 4.0, B.static);
    const hC = [
      { v: "REJECTED",  t: "Ingredient comparison" },
      { v: "CONFIRMED", t: "Family pack format" },
      { v: "CONFIRMED", t: "Child preference signal" },
    ];
    hC.forEach((h, i) => {
      const hx = 0.68 + i * 1.45;
      s.addText(h.v, { x: hx, y: 3.88, w: 1.38, h: 0.2, fontSize: 7.5, bold: true,
        color: h.v === "CONFIRMED" ? B.signal : B.dim, fontFace: MONO, charSpacing: 0.5, margin: 0 });
      body(s, h.t, hx, 4.06, 1.38, 0.2, B.dim, 8.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 17 · PROBLEM C — INTERVENTIONS + RE-SIMULATION ────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "LITTLEJOYS / PROBLEM C  ·  INTERVENTION SIMULATION");
    headline(s, "Give the family a pack.\nGive the child a voice.", 0.72, 30);
    divider(s, 1.58);

    const ivsC = [
      { n: "01", title: "Multi-Child Family Pack (Rs 1,099)",    detail: "Two 500g packs at Rs 549 each. Removes the per-child premium mental accounting and positions as a planned monthly household purchase. C-P2: 76.7% of lapsers convert.", impact: "+49.4pp reorder rate" },
      { n: "02", title: "Child Preference Reinforcement Signal", detail: "At Day 45: 'Your child asked for Nutrimix again — reorder in one tap.' Turns the child's preference into a purchase trigger for the parent. C-P4: 73.3% of lapsers convert.", impact: "+46.0pp reorder rate" },
      { n: "03", title: "Bournvita Comparison at Reorder Moment", detail: "Side-by-side iron, B12 and sugar content at the reorder screen. Partially effective — best for analytically-oriented segments. C-P3: 63.3% uptake.", impact: "+36.0pp reorder rate" },
    ];
    ivsC.forEach((iv, i) => {
      card(s, 0.5, 1.74 + i * 1.0, 5.55, 0.88);
      monoLabel(s, iv.n, 0.68, 1.88 + i * 1.0, 0.4, B.signal);
      s.addText(iv.title, { x: 1.05, y: 1.82 + i * 1.0, w: 3.0, h: 0.28, fontSize: 11.5, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      body(s, iv.detail, 1.05, 2.1 + i * 1.0, 2.95, 0.38, B.dim, 9);
      monoLabel(s, iv.impact, 4.08, 1.88 + i * 1.0, 1.8, B.static);
    });

    card(s, 6.25, 1.74, 3.25, 2.88);
    monoLabel(s, "RE-SIMULATION OUTCOME", 6.42, 1.9, 3.0, B.static);
    s.addShape("rect", { x: 6.25, y: 2.12, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });

    s.addText("27.3%", { x: 6.32, y: 2.22, w: 1.45, h: 0.72, fontSize: 34, bold: true, color: B.dim, fontFace: HEADING, margin: 0 });
    monoLabel(s, "REORDER BASELINE", 6.32, 2.94, 1.45, B.dim);
    s.addText("→", { x: 7.72, y: 2.3, w: 0.5, h: 0.6, fontSize: 22, color: B.static, fontFace: HEADING, align: "center", margin: 0 });
    s.addText("93.8%", { x: 8.18, y: 2.22, w: 1.22, h: 0.72, fontSize: 34, bold: true, color: B.signal, fontFace: HEADING, margin: 0 });
    monoLabel(s, "PROJECTED", 8.18, 2.94, 1.22, B.static);

    s.addShape("rect", { x: 6.25, y: 3.18, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
    body(s, "Family pack (76.7%) and child preference signal (73.3%) address independent segments. Combined, they convert 93.8% of lapsers — a 66.5pp lift on reorder rate from the baseline.", 6.38, 3.28, 3.0, 0.88, B.dim, 9.5);
    s.addShape("rect", { x: 6.25, y: 4.22, w: 3.25, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
    body(s, "No new product required. Two format and timing changes — tested in simulation before any spend.", 6.38, 4.3, 3.0, 0.3, B.parchment, 10.5);

    footer(s, n);
  }

  // ─── SLIDE 15 · CROSS-JOURNEY STATEMENT ─────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    monoLabel(s, "CROSS-JOURNEY SYNTHESIS", 0.5, 0.38, 6, B.static);

    s.addText("Each product has\none precise lever.", {
      x: 0.5, y: 0.82, w: 9, h: 2.4, fontSize: 56, bold: true, color: B.parchment, fontFace: HEADING, margin: 0,
    });
    divider(s, 3.35);

    const insights = [
      { n: "01", t: "Journey A (Probiotic): 98% trial, near-100% reorder. Trigger-based nurture closes the remaining lapse segment. The product is saturated — the lever is timing." },
      { n: "02", t: "Journey B (Magnesium Gummies): 32.5% trial, 23.1% reorder. A new category with one blocker — the pediatrician's veto. Fix that, and trial lifts to 90%; sleep tracking then takes reorder to 93.3%." },
      { n: "03", t: "Journey C (Nutrimix): 37.2% trial, 27.3% reorder → 93.8% with interventions. Not a price problem. A format and timing problem. Family pack + child preference signal resolved it entirely." },
    ];
    insights.forEach((ins, i) => {
      monoLabel(s, ins.n, 0.5 + i * 3.12, 3.55, 0.5, i === 0 ? B.signal : B.static);
      body(s, ins.t, 0.88 + i * 3.12, 3.52, 2.68, 1.4, B.dim, 11);
    });

    footer(s, n);
  }

  // ─── SLIDE 16 · 5 QUESTIONS ──────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "WHAT SIMULATTE ANSWERS");
    headline(s, "Five questions.\nAnswered in hours, not weeks.", 0.72, 30);
    divider(s, 1.65);

    const qs = [
      "Will our new product earn a second purchase — or just a curious first trial?",
      "Which consumer segment has the highest untapped conversion potential right now?",
      "What happens to our existing buyer base if we raise the price by 10%?",
      "Should we lead with the pediatrician, the peer, or the product — and for which segment?",
      "Between a loyalty programme, a tracking feature, and a referral mechanic — which moves the needle most?",
    ];
    qs.forEach((q, i) => {
      s.addShape("rect", { x: 0.5, y: 1.82 + i * 0.66, w: 9, h: 0.005, fill: { color: B.faint }, line: { color: B.faint } });
      monoLabel(s, `0${i + 1}`, 0.5, 1.88 + i * 0.66, 0.5, i === 0 ? B.signal : B.static);
      body(s, q, 1.0, 1.86 + i * 0.66, 8.2, 0.52, B.parchment, 12.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 17 · COMPARISON TABLE ────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "SIMULATTE VS TRADITIONAL RESEARCH");
    headline(s, "Not a supplement.\nA replacement.", 0.72, 34);
    divider(s, 1.55);

    // Table header
    const hx = 0.5, hy = 1.68;
    s.addShape("rect", { x: hx, y: hy, w: 9, h: 0.32, fill: { color: B.faint }, line: { color: B.faint } });
    [["DIMENSION", 0], ["TRADITIONAL RESEARCH", 3.4], ["SIMULATTE", 6.8]].forEach(([h, ox]) => {
      monoLabel(s, h, hx + ox, hy + 0.07, 3.2, B.static);
    });

    const rows = [
      ["Time to insight",    "6–12 weeks",                          "2–24 hours"],
      ["Cost per study",     "₹5–20L+",                            "Fraction of traditional"],
      ["Sample",             "100–500 real respondents",            "200+ synthetic personas"],
      ["Depth of finding",   "What (tick boxes)",                   "Why (5-step reasoning trace)"],
      ["Repeatability",      "One study, one result",               "Infinite re-runs, scenario comparison"],
      ["Bias",               "Response bias, recall error, desirability", "None — personas decide, not respondents"],
      ["Iteration speed",    "New study per question",              "New journey per question, same day"],
    ];
    rows.forEach((r, i) => {
      const ry = hy + 0.32 + i * 0.46;
      const bg = i % 2 === 0 ? "070707" : B.void;
      s.addShape("rect", { x: hx, y: ry, w: 9, h: 0.46, fill: { color: bg }, line: { color: B.faint, pt: 0.5 } });
      body(s, r[0], hx + 0.12, ry + 0.06, 3.1, 0.36, B.dim, 10.5);
      body(s, r[1], hx + 3.52, ry + 0.06, 3.1, 0.36, B.dim, 10.5);
      body(s, r[2], hx + 6.92, ry + 0.06, 2.9, 0.36, r[2].includes("Infinite") || r[2].includes("None") || r[2].includes("2–24") ? B.signal : B.parchment, 10.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 18 · WHO IT'S FOR ─────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "WHO SIMULATTE IS FOR");
    headline(s, "Built for brands that cannot\nafford to get it wrong.", 0.72, 32);
    divider(s, 1.65);

    const segments = [
      { label: "D2C BRANDS",           body: "You're spending on acquisition. You need to know what kills retention before you scale — not after your CAC breaks the model." },
      { label: "FMCG & NUTRITION",     body: "You're competing with legacy brands that have 70-year trust moats. You need to know exactly which argument breaks through — before you spend on it." },
      { label: "NEW CATEGORY CREATORS",body: "You're building a market that doesn't exist yet. You need to know which consumer concern is the wedge — and which is the wall." },
    ];
    segments.forEach((sg, i) => {
      const sx = 0.5 + i * 3.12;
      card(s, sx, 1.82, 2.9, 3.1);
      monoLabel(s, sg.label, sx + 0.18, 2.0, 2.55, i === 1 ? B.signal : B.static);
      s.addShape("line", { x: sx + 0.18, y: 2.3, w: 2.55, h: 0, line: { color: B.faint, pt: 0.75 } });
      body(s, sg.body, sx + 0.18, 2.42, 2.55, 2.3, B.parchment, 11.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 19 · HOW TO START ─────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };
    sectionLabel(s, "GETTING STARTED");
    headline(s, "One journey. One problem.\nOne answer. Then decide.", 0.72, 32);
    divider(s, 1.65);

    const steps = [
      { n: "01", t: "Define the problem",   b: "What decision are you trying to understand? Trial, reorder, switch, adoption — name the exact conversion moment." },
      { n: "02", t: "We build the journey", b: "Our team configures the stimuli schedule, decision scenarios, and cohort profile for your specific brand context." },
      { n: "03", t: "Explore the results",  b: "In 24–48 hours: 200 persona decisions, full reasoning traces, hypothesis verdicts, and specific interventions with projected impact." },
    ];
    steps.forEach((st, i) => {
      const sx = 0.5 + i * 3.12;
      card(s, sx, 1.82, 2.9, 3.1);
      s.addShape("rect", { x: sx, y: 1.82, w: 2.9, h: 0.12, fill: { color: i === 2 ? B.signal : B.faint }, line: { color: B.faint } });
      monoLabel(s, st.n, sx + 0.18, 2.06, 0.5, B.static);
      s.addText(st.t, { x: sx + 0.18, y: 2.36, w: 2.55, h: 0.5, fontSize: 15, bold: true, color: B.parchment, fontFace: HEADING, margin: 0 });
      s.addShape("line", { x: sx + 0.18, y: 2.9, w: 2.55, h: 0, line: { color: B.faint, pt: 0.75 } });
      body(s, st.b, sx + 0.18, 3.02, 2.55, 1.78, B.parchment, 11.5);
    });

    footer(s, n);
  }

  // ─── SLIDE 20 · CLOSING ──────────────────────────────────────────────────────
  {
    n++;
    const s = pres.addSlide();
    s.background = { color: B.void };

    for (let r = 0; r < 9; r++) {
      s.addShape("line", { x: 0, y: r * 0.7, w: W, h: 0, line: { color: "0D0D0D", pt: 0.5 } });
    }
    for (let c = 0; c < 15; c++) {
      s.addShape("line", { x: c * 0.72, y: 0, w: 0, h: H, line: { color: "0D0D0D", pt: 0.5 } });
    }

    s.addText("Simulate reality.\nDecide better.", {
      x: 0.5, y: 1.0, w: 9, h: 2.4, fontSize: 62, bold: true, color: B.parchment, fontFace: HEADING, margin: 0,
    });

    body(s, "Simulatte is decision infrastructure for the AI age. Built on behavioural science. Designed for practitioners who need outcomes, not reports.", 0.5, 3.55, 6.5, 0.7, B.dim, 13);

    s.addShape("line", { x: 0.5, y: 4.42, w: 4, h: 0, line: { color: B.faint, pt: 0.75 } });
    monoLabel(s, "simulatte.ai  ·  hello@simulatte.ai", 0.5, 4.56, 5, B.static);
    monoLabel(s, "STOP TESTING ON REALITY.", W - 4.5, 4.56, 4.0, B.signal);
  }

  await pres.writeFile({ fileName: OUT });
  console.log("✅  Written to", OUT);
}

build().catch(e => { console.error(e); process.exit(1); });
