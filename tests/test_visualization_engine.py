"""Scientific visualization engine tests.

Runtime behavior is verified by executing the pure engine builders in node
(web/build/engines.test.cjs, 30 assertions, no DOM needed). This module adds
wiring checks (renderers delegate by content type, no hardcoded content, no
raw markup leaks) plus the photosynthesis regression benchmark.
"""
import io
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"


def _read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_engine_harness_passes():
    proc = subprocess.run(["node", "web/build/engines.test.cjs"],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "31 assertions passed" in proc.stdout


def test_content_type_determines_visual_form():
    render = _read("render.ts")
    for rep in ("flow", "sequence", "pathway", "cycle", "cause_effect",
                "concept_map", "hierarchy", "worked_calculation",
                "practice_problem", "contrast"):
        assert rep in render, f"render.ts ignores {rep}"
    for engine in ("engDiagram", "engPathway", "engCycle", "engComparison",
                   "engSoloModel", "engEquation", "engData", "engConceptMap",
                   "engImage", "engCauseMechanismEffect"):
        assert engine in render, f"render.ts never calls {engine}"
    engines = _read("engines.ts")
    for internal in ("engBranch", "engSpectrum", "engBars", "engLine", "engScatter"):
        assert internal in engines, f"engines.ts missing {internal}"
    for legacy in ("dg-hub-label", "dg-name", "renderTable(scene", "renderEquation(scene",
                   "renderDiagram(scene", "renderMedia(scene"):
        assert legacy not in render, f"legacy text-card renderer remains: {legacy}"


def test_engines_carry_no_lesson_content_and_no_raw_markup():
    engines = _read("engines.ts")
    # Generic morphology keywords (membrane, lumen, …) are presentation
    # heuristics; lesson *content* (organisms, pathways, sentences) is banned.
    for forbidden in ("Chlorella", "Calvin cycle", "dark reactions", "ionophore",
                      "Newton", "Photosynthesis is", "NADP", "Photosystem", "Rubisco"):
        assert forbidden not in engines, f"hardcoded lesson content: {forbidden}"
    assert "$$" not in engines and "\\frac" not in engines


def _lesson() -> dict:
    return json.loads(io.open(ROOT / "output" / "photosynthesis_lesson" / "lesson.json",
                              encoding="utf-8").read())


def _scenes_by(rep: str) -> list:
    return [s for s in _lesson()["scenes"] if s["representation"] == rep]


def test_photosynthesis_benchmark_visuals():
    lesson = _lesson()
    by_id = {s["scene_id"]: s for s in lesson["scenes"]}

    def has_text(sid: str, needle: str) -> bool:
        return needle.lower() in json.dumps(by_id[sid]).lower()

    hook = _scenes_by("title")
    assert hook and hook[0]["visual"].get("composition") == "cinematic_hook"

    defs = _scenes_by("definition_focus")
    assert defs and "photosynthesis" in json.dumps(defs[0]["content"]).lower()

    eqs = _scenes_by("equation_focus")
    assert eqs, "photosynthesis equation missing"
    terms = (eqs[0]["visual"].get("equation", {}).get("lhs", [])
             + eqs[0]["visual"].get("equation", {}).get("rhs", []))
    species = " ".join(t.get("species", "") for t in terms)
    assert "CO" in species and "O" in species  # structured terms, never raw latex
    blob = json.dumps(eqs[0]["visual"]["equation"])
    assert "$$" not in blob and "\\" not in blob.replace("\\u", "")

    diagrams = _scenes_by("labeled_diagram")
    assert diagrams, "chloroplast architecture missing"
    v = diagrams[0]["visual"]
    names = [(l if isinstance(l, str) else l.get("name", "")) for l in v.get("labels", [])]
    text = " ".join(names).lower()
    for compartment in ("thylakoid", "stroma", "lumen"):
        assert compartment in text, f"{compartment} has no bound region"
    assert len(names) >= 3

    worked = _scenes_by("worked_calculation")
    assert worked and len(worked[0]["content"].get("steps", [])) >= 3  # quantum calc pathway

    misc = [s for s in _scenes_by("contrast")]
    assert misc and misc[0]["content"].get("wrong_idea") and misc[0]["content"].get("correct_idea")

    data = _scenes_by("data_table")
    assert data and "nm" in " ".join(data[0]["visual"].get("columns", [])).lower()  # pigment spectrum

    practice = [s for s in _lesson()["scenes"] if s["representation"] == "practice_problem"]
    text = " ".join(json.dumps(p) for p in practice).lower()
    assert "electron" in text and "c3" in text and "c4" in text

    synth = _scenes_by("big_picture")
    assert synth and synth[0]["content"].get("points")


def test_no_textbox_default_in_runtime():
    render = _read("render.ts")
    assert "renderContrastModel" in render and "renderSemanticList" in render
    assert "renderDataNode" in render and "renderDiagramNode" in render
    assert "renderEquationNode" in render and "renderPracticeNote" in render
    assert "renderMediaNode" in render
