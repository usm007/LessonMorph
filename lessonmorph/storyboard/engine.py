"""Storyboard Engine: transforms pedagogical plans and content atoms into detailed slide specifications.

Creates a machine-readable storyboard with 100% source coverage mapping,
visual model selection, native animation steps, two-stage quiz reveals, and teacher speaker notes.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from lessonmorph.core.models import (
    AnimationStep,
    AnimationType,
    ChapterPlan,
    ContentType,
    ContentUnit,
    QuestionType,
    QuizQuestion,
    SlideSpec,
    SlideType,
    SpeakerNotes,
    SubjectDomain,
)
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.pacing import PacingCalculator


class StoryboardEngine:
    """Generates structured slide specifications from pedagogical chapter plans."""

    def __init__(self, ledger: ContentCompletenessLedger):
        self.ledger = ledger
        self._slide_counter = 0

    def generate_deck(self, plans: List[ChapterPlan]) -> List[SlideSpec]:
        """Generates a full multi-chapter deck with dividers and a contents slide.

        Preserves 100% coverage: every chapter's ledger units are mapped.
        Single-chapter decks skip dividers/contents to keep classroom flow tight.
        """
        self._slide_counter = 0
        if len(plans) <= 1:
            return self.generate_storyboard(plans[0]) if plans else []
        deck: List[SlideSpec] = []
        # Global contents slide
        deck.append(self._build_contents_slide([p.title for p in plans]))
        for plan in plans:
            deck.append(self._build_chapter_divider(plan))
            # Generate chapter slides with shared counter (no reset)
            chapter_slides = self._generate_chapter_slides(plan)
            deck.extend(chapter_slides)
        # Recalculate pacing across full deck
        total = sum(p.estimated_time_minutes for p in plans)
        for p in plans:
            p.estimated_time_minutes = total
        return deck

    def _generate_chapter_slides(self, plan: ChapterPlan) -> List[SlideSpec]:
        """Chapter slides without resetting the global slide counter (for decks)."""
        slides: List[SlideSpec] = []
        slides.append(self._build_title_slide(plan))
        slides.append(self._build_roadmap_slide(plan))
        slides.append(self._build_objectives_slide(plan))
        if plan.prior_knowledge:
            slides.append(self._build_prior_knowledge_slide(plan))
        content_units = self.ledger.get_units_by_chapter(plan.id)
        if not content_units:
            content_units = self.ledger.units
        slides.extend(self._build_core_content_slides(plan, content_units))
        if plan.misconceptions:
            slides.extend(self._build_misconception_slides(plan))
        if plan.questions:
            for q in plan.questions:
                q_slide, reveal_slide = self._build_quiz_pair(plan, q)
                slides.append(q_slide)
                slides.append(reveal_slide)
        slides.append(self._build_summary_slide(plan))
        slides.append(self._build_practice_slide(plan))
        slides.append(self._build_exit_ticket_slide(plan))
        plan.slides = slides
        pacing = PacingCalculator.estimate_chapter_pacing(slides)
        plan.estimated_time_minutes = pacing.total_minutes
        return slides

    def build_contents_slide(self, titles: List[str]) -> SlideSpec:
        return self._build_contents_slide(titles)

    def build_chapter_divider(self, plan: ChapterPlan) -> SlideSpec:
        return self._build_chapter_divider(plan)

    def _build_contents_slide(self, titles: List[str]) -> SlideSpec:
        sid = self._next_slide_id()
        return SlideSpec(
            slide_id=sid,
            chapter_id="deck",
            title="Contents",
            subtitle="What we will teach in this deck",
            purpose="Provide deck-level navigation across chapters.",
            source_content_ids=[],
            slide_type=SlideType.ROADMAP,
            visual_model="contents",
            elements_data={"entries": titles},
            speaker_notes=SpeakerNotes(
                teacher_explanation="Preview the chapters so students see the full journey.",
                transition="Let's begin with our first chapter.",
            ),
            estimated_time_minutes=1.0,
        )

    def _build_chapter_divider(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title=plan.title,
            subtitle=f"Chapter • {plan.subject_domain.value.title()}",
            purpose="Mark chapter boundary for navigation.",
            source_content_ids=[],
            slide_type=SlideType.TITLE,
            visual_model="chapter_divider",
            elements_data={"detail": f"Pages {plan.source_start_page}–{plan.source_end_page} • ~{plan.estimated_time_minutes} min"},
            speaker_notes=SpeakerNotes(
                teacher_explanation=f"Introduce chapter: {plan.title}.",
                transition="Let's look at what we will master in this chapter.",
            ),
            estimated_time_minutes=0.5,
        )

    def generate_storyboard(self, plan: ChapterPlan) -> List[SlideSpec]:
        """Generates the full ordered sequence of slides for a chapter."""
        self._slide_counter = 0
        slides: List[SlideSpec] = []
        # 1. Title Slide
        slides.append(self._build_title_slide(plan))

        # 2. Roadmap / Why this matters
        slides.append(self._build_roadmap_slide(plan))

        # 3. Learning Objectives
        slides.append(self._build_objectives_slide(plan))

        # 4. Prior Knowledge / Warm-Up
        if plan.prior_knowledge:
            slides.append(self._build_prior_knowledge_slide(plan))

        # 5. Core Content Slides (Definitions, Concepts, Formulas, Tables, Diagrams)
        content_units = self.ledger.get_units_by_chapter(plan.id)
        if not content_units:
            content_units = self.ledger.units

        slides.extend(self._build_core_content_slides(plan, content_units))

        # 6. Common Misconceptions
        if plan.misconceptions:
            slides.extend(self._build_misconception_slides(plan))

        # 7. Check for Understanding (Interactive Quizzes with 2-stage classroom reveals)
        if plan.questions:
            for q in plan.questions:
                # Stage A: Question Prompt
                q_slide, reveal_slide = self._build_quiz_pair(plan, q)
                slides.append(q_slide)
                slides.append(reveal_slide)

        # 8. Summary / Key Takeaways Recap
        slides.append(self._build_summary_slide(plan))

        # 9. Practice & Exam-Style Questions
        slides.append(self._build_practice_slide(plan))

        # 10. Exit Ticket / Reflection
        slides.append(self._build_exit_ticket_slide(plan))

        # Update chapter plan and recalculate pacing
        plan.slides = slides
        pacing = PacingCalculator.estimate_chapter_pacing(slides)
        plan.estimated_time_minutes = pacing.total_minutes

        return slides

    def _next_slide_id(self) -> str:
        self._slide_counter += 1
        return f"S{self._slide_counter:03d}"

    def _build_title_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        notes = SpeakerNotes(
            teacher_explanation=f"Welcome students to {plan.title}. Today we establish a deep conceptual and practical mastery of this topic.",
            emphasis=f"Focus on fundamental definitions and principles first before moving to problem solving.",
            ask_students=f"What comes to your mind when you hear the term '{plan.title}'?",
            transition="Let's look at our roadmap for today's lesson.",
        )
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title=plan.title,
            subtitle=f"{plan.subject_domain.value.title()} • Classroom Presentation",
            purpose="Introduce topic, create engagement, and set classroom expectations.",
            source_content_ids=[],
            slide_type=SlideType.TITLE,
            visual_model="hero_title",
            elements_data={
                "unit_title": plan.subject_domain.value.upper(),
                "topic": plan.title,
                "badge": "Classroom Ready",
            },
            speaker_notes=notes,
            estimated_time_minutes=1.5,
        )

    def _build_roadmap_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        roadmap_stages = [
            {"step": "01", "name": "Foundations", "desc": "Definitions & Core Laws"},
            {"step": "02", "name": "Visual Model", "desc": "Mechanisms & Diagrams"},
            {"step": "03", "name": "Worked Examples", "desc": "Step-by-step Mastery"},
            {"step": "04", "name": "Checks & Practice", "desc": "Misconceptions & Exam Prep"},
        ]
        notes = SpeakerNotes(
            teacher_explanation="Walk students through the roadmap so they see how today's ideas connect logically.",
            emphasis="Every concept builds directly upon the previous one.",
            transition="Let's look at our specific learning objectives.",
        )
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title="Lesson Roadmap",
            subtitle="The path from core concepts to exam-level mastery",
            purpose="Provide students with cognitive scaffolding and clear expectations.",
            source_content_ids=[],
            slide_type=SlideType.ROADMAP,
            visual_model="roadmap_stepper",
            elements_data={"stages": roadmap_stages},
            speaker_notes=notes,
            estimated_time_minutes=1.5,
        )

    def _build_objectives_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        notes = SpeakerNotes(
            teacher_explanation="State the learning goals clearly so students know what they are responsible for.",
            emphasis="By the end of this session, you should be able to solve these problems independently.",
            ask_students="Which of these goals looks most challenging or interesting?",
            transition="Let's activate our prior knowledge before introducing new material.",
        )
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title="Learning Objectives",
            subtitle="What you will master in this lesson",
            purpose="Define clear, measurable learning outcomes.",
            source_content_ids=[],
            slide_type=SlideType.LEARNING_OBJECTIVES,
            visual_model="bullet_cards",
            elements_data={"objectives": plan.learning_objectives},
            speaker_notes=notes,
            estimated_time_minutes=2.0,
        )

    def _build_prior_knowledge_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        notes = SpeakerNotes(
            teacher_explanation="Briefly review prerequisite concepts to activate prior knowledge.",
            emphasis="If you are rusty on these prerequisites, pay close attention to the warm-up connections.",
            ask_students="Can someone summarize our first prerequisite in their own words?",
            transition="With this foundation ready, let's dive into our first core concept.",
        )
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title="Prior Knowledge & Warm-Up",
            subtitle="Foundations needed for today's topic",
            purpose="Activate relevant cognitive schemas and review prerequisites.",
            source_content_ids=[],
            slide_type=SlideType.PRIOR_KNOWLEDGE,
            visual_model="prerequisite_grid",
            elements_data={"prerequisites": plan.prior_knowledge},
            speaker_notes=notes,
            estimated_time_minutes=2.5,
        )

    def _build_core_content_slides(self, plan: ChapterPlan, units: List[ContentUnit]) -> List[SlideSpec]:
        """Translates all extracted content units into structured slides with 100% coverage."""
        slides: List[SlideSpec] = []
        i = 0

        while i < len(units):
            u = units[i]

            # 1. Definitions
            if u.content_type == ContentType.DEFINITION:
                sid = self._next_slide_id()
                u.mark_covered(sid)
                
                # Check if there is an immediate explanation following
                expl_u = None
                if i + 1 < len(units) and units[i + 1].content_type == ContentType.EXPLANATION:
                    expl_u = units[i + 1]
                    expl_u.mark_covered(sid)
                    i += 1

                notes = SpeakerNotes(
                    teacher_explanation=f"Define the term with high precision. Emphasize why the formal wording matters.\n{u.normalized_content}",
                    emphasis="Do not paraphrase away key terminology.",
                    ask_students="Why is this specific definition necessary?",
                    transition="Now let's see how this definition applies in practice.",
                )
                slides.append(
                    SlideSpec(
                        slide_id=sid,
                        chapter_id=plan.id,
                        title=f"Core Definition: {plan.title}",
                        subtitle="Precise terminology and fundamental meaning",
                        purpose="Establish formal definition and core terminology.",
                        source_content_ids=[u.id] + ([expl_u.id] if expl_u else []),
                        slide_type=SlideType.CONCEPT_DEFINITION,
                        visual_model="definition_card",
                        elements_data={
                            "definition_text": u.normalized_content,
                            "explanation_text": expl_u.normalized_content if expl_u else "",
                            "source_ref": u.source_location,
                        },
                        speaker_notes=notes,
                        estimated_time_minutes=2.5,
                        source_references=[u.source_location],
                    )
                )

            # 2. Formulas / Equations
            elif u.content_type == ContentType.FORMULA:
                sid = self._next_slide_id()
                u.mark_covered(sid)
                notes = SpeakerNotes(
                    teacher_explanation=f"Analyze every symbol in the formula:\n{u.normalized_content}",
                    emphasis="Units and dimensional consistency must always be checked.",
                    ask_students="What happens to the left side if we double the variable on the right?",
                    transition="Let's work through a concrete calculation using this formula.",
                )
                slides.append(
                    SlideSpec(
                        slide_id=sid,
                        chapter_id=plan.id,
                        title=f"Formula & Relationship",
                        subtitle="Mathematical representation and physical meaning",
                        purpose="Deconstruct mathematical law, variables, and units.",
                        source_content_ids=[u.id],
                        slide_type=SlideType.FORMULA_BREAKDOWN,
                        visual_model="formula_breakdown",
                        elements_data={
                            "formula": u.normalized_content,
                            "context": u.original_wording,
                            "source_ref": u.source_location,
                        },
                        speaker_notes=notes,
                        estimated_time_minutes=3.0,
                        source_references=[u.source_location],
                    )
                )

            # 3. Worked Examples (Problem + Steps)
            elif u.content_type in (ContentType.EXAMPLE, ContentType.WORKED_STEP):
                sid = self._next_slide_id()
                u.mark_covered(sid)
                example_ids = [u.id]

                # Group subsequent worked steps into this worked example
                steps = []
                if u.content_type == ContentType.EXAMPLE:
                    problem_statement = u.normalized_content
                else:
                    problem_statement = "Worked Problem"
                    steps.append(u.normalized_content)

                while i + 1 < len(units) and units[i + 1].content_type == ContentType.WORKED_STEP:
                    i += 1
                    step_u = units[i]
                    step_u.mark_covered(sid)
                    example_ids.append(step_u.id)
                    steps.append(step_u.normalized_content)

                if not steps:
                    steps = ["Identify given quantities", "Apply fundamental relation", "Compute exact final value"]

                # Add animation steps for progressive step-by-step reveal
                anim_steps = [
                    AnimationStep(
                        step_number=s_idx + 1,
                        target_object_id=f"step_box_{s_idx + 1}",
                        action=AnimationType.APPEAR,
                        description=f"Reveal solution step {s_idx + 1}",
                    )
                    for s_idx in range(len(steps))
                ]

                notes = SpeakerNotes(
                    teacher_explanation=f"Guide students step by step. Pause after each step before clicking to reveal the next step.",
                    emphasis="Ensure students write down each intermediate step rather than skipping to the final number.",
                    ask_students="Before I click, what is our next mathematical operation?",
                    transition="Let's review the final solution and check units.",
                )

                slides.append(
                    SlideSpec(
                        slide_id=sid,
                        chapter_id=plan.id,
                        title="Worked Example: Step-by-Step",
                        subtitle="Applying principles to a concrete problem",
                        purpose="Demonstrate systematic problem-solving methodology.",
                        source_content_ids=example_ids,
                        slide_type=SlideType.WORKED_EXAMPLE,
                        visual_model="stepped_cards",
                        elements_data={
                            "problem": problem_statement,
                            "steps": steps,
                            "source_ref": u.source_location,
                        },
                        animation_steps=anim_steps,
                        speaker_notes=notes,
                        estimated_time_minutes=4.0,
                        source_references=[u.source_location],
                    )
                )

            # 4. Tables
            elif u.content_type == ContentType.TABLE:
                sid = self._next_slide_id()
                u.mark_covered(sid)
                notes = SpeakerNotes(
                    teacher_explanation="Examine patterns and relationships in the structured data.",
                    emphasis="Notice the rows that illustrate key trends or exceptions.",
                    ask_students="What trend do you observe across these columns?",
                    transition="Let's analyze what this data proves.",
                )
                headers = u.metadata.get("headers", ["Column 1", "Column 2"])
                rows = u.metadata.get("rows", [["Value A", "Value B"]])
                slides.append(
                    SlideSpec(
                        slide_id=sid,
                        chapter_id=plan.id,
                        title=f"Structured Data: {u.metadata.get('title', 'Comparative Data')}",
                        subtitle="Key values, properties, and observations",
                        purpose="Present structured tabular evidence.",
                        source_content_ids=[u.id],
                        slide_type=SlideType.TABLE_DISPLAY,
                        visual_model="table_display",
                        elements_data={
                            "headers": headers,
                            "rows": rows,
                            "title": u.metadata.get("title", ""),
                            "source_ref": u.source_location,
                        },
                        speaker_notes=notes,
                        estimated_time_minutes=3.0,
                        source_references=[u.source_location],
                    )
                )

            # 5. Diagrams / Figures
            elif u.content_type == ContentType.DIAGRAM:
                sid = self._next_slide_id()
                u.mark_covered(sid)
                notes = SpeakerNotes(
                    teacher_explanation="Guide student visual attention to key components and labels.",
                    emphasis="Trace the flow of energy / sequence / structure from left to right.",
                    ask_students="What does this primary component represent?",
                    transition="Let's connect this visual model to our theoretical laws.",
                )
                slides.append(
                    SlideSpec(
                        slide_id=sid,
                        chapter_id=plan.id,
                        title=f"Visual Model: Diagram",
                        subtitle=u.normalized_content,
                        purpose="Explain structures, components, and relationships visually.",
                        source_content_ids=[u.id],
                        slide_type=SlideType.DIAGRAM_EXPLANATION,
                        visual_model="diagram_explanation",
                        elements_data={
                            "caption": u.normalized_content,
                            "image_id": u.metadata.get("image_id"),
                            "source_ref": u.source_location,
                        },
                        speaker_notes=notes,
                        estimated_time_minutes=3.5,
                        source_references=[u.source_location],
                    )
                )

            # 6. Explanations and other content
            else:
                sid = self._next_slide_id()
                u.mark_covered(sid)
                # Check strategy
                strat = SubjectClassifier.select_visual_strategy(plan.subject_domain, u.normalized_content)
                slide_type_map = {
                    "process_flow": SlideType.PROCESS_FLOW,
                    "2_column_compare": SlideType.COMPARISON,
                    "classification_grid": SlideType.CLASSIFICATION_GRID,
                    "timeline": SlideType.TIMELINE,
                    "diagram_explanation": SlideType.DIAGRAM_EXPLANATION,
                    "formula_breakdown": SlideType.FORMULA_BREAKDOWN,
                    "stepped_cards": SlideType.CONCEPT_DEFINITION,
                    "common_misconception": SlideType.COMMON_MISCONCEPTION,
                }

                notes = SpeakerNotes(
                    teacher_explanation=f"Explain this core concept thoroughly:\n{u.normalized_content}",
                    emphasis="Ensure students grasp the fundamental mechanism.",
                    ask_students="How does this relate to what we discussed earlier?",
                    transition="Let's build upon this idea.",
                )

                slides.append(
                    SlideSpec(
                        slide_id=sid,
                        chapter_id=plan.id,
                        title=f"Key Concept: {plan.title}",
                        subtitle="Mechanisms, principles, and analysis",
                        purpose="Explain core educational mechanism.",
                        source_content_ids=[u.id],
                        slide_type=slide_type_map.get(strat, SlideType.CONCEPT_DEFINITION),
                        visual_model=strat,
                        elements_data={
                            "content": u.normalized_content,
                            "source_ref": u.source_location,
                        },
                        speaker_notes=notes,
                        estimated_time_minutes=3.0,
                        source_references=[u.source_location],
                    )
                )

            i += 1

        return slides

    def _build_misconception_slides(self, plan: ChapterPlan) -> List[SlideSpec]:
        slides: List[SlideSpec] = []
        for m in plan.misconceptions[:2]:
            sid = self._next_slide_id()
            if m.get("source_unit_id"):
                self.ledger.mark_covered(m["source_unit_id"], sid)

            notes = SpeakerNotes(
                teacher_explanation="Highlight this frequent student misconception. Ask if anyone has made this mistake before.",
                emphasis="Explain the logical flaw in the wrong approach before confirming the correct reasoning.",
                ask_students=f"Why is '{m['wrong_idea']}' such an easy trap to fall into?",
                likely_misconception=m["wrong_idea"],
                transition="Let's make sure we test our understanding with a quick check.",
            )

            anim_steps = [
                AnimationStep(
                    step_number=1,
                    target_object_id="wrong_box",
                    action=AnimationType.CROSS_OUT,
                    description="Highlight and cross out common mistake",
                ),
                AnimationStep(
                    step_number=2,
                    target_object_id="correct_box",
                    action=AnimationType.APPEAR,
                    description="Reveal correct reasoning",
                ),
            ]

            slides.append(
                SlideSpec(
                    slide_id=sid,
                    chapter_id=plan.id,
                    title=f"Common Misconception & Pitfall",
                    subtitle=m["topic"],
                    purpose="Actively dismantle tempting error and reinforce sound reasoning.",
                    source_content_ids=[m["source_unit_id"]] if m.get("source_unit_id") else [],
                    slide_type=SlideType.COMMON_MISCONCEPTION,
                    visual_model="misconception_contrast",
                    elements_data={
                        "topic": m["topic"],
                        "wrong_idea": m["wrong_idea"],
                        "why_wrong": m["why_wrong"],
                        "correct_idea": m["correct_idea"],
                        "correct_reasoning": m["correct_reasoning"],
                    },
                    animation_steps=anim_steps,
                    speaker_notes=notes,
                    estimated_time_minutes=3.0,
                )
            )

        return slides

    def _build_quiz_pair(self, plan: ChapterPlan, q: QuizQuestion) -> tuple[SlideSpec, SlideSpec]:
        """Creates classroom-friendly 2-slide pattern: Question Only -> Click / Next -> Reveal + Explanation."""
        q_sid = self._next_slide_id()
        r_sid = self._next_slide_id()

        q.slide_id = q_sid
        q.reveal_slide_id = r_sid
        self.ledger.mark_multiple_covered(q.source_content_ids, q_sid)
        self.ledger.mark_multiple_covered(q.source_content_ids, r_sid)

        # Slide A: Question prompt
        q_notes = SpeakerNotes(
            teacher_explanation="Present question to the class. DO NOT give away the answer.",
            emphasis="Give students 30-45 seconds of quiet thinking time or turn-and-talk before taking answers.",
            ask_students=f"{q.prompt}\nWho can explain their reasoning?",
            transition="Let's advance to the next slide to reveal the verified answer and explanation.",
        )
        q_slide = SlideSpec(
            slide_id=q_sid,
            chapter_id=plan.id,
            title="Check for Understanding",
            subtitle=f"{q.question_type.value.replace('_', ' ').title()} • Classroom Check",
            purpose="Assess student comprehension and stimulate classroom discussion.",
            source_content_ids=q.source_content_ids,
            slide_type=SlideType.QUIZ_QUESTION,
            visual_model="quiz_prompt",
            elements_data={
                "question_id": q.id,
                "prompt": q.prompt,
                "options": q.options,
                "question_type": q.question_type.value,
                "difficulty": q.difficulty,
            },
            quiz=q,
            speaker_notes=q_notes,
            estimated_time_minutes=2.0,
        )

        # Slide B: Answer Reveal
        r_notes = SpeakerNotes(
            teacher_explanation=f"Reveal correct answer: {q.correct_answer}.\nExplanation: {q.explanation}",
            emphasis="Discuss why the distractors are incorrect so students learn from mistakes.",
            ask_students="Did anyone arrive at this using a different method?",
            transition="Let's proceed to synthesize our major takeaways.",
        )
        r_anim = [
            AnimationStep(
                step_number=1,
                target_object_id="answer_reveal_box",
                action=AnimationType.ANSWER_REVEAL,
                description="Highlight correct answer and display explanation card",
            )
        ]
        r_slide = SlideSpec(
            slide_id=r_sid,
            chapter_id=plan.id,
            title="Check for Understanding: Answer & Explanation",
            subtitle=f"Solution for {q.id}",
            purpose="Reveal correct answer, provide deep explanation, and analyze distractors.",
            source_content_ids=q.source_content_ids,
            slide_type=SlideType.QUIZ_REVEAL,
            visual_model="quiz_reveal",
            elements_data={
                "question_id": q.id,
                "prompt": q.prompt,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "options": q.options,
                "distractor_rationales": q.distractor_rationales,
            },
            quiz=q,
            animation_steps=r_anim,
            speaker_notes=r_notes,
            estimated_time_minutes=1.5,
        )

        return q_slide, r_slide

    def _build_summary_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        takeaways = plan.core_concepts[:4] if plan.core_concepts else [
            f"Mastery of {plan.title} fundamental laws and definitions",
            "Systematic problem solving with verified dimensional units",
            "Clear distinction between common misconceptions and correct reasoning",
        ]
        notes = SpeakerNotes(
            teacher_explanation="Summarize the core takeaways. Have students recite or record the 3-4 golden rules.",
            emphasis="These points are the foundation of upcoming assessments.",
            ask_students="If you had to summarize today's lesson in one sentence, what would you say?",
            transition="Let's conclude with independent practice problems.",
        )
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title="Summary & Key Takeaways",
            subtitle="Core ideas to remember",
            purpose="Synthesize and consolidate lesson knowledge.",
            source_content_ids=[],
            slide_type=SlideType.SUMMARY_RECAP,
            visual_model="summary_cards",
            elements_data={"takeaways": takeaways},
            speaker_notes=notes,
            estimated_time_minutes=2.5,
        )

    def _build_practice_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        notes = SpeakerNotes(
            teacher_explanation="Assign these practice questions for individual desk work or homework.",
            emphasis="Show all working steps clearly.",
            transition="Let's complete our exit ticket before ending the class.",
        )
        practice_problems = [
            f"1. Explain the fundamental principles of {plan.title} in your own words.",
            f"2. Solve a multi-step numerical calculation using the core relations discussed today.",
            f"3. Explain why the common misconception discussed earlier is incorrect.",
        ]
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title="Independent Practice & Exam Questions",
            subtitle="Test your mastery",
            purpose="Provide students with practice opportunities.",
            source_content_ids=[],
            slide_type=SlideType.PRACTICE_SET,
            visual_model="practice_cards",
            elements_data={"problems": practice_problems},
            speaker_notes=notes,
            estimated_time_minutes=4.0,
        )

    def _build_exit_ticket_slide(self, plan: ChapterPlan) -> SlideSpec:
        sid = self._next_slide_id()
        notes = SpeakerNotes(
            teacher_explanation="Collect exit tickets before students leave to gauge today's mastery level.",
            emphasis="One quick response per student.",
            ask_students="What was the most important thing you learned today, and what question do you still have?",
            transition="Great work today! Next time we will build directly on this topic.",
        )
        return SlideSpec(
            slide_id=sid,
            chapter_id=plan.id,
            title="Exit Ticket",
            subtitle="Before you leave the classroom",
            purpose="Rapid formative assessment to assess student confidence and lingering questions.",
            source_content_ids=[],
            slide_type=SlideType.EXIT_TICKET,
            visual_model="exit_ticket",
            elements_data={
                "prompt_1": "1. What is the single most important concept or rule from today's lesson?",
                "prompt_2": "2. What is one question or area you would like more practice on?",
            },
            speaker_notes=notes,
            estimated_time_minutes=2.0,
        )
