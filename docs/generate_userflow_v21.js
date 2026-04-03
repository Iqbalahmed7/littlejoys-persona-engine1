const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  PageNumber, PageBreak, TabStopType, TabStopPosition,
} = require("docx");

// ── colour palette ──────────────────────────────────────────────
const C = {
  primary:   "1B4F72",
  accent:    "2E86C1",
  highlight: "D5E8F0",
  green:     "27AE60",
  orange:    "E67E22",
  red:       "C0392B",
  grey:      "7F8C8D",
  lightGrey: "F2F3F4",
  white:     "FFFFFF",
  black:     "1C1C1C",
  darkGreen: "1E8449",
  systemBlue:"1A5276",
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
function subBullet(text) {
  return bulletItem(text, "bullets", 1);
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
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: C.primary, type: ShadingType.CLEAR },
    margins: cellMargins, verticalAlign: "center",
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: C.white, size: 20, font: "Arial" })] })]
  });
}
function cell(text, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    margins: cellMargins,
    children: [new Paragraph({ children: [new TextRun({ text, size: 20, font: "Arial", ...opts })] })]
  });
}
function spacer() { return new Paragraph({ spacing: { after: 200 }, children: [] }); }
function divider() {
  return new Paragraph({
    spacing: { before: 200, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.accent, space: 1 } },
    children: []
  });
}

// "System voice" callout — blue-left-bordered box for system narration
function systemVoice(text) {
  return new Paragraph({
    spacing: { before: 80, after: 120 },
    indent: { left: 360 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: C.systemBlue, space: 8 } },
    shading: { fill: "EBF5FB", type: ShadingType.CLEAR },
    children: [
      new TextRun({ text: "System: ", bold: true, size: 21, font: "Arial", color: C.systemBlue }),
      new TextRun({ text, size: 21, font: "Arial", italics: true, color: C.black }),
    ]
  });
}

// "Magic moment" callout — green-left-bordered highlight
function magicMoment(label, text) {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    indent: { left: 360 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: C.darkGreen, space: 8 } },
    shading: { fill: "EAFAF1", type: ShadingType.CLEAR },
    children: [
      new TextRun({ text: label + " ", bold: true, size: 21, font: "Arial", color: C.darkGreen }),
      new TextRun({ text, size: 21, font: "Arial", color: C.black }),
    ]
  });
}

// reusable page properties
const pageProps = {
  page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
};
function stdHeader(ver) {
  return new Header({
    children: [new Paragraph({
      children: [
        new TextRun({ text: "LittleJoys Persona Engine", size: 16, font: "Arial", color: C.grey }),
        new TextRun({ text: `\tUser Flow Document v2.0`, size: 16, font: "Arial", color: C.grey }),
      ],
      tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.accent, space: 1 } }
    })]
  });
}
function stdFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: "Page ", size: 16, font: "Arial", color: C.grey }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: C.grey }),
      ]
    })]
  });
}

