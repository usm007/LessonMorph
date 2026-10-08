"""Slide composer: Blueprint SlideIR → SlideSpec (deterministic, no pedagogy).

The composer executes the Blueprint literally. It never reinterprets
pedagogy, never invents content, never re-solves answers: every field of the
SlideSpec derives from the SlideIR. All text is sanitized; equations arrive
structured; assessments arrive locked.
"""

from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, List
from lessonmorph.blueprint.ir import LockedAssessment, Representation, SlideIR
from lessonmorph.blueprint.sanitize import clean
from lessonmorph.core.models import (
    AnimationStep,
    AnimationType,
    QuestionType,
    QuizQuestion,
    SlideSpec,
    SlideType,
    SpeakerNotes,
)

_REP_SLIDE_TYPE = {
    "definition_focus": SlideType.CONCEPT_DEFINITION,
    "big_idea": SlideType.CONCEPT_DEFINITION,
    "concept_card": SlideType.CONCEPT_DEFINITION,
    "key_principle": SlideType.CONCEPT_DEFINITION,
    "contrast": SlideType.COMMON_MISCONCEPTION,
    "labeled_diagram": SlideType.DIAGRAM_EXPLANATION,
    "anatomy_map": SlideType.DIAGRAM_EXPLANATION,
    "hierarchy": SlideType.CLASSIFICATION_GRID,
    "cutaway": SlideType.DIAGRAM_EXPLANATION,
    "spatial_relationship": SlideType.DIAGRAM_EXPLANATION,
    "flow": SlideType.PROCESS_FLOW,
    "sequence": SlideType.PROCESS_FLOW,
    "cycle": SlideType.PROCESS_FLOW,
    "cause_effect": SlideType.CAUSE_EFFECT,
    "before_after": SlideType.COMPARISON,
    "pathway": SlideType.PROCESS_FLOW,
    "equation_focus": SlideType.FORMULA_BREAKDOWN,
    "worked_calculation": SlideType.WORKED_EXAMPLE,
    "data_table": SlideType.TABLE_DISPLAY,
    "bar_chart": SlideType.TABLE_DISPLAY,
    "line_chart": SlideType.TABLE_DISPLAY,
    "comparison_matrix": SlideType.COMPARISON,
    "mcq": SlideType.QUIZ_QUESTION,
    "true_false": SlideType.QUIZ_QUESTION,
    "prediction": SlideType.QUIZ_QUESTION,
    "diagnostic_question": SlideType.QUIZ_QUESTION,
    "retrieval": SlideType.QUIZ_QUESTION,
    "practice_problem": SlideType.PRACTICE_SET,
    "concept_map": SlideType.SUMMARY_RECAP,
    "summary_matrix": SlideType.SUMMARY_RECAP,
    "big_picture": SlideType.SUMMARY_RECAP,
    "title": SlideType.TITLE,
    "roadmap": SlideType.ROADMAP,
    "objectives": SlideType.LEARNING_OBJECTIVES,
    "exit": SlideType.EXIT_TICKET,
}

_ANIM_PURPOSE = {
    "labeled_diagram": "decomposition", "anatomy_map": "decomposition",
    "cutaway": "decomposition", "spatial_relationship": "signalling",
    "flow": "sequencing", "sequence": "sequencing", "pathway": "sequencing",
    "cycle": "transformation", "cause_effect": "causal_explanation",
    "before_after": "comparison", "comparison_matrix": "comparison",
    "contrast": "error_correction", "equation_focus": "signalling",
    "worked_calculation": "sequencing", "mcq": "answer_reveal",
    "true_false": "answer_reveal", "retrieval": "answer_reveal",
    "prediction": "answer_reveal", "diagnostic_question": "answer_reveal",
}

_TIME = {"worked_calculation": 4.0, "labeled_diagram": 3.5, "equation_focus": 3.0,
         "mcq": 2.0, "true_false": 2.0, "practice_problem": 4.0}


