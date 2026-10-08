---
name: lessonmorph
description: Turn educational documents (PDF, DOCX, Markdown, Text) into detailed, classroom-ready PowerPoint presentations (.pptx) with 100% source fidelity, teacher speaker notes, native OpenXML animations, and quality validation.
---

# LessonMorph: Document-to-Teaching-Presentation Compiler

LessonMorph compiles educational documents into editable, classroom-ready Microsoft PowerPoint presentations (`.pptx`).

It behaves like a **best friend for a teacher**:
- **100% Source Content Coverage** via the atomic Content Completeness Ledger.
- **Pedagogical Flow**: Onboarding (Title, Roadmap, Objectives, Prerequisites) → Core Definitions & Formulas → Visual Models → Worked Examples (Stepped Builds) → Common Misconceptions (Tempting Error vs Correct Reasoning) → 2-Stage Classroom Checks → Key Takeaways Summary → Practice & Exit Ticket.
- **Native Editable PowerPoint**: Real shapes, rounded cards, formatted text boxes, native tables, embedded images, typography (never flattened screenshots).
- **Explanation-Driven Animation**: Native OpenXML `<p:timing>` sequences for progressive builds, misconception reveals, answer reveals.
- **Rich Teacher Speaker Notes**: Every slide carries structured guidance (Explanation, Emphasis, Ask Students, Likely Misconception, Transition, Optional Extension).
- **Automated Quality Gates**: Package integrity, 100% coverage, notes presence, density/geometry, animation XML, teaching arc.

## Conceptual foundation (Papermorph adaptation)

