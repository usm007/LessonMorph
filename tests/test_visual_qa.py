"""Visual QA system tests: static gates, repair, shot runner, gate wiring."""
import json
from pathlib import Path

from lessonmorph.qa.visual import StaticVisualQA
from lessonmorph.qa.visual_gate import REGRESSION_SLOTS, run_visual_qa
from lessonmorph.qa.visual_repair import alternate_variant, repair_lesson

ROOT = Path(__file__).resolve().parents[1]


def _scene(sid="s01", rep="concept_card", **kw):
    base = {"scene_id": sid, "representation": rep, "task": "concept",
            "states": [{"id": "base", "visible_layers": ["title", "list"]}],
            "layers": [
                {"id": "title", "kind": "title",
                 "region": {"x": 96, "y": 44, "w": 1088, "h": 120}},
                {"id": "list", "kind": "list",
                 "region": {"x": 96, "y": 196, "w": 1088, "h": 460}}],
            "content": {"title": "How leaves capture light",
                        "points": ["Chlorophyll absorbs blue and red light for energy.",
                                   "Carotenoids shield the cell from excess sun.",
                                   "Absorption peaks decide the action spectrum."]},
            "visual": {"composition": "hero_concept", "variant": "left-anchored"},
            "assets": [],
            "interaction": {"type": "none", "options": [], "correct": "",
                            "explanation": ""},
            "motion": {"enter_transition": "fade",
                       "advance": [{"step": 1, "primitive": "appear", "effect": "fade",
                                    "duration_ms": 250, "targets": ["list"],
                                    "why": "progressive disclosure"}]},
            "estimated_minutes": 2.0}
    base.update(kw)
    return base


def _write_lesson(tmp_path: Path, scenes: list) -> Path:
    dest = tmp_path / "lesson"
    dest.mkdir()
    (dest / "lesson.json").write_text(json.dumps(
        {"lesson_id": "t", "title": "T", "canvas": {"width": 1280, "height": 720},
         "scenes": scenes, "version": 1}), encoding="utf-8")
    (dest / "teacher.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    return dest


def test_clean_scene_passes_static():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        dest = _write_lesson(Path(tmp), [_scene()])
        assert StaticVisualQA.analyze(dest).status == "PASS"


def test_semantic_mismatch_and_rogue_motion_fail():
    import tempfile
    bad = _scene(sid="s09", rep="labeled_diagram")
    bad["visual"] = {"composition": "diagram_centered", "variant": "hub"}
    bad["motion"]["advance"][0]["why"] = ""
    bad["motion"]["advance"][0]["duration_ms"] = 123
    with tempfile.TemporaryDirectory() as tmp:
        dest = _write_lesson(Path(tmp), [bad])
        report = StaticVisualQA.analyze(dest)
        assert report.status == "FAIL"
        codes = {f.code for f in report.errors()}
        assert {"semantic-mismatch", "motion-without-why", "rogue-timing"} <= codes


def test_repair_rotates_variant_and_keeps_content():
    lesson = {"scenes": [_scene()]}
    log = repair_lesson(lesson, ["s01"])
    assert lesson["scenes"][0]["visual"]["variant"] == "centered"
    assert lesson["scenes"][0]["content"]["points"][0].startswith("Chlorophyll")
    assert "s01" in log
    assert alternate_variant("hero_concept", "centered") == "left-anchored"


def test_gate_static_only_and_regression_slots(tmp_path: Path):
    dest = _write_lesson(tmp_path, [_scene()])
    gate = run_visual_qa(dest, tmp_path / "work", shots=False, repair=False)
    assert gate.status == "PASS"
    assert (tmp_path / "work" / "visual_qa.md").exists()
    assert set(REGRESSION_SLOTS) >= {"title", "equation_focus", "labeled_diagram",
                                     "worked_calculation", "contrast", "mcq"}


def test_shot_runner_two_scenes(tmp_path: Path):
    from lessonmorph.qa.shots import ShotRunner
    from lessonmorph.runtime.lesson_model import Lesson
    from lessonmorph.runtime.pipeline import compile_lesson_from_ir
    slides = [
        {"representation": "definition_focus", "task": "definition",
         "content_title": "T", "body": {"term": "T", "definition": "D"},
         "visual": {}, "reveal_sequence": ["show"],
         "purpose": "", "source_ids": [], "objective_ids": [],
         "instructional_state": "", "estimated_minutes": 1.0},
        {"representation": "mcq", "task": "assess", "content_title": "Q",
         "body": {"prompt": "P?", "options": {"A": "x", "B": "y"}, "question_id": "Q1"},
         "visual": {}, "reveal_sequence": ["ask"],
         "assessment": {"options": {"A": "x", "B": "y"}, "correct_option": "A",
                        "explanation": "E"},
         "purpose": "", "source_ids": [], "objective_ids": [],
         "instructional_state": "", "estimated_minutes": 1.0},
    ]
    lesson, teachers = compile_lesson_from_ir(
        slides, [{"notes": "", "animation_purposes": []} for _ in slides],
        {}, lesson_id="t", title="T")
    from lessonmorph.runtime.bundle import write_bundle
    dest = tmp_path / "bundle"
    write_bundle(dest, lesson, teachers, {})
    report = ShotRunner.run(dest, tmp_path / "shots")
    assert report.status in ("PASS", "WARN", "FAIL"), report.skipped
    assert len(report.shots) >= 3
