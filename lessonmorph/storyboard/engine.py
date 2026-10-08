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
    TeachingMove,
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
        if plan.pedagogical_plan and plan.pedagogical_plan.teaching_sequence:
            slides = self._slides_from_sequence(plan)
        else:
            slides = self._legacy_chapter_slides(plan)
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
        """Generates the full ordered sequence of slides for a chapter.

        Pedagogy-first: when a PedagogicalPlan exists, slides are dispatched
        from its teaching_sequence (instructional states). The legacy fixed
        template is only a fallback. A coverage sweep guarantees 100%.
        """
        self._slide_counter = 0
        if plan.pedagogical_plan and plan.pedagogical_plan.teaching_sequence:
            slides = self._slides_from_sequence(plan)
        else:
            slides = self._legacy_chapter_slides(plan, reset=True)
        # Update chapter plan and recalculate pacing
        plan.slides = slides
        pacing = PacingCalculator.estimate_chapter_pacing(slides)
        plan.estimated_time_minutes = pacing.total_minutes

        return slides

    # -- pedagogy-driven dispatch -------------------------------------------
    def _slides_from_sequence(self, plan: ChapterPlan) -> List[SlideSpec]:
        """Storyboard consumes pedagogical intent: one move -> slide(s)."""
        ped = plan.pedagogical_plan
        assert ped is not None
        slides: List[SlideSpec] = []
        by_id = {u.id: u for u in self.ledger.get_units_by_chapter(plan.id)} or {
            u.id: u for u in self.ledger.units}
        covered_in_seq: set = set()
        quiz_used: set = set()

        def _tag(s: SlideSpec, move: TeachingMove) -> SlideSpec:
            s.instructional_state = move.state
            s.instructional_purpose = move.purpose
            s.objective_ids = list(move.objective_ids)
            if move.teacher_move:
                base = s.speaker_notes.ask_students or ""
                extra = f"TEACHER MOVE: {move.teacher_move}."
                s.speaker_notes.ask_students = f"{base}\n{extra}".strip() if base else extra
            for a in s.animation_steps:
                if not a.purpose:
                    a.purpose = move.animation_purpose
            return s

        for move in ped.teaching_sequence:
            cids = [c for c in move.content_ids if c in by_id]
            if move.state == "HOOK":
                slides.append(_tag(self._build_title_slide(plan), move))
            elif move.state == "PRIOR_KNOWLEDGE":
                if plan.prior_knowledge:
                    slides.append(_tag(self._build_prior_knowledge_slide(plan), move))
            elif move.state == "OBJECTIVE":
                slides.append(_tag(self._build_objectives_slide(plan), move))
            elif move.state in ("EXPLANATION", "VISUAL_MODEL", "DEEPER_EXPLANATION"):
                for cid in cids:
                    u = by_id[cid]
                    if u.covered and u.id in covered_in_seq:
                        continue
                    s = self._build_single_content_slide(plan, u)
                    covered_in_seq.add(u.id)
                    slides.append(_tag(s, move))
            elif move.state == "GUIDED_EXAMPLE":
                s = self._build_guided_example_slide(plan, [by_id[c] for c in cids if c in by_id])
                for c in cids:
                    covered_in_seq.add(c)
                slides.append(_tag(s, move))
            elif move.state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL"):
                q = self._pick_question(plan, move, quiz_used)
                if q is not None:
                    quiz_used.add(q.id)
                    a, b = self._build_quiz_pair(plan, q)
                    slides.append(_tag(a, move))
                    slides.append(_tag(b, move))
                else:
                    slides.append(_tag(self._build_retrieval_slide(plan, move), move))
            elif move.state == "MISCONCEPTION":
                for s in self._build_misconception_slides(plan):
                    slides.append(_tag(s, move))
            elif move.state == "GUIDED_PRACTICE":
                slides.append(_tag(self._build_guided_practice_slide(plan, move), move))
            elif move.state == "INDEPENDENT_PRACTICE":
                slides.append(_tag(self._build_practice_slide(plan), move))
            elif move.state == "RECAP":
                slides.append(_tag(self._build_summary_slide(plan), move))
            elif move.state == "ASSESSMENT":
                remaining = [q for q in plan.questions if q.id not in quiz_used]
                if remaining:
                    for q in remaining:
                        quiz_used.add(q.id)
                        a, b = self._build_quiz_pair(plan, q)
                        slides.append(_tag(a, move))
                        slides.append(_tag(b, move))
                else:
                    slides.append(_tag(self._build_practice_slide(plan), move))
        # Roadmap orientation after hook/title for navigation.
        if slides and len(ped.teaching_sequence) > 3:
            slides.insert(1, self._build_roadmap_slide(plan))
        # Coverage sweep: 100% guarantee — leftover units get content slides.
        uncovered = [u for u in by_id.values() if not u.covered]
        if uncovered:
            for u in uncovered:
                s = self._build_single_content_slide(plan, u)
                s.instructional_state = "EXPLANATION"
                s.instructional_purpose = f"coverage sweep: preserve {u.id} ({u.content_type.value})"
                # Insert before recap/assessment tail to keep arc intact.
                idx = next((i for i, sl in enumerate(slides)
                            if sl.instructional_state in ("RECAP", "ASSESSMENT")), len(slides))
                slides.insert(idx, s)
        slides.append(self._build_exit_ticket_slide(plan))
        return slides

    def _pick_question(self, plan: ChapterPlan, move: TeachingMove,
                       used: set) -> Optional[QuizQuestion]:
        for q in plan.questions:
            if q.id in used:
                continue
            if set(q.objective_ids) & set(move.objective_ids) or not move.objective_ids:
                return q
        for q in plan.questions:
            if q.id not in used:
                return q
        return None

    def _build_guided_example_slide(self, plan: ChapterPlan,
                                    units: List[ContentUnit]) -> SlideSpec:
        if not units:
            return self._build_practice_slide(plan)
        first = units[0]
        prob = first.normalized_content if first.content_type == ContentType.EXAMPLE else "Worked Problem"
        steps = [u.normalized_content for u in units
                 if u.content_type == ContentType.WORKED_STEP] or [
            "Identify given quantities", "Select the governing relation",
            "Substitute and compute", "Verify units and result"]
        return self._build_worked_slide(plan, prob, steps,
                                        [u.id for u in units], first.source_location)

    def _build_worked_slide(self, plan: ChapterPlan, problem: str, steps: List[str],
                            ids: List[str], source_ref: str) -> SlideSpec:
        sid = self._next_slide_id()
        for uid in ids:
            self.ledger.mark_covered(uid, sid)
        anim = [AnimationStep(step_number=i + 1, target_object_id=f"step_box_{i + 1}",
                              action=AnimationType.APPEAR,
                              description=f"Reveal solution step {i + 1}",
                              purpose="sequencing") for i in range(len(steps))]
        return SlideSpec(
            slide_id=sid, chapter_id=plan.id, title="Worked Example: Step-by-Step",
            subtitle="Applying principles to a concrete problem",
            purpose="Demonstrate systematic problem-solving methodology (I DO -> WE DO).",
            source_content_ids=ids, slide_type=SlideType.WORKED_EXAMPLE,
            visual_model="stepped_cards",
            elements_data={"problem": problem, "steps": steps, "source_ref": source_ref},
            animation_steps=anim,
            speaker_notes=SpeakerNotes(
                teacher_explanation="Guide students step by step. Pause after each step before revealing the next.",
                emphasis="Students write each intermediate step; never jump to the final number.",
                ask_students="Before I reveal: what is our next operation, and why?",
                transition="Let's verify the result and check units."),
            estimated_time_minutes=4.0, source_references=[source_ref])

    def _build_retrieval_slide(self, plan: ChapterPlan, move: TeachingMove) -> SlideSpec:
        sid = self._next_slide_id()
        self.ledger.mark_multiple_covered(move.content_ids, sid)
        cids = ", ".join(move.content_ids) or "recent concepts"
        return SlideSpec(
            slide_id=sid, chapter_id=plan.id, title="Recall & Reconstruct",
            subtitle="Close the deck — retrieve from memory",
            purpose=f"Purposeful retrieval of {cids} (not recognition of visible text).",
            source_content_ids=list(move.content_ids), slide_type=SlideType.QUIZ_QUESTION,
            visual_model="quiz_prompt",
            elements_data={"prompt": f"Without looking back: explain or apply {cids}.",
                           "options": [], "question_type": "short_answer", "difficulty": "understanding"},
            speaker_notes=SpeakerNotes(
                teacher_explanation="Hide prior slides. Cold-call or think-pair-share.",
                ask_students=f"Reconstruct {cids} in your own words.",
                transition="Let's check our reconstruction against the correct reasoning."),
            estimated_time_minutes=2.0, objective_ids=list(move.objective_ids))

    def _build_guided_practice_slide(self, plan: ChapterPlan, move: TeachingMove) -> SlideSpec:
        sid = self._next_slide_id()
        self.ledger.mark_multiple_covered(move.content_ids, sid)
        return SlideSpec(
            slide_id=sid, chapter_id=plan.id, title="Guided Practice (We Do Together)",
            subtitle="Fading support — you complete the next step",
            purpose="Release scaffolding gradually before independent work.",
            source_content_ids=list(move.content_ids), slide_type=SlideType.PRACTICE_SET,
            visual_model="practice_cards",
            elements_data={"problems": [
                f"1. Complete the partially solved example for {plan.title} (fill the missing step).",
                "2. Justify each step to your neighbour before we reveal."]},
            speaker_notes=SpeakerNotes(
                teacher_explanation="Model only the first step; students complete the rest with support.",
                ask_students="What is the next step, and how do you know?",
                transition="Now try one fully on your own."),
            estimated_time_minutes=3.5, objective_ids=list(move.objective_ids))

    def _build_single_content_slide(self, plan: ChapterPlan, u: ContentUnit) -> SlideSpec:
        """One unit -> one pedagogically-typed slide (split dense content, never cram)."""
        if u.content_type == ContentType.FORMULA:
            sid = self._next_slide_id()
            u.mark_covered(sid)
            return SlideSpec(
                slide_id=sid, chapter_id=plan.id, title="Formula & Relationship",
                subtitle="Mathematical representation and physical meaning",
                purpose="Deconstruct mathematical law, variables, and units.",
                source_content_ids=[u.id], slide_type=SlideType.FORMULA_BREAKDOWN,
                visual_model="formula_breakdown",
                elements_data={"formula": u.normalized_content, "context": u.original_wording,
                               "source_ref": u.source_location},
                speaker_notes=SpeakerNotes(
                    teacher_explanation=f"Analyse every symbol:\n{u.normalized_content}",
                    emphasis="Check units and dimensional consistency.",
                    ask_students="What happens if we double a variable on the right?",
                    transition="Let's apply this to a concrete case."),
                estimated_time_minutes=3.0, source_references=[u.source_location])
        if u.content_type == ContentType.TABLE:
            sid = self._next_slide_id()
            u.mark_covered(sid)
            return SlideSpec(
                slide_id=sid, chapter_id=plan.id,
                title=f"Structured Data: {u.metadata.get('title', 'Comparative Data')}",
                subtitle="Key values, properties, and observations",
                purpose="Present structured tabular evidence.",
                source_content_ids=[u.id], slide_type=SlideType.TABLE_DISPLAY,
                visual_model="table_display",
                elements_data={"headers": u.metadata.get("headers", ["Column 1", "Column 2"]),
                               "rows": u.metadata.get("rows", [["Value A", "Value B"]]),
                               "title": u.metadata.get("title", ""), "source_ref": u.source_location},
                speaker_notes=SpeakerNotes(
                    teacher_explanation="Examine patterns across rows/columns.",
                    ask_students="What trend do you observe?",
                    transition="Let's analyse what this data proves."),
                estimated_time_minutes=3.0, source_references=[u.source_location])
        if u.content_type == ContentType.DIAGRAM:
            sid = self._next_slide_id()
            u.mark_covered(sid)
            return SlideSpec(
                slide_id=sid, chapter_id=plan.id, title="Visual Model: Diagram",
                subtitle=u.normalized_content[:80],
                purpose="Explain structures and relationships visually (dual coding).",
                source_content_ids=[u.id], slide_type=SlideType.DIAGRAM_EXPLANATION,
                visual_model="diagram_explanation",
                elements_data={"caption": u.normalized_content,
                               "image_id": u.metadata.get("image_id"),
                               "source_ref": u.source_location},
                animation_steps=[AnimationStep(step_number=1, target_object_id="diagram_stage_1",
                                               action=AnimationType.APPEAR,
                                               description="Reveal diagram stage by stage",
                                               purpose="sequencing")],
                speaker_notes=SpeakerNotes(
                    teacher_explanation="Trace the flow left to right, one stage at a time.",
                    ask_students="What does this component represent? What comes next?",
                    transition="Let's connect this model to the theory."),
                estimated_time_minutes=3.5, source_references=[u.source_location])
        # Default: explanation/definition/terminology -> strategy-typed slide.
        sid = self._next_slide_id()
        u.mark_covered(sid)
        strat = SubjectClassifier.select_visual_strategy(plan.subject_domain, u.normalized_content)
        slide_type_map = {
            "process_flow": SlideType.PROCESS_FLOW, "2_column_compare": SlideType.COMPARISON,
            "classification_grid": SlideType.CLASSIFICATION_GRID, "timeline": SlideType.TIMELINE,
            "diagram_explanation": SlideType.DIAGRAM_EXPLANATION,
            "formula_breakdown": SlideType.FORMULA_BREAKDOWN,
            "stepped_cards": SlideType.CONCEPT_DEFINITION,
            "common_misconception": SlideType.COMMON_MISCONCEPTION,
        }
        anim_purpose = "sequencing" if strat == "process_flow" else (
            "comparison" if strat == "2_column_compare" else "")
        anim = [AnimationStep(step_number=1, target_object_id="content_build_1",
                              action=AnimationType.APPEAR,
                              description="Progressive reveal of the explanation",
                              purpose=anim_purpose)] if anim_purpose else []
        return SlideSpec(
            slide_id=sid, chapter_id=plan.id, title=f"Key Concept: {plan.title}",
            subtitle="Mechanisms, principles, and analysis",
            purpose="Explain core mechanism in a manageable chunk.",
            source_content_ids=[u.id],
            slide_type=slide_type_map.get(strat, SlideType.CONCEPT_DEFINITION),
            visual_model=strat,
            elements_data={"content": u.normalized_content, "source_ref": u.source_location},
            animation_steps=anim,
            speaker_notes=SpeakerNotes(
                teacher_explanation=f"Explain thoroughly:\n{u.normalized_content}",
                emphasis="Ensure students grasp the mechanism, not just the wording.",
                ask_students="How does this connect to what we covered earlier?",
                transition="Let's build on this idea."),
            estimated_time_minutes=3.0, source_references=[u.source_location])

    def _legacy_chapter_slides(self, plan: ChapterPlan, reset: bool = False) -> List[SlideSpec]:
        """Fixed template fallback when no pedagogical plan exists (never preferred)."""
        if reset:
            self._slide_counter = 0
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
                        purpose="sequencing",
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
                    purpose="error_correction",
                ),
                AnimationStep(
                    step_number=2,
                    target_object_id="correct_box",
                    action=AnimationType.APPEAR,
                    description="Reveal correct reasoning",
                    purpose="error_correction",
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
            objective_ids=list(q.objective_ids),
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
                purpose="answer_reveal",
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
            objective_ids=list(q.objective_ids),
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
