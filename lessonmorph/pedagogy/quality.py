"""Pedagogical safety check + QA report (judgment, not rigid pass/fail)."""

from __future__ import annotations
from typing import Dict, List, Set
from lessonmorph.core.models import (
    PedagogicalPlan, PedagogicalQAReport, QuizQuestion, SlideSpec,
)


def safety_check(plan: PedagogicalPlan, questions: List[QuizQuestion]) -> List[str]:
    warnings: List[str] = []
    states = [m.state for m in plan.teaching_sequence]
    if "PRIOR_KNOWLEDGE" not in states and plan.prerequisites:
        warnings.append("prerequisites identified but never activated")
    assessed: Set[str] = set()
    for q in questions:
        assessed.update(q.objective_ids)
    for o in plan.learning_objectives:
        if o.id not in assessed:
            warnings.append(f"{o.id} has no assessment item")
    if not any(s in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL", "ASSESSMENT") for s in states):
        warnings.append("no retrieval opportunity planned")
    if plan.content_types and not any(
            m.state in ("GUIDED_EXAMPLE", "GUIDED_PRACTICE") for m in plan.teaching_sequence):
        if "procedural" in set(plan.content_types.values()):
            warnings.append("procedural content without guided practice (support removed too fast)")
    if plan.misconceptions and "MISCONCEPTION" not in states:
        warnings.append("misconceptions identified but never confronted")
    return warnings


def build_qa_report(
    plan: PedagogicalPlan, slides: List[SlideSpec], questions: List[QuizQuestion],
) -> PedagogicalQAReport:
    slide_states = [s.instructional_state for s in slides]
    slide_objs: Set[str] = set()
    for s in slides:
        slide_objs.update(s.objective_ids)
    assessed: Set[str] = set()
    for q in questions:
        assessed.update(q.objective_ids)
    practiced_states = {"GUIDED_PRACTICE", "INDEPENDENT_PRACTICE", "GUIDED_EXAMPLE"}
    practiced = {oid for s in slides if s.instructional_state in practiced_states
                 for oid in s.objective_ids}
    retrieval = sum(1 for s in slide_states if s == "RETRIEVAL")
    cumulative = sum(1 for s in slide_states if s == "CUMULATIVE_RETRIEVAL")
    miscon_addressed = sum(1 for s in slide_states if s == "MISCONCEPTION")
    checks = sum(1 for s in slide_states if s in ("RETRIEVAL", "ASSESSMENT", "CUMULATIVE_RETRIEVAL"))
    total = len(plan.learning_objectives)
    coverage = round(100.0 * len(assessed) / total, 1) if total else 0.0
    warnings = list(plan.safety_warnings)
    if total and len(practiced) < total:
        missing = [o.id for o in plan.learning_objectives if o.id not in practiced]
        warnings.append(f"{', '.join(missing)} has limited independent practice.")
    status = "PASS"
    if warnings:
        status = "WARN"
    if total and (len(slide_objs) < total or coverage < 50.0):
        status = "FAIL"
    return PedagogicalQAReport(
        objectives_total=total,
        objectives_taught=len([o for o in plan.learning_objectives if o.id in slide_objs]),
        objectives_practiced=len(practiced),
        objectives_assessed=len(assessed),
        prerequisites_identified=len(plan.prerequisites),
        prerequisites_addressed=1 if "PRIOR_KNOWLEDGE" in slide_states else 0,
        worked_examples=len(plan.worked_examples),
        guided_practice_items=sum(1 for s in slide_states if s in ("GUIDED_EXAMPLE", "GUIDED_PRACTICE")),
        independent_practice_items=sum(1 for s in slide_states if s == "INDEPENDENT_PRACTICE"),
        retrieval_opportunities=retrieval,
        cumulative_retrieval=cumulative,
        misconceptions_identified=len(plan.misconceptions),
        misconceptions_addressed=miscon_addressed,
        formative_checks=checks,
        assessment_coverage_percent=coverage,
        warnings=warnings,
        status=status,
    )