Adapted from [Papermorph](https://github.com/DozenTwelve/Papermorph) — reuse its strongest ideas, change the runtime:

**Reuse from Papermorph:**
- Document mapping (outline → sections → pages) before any generation.
- Chapter decomposition with per-chapter scope, minutes, concepts, figures, exercises.
- Storyboarding as the plan of record (beats → slides; narration triggers → speaker notes + animation steps).
- Teaching beats: explain → show → example → misconception → question → recap.
- Content fidelity: re-create explanations/examples/drawings; never silently drop.
- Animation as explanation (visual change teaches), not decoration.
- Embedded questions with answers verified against the storyboard.
- Narration/teacher guidance per beat → speaker notes per slide.
- Systematic delivery review (loading/blanks → package integrity; overlap/cropping → geometry QA; density → text limits; consistency → design system).

**Do NOT carry over:**
- Static web book / SVG-only stage / browser player / localStorage progress / web interactions.
- The runtime is **PowerPoint** (offline `.pptx`, editable objects, native timing).

## Project Structure

```text
LessonMorph/
  lessonmorph/                Python compiler package
    core/                     Data schemas (ContentUnit, SlideSpec, ChapterPlan)
    ingest/                   PDF (PyMuPDF), DOCX, Markdown extractors + ContentAtomizer
    ledger/                   ContentCompletenessLedger (100% coverage tracker)
    pedagogy/                 Domain classifier, planner, misconceptions, pacing
                              (authoritative brain — DO NOT reinterpret downstream)
    blueprint/                Presentation IR: schemas (ir.py), pedagogy→IR adapter,
                              SlideComposer, visual-grammar registry, sanitizer,
                              Blueprint QA validators, render QA, repair loop
    storyboard/               Legacy slide-spec builder (kept for compatibility;
                              new pipeline composes from the Blueprint instead)
    renderer/                 PptxRenderer, DesignSystem, SemanticRenderer
                              (executes IR representations) + legacy visual models
    animation/                OoxmlAnimationEngine (<p:timing> injector) + presets
    quiz/                     QuizEngine (diverse types, 2-stage reveals)
    qa/                       QualityGateValidator + ValidationReport
    cli.py                    compile_document() pipeline + CLI
  skill/
    SKILL.md                  This file
    references/               authoring, ledger, animation, design_system, qa guides
    scripts/                  compile.py helper
  source/examples/            Sample input document(s)
   work/<document>/            content_ledger.*, pedagogical_plan_<chapter>.json/md,
                               blueprint_<chapter>.json, blueprint_qa_<chapter>.md,
                               storyboard.json, document_map.json,
                               assets/, validation_report.md (incl. PEDAGOGICAL QA,
                               BLUEPRINT QA, RENDER QA, repair log)
  output/                     Final .pptx deliverable(s)
  tests/                      Automated suite (ingest, ledger, pedagogy, storyboard,
                              renderer, animation, quiz, qa, blueprint, end-to-end,
                              photosynthesis regression)
```

## Quick Start / CLI Usage

```bash
pip install -r requirements.txt   # python-pptx, pymupdf, python-docx
python -m lessonmorph.cli compile <path/to/document> [-o <path/to/output.pptx>] [-w <path/to/work_dir>]
```

Example:

```bash
python -m lessonmorph.cli compile source/examples/photosynthesis_and_cellular_energy.md -o output/photosynthesis.pptx
```

Multi-chapter documents produce a Contents slide + chapter dividers automatically. Single-chapter decks stay tight (no dividers).

## The Pipeline (do not short-circuit)

```
SOURCE DOCUMENT → CONTENT UNDERSTANDING → EXISTING PEDAGOGICAL MODEL
  → PRESENTATION BLUEPRINT / IR → (Blueprint QA) → SLIDE COMPOSER
  → VISUAL COMPOSER → PPTX GENERATOR → RENDERED SLIDES
  → VISUAL + CONTENT QA → REPAIR / REGENERATE → FINAL PPTX
```

The pedagogical model is the brain, the Blueprint is the execution plan,
the renderer is the executor. The renderer never reinterprets pedagogy.

1. **MAP**: Ingest with page/section fidelity (`document_map.json`). PDFs use bookmarks when present, else heading cues; tables via `find_tables`; images extracted with bytes. DOCX preserves heading hierarchy/tables/lists. Never assume extraction is perfect — record uncertainty.
2. **PRESERVE**: Atomize into `C001…` units (definition, explanation, example, worked_step, exception, diagram, table, formula, warning, exercise, misconception, context, terminology, footnote). Save `content_ledger.json/md`.
3. **PEDAGOGICALLY PLAN**: Build the machine-readable `PedagogicalPlan` per chapter — learner profile, observable objectives (backward design), prerequisites + dependency chains, content-nature profile (conceptual/procedural/factual), adaptive strategy selection (no universal recipe), teaching sequence of instructional states, scaffolding (I DO → WE DO → YOU DO), retrieval/spacing plan, O→Q assessment map, misconceptions, worked examples, pacing. See `references/pedagogy.md`. Save `pedagogical_plan_<chapter>.json/md` and **inspect before rendering**.
4. **BLUEPRINT (Presentation IR)**: The `BlueprintCompiler` (`lessonmorph/blueprint/adapter.py`) translates the authoritative `PedagogicalPlan` into a typed `Blueprint` — every slide carries WHAT (concept/content), WHY (learning_goal/purpose), HOW-encountered (cognitive `task` + `reveal_sequence`), HOW-represented (`representation` from the finite grammar + explicit `visual` spec), HOW-used (`teacher_action`), HOW-checked (locked `assessment`). No slide without `representation` metadata. Content inventory maps every source element to its slide (`Source → Blueprint → Slide`). Save `blueprint_<chapter>.json` and **inspect before rendering**.
5. **BLUEPRINT QA (before PPTX)**: `BlueprintValidator` enforces Content QA (coverage, equations/numbers/questions/answers preserved, no duplication), Pedagogical QA (alignment, sequencing, load, retrieval, worked examples, misconception correction), Representation QA (spatial→diagram, process→flow/pathway, comparison→matrix, quantitative→table, equation→equation object), Assessment QA (options exist, answer locked to a source option, explanation consistent). FAIL refuses to render.
6. **COMPOSE → RENDER**: `SlideComposer` deterministically translates Blueprint → `SlideSpec` (sanitized text, structured payloads, locked answers); `SemanticRenderer` executes the representation with real shapes/connectors/tables — never prose in decorative cards. Equations render from structured terms as clean Unicode notation, never raw LaTeX.
7. **QUESTION (locked)**: SOURCE QUESTION → SOURCE ANSWER → LOCKED ANSWER KEY → ASSESSMENT IR → SLIDE → ANSWER VALIDATOR. Answer slides render FROM the locked object (`<doc>.answer_key.json` pins source answers, e.g. ionophore → B). Source practice problems stay verbatim and task-typed (process/comparison); model-generated retrieval is labeled as such — never silently substituted.
8. **RENDER + REPAIR**: `RenderQA` reopens the PPTX (geometry + text scan; PNG via LibreOffice when available) and flags overflow, off-canvas, orphaned/empty cards, tiny text, duplicates, raw Markdown/LaTeX, broken symbols, wrong answers. `repair_blueprint` regenerates AFFECTED slides only (representation fallback or density split), then re-renders and re-inspects (max 2 rounds). Unfixable errors escalate for human review.
7. **RENDER**: Editable pptx (16:9), design system, alt text, embedded assets. No flattened-image slides.
8. **ANIMATE**: Native `<p:timing>` on real shape IDs (step builds, cross-outs, answer reveals). No decorative motion.
9. **VALIDATE**: `validation_report.md` with Content/Structural/Visual/Teaching gates **plus BLUEPRINT QA and RENDER QA sections**. FAIL on uncovered units, corrupt package, unlocked answers, or unpreserved source elements; WARN + human-review flags otherwise.
10. **DELIVER**: `.pptx` + work artifacts. Report warnings honestly (missing table → "Table on page X requires review", unrecreatable figure → "preserved as image", unparsable formula → "C104 could not be represented natively").

## Core Principles

1. **Fidelity Before Aesthetics**: Never drop definitions, formulas, exceptions, steps, tables, figures, qualifications, terminology, warnings, exercises, footnotes, or relationships to hit a slide count. Long chapters legitimately produce long decks.
2. **Animation Must Explain**: Motion = process, build-up, transformation, reveal-after-thinking, cross-out, sequence. No random bounce/zoom/spin.
3. **Editable PowerPoint Objects**: Text boxes, shapes, tables, diagrams, images, notes — teacher-editable.
4. **Offline Usability**: Zero browser/network/hosted-asset dependence at presentation time.
5. **No Silent Loss**: Extraction/render failures are reported, never hidden. Source errors get `SOURCE: … / SYSTEM NOTE: potential inconsistency` treatment, never quiet rewrites.

## Content Completeness Ledger (mandatory)

See `references/ledger.md`. Every unit: unique ID, source location, chapter/section, type, importance, normalized content, original wording, relationships, intended destination, coverage status. Validation must be able to print `COVERED: N / UNCOVERED: 0`. Do not fake coverage.

## Teaching Flow & Subject Strategies

Follow `references/authoring.md` for slide craft and `references/pedagogy.md` for the intelligence layer (constitution, decision principles, no-recipe rule, evidence discipline). Do not force one template on every subject; choose per §6 of the product spec (concept/process/comparison/classification/timeline/cause-effect/formula/numerical/science/history/geography/biology/chemistry/physics/math/social-science/literature/language). Decorative visuals are prohibited where a real diagram would teach. Every animation stores its instructional `purpose`; every quiz maps to objectives (`objective_ids`).

## Quiz, Notes, Pacing, Design, Accessibility

- Quiz: `references/authoring.md` §9 + quiz engine; store Q-ID, concepts, difficulty, answer, explanation, distractor rationales, slide locations.
- Notes: six-part structure on substantial slides; teach, don't duplicate slide text.
- Pacing: content determines length; report per-chapter minutes.
- Design: `references/design_system.md` — projector contrast, large type, semantic color (mistake=rose, correct=emerald, accent=sky, stable per concept).
- Accessibility: contrast, no color-only meaning, readable sizes, logical order, alt text, titles, print/reduced-motion legibility.
- Math/science: preserve fractions, powers, sub/superscripts, roots, Greek, units, arrows; exact values; no rounding corruption.

## Quality Gates & Human Review

See `references/qa.md`. Distinguish AUTOMATICALLY VERIFIED vs REQUIRES HUMAN REVIEW (ambiguous OCR, poor diagrams, uncertain equations, source inconsistencies, dense layouts). Render-and-inspect: generate → reopen → render/inspect → repair → re-validate; never trust geometry blindly.

## Presentation Modes (architecture-ready)

Keep `TEACH / REVISION / EXAM / TEACHER` modes possible (slide_type + storyboard filters already separate content from rendering). Do not build all modes in v1.

## What to deliver for a new document

1. `.pptx` in `output/`
2. `work/<doc>/{content_ledger.json, content_ledger.md, storyboard.json, document_map.json, assets/, validation_report.md}`
3. Console summary: units covered, slides, minutes, PASS/WARN/FAIL + warnings.

## Limitations (v1, honest)

- Animation = on-click entrance/emphasis reveals via `<p:timing>`; no motion paths or triggers; LibreOffice may render timing subset differently — PowerPoint is the reference runtime.
- Visual QA is heuristic (density + bounds overlap + off-canvas); full pixel render inspection (e.g., via LibreOffice PDF export) is a recommended manual step for high-stakes decks — see `references/qa.md`.
- OCR for scanned PDFs is detected/flagged, not auto-transcribed; re-extract with a text layer or DOCX when possible.
- Image-heavy figures are embedded as images with labeled walkthrough cards when native recreation is unreliable (reported, not hidden).
