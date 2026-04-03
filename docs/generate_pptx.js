// LittleJoys Platform Overview — pptxgenjs generator
// Run: node docs/generate_pptx.js
// Output: docs/LittleJoys_Platform_Overview.pptx

const PptxGenJS = require("pptxgenjs");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE"; // 13.33" x 7.5"

// ─── THEME ─────────────────────────────────────────────────────────────────
const C = {
  coral:   "FF6B6B",
  navy:    "1A2340",
  white:   "FFFFFF",
  offwhite:"F7F8FC",
  slate:   "2E3A52",
  mid:     "4A5568",
  light:   "8896A8",
  teal:    "4ECDC4",
  green:   "2ECC71",
  gold:    "F9C74F",
  bg:      "FFFFFF",
  darkbg:  "1A2340",
};

const FONT_TITLE = "Calibri";
const FONT_BODY  = "Calibri";

// ─── HELPERS ───────────────────────────────────────────────────────────────

/** Add a dark-background title slide */
function titleSlide(slide) {
  // Full dark background
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: "100%", h: "100%",
    fill: { color: C.darkbg },
  });
  // Coral accent bar on left
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: 0.22, h: "100%",
    fill: { color: C.coral },
  });
  // Subtle dot pattern (decorative circles)
  for (let i = 0; i < 5; i++) {
    slide.addShape(pptx.ShapeType.ellipse, {
      x: 10.5 + i * 0.55, y: 0.4 + i * 0.3, w: 0.35, h: 0.35,
      fill: { color: C.coral, transparency: 70 },
      line: { color: C.coral, transparency: 70 },
    });
  }
}

/** Add a light-background content slide with coral top bar */
function contentSlide(slide, title, opts = {}) {
  const { topBarHeight = 0.08 } = opts;
  // White background
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: "100%", h: "100%",
    fill: { color: C.offwhite },
  });
  // Thin coral top bar
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: "100%", h: topBarHeight,
    fill: { color: C.coral },
  });
  // Title text
  slide.addText(title, {
    x: 0.45, y: 0.18, w: 12.4, h: 0.65,
    fontFace: FONT_TITLE, fontSize: 28, bold: true, color: C.navy,
    valign: "middle",
  });
  // Thin divider under title
  slide.addShape(pptx.ShapeType.line, {
    x: 0.45, y: 0.87, w: 12.4, h: 0,
    line: { color: C.coral, width: 1.5 },
  });
}

/** Add a pill/chip shape with label */
function chip(slide, label, x, y, color = C.coral) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 1.9, h: 0.35,
    fill: { color }, rectRadius: 0.08,
    line: { color, width: 0 },
  });
  slide.addText(label, {
    x, y, w: 1.9, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11, bold: true, color: C.white,
    align: "center", valign: "middle",
  });
}

/** Bold-label + body text row helper */
function labelRow(slide, label, body, x, y, w = 11.8) {
  const combined = [
    { text: label + " ", options: { bold: true, color: C.navy, fontSize: 13 } },
    { text: body,        options: { bold: false, color: C.mid,  fontSize: 13 } },
  ];
  slide.addText(combined, { x, y, w, h: 0.32, fontFace: FONT_BODY, valign: "middle" });
}

/** Standard bullet list */
function bullets(slide, items, x, y, w, h, opts = {}) {
  const {
    fontSize = 14, color = C.slate, bullet = true, lineSpacingMultiple = 1.25,
    bold = false,
  } = opts;
  slide.addText(
    items.map(t => ({ text: t, options: { bullet, color, fontSize, bold } })),
    { x, y, w, h, fontFace: FONT_BODY, lineSpacingMultiple, valign: "top" }
  );
}

/** Numbered phase box */
function phaseBox(slide, num, label, x, y, color = C.coral) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 2.2, h: 1.1,
    fill: { color }, rectRadius: 0.1,
    line: { color, width: 0 },
  });
  slide.addText(String(num), {
    x, y: y + 0.02, w: 2.2, h: 0.48,
    fontFace: FONT_TITLE, fontSize: 28, bold: true, color: C.white,
    align: "center", valign: "middle",
  });
  slide.addText(label, {
    x, y: y + 0.52, w: 2.2, h: 0.52,
    fontFace: FONT_BODY, fontSize: 11, color: C.white,
    align: "center", valign: "middle", wrap: true,
  });
}

/** Stat callout box */
function statBox(slide, stat, label, x, y, bg = C.coral) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 2.5, h: 1.15,
    fill: { color: bg }, rectRadius: 0.12,
    line: { color: bg, width: 0 },
  });
  slide.addText(stat, {
    x, y: y + 0.08, w: 2.5, h: 0.6,
    fontFace: FONT_TITLE, fontSize: 32, bold: true, color: C.white,
    align: "center", valign: "middle",
  });
  slide.addText(label, {
    x, y: y + 0.65, w: 2.5, h: 0.42,
    fontFace: FONT_BODY, fontSize: 11, color: C.white,
    align: "center", valign: "middle", wrap: true,
  });
}

/** Funnel layer row */
function funnelRow(slide, num, label, desc, x, y, color) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 0.45, h: 0.42,
    fill: { color }, rectRadius: 0.06,
    line: { color, width: 0 },
  });
  slide.addText(String(num), {
    x, y, w: 0.45, h: 0.42,
    fontFace: FONT_TITLE, fontSize: 16, bold: true, color: C.white,
    align: "center", valign: "middle",
  });
  slide.addText(label, {
    x: x + 0.55, y, w: 2.2, h: 0.42,
    fontFace: FONT_BODY, fontSize: 14, bold: true, color: C.navy,
    valign: "middle",
  });
  slide.addText(desc, {
    x: x + 2.85, y, w: 9.0, h: 0.42,
    fontFace: FONT_BODY, fontSize: 12, color: C.mid,
    valign: "middle",
  });
}

