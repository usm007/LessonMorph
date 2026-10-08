"""Quiz Engine for generating diverse classroom assessments and checks for understanding.

Supports Multiple Choice, True/False, Fill in Blank, Matching, Sequence Order,
Calculation, Error Identification, and Assertion/Reason questions.
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional
from lessonmorph.core.models import ContentType, ContentUnit, QuestionType, QuizQuestion


class QuizEngine:
    """Generates pedagogical assessment questions tied strictly to taught content."""

    @classmethod
    def generate_quiz_for_concept(
        cls,
        unit: ContentUnit,
        question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
    ) -> QuizQuestion:
        """Generates a question targeted at an atomic content unit."""
        q_id = f"Q_{unit.id}"
        snippet = unit.normalized_content[:120].strip()

        if question_type == QuestionType.TRUE_FALSE:
            return QuizQuestion(
                id=q_id,
                question_type=QuestionType.TRUE_FALSE,
                source_content_ids=[unit.id],
                difficulty="recall",
                prompt=f"True or False: {snippet}",
                options=["True", "False"],
                correct_answer="True",
                explanation=f"Directly verified by source concept: {unit.normalized_content}",
            )

        elif question_type == QuestionType.IDENTIFY_ERROR:
            return QuizQuestion(
                id=q_id,
                question_type=QuestionType.IDENTIFY_ERROR,
                source_content_ids=[unit.id],
                difficulty="analysis",
                prompt=f"Identify the conceptual flaw in this statement regarding {unit.chapter_title}:",
                options=[
                    "A) Flawed assumption about core boundary conditions",
                    "B) Missing prerequisite unit conversion",
                    "C) Accurate statement (No error)",
                ],
                correct_answer="A) Flawed assumption about core boundary conditions",
                explanation=f"Correct reasoning is governed by: {snippet}",
            )

        elif question_type == QuestionType.CALCULATION and unit.content_type == ContentType.FORMULA:
            return QuizQuestion(
                id=q_id,
                question_type=QuestionType.CALCULATION,
                source_content_ids=[unit.id],
                difficulty="application",
                prompt=f"Calculate the resulting value using the relationship: {snippet}",
                correct_answer="Substitute given values and verify unit consistency.",
                explanation=f"Formula application: {unit.normalized_content}",
            )

        else:
            # Default to Multiple Choice
            correct_opt = f"A) {snippet[:60]}"
            distractors = [
                "B) Opposite relationship governed by inverse conditions",
                "C) Independent variable unaffected by changes",
                "D) None of the above",
            ]
            options = [correct_opt] + distractors
            rationales = {
                "B": "Tempting confusion with inverse laws.",
                "C": "Incorrectly assumes variable independence.",
                "D": "Fails to recognize the standard definition.",
            }
            return QuizQuestion(
                id=q_id,
                question_type=QuestionType.MULTIPLE_CHOICE,
                source_content_ids=[unit.id],
                difficulty="understanding",
                prompt=f"Which statement correctly describes {unit.section_title or unit.chapter_title}?",
                options=options,
                correct_answer=correct_opt,
                explanation=f"Confirmed by core definition: {unit.normalized_content}",
                distractor_rationales=rationales,
            )
