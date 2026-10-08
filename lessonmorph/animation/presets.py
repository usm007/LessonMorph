"""Animation presets and timing definitions."""

from dataclasses import dataclass
from typing import Optional
from lessonmorph.core.models import AnimationType


@dataclass
class AnimationPreset:
    name: str
    action: AnimationType
    duration_ms: int = 500
    filter_effect: str = "fade"  # fade, wipe, fly, box
    transition_direction: str = "in"  # in, out
    trigger_delay_ms: int = 0


PRESETS = {
    AnimationType.APPEAR: AnimationPreset(
        name="appear",
        action=AnimationType.APPEAR,
        duration_ms=400,
        filter_effect="fade",
        transition_direction="in",
    ),
    AnimationType.FADE: AnimationPreset(
        name="fade",
        action=AnimationType.FADE,
        duration_ms=600,
        filter_effect="fade",
        transition_direction="in",
    ),
    AnimationType.ANSWER_REVEAL: AnimationPreset(
        name="answer_reveal",
        action=AnimationType.ANSWER_REVEAL,
        duration_ms=500,
        filter_effect="fade",
        transition_direction="in",
    ),
    AnimationType.CROSS_OUT: AnimationPreset(
        name="cross_out",
        action=AnimationType.CROSS_OUT,
        duration_ms=400,
        filter_effect="wipe",
        transition_direction="in",
    ),
    AnimationType.HIGHLIGHT: AnimationPreset(
        name="highlight",
        action=AnimationType.HIGHLIGHT,
        duration_ms=400,
        filter_effect="fade",
        transition_direction="in",
    ),
}
