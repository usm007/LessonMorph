---
name: lessonmorph
description: Turn educational documents (PDF, DOCX, Markdown, Text) into browser-first classroom lessons (offline 16:9 scene runtime) with 100% source fidelity, teacher notes, and quality validation. PPTX exporter retained as regression reference.
---

# LessonMorph: Document-to-Browser-Lesson Compiler

LessonMorph compiles educational documents into browser-first classroom lessons
(offline single-viewport scene runtime). A PPTX exporter is retained downstream
of the same Presentation IR as a regression reference — it is not the design target.

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
- PPTX-as-primary thinking. The primary runtime is the **browser lesson**
  (1280×720 single viewport, scenes + states, offline bundle). PPTX is a
  downstream exporter only (`PRESENTATION IR → PPTX EXPORTER`).

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
    renderer/                 PPTX EXPORTER (downstream only): pptx_exporter.py +
                              PptxRenderer, DesignSystem, SemanticRenderer
                              (executes IR representations) + legacy visual models.
                              Never imported by the browser path.
    runtime/                  PRIMARY path: lesson_model.py (Scene/state),
                              visual_director.py, motion_director.py,
                              pipeline.py (IR -> Lesson), bundle.py (offline
                              lesson dir), lesson_qa.py (LessonQA gates)
    animation/                PPTX exporter animation (<p:timing> injector) + presets
    web/                      Browser presentation runtime (TypeScript, zero
                              runtime deps): 1280×720 viewport scaler,
                              deterministic store, scene renderer, motion,
                              keyboard/mouse/fullscreen nav, progress chrome
  skill/
    SKILL.md                  This file
    references/               authoring, ledger, animation, design_system, qa, pedagogy guides
    scripts/                  compile.py helper (browser-first)
  source/examples/            Sample input document(s)
   work/<document>/            content_ledger.*, pedagogical_plan_<chapter>.json/md,
                               blueprint_<chapter>.json, blueprint_qa_<chapter>.md,
                               storyboard.json, document_map.json, lesson_qa.md,
                               assets/, validation_report.md (exporter QA)
  output/                     PRIMARY: output/<doc>_lesson/ (index.html + runtime.js +
                              styles.css + lesson.json + teacher.json + assets/).
                              Exporter: output/<doc>.pptx (regression reference only)
  tests/                      Automated suite (ingest, ledger, pedagogy, storyboard,
                              renderer, animation, quiz, qa, blueprint, browser_runtime,
                              end-to-end, photosynthesis regression)
    quiz/                     QuizEngine (diverse types, locked answers)
    qa/                       QualityGateValidator (exporter) + ValidationReport
    cli.py                    compile_lesson() primary + compile_document() compat + CLI
```

## Quick Start / CLI Usage

```bash
pip install -r requirements.txt   # python-pptx, pymupdf, python-docx
# Primary: browser lesson bundle
python -m lessonmorph.cli compile <path/to/document> [--lesson-dir output/<doc>_lesson] [--no-pptx]
# PPTX exporter (regression reference only)
python -m lessonmorph.cli export-pptx <path/to/document> [-o output/<doc>.pptx]
```

Example:

```bash
python -m lessonmorph.cli compile source/examples/photosynthesis_and_cellular_energy.md --lesson-dir output/photosynthesis_lesson
# open output/photosynthesis_lesson/index.html (file:// works, no server needed)
```

Then build the web runtime once (committed under `web/dist/`; rebuild after TS changes):

```bash
cd web && npm install && npm run build
```

Quality-gate the rendered lesson (static QA runs at every compile; screenshots + repair on demand):

```bash
python -m lessonmorph.cli visual-qa output/<doc>_lesson -w work/<doc>
```

Multi-chapter documents produce a Contents slide + chapter dividers automatically. Single-chapter decks stay tight (no dividers).

## The Pipeline (do not short-circuit)

PRIMARY (browser):

```
SOURCE DOCUMENT → CONTENT UNDERSTANDING → EXISTING PEDAGOGICAL MODEL
  → PRESENTATION BLUEPRINT / IR → VISUAL DIRECTOR → MOTION DIRECTOR
  → LESSON RUNTIME MODEL → BROWSER PRESENTATION → DESIGN + VISUAL QA
