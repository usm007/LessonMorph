"""Lesson pacing and duration estimator.

Estimates realistic classroom teaching duration based on slide types,
interactive checks, worked calculation steps, and discussion pauses.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from lessonmorph.core.models import SlideSpec, SlideType


@dataclass
class LessonPacingEstimate:
    total_minutes: int
    breakdown_minutes: Dict[str, int] = field(default_factory=dict)
    pacing_notes: str = ""


class PacingCalculator:
    """Calculates granular classroom teaching time."""

    # Default baseline minutes by slide type
    TYPE_PACE: Dict[SlideType, float] = {
        SlideType.TITLE: 1.0,
        SlideType.ROADMAP: 1.5,
        SlideType.LEARNING_OBJECTIVES: 2.0,
        SlideType.PRIOR_KNOWLEDGE: 2.5,
        SlideType.CONCEPT_DEFINITION: 2.5,
        SlideType.PROCESS_FLOW: 3.0,
        SlideType.COMPARISON: 3.0,
        SlideType.WORKED_EXAMPLE: 4.0,
        SlideType.COMMON_MISCONCEPTION: 3.0,
        SlideType.FORMULA_BREAKDOWN: 3.5,
        SlideType.CLASSIFICATION_GRID: 3.0,
        SlideType.CAUSE_EFFECT: 3.0,
        SlideType.TIMELINE: 3.0,
        SlideType.TABLE_DISPLAY: 2.5,
        SlideType.DIAGRAM_EXPLANATION: 3.5,
        SlideType.QUIZ_QUESTION: 2.0,
        SlideType.QUIZ_REVEAL: 1.5,
        SlideType.SUMMARY_RECAP: 2.5,
        SlideType.PRACTICE_SET: 4.0,
        SlideType.EXAM_STYLE: 4.0,
        SlideType.EXIT_TICKET: 2.0,
    }

    @classmethod
    def estimate_slide(cls, slide: SlideSpec) -> float:
        base = cls.TYPE_PACE.get(slide.slide_type, 2.0)
        # Add time for animation steps and interactive discussion
        if slide.animation_steps:
            base += len(slide.animation_steps) * 0.3
        if slide.quiz:
            base += 1.0
        return round(base, 1)

    @classmethod
    def estimate_chapter_pacing(cls, slides: List[SlideSpec]) -> LessonPacingEstimate:
        categories = {
            "Introduction & Objectives": 0.0,
            "Core Concept Teaching": 0.0,
            "Worked Examples & Applications": 0.0,
            "Classroom Checks & Quizzes": 0.0,
            "Practice & Exam Questions": 0.0,
            "Recap & Exit Ticket": 0.0,
        }

        for s in slides:
            mins = s.estimated_time_minutes or cls.estimate_slide(s)
            st = s.slide_type
            if st in (SlideType.TITLE, SlideType.ROADMAP, SlideType.LEARNING_OBJECTIVES, SlideType.PRIOR_KNOWLEDGE):
                categories["Introduction & Objectives"] += mins
            elif st in (SlideType.CONCEPT_DEFINITION, SlideType.PROCESS_FLOW, SlideType.COMPARISON,
                        SlideType.FORMULA_BREAKDOWN, SlideType.CLASSIFICATION_GRID, SlideType.DIAGRAM_EXPLANATION,
                        SlideType.TABLE_DISPLAY, SlideType.CAUSE_EFFECT, SlideType.TIMELINE):
                categories["Core Concept Teaching"] += mins
            elif st in (SlideType.WORKED_EXAMPLE, SlideType.COMMON_MISCONCEPTION):
                categories["Worked Examples & Applications"] += mins
            elif st in (SlideType.QUIZ_QUESTION, SlideType.QUIZ_REVEAL):
                categories["Classroom Checks & Quizzes"] += mins
            elif st in (SlideType.PRACTICE_SET, SlideType.EXAM_STYLE):
                categories["Practice & Exam Questions"] += mins
            elif st in (SlideType.SUMMARY_RECAP, SlideType.EXIT_TICKET):
                categories["Recap & Exit Ticket"] += mins
            else:
                categories["Core Concept Teaching"] += mins

        rounded_breakdown = {k: max(1, round(v)) for k, v in categories.items() if v > 0}
        total = sum(rounded_breakdown.values())

        pacing_summary = ", ".join([f"{k}: {v} min" for k, v in rounded_breakdown.items()])
        notes = f"Estimated lesson duration: {total} minutes ({pacing_summary})."

        return LessonPacingEstimate(
            total_minutes=total,
            breakdown_minutes=rounded_breakdown,
            pacing_notes=notes,
        )
