"""Semantic motion engine tests: primitives, tokens, IR control, restraint."""
from pathlib import Path

from lessonmorph.runtime.motion_director import (
    EFFECT_DURATION_MS, PRIMITIVE_DURATION, PRIMITIVES, TIMING_TOKENS,
    MotionDirector,
)

WEB = Path(__file__).resolve().parents[1] / "web" / "src"


def test_primitives_cover_the_required_vocabulary():
    for primitive in ("fade", "appear", "wipe", "slide", "scale", "highlight",
                      "pulse", "path_motion", "progressive_reveal",
                      "answer_reveal", "diagram_reveal", "state_transition"):
        assert primitive in PRIMITIVES and PRIMITIVES[primitive], primitive


def test_timing_tokens_restrained_and_mirrored():
    assert TIMING_TOKENS == {"fast": 180, "normal": 250, "slow": 400, "process": 600}
    tokens = (WEB / "tokens.ts").read_text(encoding="utf-8")
    for value in ("180", "250", "400", "600"):
        assert value in tokens
    motion = (WEB / "motion.ts").read_text(encoding="utf-8")
    assert "MOTION_TOKENS" in motion and "reducedMotion" in motion


def test_every_step_declares_why_and_uses_tokens():
    slide = {"representation": "flow", "task": "process",
             "reveal_sequence": ["a", "b", "c"], "visual": {}}
    motion = MotionDirector.direct(slide, ["sequencing"])
    assert len(motion["advance"]) == 3
    allowed = set(TIMING_TOKENS.values())
    for step in motion["advance"]:
        assert step["why"] and step["primitive"] in PRIMITIVES
        assert step["duration_ms"] in allowed
    assert motion["enter_transition"] == "fade"


def test_no_banned_effects_representable():
    for effect in ("bounce", "spin", "zoom", "flip", "elastic"):
        assert effect not in PRIMITIVES
        assert effect not in str(list(EFFECT_DURATION_MS) + list(PRIMITIVE_DURATION))
    motion = (WEB / "motion.ts").read_text(encoding="utf-8")
    for effect in ("bounce", "spin", "zoom"):
        assert effect not in motion


def test_path_motion_bound_to_real_waypoints():
    slide = {"representation": "labeled_diagram", "task": "mechanism",
             "reveal_sequence": ["show"],
             "visual": {"labels": [{"name": "PSII"}, {"name": "PSI"}, {"name": "NADP+"}]},
             "animation_purposes": []}
    motion = MotionDirector.direct(slide, [])
    assert motion["paths"] and motion["paths"][0]["kind"] == "transit"
    assert motion["paths"][0]["via"] == ["PSII", "PSI", "NADP+"]
    assert motion["paths"][0]["why"]
    bare = MotionDirector.direct({"representation": "concept_card", "task": "fact",
                                  "reveal_sequence": [], "visual": {}}, [])
    assert bare.get("paths", []) == []


def test_cycle_and_gradient_journeys():
    cycle = MotionDirector.direct(
        {"representation": "cycle", "task": "", "reveal_sequence": ["x"],
         "visual": {"labels": ["A", "B", "C"]}}, [])
    assert cycle["paths"][0]["kind"] == "loop"
    grad = MotionDirector.direct(
        {"representation": "labeled_diagram", "task": "gradient flow",
         "reveal_sequence": ["x"], "visual": {"labels": ["Stroma", "Lumen"]}}, [])
    assert grad["paths"][0]["kind"] == "gradient"


def test_step_targets_come_from_states():
    layers = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    states = [{"visible_layers": ["a"]}, {"visible_layers": ["a", "b"]},
              {"visible_layers": ["a", "b", "c"]}]
    slide = {"representation": "flow", "task": "", "reveal_sequence": ["1", "2"],
             "visual": {}}
    motion = MotionDirector.direct(slide, [], layers=layers, states=states)
    assert motion["advance"][0]["targets"] == ["b"]
    assert motion["advance"][1]["targets"] == ["c"]
