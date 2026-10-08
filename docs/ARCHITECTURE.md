# Developer notes

## Architecture (teaching model first, renderer second)

- **Content layer** (`ingest/`, `ledger/`): extraction → normalization → atoms (`C001…`) → coverage. No pedagogy here.
- **Teaching layer** (`pedagogy/`): domain classification, objectives, prerequisites, misconceptions, questions, pacing. Pure data (`ChapterPlan`), no pptx.
- **Storyboard layer** (`storyboard/`): `SlideSpec` list — slide types, visual models, animation plan, quiz placement, notes, source mapping. Inspectable via `storyboard.json` before rendering.
- **Rendering layer** (`renderer/`): `SlideSpec` → editable pptx (16:9, design tokens, shapes/tables/images/notes/alt text). Dispatch per `visual_model`; unknown models fall back to `definition_card` (never crash).
- **Animation layer** (`animation/`): isolated `<p:timing>` injector on real shape IDs + presets. Validated by reopening the package and parsing slide XML.
- **Quiz** (`quiz/` + storyboard pairs): taught-only questions, 2-slide reveal pattern, stored Q-ID/concepts/difficulty/answer/explanation/distractors.
- **QA** (`qa/`): Content / Structural / Visual / Teaching gates → `PASS/WARN/FAIL` + human-review flags.

## Key decisions

1. `python-pptx` + controlled OOXML patching (not PptxGenJS): mature editing, notes, tables, images; animation added via isolated timing injector rather than abandoning editability.
2. Multi-chapter = `generate_deck()` (Contents + dividers + per-chapter plans); single-chapter stays divider-free. Coverage tracked globally in one ledger.
3. Subject strategies (`classifier.select_visual_strategy`) return model names the renderer now implements (`process_flow`, `2_column_compare`, `classification_grid`, `timeline`, `diagram_explanation`, …) — no silent fallback to generic cards for known models.
4. Source images embedded from `work/<doc>/assets/` with labeled walkthrough cards when native recreation is unreliable (reported in `asset_warnings.md`).
5. Validator uses stdlib zip + optional lxml; missing lxml degrades to INFO, never FAIL.

## Adding a visual model

1. Add `render_<model>(cls, slide, spec)` in `renderer/diagrams.py` returning `List[(shape_id, AnimationType)]` for animated targets.
2. Wire the name in `renderer/engine.py` dispatch.
3. Map the strategy in `storyboard/engine.py` `slide_type_map` if storyboard can emit it.
4. Add a test in `tests/test_renderer.py` rendering one slide and reopening the file.

## Presentation modes (future)

`slide_type` + `visual_model` + quiz metadata already separate content from rendering, so TEACH / REVISION (filter to summary+practice) / EXAM (quiz pairs only) / TEACHER (notes-heavy) can be implemented as storyboard filters without renderer changes.
