"""Semantic Motion Director — instructional movement only.

Every emitted animation answers "why should this move?". Purposes without an
instructional reason never become motion. Pure translation of IR reveal and
storyboard intent into declarative browser primitives; no pedagogy, no content.

Primitives (centralized — scenes never invent timings):
    fade, appear, wipe, slide, scale, highlight, pulse, path_motion,
    progressive_reveal, answer_reveal, diagram_reveal, state_transition

Timing tokens (restrained — objects never each animate independently):
    fast 180ms, normal 250ms, slow 400ms, process 600ms (journeys only)

Default scene transition: subtle fade. Related visual states persist spatially
(the browser only animates newly visible layers), giving continuity without
novelty effects. Bounce, spin, zoom and decoration are not representable here.
"""

from __future__ import annotations
from typing import Any, Dict, List

# Primitive → why it exists. Every advance step carries one of these reasons.
PRIMITIVES: Dict[str, str] = {
    "fade": "enter a supporting element without stealing focus",
    "appear": "progressive disclosure of the next idea",
    "wipe": "causal direction: this leads to that",
    "slide": "transformation: the same object changes state",
    "scale": "emphasize magnitude or importance once",
    "highlight": "direct attention for comparison",
    "pulse": "draw the eye to the active region, then stop",
    "path_motion": "a marker travels a real visual path (transport, gradient, loop)",
    "progressive_reveal": "build a derivation or structure piece by piece",
    "answer_reveal": "disclose the locked answer after thinking",
    "diagram_reveal": "light up the next diagram component in sequence",
    "state_transition": "move between scene states without rebuilding",
}

TIMING_TOKENS: Dict[str, int] = {
    "fast": 180,
    "normal": 250,
    "slow": 400,
    "process": 600,
}

# Atomic browser effects (what WAAPI executes) per primitive.
PRIMITIVE_EFFECT: Dict[str, str] = {
    "fade": "fade",
    "appear": "fade",
    "wipe": "wipe",
    "slide": "slide",
    "scale": "emphasis",
    "highlight": "highlight",
    "pulse": "highlight",
    "path_motion": "reveal",
    "progressive_reveal": "reveal",
    "answer_reveal": "reveal",
    "diagram_reveal": "highlight",
    "state_transition": "fade",
}

PRIMITIVE_DURATION: Dict[str, int] = {
    "fade": TIMING_TOKENS["normal"],
    "appear": TIMING_TOKENS["normal"],
    "wipe": TIMING_TOKENS["slow"],
    "slide": TIMING_TOKENS["normal"],
    "scale": TIMING_TOKENS["slow"],
    "highlight": TIMING_TOKENS["slow"],
    "pulse": TIMING_TOKENS["slow"],
    "path_motion": TIMING_TOKENS["process"],
    "progressive_reveal": TIMING_TOKENS["normal"],
    "answer_reveal": TIMING_TOKENS["normal"],
    "diagram_reveal": TIMING_TOKENS["slow"],
    "state_transition": TIMING_TOKENS["fast"],
}

# Storyboard/IR purpose → motion primitive (instructional reason preserved).
PURPOSE_TO_PRIMITIVE: Dict[str, str] = {
    "sequencing": "progressive_reveal",
    "signalling": "fade",
    "decomposition": "progressive_reveal",
    "reconstruction": "progressive_reveal",
    "transformation": "slide",
    "causal_explanation": "wipe",
    "comparison": "highlight",
    "highlighting": "highlight",
    "error_correction": "answer_reveal",
    "answer_reveal": "answer_reveal",
    "transport": "path_motion",
    "gradient": "path_motion",
    "diagram_reveal": "diagram_reveal",
    "emphasis": "scale",
    "pulse": "pulse",
}

# Back-compat: purpose → browser effect (as before, via primitive).
PURPOSE_TO_EFFECT: Dict[str, str] = {
    p: PRIMITIVE_EFFECT[prim] for p, prim in PURPOSE_TO_PRIMITIVE.items()
}
PURPOSE_TO_EFFECT.update({
    # legacy storyboard purposes keep their historical effects
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
})

