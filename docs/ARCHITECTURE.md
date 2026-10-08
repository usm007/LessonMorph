# Developer notes

## Architecture (brain → execution plan → executor)

- **Content layer** (`ingest/`, `ledger/`): extraction → normalization → atoms (`C001…`) → coverage. No pedagogy here.
- **Pedagogical intelligence layer** (`pedagogy/` + `core/models.py` plan types): the formal decision engine. Authoritative input to everything downstream — never reinterpreted, never duplicated. (Details + constitution: `skill/references/pedagogy.md`.)
- **Presentation Blueprint / IR** (`blueprint/`): the execution plan between pedagogy and slides. `ir.py` (typed `SlideIR`/`Blueprint`, finite `Representation` grammar, `TaskType` taxonomy, structured `EquationIR`, `LockedAssessment`), `adapter.py` (`BlueprintCompiler`: task classification → in-family representation choice → structured payloads, content inventory with `Source → Blueprint → Slide` traceability), `composer.py` (deterministic `SlideIR` → `SlideSpec`), `registry.py` (grammar single source of truth), `sanitize.py` (no Markdown/LaTeX ever reaches a slide). Inspectable via `work/blueprint_<chapter>.json` before rendering.
- **Slide + visual composition** (`renderer/`): `PptxRenderer` dispatches IR representations to `SemanticRenderer` (real shapes/connectors/arrows/native tables per representation) and legacy models for chrome. Pure execution — no pedagogical decisions.
- **Animation layer** (`animation/`): isolated `<p:timing>` injector on real shape IDs + presets. Validated by reopening the package and parsing slide XML.
- **Quiz**: locked assessments only — SOURCE QUESTION → LOCKED KEY → IR → SLIDE → VALIDATOR. Answer slides render from the locked object; `<doc>.answer_key.json` pins source answers.
- **QA**: legacy gates (`qa/`) **+ Blueprint QA** (`blueprint/validators.py`: content/pedagogical/representation/assessment gates, FAIL refuses render) **+ Render QA** (`blueprint/render_qa.py`: geometry + text scan of the PPTX, PNG via LibreOffice when present) **+ repair loop** (`blueprint/repair.py`: regenerate affected slides only, ≤2 rounds, escalate the rest) → `PASS/WARN/FAIL` + human-review flags.
- **Legacy storyboard** (`storyboard/`): superseded by Blueprint→Composer; kept for compatibility and multi-chapter chrome builders.

## Key decisions

1. `python-pptx` + controlled OOXML patching (not PptxGenJS): mature editing, notes, tables, images; animation added via isolated timing injector rather than abandoning editability.
2. Multi-chapter = `generate_deck()` (Contents + dividers + per-chapter plans); single-chapter stays divider-free. Coverage tracked globally in one ledger.
3. Subject strategies (`classifier.select_visual_strategy`) return model names the renderer now implements (`process_flow`, `2_column_compare`, `classification_grid`, `timeline`, `diagram_explanation`, …) — no silent fallback to generic cards for known models.
4. Source images embedded from `work/<doc>/assets/` with labeled walkthrough cards when native recreation is unreliable (reported in `asset_warnings.md`).
5. Validator uses stdlib zip + optional lxml; missing lxml degrades to INFO, never FAIL.

## Adding a representation (semantic, not cosmetic)

1. Add the value to `Representation` in `blueprint/ir.py` and its legal tasks in `TASK_FAMILIES` (a representation without a task family is rejected by Blueprint QA).
2. Add `render_<representation>(cls, slide, spec)` in `renderer/semantic.py` reading ONLY structured `elements_data` keys; return `List[(shape_id, AnimationType)]`.
3. Wire the name in `renderer/engine.py` `_SEMANTIC_DISPATCH` (or the `concept_card` branch for points-style cards).
4. Add Blueprint + render coverage in `tests/test_blueprint.py` (and a photosynthesis regression case if it affects the demo).

## Presentation modes (future)

`slide_type` + `visual_model` + quiz metadata already separate content from rendering, so TEACH / REVISION (filter to summary+practice) / EXAM (quiz pairs only) / TEACHER (notes-heavy) can be implemented as storyboard filters without renderer changes.
