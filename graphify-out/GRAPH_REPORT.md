# Graph Report - .  (2026-04-27)

## Corpus Check
- Corpus is ~3,209 words - fits in a single context window. You may not need a graph.

## Summary
- 72 nodes · 96 edges · 9 communities detected
- Extraction: 86% EXTRACTED · 11% INFERRED · 2% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.84)
- Token cost: 10,800 input · 3,600 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Icon Design System|Icon Design System]]
- [[_COMMUNITY_Brand Visual Assets|Brand Visual Assets]]
- [[_COMMUNITY_Favicon Color Palette|Favicon Color Palette]]
- [[_COMMUNITY_Sales Workflow Backend|Sales Workflow Backend]]
- [[_COMMUNITY_React + Vite FE Setup|React + Vite FE Setup]]
- [[_COMMUNITY_Data & Intelligence Layer|Data & Intelligence Layer]]
- [[_COMMUNITY_Outreach Email Sequences|Outreach Email Sequences]]
- [[_COMMUNITY_AI Negotiation & Human Loop|AI Negotiation & Human Loop]]
- [[_COMMUNITY_Sales Data Intake|Sales Data Intake]]

## God Nodes (most connected - your core abstractions)
1. `SalesCatalyst - Sales Automation System` - 21 edges
2. `Favicon SVG - Lightning Bolt Icon` - 8 edges
3. `SVG Icon Sprite File` - 7 edges
4. `FE Entry Point - index.html` - 5 edges
5. `FE README - React + Vite Setup` - 5 edges
6. `Design Color: Dark (#08060d)` - 5 edges
7. `Design Style: Filled / Solid Icons` - 5 edges
8. `Introductory Email / Brochure Send Step` - 4 edges
9. `Data Collection & Maintenance Store` - 4 edges
10. `Bluesky Social Icon` - 4 edges

## Surprising Connections (you probably didn't know these)
- `Backend Sample File` --conceptually_related_to--> `SalesCatalyst - Sales Automation System`  [AMBIGUOUS]
  BE/sample.txt → SalesCatalyst.md
- `SalesCatalyst - Sales Automation System` --conceptually_related_to--> `FE Entry Point - index.html`  [INFERRED]
  SalesCatalyst.md → FE/index.html
- `UI Dashboard - Product Entry Interface` --conceptually_related_to--> `FE Entry Point - index.html`  [INFERRED]
  SalesCatalyst.md → FE/index.html
- `Favicon SVG - Lightning Bolt Icon` --represents_brand_of--> `Team TradeCatalysts Project`  [EXTRACTED]
  FE/public/favicon.svg → .
- `Lightning Bolt / Downward Arrow Shape` --symbolizes--> `Team TradeCatalysts Project`  [EXTRACTED]
  FE/public/favicon.svg → .

## Communities

### Community 0 - "Icon Design System"
Cohesion: 0.3
Nodes (14): Design Color: Dark (#08060d), Design Color: Purple (#aa3bff), Design Style: Filled / Solid Icons, Design Style: Outlined / Stroke Icons, Frontend Public Assets Directory, Bluesky Social Icon, Discord Icon, Documentation Icon (+6 more)

### Community 1 - "Brand Visual Assets"
Cohesion: 0.25
Nodes (11): Frontend Assets Directory, Frontend Project, Isometric Illustration Style, Layered Card / Platform Stack Visual, Hero Image (hero.png), Purple / Violet Brand Accent Color, Iconify Logos Icon Set, React JavaScript Framework (+3 more)

### Community 2 - "Favicon Color Palette"
Cohesion: 0.27
Nodes (10): Cyan Blue Accent Color (#47bfff), Light Lavender Color (#ede6ff), Dark Purple Color (#7e14ff), Primary Purple Color (#863bff), Gaussian Blur Glow Visual Effect, Favicon SVG - Lightning Bolt Icon, Frontend Application (FE), Frontend Public Assets Directory (+2 more)

### Community 3 - "Sales Workflow Backend"
Cohesion: 0.25
Nodes (9): Backend Sample File, Adhoc: Returning Customer - Skip Intro, Send Pricing Directly, Deal Close Marking - Success/Failure with Remarks, Visual Flow Chart Representation of Journey, Google Calendar - Meeting Setup & Reminder, HubSpot Integration - Prior Contact Check, Objective: Help Sales Person Complete Sale Process, Pricing Follow-up Step (+1 more)

### Community 4 - "React + Vite FE Setup"
Cohesion: 0.22
Nodes (9): FE Entry Point - index.html, Main JSX Entry Script (src/main.jsx), React Root Mount Point (#root div), FE README - React + Vite Setup, @vitejs/plugin-react (uses Oxc), @vitejs/plugin-react-swc (uses SWC), Rationale: React Compiler Disabled Due to Dev/Build Performance Impact, React Compiler (disabled by default) (+1 more)

### Community 5 - "Data & Intelligence Layer"
Cohesion: 0.5
Nodes (4): Data Collection & Maintenance Store, Gong/Sybill Integration, LinkedIn & LUSHA - Contact Discovery, Real-Time Sales Analyst AI - Meeting Integration

### Community 6 - "Outreach Email Sequences"
Cohesion: 0.5
Nodes (4): Introductory Email / Brochure Send Step, Personalised Call - Contact Only Scenario, 2nd Email with Pricing & Deadline, Spreadsheet Fallback - No Email/Contact Scenario

### Community 7 - "AI Negotiation & Human Loop"
Cohesion: 0.5
Nodes (4): AI Negotiation Handler - Requires Internal Team Approval, Internal Team Member (Sales Person / Actor), Manual Interference Option for Internal Team Member, Rationale: Human-in-the-Loop for AI Negotiation Responses

### Community 9 - "Sales Data Intake"
Cohesion: 1.0
Nodes (2): UI Dashboard - Product Entry Interface, Volza API - Customer & Purchase History Data

## Ambiguous Edges - Review These
- `SalesCatalyst - Sales Automation System` → `Backend Sample File`  [AMBIGUOUS]
  BE/sample.txt · relation: conceptually_related_to
- `Social / User-with-Star Rating Icon` → `Social Media Platforms`  [AMBIGUOUS]
  FE/public/icons.svg · relation: conceptually_related_to

## Knowledge Gaps
- **18 isolated node(s):** `Objective: Help Sales Person Complete Sale Process`, `Pricing Follow-up Step`, `Google Calendar - Meeting Setup & Reminder`, `Deal Close Marking - Success/Failure with Remarks`, `Visual Flow Chart Representation of Journey` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Sales Data Intake`** (2 nodes): `UI Dashboard - Product Entry Interface`, `Volza API - Customer & Purchase History Data`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `SalesCatalyst - Sales Automation System` and `Backend Sample File`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Social / User-with-Star Rating Icon` and `Social Media Platforms`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `SalesCatalyst - Sales Automation System` connect `Sales Workflow Backend` to `React + Vite FE Setup`, `Data & Intelligence Layer`, `Outreach Email Sequences`, `AI Negotiation & Human Loop`, `Sales Data Intake`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `FE Entry Point - index.html` connect `React + Vite FE Setup` to `Sales Data Intake`, `Sales Workflow Backend`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `FE Entry Point - index.html` (e.g. with `SalesCatalyst - Sales Automation System` and `FE README - React + Vite Setup`) actually correct?**
  _`FE Entry Point - index.html` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Objective: Help Sales Person Complete Sale Process`, `Pricing Follow-up Step`, `Google Calendar - Meeting Setup & Reminder` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._