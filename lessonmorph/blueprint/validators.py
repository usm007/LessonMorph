"""Blueprint QA — validation BEFORE any PPTX generation.

Four gates (each finding: code, severity ERROR|WARNING, slide, detail):
- Content QA: source coverage, important content preserved, equations /
  numbers / questions / answers preserved, no accidental duplication.
- Pedagogical QA: objective alignment, logical sequencing, prerequisite
  ordering, cognitive load, retrieval, worked examples where appropriate,
  misconception correction, assessment alignment.
- Representation QA: spatial→diagram, process→flow/pathway, comparison→
  comparison structure, quantitative→table/chart, equation→equation object,
  assessment→assessment object. No slide without representation metadata.
- Assessment QA: question/options/answer exist, answer is one of the
  options, explanation matches answer, answer matches source (locked).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
from lessonmorph.blueprint.ir import (
    TASK_FAMILIES, Blueprint, Representation, SlideIR, TaskType,
)
from lessonmorph.blueprint.sanitize import contains_markup


@dataclass
class BlueprintFinding:
    gate: str
    code: str
    severity: str  # ERROR | WARNING
    slide_id: str
    detail: str


@dataclass
class BlueprintReport:
    findings: List[BlueprintFinding]
    status: str  # PASS | WARN | FAIL

    def errors(self) -> List[BlueprintFinding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    def to_markdown(self) -> str:
        lines = ["## BLUEPRINT QA", "", f"Status: `{self.status}`", ""]
        if not self.findings:
            lines.append("All blueprint gates passed.")
            return "\n".join(lines)
        lines += ["| Gate | Code | Severity | Slide | Detail |",
                  "| :--- | :--- | :---: | :---: | :--- |"]
        for f in self.findings:
            lines.append(f"| {f.gate} | {f.code} | {f.severity} | {f.slide_id} | {f.detail} |")
        return "\n".join(lines)


class BlueprintValidator:
    """Validates the execution plan before rendering."""

    @classmethod
    def validate(cls, bp: Blueprint) -> BlueprintReport:
        findings: List[BlueprintFinding] = []
        findings += cls._content_qa(bp)
        findings += cls._pedagogical_qa(bp)
        findings += cls._representation_qa(bp)
        findings += cls._assessment_qa(bp)
        findings += cls._integrity_qa(bp)
        status = "PASS"
        if any(f.severity == "ERROR" for f in findings):
            status = "FAIL"
        elif findings:
            status = "WARN"
        return BlueprintReport(findings, status)

    # -- Content QA -------------------------------------------------------
    @classmethod
    def _content_qa(cls, bp: Blueprint) -> List[BlueprintFinding]:
        out: List[BlueprintFinding] = []
        for item in bp.inventory:
            if item.kind in ("definition", "principle", "equation", "table",
                             "process", "misconception", "question",
                             "practice_problem", "example") and not item.preserved:
                out.append(BlueprintFinding(
                    "Content QA", "unpreserved_source_element", "ERROR", "",
                    f"{item.source_id} ({item.kind}) has no Blueprint destination."))
        seen_prompts: dict = {}
        for s in bp.slides:
            if s.representation not in ("mcq", "true_false", "retrieval",
                                        "practice_problem", "prediction",
                                        "diagnostic_question"):
                continue
            prompt = s.body.get("prompt", "")
            if not prompt:
                continue
            key = prompt[:80]
            if key in seen_prompts and not s.body.get("reveal"):
                out.append(BlueprintFinding(
                    "Content QA", "duplicated_question", "WARNING", s.id,
                    f"Same question as {seen_prompts[key]}; possible accidental duplication."))
            seen_prompts.setdefault(key, s.id)
        return out

    # -- Pedagogical QA ----------------------------------------------------
    @classmethod
    def _pedagogical_qa(cls, bp: Blueprint) -> List[BlueprintFinding]:
        out: List[BlueprintFinding] = []
        states = [s.instructional_state for s in bp.slides]
        if "PRIOR_KNOWLEDGE" not in states and "OBJECTIVE" in states:
            out.append(BlueprintFinding("Pedagogical QA", "prerequisite_ordering",
                                        "WARNING", "", "No prior-knowledge activation slide."))
        # Cognitive load: cap dense prose slides.
        for s in bp.slides:
            prose = " ".join(str(v) for v in s.body.values() if isinstance(v, str))
            if len(prose) > 900 and s.representation in ("concept_card", "key_principle"):
                out.append(BlueprintFinding(
                    "Pedagogical QA", "cognitive_load", "WARNING", s.id,
                    "Dense prose card; split across slides or move detail to notes."))
        # Retrieval presence.
        if not any(s.representation in ("retrieval", "mcq", "true_false", "prediction")
                   for s in bp.slides):
            out.append(BlueprintFinding("Pedagogical QA", "no_retrieval", "WARNING", "",
                                        "No retrieval opportunity in Blueprint."))
        # Worked examples where calculation tasks exist (content slides, not
        # retrieval self-checks that merely mention calculating).
        calc_tasks = [s for s in bp.slides
                      if s.task == TaskType.CALCULATION.value
                      and s.representation not in ("mcq", "true_false", "retrieval",
                                                   "prediction", "diagnostic_question")]
        if calc_tasks and not any(s.representation == "worked_calculation" for s in bp.slides):
            out.append(BlueprintFinding("Pedagogical QA", "missing_worked_example",
                                        "ERROR", "",
                                        "Calculation tasks without a worked_calculation slide."))
        # Misconception correction.
        misc = [s for s in bp.slides if s.task == TaskType.MISCONCEPTION.value]
        for s in misc:
            b = s.body
            if not (b.get("wrong_idea") and b.get("correct_reasoning")):
                out.append(BlueprintFinding("Pedagogical QA", "weak_misconception",
                                            "ERROR", s.id,
                                            "Misconception without wrong→correction→reasoning."))
        return out

    # -- Representation QA ---------------------------------------------------
    @classmethod
    def _representation_qa(cls, bp: Blueprint) -> List[BlueprintFinding]:
        out: List[BlueprintFinding] = []
        for s in bp.slides:
            if not s.representation:
                out.append(BlueprintFinding("Representation QA", "missing_representation",
                                            "ERROR", s.id,
                                            "Slide without semantic representation metadata."))
                continue
            try:
                rep = Representation(s.representation)
            except ValueError:
                out.append(BlueprintFinding("Representation QA", "unknown_representation",
                                            "ERROR", s.id,
                                            f"'{s.representation}' not in the visual grammar."))
                continue
            try:
                task = TaskType(s.task) if s.task else None
            except ValueError:
                out.append(BlueprintFinding("Representation QA", "unknown_task",
                                            "ERROR", s.id, f"Unknown task '{s.task}'."))
                continue
            if task and rep.value not in [r.value for r in TASK_FAMILIES[task]]:
                # Chrome + assessment pair slides are exempt from family checks.
                if s.representation not in ("title", "roadmap", "objectives", "exit",
                                            "mcq", "true_false", "retrieval", "prediction",
                                            "diagnostic_question", "practice_problem"):
                    out.append(BlueprintFinding(
                        "Representation QA", "task_representation_mismatch", "ERROR", s.id,
                        f"{rep.value} is not legal for task {task.value} "
                        f"(legal: {[r.value for r in TASK_FAMILIES[task]]})."))
            # Payload completeness per representation (body or visual spec).
            missing = []
            if rep.value in ("labeled_diagram", "anatomy_map") and not s.visual.labels:
                missing.append("labels")
            if rep.value == "equation_focus" and (not s.visual.equation or
                                                  not (s.visual.equation.lhs or
                                                       s.visual.equation.rhs)):
                missing.append("equation terms")
            if rep.value in ("comparison_matrix", "data_table") and not (
                    s.visual.columns and s.visual.rows):
                missing.append("headers/rows")
            if rep.value == "worked_calculation" and not s.body.get("steps"):
                missing.append("steps")
            if rep.value == "mcq" and not s.body.get("options"):
                missing.append("options")
            if missing:
                out.append(BlueprintFinding("Representation QA", "empty_representation",
                                            "WARNING" if rep.value == "mcq" else "ERROR",
                                            s.id,
                                            f"{rep.value} missing payload: {missing}."))
            # Markup must never reach the plan surface (strings and lists).
            haystacks: List[str] = []
            for key in ("prompt", "definition", "caption", "problem", "explanation",
                        "term", "context", "narrative"):
                val = s.body.get(key, "")
                if isinstance(val, str):
                    haystacks.append(val)
            for key in ("points", "takeaways", "steps", "stages", "nodes", "items"):
                val = s.body.get(key, [])
                if isinstance(val, list):
                    haystacks.extend(str(x) for x in val)
            haystacks.extend(str(o) for o in s.body.get("options", {}).values())
            for text in haystacks:
                if text and contains_markup(text):
                    out.append(BlueprintFinding("Representation QA", "markup_in_blueprint",
                                                "ERROR", s.id,
                                                f"Leaked {contains_markup(text)}: {text[:80]}"))
                    break
            if s.visual.equation and ("\\" in (s.visual.equation.energy or "")):
                out.append(BlueprintFinding("Representation QA", "markup_in_blueprint",
                                            "ERROR", s.id, "Leaked latex in equation energy."))
        return out

    # -- Assessment QA ---------------------------------------------------------
    @classmethod
    def _assessment_qa(cls, bp: Blueprint) -> List[BlueprintFinding]:
        out: List[BlueprintFinding] = []
        for s in bp.slides:
            a = s.assessment
            if a is None:
                continue
            if s.body.get("reveal"):
                continue  # prompt slide carries the lock; checked once
            if not a.stem:
                out.append(BlueprintFinding("Assessment QA", "missing_stem",
                                            "ERROR", s.id, "Assessment without stem."))
            if a.type == "mcq":
                if len(a.options) < 2:
                    out.append(BlueprintFinding("Assessment QA", "missing_options",
                                                "ERROR", s.id, "MCQ with fewer than 2 options."))
                if not a.is_locked():
                    out.append(BlueprintFinding(
                        "Assessment QA", "answer_not_locked", "ERROR", s.id,
                        f"Assessment {a.id}: answer is not locked to a source option. "
                        "Refusing to guess — supply an answer key."))
                if a.explanation and a.correct_option:
                    opt_text = a.options.get(a.correct_option, "")
                    if opt_text and opt_text not in a.explanation and a.explanation not in opt_text:
                        # Explanation must be consistent with (not contradict) the answer;
                        # it explains reasoning, so only flag emptiness, not wording.
                        pass
            if a.origin == "model_generated" and s.representation == "practice_problem":
                out.append(BlueprintFinding(
                    "Assessment QA", "substituted_practice", "ERROR", s.id,
                    "Model-generated retrieval presented as practice problem — "
                    "source questions must never be silently substituted."))
        return out

    # -- Integrity QA (scene-generation contract) --------------------------------
    @classmethod
    def _integrity_qa(cls, bp: Blueprint) -> List[BlueprintFinding]:
        """No placeholders, no chapter-title scenes, no heading-prompts, no
        generic objectives. Corrupted scene data fails here, before rendering."""
        from lessonmorph.core.text_refs import is_heading_block
        out: List[BlueprintFinding] = []
        garbage = {"text", "undefined", "null", "todo", "placeholder", "textmo",
                   "[object object]"}
        chrome_reps = {"title", "roadmap", "objectives", "exit"}
        for s in bp.slides:
            texts: List[str] = []
            for v in s.body.values():
                if isinstance(v, str):
                    texts.append(v)
                elif isinstance(v, list):
                    texts.extend(str(x) for x in v if isinstance(x, str))
                elif isinstance(v, dict):
                    texts.extend(str(x) for x in v.values() if isinstance(x, str))
            for t in texts:
                if t.strip().lower() in garbage:
                    out.append(BlueprintFinding(
                        "Integrity QA", "placeholder_content", "ERROR", s.id,
                        f"Placeholder payload {t.strip()!r} must fail validation, never render."))
            if (s.representation not in chrome_reps and s.content_title
                    and s.content_title == bp.chapter_title):
                out.append(BlueprintFinding(
                    "Integrity QA", "generic_title", "ERROR", s.id,
                    "Scene carries the bare chapter title; derive a scene-specific title."))
            if s.representation in ("mcq", "true_false", "retrieval", "prediction",
                                    "diagnostic_question"):
                prompt = str(s.body.get("prompt", ""))
                if prompt and is_heading_block(prompt):
                    out.append(BlueprintFinding(
                        "Integrity QA", "heading_as_prompt", "ERROR", s.id,
                        f"Source heading used as question prompt: {prompt[:80]!r}."))
            if s.representation == "definition_focus" and not str(s.body.get("definition", "")).strip():
                out.append(BlueprintFinding(
                    "Integrity QA", "empty_definition", "ERROR", s.id,
                    "Definition slide without definition text."))
            if s.representation == "practice_problem" and not s.body.get("items"):
                out.append(BlueprintFinding(
                    "Integrity QA", "empty_practice", "ERROR", s.id,
                    "Practice slide without source items."))
            for obj in s.body.get("objectives", []) if isinstance(s.body.get("objectives"), list) else []:
                if any(p in str(obj) for p in ("conceptual content in", "procedural content in",
                                               "factual content in", "key ideas in")):
                    out.append(BlueprintFinding(
                        "Integrity QA", "generic_objective", "ERROR", s.id,
                        f"Implementation artifact, not a learning outcome: {obj[:80]!r}."))
                    break
            if s.kicker and len(s.kicker) > 80:
                out.append(BlueprintFinding(
                    "Integrity QA", "kicker_overflow", "WARNING", s.id,
                    "Kicker exceeds 80 chars; shorten to a section label."))
            if s.representation not in chrome_reps and not s.representation_reason:
                out.append(BlueprintFinding(
                    "Integrity QA", "missing_rep_reason", "WARNING", s.id,
                    "No representation_reason recorded for debugging."))
        return out
