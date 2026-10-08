"""Student-first browser design-system tests.

Guards the task contract without touching pedagogy/IR semantics:
tokens centralized, 17 genuine composition families, cards not dominant,
consistent type/spacing, clear hierarchy, no scroll, readability, and
deterministic visual variety.
"""
import re
from pathlib import Path

from lessonmorph.blueprint.ir import Representation
from lessonmorph.runtime import visual_director as vd

WEB = Path(__file__).resolve().parents[1] / "web" / "src"

FAMILIES = vd.COMPOSITION_FAMILIES
REP_TO_FAM = vd.FAMILY_BY_REPRESENTATION


def _read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_tokens_centralized_and_mirrored_in_css():
    tokens = _read("tokens.ts")
    css = _read("styles.css")
    for token in ("canvas", "spacing", "type", "color", "radius", "shadow", "motion",
                  "display", "hero", "question", "answer", "equation", "data"):
        assert token in tokens, f"tokens.ts missing {token}"
    for var in ("--fs-display", "--fs-hero", "--fs-title", "--fs-question",
                "--fs-answer", "--fs-equation", "--fs-data", "--sp-md",
                "--ink", "--accent", "--hairline", "--motion-normal",
                "--motion-fast", "--motion-slow", "--motion-process"):
        assert var in css, f"styles.css missing {var}"
    # Spot-check mirrored numbers between tokens.ts and :root.
    for value in ("1280", "720", "76", "56", "44", "32", "22", "18",
                  "#2f6fed", "#d7dee8"):
        assert value in tokens and value in css, f"token/css drift on {value}"


def test_seventeen_families_cover_every_representation():
    assert len(FAMILIES) == 17
    assert len(vd.FAMILY_VARIANTS) == 17
    reps = {r.value for r in Representation}
    assert set(REP_TO_FAM) == reps, f"unmapped reps: {reps - set(REP_TO_FAM)}"
    assert set(REP_TO_FAM.values()) | {"answer_reveal"} == set(FAMILIES)
    # answer_reveal is not a static IR mapping: merged Q&A pairs become it.
    from lessonmorph.runtime.bundle import build_scenes
    scenes, _ = build_scenes(
        {"slides": [
            {"representation": "mcq", "task": "assess", "content_title": "Q",
             "body": {"prompt": "P?", "options": {"A": "x", "B": "y"}, "question_id": "Q9"},
             "visual": {}, "reveal_sequence": ["ask"],
             "assessment": {"options": {"A": "x", "B": "y"}, "correct_option": "A", "explanation": "E"},
             "purpose": "", "source_ids": [], "objective_ids": [], "instructional_state": "",
             "estimated_minutes": 2.0},
            {"representation": "mcq", "task": "assess", "content_title": "A",
             "body": {"reveal": True, "question_id": "Q9"},
             "visual": {}, "reveal_sequence": ["reveal"],
             "assessment": {"options": {"A": "x", "B": "y"}, "correct_option": "A", "explanation": "E"},
             "purpose": "", "source_ids": [], "objective_ids": [], "instructional_state": "",
             "estimated_minutes": 1.5},
        ]},
        [{"notes": "", "animation_purposes": []}], {})
    assert scenes[0].visual.get("composition") == "answer_reveal"


def test_families_have_genuinely_different_geometry():
    kinds = ["title", "list", "list"]
    seen: dict[str, str] = {}
    for fam in FAMILIES:
        regions = vd.family_regions(fam, vd.FAMILY_VARIANTS[fam][0], kinds)
        assert len(regions) == len(kinds), fam
        for r in regions:
            assert r["x"] >= 0 and r["y"] >= 0
            assert r["x"] + r["w"] <= 1280 and r["y"] + r["h"] <= 720, f"{fam} overflows canvas"
        sig = ";".join(f"{r['x']:.0f},{r['y']:.0f},{r['w']:.0f},{r['h']:.0f}" for r in regions)
        assert sig not in seen.values(), f"{fam} duplicates {seen}"
        seen[fam] = sig
    assert len(set(seen.values())) == 17


def test_typescript_executes_all_families_without_lesson_content():
    comp = _read("compositions.ts")
    render = _read("render.ts")
    for fam in FAMILIES:
        assert fam in comp, f"compositions.ts missing {fam}"
    for component in ("HeroScene", "HeroConcept", "FullVisualScene", "SplitScene",
                      "DiagramScene", "ProcessScene", "CycleScene", "ComparisonScene",
                      "EquationScene", "DataScene", "QuestionScene", "AnswerScene",
                      "MisconceptionScene", "PracticeScene", "ConceptMapScene",
                      "SynthesisScene", "ReflectionScene"):
        assert component in comp, f"missing component {component}"
    assert "renderFamily" in render and "familyOf" in render and "stageClass" in render
    for forbidden in ("Photosynthesis", "Chlorella", "thylakoid", "ionophore", "Newton"):
        assert forbidden not in render and forbidden not in comp, f"hardcoded content: {forbidden}"


