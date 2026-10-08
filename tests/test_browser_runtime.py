"""Browser-first architecture tests: scene model, directors, bundle, web contracts."""
import json
from pathlib import Path

from lessonmorph.runtime.bundle import build_scenes
from lessonmorph.runtime.lesson_model import CANVAS_WIDTH, CANVAS_HEIGHT
from lessonmorph.runtime.lesson_qa import LessonQA
from lessonmorph.runtime.motion_director import MotionDirector
from lessonmorph.runtime.pipeline import compile_lesson_from_ir
from lessonmorph.runtime.visual_director import VisualDirector


def _sample_slide():
    return {
        "representation": "definition_focus",
        "task": "explain",
        "content_title": "Photosynthesis",
        "kicker": "Core concept",
        "body": {"term": "Photosynthesis", "definition": "Converts light to chemical energy."},
        "visual": {"subject": "biology", "structure": "card"},
        "reveal_sequence": ["show definition"],
        "teacher_action": {"prompt": "Ask what plants need."},
        "purpose": "Teach definition",
        "concept_id": "c1",
        "learning_goal": ["Define photosynthesis"],
        "source_ids": ["C001"],
        "objective_ids": ["O1"],
        "instructional_state": "explain",
        "estimated_minutes": 2.0,
    }


def _sample_mcq():
    return {
        "representation": "mcq",
        "task": "assess",
        "content_title": "Check",
        "body": {"prompt": "Where does photosynthesis occur?",
                 "options": {"A": "Chloroplast", "B": "Nucleus"},
                 "question_id": "Q1"},
        "visual": {},
        "reveal_sequence": ["ask"],
        "assessment": {"options": {"A": "Chloroplast", "B": "Nucleus"},
                       "correct_option": "A", "explanation": "Chlorophyll lives there."},
        "purpose": "Check understanding",
        "source_ids": ["C002"],
        "objective_ids": ["O1"],
        "instructional_state": "assess",
        "estimated_minutes": 2.0,
    }


def test_canvas_is_16_9_logical():
    assert (CANVAS_WIDTH, CANVAS_HEIGHT) == (1280, 720)


def test_directors_are_pure_and_pedagogy_free():
    import lessonmorph.runtime.visual_director as vd
    import lessonmorph.runtime.motion_director as md
    import lessonmorph.runtime.bundle as bb
    for mod in (vd, md, bb):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import pptx" not in src and "from pptx" not in src
        assert "PedagogicalPlanner" not in src
    directed = VisualDirector.direct(_sample_slide())
    assert directed["layers"] and directed["states"]
    assert directed["states"][0]["id"] == "base"
    motion = MotionDirector.direct(_sample_slide(), ["signalling"])
    assert motion["enter_transition"] == "fade" and motion["advance"]


def test_scene_states_progress_without_rebuild():
    lesson, teachers = compile_lesson_from_ir(
        [_sample_slide()], [{"notes": "Teach it.", "animation_purposes": ["signalling"]}],
        {}, lesson_id="demo", title="Demo")
    scene = lesson.scenes[0]
    assert len(scene.states) >= 2
    first = set(scene.states[0].visible_layers)
    last = set(scene.states[-1].visible_layers)
    assert first < last  # states reveal; app does not rebuild
    assert teachers[0].scene_id == scene.scene_id
    assert teachers[0].source_ids == ["C001"]  # traceability lives teacher-side


def test_locked_answers_and_student_separation(tmp_path: Path):
    lesson, teachers = compile_lesson_from_ir(
        [_sample_mcq()], [{"notes": "", "animation_purposes": []}],
        {}, lesson_id="quiz", title="Quiz")
    assert lesson.scenes[0].interaction.correct == "A"
    assert lesson.scenes[0].interaction.explanation != ""
    student_text = json.dumps(lesson.to_dict())
    for leaked in ("source_ids", "objective_ids", "concept_id",
                   "instructional_state", "teacher_action", "learning_goal"):
        assert leaked not in student_text


def test_offline_bundle_and_lesson_qa(tmp_path: Path):
    lesson, teachers = compile_lesson_from_ir(
        [_sample_slide(), _sample_mcq()],
        [{"notes": "n1", "animation_purposes": []}, {"notes": "n2", "animation_purposes": []}],
        {}, lesson_id="bundle", title="Bundle")
    from lessonmorph.runtime.bundle import write_bundle
    dest = tmp_path / "lesson"
    write_bundle(dest, lesson, teachers, {})
    for name in ("index.html", "runtime.js", "styles.css", "lesson.json", "teacher.json"):
        assert (dest / name).exists()
    html = (dest / "index.html").read_text(encoding="utf-8")
    assert "lesson-data" in html
    report = LessonQA.validate(dest)
    assert report.status == "PASS", report.to_markdown()


def test_bundle_shell_escapes_title_and_labels_language(tmp_path: Path):
    from lessonmorph.runtime.bundle import write_bundle
    lesson, teachers = compile_lesson_from_ir(
        [_sample_slide()], [{"notes": "", "animation_purposes": []}],
        {}, lesson_id="x", title="AT&T <Basics>")
    dest = tmp_path / "lesson"
    write_bundle(dest, lesson, teachers, {}, lang="fr")
    html = (dest / "index.html").read_text(encoding="utf-8")
    head = html.split('id="lesson-data"')[0]  # shell only, not the JSON payload
    assert "AT&T <Basics>" not in head  # raw markup must not reach the shell
    assert "AT&amp;T &lt;Basics&gt;" in head
    assert 'lang="fr"' in head
    dest2 = tmp_path / "lesson2"
    write_bundle(dest2, lesson, teachers, {}, lang='en"><script>')
    assert 'lang="en"' in (dest2 / "index.html").read_text(encoding="utf-8")


def test_web_runtime_contracts():
    web = Path(__file__).resolve().parents[1] / "web" / "src"
    viewport = (web / "viewport.ts").read_text(encoding="utf-8")
    assert "1280" in viewport and "720" in viewport
    assert "overflow" in viewport and "hidden" in viewport
    assert "scale" in viewport  # proportional scaling / letterbox
    nav = (web / "nav.ts").read_text(encoding="utf-8")
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert key in nav
    assert "requestFullscreen" in nav
    assert "click" in nav  # click/tap progression
    store = (web / "store.ts").read_text(encoding="utf-8")
    assert "stateIndex" in store and "sceneIndex" in store  # scene + state progression
    render = (web / "render.ts").read_text(encoding="utf-8")
    assert "progress" in render.lower() or "renderChrome" in render
    css = (web / "styles.css").read_text(encoding="utf-8")
    assert "overflow" in css and "hidden" in css  # no scrolling


def test_browser_bundle_has_no_pptx_dependency():
    import lessonmorph.runtime.pipeline as pipe
    import lessonmorph.runtime.bundle as bb
    for mod in (pipe, bb):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from pptx" not in src and "import pptx" not in src
        assert "PptxRenderer" not in src
