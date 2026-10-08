# Usage

## Install

```bash
pip install -r requirements.txt
cd web && npm install && npm run build
```

## Compile a document (browser-first)

```bash
python -m lessonmorph.cli compile <document> [--lesson-dir output/<name>_lesson] [--no-pptx] [-w work/<name>]
```

Supported: `.pdf`, `.docx`/`.doc`, `.md`/`.markdown`/`.txt`.

## Present the lesson

1. Open `output/<name>_lesson/index.html` directly in a browser (file:// works — no server, no internet).
2. Click / Space / ArrowRight to advance (states first, then scenes); ArrowLeft to go back; Home/End to jump; F or the fullscreen button for fullscreen; Esc exits fullscreen.
3. Give 30–45s thinking time on question scenes before advancing to the `answered` state.
4. Teacher metadata lives in `teacher.json` (future presenter mode); the student view never shows it.

## PPTX exporter (regression only)

```bash
python -m lessonmorph.cli export-pptx <document> [-o output/<name>.pptx] [-w work/<name>]
```

The `.pptx` is a regression reference, not the design target. It reads the same IR and never influences scene design.

## Review quality

- `work/<doc>/lesson_qa.md`: LessonQA (schema, student-separation, offline, assets, teacher map). FAIL blocks delivery.
- `work/<doc>/blueprint_qa_*.md`: IR gates. `validation_report.md`: exporter gates.
- `work/<doc>/pedagogical_plan_*.md`: inspect teaching intent before rendering.

## Classroom tips

- Advance state-by-state; ask "what's next?" before clicking.
- The lesson is long by design (fidelity > brevity); skip extension notes if time is short.
