# LessonMorph — Document-to-Browser-Lesson Compiler

Turns educational documents (PDF, DOCX, Markdown, Text) into **browser-first classroom lessons** (offline 16:9 scene runtime): 100% source fidelity, teaching flow, visual explanations, state reveals, quizzes, teacher notes, validation. A PPTX exporter is retained downstream of the same IR as a regression reference — not a design target.

Conceptual foundation: [Papermorph](https://github.com/DozenTwelve/Papermorph) (document mapping, chapter decomposition, storyboarding, teaching beats, fidelity, animation-as-explanation, questions, narration guidance, review) — **primary runtime is the browser**. PPTX is an exporter only.

## Install

```bash
pip install -r requirements.txt
cd web && npm install && npm run build   # builds web/dist/runtime.js + styles.css (committed)
```

## Use

```bash
python -m lessonmorph.cli compile source/examples/photosynthesis_and_cellular_energy.md --lesson-dir output/photosynthesis_lesson
python -m lessonmorph.cli compile path/to/chapter.pdf --lesson-dir output/chapter_lesson --no-pptx -w work/chapter
python -m lessonmorph.cli export-pptx path/to/chapter.pdf -o output/chapter.pptx
```

Then open `output/<lesson>/index.html` directly (file:// works, no server, no network).

Output: browser lesson dir + `work/<doc>/{content_ledger, pedagogical_plan_*, blueprint_*, storyboard.json, lesson_qa.md, assets/}` + optional exporter `.pptx`.

## How it works (browser-first)

```
SOURCE → MAP → PRESERVE (ledger C001…) → TEACH (plan of record)
 → BLUEPRINT IR → VISUAL DIRECTOR → MOTION DIRECTOR → LESSON RUNTIME (scenes+states)
 → BROWSER PRESENTATION (1280×720, no scroll) → LESSON QA → DELIVER
                                    ↘ PPTX EXPORTER (regression only)
```

- **Fidelity first**: every meaningful unit mapped; uncovered units FAIL the build.
- **Teacher-first**: scenes follow the pedagogical sequence, never the exporter template.
- **Scenes, not slides**: each scene carries states (e.g. base → revealed → answered); the browser advances state without rebuilding.
- **Clean contracts**: renderer executes IR literally; student bundle carries no source/objective IDs, intents, or teacher guidance (those live in `teacher.json`).
- **Honest failures**: missing tables/figures/formulas reported, never silently dropped.

## Repo layout

See `skill/SKILL.md` for the full skill contract and `docs/` for developer notes (`ARCHITECTURE.md`, `USAGE.md`).

## Testing

```bash
python -m pytest tests/ -q
```

## Papermorph adaptation

| Papermorph | LessonMorph |
|---|---|
| PDF → outline/sections/pages | Same (PyMuPDF TOC + heading fallback + page refs) |
| Chapter map + minutes + concepts | `PedagogicalPlan` per section (plan of record) |
| Storyboard beats + narration triggers | Presentation IR (SlideIR) + locked assessments |
| SVG stage animation | Visual/Motion directors → browser scenes + CSS/Web Animations |
| In-picture quizzes | Choice scenes with locked answers + `answered` state |
| Delivery review pass | Blueprint QA + LessonQA + exporter RenderQA |
| Web book output | Offline browser lesson bundle (primary); PPTX exporter (regression) |

## Limitations

- Browser composition is functional, not a visual redesign (next phase).
- PPTX exporter keeps its own animation/QA stack; PowerPoint is its reference runtime only.
- Scanned-PDF OCR flagged, not auto-transcribed. Unrecreatable figures ship as local assets with attribution.
