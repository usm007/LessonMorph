"""Pedagogical lesson planner.

Synthesizes atomic content units into an instructional sequence designed for
classroom delivery, ensuring pedagogical flow, subject-aware models, and 100% coverage.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from lessonmorph.core.models import (
    ChapterPlan,
    ContentImportance,
    ContentType,
    ContentUnit,
    DocumentSection,
    QuestionType,
    QuizQuestion,
    SlideType,
    SubjectDomain,
)
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.misconceptions import MisconceptionDetector, StructuredMisconception
from lessonmorph.pedagogy.pacing import PacingCalculator


class PedagogicalPlanner:
    """Plans complete lesson structure from source sections and content ledger."""

    def __init__(self, ledger: ContentCompletenessLedger):
        self.ledger = ledger

    def plan_chapter(self, section: DocumentSection) -> ChapterPlan:
        units = self.ledger.get_units_by_chapter(section.id)
        if not units:
            units = self.ledger.units

        full_text = " ".join([u.normalized_content for u in units])
        domain = SubjectClassifier.classify_domain(full_text)

        # 1. Synthesize Learning Objectives
        objectives = self._extract_objectives(units, section.title)

        # 2. Extract Prior Knowledge prerequisites
        prior_knowledge = self._extract_prior_knowledge(units, domain)

        # 3. Extract Core Concepts
        core_concepts = [
            u.normalized_content[:80]
            for u in units
            if u.content_type in (ContentType.DEFINITION, ContentType.FORMULA)
        ]
        if not core_concepts:
            core_concepts = [f"Foundations of {section.title}"]

        # 4. Extract Misconceptions
        detected_misconceptions = MisconceptionDetector.extract_from_content(units)
        if not detected_misconceptions:
            detected_misconceptions = MisconceptionDetector.get_domain_misconceptions(domain, section.title)

        # Convert to dict representation
        misconception_dicts = [
            {
                "topic": m.topic,
                "wrong_idea": m.wrong_idea,
                "why_wrong": m.why_wrong,
                "correct_idea": m.correct_idea,
                "correct_reasoning": m.correct_reasoning,
                "source_unit_id": m.source_unit_id,
            }
            for m in detected_misconceptions
        ]

        # 5. Build Initial Questions (from exercises or synthesized checks)
        questions = self._synthesize_questions(units, section.id)

        plan = ChapterPlan(
            id=section.id,
            title=section.title,
            source_start_page=section.start_page,
            source_end_page=section.end_page,
            estimated_time_minutes=45,
            subject_domain=domain,
            learning_objectives=objectives,
            prior_knowledge=prior_knowledge,
            core_concepts=core_concepts,
            misconceptions=misconception_dicts,
            slides=[],
            questions=questions,
        )

        return plan

    def _extract_objectives(self, units: List[ContentUnit], title: str) -> List[str]:
        # Look for explicit objectives in text
        for u in units:
            text = u.normalized_content
            if "objective" in text.lower() or "you will learn" in text.lower():
                lines = [l.strip("- *0123456789.") for l in text.splitlines() if l.strip()]
                clean_objs = [l for l in lines if len(l) > 10 and not "objective" in l.lower()][:4]
                if clean_objs:
                    return clean_objs

        # Synthesize standard educational Bloom's taxonomy objectives
        defs = [u for u in units if u.content_type == ContentType.DEFINITION]
        formulas = [u for u in units if u.content_type == ContentType.FORMULA]
        examples = [u for u in units if u.content_type in (ContentType.EXAMPLE, ContentType.WORKED_STEP)]

        objs = [f"Define and explain key concepts in {title}."]
        if formulas:
            objs.append(f"Apply fundamental formulas and laws accurately.")
        if examples:
            objs.append(f"Solve multi-step problems and analyze concrete applications.")
        objs.append(f"Identify and avoid common pitfalls and misconceptions.")
        return objs

    def _extract_prior_knowledge(self, units: List[ContentUnit], domain: SubjectDomain) -> List[str]:
        for u in units:
            text = u.normalized_content
            if "prerequisite" in text.lower() or "recall" in text.lower() or "prior knowledge" in text.lower():
                lines = [l.strip("- *0123456789.") for l in text.splitlines() if l.strip()]
                clean = [l for l in lines if len(l) > 10 and "recall" not in l.lower()][:3]
                if clean:
                    return clean

        domain_defaults = {
            SubjectDomain.MATHEMATICS: [
                "Basic arithmetic operations and order of operations",
                "Algebraic substitution and variable manipulation",
            ],
            SubjectDomain.PHYSICS: [
                "Standard SI units (meters, seconds, kilograms)",
                "Basic vector addition and scalar quantities",
            ],
            SubjectDomain.CHEMISTRY: [
                "Atomic structure (protons, neutrons, electrons)",
                "Conservation of mass in reactions",
            ],
            SubjectDomain.BIOLOGY: [
                "Cell theory fundamentals",
                "Basic energy conversion principles",
            ],
            SubjectDomain.HISTORY: [
                "Chronological sequence of major historical eras",
                "Distinction between primary and secondary sources",
            ],
        }
        return domain_defaults.get(domain, [
            "Foundational vocabulary and definitions",
            "General conceptual principles introduced in previous modules",
        ])

    def _synthesize_questions(self, units: List[ContentUnit], chapter_id: str) -> List[QuizQuestion]:
        questions: List[QuizQuestion] = []
        q_counter = 1

        # Check for explicit source exercises
        exercise_units = [u for u in units if u.content_type == ContentType.EXERCISE]
        for eu in exercise_units:
            text = eu.normalized_content
            # Check if MCQ options exist
            mcq_match = re.findall(r"([A-D]\))\s*([^\n]+)", text)
            if mcq_match:
                prompt_line = text.splitlines()[0]
                options = [f"{letter} {opt.strip()}" for letter, opt in mcq_match]
                correct = options[0]  # default fallback if not specified
                questions.append(
                    QuizQuestion(
                        id=f"Q{q_counter:02d}",
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        source_content_ids=[eu.id],
                        difficulty="application",
                        prompt=prompt_line,
                        options=options,
                        correct_answer=correct,
                        explanation=f"Direct application of source exercise.",
                    )
                )
                q_counter += 1
            else:
                questions.append(
                    QuizQuestion(
                        id=f"Q{q_counter:02d}",
                        question_type=QuestionType.SHORT_ANSWER,
                        source_content_ids=[eu.id],
                        difficulty="understanding",
                        prompt=text[:140],
                        correct_answer="See worked explanation and step guidelines.",
                        explanation=text,
                    )
                )
                q_counter += 1

        # If few or no exercises in source, synthesize quick checks from definitions and formulas
        if len(questions) < 3:
            defs = [u for u in units if u.content_type == ContentType.DEFINITION]
            for du in defs[:2]:
                snippet = du.normalized_content[:90]
                questions.append(
                    QuizQuestion(
                        id=f"Q{q_counter:02d}",
                        question_type=QuestionType.TRUE_FALSE,
                        source_content_ids=[du.id],
                        difficulty="recall",
                        prompt=f"True or False: {snippet}",
                        options=["True", "False"],
                        correct_answer="True",
                        explanation=f"Based on the core definition: '{snippet}'.",
                    )
                )
                q_counter += 1

        return questions
