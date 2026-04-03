const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  PageNumber, PageBreak, TabStopType, TabStopPosition,
  ExternalHyperlink
} = require("docx");

// ── colour palette ──────────────────────────────────────────────
const C = {
  primary:   "1B4F72",  // deep navy
  accent:    "2E86C1",  // blue
  highlight: "D5E8F0",  // light blue bg
  green:     "27AE60",
  orange:    "E67E22",
  red:       "C0392B",
  grey:      "7F8C8D",
  lightGrey: "F2F3F4",
  white:     "FFFFFF",
  black:     "1C1C1C",
};

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

// ── helpers ─────────────────────────────────────────────────────
function heading(text, level) {
  return new Paragraph({ heading: level, children: [new TextRun({ text, bold: true })] });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    ...opts.paraOpts,
    children: [new TextRun({ text, size: 22, font: "Arial", ...opts })]
  });
}

function boldPara(label, text) {
  return new Paragraph({
    spacing: { after: 120 },
    children: [
      new TextRun({ text: label, bold: true, size: 22, font: "Arial" }),
      new TextRun({ text, size: 22, font: "Arial" }),
    ]
  });
}

function bulletItem(text, ref = "bullets", level = 0) {
  return new Paragraph({
    numbering: { reference: ref, level },
    spacing: { after: 60 },
    children: [new TextRun({ text, size: 22, font: "Arial" })]
  });
}

function numberedItem(text, ref = "numbers", level = 0) {
  return new Paragraph({
    numbering: { reference: ref, level },
    spacing: { after: 60 },
    children: [new TextRun({ text, size: 22, font: "Arial" })]
  });
}

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: C.primary, type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: C.white, size: 20, font: "Arial" })] })]
  });
}

function cell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    margins: cellMargins,
    children: [new Paragraph({ children: [new TextRun({ text, size: 20, font: "Arial", ...opts })] })]
  });
}

function spacer() {
  return new Paragraph({ spacing: { after: 200 }, children: [] });
}

function divider() {
  return new Paragraph({
    spacing: { before: 200, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.accent, space: 1 } },
    children: []
  });
}