def test_cards_are_not_the_default():
    css = _read("styles.css")
    render = _read("render.ts")
    assert ".card" not in css and "lyr-card" not in render
    # Cardless default is explicit in the stylesheet.
    assert "background: transparent; border: 0" in css
    # Structural borders only (radius/color excluded): card-like surfaces
    # must be named treatments, never generic containers.
    bordered = set(re.findall(
        r"([.#][\w-]+)[^}{]*\{[^}]*?border(?:-(?:top|right|bottom|left|width|style))?\s*:",
        css))
    allowed = {
        ".scene-body",  # the cardless reset itself (background: transparent; border: 0)
        ".opt",  # choice control
        ".lyr-table",  # data hairlines
        ".cmp-matrix",  # comparison/data matrix hairlines
        "#fs-btn",  # chrome control
        ".answer-banner",  # verdict banner
        "#progress",  # chrome hairline
        ".fam-equation_focus",  # legend accent rule
        ".fam-misconception",  # correction accent rule
        ".fam-split_visual",  # editorial split rule
        ".fam-process_pathway",  # vertical path rule
        ".wc-right",  # verified-model panel
        ".pw-loopback",  # feedback-loop line
        ".pw-branch",  # branch lane rule
        ".eqn",  # energy badge + fraction rules
        ".img-annotated",  # image annotation callout
        ".path-marker",  # journey marker ring
        ".img-broken",  # graceful image-failure placeholder
    }
    assert bordered - allowed == set(), f"card-like surfaces beyond treatments: {bordered - allowed}"


def test_typography_and_spacing_consistent():
    css = _read("styles.css")
    for cls in (".t-display", ".t-hero", ".t-title", ".t-subtitle", ".t-body",
                ".t-body-large", ".t-label", ".t-caption", ".t-question",
                ".t-answer", ".t-equation", ".t-data"):
        assert cls in css, f"missing type style {cls}"
    # Type/spacing flow from vars, not scattered literals.
    assert css.count("var(--fs-") >= 12
    assert css.count("var(--sp-") >= 2 or "var(--gutter)" in css
    # No full-chapter-title repetition: chrome tag is small + truncated.
    assert ".lesson-tag" in css and "ellipsis" in css


def test_viewport_no_scroll_letterboxed():
    css = _read("styles.css")
    assert css.count("overflow: hidden") >= 3
    assert "overflow-x" not in css and "overflow-y" not in css
    code = re.sub(r"/\*.*?\*/", "", css, flags=re.S).lower()
    assert "scroll" not in code
    viewport = _read("viewport.ts")
    assert "1280" in viewport and "720" in viewport and "scale" in viewport


def test_readability_floor():
    tokens = _read("tokens.ts")
    body = int(re.search(r"body:\s*\{[^}]*size:\s*(\d+)", tokens).group(1))
    question = int(re.search(r"question:\s*\{[^}]*size:\s*(\d+)", tokens).group(1))
    equation = int(re.search(r"equation:\s*\{[^}]*size:\s*(\d+)", tokens).group(1))
    assert body >= 20 and question >= 30 and equation >= 56
    css = _read("styles.css")
    assert "prefers-reduced-motion" in css


def test_variety_deterministic_never_random():
    vd_src = Path(vd.__file__).read_text(encoding="utf-8")
    bundle_src = (Path(vd.__file__).parent / "bundle.py").read_text(encoding="utf-8")
    assert "import random" not in vd_src and "import random" not in bundle_src
    slide = {"representation": "concept_card", "body": {"points": ["a"]},
             "visual": {}, "reveal_sequence": []}
    first = [vd.VisualDirector.direct(slide, []).get("variant")]
    recent: list = []
    for _ in range(4):
        v = vd.VisualDirector.direct(slide, recent)["variant"]
        recent.append("hero_concept")
    assert first == [vd.VisualDirector.direct(slide, []).get("variant")]  # repeatable
    assert len(set([vd.select_variant("hero_concept", "standard", ["hero_concept"] * k)
                    for k in range(4)])) > 1  # repeats rotate arrangement
    assert vd.content_density({"body": {"points": ["x" * 2000]}}) == "dense"
