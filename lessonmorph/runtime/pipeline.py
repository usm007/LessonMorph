"""Browser-first lesson pipeline — the PRIMARY presentation path.

Architecture position (authoritative)::

    SOURCE DOCUMENT
        -> CONTENT UNDERSTANDING (ingest + ledger; untouched by this module)
        -> EXISTING PEDAGOGICAL MODEL (planner; untouched by this module)
        -> PRESENTATION BLUEPRINT / IR (SlideIR, authoritative)
        -> VISUAL DIRECTOR (composition: layers/regions/states)
        -> MOTION DIRECTOR (motion: entrance/advance primitives)
        -> LESSON RUNTIME MODEL (Lesson: scenes + states, student-safe)
        -> BROWSER PRESENTATION (executes scenes; never reinterprets pedagogy)
        -> DESIGN + VISUAL QA (LessonQA)

Input/output contracts (nothing here imports PPTX)::

    PedagogicalModel -> BlueprintCompiler.compile(plan) -> Blueprint (IR)
    Blueprint.to_dict()["slides"] + storyboard notes + asset_map
        -> build_scenes() [VisualDirector.direct + MotionDirector.direct per slide]
        -> (Lesson, TeacherScene list)
    (Lesson, teachers, asset_sources) -> write_bundle(lesson_dir)
    lesson_dir -> LessonQA.validate() -> PASS/FAIL (FAIL blocks delivery)

Scene model (student Scene + teacher TeacherScene joined by scene_id)::

    student Scene:  scene_id, representation, task, states, layers,
                    content, visual, assets, interaction, motion,
                    estimated_minutes
    teacher Scene:  scene_id, purpose, instructional_state, learning_goal,
                    teacher_notes, teacher_prompt, source_ids (traceability),
                    objective_ids, concept_id, estimated_minutes

Together they carry every required scene field (purpose, concept,
learning_goal, representation, content, visual, assets, interaction,
animation/transition via motion, teacher_notes, assessment via
interaction+locked answer, source_traceability via source_ids) while
the student bundle itself stays clean (no source/objective ids,
no intents, no model labels, no teacher guidance).
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

from lessonmorph.runtime.bundle import build_scenes, write_bundle
from lessonmorph.runtime.lesson_model import Lesson, TeacherScene
from lessonmorph.runtime.lesson_qa import LessonQA, LessonQAReport


def compile_lesson_from_ir(
    blueprint_slide_dicts: List[Dict[str, Any]],
    storyboard_notes: List[Dict[str, Any]],
    asset_map: Dict[str, str],
    lesson_id: str,
    title: str,
) -> tuple[Lesson, List[TeacherScene]]:
    """IR -> Lesson Runtime Model. Pure orchestration over the directors.

    Each SlideIR dict passes through VisualDirector (composition) and
    MotionDirector (motion) inside build_scenes; prompt/reveal pairs merge
    into one scene with an added "answered" state.
    """
    scenes, teachers = build_scenes({"slides": blueprint_slide_dicts}, storyboard_notes, asset_map)
    lesson = Lesson(lesson_id=lesson_id, title=title, scenes=scenes)
    return lesson, teachers


def write_and_validate_lesson(
    lesson_dir: Path | str,
    lesson: Lesson,
    teachers: List[TeacherScene],
    asset_sources: Dict[str, str],
    lang: str = "en",
) -> tuple[Dict[str, Any], LessonQAReport]:
    """Write the offline bundle and gate it on LessonQA. FAIL raises."""
    manifest = write_bundle(lesson_dir, lesson, teachers, asset_sources, lang=lang)
    report = LessonQA.validate(lesson_dir)
    if report.status != "PASS":
        details = "; ".join(f"{c.name}: {c.detail}" for c in report.errors())
        raise RuntimeError(f"Lesson QA FAILED: {details}")
    return manifest, report
