# LessonMorph — Document-to-Teaching-Presentation Compiler

Turns educational documents (PDF, DOCX, Markdown, Text) into **detailed, classroom-ready PowerPoint (`.pptx`)** decks: 100% source fidelity, teaching flow, visual explanations, progressive animation, quizzes, speaker notes, validation.

Conceptual foundation: [Papermorph](https://github.com/DozenTwelve/Papermorph) (document mapping, chapter decomposition, storyboarding, teaching beats, fidelity, animation-as-explanation, questions, narration guidance, review) — **runtime replaced with PowerPoint**. No web-book/SVG/browser output.

## Install

```bash
pip install python-pptx pymupdf python-docx pytest
```

## Use

```bash
python -m lessonmorph.cli compile source/examples/photosynthesis_and_cellular_energy.md -o output/photosynthesis.pptx
python -m lessonmorph.cli compile path/to/chapter.pdf -o output/chapter.pptx -w work/chapter
```

Or via helper:

```bash
python skill/scripts/compile.py source/examples/photosynthesis_and_cellular_energy.md -o output/photosynthesis.pptx
```

Output: `.pptx` + `work/<doc>/{content_ledger.json, content_ledger.md, storyboard.json, document_map.json, assets/, validation_report.md}`.

## How it works

```
SOURCE → MAP → PRESERVE (ledger C001…) → TEACH (objectives, misconceptions, pacing)
 → STORYBOARD → VISUALIZE (subject-aware models) → QUESTION (2-stage checks)
 → RENDER (editable pptx) → ANIMATE (<p:timing>) → VALIDATE → DELIVER
```

- **Fidelity first**: every meaningful unit mapped; uncovered units FAIL the build.
- **Teacher-first**: title → why-it-matters → objectives → warm-up → definitions → visuals → worked examples → misconceptions → checks → summary → practice → exit ticket (adapted per subject).
- **Real PowerPoint**: shapes, tables, embedded images, notes, native timing XML. Offline. Editable.
- **Honest failures**: missing tables/figures/formulas reported in `validation_report.md` + `asset_warnings.md`, never silently dropped.

## Repo layout

See `skill/SKILL.md` for the full skill contract and `docs/` for developer notes.

## Testing

```bash
python -m pytest tests/ -q
```

## Papermorph adaptation

| Papermorph | LessonMorph |
|---|---|
| PDF → outline/sections/pages | Same (PyMuPDF TOC + heading fallback + page refs) |
| Chapter map + minutes + concepts | `ChapterPlan` per section |
| Storyboard beats + narration triggers | `SlideSpec` + animation steps + speaker notes |
| SVG stage animation | Native `<p:timing>` on shape IDs |
| In-picture quizzes | 2-slide Question → Answer+Explanation |
| Delivery review pass | 4 quality gates + validation report |
| Web book output | Editable offline `.pptx` |

## Limitations (v1)

- On-click reveals only; no motion paths/triggers. PowerPoint is the reference runtime.
- Visual QA is heuristic; manual PDF-export inspection recommended for high-stakes decks.
- Scanned-PDF OCR flagged, not auto-transcribed. Unrecreatable figures embedded as images with attribution.
