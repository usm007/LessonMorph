"""Pedagogical lesson planner (intelligence layer).

Orchestrates: learner profile -> backward-designed objectives ->
prerequisites/dependencies -> content-nature profile -> strategy selection ->
adaptive teaching sequence -> scaffolding/retrieval/assessment/pacing.

Produces a machine-readable, testable PedagogicalPlan attached to the
ChapterPlan. Inspect `plan.pedagogical_plan` (or work/pedagogical_plan.json)
BEFORE rendering — a reviewer must be able to answer: what must students
learn, what must they know first, why is each concept/example/question here,
where retrieval/guided/independent practice happens, which misconception is
addressed, how support fades, and how objectives are assessed.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from lessonmorph.core.models import (
    ChapterPlan,
    ContentImportance,
    ContentType,
    ContentUnit,
    DocumentSection,
    LearnerProfile,
    PedagogicalPlan,
    QuestionType,
    QuizQuestion,
    SubjectDomain,
)
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.learner import infer_learner_profile
from lessonmorph.pedagogy.misconceptions import MisconceptionDetector, StructuredMisconception
from lessonmorph.pedagogy.pacing import PacingCalculator
from lessonmorph.pedagogy.quality import safety_check
from lessonmorph.pedagogy.sequencing import build_teaching_sequence
from lessonmorph.pedagogy.strategies import (
    build_dependency_chain,
    profile_content,
    select_strategies,
    synthesize_objectives,
)


class PedagogicalPlanner:
    """Plans complete lesson structure from source sections and content ledger."""

    def __init__(self, ledger: ContentCompletenessLedger,
                 learner_hint: Optional[Dict[str, Any]] = None):
        self.ledger = ledger
        self.learner_hint = learner_hint or {}

    def plan_chapter(self, section: DocumentSection) -> ChapterPlan:
        units = self.ledger.get_units_by_chapter(section.id)
        if not units:
            units = self.ledger.units

        full_text = " ".join([u.normalized_content for u in units])
        domain = SubjectClassifier.classify_domain(full_text)
        learner = infer_learner_profile(full_text, self.learner_hint)

        # Backward design: observable objectives bound to teaching content.
        content_profile = profile_content(units)
        objectives = synthesize_objectives(units, section.title, content_profile)

        # Prior knowledge + dependency chain (no hidden prerequisites).
        prior_knowledge = self._extract_prior_knowledge(units, domain)
        core_concepts = [
            u.normalized_content[:80]
            for u in units
            if u.content_type in (ContentType.DEFINITION, ContentType.FORMULA)
        ] or [f"Foundations of {section.title}"]
        dependencies = build_dependency_chain(prior_knowledge, core_concepts)

        # Strategy: goal + content + learner -> decision principles (no recipe).
        strategies = select_strategies(domain, content_profile, learner)

        # Misconceptions (source-first, domain-grounded fallback).
        detected = MisconceptionDetector.extract_from_content(units)
        if not detected:
            detected = MisconceptionDetector.get_domain_misconceptions(domain, section.title)
        misconception_dicts = [
            {"topic": m.topic, "wrong_idea": m.wrong_idea, "why_wrong": m.why_wrong,
             "correct_idea": m.correct_idea, "correct_reasoning": m.correct_reasoning,
             "source_unit_id": m.source_unit_id or ""}
            for m in detected
        ]

        # Adaptive teaching sequence (instructional states, not slide titles).
        sequence = build_teaching_sequence(
            units, objectives, content_profile, strategies, domain, len(detected))

        # Worked examples: full problem -> reasoning steps -> verification.
        worked_examples = self._extract_worked_examples(units)

        # Assessment downstream of objectives (O -> Q mapping comes after Q synthesis).
        questions = self._synthesize_questions(units, section.id)
        self._ensure_objective_coverage(questions, objectives, units)
        self._align_questions_to_objectives(questions, objectives, units)

        assessment_map: Dict[str, List[str]] = {o.id: [] for o in objectives}
        for q in questions:
            for oid in q.objective_ids:
                assessment_map.setdefault(oid, []).append(q.id)

        retrieval_plan = [
            f"{i+1}. {m.state}: {m.purpose}" for i, m in enumerate(sequence)
            if m.state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL", "ASSESSMENT")]
        scaffolding = self._scaffolding_plan(strategies, bool(worked_examples))
        practice = self._practice_plan(section.title, worked_examples, learner)

        ped_plan = PedagogicalPlan(
            chapter_id=section.id, chapter_title=section.title,
            subject_domain=domain.value, learner_profile=learner,
            learning_objectives=objectives, prerequisites=prior_knowledge,
            concept_dependencies=dependencies, content_types=content_profile,
            pedagogical_strategies=strategies, teaching_sequence=sequence,
            scaffolding_plan=scaffolding, retrieval_plan=retrieval_plan,
            assessment_map=assessment_map, misconceptions=misconception_dicts,
            worked_examples=worked_examples, practice_plan=practice,
            pacing_notes=self._pacing_notes(sequence, learner),
        )
        ped_plan.safety_warnings = safety_check(ped_plan, questions)

        plan = ChapterPlan(
            id=section.id, title=section.title,
            source_start_page=section.start_page, source_end_page=section.end_page,
            estimated_time_minutes=learner.lesson_duration_minutes,
            subject_domain=domain,
            learning_objectives=[o.text for o in objectives],
            prior_knowledge=prior_knowledge, core_concepts=core_concepts,
            misconceptions=misconception_dicts, slides=[], questions=questions,
            pedagogical_plan=ped_plan,
        )
        return plan

    # -- scaffolding / pacing -------------------------------------------------
    def _scaffolding_plan(self, strategies: List[str], has_worked: bool) -> List[str]:
        if "worked_example" in strategies or "gradual_release" in strategies or has_worked:
            return ["I DO: teacher models the full reasoning",
                    "WE DO: partially completed example with fading support",
                    "YOU DO TOGETHER: guided practice with peer/teacher support",
                    "YOU DO: independent novel application"]
        return ["I DO: teacher models the concept",
                "WE DO: reason through an example together",
                "YOU DO: independent application"]

    def _practice_plan(self, title: str, worked: List[Dict], learner: LearnerProfile) -> List[str]:
        depth = "with full reasoning steps" if learner.level in ("undergraduate", "high_school") else "in your own words"
        items = [f"Explain the fundamental principles of {title} {depth}.",
                 "Solve a multi-step application using the core relations discussed."]
        if worked:
            items.append("Complete the faded worked example (fill the missing step, then verify).")
        items.append("Explain why the addressed misconception is incorrect.")
        return items

    def _pacing_notes(self, sequence, learner: LearnerProfile) -> str:
        high = sum(1 for m in sequence if m.complexity == "high")
        base = learner.lesson_duration_minutes
        return (f"~{base} min budget; {high} high-complexity move(s) get smaller chunks "
                "and extra checks; factual sections progress faster; procedural sections "
                "reserve time for worked examples and practice.")

    def _ensure_objective_coverage(self, questions: List[QuizQuestion],
                                     objectives, units: List[ContentUnit]) -> None:
        """Constructive alignment: every objective gets >= 1 assessment item."""
        by_unit = {u.id: u for u in units}
        covered: set = set()
        for q in questions:
            for cid in q.source_content_ids:
                covered.add(cid)
        n = len(questions) + 1
        for o in objectives:
            if any(cid in covered for cid in o.content_ids):
                continue
            cid = next((c for c in o.content_ids if c in by_unit), None)
            if cid is None:
                continue
            u = by_unit[cid]
            snippet = u.normalized_content[:110]
            questions.append(QuizQuestion(
                id=f"Q{n:02d}", question_type=QuestionType.SHORT_ANSWER,
                source_content_ids=[cid], difficulty=o.bloom_level,
                prompt=f"{o.verb.capitalize()} ({o.id}): {snippet}",
                correct_answer="See explanation and source reasoning.",
                explanation=f"Aligned to {o.id} ({o.verb}/{o.bloom_level}): {u.normalized_content[:200]}",
            ))
            covered.add(cid)
            n += 1

    def _align_questions_to_objectives(self, questions: List[QuizQuestion],
                                       objectives, units: List[ContentUnit]) -> None:
        by_unit: Dict[str, List[str]] = {}
        for o in objectives:
            for cid in o.content_ids:
                by_unit.setdefault(cid, []).append(o.id)
        fallback = [o.id for o in objectives[:2]] or [o.id for o in objectives[:1]]
        for q in questions:
            oids: List[str] = []
            for cid in q.source_content_ids:
                oids += by_unit.get(cid, [])
            q.objective_ids = list(dict.fromkeys(oids)) or list(fallback)

    def _extract_worked_examples(self, units: List[ContentUnit]) -> List[Dict]:
        out: List[Dict] = []
        i = 0
        while i < len(units):
            u = units[i]
            if u.content_type in (ContentType.EXAMPLE, ContentType.WORKED_STEP):
                steps = [u.normalized_content] if u.content_type == ContentType.WORKED_STEP else []
                problem = u.normalized_content if u.content_type == ContentType.EXAMPLE else "Worked Problem"
                ids = [u.id]
                j = i + 1
                while j < len(units) and units[j].content_type == ContentType.WORKED_STEP:
                    steps.append(units[j].normalized_content)
                    ids.append(units[j].id)
                    j += 1
                out.append({"problem": problem[:200], "steps": [s[:200] for s in steps[:8]],
                            "content_ids": ids, "verify": "check units, boundary conditions, and result"})
                i = j
            else:
                i += 1
        return out

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
                        explanation="Direct application of source exercise.",
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