EFFECT_DURATION_MS: Dict[str, int] = {
    "fade": TIMING_TOKENS["normal"],
    "wipe": TIMING_TOKENS["slow"],
    "slide": TIMING_TOKENS["normal"],
    "highlight": TIMING_TOKENS["slow"],
    "emphasis": TIMING_TOKENS["slow"],
    "reveal": TIMING_TOKENS["normal"],
}

_PATH_TASKS = {"mechanism", "process", "transport", "flow"}


class MotionDirector:
    """Builds the scene motion track from IR reveal + storyboard purposes.

    Each advance step declares what appears (targets), when (step order),
    what moves (effect), and why (instructional reason). Path journeys are
    described separately so the browser can move a marker along real geometry.
    """

    @classmethod
    def direct(cls, slide: Dict[str, Any],
               animation_purposes: List[str] | None = None,
               layers: List[Dict[str, Any]] | None = None,
               states: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        reveal = [str(r) for r in slide.get("reveal_sequence", [])] or ["show"]
        purposes = list(animation_purposes or [])
        task = str(slide.get("task", "")).lower()
        rep = str(slide.get("representation", ""))
        advance = []
        for i in range(len(reveal)):
            purpose = purposes[i] if i < len(purposes) else (purposes[0] if purposes else "")
            primitive = PURPOSE_TO_PRIMITIVE.get(purpose, "appear")
            effect = PRIMITIVE_EFFECT[primitive]
            targets = cls._targets_for_step(layers or [], states or [], i + 1)
            advance.append({
                "step": i + 1,
                "primitive": primitive,
                "effect": effect,
                "duration_ms": PRIMITIVE_DURATION[primitive],
                "targets": targets,
                "why": PRIMITIVES[primitive],
            })
        motion: Dict[str, Any] = {"enter_transition": "fade", "advance": advance}
        paths = cls._paths_for_slide(slide, task, rep)
        if paths:
            motion["paths"] = paths
        return motion

    @staticmethod
    def _targets_for_step(layers: List[Dict[str, Any]],
                          states: List[Dict[str, Any]],
                          step: int) -> List[str]:
        """Layer ids first visible exactly at this state (no independent extras)."""
        if not states or step >= len(states) or step <= 0:
            return []
        now = set(states[step].get("visible_layers", []))
        prev = set(states[step - 1].get("visible_layers", []))
        return sorted(now - prev)

    @staticmethod
    def _labels_of(slide: Dict[str, Any]) -> List[str]:
        visual = slide.get("visual", {}) or {}
        out = []
        for lab in visual.get("labels", []) or []:
            name = lab if isinstance(lab, str) else (lab.get("name", "") or "")
            if str(name).strip():
                out.append(str(name).strip())
        return out[:6]

    @classmethod
    def _paths_for_slide(cls, slide: Dict[str, Any], task: str, rep: str) -> List[Dict[str, Any]]:
        """Journey descriptors the browser executes along rendered geometry.

        Waypoints are real label names from the IR visual spec — the browser
        resolves them to on-screen anchors at runtime. Nothing is invented:
        no waypoints, no path.
        """
        labels = cls._labels_of(slide)
        visual = slide.get("visual", {}) or {}
        if rep == "cycle" and labels and len(labels) >= 2:
            return [{"kind": "loop", "via": labels,
                     "duration_ms": TIMING_TOKENS["process"],
                     "why": "follow the cycle around, returning to start"}]
        if "gradient" in str(visual.get("gradient", "")).lower() or "gradient" in task:
            if len(labels) >= 2:
                return [{"kind": "gradient", "via": labels,
                         "duration_ms": TIMING_TOKENS["process"],
                         "why": "accumulation becomes movement becomes production"}]
            return []
        if task in _PATH_TASKS and len(labels) >= 2:
            return [{"kind": "transit", "via": labels,
                     "duration_ms": TIMING_TOKENS["process"],
                     "why": "a carrier visibly travels the mechanism step by step"}]
        return []
