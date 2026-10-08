"""Regression tests: the photosynthesis demo must execute pedagogy, not extract text.

Failures once observed in the demo that must never return:
- chloroplast architecture as prose cards instead of a labeled diagram
- raw Markdown/LaTeX on slides
- Chlorella calculation fragmented or as generic cards
- day/night respiration misconception as generic prose
- ionophore answer re-solved (anything other than source-locked B fails)
- electron-trace / C3-vs-C4 practice replaced by generic/calculation templates
"""

import io
import json
import re
import zipfile
from pathlib import Path

from lessonmorph.cli import compile_document

DEMO = Path("source/examples/photosynthesis_and_cellular_energy.md")
KEY = Path("source/examples/photosynthesis_and_cellular_energy.answer_key.json")


def _build(tmp_path):
    assert DEMO.exists(), "demo source missing"
    out = tmp_path / "photo.pptx"
    work = tmp_path / "work"
    res = compile_document(DEMO, output_file=out, work_dir=work)
    assert res["status"] in ("PASS", "WARN")
    bp = json.load(io.open(work / "blueprint_ch01.json", encoding="utf-8"))
    return out, bp


def _slides_by(bp, rep):
    return [s for s in bp["slides"]
            if s["representation"] == rep and not s["body"].get("reveal")]


def test_chloroplast_labeled_diagram_with_compartments(tmp_path):
    _, bp = _build(tmp_path)
    diagrams = _slides_by(bp, "labeled_diagram")
    assert diagrams, "no labeled_diagram in blueprint"
    struct = " ".join(" ".join(s["visual"]["structure"]) for s in diagrams).lower()
    for compartment in ("thylakoid", "stroma", "lumen"):
        assert compartment in struct, f"{compartment} missing from diagram structure"
    assert any(s["visual"]["labels"] for s in diagrams)


def test_equation_typeset_not_raw_latex(tmp_path):
    _, bp = _build(tmp_path)
    eqs = _slides_by(bp, "equation_focus")
    assert eqs, "no equation slide"
    eq = eqs[0]["visual"]["equation"]
    inline = " + ".join(
        [f"{t['coefficient']} {t['species']}".strip() for t in eq["lhs"]])
    inline += f" {eq['arrow']} " + " + ".join(
        [f"{t['coefficient']} {t['species']}".strip() for t in eq["rhs"]])
    assert "\\" not in inline and "$$" not in inline
    assert "CO₂" in inline and "→" in inline


def test_chlorella_single_worked_calculation(tmp_path):
    _, bp = _build(tmp_path)
    worked = [s for s in _slides_by(bp, "worked_calculation")
              if "chlorella" in s["body"]["problem"].lower()
              or "quantum" in s["body"]["problem"].lower()]
    assert len(worked) == 1, "Chlorella calculation must be ONE worked slide"
    assert len(worked[0]["body"]["steps"]) >= 3
    assert "0.167" in " ".join(worked[0]["body"]["steps"])


def test_misconception_contrast_structure(tmp_path):
    _, bp = _build(tmp_path)
    misc = [s for s in bp["slides"] if s["task"] == "misconception"
            and not s["body"].get("reveal")]
    assert misc, "misconception never confronted"
    body = misc[0]["body"]
    assert body["wrong_idea"] and body["correct_reasoning"]
    assert "respiration" in (body["wrong_idea"] + body["correct_reasoning"]).lower()


def test_ionophore_answer_locked_to_source_B(tmp_path):
    _, bp = _build(tmp_path)
    assert KEY.exists(), "answer key file missing"
    mcqs = [s for s in _slides_by(bp, "mcq") if "ionophore" in s["assessment"]["stem"]]
    assert mcqs, "ionophore MCQ missing"
    for s in mcqs:
        assert s["assessment"]["correct_option"] == "B", \
            "ionophore answer must be source-locked B — never re-solved"
        assert s["assessment"]["origin"] == "source"


def test_practice_tasks_preserved_with_process_comparison_tasks(tmp_path):
    _, bp = _build(tmp_path)
    practice = [s for s in bp["slides"]
                if s["representation"] == "practice_problem"]
    text = " ".join(str(s["body"].get("items")) for s in practice).lower()
    assert "trace the path" in text, "electron-trace task disappeared"
    assert "c3" in text and "c4" in text, "C3/C4 task disappeared"
    tasks = {s["task"] for s in practice}
    assert "process" in tasks and "comparison" in tasks
    assert all(s["representation"] != "worked_calculation" for s in practice)
    assert all(s["body"].get("origin") == "source" for s in practice)


def test_no_markup_leaks_in_final_pptx(tmp_path):
    out, _ = _build(tmp_path)
    leaked = []
    with zipfile.ZipFile(out) as z:
        for name in z.namelist():
            if name.startswith("ppt/slides/slide") or name.startswith("ppt/notesSlides"):
                t = z.read(name).decode("utf-8")
                hits = set(re.findall(r"\\\\[a-zA-Z]+|\$\$", t))
                if hits:
                    leaked.append((name, hits))
    assert not leaked, f"markup leaked into PPTX: {leaked}"