```

EXPORTER (regression only, never upstream of design):

```
PRESENTATION IR → PPTX EXPORTER → .pptx
```

The pedagogical model is the brain, the Blueprint is the execution plan.
Directors and renderers execute it literally and never reinterpret pedagogy.

1. **MAP**: Ingest with page/section fidelity (`document_map.json`). PDFs use bookmarks when present, else heading cues; tables via `find_tables`; images extracted with bytes. DOCX preserves heading hierarchy/tables/lists. Never assume extraction is perfect — record uncertainty.
2. **PRESERVE**: Atomize into `C001…` units (definition, explanation, example, worked_step, exception, diagram, table, formula, warning, exercise, misconception, context, terminology, footnote). Save `content_ledger.json/md`.
3. **PEDAGOGICALLY PLAN**: Build the machine-readable `PedagogicalPlan` per chapter — learner profile, observable objectives (backward design), prerequisites + dependency chains, content-nature profile (conceptual/procedural/factual), adaptive strategy selection (no universal recipe), teaching sequence of instructional states, scaffolding (I DO → WE DO → YOU DO), retrieval/spacing plan, O→Q assessment map, misconceptions, worked examples, pacing. See `references/pedagogy.md`. Save `pedagogical_plan_<chapter>.json/md` and **inspect before rendering**.
4. **BLUEPRINT (Presentation IR)**: The `BlueprintCompiler` (`lessonmorph/blueprint/adapter.py`) translates the authoritative `PedagogicalPlan` into a typed `Blueprint` — every slide carries WHAT (concept/content), WHY (learning_goal/purpose), HOW-encountered (cognitive `task` + `reveal_sequence`), HOW-represented (`representation` from the finite grammar + explicit `visual` spec), HOW-used (`teacher_action`), HOW-checked (locked `assessment`). No slide without `representation` metadata. Content inventory maps every source element to its slide (`Source → Blueprint → Slide`). Save `blueprint_<chapter>.json` and **inspect before rendering**.
5. **BLUEPRINT QA (before PPTX)**: `BlueprintValidator` enforces Content QA (coverage, equations/numbers/questions/answers preserved, no duplication), Pedagogical QA (alignment, sequencing, load, retrieval, worked examples, misconception correction), Representation QA (spatial→diagram, process→flow/pathway, comparison→matrix, quantitative→table, equation→equation object), Assessment QA (options exist, answer locked to a source option, explanation consistent). FAIL refuses to render.
6. **DIRECT (Visual + Motion)**: `VisualDirector` maps each SlideIR representation to layers/regions/states on the 1280×720 canvas (safe area, no scroll); `MotionDirector` maps reveal intent to browser motion primitives (fade/wipe/slide/highlight/emphasis/reveal, calm fade transitions). No pedagogy here, no content extraction, no reinterpretation.
7. **LESSON RUNTIME MODEL**: `pipeline.compile_lesson_from_ir()` assembles student `Scene` objects (scene_id, representation, task, states, layers, content, visual, assets, interaction with LOCKED answers, motion) plus separate `TeacherScene` records (purpose, instructional_state, learning_goal, teacher_notes/prompts, source_ids traceability, objective_ids, concept_id). Prompt/reveal pairs merge into one scene with an `answered` state. The browser moves between states without rebuilding the app.
8. **BROWSER PRESENTATION**: `bundle.write_bundle()` writes the offline lesson dir (`index.html` with inlined lesson JSON — file:// safe, `runtime.js`, `styles.css`, `lesson.json`, `teacher.json`, `assets/`). The TS runtime (`web/src`) executes scenes only: 16:9 letterboxed viewport, one scene per viewport, no scrolling, next/previous/first/last, ArrowRight/Space → next, ArrowLeft → previous, Home/End → ends, Escape exits fullscreen natively, click/tap progression, progress indicator, fullscreen mode. Student view exposes no raw JSON, source IDs, objective IDs, metadata, or debug controls.
9. **DESIGN + VISUAL QA (LessonQA)**: schema (canvas 1280×720, states/layers/motion, locked choice answers), student-separation (no internal fields in `lesson.json`), offline (no remote refs/fetch, all assets local), teacher 1:1 scene mapping. FAIL blocks delivery. See `lessonmorph/runtime/lesson_qa.py`.
10. **PPTX EXPORTER (regression only)**: `renderer/pptx_exporter.py` reads the same IR (`SlideComposer` → `PptxRenderer` → `RenderQA` + targeted repair → `QualityGateValidator`). The current photosynthesis PPTX is a regression reference, not a design target.
11. **DELIVER**: browser lesson dir + `work/<doc>/` artifacts (`lesson_qa.md`, ledger, plans, blueprints, storyboard) + optional exporter `.pptx`. Report warnings honestly.

## Core Principles

1. **Fidelity Before Aesthetics**: Never drop definitions, formulas, exceptions, steps, tables, figures, qualifications, terminology, warnings, exercises, footnotes, or relationships to hit a scene count. Long chapters legitimately produce long lessons.
2. **Animation Must Explain**: Motion = process, build-up, transformation, reveal-after-thinking, cross-out, sequence. Browser effects stay calm (fade/wipe/slide/highlight/emphasis/reveal). No random bounce/zoom/spin.
3. **Scenes, Not Slides**: Think "learning scenes in a browser viewport" (semantic content + composition + interaction + states), never "PowerPoint slides". The PPTX exporter must not shape scene design.
4. **Offline Usability**: Zero network dependence at presentation time — browser bundle and PPTX both run local-only.
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

1. Browser lesson dir in `output/<doc>_lesson/` (`index.html`, `runtime.js`, `styles.css`, `lesson.json`, `teacher.json`, `assets/`)
2. `work/<doc>/{content_ledger.json, content_ledger.md, pedagogical_plan_*.json/md, blueprint_*.json, blueprint_qa_*.md, storyboard.json, document_map.json, assets/, lesson_qa.md}`
3. Optional exporter `.pptx` (regression reference) + `validation_report.md`
4. Console summary: scenes, LessonQA status, exporter status + warnings.

## Limitations (honest)

- Browser motion is calm by design (no motion paths); scene composition is functional, not a visual redesign — that is the next phase.
- PPTX exporter keeps its own animation/QA stack (`<p:timing>`, RenderQA); PowerPoint remains its reference runtime, the browser does not depend on it.
- Visual QA for the browser is structural (LessonQA + bounds); pixel-perfect review happens in the next phase.
- OCR for scanned PDFs is detected/flagged, not auto-transcribed; re-extract with a text layer or DOCX when possible.
- Image-heavy figures ship as local bundle assets with labeled walkthroughs when native recreation is unreliable (reported, not hidden).
