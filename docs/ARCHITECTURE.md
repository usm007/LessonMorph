# Architecture (browser-first)

## Primary path (design target)

```
SOURCE → CONTENT UNDERSTANDING (ingest/, ledger/, core/)
  → EXISTING PEDAGOGICAL MODEL (pedagogy/: planner, sequencing, strategies,
    learner, misconceptions, pacing, quality — untouched by this migration)
  → PRESENTATION BLUEPRINT / IR (blueprint/: ir, adapter, composer, registry,
    validators, sanitize, repair — untouched)
  → VISUAL DIRECTOR (runtime/visual_director.py: representation → layers,
    regions, states on the 1280×720 canvas; pure, deterministic)
  → MOTION DIRECTOR (runtime/motion_director.py: reveal intent → fade/wipe/
    slide/highlight/emphasis/reveal primitives; pure)
  → LESSON RUNTIME MODEL (runtime/lesson_model.py: Lesson/Scene/SceneState/
    SceneLayer/SceneMotion/SceneInteraction + TeacherScene; runtime/pipeline.py
    orchestrates IR → Lesson)
  → BROWSER PRESENTATION (web/src/: viewport scaler, store state machine,
    scene renderer, motion player, keyboard/mouse/fullscreen nav, progress
    chrome; runtime/bundle.py writes the offline lesson dir)
  → DESIGN + VISUAL QA (runtime/lesson_qa.py: schema, student-separation,
    offline, assets, teacher 1:1 mapping; FAIL blocks delivery)
```

## Exporter path (regression only)

```
PRESENTATION IR → PPTX EXPORTER (renderer/pptx_exporter.py: SlideComposer →
  PptxRenderer → RenderQA + repair → QualityGateValidator) → .pptx
```

The exporter reads the same IR and feeds nothing back. Nothing in
`lessonmorph/runtime/` or `web/` imports it.

## Interfaces

| Boundary | Module | Input → Output |
|---|---|---|
| Pedagogy → IR | `blueprint/adapter.BlueprintCompiler.compile(plan)` | `ChapterPlan` → `Blueprint` |
| IR → Scenes | `runtime/pipeline.compile_lesson_from_ir(slides, notes, assets, id, title)` | SlideIR dicts → `(Lesson, TeacherScene[])` |
| Composition | `runtime/visual_director.VisualDirector.direct(slide)` | SlideIR dict → layers/states/content/visual/interaction/assets |
| Motion | `runtime/motion_director.MotionDirector.direct(slide, purposes)` | reveal + purposes → `{enter_transition, advance[]}` |
| Bundle | `runtime/bundle.write_bundle(dir, lesson, teachers, sources)` | Lesson → `index.html lesson.json teacher.json runtime.js styles.css assets/` |
| Gate | `runtime/lesson_qa.LessonQA.validate(dir)` | bundle dir → PASS/FAIL report |
| Exporter | `renderer/pptx_exporter.export_pptx(...)` | IR → `.pptx` + RenderQA report |

Scene = student `Scene` + teacher `TeacherScene` on the same `scene_id`:
student carries representation/task/states/layers/content/visual/assets/
interaction(motion); teacher carries purpose/instructional_state/learning_goal/
teacher_notes+prompt/source_ids/objective_ids/concept_id. Student JSON never
contains internal fields.

## Adding a visual model (browser)

1. Add the representation to `blueprint/ir.py` + `registry.py` + `adapter.select_representation`.
2. Add the layer layout to `runtime/visual_director.LAYOUTS` + content mapping in `_content`.
3. Render the layer kinds in `web/src/render.ts` (+ styles in `web/src/styles.css`).
4. Rebuild: `cd web && npm run build`; add a test in `tests/test_browser_runtime.py`.

## Presentation modes (future)

`representation` + `task` + interaction metadata already separate content from
rendering, so TEACH / REVISION / EXAM / TEACHER can be storyboard filters or
bundle slicers without renderer changes. Teacher mode reads `teacher.json`.
