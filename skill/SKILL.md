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
    storyboard/               StoryboardEngine (slide specs, visual models, quiz placement)
    renderer/                 PptxRenderer, DesignSystem, shape + visual-model builders
    animation/                OoxmlAnimationEngine (<p:timing> injector) + presets
    quiz/                     QuizEngine (diverse types, 2-stage reveals)
    qa/                       QualityGateValidator + ValidationReport
    cli.py                    compile_document() pipeline + CLI
  skill/
    SKILL.md                  This file
    references/               authoring, ledger, animation, design_system, qa guides
    scripts/                  compile.py helper
  source/examples/            Sample input document(s)
  work/<document>/            content_ledger.*, storyboard.json, document_map.json,
                              assets/, validation_report.md
  output/                     Final .pptx deliverable(s)
  tests/                      Automated suite (ingest, ledger, pedagogy, storyboard,
                              renderer, animation, quiz, qa, end-to-end)
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
SOURCE → UNDERSTAND → MAP → PRESERVE → TEACH → STORYBOARD
  → VISUALIZE → QUESTION → RENDER → ANIMATE → VALIDATE → DELIVER PPTX
```

1. **MAP**: Ingest with page/section fidelity (`document_map.json`). PDFs use bookmarks when present, else heading cues; tables via `find_tables`; images extracted with bytes. DOCX preserves heading hierarchy/tables/lists. Never assume extraction is perfect — record uncertainty.
2. **PRESERVE**: Atomize into `C001…` units (definition, explanation, example, worked_step, exception, diagram, table, formula, warning, exercise, misconception, context, terminology, footnote). Save `content_ledger.json/md`.
3. **TEACH**: Classify domain (math/physics/chemistry/biology/history/geography/…), plan objectives, prerequisites, core concepts, misconceptions, questions, pacing. One plan per chapter.
4. **STORYBOARD**: Emit `storyboard.json` — every slide has `slide_id, chapter_id, title, purpose, source_content_ids[], slide_type, visual_model, objects, animation_sequence, quiz, speaker_notes, estimated_time, source_references`. Inspect the plan before rendering.
5. **VISUALIZE**: Subject-aware models — concept→diagram+example, process→sequential build, comparison→side-by-side, classification→grid, timeline→chronology, formula→breakdown→worked example. Recreate diagrams as editable shapes; embed source figures with attribution; decompose into animated stages where it teaches.
6. **QUESTION**: Only quiz taught material. Vary form (MCQ, true/false, fill-blank, matching, sequence, classification, identify-error, calculation, assertion/reason, short answer, exam-style) and difficulty (recall→evaluation). Two-slide pattern: A=question only, B=answer+explanation.
7. **RENDER**: Editable pptx (16:9), design system, alt text, embedded assets. No flattened-image slides.
8. **ANIMATE**: Native `<p:timing>` on real shape IDs (step builds, cross-outs, answer reveals). No decorative motion.
9. **VALIDATE**: `validation_report.md` with Content/Structural/Visual/Teaching gates. FAIL on uncovered units or corrupt package; WARN + human-review flags otherwise.
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

Follow `references/authoring.md`. Do not force one template on every subject; choose per §6 of the product spec (concept/process/comparison/classification/timeline/cause-effect/formula/numerical/science/history/geography/biology/chemistry/physics/math/social-science/literature/language). Decorative visuals are prohibited where a real diagram would teach.

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