// ── DOCUMENT ────────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: C.primary },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: C.accent },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: C.black },
        paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
        ] },
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.LOWER_LETTER, text: "%2)", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
        ] },
      { reference: "steps",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "Step %1:", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 720 } } } },
        ] },
      { reference: "phase_bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
        ] },
    ]
  },
  sections: [

    // ═══════════════════════════════════════════════════════════
    // TITLE PAGE
    // ═══════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: [
        spacer(), spacer(), spacer(), spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 120 },
          children: [new TextRun({ text: "LittleJoys Persona Engine", size: 52, bold: true, font: "Arial", color: C.primary })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 80 },
          children: [new TextRun({ text: "User Flow Document v2.0", size: 36, font: "Arial", color: C.accent })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.accent, space: 1 } },
          spacing: { after: 400 },
          children: []
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 60 },
          children: [new TextRun({ text: "Complete Interaction Flow for the Synthetic Research Platform", size: 24, font: "Arial", color: C.grey, italics: true })]
        }),
        spacer(), spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 60 },
          children: [new TextRun({ text: "Simulatte Research Pvt Ltd", size: 22, font: "Arial", color: C.grey })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 60 },
          children: [new TextRun({ text: "March 2026  |  Confidential", size: 20, font: "Arial", color: C.grey })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Version 2.0 \u2014 Redesigned from founder vision & UAT feedback", size: 18, font: "Arial", color: C.grey, italics: true })]
        }),
      ]
    },

    // ═══════════════════════════════════════════════════════════
    // TABLE OF CONTENTS (manual)
    // ═══════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            children: [
              new TextRun({ text: "LittleJoys Persona Engine", size: 16, font: "Arial", color: C.grey }),
              new TextRun({ text: "\tUser Flow Document v2.0", size: 16, font: "Arial", color: C.grey }),
            ],
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.accent, space: 1 } }
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", size: 16, font: "Arial", color: C.grey }),
              new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: C.grey }),
            ]
          })]
        })
      },
      children: [
        heading("Table of Contents", HeadingLevel.HEADING_1),
        spacer(),
        ...[
          "1.  Document Purpose & Scope",
          "2.  Platform Architecture Overview",
          "3.  Phase 0 \u2014 Population Explorer",
          "4.  Phase 1 \u2014 Scenario Introduction & Cohort Formation",
          "5.  Phase 2 \u2014 Diagnosis & Hypothesis Mapping",
          "6.  Phase 3 \u2014 Deep Dives & Report Generation",
          "7.  Phase 4 \u2014 Intervention Design & Simulation",
          "8.  Navigation & UX Principles",
          "9.  Infrastructure Mapping (Build / Reuse / Defer)",
          "10. Page-by-Page Wireframe Descriptions",
        ].map(t => para(t, { size: 24 })),
        new Paragraph({ children: [new PageBreak()] }),
      ]
    },

    // ═══════════════════════════════════════════════════════════
    // SECTION 1 — DOCUMENT PURPOSE
    // ═══════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            children: [
              new TextRun({ text: "LittleJoys Persona Engine", size: 16, font: "Arial", color: C.grey }),
              new TextRun({ text: "\tUser Flow Document v2.0", size: 16, font: "Arial", color: C.grey }),
            ],
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.accent, space: 1 } }
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", size: 16, font: "Arial", color: C.grey }),
              new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: C.grey }),
            ]
          })]
        })
      },
      children: [
        heading("1. Document Purpose & Scope", HeadingLevel.HEADING_1),

        para("This document defines the complete user interaction flow for the LittleJoys Persona Simulation Engine \u2014 a synthetic research platform that generates 200+ deep household personas representing Indian parents and simulates their decision-making around children\u2019s nutrition products."),
        spacer(),

        heading("1.1 Who This Document Is For", HeadingLevel.HEADING_2),
        bulletItem("Product managers designing the next sprint"),
        bulletItem("Engineers implementing the redesigned flow"),
        bulletItem("Stakeholders and investors evaluating the platform\u2019s capability"),
        bulletItem("QA teams validating each phase of the simulation pipeline"),
        spacer(),

        heading("1.2 What Changed in v2.0", HeadingLevel.HEADING_2),
        para("Version 2.0 reflects a fundamental redesign based on the founder\u2019s vision document and comprehensive UAT feedback. Key changes:"),
        bulletItem("Mandatory simulation-first flow: Every scenario MUST run a baseline temporal simulation before any research begins"),
        bulletItem("Cohort formation from actual simulated behavior, not static funnel scores"),
        bulletItem("Hypothesis-to-cohort mapping: Each research hypothesis explicitly maps to the cohorts it targets"),
        bulletItem("Alternative simulation auto-generation: Platform auto-proposes 2\u20133 intervention alternatives"),
        bulletItem("Semantic memory integration: Persona narratives actively inform decision-making (not just display)"),
        bulletItem("Purchase history population: Temporal simulation populates actual buying records per persona"),
        spacer(),

        heading("1.3 Design Principles", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2800, 6560],
          rows: [
            new TableRow({ children: [headerCell("Principle", 2800), headerCell("Description", 6560)] }),
            new TableRow({ children: [
              cell("Simulation-First", 2800, { bold: true }),
              cell("No research question can be investigated until a temporal baseline exists. Cohorts emerge from simulated behavior, not static attributes.", 6560)
            ] }),
            new TableRow({ children: [
              cell("Deep Personas", 2800, { bold: true }),
              cell("Every persona has a 300\u2013500 word LLM narrative, episodic memories, brand memories, and semantic anchors. No shallow profiles.", 6560)
            ] }),
            new TableRow({ children: [
              cell("Mandatory Product Introduction", 2800, { bold: true }),
              cell("Before any study, the platform simulates how the product enters the persona\u2019s world \u2014 through which channel, at what moment, with what framing.", 6560)
            ] }),
            new TableRow({ children: [
              cell("Hypothesis-Driven", 2800, { bold: true }),
              cell("Every research action is tied to a hypothesis. The platform enforces this connection from cohort selection through to results.", 6560)
            ] }),
            new TableRow({ children: [
              cell("Compressed Timelines", 2800, { bold: true }),
              cell("12-month temporal simulations run in seconds. What takes traditional research 3 months happens in one session.", 6560)
            ] }),
            new TableRow({ children: [
              cell("Reusable Infrastructure", 2800, { bold: true }),
              cell("Leverage existing funnel engine, event simulation, probe engine, and LLM interview capabilities. Build incrementally.", 6560)
            ] }),
          ]
        }),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 2 — PLATFORM ARCHITECTURE OVERVIEW
        // ═══════════════════════════════════════════════════════════
        heading("2. Platform Architecture Overview", HeadingLevel.HEADING_1),

        para("The platform operates as a 5-phase pipeline. Each phase gates the next \u2014 users cannot skip ahead without completing prerequisites. This enforces methodological rigor while remaining intuitive."),
        spacer(),

        heading("2.1 The Five Phases", HeadingLevel.HEADING_2),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1200, 2400, 5760],
          rows: [
            new TableRow({ children: [headerCell("Phase", 1200), headerCell("Name", 2400), headerCell("Purpose", 5760)] }),
            new TableRow({ children: [
              cell("0", 1200, { bold: true, fill: C.lightGrey }),
              cell("Population Explorer", 2400, { fill: C.lightGrey }),
              cell("Browse and understand 200 synthetic household personas. Organic insight discovery.", 5760, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("1", 1200, { bold: true }),
              cell("Scenario + Cohort Formation", 2400),
              cell("Define a product scenario. Run mandatory 12-month baseline temporal simulation. Form behavioral cohorts from results.", 5760)
            ] }),
            new TableRow({ children: [
              cell("2", 1200, { bold: true, fill: C.lightGrey }),
              cell("Diagnosis", 2400, { fill: C.lightGrey }),
              cell("Formulate hypotheses. Map each hypothesis to target cohorts. Run diagnostic probes (attribute, interview, simulation).", 5760, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("3", 1200, { bold: true }),
              cell("Deep Dives & Report", 2400),
              cell("LLM-driven persona interviews. Pattern analysis across cohorts. Downloadable synthesis report.", 5760)
            ] }),
            new TableRow({ children: [
              cell("4", 1200, { bold: true, fill: C.lightGrey }),
              cell("Intervention & Simulation", 2400, { fill: C.lightGrey }),
              cell("Design interventions. Platform auto-generates alternatives. Run counterfactual simulations. Compare lift across quadrant.", 5760, { fill: C.lightGrey })
            ] }),
          ]
        }),
        spacer(),

        heading("2.2 Mandatory Flow Enforcement", HeadingLevel.HEADING_2),
        para("The platform enforces a strict progression:"),
        bulletItem("Phase 0 is always accessible (read-only exploration)"),
        bulletItem("Phase 1 unlocks when user selects a scenario and clicks \u201CRun Baseline\u201D"),
        bulletItem("Phase 2 unlocks only after Phase 1 baseline simulation completes and cohorts are formed"),
        bulletItem("Phase 3 unlocks after at least one diagnostic probe completes in Phase 2"),
        bulletItem("Phase 4 unlocks after Phase 3 report is generated"),
        spacer(),
        para("Locked phases show a greyed-out sidebar entry with a tooltip explaining the prerequisite. This prevents the \u201Cresearch without foundation\u201D anti-pattern identified in UAT."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 3 — PHASE 0: POPULATION EXPLORER
        // ═══════════════════════════════════════════════════════════
        heading("3. Phase 0 \u2014 Population Explorer", HeadingLevel.HEADING_1),

        para("The entry point. Users land here after population generation. This phase is purely exploratory \u2014 no simulation, no research. The goal is to build intuition about the synthetic population."),
        spacer(),

        heading("3.1 Landing View", HeadingLevel.HEADING_2),
        para("The landing view shows three headline metrics:"),
        bulletItem("Total Personas (e.g., 200)"),
        bulletItem("Personas with LLM Narratives (e.g., 200 / 200)"),
        bulletItem("Scenarios Available (e.g., 4)"),
        spacer(),

        heading("3.2 Population Distribution Dashboard", HeadingLevel.HEADING_2),
        para("Below the metrics, a set of distribution charts provides an overview:"),
        bulletItem("Income distribution (histogram with 5 brackets)"),
        bulletItem("City tier split (pie chart: Metro / Tier-1 / Tier-2 / Tier-3)"),
        bulletItem("Child age distribution (bar chart by age bands: 0\u20132, 3\u20135, 6\u20138, 9\u201312)"),
        bulletItem("Education level (stacked bar)"),
        bulletItem("Health consciousness score (density plot)"),
        spacer(),

        heading("3.3 Persona Browser", HeadingLevel.HEADING_2),
        para("The persona browser lets users filter and explore individual profiles."),
        spacer(),

        heading("3.3.1 Filters", HeadingLevel.HEADING_3),
        bulletItem("Income bracket (dropdown)"),
        bulletItem("City tier (multi-select)"),
        bulletItem("Number of children (slider: 1\u20134)"),
        bulletItem("Child age range (range slider)"),
        bulletItem("Health consciousness (low / medium / high)"),
        bulletItem("Free-text search across persona narratives"),
        spacer(),

        heading("3.3.2 Persona Card", HeadingLevel.HEADING_3),
        para("Each persona displays as an expandable card with:"),
        bulletItem("Human-readable ID (e.g., \u201CSneha M., Pune, 2 children\u201D) \u2014 never raw UUID"),
        bulletItem("Key demographics shown as chips (income, city, education, children count)"),
        bulletItem("Health consciousness score as a colored bar (red / amber / green)"),
        bulletItem("First 2 sentences of the LLM narrative as preview text"),
        spacer(),

        heading("3.3.3 Expanded Persona View", HeadingLevel.HEADING_3),
        para("Clicking a card expands it to show:"),
        bulletItem("Full 300\u2013500 word narrative (the persona\u2019s life story)"),
        bulletItem("All 12 taxonomy categories in collapsible sections (Demographics, Health, Psychology, Cultural, Relationship, Career, Education, Lifestyle, DailyRoutine, Values, Emotional, Media)"),
        bulletItem("Memory layer: episodic memories, semantic anchors, brand memories"),
        bulletItem("Children detail cards (each child: name, age, gender, health conditions, food preferences)"),
        spacer(),

        heading("3.4 Organic Insight Cards", HeadingLevel.HEADING_2),
        para("Scattered throughout the explorer, the platform auto-generates \u201Cinsight nudges\u201D:"),
        bulletItem("\u201C42% of your population lives in Tier-2 cities \u2014 higher than national average for this income bracket\u201D"),
        bulletItem("\u201CPersonas with 2+ children show 1.8x higher price sensitivity than single-child households\u201D"),
        bulletItem("\u201CHealth consciousness peaks in the 28\u201334 age band, drops sharply after 40\u201D"),
        para("These are computed from population statistics, not LLM-generated, ensuring they are always factually grounded."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 4 — PHASE 1: SCENARIO + COHORT FORMATION
        // ═══════════════════════════════════════════════════════════
        heading("4. Phase 1 \u2014 Scenario Introduction & Cohort Formation", HeadingLevel.HEADING_1),

        para("This is the most critical phase in the redesign. It replaces the old \u201Cstatic funnel\u201D approach with a mandatory temporal simulation that produces real behavioral cohorts."),
        spacer(),

        heading("4.1 Scenario Selection", HeadingLevel.HEADING_2),
        para("User selects from available scenarios (or creates a custom one):"),
        spacer(),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2000, 3680, 3680],
          rows: [
            new TableRow({ children: [headerCell("Scenario ID", 2000), headerCell("Name", 3680), headerCell("Description", 3680)] }),
            new TableRow({ children: [
              cell("baseline", 2000, { fill: C.lightGrey }),
              cell("Baseline Nutrition Product", 3680, { fill: C.lightGrey }),
              cell("Standard children\u2019s nutrition supplement, no special positioning", 3680, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("premium_health", 2000),
              cell("Premium Health Positioning", 3680),
              cell("Higher price point, doctor-endorsed, clinical claims", 3680)
            ] }),
            new TableRow({ children: [
              cell("ayurvedic", 2000, { fill: C.lightGrey }),
              cell("Ayurvedic / Natural", 3680, { fill: C.lightGrey }),
              cell("Natural ingredients, traditional positioning, trust-based", 3680, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("budget_mass", 2000),
              cell("Budget Mass Market", 3680),
              cell("Affordable, sachet-based, wide distribution", 3680)
            ] }),
          ]
        }),
        spacer(),

        heading("4.2 Mandatory Product Introduction Simulation", HeadingLevel.HEADING_2),
        para("Before the full temporal simulation runs, the platform simulates HOW the product enters each persona\u2019s world. This is the \u201Cproduct introduction\u201D step from the founder\u2019s vision:"),
        spacer(),

        numberedItem("Channel determination \u2014 For each persona, the engine determines the most likely discovery channel based on their media consumption profile (Instagram ad, doctor recommendation, friend\u2019s WhatsApp forward, supermarket shelf, etc.)"),
        numberedItem("Moment determination \u2014 When in the persona\u2019s daily routine does the product message arrive? Morning rush, afternoon browsing, evening family time?"),
        numberedItem("Frame determination \u2014 What is the persona\u2019s emotional and cognitive state at the moment of introduction? Stressed about child\u2019s health? Browsing casually? Comparing products?"),
        numberedItem("First impression scoring \u2014 Based on channel + moment + frame, the engine computes an initial interest score and stores it in the persona\u2019s near-term memory"),
        spacer(),

        para("Output: Each persona now has a \u201Cproduct_introduction\u201D record in their memory, which feeds into the temporal simulation."),
        spacer(),

        heading("4.3 Baseline Temporal Simulation (12 months)", HeadingLevel.HEADING_2),
        para("The engine runs a 12-month day-level simulation using the existing EventEngine. For each persona, across 365 simulated days:"),
        spacer(),

        bulletItem("10 decision variables evolve daily: trust, habit_strength, child_acceptance, price_salience, reorder_urgency, fatigue, perceived_value, brand_salience, effort_friction, discretionary_budget"),
        bulletItem("Environmental triggers fire on realistic schedules (payday cycles, seasonal illness spikes, festival periods, school exam stress)"),
        bulletItem("Purchase events are recorded when reorder_urgency exceeds threshold and discretionary_budget allows"),
        bulletItem("Word-of-mouth propagation between personas in the same city/social cluster"),
        bulletItem("Churn events recorded when habit_strength decays below threshold for 30+ consecutive days"),
        spacer(),

        para("Critical change from v1: The temporal simulation now POPULATES the purchase_history field on each persona, creating actual PurchaseEvent records with product, channel, trigger, and outcome."),
        spacer(),

        heading("4.4 Cohort Formation from Simulation Results", HeadingLevel.HEADING_2),
        para("After the 12-month simulation completes, the cohort classifier groups personas into 5 behavioral cohorts based on ACTUAL simulated behavior:"),
        spacer(),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2200, 4160, 3000],
          rows: [
            new TableRow({ children: [headerCell("Cohort", 2200), headerCell("Definition", 4160), headerCell("Typical Size", 3000)] }),
            new TableRow({ children: [
              cell("Never Aware", 2200, { bold: true, fill: C.lightGrey }),
              cell("Product introduction simulation resulted in zero engagement. No awareness registered across 12 months.", 4160, { fill: C.lightGrey }),
              cell("15\u201325% of population", 3000, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Aware, Not Tried", 2200, { bold: true }),
              cell("Became aware (brand_salience > 0) but never purchased. May have considered but dropped out.", 4160),
              cell("25\u201335%", 3000)
            ] }),
            new TableRow({ children: [
              cell("First-Time Buyer", 2200, { bold: true, fill: C.lightGrey }),
              cell("Made exactly 1 purchase during 12 months. Purchased but did not repeat.", 4160, { fill: C.lightGrey }),
              cell("10\u201320%", 3000, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Current User", 2200, { bold: true }),
              cell("Made 2+ purchases AND purchased within last 60 simulated days. Active repeat buyer.", 4160),
              cell("10\u201320%", 3000)
            ] }),
            new TableRow({ children: [
              cell("Lapsed User", 2200, { bold: true, fill: C.lightGrey }),
              cell("Made 2+ purchases but last purchase > 60 days ago. Was a repeat buyer, stopped.", 4160, { fill: C.lightGrey }),
              cell("5\u201315%", 3000, { fill: C.lightGrey })
            ] }),
          ]
        }),
        spacer(),

        heading("4.5 Cohort Dashboard", HeadingLevel.HEADING_2),
        para("After simulation completes, users see:"),
        bulletItem("Cohort distribution bar chart (count and % for each of 5 cohorts)"),
        bulletItem("Per-cohort summary cards showing: average purchase count, average time-to-first-purchase, top 3 drop-off reasons, representative persona previews"),
        bulletItem("Funnel visualization: Awareness \u2192 Consideration \u2192 Trial \u2192 Repeat \u2192 Loyalty, with conversion rates between each stage"),
        bulletItem("Key metric: Overall adoption rate (% who purchased at least once in 12 months)"),
        spacer(),

        para("This dashboard replaces the old static funnel view. Every number is backed by actual simulated behavior, not static score thresholds."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 5 — PHASE 2: DIAGNOSIS
        // ═══════════════════════════════════════════════════════════
        heading("5. Phase 2 \u2014 Diagnosis & Hypothesis Mapping", HeadingLevel.HEADING_1),

        para("With behavioral cohorts established, the user now investigates WHY the simulated outcomes look the way they do. This phase replaces both the old \u201CResearch\u201D and \u201CDiagnose\u201D tabs with a unified, hypothesis-driven workflow."),
        spacer(),

        heading("5.1 Problem Statement", HeadingLevel.HEADING_2),
        para("The platform auto-generates a problem statement from the Phase 1 results:"),
        spacer(),
        new Paragraph({
          spacing: { after: 120 },
          indent: { left: 720, right: 720 },
          shading: { fill: C.highlight, type: ShadingType.CLEAR },
          children: [new TextRun({
            text: "Example: \u201CIn the Baseline scenario, only 28% of the population purchased at least once in 12 months. 35% remained unaware despite product introduction. Of those who tried once, 40% did not repeat. The largest barrier appears to be price_salience exceeding tolerance in Tier-2/3 cities.\u201D",
            size: 20, font: "Arial", italics: true
          })]
        }),
        spacer(),

        heading("5.2 Hypothesis Generation", HeadingLevel.HEADING_2),
        para("The user formulates hypotheses to investigate. The platform assists by suggesting hypotheses based on cohort patterns:"),
        spacer(),

        boldPara("Auto-suggested hypotheses ", "(user can accept, modify, or add their own):"),
        bulletItem("H1: \u201CPrice sensitivity is the primary barrier for Aware-Not-Tried personas in Tier-2/3 cities\u201D"),
        bulletItem("H2: \u201CChild taste rejection drives first-time buyers to lapse within 30 days\u201D"),
        bulletItem("H3: \u201CDoctor endorsement would shift 20%+ of Never-Aware personas into the awareness funnel\u201D"),
        bulletItem("H4: \u201CWhatsApp-based social proof from other mothers would increase repeat purchase rate by 15%\u201D"),
        spacer(),

        heading("5.3 Hypothesis-to-Cohort Mapping", HeadingLevel.HEADING_2),
        para("Each hypothesis MUST be mapped to one or more target cohorts. This is enforced by the UI:"),
        spacer(),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1500, 3930, 3930],
          rows: [
            new TableRow({ children: [headerCell("Hypothesis", 1500), headerCell("Target Cohorts", 3930), headerCell("Probe Type", 3930)] }),
            new TableRow({ children: [
              cell("H1", 1500, { bold: true, fill: C.lightGrey }),
              cell("Aware-Not-Tried", 3930, { fill: C.lightGrey }),
              cell("Attribute probe (price_salience by city_tier)", 3930, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("H2", 1500, { bold: true }),
              cell("First-Time Buyer, Lapsed User", 3930),
              cell("Interview probe (explore taste rejection)", 3930)
            ] }),
            new TableRow({ children: [
              cell("H3", 1500, { bold: true, fill: C.lightGrey }),
              cell("Never Aware", 3930, { fill: C.lightGrey }),
              cell("Simulation probe (counterfactual: add doctor channel)", 3930, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("H4", 1500, { bold: true }),
              cell("First-Time Buyer, Current User", 3930),
              cell("Simulation probe (counterfactual: add WOM multiplier)", 3930)
            ] }),
          ]
        }),
        spacer(),

        heading("5.4 Probe Execution", HeadingLevel.HEADING_2),
        para("The platform supports three probe types, each leveraging existing infrastructure:"),
        spacer(),

        heading("5.4.1 Attribute Probe", HeadingLevel.HEADING_3),
        para("Computes Cohen\u2019s d effect size between cohorts on a selected attribute. Example: \u201CCompare price_salience between Aware-Not-Tried and Current-User cohorts.\u201D"),
        bulletItem("Output: Effect size (small / medium / large), distribution overlay chart, statistical significance"),
        bulletItem("Existing infrastructure: src/probing/engine.py \u2192 _run_attribute_probe()"),
        spacer(),

        heading("5.4.2 Interview Probe", HeadingLevel.HEADING_3),
        para("LLM role-plays as sampled personas from the target cohort, answering research questions in character."),
        bulletItem("Smart sampling: Platform selects 5\u20138 diverse personas from the target cohort(s)"),
        bulletItem("Interview format: Structured questions with follow-up probing"),
        bulletItem("Output: Thematic analysis across interviews, verbatim quotes, pattern detection"),
        bulletItem("Existing infrastructure: src/probing/engine.py \u2192 _run_interview_probe()"),
        spacer(),

        heading("5.4.3 Simulation Probe", HeadingLevel.HEADING_3),
        para("Runs a counterfactual simulation: \u201CWhat if we changed X?\u201D and measures lift."),
        bulletItem("User defines the counterfactual modification (e.g., add doctor endorsement channel)"),
        bulletItem("Engine re-runs temporal simulation with modification applied"),
        bulletItem("Output: Lift percentage, before/after cohort distribution, per-persona movement"),
        bulletItem("Existing infrastructure: src/simulation/counterfactual.py"),
        spacer(),

        heading("5.5 Diagnostic Dashboard", HeadingLevel.HEADING_2),
        para("After probes run, the diagnostic dashboard shows:"),
        bulletItem("Hypothesis status matrix: Each hypothesis marked as Supported / Partially Supported / Not Supported"),
        bulletItem("Key findings per hypothesis with evidence links"),
        bulletItem("Cross-hypothesis pattern detection (e.g., \u201CH1 and H4 both point to trust as the underlying barrier\u201D)"),
        bulletItem("Suggested next steps: \u201CBased on findings, proceed to Deep Dives for H2 (taste rejection) or jump to Intervention for H1 (price sensitivity)\u201D"),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 6 — PHASE 3: DEEP DIVES & REPORT
        // ═══════════════════════════════════════════════════════════
        heading("6. Phase 3 \u2014 Deep Dives & Report Generation", HeadingLevel.HEADING_1),

        para("This phase provides qualitative depth through extended persona interviews and synthesizes all findings into a downloadable report."),
        spacer(),

        heading("6.1 Smart-Sampled Interview Sessions", HeadingLevel.HEADING_2),
        para("The platform selects personas for deep-dive interviews using stratified sampling that ensures:"),
        bulletItem("Representation from each relevant cohort"),
        bulletItem("Diversity across city tiers, income brackets, and child age bands"),
        bulletItem("Priority given to personas near cohort boundaries (e.g., almost-converted, recently-lapsed)"),
        spacer(),

        heading("6.2 Interview Experience", HeadingLevel.HEADING_2),
        para("Each interview follows a structured protocol:"),
        spacer(),

        numberedItem("Context loading \u2014 The LLM receives the full persona profile, narrative, memory layer, purchase history, and simulation trajectory"),
        numberedItem("Opening \u2014 Persona introduces themselves naturally, referencing their life story"),
        numberedItem("Guided exploration \u2014 Structured questions probe the hypothesis under investigation"),
        numberedItem("Follow-up probing \u2014 The LLM identifies contradictions or surprises and probes deeper"),
        numberedItem("Behavioral validation \u2014 Interview responses are cross-checked against the persona\u2019s simulated behavior for consistency"),
        spacer(),

        para("Critical improvement from v1: The LLM now has access to the persona\u2019s semantic memory (anchor values, life stories) AND their purchase history from the temporal simulation. Interviews are grounded in actual simulated behavior, not just demographic attributes."),
        spacer(),

        heading("6.3 Pattern Analysis", HeadingLevel.HEADING_2),
        para("After interviews complete, the platform runs cross-interview pattern analysis:"),
        bulletItem("Theme extraction across all interviews (e.g., \u201C5 of 8 interviewed personas mentioned school lunch as a key use occasion\u201D)"),
        bulletItem("Contradiction detection (e.g., \u201CPersona claims to be health-conscious but simulated behavior shows zero health product purchases\u201D)"),
        bulletItem("Quote bank: Key verbatim quotes organized by theme, with persona attribution"),
        spacer(),

        heading("6.4 Synthesis Report", HeadingLevel.HEADING_2),
        para("The platform generates a downloadable PDF/DOCX report containing:"),
        bulletItem("Executive summary with key findings"),
        bulletItem("Cohort analysis with behavioral data"),
        bulletItem("Hypothesis validation results with evidence"),
        bulletItem("Interview highlights and thematic analysis"),
        bulletItem("Strategic recommendations prioritized by impact and feasibility"),
        bulletItem("Appendix: Full persona profiles for interviewed personas"),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 7 — PHASE 4: INTERVENTION DESIGN & SIMULATION
        // ═══════════════════════════════════════════════════════════
        heading("7. Phase 4 \u2014 Intervention Design & Simulation", HeadingLevel.HEADING_1),

        para("Armed with diagnostic findings, the user designs interventions and the platform simulates their impact."),
        spacer(),

        heading("7.1 The Intervention Matrix (4\u00D74)", HeadingLevel.HEADING_2),
        para("Interventions are organized along two axes:"),
        spacer(),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 2340, 2340, 2340],
          rows: [
            new TableRow({ children: [
              headerCell("", 2340),
              headerCell("Product Change", 2340),
              headerCell("Communication Change", 2340),
              headerCell("Distribution Change", 2340)
            ] }),
            new TableRow({ children: [
              cell("Targeting: Acquisition", 2340, { bold: true, fill: C.highlight }),
              cell("New SKU for trial (sachet)", 2340),
              cell("Doctor endorsement campaign", 2340),
              cell("Add pharmacy channel", 2340)
            ] }),
            new TableRow({ children: [
              cell("Targeting: Retention", 2340, { bold: true, fill: C.highlight }),
              cell("Flavor variant for picky eaters", 2340),
              cell("WhatsApp subscription reminders", 2340),
              cell("Auto-delivery subscription", 2340)
            ] }),
            new TableRow({ children: [
              cell("Targeting: Win-back", 2340, { bold: true, fill: C.highlight }),
              cell("Reformulated product", 2340),
              cell("Win-back discount offer", 2340),
              cell("Home delivery re-engagement", 2340)
            ] }),
            new TableRow({ children: [
              cell("Targeting: Awareness", 2340, { bold: true, fill: C.highlight }),
              cell("Free sample distribution", 2340),
              cell("Influencer mother campaign", 2340),
              cell("School tie-up program", 2340)
            ] }),
          ]
        }),
        spacer(),

        heading("7.2 Primary Intervention Design", HeadingLevel.HEADING_2),
        para("The user designs their primary intervention by specifying:"),
        bulletItem("Target cohort(s) and hypothesis being addressed"),
        bulletItem("Intervention type (from the 4\u00D74 matrix)"),
        bulletItem("Specific parameters (e.g., discount percentage, new channel, message framing)"),
        bulletItem("Expected outcome hypothesis (e.g., \u201CExpect 15% lift in trial rate among Aware-Not-Tried\u201D)"),
        spacer(),

        heading("7.3 Auto-Generated Alternatives", HeadingLevel.HEADING_2),
        para("A key innovation from the founder\u2019s vision: the platform auto-generates 2\u20133 alternative interventions based on the diagnostic findings:"),
        spacer(),

        bulletItem("Alternative A: A different intervention targeting the same cohort (e.g., if user chose price discount, platform suggests doctor endorsement)"),
        bulletItem("Alternative B: The same intervention type targeting a different cohort (e.g., if user targeted Aware-Not-Tried, platform suggests First-Time Buyer)"),
        bulletItem("Alternative C: A combined intervention addressing multiple barriers simultaneously"),
        spacer(),

        heading("7.4 Counterfactual Simulation", HeadingLevel.HEADING_2),
        para("For the primary intervention AND each alternative, the engine:"),
        numberedItem("Modifies the scenario parameters according to the intervention spec"),
        numberedItem("Re-runs the full 12-month temporal simulation with the modification"),
        numberedItem("Computes lift: (modified adoption rate - baseline adoption rate) / baseline adoption rate"),
        numberedItem("Tracks per-cohort movement (e.g., how many Never-Aware personas moved to First-Time Buyer)"),
        spacer(),

        heading("7.5 Results Dashboard", HeadingLevel.HEADING_2),
        para("The results view shows a comparison table:"),
        spacer(),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1872, 1872, 1872, 1872, 1872],
          rows: [
            new TableRow({ children: [
              headerCell("Metric", 1872),
              headerCell("Baseline", 1872),
              headerCell("Primary", 1872),
              headerCell("Alt A", 1872),
              headerCell("Alt B", 1872)
            ] }),
            new TableRow({ children: [
              cell("Adoption Rate", 1872, { bold: true, fill: C.lightGrey }),
              cell("28%", 1872, { fill: C.lightGrey }),
              cell("41% (+46%)", 1872, { fill: C.lightGrey }),
              cell("35% (+25%)", 1872, { fill: C.lightGrey }),
              cell("38% (+36%)", 1872, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Repeat Rate", 1872, { bold: true }),
              cell("18%", 1872),
              cell("24% (+33%)", 1872),
              cell("22% (+22%)", 1872),
              cell("27% (+50%)", 1872)
            ] }),
            new TableRow({ children: [
              cell("Avg Purchases/Year", 1872, { bold: true, fill: C.lightGrey }),
              cell("1.2", 1872, { fill: C.lightGrey }),
              cell("2.8", 1872, { fill: C.lightGrey }),
              cell("2.1", 1872, { fill: C.lightGrey }),
              cell("3.1", 1872, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Never-Aware Reduction", 1872, { bold: true }),
              cell("\u2014", 1872),
              cell("-12pp", 1872),
              cell("-8pp", 1872),
              cell("-15pp", 1872)
            ] }),
          ]
        }),
        spacer(),
        para("Each cell is clickable to see the per-persona breakdown: which specific personas changed behavior and why."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 8 — NAVIGATION & UX PRINCIPLES
        // ═══════════════════════════════════════════════════════════
        heading("8. Navigation & UX Principles", HeadingLevel.HEADING_1),

        heading("8.1 Sidebar Navigation", HeadingLevel.HEADING_2),
        para("The sidebar serves as the primary navigation and status indicator:"),
        spacer(),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1500, 2500, 2800, 2560],
          rows: [
            new TableRow({ children: [headerCell("Phase", 1500), headerCell("Label", 2500), headerCell("Status Indicator", 2800), headerCell("Lock Condition", 2560)] }),
            new TableRow({ children: [
              cell("0", 1500, { fill: C.lightGrey }),
              cell("Population Explorer", 2500, { fill: C.lightGrey }),
              cell("Always active (green dot)", 2800, { fill: C.lightGrey }),
              cell("Never locked", 2560, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("1", 1500),
              cell("Scenario & Cohorts", 2500),
              cell("Grey until scenario selected", 2800),
              cell("Requires population loaded", 2560)
            ] }),
            new TableRow({ children: [
              cell("2", 1500, { fill: C.lightGrey }),
              cell("Diagnosis", 2500, { fill: C.lightGrey }),
              cell("Locked icon until Phase 1 done", 2800, { fill: C.lightGrey }),
              cell("Requires baseline simulation", 2560, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("3", 1500),
              cell("Deep Dives", 2500),
              cell("Locked until probe completes", 2800),
              cell("Requires at least 1 probe run", 2560)
            ] }),
            new TableRow({ children: [
              cell("4", 1500, { fill: C.lightGrey }),
              cell("Intervention", 2500, { fill: C.lightGrey }),
              cell("Locked until report generated", 2800, { fill: C.lightGrey }),
              cell("Requires Phase 3 report", 2560, { fill: C.lightGrey })
            ] }),
          ]
        }),
        spacer(),

        heading("8.2 Display Rules", HeadingLevel.HEADING_2),
        bulletItem("Never display raw field names: \u201Cprice_salience\u201D becomes \u201CPrice Sensitivity\u201D"),
        bulletItem("Never display raw UUIDs: Always show human-readable identifiers"),
        bulletItem("All scores show contextual explanation: \u201C0.72 (High \u2014 this persona is very price-conscious)\u201D"),
        bulletItem("Charts always have a human-readable insight sentence below them"),
        bulletItem("LLM responses are structured with headers, not wall-of-text paragraphs"),
        bulletItem("Loading states show progress bars with estimated time remaining"),
        spacer(),

        heading("8.3 Session Persistence", HeadingLevel.HEADING_2),
        para("The platform maintains session state across page navigations:"),
        bulletItem("Population and simulation results are cached in st.session_state"),
        bulletItem("Phase completion status persists within a session"),
        bulletItem("Users can return to any completed phase without re-running simulations"),
        bulletItem("Scenario results are keyed by scenario ID for multi-scenario comparison"),
        spacer(),

        heading("8.4 Error Handling", HeadingLevel.HEADING_2),
        bulletItem("If LLM calls fail: Show graceful fallback with \u201CRetry\u201D button, never raw error traces"),
        bulletItem("If simulation produces unexpected results: Show diagnostic info (\u201C0% adoption detected \u2014 likely due to age range mismatch. Consider adjusting target age.\u201D)"),
        bulletItem("If population data is missing: Redirect to generation flow with clear instructions"),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 9 — INFRASTRUCTURE MAPPING
        // ═══════════════════════════════════════════════════════════
        heading("9. Infrastructure Mapping (Build / Reuse / Defer)", HeadingLevel.HEADING_1),

        para("A key principle of this redesign is to maximize reuse of existing infrastructure. The table below maps each component to its status:"),
        spacer(),

        heading("9.1 Reuse Existing (Ready Now)", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 3120, 3120],
          rows: [
            new TableRow({ children: [headerCell("Component", 3120), headerCell("Source File", 3120), headerCell("Used In Phase", 3120)] }),
            new TableRow({ children: [
              cell("Population Generator", 3120, { fill: C.lightGrey }),
              cell("src/generation/population.py", 3120, { fill: C.lightGrey }),
              cell("Phase 0 (population creation)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Persona Schema (200+ attributes)", 3120),
              cell("src/taxonomy/schema.py", 3120),
              cell("All phases", 3120)
            ] }),
            new TableRow({ children: [
              cell("LLM Narrative Generator", 3120, { fill: C.lightGrey }),
              cell("src/generation/tier2_generator.py", 3120, { fill: C.lightGrey }),
              cell("Phase 0 (persona depth)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("4-Layer Decision Funnel", 3120),
              cell("src/decision/funnel.py", 3120),
              cell("Phase 1 (within temporal sim)", 3120)
            ] }),
            new TableRow({ children: [
              cell("Event Engine (day-level sim)", 3120, { fill: C.lightGrey }),
              cell("src/simulation/event_engine.py", 3120, { fill: C.lightGrey }),
              cell("Phase 1, Phase 4 (baseline + counterfactual)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Cohort Classifier", 3120),
              cell("src/analysis/cohort_classifier.py", 3120),
              cell("Phase 1 (cohort formation)", 3120)
            ] }),
            new TableRow({ children: [
              cell("Probe Engine (3 types)", 3120, { fill: C.lightGrey }),
              cell("src/probing/engine.py", 3120, { fill: C.lightGrey }),
              cell("Phase 2 (diagnostic probes)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Counterfactual Simulator", 3120),
              cell("src/simulation/counterfactual.py", 3120),
              cell("Phase 4 (intervention testing)", 3120)
            ] }),
            new TableRow({ children: [
              cell("Scenario Definitions", 3120, { fill: C.lightGrey }),
              cell("src/decision/scenarios.py", 3120, { fill: C.lightGrey }),
              cell("Phase 1 (scenario selection)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Repeat/Churn Model", 3120),
              cell("src/decision/repeat.py", 3120),
              cell("Phase 1 (temporal sim)", 3120)
            ] }),
          ]
        }),
        spacer(),

        heading("9.2 Build New (Sprint Work)", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 3120, 3120],
          rows: [
            new TableRow({ children: [headerCell("Component", 3120), headerCell("Description", 3120), headerCell("Effort Estimate", 3120)] }),
            new TableRow({ children: [
              cell("Product Introduction Engine", 3120, { fill: C.lightGrey }),
              cell("Simulate how product enters each persona\u2019s world (channel + moment + frame)", 3120, { fill: C.lightGrey }),
              cell("Medium (extends EventEngine)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Purchase History Population", 3120),
              cell("Wire temporal simulation output to persona.purchase_history field", 3120),
              cell("Small (field exists, needs wiring)", 3120)
            ] }),
            new TableRow({ children: [
              cell("Semantic Memory Read-back", 3120, { fill: C.lightGrey }),
              cell("Feed persona narratives/anchors into decision engine and interview prompts", 3120, { fill: C.lightGrey }),
              cell("Small (data exists, needs integration)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Hypothesis-Cohort Mapping UI", 3120),
              cell("UI for mapping hypotheses to target cohorts with enforcement", 3120),
              cell("Medium (new Streamlit page)", 3120)
            ] }),
            new TableRow({ children: [
              cell("Auto-Alternative Generator", 3120, { fill: C.lightGrey }),
              cell("Auto-propose 2\u20133 intervention alternatives from diagnostic findings", 3120, { fill: C.lightGrey }),
              cell("Medium (LLM + scenario mutation)", 3120, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Phase Gating Logic", 3120),
              cell("Sidebar lock/unlock based on phase completion status", 3120),
              cell("Small (session state checks)", 3120)
            ] }),
            new TableRow({ children: [
              cell("Synthesis Report Generator", 3120, { fill: C.lightGrey }),
              cell("Auto-generate downloadable PDF/DOCX from research findings", 3120, { fill: C.lightGrey }),
              cell("Medium (template + LLM synthesis)", 3120, { fill: C.lightGrey })
            ] }),
          ]
        }),
        spacer(),

        heading("9.3 Defer to v2.0", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 6240],
          rows: [
            new TableRow({ children: [headerCell("Component", 3120), headerCell("Reason for Deferral", 6240)] }),
            new TableRow({ children: [
              cell("Inter-Persona Learning", 3120, { fill: C.lightGrey }),
              cell("Mirofish-style autonomous agent communication between personas. Requires agent orchestration framework.", 6240, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Weekly Real-World Data Scraping", 3120),
              cell("Ingesting actual market data to update persona perceptions. Requires data pipeline infrastructure.", 6240)
            ] }),
            new TableRow({ children: [
              cell("Multi-Product Simulation", 3120, { fill: C.lightGrey }),
              cell("Simulating competitive dynamics between multiple products. Requires scenario composition engine.", 6240, { fill: C.lightGrey })
            ] }),
            new TableRow({ children: [
              cell("Custom Persona Upload", 3120),
              cell("Allow users to upload real consumer data to seed persona generation. Requires PII handling.", 6240)
            ] }),
          ]
        }),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════
        // SECTION 10 — PAGE-BY-PAGE WIREFRAME DESCRIPTIONS
        // ═══════════════════════════════════════════════════════════
        heading("10. Page-by-Page Wireframe Descriptions", HeadingLevel.HEADING_1),

        para("This section describes the layout of each Streamlit page in sufficient detail for an engineer to implement."),
        spacer(),

        heading("10.1 Home / Landing (streamlit_app.py)", HeadingLevel.HEADING_2),
        bulletItem("Top: Title bar with \u201CLittleJoys Persona Simulation Engine\u201D and subtitle"),
        bulletItem("3-column metric row: Total Personas | With Narratives | Scenarios Available"),
        bulletItem("Getting Started section with numbered steps mapping to phases"),
        bulletItem("3 quick-link buttons: Browse Personas | Design Research | Diagnose"),
        bulletItem("Sidebar: Phase navigation with status indicators (dots/locks)"),
        spacer(),

        heading("10.2 Phase 0: Personas Page (pages/1_personas.py)", HeadingLevel.HEADING_2),
        bulletItem("Top: Population distribution charts (4 charts in 2\u00D72 grid)"),
        bulletItem("Filter panel (collapsible): Income, City Tier, Children, Age Range, Health Score, Free-text search"),
        bulletItem("Results count: \u201CShowing 47 of 200 personas\u201D"),
        bulletItem("Persona card grid (2 columns): Each card shows ID, chips, health bar, narrative preview"),
        bulletItem("Click-to-expand: Full profile with 12 taxonomy sections, memory layer, children cards"),
        bulletItem("Insight nudge cards scattered between persona rows"),
        spacer(),

        heading("10.3 Phase 1: Scenario & Cohorts (pages/2_scenario.py)", HeadingLevel.HEADING_2),
        bulletItem("Top: Scenario selector (dropdown or card-based selection)"),
        bulletItem("Scenario detail panel: Name, description, key parameters"),
        bulletItem("\u201CRun Baseline Simulation\u201D button (primary, prominent)"),
        bulletItem("Progress indicator during simulation: \u201CSimulating month 3 of 12... 142 personas processed\u201D"),
        bulletItem("After completion: Cohort distribution chart (horizontal stacked bar)"),
        bulletItem("5 cohort summary cards (expandable) with metrics and representative personas"),
        bulletItem("Funnel visualization: Awareness \u2192 Trial \u2192 Repeat with conversion rates"),
        bulletItem("Key metrics row: Overall Adoption Rate, Avg Time-to-Trial, Top Drop-off Reason"),
        spacer(),

        heading("10.4 Phase 2: Diagnosis (pages/3_diagnosis.py)", HeadingLevel.HEADING_2),
        bulletItem("Top: Auto-generated problem statement (blue highlight box)"),
        bulletItem("Hypothesis panel: List of hypotheses with status badges"),
        bulletItem("\u201CAdd Hypothesis\u201D button with form: hypothesis text, target cohorts (multi-select), suggested probe type"),
        bulletItem("Hypothesis-Cohort mapping matrix (visual)"),
        bulletItem("Probe launcher: Select hypothesis \u2192 Select probe type \u2192 Configure parameters \u2192 Run"),
        bulletItem("Results panel: Per-hypothesis findings with evidence cards"),
        bulletItem("Cross-hypothesis synthesis section"),
        spacer(),

        heading("10.5 Phase 3: Deep Dives (pages/4_deepdives.py)", HeadingLevel.HEADING_2),
        bulletItem("Top: Sampling configuration (cohorts to sample, diversity parameters)"),
        bulletItem("Interview cards: Each persona interview shown as a chat-like transcript"),
        bulletItem("Persona context sidebar: Profile summary visible alongside interview"),
        bulletItem("Pattern analysis section: Themes, contradictions, quote bank"),
        bulletItem("Report generation button: \u201CGenerate Synthesis Report\u201D"),
        bulletItem("Download button for generated report (PDF/DOCX)"),
        spacer(),

        heading("10.6 Phase 4: Intervention (pages/5_intervention.py)", HeadingLevel.HEADING_2),
        bulletItem("Top: 4\u00D74 intervention matrix (clickable cells)"),
        bulletItem("Intervention designer form: Target cohort, type, parameters, expected outcome"),
        bulletItem("Auto-alternatives panel: 2\u20133 system-generated alternatives with rationale"),
        bulletItem("\u201CRun All Simulations\u201D button"),
        bulletItem("Comparison table: Baseline vs Primary vs Alt A vs Alt B"),
        bulletItem("Per-persona movement tracker (which personas changed behavior)"),
        bulletItem("Final recommendation section with strategic priorities"),
        spacer(),

        heading("10.7 Comparison Page (pages/6_comparison.py)", HeadingLevel.HEADING_2),
        bulletItem("Side-by-side scenario comparison (select any 2 completed scenarios)"),
        bulletItem("Delta metrics: Differences highlighted in green (better) or red (worse)"),
        bulletItem("Cohort movement Sankey diagram: How personas shifted between cohorts"),
        bulletItem("Per-persona drill-down: Click any persona to see their journey in both scenarios"),

        spacer(), spacer(),
        divider(),

        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 200 },
          children: [new TextRun({ text: "End of User Flow Document v2.0", size: 22, font: "Arial", color: C.grey, italics: true })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Simulatte Research Pvt Ltd \u2014 March 2026 \u2014 Confidential", size: 18, font: "Arial", color: C.grey })]
        }),
      ]
    },
  ]
});

// ── Generate ────────────────────────────────────────────────────
const outPath = process.argv[2] || "LittleJoys_User_Flow_Document.docx";
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`Written ${outPath} (${(buf.length / 1024).toFixed(0)} KB)`);
});
