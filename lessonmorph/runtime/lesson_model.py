"""Lesson Runtime Model — renderer-neutral scene/state model for the browser lesson.

Position in architecture:
    Presentation IR (SlideIR, authoritative)
        ↓ VisualDirector (composition) + MotionDirector (motion)
    Lesson (this module: scenes + states + interactions + assets)
        ↓ bundle.py
    BROWSER PRESENTATION (executes scenes; never reinterprets pedagogy)

A scene fills one 16:9 viewport. Scenes move through discrete STATES
(e.g. base → thylakoid_revealed → ...) without rebuilding the app.
Student bundle JSON carries NO internal fields (no source/objective ids,
no model labels, no teacher guidance); those live in teacher.json.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


@dataclass
class SceneLayer:
    """One composited layer: content shown from a given state onward."""
    id: str  # e.g. "title", "diagram", "opt-B"
    kind: str  # title|kicker|text|list|diagram|table|equation|options|
    # prompt|media|answer|note|spacer
    region: Dict[str, float] = field(default_factory=dict)  # x,y,w,h in canvas px
    content_ref: str = ""  # key into Scene.content payloads
    reveal_at: int = 0  # first visible state index (0 = base state)
    z: int = 0


@dataclass
class SceneState:
    id: str  # e.g. "base", "s1", "answered"
    label: str = ""
    visible_layers: List[str] = field(default_factory=list)


@dataclass
class SceneMotion:
    enter_transition: str = "fade"  # fade only unless story needs direction
    advance: List[Dict[str, Any]] = field(default_factory=list)
    # [{step, primitive, effect, duration_ms, targets, why}]
    paths: List[Dict[str, Any]] = field(default_factory=list)
    # [{kind: transit|loop|gradient, via: [label names], duration_ms, why}]


@dataclass
class SceneInteraction:
    type: str = "none"  # none|choice|self_check|open
    options: List[str] = field(default_factory=list)  # option keys, e.g. ["A","B"]
    correct: str = ""  # LOCKED answer key (renderer checks, never solves)
    explanation: str = ""


@dataclass
class Scene:
    scene_id: str  # e.g. "s01" (stable, 1-based order)
    representation: str  # IR representation value (renderer picks composition)
    task: str = ""
    states: List[SceneState] = field(default_factory=list)
    layers: List[SceneLayer] = field(default_factory=list)
    content: Dict[str, Any] = field(default_factory=dict)  # student-safe payloads
    visual: Dict[str, Any] = field(default_factory=dict)  # renderer-neutral visual spec
    assets: List[str] = field(default_factory=list)  # local asset paths
    interaction: SceneInteraction = field(default_factory=SceneInteraction)
    motion: SceneMotion = field(default_factory=SceneMotion)
    estimated_minutes: float = 2.0


@dataclass
class Lesson:
    lesson_id: str
    title: str
    canvas: Dict[str, int] = field(default_factory=lambda: {
        "width": CANVAS_WIDTH, "height": CANVAS_HEIGHT})
    scenes: List[Scene] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TeacherScene:
    """Teacher-facing metadata, stored separately (never in student bundle)."""
    scene_id: str
    purpose: str = ""
    instructional_state: str = ""
    learning_goal: List[str] = field(default_factory=list)
    teacher_notes: str = ""
    teacher_prompt: str = ""
    source_ids: List[str] = field(default_factory=list)
    objective_ids: List[str] = field(default_factory=list)
    concept_id: str = ""
    estimated_minutes: float = 2.0
    representation_reason: str = ""  # why this visual was selected (debugging)
    pedagogical_ref: str = ""  # chapter:state that decided this scene (debugging)