// ═════════════════════════════════════════════════════════════════
// DOCUMENT
// ═════════════════════════════════════════════════════════════════
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
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
      ] },
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.LOWER_LETTER, text: "%2)", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
      ] },
    ]
  },
  sections: [

  // ═══════════════════════════════════════════════════════════════
  // TITLE PAGE
  // ═══════════════════════════════════════════════════════════════
  {
    properties: pageProps,
    children: [
      spacer(), spacer(), spacer(), spacer(), spacer(),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "LittleJoys Persona Engine", size: 52, bold: true, font: "Arial", color: C.primary })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
        children: [new TextRun({ text: "User Flow Document v2.0", size: 36, font: "Arial", color: C.accent })] }),
      new Paragraph({ alignment: AlignmentType.CENTER,
        border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.accent, space: 1 } },
        spacing: { after: 400 }, children: [] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "Problem-First Decision Intelligence Flow", size: 24, font: "Arial", color: C.grey, italics: true })] }),
      spacer(), spacer(), spacer(),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "Simulatte Research Pvt Ltd", size: 22, font: "Arial", color: C.grey })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "March 2026  |  Confidential", size: 20, font: "Arial", color: C.grey })] }),
      new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Problem-first \u2022 System-led \u2022 Simulation as hero", size: 18, font: "Arial", color: C.grey, italics: true })] }),
    ]
  },

  // ═══════════════════════════════════════════════════════════════
  // TOC + ALL CONTENT (single section for continuous headers/footers)
  // ═══════════════════════════════════════════════════════════════
  {
    properties: pageProps,
    headers: { default: stdHeader("v2.1") },
    footers: { default: stdFooter() },
    children: [

      // ─── TABLE OF CONTENTS ───────────────────────────────────
      heading("Table of Contents", HeadingLevel.HEADING_1),
      spacer(),
      ...[
        "1.  Document Purpose & Scope",
        "2.  Platform Architecture Overview",
        "3.  Phase 0 \u2014 Population Explorer",
        "4.  Phase 1 \u2014 Business Problem & Baseline Simulation",
        "5.  Phase 2 \u2014 System Decomposition & Probing Tree",
        "6.  Phase 3 \u2014 Core Finding & Deep Dives",
        "7.  Phase 4 \u2014 System-Proposed Interventions & Simulation",
        "8.  Navigation, UX Principles & Magic Moments",
        "9.  Infrastructure Mapping (Build / Reuse / Defer)",
        "10. Page-by-Page Wireframe Descriptions",
        "",
        "Appendix A \u2014 Glossary of System Components",
      ].map(t => para(t, { size: 24 })),
      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 1 — DOCUMENT PURPOSE
      // ═════════════════════════════════════════════════════════
      heading("1. Document Purpose & Scope", HeadingLevel.HEADING_1),
      para("This document defines the complete user interaction flow for the LittleJoys Persona Simulation Engine \u2014 a decision intelligence platform that generates 200+ deep household personas and simulates their decision-making around children\u2019s nutrition products in India."),
      spacer(),

      heading("1.1 Who This Document Is For", HeadingLevel.HEADING_2),
      bulletItem("Product managers designing the next sprint"),
      bulletItem("Engineers implementing the problem-first flow"),
      bulletItem("Stakeholders and investors evaluating the demo"),
      bulletItem("QA teams validating each phase of the pipeline"),
      spacer(),

      heading("1.2 What This Document Covers", HeadingLevel.HEADING_2),
      para("This document specifies:"),
      bulletItem("The complete 5-phase pipeline from business problem to intervention recommendation"),
      bulletItem("System-led UX posture: what the system does vs. what the user decides"),
      bulletItem("Simulation-first rigor: mandatory temporal baseline before any research"),
      bulletItem("The five \u201Cmagic moments\u201D that make this a decision intelligence system, not a dashboard tool"),
      bulletItem("Infrastructure mapping: what exists, what to build, what to defer"),
      bulletItem("Page-by-page wireframe specifications for implementation"),
      spacer(),

      heading("1.3 Core Design Principle: System-Led Intelligence", HeadingLevel.HEADING_2),
      para("The platform is a decision intelligence system, not a simulation workbench. The UX posture is:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({ children: [headerCell("The System\u2019s Job", 4680), headerCell("The User\u2019s Job", 4680)] }),
          new TableRow({ children: [
            cell("Run simulations and present results as narrative", 4680, { fill: C.lightGrey }),
            cell("State the business problem", 4680, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Generate hypotheses with rationale and evidence", 4680),
            cell("Approve, modify, or add hypotheses", 4680)
          ] }),
          new TableRow({ children: [
            cell("Build probing tree and run probes in sequence", 4680, { fill: C.lightGrey }),
            cell("Review probe results, go deeper or move on", 4680, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Synthesize core finding from all evidence", 4680),
            cell("Validate the finding against intuition", 4680)
          ] }),
          new TableRow({ children: [
            cell("Propose interventions and run all simulations", 4680, { fill: C.lightGrey }),
            cell("Choose which intervention to pursue", 4680, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      heading("1.4 Design Principles", HeadingLevel.HEADING_2),
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
            cell("Problem-First Entry", 2800, { bold: true }),
            cell("User starts by stating a business problem, not picking a scenario. The system maps problem to scenario automatically.", 6560)
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

      // ═════════════════════════════════════════════════════════
      // SECTION 2 — PLATFORM ARCHITECTURE OVERVIEW
      // ═════════════════════════════════════════════════════════
      heading("2. Platform Architecture Overview", HeadingLevel.HEADING_1),
      para("The platform operates as a 5-phase pipeline. Each phase gates the next \u2014 users cannot skip ahead without completing prerequisites. This enforces methodological rigor while remaining intuitive."),
      spacer(),

      heading("2.1 The Five Phases", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1000, 2600, 5760],
        rows: [
          new TableRow({ children: [headerCell("Phase", 1000), headerCell("Name", 2600), headerCell("Purpose", 5760)] }),
          new TableRow({ children: [
            cell("0", 1000, { bold: true, fill: C.lightGrey }),
            cell("Population Explorer", 2600, { fill: C.lightGrey }),
            cell("Browse and understand 200 synthetic household personas. Organic insight discovery. Always accessible.", 5760, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("1", 1000, { bold: true }),
            cell("Problem & Simulation", 2600),
            cell("User states a business problem. System maps it to a scenario, runs mandatory 12-month baseline simulation. Cohorts form from results. Simulation is center-stage and dramatic.", 5760)
          ] }),
          new TableRow({ children: [
            cell("2", 1000, { bold: true, fill: C.lightGrey }),
            cell("Decomposition & Probing", 2600, { fill: C.lightGrey }),
            cell("System presents hypothesis decomposition. User approves. System runs probing tree (sequential, deepening probes). Causal chain builds visually.", 5760, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("3", 1000, { bold: true }),
            cell("Core Finding & Deep Dives", 2600),
            cell("System synthesizes all evidence into a single Core Issue Statement. Optional deep-dive interviews with personas grounded in simulation. Report generation.", 5760)
          ] }),
          new TableRow({ children: [
            cell("4", 1000, { bold: true, fill: C.lightGrey }),
            cell("Interventions & Simulation", 2600, { fill: C.lightGrey }),
            cell("System proposes interventions with rationale tied to core finding. Runs all counterfactual simulations. User reviews comparison dashboard.", 5760, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      heading("2.2 Mandatory Flow Enforcement", HeadingLevel.HEADING_2),
      para("The platform enforces strict progression:"),
      bulletItem("Phase 0 is always accessible (read-only exploration)"),
      bulletItem("Phase 1 unlocks when the user states a business problem and clicks \u201CRun Baseline Simulation\u201D"),
      bulletItem("Phase 2 unlocks only after Phase 1 baseline simulation completes and cohorts are formed"),
      bulletItem("Phase 3 unlocks after the probing tree in Phase 2 completes (at least one full probe chain)"),
      bulletItem("Phase 4 unlocks after the Core Finding is generated in Phase 3"),
      spacer(),
      para("Locked phases show a greyed-out sidebar entry with a tooltip explaining the prerequisite. This prevents the \u201Cresearch without foundation\u201D anti-pattern identified in UAT."),

      heading("2.3 The System Voice", HeadingLevel.HEADING_2),
      para("Throughout the flow, the system communicates through narrative callouts \u2014 not just dashboards. After every major computation, the system SPEAKS before showing data:"),
      systemVoice("Your biggest leaky bucket is between trial and repeat. 40% of first-time buyers didn\u2019t come back within 60 days."),
      para("This voice appears as a blue-bordered callout (shown above). It precedes every chart, every table, every result. The user reads the system\u2019s interpretation BEFORE they see the raw data. This is the core UX differentiator from dashboard tools."),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 3 — PHASE 0: POPULATION EXPLORER
      // ═════════════════════════════════════════════════════════
      heading("3. Phase 0 \u2014 Population Explorer", HeadingLevel.HEADING_1),
      para("The entry point. Users land here after population generation. This phase is purely exploratory \u2014 no simulation, no research. The goal is to build intuition about the synthetic population before stating a business problem."),
      spacer(),

      heading("3.1 Landing View", HeadingLevel.HEADING_2),
      para("Three headline metrics:"),
      bulletItem("Total Personas (e.g., 200)"),
      bulletItem("Personas with LLM Narratives (e.g., 200 / 200)"),
      bulletItem("Business Problems Available (e.g., 4) \u2014 replaces \u201CScenarios Available\u201D"),
      spacer(),

      heading("3.2 Population Distribution Dashboard", HeadingLevel.HEADING_2),
      bulletItem("Income distribution (histogram with 5 brackets)"),
      bulletItem("City tier split (pie chart: Metro / Tier-1 / Tier-2 / Tier-3)"),
      bulletItem("Child age distribution (bar chart by age bands: 0\u20132, 3\u20135, 6\u20138, 9\u201312)"),
      bulletItem("Education level (stacked bar)"),
      bulletItem("Health consciousness score (density plot)"),
      spacer(),

      heading("3.3 Persona Browser", HeadingLevel.HEADING_2),
      heading("3.3.1 Filters", HeadingLevel.HEADING_3),
      bulletItem("Income bracket (dropdown)"),
      bulletItem("City tier (multi-select)"),
      bulletItem("Number of children (slider: 1\u20134)"),
      bulletItem("Child age range (range slider)"),
      bulletItem("Health consciousness (low / medium / high)"),
      bulletItem("Free-text search across persona narratives"),
      spacer(),

      heading("3.3.2 Persona Card", HeadingLevel.HEADING_3),
      bulletItem("Human-readable ID (e.g., \u201CSneha M., Pune, 2 children\u201D) \u2014 never raw UUID"),
      bulletItem("Key demographics shown as chips (income, city, education, children count)"),
      bulletItem("Health consciousness score as a colored bar (red / amber / green)"),
      bulletItem("First 2 sentences of the LLM narrative as preview text"),
      spacer(),

      heading("3.3.3 Expanded Persona View", HeadingLevel.HEADING_3),
      bulletItem("Full 300\u2013500 word narrative (the persona\u2019s life story)"),
      bulletItem("All 12 taxonomy categories in collapsible sections"),
      bulletItem("Memory layer: episodic memories, semantic anchors, brand memories"),
      bulletItem("Children detail cards (each child: name, age, gender, health conditions, food preferences)"),
      spacer(),

      heading("3.4 Organic Insight Cards", HeadingLevel.HEADING_2),
      para("Auto-generated population-level insights, computed from statistics (not LLM-generated):"),
      systemVoice("42% of your population lives in Tier-2 cities \u2014 higher than national average for this income bracket."),
      systemVoice("Personas with 2+ children show 1.8x higher price sensitivity than single-child households."),
      systemVoice("Health consciousness peaks in the 28\u201334 age band, drops sharply after 40."),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 4 — PHASE 1: PROBLEM & SIMULATION
      // ═════════════════════════════════════════════════════════
      heading("4. Phase 1 \u2014 Business Problem & Baseline Simulation", HeadingLevel.HEADING_1),
      para("This is the most critical phase. The user starts with a BUSINESS PROBLEM, not a scenario selection. The system maps the problem to the right scenario, runs a dramatic baseline simulation, and forms behavioral cohorts from the results."),
      spacer(),

      heading("4.1 Business Problem Selection (Key Design Decision)", HeadingLevel.HEADING_2),
      para("The user\u2019s first action is to state what they want to solve. The platform presents pre-built business problems (from problem_templates.py) as cards:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3120, 3120, 3120],
        rows: [
          new TableRow({ children: [headerCell("Business Problem", 3120), headerCell("Product Context", 3120), headerCell("Success Metric", 3120)] }),
          new TableRow({ children: [
            cell("Why is repeat purchase low despite high NPS?", 3120, { bold: true, fill: C.lightGrey }),
            cell("Nutrimix 2\u20136 (children\u2019s nutrition supplement)", 3120, { fill: C.lightGrey }),
            cell("Repeat purchase rate", 3120, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("How to expand Nutrimix from 2\u20136 age group to 7\u201314?", 3120, { bold: true }),
            cell("Nutrimix 7\u201314 (age expansion)", 3120),
            cell("Trial rate in 7\u201314 segment", 3120)
          ] }),
          new TableRow({ children: [
            cell("How to grow sales of a niche supplement?", 3120, { bold: true, fill: C.lightGrey }),
            cell("Magnesium Gummies (niche product)", 3120, { fill: C.lightGrey }),
            cell("Awareness-to-trial conversion", 3120, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("High effort barrier \u2014 product requires cooking", 3120, { bold: true }),
            cell("Protein Mix (mix-in-food format)", 3120),
            cell("Adoption rate despite effort friction", 3120)
          ] }),
        ]
      }),
      spacer(),

      para("The user can also type a custom business problem. In this case, the system asks clarifying questions to map it to a scenario configuration."),
      spacer(),
      boldPara("Key design decision: ", "The user never sees \u201CScenario ID: baseline\u201D or technical configuration parameters. They see business problems in natural language. The system handles the problem-to-scenario mapping internally."),
      spacer(),

      heading("4.2 System Explains What It Will Do", HeadingLevel.HEADING_2),
      para("After the user selects a problem, the system narrates what will happen next:"),
      systemVoice("To investigate why repeat purchase is low, I need to simulate how 200 households interact with Nutrimix 2\u20136 over 12 months. This will show me who buys, who repeats, who lapses, and why. Ready to run?"),
      spacer(),
      para("This narrative serves two purposes: (1) it grounds the simulation in the user\u2019s business question, and (2) it builds anticipation for the simulation event."),
      spacer(),
      para("Below the narrative: a prominent \u201CRun Baseline Simulation\u201D button. The user consciously initiates the simulation."),
      spacer(),

      heading("4.3 Dramatic Simulation Experience", HeadingLevel.HEADING_2),
      para("The 12-month simulation runs visibly and dramatically. This is NOT a loading spinner. It is the product demonstrating its core capability:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2000, 7360],
        rows: [
          new TableRow({ children: [headerCell("Simulated Month", 2000), headerCell("Narrative Progress Update", 7360)] }),
          new TableRow({ children: [
            cell("Month 1", 2000, { bold: true, fill: C.lightGrey }),
            cell("Product introduced to 200 personas via their most likely discovery channels...", 7360, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Month 3", 2000, { bold: true }),
            cell("84 personas now aware. 31 have tried the product. First churn signals emerging...", 7360)
          ] }),
          new TableRow({ children: [
            cell("Month 6", 2000, { bold: true, fill: C.lightGrey }),
            cell("Trial rate plateauing at 38%. 8 first-time buyers haven\u2019t reordered in 60 days. Word-of-mouth spreading in Metro clusters.", 7360, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Month 9", 2000, { bold: true }),
            cell("Lapsed users now outnumber active repeaters in Tier-2 cities. Price sensitivity spiking post-festival spend.", 7360)
          ] }),
          new TableRow({ children: [
            cell("Month 12", 2000, { bold: true, fill: C.lightGrey }),
            cell("Simulation complete. 200 personas simulated across 365 days. Forming behavioral cohorts...", 7360, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      magicMoment("Demo Magic Moment #1:", "The user just ran a 12-month market simulation in 30 seconds. They watched it unfold. No traditional research can do this."),
      spacer(),

      heading("4.4 What the Simulation Computes", HeadingLevel.HEADING_2),
      para("Under the hood, the engine runs a day-level simulation using the existing EventEngine:"),
      bulletItem("10 decision variables evolve daily: trust, habit_strength, child_acceptance, price_salience, reorder_urgency, fatigue, perceived_value, brand_salience, effort_friction, discretionary_budget"),
      bulletItem("Environmental triggers fire on realistic schedules (payday cycles, seasonal illness spikes, festival periods, school exam stress)"),
      bulletItem("Purchase events are recorded and written to each persona\u2019s purchase_history field"),
      bulletItem("Word-of-mouth propagation between personas in the same city/social cluster"),
      bulletItem("Churn events recorded when habit_strength decays below threshold for 30+ consecutive days"),
      spacer(),

      heading("4.5 Cohort Formation from Simulation Results", HeadingLevel.HEADING_2),
      para("After simulation, the cohort classifier groups personas into 5 behavioral cohorts based on ACTUAL simulated behavior:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2200, 4160, 3000],
        rows: [
          new TableRow({ children: [headerCell("Cohort", 2200), headerCell("Definition (from simulation data)", 4160), headerCell("Typical Size", 3000)] }),
          new TableRow({ children: [
            cell("Never Aware", 2200, { bold: true, fill: C.lightGrey }),
            cell("Product introduction resulted in zero engagement. No awareness across 12 months.", 4160, { fill: C.lightGrey }),
            cell("15\u201325%", 3000, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Aware, Not Tried", 2200, { bold: true }),
            cell("Became aware but never purchased. Considered but dropped out.", 4160),
            cell("25\u201335%", 3000)
          ] }),
          new TableRow({ children: [
            cell("First-Time Buyer", 2200, { bold: true, fill: C.lightGrey }),
            cell("Made exactly 1 purchase. Did not repeat.", 4160, { fill: C.lightGrey }),
            cell("10\u201320%", 3000, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Current User", 2200, { bold: true }),
            cell("Made 2+ purchases AND purchased within last 60 simulated days.", 4160),
            cell("10\u201320%", 3000)
          ] }),
          new TableRow({ children: [
            cell("Lapsed User", 2200, { bold: true, fill: C.lightGrey }),
            cell("Made 2+ purchases but last purchase > 60 days ago. Was active, stopped.", 4160, { fill: C.lightGrey }),
            cell("5\u201315%", 3000, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      heading("4.6 System-Narrated Cohort Dashboard", HeadingLevel.HEADING_2),
      para("The system SPEAKS before showing the dashboard:"),
      systemVoice("Simulation complete. Here\u2019s what 73,000 simulated days across 200 households revealed: 28% purchased at least once, but only 18% repeated. The critical drop-off happens between day 21 and day 45 post-first-purchase \u2014 that\u2019s where child_acceptance and brand_salience both decay sharply. 40% of first-time buyers never came back. The pattern concentrates in Tier-2 cities among price-conscious mothers with children aged 3\u20135, where price_salience spikes right as habit_strength fails to build."),
      spacer(),
      para("Then the dashboard shows:"),
      bulletItem("Cohort distribution bar chart (count and % for each of 5 cohorts)"),
      bulletItem("Per-cohort summary cards: average purchase count, time-to-first-purchase, top drop-off reasons, representative personas"),
      bulletItem("Funnel visualization: Awareness \u2192 Trial \u2192 Repeat \u2192 Loyalty, with conversion rates"),
      bulletItem("Key metrics: Overall adoption rate, repeat rate, average purchases/year"),
      spacer(),

      magicMoment("Demo Magic Moment #2:", "The system narrates what it found BEFORE showing the charts. The audience hears the insight, then sees the evidence. This feels like intelligence, not a dashboard."),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 5 — PHASE 2: DECOMPOSITION & PROBING
      // ═════════════════════════════════════════════════════════
      heading("5. Phase 2 \u2014 System Decomposition & Probing Tree", HeadingLevel.HEADING_1),
      para("With behavioral cohorts established, the SYSTEM now decomposes the problem. The user\u2019s role shifts from driver to reviewer. This phase merges the old \u201CResearch\u201D and \u201CDiagnose\u201D tabs into a single, system-led analytical journey."),
      spacer(),

      heading("5.1 System Presents Hypothesis Decomposition", HeadingLevel.HEADING_2),
      para("The system generates hypotheses automatically from predefined probing trees (predefined_trees.py) enriched with baseline simulation data. The user does NOT formulate hypotheses \u2014 the system does."),
      spacer(),
      systemVoice("I\u2019ve analyzed the simulation trajectories of your 200 personas and identified 4 signals worth investigating. These aren\u2019t generic hypotheses \u2014 they emerged directly from what the simulation showed:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [700, 2800, 2930, 2930],
        rows: [
          new TableRow({ children: [headerCell("#", 700), headerCell("Hypothesis", 2800), headerCell("Target Cohort(s)", 2930), headerCell("Simulation Signal", 2930)] }),
          new TableRow({ children: [
            cell("H1", 700, { bold: true, fill: C.lightGrey }),
            cell("Price re-evaluation kills the second purchase", 2800, { fill: C.lightGrey }),
            cell("Lapsed Users (62% have price_salience > 0.7)", 2930, { fill: C.lightGrey }),
            cell("Simulation showed price_salience spikes 18% between purchase 1 and the reorder window. Lapsed users in Tier-2/3 cities show 2.1x higher spike than Metro.", 2930, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("H2", 700, { bold: true }),
            cell("Child taste fatigue triggers lapse at week 3", 2800),
            cell("Lapsed Users, First-Time Buyers", 2930),
            cell("child_acceptance decays below 0.4 by day 21 for 71% of lapsed users. Current users show stable acceptance above 0.6. The decay curve is sharp, not gradual.", 2930)
          ] }),
          new TableRow({ children: [
            cell("H3", 700, { bold: true, fill: C.lightGrey }),
            cell("Silent lapse: product drops out of memory without re-engagement", 2800, { fill: C.lightGrey }),
            cell("First-Time Buyers (83% with zero brand touchpoints post-purchase)", 2930, { fill: C.lightGrey }),
            cell("brand_salience drops to near-zero within 30 days of first purchase for 83% of single-buyers. No re-engagement trigger fires in the simulation. They didn\u2019t reject the product \u2014 they simply forgot.", 2930, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("H4", 700, { bold: true }),
            cell("Competitive substitution to home remedies or Bournvita", 2800),
            cell("Lapsed Users", 2930),
            cell("Weak signal: only 23% of lapsed users show elevated competitive_salience. This may not be the primary driver, but worth testing.", 2930)
          ] }),
        ]
      }),
      spacer(),

      para("Each hypothesis comes pre-mapped to target cohorts and proposed probe sequence. The user\u2019s job:"),
      bulletItem("Review the hypotheses and rationale"),
      bulletItem("Check/uncheck which to investigate (defaults: all selected)"),
      bulletItem("Optionally add their own hypothesis (escape hatch, not the default)"),
      bulletItem("Click \u201CRun Investigation\u201D to trigger the probing tree"),
      spacer(),

      magicMoment("Demo Magic Moment #3:", "The system presents hypotheses IT generated, each with rationale and target cohorts already mapped. The user didn\u2019t have to think of a single hypothesis. They just approve."),
      spacer(),

      heading("5.2 The Probing Tree (Sequential, Deepening)", HeadingLevel.HEADING_2),
      para("This is the \u201C5 Whys\u201D mechanism from the founding vision. For each approved hypothesis, the system runs probes in sequence \u2014 each level going deeper:"),
      spacer(),

      boldPara("Level 1 \u2014 Attribute Probe: ", "Is the signal statistically real?"),
      bulletItem("System runs Cohen\u2019s d effect size analysis between target cohort and comparison cohort"),
      bulletItem("Output: Effect size (small/medium/large), distribution overlay, significance"),
      bulletItem("Infrastructure: src/probing/engine.py \u2192 _run_attribute_probe()"),
      spacer(),

      systemVoice("H2 shows a strong signal: child_acceptance effect size d=0.72 (large) between Current Users and Lapsed Users. But I\u2019m also seeing a weaker signal on H1 \u2014 price_salience shows d=0.34, which is small but not negligible. It\u2019s possible price and taste are interacting: parents tolerate the price WHILE the child likes it, but re-evaluate once acceptance drops. Investigating H2 deeper first \u2014 it\u2019s the stronger signal."),
      spacer(),

      boldPara("Level 2 \u2014 Interview Probe: ", "What\u2019s the lived experience behind the signal?"),
      bulletItem("System selects 5\u20138 diverse personas from target cohort via smart sampling"),
      bulletItem("LLM role-plays each persona, answering research questions in character"),
      bulletItem("The LLM receives full persona profile, narrative, memory layer, AND simulation trajectory"),
      bulletItem("Output: Thematic analysis, verbatim quotes, pattern detection"),
      bulletItem("Infrastructure: src/probing/engine.py \u2192 _run_interview_probe()"),
      spacer(),

      systemVoice("Interview results are mixed but directional. 5 of 6 lapsed users mentioned child taste rejection, but the reasons diverge: 3 cite monotony (\u201Csame flavor every day\u201D), 1 cites texture issues, and 1 says the child simply lost interest after the novelty period. The 6th persona (Meera K., Tier-2, working mother) said taste wasn\u2019t the issue \u2014 she just forgot to reorder. This outlier aligns more with H3. Pattern: taste fatigue is the dominant thread, but it\u2019s not the only one. Moving to counterfactual to test whether addressing taste actually shifts behavior."),
      spacer(),

      boldPara("Level 3 \u2014 Simulation Probe: ", "Does a counterfactual intervention actually shift behavior?"),
      bulletItem("System runs counterfactual simulation: \u201CWhat if we added flavor variants?\u201D"),
      bulletItem("Engine re-runs temporal simulation with modification applied"),
      bulletItem("Output: Lift %, before/after cohort distribution, per-persona movement"),
      bulletItem("Infrastructure: src/simulation/counterfactual.py"),
      spacer(),

      systemVoice("Counterfactual result: flavor rotation increases repeat rate from 18% to 27% (+50% lift). However, the lift is not uniform \u2014 it concentrates in Tier-1/Metro lapsed users (68% of the lift), while Tier-2/3 lapsed users show weaker response (+19% lift). This suggests taste fatigue is the primary barrier for Metro households, but Tier-2/3 may have a compounding price barrier that flavor alone doesn\u2019t address."),
      spacer(),

      heading("5.3 Probing Tree Visualization", HeadingLevel.HEADING_2),
      para("The UI shows the probing tree building in real-time as each level completes:"),
      spacer(),
      para("Problem: \u201CWhy is repeat purchase low?\u201D", { bold: true }),
      bulletItem("H1: Price re-evaluation \u2192 Attribute: d=0.34 (small but present) \u2192 Likely a moderator, not root cause. Parked for now."),
      bulletItem("H2: Taste fatigue \u2192 Attribute: d=0.72 (large) \u2192 Interview: 5/6 confirm, but reasons diverge (monotony vs. texture vs. novelty fade) \u2192 Simulation: +50% lift (Metro-concentrated) \u2192 CONFIRMED as primary driver"),
      bulletItem("H3: Silent lapse \u2192 Attribute: d=0.81 (large) \u2192 Interview: 4/6 confirm, 1 outlier matches H3 pattern \u2192 Simulation: +33% lift \u2192 CONFIRMED as compounding factor"),
      bulletItem("H4: Competition \u2192 Attribute: d=0.28 (weak) \u2192 Insufficient signal to pursue. Likely downstream of H2+H3."),
      spacer(),

      para("Each node is clickable to see the full probe results. The tree grows downward as the system digs deeper, giving the user a visual sense of the analytical journey."),
      spacer(),

      heading("5.4 Cross-Hypothesis Synthesis", HeadingLevel.HEADING_2),
      para("After all probe chains complete, the system identifies patterns across hypotheses:"),
      systemVoice("Cross-hypothesis pattern: H2 and H3 are not independent \u2014 they form a causal chain. Taste fatigue (H2) creates the initial vulnerability at week 3, and absence of re-engagement (H3) ensures the lapse becomes permanent. In isolation, each explains part of the picture: H2 alone accounts for ~60% of lapsed users, H3 alone for ~40%. But 28% of lapsed users show BOTH signals simultaneously. Meanwhile, H1 (price) appears to be a moderator, not a root cause: price_salience rises AFTER taste fatigue sets in, suggesting parents re-evaluate value once the child stops liking it. H4 (competition) is weak and likely downstream of the same dynamic."),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 6 — PHASE 3: CORE FINDING & DEEP DIVES
      // ═════════════════════════════════════════════════════════
      heading("6. Phase 3 \u2014 Core Finding & Deep Dives", HeadingLevel.HEADING_1),
      para("This phase delivers the CLIMAX of the analytical journey: the Core Issue Statement. It then offers optional depth through persona interviews and generates the downloadable report."),
      spacer(),

      heading("6.1 Core Issue Statement (Key Design Decision)", HeadingLevel.HEADING_2),
      para("The system synthesizes all probe results into a single, sharp statement. This is the moment the demo audience should feel: \u201CThis system just did in 20 minutes what a research team does in 3 months.\u201D"),
      spacer(),

      new Paragraph({
        spacing: { before: 160, after: 160 },
        indent: { left: 360, right: 360 },
        shading: { fill: "FDEBD0", type: ShadingType.CLEAR },
        border: {
          top: { style: BorderStyle.SINGLE, size: 4, color: C.orange, space: 4 },
          bottom: { style: BorderStyle.SINGLE, size: 4, color: C.orange, space: 4 },
          left: { style: BorderStyle.SINGLE, size: 12, color: C.orange, space: 8 },
          right: { style: BorderStyle.SINGLE, size: 4, color: C.orange, space: 4 },
        },
        children: [
          new TextRun({ text: "Core Finding: ", bold: true, size: 26, font: "Arial", color: C.orange }),
          new TextRun({ text: "Repeat purchase fails because of a two-stage breakdown: child taste fatigue triggers disengagement at week 3 (H2 confirmed, d=0.72, strongest in Metro), and the absence of any re-engagement mechanism ensures the lapse becomes permanent (H3 confirmed, d=0.81, 83% of single-buyers had zero brand touchpoints post-purchase). Price sensitivity (H1) is a moderator that amplifies in Tier-2/3 cities but is not the root cause \u2014 it rises AFTER taste fatigue sets in. Competitive substitution (H4) is weak and downstream.", size: 22, font: "Arial" }),
        ]
      }),
      spacer(),

      para("Below the core finding, an evidence chain shows exactly how each probe contributed:"),
      bulletItem("H2 Level 1: Attribute probe \u2192 d=0.72 (large effect, taste acceptance)"),
      subBullet("H2 Level 2: Interview \u2192 5/6 lapsed users confirm taste fatigue at 2\u20133 weeks"),
      subBullet("H2 Level 3: Counterfactual \u2192 flavor rotation yields +50% repeat lift"),
      bulletItem("H3 Level 1: Attribute probe \u2192 d=0.81 (large effect, re-engagement absence)"),
      subBullet("H3 Level 2: Interview \u2192 4/6 confirm \u201Cjust forgot to reorder\u201D"),
      subBullet("H3 Level 3: Counterfactual \u2192 WhatsApp reminders yield +33% repeat lift"),
      spacer(),

      magicMoment("Demo Magic Moment #4:", "Full-screen core finding. One sentence. Backed by quantified evidence. This is the moment the audience goes \u201CWhoa.\u201D No human analyst synthesizes this fast."),
      spacer(),

      heading("6.2 Deep-Dive Interviews (Optional)", HeadingLevel.HEADING_2),
      para("The user can optionally drill into individual persona interviews for qualitative depth:"),
      spacer(),

      heading("6.2.1 Smart Sampling", HeadingLevel.HEADING_3),
      bulletItem("Platform selects personas using stratified sampling across relevant cohorts"),
      bulletItem("Diversity enforced across city tiers, income brackets, child age bands"),
      bulletItem("Priority to personas near cohort boundaries (almost-converted, recently-lapsed)"),
      spacer(),

      heading("6.2.2 Interview Protocol", HeadingLevel.HEADING_3),
      numberedItem("Context loading \u2014 LLM receives full profile, narrative, memory layer, purchase history, AND simulation trajectory"),
      numberedItem("Opening \u2014 Persona introduces themselves referencing their life story"),
      numberedItem("Guided exploration \u2014 Structured questions probe the hypothesis under investigation"),
      numberedItem("Follow-up probing \u2014 LLM identifies contradictions and probes deeper"),
      numberedItem("Behavioral validation \u2014 Responses cross-checked against simulated behavior"),
      spacer(),

      heading("6.2.3 Pattern Analysis", HeadingLevel.HEADING_3),
      bulletItem("Theme extraction across all interviews"),
      bulletItem("Contradiction detection (persona claims vs. simulated behavior)"),
      bulletItem("Quote bank organized by theme with persona attribution"),
      spacer(),

      heading("6.3 Synthesis Report", HeadingLevel.HEADING_2),
      para("The platform generates a downloadable PDF/DOCX containing:"),
      bulletItem("Executive summary with the Core Issue Statement"),
      bulletItem("Cohort analysis with behavioral data from simulation"),
      bulletItem("Hypothesis validation results with full evidence chains"),
      bulletItem("Interview highlights and thematic analysis"),
      bulletItem("Strategic recommendations prioritized by impact and feasibility"),
      bulletItem("Appendix: Full profiles for interviewed personas"),
      spacer(),
      para("Existing infrastructure: src/analysis/executive_summary.py (LLM narrative), src/analysis/research_consolidator.py (report assembly), src/analysis/pdf_export.py (export)."),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 7 — PHASE 4: INTERVENTIONS & SIMULATION
      // ═════════════════════════════════════════════════════════
      heading("7. Phase 4 \u2014 System-Proposed Interventions & Simulation", HeadingLevel.HEADING_1),
      para("The system doesn\u2019t wait for the user to design interventions. It PROPOSES them based on the Core Finding, then runs all simulations. The user\u2019s role is to review, not to design."),
      spacer(),

      heading("7.1 System Proposes Interventions (Key Design Decision)", HeadingLevel.HEADING_2),
      para("Based on the Core Finding and the diagnostic evidence, the system auto-generates interventions using the existing auto_variants.py engine:"),
      spacer(),

      systemVoice("Based on the core issue (taste fatigue + re-engagement gap), I recommend 3 interventions:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [700, 2200, 3230, 3230],
        rows: [
          new TableRow({ children: [headerCell("#", 700), headerCell("Intervention", 2200), headerCell("Addresses", 3230), headerCell("System Rationale", 3230)] }),
          new TableRow({ children: [
            cell("1", 700, { bold: true, fill: C.lightGrey }),
            cell("Flavor rotation program", 2200, { bold: true, fill: C.lightGrey }),
            cell("H2: Taste fatigue (Lapsed Users)", 3230, { fill: C.lightGrey }),
            cell("If taste novelty fading is the trigger, introducing 3 rotating flavors prevents adaptation.", 3230, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("2", 700, { bold: true }),
            cell("WhatsApp reorder reminders at day 25", 2200, { bold: true }),
            cell("H3: Re-engagement gap (First-Time Buyers)", 3230),
            cell("If the product drops out of working memory, a timely nudge at the reorder threshold prevents silent lapse.", 3230)
          ] }),
          new TableRow({ children: [
            cell("3", 700, { bold: true, fill: C.lightGrey }),
            cell("Combined: Flavor + reminder + 10% loyalty discount", 2200, { bold: true, fill: C.lightGrey }),
            cell("H2 + H3 combined (all post-trial cohorts)", 3230, { fill: C.lightGrey }),
            cell("Cross-hypothesis analysis showed compounding effect. Testing both barriers simultaneously.", 3230, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      para("Additionally, the system auto-generates 2 alternative interventions (lighter-touch variants from auto_variants.py) for comparison:"),
      bulletItem("Alt A: 15% promotional discount (tests if price alone moves the needle, despite H1 being only partially supported)"),
      bulletItem("Alt B: Pediatrician endorsement campaign (tests authority-led trust signal as alternative to direct re-engagement)"),
      spacer(),

      para("The user can:"),
      bulletItem("Accept the system\u2019s proposals as-is"),
      bulletItem("Modify parameters (e.g., change discount from 10% to 15%)"),
      bulletItem("Add their own intervention (escape hatch)"),
      bulletItem("Click \u201CRun All Simulations\u201D"),
      spacer(),

      magicMoment("Demo Magic Moment #5:", "The system proposed interventions tied to the exact hypotheses it just validated. It solved the problem, not just diagnosed it. The user didn\u2019t design anything."),
      spacer(),

      heading("7.2 The Intervention Matrix (Reference)", HeadingLevel.HEADING_2),
      para("For users who want to design custom interventions, the 4\u00D74 matrix provides a structured framework:"),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2340, 2340, 2340, 2340],
        rows: [
          new TableRow({ children: [headerCell("", 2340), headerCell("Product Change", 2340), headerCell("Communication", 2340), headerCell("Distribution", 2340)] }),
          new TableRow({ children: [
            cell("Acquisition", 2340, { bold: true, fill: C.highlight }),
            cell("Trial sachet SKU", 2340), cell("Doctor endorsement", 2340), cell("Pharmacy channel", 2340)
          ] }),
          new TableRow({ children: [
            cell("Retention", 2340, { bold: true, fill: C.highlight }),
            cell("Flavor variants", 2340), cell("WhatsApp reminders", 2340), cell("Auto-delivery subscription", 2340)
          ] }),
          new TableRow({ children: [
            cell("Win-back", 2340, { bold: true, fill: C.highlight }),
            cell("Reformulated product", 2340), cell("Win-back discount", 2340), cell("Home delivery re-engagement", 2340)
          ] }),
          new TableRow({ children: [
            cell("Awareness", 2340, { bold: true, fill: C.highlight }),
            cell("Free sample program", 2340), cell("Influencer campaign", 2340), cell("School tie-up", 2340)
          ] }),
        ]
      }),
      spacer(),

      heading("7.3 Counterfactual Simulation (Visible, Dramatic)", HeadingLevel.HEADING_2),
      para("For each intervention (system-proposed + alternatives), the engine re-runs the full 12-month temporal simulation with modifications applied. The same dramatic progress treatment as Phase 1:"),
      spacer(),

      systemVoice("Running 5 counterfactual simulations in parallel. Each modifies the baseline scenario and re-simulates 200 personas across 12 months..."),
      spacer(),

      para("After completion, the system narrates before showing the comparison \u2014 including trade-offs, not just lift numbers:"),
      systemVoice("Results are in. The combined intervention delivers the highest raw lift (+72%), but it\u2019s also the most complex to execute and the most expensive. Flavor rotation alone delivers 80% of the lift at roughly a third of the cost. Here\u2019s the full comparison with implementation trade-offs:"),
      spacer(),

      heading("7.4 Results Comparison Dashboard", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1560, 1560, 1560, 1560, 1560, 1560],
        rows: [
          new TableRow({ children: [
            headerCell("Metric", 1560), headerCell("Baseline", 1560), headerCell("Intervention 1", 1560),
            headerCell("Intervention 2", 1560), headerCell("Intervention 3", 1560), headerCell("Alt A", 1560)
          ] }),
          new TableRow({ children: [
            cell("Adoption Rate", 1560, { bold: true, fill: C.lightGrey }),
            cell("28%", 1560, { fill: C.lightGrey }), cell("41% (+46%)", 1560, { fill: C.lightGrey }),
            cell("37% (+32%)", 1560, { fill: C.lightGrey }), cell("48% (+72%)", 1560, { fill: C.lightGrey }),
            cell("32% (+14%)", 1560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Repeat Rate", 1560, { bold: true }),
            cell("18%", 1560), cell("27% (+50%)", 1560),
            cell("24% (+33%)", 1560), cell("31% (+72%)", 1560),
            cell("20% (+11%)", 1560)
          ] }),
          new TableRow({ children: [
            cell("Avg Purchases/Yr", 1560, { bold: true, fill: C.lightGrey }),
            cell("1.2", 1560, { fill: C.lightGrey }), cell("2.8", 1560, { fill: C.lightGrey }),
            cell("2.3", 1560, { fill: C.lightGrey }), cell("3.4", 1560, { fill: C.lightGrey }),
            cell("1.6", 1560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Lapsed Reduction", 1560, { bold: true }),
            cell("\u2014", 1560), cell("-8pp", 1560),
            cell("-6pp", 1560), cell("-12pp", 1560),
            cell("-2pp", 1560)
          ] }),
          new TableRow({ children: [
            cell("Impl. Complexity", 1560, { bold: true, fill: C.lightGrey }),
            cell("\u2014", 1560, { fill: C.lightGrey }), cell("Medium (R&D)", 1560, { fill: C.lightGrey }),
            cell("Low (tech only)", 1560, { fill: C.lightGrey }), cell("High (multi-team)", 1560, { fill: C.lightGrey }),
            cell("Low (pricing)", 1560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Time to Market", 1560, { bold: true }),
            cell("\u2014", 1560), cell("3\u20134 months", 1560),
            cell("2\u20133 weeks", 1560), cell("4\u20136 months", 1560),
            cell("1 week", 1560)
          ] }),
          new TableRow({ children: [
            cell("Estimated Cost", 1560, { bold: true, fill: C.lightGrey }),
            cell("\u2014", 1560, { fill: C.lightGrey }), cell("Medium", 1560, { fill: C.lightGrey }),
            cell("Low", 1560, { fill: C.lightGrey }), cell("High", 1560, { fill: C.lightGrey }),
            cell("Margin impact", 1560, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      para("Each cell is clickable to see per-persona movement: which specific personas changed behavior and why."),
      spacer(),

      heading("7.5 System Recommendation (with Trade-offs)", HeadingLevel.HEADING_2),
      para("The system doesn\u2019t just recommend the highest-lift option. It reasons about trade-offs:"),
      spacer(),
      systemVoice("The combined intervention (#3) delivers the highest lift (+72%), but requires coordination across R&D (new flavors), tech (WhatsApp integration), and pricing (loyalty discount). Time-to-market: 4\u20136 months. For a brand at your stage, that\u2019s high risk."),
      spacer(),
      systemVoice("My recommendation: Start with Intervention #2 (WhatsApp reminders) immediately \u2014 it\u2019s deployable in 2\u20133 weeks, costs almost nothing, and addresses 40% of lapsed users who simply forgot to reorder. In parallel, begin R&D on flavor rotation (Intervention #1). When flavors are ready (month 3\u20134), layer them in. This staged approach captures 80% of the combined lift while keeping execution risk low."),
      spacer(),
      systemVoice("The price discount (Alt A) shows +14% lift but I\u2019d caution against it: our analysis suggests price sensitivity is a downstream symptom of taste fatigue, not a root cause. Discounting trains margin expectations without fixing the underlying issue. If Tier-2/3 price sensitivity persists after flavor rotation, revisit then with targeted sachet pricing rather than broad discounts."),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 8 — NAVIGATION & UX PRINCIPLES
      // ═════════════════════════════════════════════════════════
      heading("8. Navigation, UX Principles & Magic Moments", HeadingLevel.HEADING_1),

      heading("8.1 Sidebar Navigation", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1200, 2400, 2880, 2880],
        rows: [
          new TableRow({ children: [headerCell("Phase", 1200), headerCell("Label", 2400), headerCell("Status Indicator", 2880), headerCell("Lock Condition", 2880)] }),
          new TableRow({ children: [
            cell("0", 1200, { fill: C.lightGrey }), cell("Explore Population", 2400, { fill: C.lightGrey }),
            cell("Always active (green dot)", 2880, { fill: C.lightGrey }), cell("Never locked", 2880, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("1", 1200), cell("Problem & Simulation", 2400),
            cell("Grey until problem selected", 2880), cell("Requires population loaded", 2880)
          ] }),
          new TableRow({ children: [
            cell("2", 1200, { fill: C.lightGrey }), cell("Decomposition", 2400, { fill: C.lightGrey }),
            cell("Locked until Phase 1 complete", 2880, { fill: C.lightGrey }), cell("Requires baseline simulation", 2880, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("3", 1200), cell("Core Finding", 2400),
            cell("Locked until probing done", 2880), cell("Requires at least 1 probe chain", 2880)
          ] }),
          new TableRow({ children: [
            cell("4", 1200, { fill: C.lightGrey }), cell("Interventions", 2400, { fill: C.lightGrey }),
            cell("Locked until core finding", 2880, { fill: C.lightGrey }), cell("Requires Core Finding generated", 2880, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      heading("8.2 The System Voice Pattern", HeadingLevel.HEADING_2),
      para("Every major computation follows the same UX pattern:"),
      numberedItem("System explains what it will do (narrative setup)"),
      numberedItem("User initiates (explicit button click)"),
      numberedItem("Computation runs visibly with narrative progress"),
      numberedItem("System narrates what it found (insight-first)"),
      numberedItem("Dashboard/data appears below the narration (evidence second)"),
      spacer(),
      para("This pattern ensures the user ALWAYS encounters the system\u2019s interpretation before raw data. The system is the analyst; the dashboard is the appendix."),
      spacer(),

      heading("8.3 Display Rules", HeadingLevel.HEADING_2),
      bulletItem("Never display raw field names: \u201Cprice_salience\u201D \u2192 \u201CPrice Sensitivity\u201D"),
      bulletItem("Never display raw UUIDs: Always show human-readable identifiers"),
      bulletItem("All scores show contextual explanation: \u201C0.72 (High \u2014 this persona is very price-conscious)\u201D"),
      bulletItem("Charts always have a system narration sentence above them"),
      bulletItem("LLM responses are structured with headers, not wall-of-text paragraphs"),
      bulletItem("Loading states show narrative progress, not spinners"),
      spacer(),

      heading("8.4 The Five Magic Moments (Demo Narrative Summary)", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [700, 2200, 3230, 3230],
        rows: [
          new TableRow({ children: [headerCell("#", 700), headerCell("Moment", 2200), headerCell("Where in Flow", 3230), headerCell("User Feeling", 3230)] }),
          new TableRow({ children: [
            cell("1", 700, { bold: true, fill: C.lightGrey }),
            cell("The Simulation Event", 2200, { bold: true, fill: C.lightGrey }),
            cell("Phase 1: 12-month simulation runs live with narrative progress", 3230, { fill: C.lightGrey }),
            cell("\u201CI just ran a year-long market simulation in 30 seconds\u201D", 3230, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("2", 700, { bold: true }),
            cell("The System Speaks", 2200, { bold: true }),
            cell("Phase 1: System narrates cohort results before showing charts", 3230),
            cell("\u201CIt already understands my problem\u201D", 3230)
          ] }),
          new TableRow({ children: [
            cell("3", 700, { bold: true, fill: C.lightGrey }),
            cell("The Hypothesis Tree", 2200, { bold: true, fill: C.lightGrey }),
            cell("Phase 2: System presents 4 hypotheses it generated, user just approves", 3230, { fill: C.lightGrey }),
            cell("\u201CIt\u2019s doing the thinking for me\u201D", 3230, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("4", 700, { bold: true }),
            cell("The Core Finding", 2200, { bold: true }),
            cell("Phase 3: Full-screen single statement with quantified evidence chain", 3230),
            cell("\u201CNo human analyst does this in 20 minutes\u201D", 3230)
          ] }),
          new TableRow({ children: [
            cell("5", 700, { bold: true, fill: C.lightGrey }),
            cell("The System Solves It", 2200, { bold: true, fill: C.lightGrey }),
            cell("Phase 4: System proposes interventions tied to exact findings, already simulated", 3230, { fill: C.lightGrey }),
            cell("\u201CIt\u2019s not just a tool \u2014 it\u2019s solving my problem\u201D", 3230, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      heading("8.5 Session Persistence", HeadingLevel.HEADING_2),
      bulletItem("Population and simulation results cached in st.session_state"),
      bulletItem("Phase completion status persists within a session"),
      bulletItem("Users can return to any completed phase without re-running simulations"),
      bulletItem("Scenario results keyed by problem ID for multi-problem comparison"),
      spacer(),

      heading("8.6 Error Handling", HeadingLevel.HEADING_2),
      bulletItem("LLM failures: Graceful fallback with \u201CRetry\u201D button, never raw error traces"),
      bulletItem("Unexpected results: System explains (\u201C0% adoption detected \u2014 likely due to age range mismatch. Consider adjusting target age.\u201D)"),
      bulletItem("Missing population: Redirect to generation flow with clear instructions"),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 9 — INFRASTRUCTURE MAPPING
      // ═════════════════════════════════════════════════════════
      heading("9. Infrastructure Mapping (Build / Reuse / Defer)", HeadingLevel.HEADING_1),
      para("A key principle is to maximize reuse. The system-led intelligence mostly exists in the codebase \u2014 it needs to be staged as the hero, not rebuilt."),
      spacer(),

      heading("9.1 Reuse Existing (Ready Now)", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2500, 3430, 3430],
        rows: [
          new TableRow({ children: [headerCell("Component", 2500), headerCell("Source File", 3430), headerCell("Used In Phase", 3430)] }),
          new TableRow({ children: [
            cell("Population Generator", 2500, { fill: C.lightGrey }), cell("src/generation/population.py", 3430, { fill: C.lightGrey }),
            cell("Phase 0 (population creation)", 3430, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Persona Schema (200+ attributes)", 2500), cell("src/taxonomy/schema.py", 3430),
            cell("All phases", 3430)
          ] }),
          new TableRow({ children: [
            cell("LLM Narrative Generator", 2500, { fill: C.lightGrey }), cell("src/generation/tier2_generator.py", 3430, { fill: C.lightGrey }),
            cell("Phase 0 (persona depth)", 3430, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Problem Templates", 2500), cell("src/analysis/problem_templates.py", 3430),
            cell("Phase 1 (problem selection)", 3430)
          ] }),
          new TableRow({ children: [
            cell("Predefined Probing Trees", 2500, { fill: C.lightGrey }), cell("src/probing/predefined_trees.py", 3430, { fill: C.lightGrey }),
            cell("Phase 2 (hypothesis decomposition)", 3430, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Problem Decomposition", 2500), cell("src/analysis/problem_decomposition.py", 3430),
            cell("Phase 2 (cohort-hypothesis mapping)", 3430)
          ] }),
          new TableRow({ children: [
            cell("Event Engine (day-level sim)", 2500, { fill: C.lightGrey }), cell("src/simulation/event_engine.py", 3430, { fill: C.lightGrey }),
            cell("Phase 1 + 4 (baseline + counterfactual)", 3430, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Cohort Classifier", 2500), cell("src/analysis/cohort_classifier.py", 3430),
            cell("Phase 1 (cohort formation)", 3430)
          ] }),
          new TableRow({ children: [
            cell("Probe Engine (3 types)", 2500, { fill: C.lightGrey }), cell("src/probing/engine.py", 3430, { fill: C.lightGrey }),
            cell("Phase 2 (probing tree execution)", 3430, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Auto-Variant Generator", 2500), cell("src/simulation/auto_variants.py", 3430),
            cell("Phase 4 (system-proposed interventions)", 3430)
          ] }),
          new TableRow({ children: [
            cell("Counterfactual Simulator", 2500, { fill: C.lightGrey }), cell("src/simulation/counterfactual.py", 3430, { fill: C.lightGrey }),
            cell("Phase 2 Level 3 probes + Phase 4", 3430, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Executive Summary (LLM narrative)", 2500), cell("src/analysis/executive_summary.py", 3430),
            cell("Phase 3 (Core Finding), Phase 4 (recommendation)", 3430)
          ] }),
          new TableRow({ children: [
            cell("Report Consolidator", 2500, { fill: C.lightGrey }), cell("src/analysis/research_consolidator.py", 3430, { fill: C.lightGrey }),
            cell("Phase 3 (synthesis report)", 3430, { fill: C.lightGrey })
          ] }),
        ]
      }),
      spacer(),

      heading("9.2 Build New (Sprint Work)", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2500, 3930, 2930],
        rows: [
          new TableRow({ children: [headerCell("Component", 2500), headerCell("Description", 3930), headerCell("Effort", 2930)] }),
          new TableRow({ children: [
            cell("Problem \u2192 Scenario Mapper", 2500, { bold: true, fill: C.lightGrey }),
            cell("UI that presents business problems and auto-maps to scenario config. Wire problem_templates to scenario selection.", 3930, { fill: C.lightGrey }),
            cell("Small (mapping logic exists, needs UI)", 2930, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Simulation Narrative Progress", 2500, { bold: true }),
            cell("Dramatic progress display during simulation: monthly narrative updates instead of spinner.", 3930),
            cell("Small (Streamlit st.status + polling)", 2930)
          ] }),
          new TableRow({ children: [
            cell("System Voice Narration Layer", 2500, { bold: true, fill: C.lightGrey }),
            cell("Generate system narration text for each phase transition. Use executive_summary.py patterns.", 3930, { fill: C.lightGrey }),
            cell("Small (prompt engineering + UI component)", 2930, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Sequential Probe Orchestrator", 2500, { bold: true }),
            cell("Run probes in order (L1 \u2192 L2 \u2192 L3) per hypothesis, using predefined_trees.py probe ordering.", 3930),
            cell("Medium (orchestration logic over existing probes)", 2930)
          ] }),
          new TableRow({ children: [
            cell("Core Finding Synthesis", 2500, { bold: true, fill: C.lightGrey }),
            cell("Aggregate all probe results into single Core Issue Statement. Extend executive_summary.py.", 3930, { fill: C.lightGrey }),
            cell("Medium (LLM prompt + evidence chain assembly)", 2930, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Purchase History Population", 2500, { bold: true }),
            cell("Wire temporal simulation output to persona.purchase_history field.", 3930),
            cell("Small (field exists, needs wiring)", 2930)
          ] }),
          new TableRow({ children: [
            cell("Semantic Memory Read-back", 2500, { bold: true, fill: C.lightGrey }),
            cell("Feed persona narratives/anchors into decision engine and interview prompts.", 3930, { fill: C.lightGrey }),
            cell("Small (data exists, needs integration)", 2930, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Phase Gating Logic", 2500, { bold: true }),
            cell("Sidebar lock/unlock based on phase completion status in session_state.", 3930),
            cell("Small (conditional rendering)", 2930)
          ] }),
        ]
      }),
      spacer(),

      heading("9.3 Defer to v2.0+ (Do Not Build for Demo)", HeadingLevel.HEADING_2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3120, 6240],
        rows: [
          new TableRow({ children: [headerCell("Component", 3120), headerCell("Why Defer", 6240)] }),
          new TableRow({ children: [
            cell("Inter-Persona Learning (Mirofish)", 3120, { fill: C.lightGrey }),
            cell("Requires agent orchestration framework. Massive scope, zero demo value.", 6240, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Weekly Real-World Data Scraping", 3120),
            cell("Requires data pipeline infra. Doesn\u2019t change the demo flow.", 6240)
          ] }),
          new TableRow({ children: [
            cell("Persona Schema Evolution", 3120, { fill: C.lightGrey }),
            cell("Personas evolving beliefs over time. Simulation evolves decision variables; schema evolution is v2.0+.", 6240, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Multi-Product Competition", 3120),
            cell("Requires scenario composition engine. Demo focuses on single-product decisions.", 6240)
          ] }),
          new TableRow({ children: [
            cell("Custom Persona Upload / PII", 3120, { fill: C.lightGrey }),
            cell("Legal and infra complexity. Use synthetic personas for demo.", 6240, { fill: C.lightGrey })
          ] }),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // SECTION 10 — PAGE-BY-PAGE WIREFRAMES
      // ═════════════════════════════════════════════════════════
      heading("10. Page-by-Page Wireframe Descriptions", HeadingLevel.HEADING_1),
      para("Layout specifications for each Streamlit page."),
      spacer(),

      heading("10.1 Home / Landing (streamlit_app.py)", HeadingLevel.HEADING_2),
      bulletItem("Top: Title bar with \u201CLittleJoys Persona Simulation Engine\u201D and subtitle"),
      bulletItem("3-column metric row: Total Personas | With Narratives | Business Problems Available"),
      bulletItem("Getting Started section with numbered steps mapping to phases"),
      bulletItem("3 quick-link buttons: Explore Population | State a Problem | View Results"),
      bulletItem("Sidebar: Phase navigation with status indicators (dots/locks)"),
      spacer(),

      heading("10.2 Phase 0: Population Explorer (pages/1_personas.py)", HeadingLevel.HEADING_2),
      bulletItem("Top: Population distribution charts (4 charts in 2\u00D72 grid)"),
      bulletItem("Collapsible filter panel: Income, City Tier, Children, Age Range, Health Score, Free-text"),
      bulletItem("Results count: \u201CShowing 47 of 200 personas\u201D"),
      bulletItem("Persona card grid (2 columns): ID, chips, health bar, narrative preview"),
      bulletItem("Click-to-expand: Full profile with 12 taxonomy sections, memory layer, children cards"),
      bulletItem("System insight cards scattered between persona rows"),
      spacer(),

      heading("10.3 Phase 1: Problem & Simulation (pages/2_problem.py)", HeadingLevel.HEADING_2),
      bulletItem("Top: \u201CWhat business problem are you trying to solve?\u201D"),
      bulletItem("4 business problem cards (from problem_templates.py) + \u201CCustom problem\u201D option"),
      bulletItem("After selection: System narrative explaining what it will simulate"),
      bulletItem("Prominent \u201CRun Baseline Simulation\u201D button"),
      bulletItem("During simulation: Narrative progress panel (monthly updates, not spinner)"),
      bulletItem("After simulation: System narration callout (blue-bordered, insight-first)"),
      bulletItem("Below narration: Cohort distribution chart, 5 cohort summary cards, funnel visualization"),
      bulletItem("Key metrics row: Adoption Rate, Repeat Rate, Avg Purchases/Year, Top Drop-off Reason"),
      spacer(),

      heading("10.4 Phase 2: Decomposition (pages/3_decomposition.py)", HeadingLevel.HEADING_2),
      bulletItem("Top: System-generated hypothesis table with checkboxes (all selected by default)"),
      bulletItem("Each hypothesis row: title, target cohort(s), system rationale, proposed probe chain"),
      bulletItem("\u201CAdd Custom Hypothesis\u201D button (escape hatch, collapsed by default)"),
      bulletItem("\u201CRun Investigation\u201D button to trigger probing tree"),
      bulletItem("Probing tree visualization: grows downward as probes complete at each level"),
      bulletItem("Per-level results: system narration + evidence (attribute charts, interview quotes, lift numbers)"),
      bulletItem("Cross-hypothesis synthesis section at bottom"),
      spacer(),

      heading("10.5 Phase 3: Core Finding & Deep Dives (pages/4_finding.py)", HeadingLevel.HEADING_2),
      bulletItem("Top: Core Issue Statement (orange-bordered callout, full-width, prominent)"),
      bulletItem("Evidence chain below: each probe result linked to the conclusion"),
      bulletItem("Deep-dive section: \u201CInterview a Persona\u201D selector with smart sampling"),
      bulletItem("Interview display: chat-like transcript with persona context sidebar"),
      bulletItem("Pattern analysis: themes, contradictions, quote bank"),
      bulletItem("\u201CGenerate Report\u201D button \u2192 downloadable PDF/DOCX"),
      spacer(),

      heading("10.6 Phase 4: Interventions (pages/5_intervention.py)", HeadingLevel.HEADING_2),
      bulletItem("Top: System-proposed interventions table with rationale tied to Core Finding"),
      bulletItem("Auto-generated alternatives below"),
      bulletItem("User can modify parameters or add custom intervention"),
      bulletItem("\u201CRun All Simulations\u201D button"),
      bulletItem("During simulation: Narrative progress for each counterfactual"),
      bulletItem("After simulation: System narration with recommendation"),
      bulletItem("Comparison table: Baseline vs all interventions"),
      bulletItem("Per-persona movement tracker (clickable cells for drill-down)"),
      bulletItem("System recommendation callout at bottom"),
      spacer(),

      heading("10.7 Comparison Page (pages/6_comparison.py)", HeadingLevel.HEADING_2),
      bulletItem("Side-by-side comparison of any 2 completed problem investigations"),
      bulletItem("Delta metrics highlighted in green (better) or red (worse)"),
      bulletItem("Cohort movement Sankey diagram"),
      bulletItem("Per-persona drill-down: click any persona to see journey in both scenarios"),

      new Paragraph({ children: [new PageBreak()] }),

      // ═════════════════════════════════════════════════════════
      // APPENDIX A — CHANGELOG
      // ═════════════════════════════════════════════════════════
      heading("Appendix A \u2014 Glossary of System Components", HeadingLevel.HEADING_1),
      spacer(),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 6560],
        rows: [
          new TableRow({ children: [headerCell("Term", 2800), headerCell("Definition", 6560)] }),
          new TableRow({ children: [
            cell("System Voice", 2800, { bold: true, fill: C.lightGrey }),
            cell("Blue-bordered narrative callout where the platform communicates insights before showing raw data. Appears after every major computation.", 6560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Magic Moment", 2800, { bold: true }),
            cell("A specific point in the demo flow where the user should feel the system\u2019s intelligence. 5 are defined, each targeting a specific emotional response.", 6560)
          ] }),
          new TableRow({ children: [
            cell("Probing Tree", 2800, { bold: true, fill: C.lightGrey }),
            cell("Sequential, deepening investigation: Level 1 (attribute probe) \u2192 Level 2 (interview probe) \u2192 Level 3 (simulation probe). Based on the 5 Whys method.", 6560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Core Finding", 2800, { bold: true }),
            cell("Single synthesized statement summarizing why the business problem exists, backed by quantified evidence from the probing tree.", 6560)
          ] }),
          new TableRow({ children: [
            cell("Cohort (Behavioral)", 2800, { bold: true, fill: C.lightGrey }),
            cell("Grouping of personas based on ACTUAL simulated behavior over 12 months (not static attributes). 5 cohorts: Never Aware, Aware-Not-Tried, First-Time Buyer, Current User, Lapsed User.", 6560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Problem \u2192 Scenario Mapping", 2800, { bold: true }),
            cell("The system\u2019s automatic translation of a business problem (natural language) to a scenario configuration (product parameters, marketing mix, distribution). The user sees the problem; the system handles the scenario.", 6560)
          ] }),
          new TableRow({ children: [
            cell("Phase Gating", 2800, { bold: true, fill: C.lightGrey }),
            cell("Mandatory progression through 5 phases. Each phase unlocks only when the previous phase\u2019s prerequisite is met. Enforces methodological rigor.", 6560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Auto-Variant", 2800, { bold: true }),
            cell("System-generated intervention variant with business rationale, produced by auto_variants.py. Covers pricing, trust, channel, and messaging dimensions.", 6560)
          ] }),
          new TableRow({ children: [
            cell("Counterfactual Simulation", 2800, { bold: true, fill: C.lightGrey }),
            cell("Re-running the 12-month temporal simulation with a specific modification applied (e.g., add doctor endorsement). Produces lift % vs. baseline.", 6560, { fill: C.lightGrey })
          ] }),
          new TableRow({ children: [
            cell("Semantic Memory", 2800, { bold: true }),
            cell("LLM-generated anchor values, life stories, and biography stored per persona. Provides the depth that makes interviews believable.", 6560)
          ] }),
        ]
      }),

      spacer(), spacer(), divider(),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 },
        children: [new TextRun({ text: "End of User Flow Document v2.0", size: 22, font: "Arial", color: C.grey, italics: true })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: "Simulatte Research Pvt Ltd \u2014 March 2026 \u2014 Confidential", size: 18, font: "Arial", color: C.grey })] }),
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