/** Scenario card */
function scenarioCard(slide, name, price, ages, tags, x, y, color = C.navy) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 2.95, h: 1.6,
    fill: { color: C.white }, rectRadius: 0.1,
    line: { color, width: 1.2 },
  });
  // Top color band
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 2.95, h: 0.4,
    fill: { color }, rectRadius: 0.1,
    line: { color, width: 0 },
  });
  // Cover corners at bottom of band
  slide.addShape(pptx.ShapeType.rect, {
    x, y: y + 0.25, w: 2.95, h: 0.15,
    fill: { color }, line: { color, width: 0 },
  });
  slide.addText(name, {
    x: x + 0.12, y: y + 0.05, w: 2.7, h: 0.32,
    fontFace: FONT_TITLE, fontSize: 13, bold: true, color: C.white,
    valign: "middle",
  });
  slide.addText(price, {
    x: x + 0.12, y: y + 0.46, w: 1.2, h: 0.28,
    fontFace: FONT_BODY, fontSize: 15, bold: true, color: C.coral,
    valign: "middle",
  });
  slide.addText(`Ages ${ages}`, {
    x: x + 1.5, y: y + 0.46, w: 1.3, h: 0.28,
    fontFace: FONT_BODY, fontSize: 11, color: C.mid,
    valign: "middle",
  });
  slide.addText(tags, {
    x: x + 0.12, y: y + 0.8, w: 2.7, h: 0.72,
    fontFace: FONT_BODY, fontSize: 10.5, color: C.mid,
    valign: "top", wrap: true,
  });
}

/** Quadrant cell */
function quadrantCell(slide, title, items, x, y, w, h, bg = C.offwhite, border = C.coral) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    fill: { color: bg }, rectRadius: 0.1,
    line: { color: border, width: 1.0 },
  });
  slide.addText(title, {
    x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.36,
    fontFace: FONT_TITLE, fontSize: 13, bold: true, color: C.navy,
    valign: "middle",
  });
  slide.addText(
    items.map(t => ({ text: t, options: { bullet: { type: "bullet" }, fontSize: 11, color: C.slate } })),
    { x: x + 0.15, y: y + 0.5, w: w - 0.3, h: h - 0.62, fontFace: FONT_BODY, lineSpacingMultiple: 1.2, valign: "top" }
  );
}

