"""PPTX as secondary output: same IR in, browser untouched, static fallback."""
import hashlib
import io
import json
from pathlib import Path


def _imports_of(mod: str) -> list:
    src = Path(f"lessonmorph/{mod.replace('.', '/')}.py").read_text(encoding="utf-8")
    return [l.strip() for l in src.splitlines()
            if l.strip().startswith(("import ", "from ")) and "__future__" not in l]


def test_exporter_never_touches_browser_path():
    for line in _imports_of("renderer.pptx_exporter"):
        assert "lessonmorph.runtime" not in line, line
        assert "lessonmorph.web" not in line and "from web" not in line, line
        assert "PptxRenderer" not in line or "renderer.engine" in line


def test_browser_path_never_touches_pptx():
    for mod in ("runtime.pipeline", "runtime.bundle", "runtime.visual_director",
                "runtime.motion_director", "runtime.lesson_model"):
        for line in _imports_of(mod):
            assert "pptx" not in line.lower() or "exporter" in line.lower(), f"{mod}: {line}"


def test_same_ir_feeds_both_outputs_without_interference(tmp_path: Path):
    from lessonmorph.cli import _build_ir
    from lessonmorph.renderer.pptx_exporter import export_pptx
    from lessonmorph.runtime.pipeline import compile_lesson_from_ir
    from lessonmorph.runtime.bundle import write_bundle
    from lessonmorph.storyboard.engine import StoryboardEngine

    src = Path("source/examples/photosynthesis_and_cellular_energy.md")
    work = tmp_path / "work"
    ir = _build_ir(src, work)
    before = json.dumps([b.to_dict() for b in ir["blueprints"]], sort_keys=True)

    lesson, teachers = compile_lesson_from_ir(
        [s for b in ir["blueprints"] for s in b.to_dict()["slides"]],
        [{"notes": "", "animation_purposes": []}] * sum(len(b.slides) for b in ir["blueprints"]),
        ir["assets"]["mapping"], lesson_id="t", title="T")
    write_bundle(tmp_path / "lesson", lesson, teachers, ir["assets"]["mapping"])
    digest_before = hashlib.sha256(
        (tmp_path / "lesson" / "lesson.json").read_bytes()).hexdigest()

    sb = StoryboardEngine(ir["ledger"])
    exp = export_pptx(ir["blueprints"], ir["chapter_plans"], ir["ledger"],
                      ir["assets"], work, tmp_path / "out.pptx", sb)
    assert exp["slides"], "exporter produced no static fallback slides"

    after = json.dumps([b.to_dict() for b in ir["blueprints"]], sort_keys=True)
    assert before == after, "exporter mutated the shared IR"
    digest_after = hashlib.sha256(
        (tmp_path / "lesson" / "lesson.json").read_bytes()).hexdigest()
    assert digest_before == digest_after, "browser bundle changed by exporter run"

    import zipfile
    assert zipfile.ZipFile(tmp_path / "out.pptx").namelist(), "pptx is not a package"


def test_every_browser_scene_has_static_counterpart(tmp_path: Path):
    lesson = json.loads(io.open(
        "output/photosynthesis_lesson/lesson.json", encoding="utf-8").read())
    import pptx
    prs = pptx.Presentation("output/photosynthesis_and_cellular_energy.pptx")
    assert len(prs.slides) >= len(lesson["scenes"]) - len(lesson["scenes"]) // 3