class SlideComposer:
    """Deterministic SlideIR → SlideSpec translation."""

    def __init__(self):
        self._counter = 0

    def compose_all(self, slides: List[SlideIR], chapter_id: str) -> List[SlideSpec]:
        return [self.compose(s, chapter_id) for s in slides]

    def compose(self, ir: SlideIR, chapter_id: str) -> SlideSpec:
        self._counter += 1
        sid = f"S{self._counter:03d}"
        rep = ir.representation
        slide_type = _REP_SLIDE_TYPE.get(rep, SlideType.CONCEPT_DEFINITION)
        # Reveal slides reuse the quiz-reveal type so the renderer highlights answers.
        if ir.body.get("reveal") and slide_type == SlideType.QUIZ_QUESTION:
            slide_type = SlideType.QUIZ_REVEAL
        elements = self._elements(ir)
        anim = self._animations(ir)
        notes = self._notes(ir)
        quiz = self._quiz(ir) if ir.assessment else None
        return SlideSpec(
            slide_id=sid, chapter_id=chapter_id,
            title=clean(ir.content_title)[:120] or clean(ir.concept_title)[:120],
            subtitle=(clean(ir.kicker)[:160] or clean(ir.concept_title)[:160] or None),
            purpose=clean(ir.purpose)[:300],
            source_content_ids=list(ir.source_ids),
            slide_type=slide_type, visual_model=rep,
            elements_data=elements, animation_steps=anim, quiz=quiz,
            speaker_notes=notes,
            estimated_time_minutes=_TIME.get(rep, 2.5),
            source_references=[],
            instructional_state=ir.instructional_state,
            instructional_purpose=clean(ir.purpose)[:300],
            objective_ids=list(ir.objective_ids))

    # -- elements: one structured payload per representation -----------------
    def _elements(self, ir: SlideIR) -> Dict[str, Any]:
        b = ir.body
        v = ir.visual
        rep = ir.representation
        base: Dict[str, Any] = {"representation": rep,
                                "reveal_sequence": list(ir.reveal_sequence)}
        if rep == "definition_focus":
            base.update({"term": clean(b.get("term", ir.concept_title)),
                         "definition": clean(b.get("definition", ""))})
        elif rep in ("labeled_diagram", "anatomy_map", "cutaway", "spatial_relationship"):
            base.update({"subject": clean(v.subject or ir.concept_title),
                         "structure": [clean(s) for s in v.structure],
                         "labels": [{"name": clean(l.get("name", "")),
                                     "target": l.get("target", ""),
                                     "explanation": clean(l.get("explanation", ""))}
                                    for l in v.labels],
                         "caption": clean(b.get("caption", ""))})
        elif rep in ("flow", "sequence", "pathway", "cycle"):
            base.update({"subject": clean(v.subject or ir.concept_title),
                         "stages": [clean(s) for s in v.structure],
                         "narrative": clean(b.get("narrative", ""))})
        elif rep == "cause_effect":
            base.update({"points": [clean(p) for p in b.get("points", [])]})
        elif rep in ("contrast",):
            base.update({k: clean(b.get(k, "")) for k in
                         ("wrong_idea", "why_wrong", "correct_idea", "correct_reasoning")})
            base["topic"] = clean(ir.concept_title)
        elif rep == "equation_focus":
            eq = v.equation
            base.update({"equation": {
                "lhs": [{"coefficient": t.coefficient, "species": t.species, "note": t.note}
                        for t in (eq.lhs if eq else [])],
                "energy": eq.energy if eq else "",
                "arrow": eq.arrow if eq else "→",
                "rhs": [{"coefficient": t.coefficient, "species": t.species, "note": t.note}
                        for t in (eq.rhs if eq else [])],
                "inline": eq.inline() if eq else ""},
                "context": clean(b.get("context", ""))})
        elif rep == "worked_calculation":
            base.update({"problem": clean(b.get("problem", "")),
                         "givens": [clean(g) for g in b.get("givens", [])],
                         "steps": [clean(s) for s in b.get("steps", [])],
                         "verify": clean(b.get("verify", ""))})
        elif rep in ("data_table", "comparison_matrix"):
            base.update({"headers": [clean(h) for h in v.columns],
                         "rows": [[clean(str(cell)) for cell in
                                   ([r.get(h, "") for h in v.columns] if isinstance(r, dict)
                                    else r)]
                                  for r in v.rows],
                         "title": clean(b.get("title", ir.concept_title))})
        elif rep in ("mcq", "true_false", "prediction", "diagnostic_question", "retrieval"):
            a: LockedAssessment | None = ir.assessment
            base.update({"question_id": b.get("question_id", ""),
                         "prompt": clean(b.get("prompt", "")),
                         "options": {k: clean(x) for k, x in b.get("options", {}).items()},
                         "question_type": a.type if a else "short_answer",
                         "reveal": bool(b.get("reveal")),
                         "correct_option": a.correct_option if a and b.get("reveal") else "",
                         "explanation": a.explanation if a and b.get("reveal") else "",
                         "origin": b.get("origin", "")})
        elif rep == "practice_problem":
            base.update({"items": [clean(i) for i in b.get("items", [])],
                         "origin": b.get("origin", ""),
                         "scaffold": b.get("scaffold", {}),
                         "faded": bool(b.get("faded"))})
        elif rep in ("concept_map", "summary_matrix", "big_picture"):
            base.update({"takeaways": [clean(t) for t in b.get("takeaways", [])],
                         "center": clean(v.subject or ir.concept_title),
                         "nodes": [clean(s) for s in v.structure]})
        elif rep == "title":
            base.update({"unit_title": clean(b.get("unit", "")),
                         "topic": clean(b.get("topic", ir.concept_title)),
                         "badge": "Classroom Ready"})
        elif rep == "objectives":
            base.update({"objectives": [clean(o) for o in b.get("objectives", [])]})
        elif rep == "exit":
            base.update({"prompt_1": clean(b.get("prompt_1", "")),
                         "prompt_2": clean(b.get("prompt_2", ""))})
        else:  # concept_card / key_principle / big_idea / roadmap / hierarchy / charts
            base.update({"points": [clean(p) for p in b.get("points", [])],
                         "prerequisites": [clean(p) for p in b.get("prerequisites", [])],
                         "takeaways": [clean(t) for t in b.get("takeaways", [])]})
        return base

    def _animations(self, ir: SlideIR) -> List[AnimationStep]:
        purpose = _ANIM_PURPOSE.get(ir.representation, "")
        steps = []
        for i, target in enumerate(ir.reveal_sequence[:8]):
            action = AnimationType.ANSWER_REVEAL if (
                ir.body.get("reveal") and i == 0) else (
                AnimationType.CROSS_OUT if (
                    ir.representation == "contrast" and i == 0)
                else AnimationType.APPEAR)
            steps.append(AnimationStep(
                step_number=i + 1, target_object_id=f"rv_{i+1}",
                action=action, description=f"Reveal: {clean(target)[:60]}",
                purpose=purpose or "sequencing"))
        return steps

    def _notes(self, ir: SlideIR) -> SpeakerNotes:
        ta = ir.teacher_action
        ask, expl = "", ""
        if ta.type == "prompt":
            ask = ta.prompt
        elif ta.type == "prediction":
            ask = ta.prompt
        elif ta.type in ("explanation", ""):
            expl = ta.focus or ta.prompt
        return SpeakerNotes(
            teacher_explanation=expl[:600],
            ask_students=ask[:600],
            emphasis=f"Learning goal: {'; '.join(ir.learning_goal)[:250]}" if ir.learning_goal else "",
            transition="")

    def _quiz(self, ir: SlideIR) -> QuizQuestion | None:
        a = ir.assessment
        if a is None:
            return None
        options = [f"{k}) {v}" for k, v in a.options.items()]
        correct_text = f"{a.correct_option}) {a.options.get(a.correct_option, '')}".strip()
        return QuizQuestion(
            id=a.id,
            question_type={"mcq": QuestionType.MULTIPLE_CHOICE,
                           "true_false": QuestionType.TRUE_FALSE}.get(
                               a.type, QuestionType.SHORT_ANSWER),
            source_content_ids=list(ir.source_ids),
            difficulty="application", prompt=a.stem, options=options,
            correct_answer=correct_text, explanation=a.explanation,
            objective_ids=list(ir.objective_ids))
