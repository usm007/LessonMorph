"""Student interaction experience tests: think, answer, workspace, control."""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "src"


def _read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_think_state_before_answers():
    render = _read("render.ts")
    assert "Think first" in render and "30 seconds" in render
    # Think cue shows only before commitment, never with the answer.
    assert "think-cue" in render


def test_answers_come_from_locked_assessment():
    render = _read("render.ts")
    assert "scene.interaction.correct" in render
    assert "inter.explanation" in render or "interaction.explanation" in render
    # Nothing here solves or regenerates answers.
    for forbidden in ("correct =", "correct:", "solve(", "computeAnswer"):
        assert forbidden not in render


def test_practice_workspace_structured():
    render = _read("render.ts")
    assert "renderPracticeNote" in render
    assert "workspace" in render and "blank" in render


def test_keyboard_touch_mouse_and_subtle_chrome():
    nav = _read("nav.ts")
    for key in ("ArrowRight", "ArrowLeft", "Enter", "Home", "End"):
        assert key in nav, key
    assert "Escape" in nav and "click" in nav
    # No hover-gated essential information.
    css = _read("styles.css")
    assert ":hover" not in css or "border-color" in css
    assert ".lesson-tag" in css and "ellipsis" in css


def test_graceful_degradation():
    engines = _read("engines.ts")
    assert "onerror" in engines and "img-broken" in engines
    motion = _read("motion.ts")
    assert "try" in motion and "catch" in motion
    assert "reducedMotion" in motion
    render = _read("render.ts")
    assert "if (!wrap.querySelector" in render or "return null" in render


def test_progress_fullscreen_present_not_gamified():
    render = _read("render.ts")
    assert "progress" in render and "toggleFullscreen" in render
    for forbidden in ("scoreboard", "badge", "streak", "leaderboard", "gameover"):
        assert forbidden not in render.lower()
