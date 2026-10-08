"""Learner profile inference (cautious defaults, never invented specifics)."""

from __future__ import annotations
from typing import Any, Dict, Optional
from lessonmorph.core.models import LearnerProfile


LEVEL_HINTS = ("middle_school", "high_school", "undergraduate", "graduate", "primary", "general")


def infer_learner_profile(
    source_text: str = "",
    hint: Optional[Dict[str, Any]] = None,
) -> LearnerProfile:
    """Build a LearnerProfile from an optional user hint.

    When no hint is given, infer cautiously from the source and use reasonable
    defaults. Never invents highly specific learner characteristics.
    """
    hint = hint or {}
    text = (source_text or "").lower()

    def _str(*keys: str, default: str = "") -> str:
        for k in keys:
            v = hint.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return default

    level = _str("level", "academic_level", default="")
    if level not in LEVEL_HINTS:
        # Cautious inference: advanced vocabulary -> undergraduate, else general.
        advanced = sum(1 for w in ("theorem", "stoichiometry", "eigen", "thermodynamics",
                                   "epistemology", "photosynthesis") if w in text)
        level = "undergraduate" if advanced >= 2 else "general"

    try:
        duration = int(hint.get("lesson_duration_minutes", hint.get("duration_min", 45)) or 45)
    except (TypeError, ValueError):
        duration = 45
    duration = max(15, min(180, duration))

    supplied = any(hint.get(k) for k in ("grade", "level", "academic_level", "age_range",
                                         "curriculum", "language", "exam_orientation"))
    return LearnerProfile(
        grade=_str("grade", "class"),
        age_range=_str("age_range", "age"),
        level=level,
        prior_knowledge=_str("prior_knowledge"),
        curriculum=_str("curriculum", "board"),
        lesson_duration_minutes=duration,
        language=_str("language", default="en") or "en",
        exam_orientation=_str("exam_orientation", "exam"),
        inferred=not supplied,
    )
