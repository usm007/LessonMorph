"""Motion Director — animation purposes → declarative browser motion.

Pure translation of the IR's reveal/animation intent into motion primitives
the browser executes with CSS / Web Animations API. No pedagogy, no content.

Vocabulary (browser-native, sufficient, calm):
  fade | wipe | slide | highlight | emphasis | reveal
Purposes map onto these; slide transitions default to a subtle fade.
"""

from __future__ import annotations
from typing import Any, Dict, List

# Animation purpose (IR) → motion effect (browser).
PURPOSE_TO_EFFECT = {
    "sequencing": "reveal",
    "signalling": "fade",
    "decomposition": "reveal",
    "reconstruction": "reveal",
    "transformation": "slide",
    "causal_explanation": "wipe",
    "comparison": "highlight",
    "highlighting": "highlight",
    "error_correction": "emphasis",
    "answer_reveal": "reveal",
}

EFFECT_DURATION_MS = {
    "fade": 250, "wipe": 350, "slide": 300, "highlight": 400,
    "emphasis": 350, "reveal": 250,
}


class MotionDirector:
    """Builds the scene motion track from IR reveal + storyboard purposes."""

    @classmethod
    def direct(cls, slide: Dict[str, Any],
               animation_purposes: List[str] | None = None) -> Dict[str, Any]:
        reveal = [str(r) for r in slide.get("reveal_sequence", [])] or ["show"]
        purposes = list(animation_purposes or [])
        advance = []
        # One advance step per reveal item (after base): effect from the
        # step's purpose, falling back to the first purpose, then fade.
        for i in range(len(reveal)):
            purpose = purposes[i] if i < len(purposes) else (purposes[0] if purposes else "")
            effect = PURPOSE_TO_EFFECT.get(purpose, "fade")
            advance.append({"step": i + 1, "effect": effect,
                            "duration_ms": EFFECT_DURATION_MS[effect]})
        return {"enter_transition": "fade", "advance": advance}