/** Tech stack row */
function techRow(slide, label, value, x, y) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 0.06, h: 0.3,
    fill: { color: C.coral }, rectRadius: 0.03,
    line: { color: C.coral, width: 0 },
  });
  slide.addText(label, {
    x: x + 0.18, y, w: 2.0, h: 0.3,
    fontFace: FONT_BODY, fontSize: 12, bold: true, color: C.navy,
    valign: "middle",
  });
  slide.addText(value, {
    x: x + 2.3, y, w: 9.5, h: 0.3,
    fontFace: FONT_BODY, fontSize: 12, color: C.mid,
    valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  titleSlide(s);

  // Main title
  s.addText("LittleJoys\nPersona Simulation Engine", {
    x: 0.55, y: 1.35, w: 9.8, h: 2.4,
    fontFace: FONT_TITLE, fontSize: 44, bold: true, color: C.white,
    lineSpacingMultiple: 1.15,
  });

  // Subtitle
  s.addText("A Synthetic Research Platform for Kids Nutrition D2C in India", {
    x: 0.55, y: 3.85, w: 9.8, h: 0.6,
    fontFace: FONT_BODY, fontSize: 20, color: C.teal,
    lineSpacingMultiple: 1.2,
  });

  // Tagline
  s.addText("Understand 200 Indian parent households — without a single survey", {
    x: 0.55, y: 4.55, w: 9.8, h: 0.42,
    fontFace: FONT_BODY, fontSize: 15, color: C.light, italic: true,
  });

  // Divider
  s.addShape(pptx.ShapeType.line, {
    x: 0.55, y: 4.46, w: 5.5, h: 0,
    line: { color: C.coral, width: 1 },
  });

  // Bottom badge row
  const badges = ["200 Households", "4 Scenarios", "145 Attributes", "Phase A→C"];
  badges.forEach((b, i) => {
    chip(s, b, 0.55 + i * 2.05, 6.6, C.coral);
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 2 — THE PROBLEM
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "The Business Questions We Answer");

  // Left column — questions
  s.addText("Questions the platform resolves:", {
    x: 0.45, y: 1.02, w: 7.5, h: 0.3,
    fontFace: FONT_BODY, fontSize: 13, color: C.light, italic: true,
  });

  const questions = [
    "Which parent segments will actually buy a kids nutrition product?",
    "Where does the purchase funnel break down — and why?",
    "Which marketing or product interventions create the most lift?",
    "How do we test hypotheses on 200 synthetic households in minutes, not months?",
  ];
  questions.forEach((q, i) => {
    // Number circle
    s.addShape(pptx.ShapeType.ellipse, {
      x: 0.45, y: 1.38 + i * 0.92, w: 0.4, h: 0.4,
      fill: { color: C.coral }, line: { color: C.coral, width: 0 },
    });
    s.addText(String(i + 1), {
      x: 0.45, y: 1.38 + i * 0.92, w: 0.4, h: 0.4,
      fontFace: FONT_TITLE, fontSize: 15, bold: true, color: C.white,
      align: "center", valign: "middle",
    });
    s.addText(q, {
      x: 0.98, y: 1.35 + i * 0.92, w: 7.5, h: 0.46,
      fontFace: FONT_BODY, fontSize: 14, color: C.slate,
      valign: "middle", wrap: true,
    });
  });

  // Right panel — context card
  s.addShape(pptx.ShapeType.roundRect, {
    x: 9.1, y: 1.0, w: 3.7, h: 5.85,
    fill: { color: C.navy }, rectRadius: 0.14,
    line: { color: C.navy, width: 0 },
  });
  s.addText("Business Context", {
    x: 9.3, y: 1.18, w: 3.3, h: 0.38,
    fontFace: FONT_TITLE, fontSize: 15, bold: true, color: C.coral,
    align: "center",
  });
  const ctx = [
    "LittleJoys is a D2C kids nutrition brand in India",
    "4 products: Nutrimix 2–6, Nutrimix 7–14, Magnesium Gummies, ProteinMix",
    "4 unresolved adoption questions — each one a strategic bet",
    "Traditional research takes months and costs lakhs",
    "This platform answers them in seconds, repeatedly, for free",
  ];
  s.addText(
    ctx.map(t => ({ text: t, options: { bullet: { type: "bullet" }, fontSize: 12.5, color: C.offwhite } })),
    { x: 9.3, y: 1.62, w: 3.3, h: 5.0, fontFace: FONT_BODY, lineSpacingMultiple: 1.4, valign: "top" }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 3 — ARCHITECTURE
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Five-Phase Research Architecture");

  const phases = [
    ["1", "Population\nGeneration", C.coral],
    ["2", "Decision\nSimulation", C.navy],
    ["3", "Probing /\nResearch", "028090"],
    ["4", "Analysis\nLayer", "6C3483"],
    ["5", "Intervention\nSimulation", "1E8449"],
  ];

  phases.forEach(([num, label, color], i) => {
    phaseBox(s, num, label, 0.45 + i * 2.5, 1.05, color);
    // Arrow between boxes
    if (i < 4) {
      s.addShape(pptx.ShapeType.line, {
        x: 2.62 + i * 2.5, y: 1.6, w: 0.33, h: 0,
        line: { color: C.light, width: 1.5 },
      });
      s.addText("▶", {
        x: 2.87 + i * 2.5, y: 1.45, w: 0.2, h: 0.3,
        fontFace: FONT_BODY, fontSize: 10, color: C.light,
      });
    }
  });

  // Description rows
  const descs = [
    ["Phase 1", "200 synthetic Indian parent households built from real distributions + Gaussian copula + LLM narratives"],
    ["Phase 2", "4-layer purchase funnel (Need → Awareness → Consideration → Purchase) per persona × per scenario"],
    ["Phase 3", "Hybrid pipeline: LLM persona interviews + counterfactual simulations + statistical attribute probes"],
    ["Phase 4", "SHAP feature importance, barrier waterfall, cohort segmentation, trajectory clustering, executive summary"],
    ["Phase 5", "2×2 intervention quadrant (scope × temporality), lift calculation, ranked leaderboard"],
  ];

  descs.forEach(([label, desc], i) => {
    labelRow(s, label + ":", desc, 0.45, 2.45 + i * 0.73, 12.3);
    if (i < 4) {
      s.addShape(pptx.ShapeType.line, {
        x: 0.45, y: 2.76 + i * 0.73, w: 12.3, h: 0,
        line: { color: "E8EDF3", width: 0.8 },
      });
    }
  });

  // Footer note
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.82, w: 12.3, h: 0.42,
    fill: { color: "FFF3F3" }, rectRadius: 0.07,
    line: { color: C.coral, width: 0.8 },
  });
  s.addText("Each phase feeds the next. The full pipeline runs in under 30 seconds.", {
    x: 0.6, y: 6.82, w: 12.1, h: 0.42,
    fontFace: FONT_BODY, fontSize: 13, color: C.coral, italic: true,
    valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 4 — POPULATION GENERATION
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "200 Synthetic Households — Built From Real Distributions");

  // Stat boxes row
  statBox(s, "200", "Synthetic\nHouseholds",   0.45, 1.05, C.coral);
  statBox(s, "145", "Attributes\nPer Persona", 3.15, 1.05, C.navy);
  statBox(s, "30",  "Deep Personas\nWith Narratives", 5.85, 1.05, "028090");
  statBox(s, "42",  "Default Seed\n(Reproducible)", 8.55, 1.05, "6C3483");
  statBox(s, "<30s", "Full Pipeline\nRuntime",  11.25, 1.05, "1E8449");

  // Left bullet list
  const items = [
    "Sampled from validated Indian urban parent demographics (city tier, income, age, education)",
    "City tiers: Tier 1 Metro 45%, Tier 2 City 35%, Tier 3 Emerging 20%",
    "Parent age: 22–45, mean 32 yrs; children aged 2–14; 1–5 children per household",
    "Income: Tier 1 mean ₹18L/yr, Tier 2 ₹12L/yr, Tier 3 ₹7L/yr (truncated normal per tier)",
    "Psychographic attributes via Gaussian copula with validated inter-attribute correlations",
    "Conditional rule engine: working mothers +0.15 time scarcity, first-time parents +0.12 health anxiety",
    "Tier 3 households +0.10 authority bias, joint families +0.15 elder influence weight",
    "Same seed → identical 200 personas every run (NumPy + LLM cache keyed by SHA-256)",
  ];
  bullets(s, items, 0.45, 2.45, 12.3, 4.0, { fontSize: 13 });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 5 — PERSONA ANATOMY
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "145 Attributes Per Persona — Across 12 Dimensions");

  const dims = [
    { label: "Demographics",   fields: "city_tier · income_lpa · parent_age · family_structure · socioeconomic_class (A1–C2)" },
    { label: "Health",         fields: "immunity_concern · growth_concern · nutrition_gap_awareness · medical_authority_trust" },
    { label: "Psychology",     fields: "health_anxiety · risk_tolerance · information_need · decision_speed · mental_bandwidth" },
    { label: "Values",         fields: "supplement_belief · indie_brand_openness · best_for_my_child · transparency_importance" },
    { label: "Cultural",       fields: "dietary_culture · ayurveda_affinity · western_brand_trust · community_orientation" },
    { label: "Media",          fields: "primary_social_platform · ad_receptivity · digital_payment_comfort · discovery_channel" },
    { label: "Career",         fields: "employment_status · work_hours · perceived_time_scarcity · cooking_time_available" },
    { label: "Relationships",  fields: "primary_decision_maker · peer_influence · pediatrician_influence · child_pester_power" },
    { label: "Education",      fields: "education_level · science_literacy · label_reading_habit · ingredient_awareness" },
    { label: "Lifestyle",      fields: "clean_label_importance · wellness_trend_follower · parenting_philosophy · meal_planning" },
    { label: "Daily Routine",  fields: "shopping_platform · budget_consciousness · health_spend_priority · price_reference_point" },
    { label: "Emotional",      fields: "fear_appeal_responsiveness · aspirational_messaging · testimonial_impact · buyer_remorse" },
  ];

  const cols = 2;
  const rows = Math.ceil(dims.length / cols);
  const colW = 6.15;
  const rowH = 0.52;

  dims.forEach((d, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = 0.45 + col * 6.45;
    const y = 1.05 + row * rowH;

    // Label chip
    s.addShape(pptx.ShapeType.roundRect, {
      x, y: y + 0.06, w: 1.55, h: 0.3,
      fill: { color: C.coral }, rectRadius: 0.06,
      line: { color: C.coral, width: 0 },
    });
    s.addText(d.label, {
      x, y: y + 0.06, w: 1.55, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10.5, bold: true, color: C.white,
      align: "center", valign: "middle",
    });
    s.addText(d.fields, {
      x: x + 1.65, y, w: colW - 1.75, h: 0.46,
      fontFace: FONT_BODY, fontSize: 10.5, color: C.mid,
      valign: "middle", wrap: true,
    });
  });

  // Footer
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.92, w: 12.3, h: 0.35,
    fill: { color: "EBF5FB" }, rectRadius: 0.07,
    line: { color: "AED6F1", width: 0.8 },
  });
  s.addText("All continuous attributes are 0–1 unit intervals. All categoricals use validated enums. Identity layer is frozen (Pydantic, extra='forbid').", {
    x: 0.6, y: 6.92, w: 12.1, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11, color: C.navy, italic: true,
    valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 6 — LLM NARRATIVE GENERATION
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Deep Personas: First-Person Narratives From Claude");

  // Left column — bullets
  const items = [
    "30 of 200 personas receive a ~400-word narrative generated by Claude",
    "Narrative covers: household context, child health situation, shopping behaviour, brand beliefs",
    "K-means cluster-stratified selection ensures narrative diversity across the psychographic space",
    "Narratives are cached by SHA-256 prompt hash — re-runs skip LLM calls entirely",
    "Any persona with a narrative can be interviewed in natural language through the dashboard",
    "Interview engine: 20-turn structured dialogue with guardrails against AI disclosure",
  ];
  bullets(s, items, 0.45, 1.05, 7.2, 3.6, { fontSize: 13.5 });

  // Narrative excerpt card
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 4.78, w: 7.2, h: 2.45,
    fill: { color: "FFF8F8" }, rectRadius: 0.12,
    line: { color: C.coral, width: 1 },
  });
  s.addText("Example Narrative Excerpt", {
    x: 0.65, y: 4.9, w: 6.8, h: 0.32,
    fontFace: FONT_TITLE, fontSize: 12, bold: true, color: C.coral,
  });
  s.addText(
    '"Priya is a 34-year-old working mother in Mumbai\'s Bandra neighbourhood... She reads ingredient labels habitually, cross-references Amazon reviews with Instagram reels from paediatrician-backed handles, and distrusts anything that sounds like hollow marketing. She is not brand-loyal but highly ingredient-loyal: the first question is always \'what\'s actually in this?\'"',
    {
      x: 0.65, y: 5.25, w: 6.8, h: 1.84,
      fontFace: FONT_BODY, fontSize: 12.5, color: C.slate, italic: true,
      valign: "top", wrap: true,
    }
  );

  // Right panel — interview flow
  s.addShape(pptx.ShapeType.roundRect, {
    x: 7.9, y: 1.05, w: 4.9, h: 6.18,
    fill: { color: C.navy }, rectRadius: 0.14,
    line: { color: C.navy, width: 0 },
  });
  s.addText("Interview Flow", {
    x: 8.1, y: 1.22, w: 4.5, h: 0.38,
    fontFace: FONT_TITLE, fontSize: 14, bold: true, color: C.coral,
    align: "center",
  });
  const steps = [
    ["1", "Tier 2 selection", "K-means on psychographic matrix → 30 cluster-stratified personas"],
    ["2", "Narrative prompt", "Claude generates 400-word first-person identity story"],
    ["3", "Cache check", "SHA-256 of prompt → skip if cached in data/.llm_cache/"],
    ["4", "Interview session", "PM asks question → LLM role-plays persona response"],
    ["5", "Guardrails active", "Prevents AI self-disclosure, stays in character 20 turns"],
  ];
  steps.forEach(([n, title, desc], i) => {
    s.addShape(pptx.ShapeType.ellipse, {
      x: 8.15, y: 1.75 + i * 0.98, w: 0.35, h: 0.35,
      fill: { color: C.coral }, line: { color: C.coral, width: 0 },
    });
    s.addText(n, {
      x: 8.15, y: 1.75 + i * 0.98, w: 0.35, h: 0.35,
      fontFace: FONT_BODY, fontSize: 12, bold: true, color: C.white,
      align: "center", valign: "middle",
    });
    s.addText(title, {
      x: 8.6, y: 1.73 + i * 0.98, w: 3.9, h: 0.24,
      fontFace: FONT_BODY, fontSize: 12, bold: true, color: C.white,
      valign: "middle",
    });
    s.addText(desc, {
      x: 8.6, y: 1.97 + i * 0.98, w: 3.9, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10.5, color: C.light,
      valign: "top", wrap: true,
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 7 — DECISION ENGINE
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "4-Layer Purchase Funnel — Per Persona × Per Scenario");

  const colors = [C.coral, "E67E22", "8E44AD", "1A7A4A"];
  const layers = [
    ["0", "Need Recognition",
      "health_anxiety (×0.20) + nutrition_gap_awareness (×0.25) + child_health_proactivity (×0.20) + immunity/growth concerns × age relevance factor"],
    ["1", "Awareness",
      "marketing_budget × channel_match + paediatrician boost (+0.15) + school boost (+0.20) + influencer boost (+0.10) + WOM mass"],
    ["2", "Consideration",
      "trust (×0.30) + research_depth (×0.20) + cultural_fit (×0.15) + brand_openness (×0.20) + risk_factor (×0.15)"],
    ["3", "Purchase",
      "(value_core × benefit_mix) + emotional_pull − price_barrier − effort_barrier → clipped to [0,1]"],
  ];

  layers.forEach(([num, label, desc], i) => {
    funnelRow(s, num, label, desc, 0.45, 1.12 + i * 0.82, colors[i]);
    if (i < 3) {
      s.addShape(pptx.ShapeType.line, {
        x: 0.45, y: 1.53 + i * 0.82, w: 12.3, h: 0,
        line: { color: "E8EDF3", width: 0.8 },
      });
    }
  });

  // Rejection taxonomy
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 4.42, w: 7.8, h: 1.95,
    fill: { color: "FFF3F3" }, rectRadius: 0.1,
    line: { color: C.coral, width: 0.8 },
  });
  s.addText("Rejection Reasons (labelled at each exit)", {
    x: 0.65, y: 4.52, w: 7.4, h: 0.3,
    fontFace: FONT_TITLE, fontSize: 12.5, bold: true, color: C.coral,
  });
  const reasons = [
    "age_irrelevant · low_need (Layer 0)",
    "low_awareness (Layer 1)",
    "dietary_incompatible · insufficient_trust · insufficient_research (Layer 2)",
    "price_too_high · effort_too_high · insufficient_trust (Layer 3)",
  ];
  bullets(s, reasons, 0.65, 4.85, 7.4, 1.42, { fontSize: 12, bullet: true });

  // Right — calibration box
  s.addShape(pptx.ShapeType.roundRect, {
    x: 8.5, y: 4.42, w: 4.3, h: 1.95,
    fill: { color: C.navy }, rectRadius: 0.1,
    line: { color: C.navy, width: 0 },
  });
  s.addText("Calibration Target", {
    x: 8.7, y: 4.55, w: 3.9, h: 0.32,
    fontFace: FONT_TITLE, fontSize: 13, bold: true, color: C.coral,
    align: "center",
  });
  s.addText("12–18%", {
    x: 8.7, y: 4.92, w: 3.9, h: 0.62,
    fontFace: FONT_TITLE, fontSize: 36, bold: true, color: C.white,
    align: "center",
  });
  s.addText("First-purchase adoption rate\n(binary search calibration)", {
    x: 8.7, y: 5.56, w: 3.9, h: 0.62,
    fontFace: FONT_BODY, fontSize: 11.5, color: C.light,
    align: "center", valign: "top",
  });

  // Footer note
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.55, w: 12.3, h: 0.35,
    fill: { color: "EBF5FB" }, rectRadius: 0.07,
    line: { color: "AED6F1", width: 0.8 },
  });
  s.addText("Each layer threshold is configurable per scenario. Thresholds calibrated via binary search to match real-world first-purchase rates.", {
    x: 0.6, y: 6.55, w: 12.1, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11, color: C.navy, italic: true,
    valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 8 — SCENARIOS
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Four Pre-Built Scenarios, Fully Configurable");

  const scenColors = [C.coral, C.navy, "028090", "6C3483"];
  const scens = [
    { name: "Nutrimix 2–6", price: "₹599", ages: "2–6",
      tags: "Nutrition powder · Immunity/Growth · Pediatrician + Instagram · LJ Pass · Temporal 6-month" },
    { name: "Nutrimix 7–14", price: "₹649", ages: "7–14",
      tags: "Nutrition powder · Focus/Energy · School partnership · Brand extension test · Temporal 12-month" },
    { name: "MagBites Gummies", price: "₹499", ages: "4–12",
      tags: "Supplement gummies · Sleep/Calm/Focus · New category · Awareness challenge · Static" },
    { name: "ProteinMix", price: "₹799", ages: "6–14",
      tags: "Protein supplement · Muscle/Growth · High effort · Sports club channel · Static" },
  ];

  scens.forEach((sc, i) => {
    scenarioCard(s, sc.name, sc.price, sc.ages, sc.tags, 0.45 + i * 3.15, 1.05, scenColors[i]);
  });

  // Config anatomy
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 2.82, w: 12.3, h: 1.7,
    fill: { color: "F0F3F7" }, rectRadius: 0.1,
    line: { color: "D5DCE8", width: 0.8 },
  });
  s.addText("Scenario Config Anatomy", {
    x: 0.65, y: 2.92, w: 11.9, h: 0.32,
    fontFace: FONT_TITLE, fontSize: 13, bold: true, color: C.navy,
  });
  const configCols = [
    { label: "ProductConfig", items: ["name, category, price_inr", "age_range, key_benefits", "taste_appeal, clean_label_score", "effort_to_acquire, subscription_available"] },
    { label: "MarketingConfig", items: ["awareness_budget (0–1)", "channel_mix (sums to 1.0)", "trust_signals list", "pediatrician / school / influencer flags"] },
    { label: "LJPassConfig", items: ["monthly_price: ₹299", "discount: 15%", "free_trial: 1 month", "retention_boost: +10%"] },
    { label: "Thresholds", items: ["need_recognition: 0.35", "awareness: 0.30", "consideration: 0.40", "purchase: 0.45"] },
  ];
  configCols.forEach((c, i) => {
    s.addText(c.label, {
      x: 0.65 + i * 3.05, y: 3.28, w: 2.9, h: 0.28,
      fontFace: FONT_BODY, fontSize: 12, bold: true, color: C.coral,
    });
    s.addText(c.items.join("\n"), {
      x: 0.65 + i * 3.05, y: 3.58, w: 2.9, h: 0.85,
      fontFace: FONT_BODY, fontSize: 10.5, color: C.mid,
      valign: "top", wrap: true,
    });
  });

  // LJ Pass callout
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 4.68, w: 12.3, h: 0.55,
    fill: { color: "FFF3F3" }, rectRadius: 0.08,
    line: { color: C.coral, width: 0.8 },
  });
  s.addText("LJ Pass (Subscription Layer):", {
    x: 0.65, y: 4.68, w: 2.8, h: 0.55,
    fontFace: FONT_BODY, fontSize: 13, bold: true, color: C.coral,
    valign: "middle",
  });
  s.addText("₹299/month · 15% discount on all purchases · 1 free trial month · +10% retention boost · –20% churn reduction. Available for Nutrimix 2–6 and Nutrimix 7–14.", {
    x: 3.5, y: 4.68, w: 9.0, h: 0.55,
    fontFace: FONT_BODY, fontSize: 12.5, color: C.slate,
    valign: "middle",
  });

  // Bottom bullets
  bullets(s, [
    "All scenario parameters are configurable in real-time from the dashboard — price, channel mix, trust signals, thresholds",
    "Scenario modifications use dot-path notation (e.g. 'marketing.pediatrician_endorsement': True) for counterfactual interventions",
  ], 0.45, 5.42, 12.3, 0.9, { fontSize: 13 });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 9 — PROBING PIPELINE
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Hybrid Research: LLM Interviews + Simulations + Statistics");

  // Probe type cards (3 cards)
  const probeCards = [
    { color: C.coral, icon: "💬", title: "Interview Probe",
      lines: ["LLM role-plays persona", "Structured open question", "15 personas sampled (stratified)", "k-means clusters responses", "→ Themes + representative quotes"] },
    { color: "028090", icon: "⚙️", title: "Simulation Probe",
      lines: ["Scenario modified via dot-path", "Re-run against full population", "adoption_lift = modified − baseline", "→ Lift %  and rejection shift"] },
    { color: "6C3483", icon: "📊", title: "Attribute Probe",
      lines: ["Adopters vs Rejectors split", "Cohen's d effect size per field", "Sorted by effect magnitude", "→ AttributeSplit list"] },
  ];

  probeCards.forEach((c, i) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: 0.45 + i * 4.2, y: 1.05, w: 3.95, h: 3.1,
      fill: { color: C.white }, rectRadius: 0.12,
      line: { color: c.color, width: 1.5 },
    });
    s.addShape(pptx.ShapeType.roundRect, {
      x: 0.45 + i * 4.2, y: 1.05, w: 3.95, h: 0.52,
      fill: { color: c.color }, rectRadius: 0.12,
      line: { color: c.color, width: 0 },
    });
    s.addShape(pptx.ShapeType.rect, {
      x: 0.45 + i * 4.2, y: 1.38, w: 3.95, h: 0.2,
      fill: { color: c.color }, line: { color: c.color, width: 0 },
    });
    s.addText(c.title, {
      x: 0.6 + i * 4.2, y: 1.1, w: 3.65, h: 0.38,
      fontFace: FONT_TITLE, fontSize: 14, bold: true, color: C.white,
      valign: "middle",
    });
    s.addText(
      c.lines.map(t => ({ text: t, options: { bullet: { type: "bullet" }, fontSize: 12.5, color: C.slate } })),
      { x: 0.6 + i * 4.2, y: 1.62, w: 3.65, h: 2.44, fontFace: FONT_BODY, lineSpacingMultiple: 1.3, valign: "top" }
    );
  });

  // Tree structure
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 4.3, w: 12.3, h: 2.0,
    fill: { color: "F0F3F7" }, rectRadius: 0.1,
    line: { color: "D5DCE8", width: 0.8 },
  });
  s.addText("Probing Tree Structure", {
    x: 0.65, y: 4.4, w: 11.9, h: 0.32,
    fontFace: FONT_TITLE, fontSize: 13, bold: true, color: C.navy,
  });

  // Tree diagram (text-based)
  const treeItems = [
    { level: 0, text: "ProblemStatement: 'How can we improve repeat purchase for NutriMix?'", x: 0.65, y: 4.76 },
    { level: 1, text: "Hypothesis 1: Doctor-backed proof unlocks first trial", x: 1.3, y: 5.14 },
    { level: 2, text: "Interview Probe · Simulation Probe · Attribute Probe", x: 2.0, y: 5.46 },
    { level: 1, text: "Hypothesis 2: Lower effort and price-framing improve trial", x: 1.3, y: 5.74 },
  ];
  treeItems.forEach(item => {
    s.addText(item.text, {
      x: item.x, y: item.y, w: 11.5 - item.x + 0.65, h: 0.3,
      fontFace: FONT_BODY, fontSize: 11.5, color: item.level === 0 ? C.navy : item.level === 1 ? C.slate : C.light,
      valign: "middle", bold: item.level === 0,
    });
  });

  // Stats footer
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.52, w: 12.3, h: 0.35,
    fill: { color: C.navy }, rectRadius: 0.07,
    line: { color: C.navy, width: 0 },
  });
  s.addText("13 business questions · 4 predefined full trees · 9 lightweight trees · HypothesisVerdict + TreeSynthesis produced per run", {
    x: 0.6, y: 6.52, w: 12.1, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11.5, color: C.white,
    align: "center", valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 10 — ANALYSIS LAYER
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "From Raw Results to Decision-Quality Insights");

  const analyses = [
    {
      title: "SHAP Feature Importance",
      color: C.coral,
      lines: ["LogisticRegression + LinearExplainer on all 145 attributes", "Ranked by mean |SHAP| across population", "Example: 'Health Worry Level > 0.62 → 2.4× more likely to adopt'", "Segment-level splits by city_tier and income_bracket"],
    },
    {
      title: "Barrier Waterfall",
      color: C.navy,
      lines: ["36% rejections at Consideration (primary bottleneck)", "29% at Need Recognition · 23% at Purchase · 13% at Awareness", "Per-stage top reasons ranked by count", "Powers the waterfall visualisation on the Results page"],
    },
    {
      title: "Cohort Segmentation",
      color: "028090",
      lines: ["Pre-defined cohorts: lapsed users, trust skeptics, time-scarce parents", "high-need rejecters, first-time buyers, committed users", "Trajectory k-means on 12-month active/inactive time series", "Cohort IDs used as target_cohort_id in Phase C interventions"],
    },
    {
      title: "Executive Summary",
      color: "6C3483",
      lines: ["Claude LLM generates PM-ready narrative (Haiku, temp=0.4)", "Fields: headline · trajectory_summary · 3 key_drivers", "3 recommendations · 2 risk_factors · mock_mode fallback", "Input: monthly active counts, cluster breakdown, top intervention"],
    },
  ];

  analyses.forEach((a, i) => {
    const row = Math.floor(i / 2);
    const col = i % 2;
    const x = 0.45 + col * 6.3;
    const y = 1.05 + row * 2.65;

    s.addShape(pptx.ShapeType.roundRect, {
      x, y, w: 6.05, h: 2.45,
      fill: { color: C.white }, rectRadius: 0.12,
      line: { color: a.color, width: 1.2 },
    });
    s.addShape(pptx.ShapeType.roundRect, {
      x, y, w: 6.05, h: 0.44,
      fill: { color: a.color }, rectRadius: 0.12,
      line: { color: a.color, width: 0 },
    });
    s.addShape(pptx.ShapeType.rect, {
      x, y: y + 0.3, w: 6.05, h: 0.14,
      fill: { color: a.color }, line: { color: a.color, width: 0 },
    });
    s.addText(a.title, {
      x: x + 0.18, y: y + 0.06, w: 5.65, h: 0.34,
      fontFace: FONT_TITLE, fontSize: 14, bold: true, color: C.white,
      valign: "middle",
    });
    s.addText(
      a.lines.map(t => ({ text: t, options: { bullet: { type: "bullet" }, fontSize: 12, color: C.slate } })),
      { x: x + 0.18, y: y + 0.5, w: 5.65, h: 1.88, fontFace: FONT_BODY, lineSpacingMultiple: 1.25, valign: "top" }
    );
  });

  // Footer
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.55, w: 12.3, h: 0.35,
    fill: { color: "FFF3F3" }, rectRadius: 0.07,
    line: { color: C.coral, width: 0.8 },
  });
  s.addText("All analysis is reproducible — same population + scenario → same SHAP rankings, same barrier distribution, same executive summary (mock mode).", {
    x: 0.6, y: 6.55, w: 12.1, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11, color: C.coral, italic: true,
    valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 11 — INTERVENTION SIMULATION
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Phase C: Test Interventions Before Spending a Rupee");

  // Axis labels
  s.addText("NON-TEMPORAL\n(One-shot changes)", {
    x: 2.85, y: 1.05, w: 3.1, h: 0.45,
    fontFace: FONT_BODY, fontSize: 11.5, bold: true, color: C.navy,
    align: "center", valign: "middle",
  });
  s.addText("TEMPORAL\n(Sustained over months)", {
    x: 6.15, y: 1.05, w: 3.1, h: 0.45,
    fontFace: FONT_BODY, fontSize: 11.5, bold: true, color: C.navy,
    align: "center", valign: "middle",
  });

  // Row labels
  s.addText("GENERAL\n(All personas)", {
    x: 0.45, y: 1.55, w: 2.25, h: 1.95,
    fontFace: FONT_BODY, fontSize: 11.5, bold: true, color: C.navy,
    align: "center", valign: "middle",
  });
  s.addText("COHORT-\nSPECIFIC", {
    x: 0.45, y: 3.6, w: 2.25, h: 1.95,
    fontFace: FONT_BODY, fontSize: 11.5, bold: true, color: C.navy,
    align: "center", valign: "middle",
  });

  // Quadrant cells
  quadrantCell(s, "General · Non-Temporal",
    ["15% Returning Customer Discount", "Free Sample of New Flavour", "Pediatrician Endorsement Campaign (+4pp lift)"],
    2.85, 1.55, 3.1, 1.95, "FFF8F8", C.coral);

  quadrantCell(s, "General · Temporal",
    ["LJ Pass ₹199/quarter (+2.5pp + 23% revenue lift)", "Monthly Recipe Content Subscription", "Brand Ambassador Program"],
    6.15, 1.55, 3.1, 1.95, "F0FFF4", "1E8449");

  quadrantCell(s, "Cohort · Non-Temporal",
    ["Lapsed Users: ₹100 Coupon (+5.7pp within cohort)", "First-time Buyers: Starter Kit Bundle Discount", "Current Users: Referral Reward ₹150"],
    2.85, 3.6, 3.1, 1.95, "F0F8FF", C.navy);

  quadrantCell(s, "Cohort · Temporal",
    ["Lapsed: Day-22 Reminder + Flavour Rotation", "Current: Loyalty Tier Program (Bronze→Gold)", "First-time: 90-day Habit Formation Nudge Sequence"],
    6.15, 3.6, 3.1, 1.95, "F8F0FF", "6C3483");

  // Right summary panel
  s.addShape(pptx.ShapeType.roundRect, {
    x: 9.45, y: 1.55, w: 3.4, h: 5.55,
    fill: { color: C.navy }, rectRadius: 0.12,
    line: { color: C.navy, width: 0 },
  });
  s.addText("Lift Calculation", {
    x: 9.65, y: 1.7, w: 3.0, h: 0.34,
    fontFace: FONT_TITLE, fontSize: 13, bold: true, color: C.coral,
    align: "center",
  });
  s.addText("adoption_lift_pp\n= intervention_rate\n− baseline_rate", {
    x: 9.65, y: 2.1, w: 3.0, h: 0.85,
    fontFace: "Consolas", fontSize: 11, color: C.teal,
    align: "center",
  });
  s.addText("adoption_lift_pct\n= lift_pp / baseline\n× 100", {
    x: 9.65, y: 3.0, w: 3.0, h: 0.75,
    fontFace: "Consolas", fontSize: 11, color: C.teal,
    align: "center",
  });
  s.addText("48 total interventions\nacross 4 scenarios", {
    x: 9.65, y: 3.88, w: 3.0, h: 0.55,
    fontFace: FONT_BODY, fontSize: 12, color: C.white,
    align: "center",
  });
  s.addText("Temporal runs use\nfull event engine:\ndaily stochastic\nfiring of ad exposures,\ndoctor recommendations,\npack depletion reminders,\nchild reactions", {
    x: 9.65, y: 4.5, w: 3.0, h: 2.42,
    fontFace: FONT_BODY, fontSize: 11, color: C.light,
    align: "center", valign: "top",
  });

  // Bottom footer note
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.82, w: 8.85, h: 0.35,
    fill: { color: "F0F3F7" }, rectRadius: 0.07,
    line: { color: "D5DCE8", width: 0.8 },
  });
  s.addText("Interventions ranked by lift within each quadrant → leaderboard output on the Simulate dashboard page.", {
    x: 0.6, y: 6.82, w: 8.65, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11, color: C.navy, italic: true,
    valign: "middle",
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 12 — RESULTS & OUTPUTS
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "What the Platform Produces");

  const outputSections = [
    {
      title: "Quantitative Outputs",
      color: C.coral,
      items: [
        "Adoption rates by scenario, city tier, income bracket, employment status",
        "Funnel drop-off counts per stage and rejection reason",
        "SHAP variable importance rankings (145 attributes ranked)",
        "Intervention lift percentages (pp and % vs baseline)",
        "Monthly active rate trajectory for temporal scenarios",
      ],
    },
    {
      title: "Qualitative Outputs",
      color: C.navy,
      items: [
        "Themed interview clusters with representative quotes",
        "LLM-generated causal insight statements (grounded in SHAP)",
        "PM-ready executive summary (headline + trajectory + drivers + recommendations + risks)",
        "Hypothesis verdicts with confidence scores",
        "Intervention expected mechanisms",
      ],
    },
    {
      title: "Visualisations",
      color: "028090",
      items: [
        "Funnel waterfall chart (population at each layer + reasons)",
        "Psychographic 2D scatter coloured by adoption outcome",
        "Monthly active rate line chart (temporal scenarios)",
        "Intervention lift bar chart ranked by quadrant",
        "Cohort comparison tables",
      ],
    },
    {
      title: "Exports & Reproducibility",
      color: "6C3483",
      items: [
        "PDF research report (executive summary + SHAP + barriers + interviews)",
        "JSON population snapshots (all 200 personas, fully serialised)",
        "CSV decision results (one row per persona per scenario)",
        "Same seed → identical personas → identical results every run",
        "LLM cache ensures zero re-billing on re-runs",
      ],
    },
  ];

  outputSections.forEach((sec, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.45 + col * 6.3;
    const y = 1.05 + row * 2.72;

    s.addShape(pptx.ShapeType.roundRect, {
      x, y, w: 6.05, h: 2.52,
      fill: { color: C.white }, rectRadius: 0.12,
      line: { color: sec.color, width: 1.2 },
    });
    s.addShape(pptx.ShapeType.roundRect, {
      x, y, w: 6.05, h: 0.42,
      fill: { color: sec.color }, rectRadius: 0.12,
      line: { color: sec.color, width: 0 },
    });
    s.addShape(pptx.ShapeType.rect, {
      x, y: y + 0.28, w: 6.05, h: 0.14,
      fill: { color: sec.color }, line: { color: sec.color, width: 0 },
    });
    s.addText(sec.title, {
      x: x + 0.18, y: y + 0.06, w: 5.65, h: 0.32,
      fontFace: FONT_TITLE, fontSize: 13.5, bold: true, color: C.white,
      valign: "middle",
    });
    s.addText(
      sec.items.map(t => ({ text: t, options: { bullet: { type: "bullet" }, fontSize: 11.5, color: C.slate } })),
      { x: x + 0.18, y: y + 0.48, w: 5.65, h: 1.96, fontFace: FONT_BODY, lineSpacingMultiple: 1.22, valign: "top" }
    );
  });

  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.62, w: 12.3, h: 0.6,
    fill: { color: C.navy }, rectRadius: 0.08,
    line: { color: C.navy, width: 0 },
  });
  s.addText("All outputs feed each other: SHAP findings inform intervention selection; interview themes confirm quantitative signals; executive summary synthesises everything into one PM-ready document.", {
    x: 0.6, y: 6.62, w: 12.1, h: 0.6,
    fontFace: FONT_BODY, fontSize: 12, color: C.white,
    align: "center", valign: "middle", wrap: true,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 13 — TECH STACK
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Technology Stack");

  const stack = [
    ["Language",        "Python 3.11"],
    ["Data Models",     "Pydantic v2 — strict frozen identity models, extra='forbid', model validators"],
    ["LLM",             "Anthropic Claude — Sonnet (interviews), Haiku (exec summary), Opus (ReportAgent)"],
    ["ML / Stats",      "scikit-learn (LogisticRegression, KMeans), SHAP (LinearExplainer), NumPy, SciPy"],
    ["Visualisation",   "Plotly (all charts), Streamlit (dashboard + multi-page routing)"],
    ["Simulation",      "Custom event engine — daily stochastic dynamics, WOM propagation, habit formation"],
    ["Testing",         "pytest, 700+ tests, 80%+ coverage target, smoke tests across all 4 scenarios"],
    ["Infrastructure",  "uv (package management), structlog (structured logging), Pydantic Settings"],
    ["Caching",         "LLM responses cached by SHA-256 in data/.llm_cache/ — zero re-billing on re-runs"],
    ["Serialisation",   "JSON (population snapshots in data/population/), file-based, no database required"],
  ];

  stack.forEach(([label, value], i) => {
    techRow(s, label, value, 0.45, 1.12 + i * 0.53);
    if (i < stack.length - 1) {
      s.addShape(pptx.ShapeType.line, {
        x: 0.45, y: 1.42 + i * 0.53, w: 12.3, h: 0,
        line: { color: "E8EDF3", width: 0.7 },
      });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 14 — DEPLOYMENT
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  contentSlide(s, "Deployment and Access");

  // Left column — deployment details
  const deployItems = [
    ["Hosting",       "Render cloud (Python web service, auto-deploy from main branch)"],
    ["Demo Mode",     "Runs without API key — mock LLM, fixture personas, zero cost"],
    ["Population",    "Pre-generated and serialised to data/population/ as JSON files"],
    ["LLM Cache",     "SHA-256 keyed responses in data/.llm_cache/ — skips API on re-runs"],
    ["Storage",       "File-based only — no database, no external state, fully portable"],
    ["Local Run",     "streamlit run app/streamlit_app.py"],
    ["Dependencies",  "Python 3.11, managed via pyproject.toml + uv.lock"],
  ];

  deployItems.forEach(([label, value], i) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: 0.45, y: 1.08 + i * 0.72, w: 1.8, h: 0.46,
      fill: { color: C.coral }, rectRadius: 0.07,
      line: { color: C.coral, width: 0 },
    });
    s.addText(label, {
      x: 0.45, y: 1.08 + i * 0.72, w: 1.8, h: 0.46,
      fontFace: FONT_BODY, fontSize: 12, bold: true, color: C.white,
      align: "center", valign: "middle",
    });
    s.addText(value, {
      x: 2.4, y: 1.08 + i * 0.72, w: 6.1, h: 0.46,
      fontFace: FONT_BODY, fontSize: 13, color: C.slate,
      valign: "middle",
    });
  });

  // Right panel
  s.addShape(pptx.ShapeType.roundRect, {
    x: 8.75, y: 1.05, w: 4.05, h: 5.95,
    fill: { color: C.navy }, rectRadius: 0.14,
    line: { color: C.navy, width: 0 },
  });
  s.addText("Quick Start", {
    x: 8.95, y: 1.22, w: 3.65, h: 0.36,
    fontFace: FONT_TITLE, fontSize: 15, bold: true, color: C.coral,
    align: "center",
  });

  const cmds = [
    ["git clone <repo>", "Clone the repository"],
    ["uv sync", "Install all dependencies"],
    ["cp .env.example .env", "Configure API key"],
    ["python scripts/generate.py", "Pre-generate population"],
    ["streamlit run app/streamlit_app.py", "Launch dashboard"],
  ];
  cmds.forEach(([cmd, desc], i) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: 8.95, y: 1.72 + i * 0.95, w: 3.65, h: 0.52,
      fill: { color: "0D1A30" }, rectRadius: 0.07,
      line: { color: C.teal, width: 0.5 },
    });
    s.addText(cmd, {
      x: 9.08, y: 1.72 + i * 0.95, w: 3.38, h: 0.28,
      fontFace: "Consolas", fontSize: 11, color: C.teal,
      valign: "middle",
    });
    s.addText(desc, {
      x: 9.08, y: 1.99 + i * 0.95, w: 3.38, h: 0.22,
      fontFace: FONT_BODY, fontSize: 10, color: C.light,
      valign: "middle",
    });
  });

  // Footer
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.45, y: 6.62, w: 8.15, h: 0.6,
    fill: { color: "F0F3F7" }, rectRadius: 0.08,
    line: { color: "D5DCE8", width: 0.8 },
  });
  s.addText("render.yaml configures cloud deployment. runtime.txt pins Python 3.11. uv.lock ensures dependency reproducibility across environments.", {
    x: 0.6, y: 6.62, w: 7.95, h: 0.6,
    fontFace: FONT_BODY, fontSize: 11.5, color: C.mid,
    valign: "middle", wrap: true,
  });
}

// ─── WRITE ──────────────────────────────────────────────────────────────────
pptx.writeFile({ fileName: "docs/LittleJoys_Platform_Overview.pptx" })
  .then(() => console.log("✅ Saved: docs/LittleJoys_Platform_Overview.pptx"))
  .catch(err => { console.error("❌ Error:", err); process.exit(1); });
