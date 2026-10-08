# Student-First Browser Design System

Audience is always students. The lesson must feel like modern science
education + interactive visual storytelling + professionally designed
presentation — never a dashboard, worksheet, report, or document viewer.

## Tokens (single source of truth)

`web/src/tokens.ts` ↔ `:root` in `web/src/styles.css` (same names, same
numbers). Nothing else hardcodes sizes, colors, spacing, or motion.

- Canvas 1280×720, safe margin 64, 8px grid; spacing xs→xxxl + gutter/section gaps.
- Type: display 76 / hero 56 / title 44 / subtitle 22 / body 21 / body-large 24 /
  label 13 / caption 15 / question 32 / answer 22 / equation 64 / data 18.
- Semantic color: ink/soft/faint, paper/warm/dark, accent, success, danger, warn
  (+washes), hairline. One stage shadow only — no per-card shadows.
- Motion: fast 220 / base 250 / slow 350ms, ease-out; `prefers-reduced-motion`
  disables transitions (content stays visible).

## Viewport

Fixed logical canvas scaled by `viewport.ts` (proportional, letterboxed,
centered). `overflow:hidden` on viewport, stage, scene, and table wraps —
no scrolling, no document flow, no distortion. Fullscreen via chrome button.

## Composition families (17)

| Family | Serves (IR reps) | Spatial logic |
|---|---|---|
| cinematic_hook | title | bottom-anchored monument on dark field |
| hero_concept | definition/big_idea/concept/key_principle/objectives | term as architecture, whitespace-led |
| full_visual | cutaway/spatial | image-led bleed, text recedes to rail |
| split_visual | anatomy_map | two-pane editorial spread, flippable |
| diagram_centered | labeled_diagram | radial hub, labels orbit |
| process_pathway | flow/sequence/pathway | numbered horizontal journey or vertical rail |
| cycle | cycle | hub + ring, or grid |
| comparison | cause_effect/before_after/matrix | A vs B across a versus gutter |
| equation_focus | equation/worked_calc | monument math on open field |
| data_visualization | tables/charts | reading-scale table, ink header |
| question_focus | mcq/true-false/prediction/diagnostic/retrieval | the question owns the room |
| answer_reveal | merged Q&A pairs | verdict banner, rest recedes |
| misconception | contrast | myth struck, correction lit (correction gets room) |
| practice_workspace | practice_problem | prompt + calm ruled room |
| concept_map | hierarchy/concept_map | hub + satellite lanes |
| synthesis | roadmap/summary/big_picture | takeaway band, first idea leads |
| reflection | exit | two quiet prompts |

Geometry lives in `VisualDirector.family_regions()` (logical px, canvas-safe);
emphasis lives in `styles.css` (`fam-*` blocks). TS components in `render.ts`
(`renderFamily` → 17 stagings) consume scene data only — no hardcoded content.

## Focal point & restraint

One dominant element per scene (giant equation, diagram, photo, question,
pathway, chart). Metadata (kicker, lesson tag, progress) stays small.
Cards are not the default: layers are transparent; only answer banners,
choice controls, and the correction panel use bordered surfaces.
No decorative gradients, badges, or random illustration.

## Variety (deterministic)

`select_variant()` rotates within a family by prior-use count (dense content
offsets to airier variants). `build_scenes` tracks the last 6 families.
Consecutive same-family scenes always differ in arrangement. No `random`
anywhere in this path (tested).

## Readability

Body ≥21px, questions ≥32px, equations ≥64px; high-contrast ink on paper;
short on-screen text; large diagrams. Dense sources split upstream —
never shrink-to-fit.

## Files

- `web/src/tokens.ts`, `web/src/compositions.ts` (family→component dispatch),
  `web/src/render.ts` (17 components), `web/src/styles.css`, `web/src/motion.ts`,
  `web/src/store.ts`, `web/src/viewport.ts`, `web/src/nav.ts`
- `lessonmorph/runtime/visual_director.py` (families, regions, variety),
  `lessonmorph/runtime/bundle.py` (recent-history tracking, pair→answer_reveal)
- `tests/test_browser_design_system.py` (9 contract tests)

## Visualization engines (`web/src/engines.ts`)

Pure string builders (no DOM) executed by the components above; content type
determines form. Test harness: `web/build/engines.test.cjs` (30 assertions).

- Diagram: membrane bands, disc stacks, fluid compartments from label
  semantics; every label bound to a region id with leader lines, numbered
  markers, legend, and per-state reveal emphasis.
- Process: numbered node chains with directional arrows (never paragraphs);
  feedback rails, branched lanes, and cause→mechanism→effect lanes.
- Cycle: node ring with directed arcs and current-stage emphasis.
- Comparison: symmetric matrices with computed difference/shared highlighting;
  misconceptions stage as wrong (struck) vs correct (lit) models.
- Equation: coefficients, sub/superscripts, fractions, arrows, energy badges,
  numbered annotation legends. Raw LaTeX/Markdown never renders.
- Data: intent chooser — wavelength columns → spectrum, bar/line reps →
  bars/line, x/y pairs → scatter, else table; figures keep the full source
  table beneath (same values, nothing invented).
- Concept maps: hub + satellites; edge style from the cognitive task
  (sequence/causal/dependency/plain), never invented verbs.
- Images: hero/bleed/split/annotated/inset/overlay layouts driven by assets +
  caption purpose; empty assets render nothing.
## Motion, interaction, visual QA (see code for full contracts)

- Motion: `lessonmorph/runtime/motion_director.py` (12 primitives, timing
  tokens fast 180 / normal 250 / slow 400 / process 600ms, every step carries
  WHY + targets, path journeys bound to IR label waypoints) executes in
  `web/src/motion.ts` (WAAPI, reduced-motion inert, marker + live-caption
  path player, misconception strike, answer evidence, option stagger).
- Interaction: think cue before commitment, locked-answer reveal, structured
  practice workspaces, Space/Right next, Left back, Enter confirm, Esc native,
  click/tap, subtle progress + fullscreen, graceful image/motion fallbacks.
- Visual QA: `lessonmorph/qa/visual.py` (static) + `shots.py` (Playwright
  screenshots of initial/mid/final/answered states + pixel checks) +
  `visual_repair.py` (roomiest-variant restage) + `visual_gate.py`
  (static FAIL blocks; rendered FAIL blocks; SKIP only without a browser;
  photosynthesis regression benchmark). Run:
  `python -m lessonmorph.cli visual-qa output/<lesson> -w work/<doc>`.
- PPTX stays secondary: `lessonmorph/renderer/pptx_exporter.py` consumes the
  same IR; neither direction imports the other (tested).
