"""Adaptive teaching-sequence builder.

Produces instructional states (not slide titles); the storyboard consumes
these moves. Sequence adapts to domain + content mix + strategies — there is
no fixed per-chapter template.
"""

from __future__ import annotations
from typing import Dict, List
from lessonmorph.core.models import (
    ContentType, ContentUnit, LearningObjective, SubjectDomain, TeachingMove,
)
from lessonmorph.pedagogy.strategies import complexity_of

_ANIM_FOR_STATE = {
    "VISUAL_MODEL": "sequencing",
    "GUIDED_EXAMPLE": "sequencing",
    "MISCONCEPTION": "error_correction",
    "RETRIEVAL": "answer_reveal",
    "CUMULATIVE_RETRIEVAL": "answer_reveal",
    "ASSESSMENT": "answer_reveal",
}

_TEACHER_MOVES = {
    "HOOK": "ask students to predict before revealing anything",
    "PRIOR_KNOWLEDGE": "elicit prior knowledge; cold-call one summary",
    "OBJECTIVE": "read objectives aloud; ask which looks hardest",
    "EXPLANATION": "explain, then pause; ask 'why does this step follow?'",
    "VISUAL_MODEL": "pause before revealing each stage; ask what comes next",
    "GUIDED_EXAMPLE": "model the first step (I DO), let students attempt the next (WE DO)",
    "RETRIEVAL": "hide the source slide; require recall, not recognition",
    "DEEPER_EXPLANATION": "compare the naive answer with the refined one",
    "MISCONCEPTION": "surface the tempting error first; ask why it feels right",
    "GUIDED_PRACTICE": "release support gradually; circulate and probe reasoning",
    "INDEPENDENT_PRACTICE": "silent independent work; collect one exit answer",
    "CUMULATIVE_RETRIEVAL": "revisit an earlier concept in a new context",
    "RECAP": "ask a student to teach back the golden rule",
    "ASSESSMENT": "think time first; then reveal with explanatory feedback",
}


def build_teaching_sequence(
    units: List[ContentUnit],
    objectives: List[LearningObjective],
    content_profile: Dict[str, str],
    strategies: List[str],
    domain: SubjectDomain,
    misconception_count: int,
) -> List[TeachingMove]:
    """Goal + content + learner needs -> ordered instructional states."""
    by_id = {u.id: u for u in units}
    obj_ids = [o.id for o in objectives]
    nature_mix = set(content_profile.values()) or {"conceptual"}
    procedural = "procedural" in nature_mix
    moves: List[TeachingMove] = []

    def _add(state: str, purpose: str, cids: List[str], oids: List[str],
             strategy: str, complexity: str = "medium") -> None:
        moves.append(TeachingMove(
            state=state, purpose=purpose, content_ids=[c for c in cids if c in by_id],
            objective_ids=oids, strategy=strategy,
            teacher_move=_TEACHER_MOVES.get(state, ""),
            animation_purpose=_ANIM_FOR_STATE.get(state, ""),
            complexity=complexity))

    _add("HOOK", "create relevance and curiosity for the chapter", [], obj_ids[:1], "prior_activation", "low")
    _add("PRIOR_KNOWLEDGE", "activate prerequisites before new complexity",
         [], obj_ids[:1], "prior_activation", "low")
    _add("OBJECTIVE", "state observable outcomes (backward design)", [], obj_ids, "backward_design", "low")

    # Core exposition: chunk dense content progressively (intrinsic-load control).
    taught: List[str] = []
    for u in units:
        nature = content_profile.get(u.id, "conceptual")
        cx = complexity_of(u, nature)
        oids = [o.id for o in objectives if u.id in o.content_ids] or obj_ids[:1]
        if u.content_type in (ContentType.EXAMPLE, ContentType.WORKED_STEP):
            _add("GUIDED_EXAMPLE", f"model reasoning for {u.id}",
                 [u.id], oids, "worked_example", cx)
        elif u.content_type in (ContentType.DIAGRAM, ContentType.TABLE) or nature == "conceptual" and "worked_example" not in strategies and u.content_type == ContentType.EXPLANATION:
            _add("VISUAL_MODEL", f"coordinate explanation + visual for {u.id}",
                 [u.id], oids, "dual_coding", cx)
        else:
            _add("EXPLANATION", f"teach {u.id} in a manageable chunk", [u.id], oids,
                 "scaffolding" if cx == "high" else "elaboration", cx)
        taught.append(u.id)
        # Retrieval after every ~3 taught chunks in longer lessons (spacing).
        if len(taught) % 3 == 0 and len(units) > 5:
            _add("RETRIEVAL", f"retrieve {', '.join(taught[-3:])} before moving on",
                 taught[-3:], oids, "retrieval", "medium")

    if misconception_count:
        _add("MISCONCEPTION", "confront the tempting error with evidence",
             [], obj_ids, "misconception_check", "medium")
    if procedural:
        _add("GUIDED_PRACTICE", "partially completed example with fading support",
             taught[-2:] if taught else [], obj_ids, "gradual_release", "high")
        _add("INDEPENDENT_PRACTICE", "novel application without support",
             [], obj_ids, "deliberate_practice", "high")
    elif domain in (SubjectDomain.HISTORY, SubjectDomain.LITERATURE):
        _add("GUIDED_PRACTICE", "compare/interpret with teacher guidance",
             taught[-2:] if taught else [], obj_ids, "comparison", "medium")
    if len(taught) > 4:
        _add("CUMULATIVE_RETRIEVAL", "revisit the earliest important idea in a new context",
             taught[:2], obj_ids[:2], "spacing", "medium")
    _add("RECAP", "consolidate golden rules", taught[:4], obj_ids, "elaboration", "low")
    _add("ASSESSMENT", "assess each objective with explanatory feedback",
         taught, obj_ids, "formative_assessment", "medium")
    return moves
