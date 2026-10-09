"""Pedagogy → Presentation-IR adapter (the compiler).

Treats PedagogicalPlan + ChapterPlan output as AUTHORITATIVE:
input = decisions already made (sequence, objectives, strategies,
retrieval, misconceptions, worked examples, assessments).
Output = executable Blueprint. This module contains NO pedagogical logic —
only deterministic translation: task classification → representation choice
(within the task's legal family) → structured payloads.

Architectural question answered here: "How do we turn an already-decided
teaching strategy into an executable presentation?"
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from lessonmorph.blueprint.ir import (
    Blueprint,
    DEFAULT_REPRESENTATION,
    TASK_FAMILIES,
    EquationIR,
    EquationTerm,
    InventoryItem,
    LockedAssessment,
    Representation,
    SlideIR,
    TaskType,
    TeacherAction,
    VisualSpec,
)
from lessonmorph.blueprint.sanitize import clean, latex_to_unicode
from lessonmorph.core.models import (
    ChapterPlan,
    ContentType,
    ContentUnit,
    PedagogicalPlan,
    QuestionType,
    QuizQuestion,
    TeachingMove,
)
from lessonmorph.core.text_refs import (
    clip_sentences,
    clip_words,
    extract_term,
    first_sentences,
    is_heading_block,
    leading_label,
    section_topic,
    short_headline,
    strip_markup_line,
)
from lessonmorph.ledger.ledger import ContentCompletenessLedger

# ---------------------------------------------------------------------------
# Semantic task taxonomy (deterministic cues — classification, not pedagogy)
# ---------------------------------------------------------------------------

_PROCESS_CUES = ("trace", "path of", "pathway", "steps", "stages", "first",
                 "then", "cycle", "flow of", "sequence", "phase")
_COMPARISON_CUES = ("contrast", "compare", "versus", " vs ", "difference between",
                    "c3", "c4", "advantage", "while", "whereas")
_MECHANISM_CUES = ("how ", "site of", "converts", "via", "through", "transport",
                   "mechanism", "housing", "established", "compartment")
_CALC_CUES = ("calculate", "compute", "determine the", "moles", "yield",
              "efficiency", "how much", "solve")
_STRUCTURE_CUES = ("architecture", "membrane system", "stroma", "lumen",
                   "compartments", "structure", "components", "consists of")


def classify_task(unit: ContentUnit, move_state: str = "") -> TaskType:
    """Map a content unit to its cognitive task. Structure follows this."""
    text = unit.normalized_content
    low = text.lower()
    ctype = unit.content_type

    if move_state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL"):
        return TaskType.RETRIEVAL
    if ctype == ContentType.MISCONCEPTION:
        return TaskType.MISCONCEPTION
    if ctype == ContentType.TABLE:
        return TaskType.EXPERIMENTAL_DATA
    if _parse_markdown_table(text)[0]:
        return TaskType.EXPERIMENTAL_DATA
    if ctype == ContentType.DIAGRAM:
        return TaskType.DIAGRAM_INTERPRETATION
    if ctype == ContentType.DEFINITION:
        return TaskType.DEFINITION
    if ctype in (ContentType.EXAMPLE, ContentType.WORKED_STEP):
        if any(w in low for w in ("contrast", "compare")):
            return TaskType.COMPARISON
        if re.search(r"\d", text) and any(w in low for w in _CALC_CUES + ("mol", "=", "/")):
            return TaskType.CALCULATION
        if any(w in low for w in _PROCESS_CUES):
            return TaskType.PROCESS
        return TaskType.PROCEDURE
    if ctype == ContentType.FORMULA:
        if any(w in low for w in ("step", "compute", "moles of", "substitute")):
            return TaskType.CALCULATION
        return TaskType.DERIVATION
    if ctype == ContentType.EXERCISE:
        if re.match(r"\s*[A-D]\)", text, re.MULTILINE) or "?" in text and re.search(
                r"\b(what|which)\b.*\?", low):
            if any(w in low for w in ("immediate", "predict", "would happen", "what happens",
                                      "consequence")):
                return TaskType.PREDICTION
        if any(w in low for w in ("trace", "path of")):
            return TaskType.PROCESS
        if any(w in low for w in ("contrast", "compare")):
            return TaskType.COMPARISON
        if any(w in low for w in _CALC_CUES):
            return TaskType.CALCULATION
        return TaskType.APPLICATION
    # EXPLANATION / CONTEXT / TERMINOLOGY
    if _has_structure(text):
        return TaskType.MECHANISM
    if any(w in low for w in _COMPARISON_CUES) and ("?" in text or "contrast" in low):
        return TaskType.COMPARISON
    if any(w in low for w in _PROCESS_CUES):
        return TaskType.PROCESS
    if any(w in low for w in _MECHANISM_CUES):
        return TaskType.MECHANISM
    return TaskType.CONCEPT


def question_task(prompt: str) -> TaskType:
    low = prompt.lower()
    if any(w in low for w in ("trace", "path of")):
        return TaskType.PROCESS
    if any(w in low for w in ("contrast", "compare")):
        return TaskType.COMPARISON
    if any(w in low for w in ("immediate", "predict", "consequence", "what happens")):
        return TaskType.PREDICTION
    if any(w in low for w in _CALC_CUES):
        return TaskType.CALCULATION
    return TaskType.RETRIEVAL


# ---------------------------------------------------------------------------
# Representation selection (MUST stay inside the task's legal family)
# ---------------------------------------------------------------------------

def select_representation(task: TaskType, unit: ContentUnit,
                          move_state: str = "") -> Representation:
    text = unit.normalized_content
    low = text.lower()
    if move_state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL"):
        return Representation.RETRIEVAL
    if task == TaskType.MISCONCEPTION:
        return Representation.CONTRAST
    if task == TaskType.DIAGRAM_INTERPRETATION or (
            task == TaskType.MECHANISM and any(w in low for w in _STRUCTURE_CUES)):
        return Representation.LABELED_DIAGRAM
    if task == TaskType.DERIVATION or ("$$" in text and task != TaskType.CALCULATION):
        return Representation.EQUATION_FOCUS
    if task == TaskType.CALCULATION:
        return Representation.WORKED_CALCULATION
    if task == TaskType.EXPERIMENTAL_DATA:
        headers = unit.metadata.get("headers", [])
        head = " ".join(headers).lower()
        # Two named entities compared across attributes -> comparison matrix.
        if len(headers) >= 3 and not any(w in head for w in ("peak", "relative", "%", "nm")):
            return Representation.COMPARISON_MATRIX
        return Representation.DATA_TABLE
    if task == TaskType.PROCESS:
        if "cycle" in low:
            return Representation.CYCLE
        return Representation.PATHWAY
    if task == TaskType.COMPARISON and unit.content_type == ContentType.EXERCISE:
        return Representation.PRACTICE_PROBLEM
    if task == TaskType.PROCESS and unit.content_type == ContentType.EXERCISE:
        return Representation.PRACTICE_PROBLEM
    if task == TaskType.APPLICATION and unit.content_type == ContentType.EXERCISE:
        return Representation.PRACTICE_PROBLEM
    if task == TaskType.PREDICTION and re.search(r"^\s*[A-D]\)", text, re.MULTILINE):
        return Representation.MCQ
    rep = DEFAULT_REPRESENTATION[task]
    assert rep in TASK_FAMILIES[task], f"{rep} not legal for {task}"
    return rep


# ---------------------------------------------------------------------------
# Structured equations (never raw LaTeX downstream)
# ---------------------------------------------------------------------------

_ARROWS = ("\\longrightarrow", "\\rightarrow", "\\Rightarrow", "⟶", "→", "-->")


def _split_equation_block(block: str) -> Tuple[str, str]:
    for a in _ARROWS:
        if a in block:
            left, _, right = block.partition(a)
            return left, right
    return block, ""


def _parse_term(chunk: str) -> EquationTerm:
    t = latex_to_unicode(chunk).strip().strip("+").strip()
    m = re.match(r"^([\d.]+)\s*(.*)$", t)
    if m and m.group(2):
        return EquationTerm(coefficient=m.group(1), species=m.group(2).strip())
    return EquationTerm(species=t)


def structure_equation(text: str, legend_lines: Optional[List[str]] = None) -> EquationIR:
    """Parse a $$..$$ (or inline) equation into structured terms + legend."""
    m = re.search(r"\$\$(.+?)\$\$", text, re.DOTALL)
    block = m.group(1) if m else text
    left, right = _split_equation_block(block)
    energy = ""
    lhs_terms: List[EquationTerm] = []
    for chunk in re.split(r"(?<!\\)\+", left):
        term = _parse_term(chunk)
        if "light" in term.species.lower() or "energy" in term.species.lower():
            energy = term.species
            continue
        if term.species:
            lhs_terms.append(term)
    rhs_terms = [_parse_term(c) for c in re.split(r"(?<!\\)\+", right) if _parse_term(c).species]
    notes = {t.species: t.note for t in lhs_terms + rhs_terms}
    for line in legend_lines or []:
        lm = re.match(r"[-•]?\s*(.+?)\s+represents\s+(.+)", latex_to_unicode(line).strip())
        if not lm:
            continue
        key = lm.group(1).strip()
        for term in lhs_terms + rhs_terms:
            if _legend_match(key, term.species):
                term.note = lm.group(2).strip()
    return EquationIR(lhs=lhs_terms, energy=energy, arrow="→", rhs=rhs_terms,
                      raw_source=text[:300])


# ---------------------------------------------------------------------------
# Locked assessments (SOURCE → LOCKED KEY → IR; never re-solved downstream)
# ---------------------------------------------------------------------------

def parse_mcq_options(text: str) -> Tuple[str, Dict[str, str]]:
    """Split source MCQ text into (stem, {letter: option})."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    stem_lines: List[str] = []
    options: Dict[str, str] = {}
    for line in lines:
        m = re.match(r"^([A-D])\)\s*(.+)$", line)
        if m:
            options[m.group(1)] = latex_to_unicode(m.group(2)).strip()
        elif not options:
            stem_lines.append(line)
    stem = latex_to_unicode(" ".join(stem_lines))
    stem = re.sub(r"^(Question|Exercise|Check for Understanding)\s*:\s*", "", stem,
                  flags=re.IGNORECASE)
    return stem.strip(), options


def load_answer_key(path: Optional[Path | str]) -> List[Dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("assessments", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def lock_assessment(question: QuizQuestion, unit: Optional[ContentUnit],
                    answer_keys: List[Dict[str, Any]]) -> LockedAssessment:
    """Lock ONE answer from source material. Unresolvable → unlocked (QA ERROR)."""
    text = unit.normalized_content if unit else question.prompt
    origin = "source" if (unit and unit.content_type == ContentType.EXERCISE) else "model_generated"
    if question.question_type == QuestionType.MULTIPLE_CHOICE or re.search(
            r"^\s*[A-D]\)", text, re.MULTILINE):
        stem, options = parse_mcq_options(text)
        correct, explanation, anchor = "", question.explanation, ""
        for key in answer_keys:
            if key.get("match", "").lower() in (stem + " " + question.prompt).lower():
                correct, explanation = key.get("correct_option", ""), key.get(
                    "explanation", explanation)
                anchor = key.get("source_anchor", "")
                origin = "source"
                break
        if not correct:
            # Pedagogy-provided answer (authoritative) mapped onto option letters.
            given = latex_to_unicode(question.correct_answer).strip()
            for letter, opt in options.items():
                if given and (given == opt or given.rstrip(")") == letter
                              or given.startswith(letter + ")")
                              or opt in given or given in opt):
                    correct = letter
                    break
        return LockedAssessment(
            id=f"{question.id}_{(unit.id if unit else 'gen')}".lower().replace(" ", "_"),
            type="mcq", stem=clean(stem) or clean(question.prompt),
            options={k: clean(v) for k, v in options.items()},
            correct_option=correct, explanation=clean(explanation),
            source_anchor=anchor or (unit.source_location if unit else ""),
            origin=origin, objective_ids=list(question.objective_ids))
    if question.question_type == QuestionType.TRUE_FALSE:
        return LockedAssessment(
            id=f"{question.id}_tf", type="true_false",
            stem=clean(question.prompt),
            options={"A": "True", "B": "False"},
            correct_option="A" if "true" in latex_to_unicode(
                question.correct_answer).lower() else "B",
            explanation=clean(question.explanation), origin=origin,
            objective_ids=list(question.objective_ids))
    return LockedAssessment(
        id=f"{question.id}_sa", type="short_answer",
        stem=clean(question.prompt), options={},
        correct_option="", explanation=clean(question.explanation),
        origin=origin, objective_ids=list(question.objective_ids))


# ---------------------------------------------------------------------------
# Blueprint compiler
# ---------------------------------------------------------------------------

_INVENTORY_KIND = {
    ContentType.DEFINITION: "definition",
    ContentType.FORMULA: "equation",
    ContentType.TABLE: "table",
    ContentType.DIAGRAM: "process",
    ContentType.EXAMPLE: "example",
    ContentType.WORKED_STEP: "example",
    ContentType.EXERCISE: "practice_problem",
    ContentType.MISCONCEPTION: "misconception",
    ContentType.EXPLANATION: "principle",
    ContentType.TERMINOLOGY: "terminology",
    ContentType.WARNING: "principle",
    ContentType.EXCEPTION: "principle",
    ContentType.CONTEXT: "principle",
    ContentType.FOOTNOTE: "principle",
}

_CHROME = {
    "HOOK": (Representation.TITLE, "title"),
    "PRIOR_KNOWLEDGE": (Representation.CONCEPT_CARD, "prior_knowledge"),
    "OBJECTIVE": (Representation.OBJECTIVES, "objectives"),
    "RECAP": (Representation.BIG_PICTURE, "recap"),
}


class BlueprintCompiler:
    """Compiles (PedagogicalPlan, ChapterPlan, ledger) → Blueprint.

    Reads pedagogy as authoritative; every choice here is translation.
    """

    def __init__(self, ledger: ContentCompletenessLedger,
                 answer_key_path: Optional[Path | str] = None):
        self.ledger = ledger
        self.answer_keys = load_answer_key(answer_key_path)

    # -- public -----------------------------------------------------------
    def compile(self, plan: ChapterPlan) -> Blueprint:
        ped: Optional[PedagogicalPlan] = plan.pedagogical_plan
        units = {u.id: u for u in self.ledger.get_units_by_chapter(plan.id)} or {
            u.id: u for u in self.ledger.units}
        self._units = units
        self._order = [u.id for u in self.ledger.units if u.id in units]
        self._recall_titles: set = set()
        bp = Blueprint(chapter_id=plan.id, chapter_title=plan.title,
                       subject_domain=plan.subject_domain.value)
        for u in units.values():
            practice_worded = bool(re.search(
                r"Practice Problem|Trace the|Contrast the", u.normalized_content))
            bp.inventory.append(InventoryItem(
                source_id=u.id,
                kind="practice_problem" if practice_worded else (
                    "question" if u.content_type == ContentType.EXERCISE and re.search(
                        r"^\s*[A-D]\)", u.normalized_content, re.MULTILINE)
                    else _INVENTORY_KIND.get(u.content_type, "principle"))))
        by_objective: Dict[str, List[QuizQuestion]] = {}
        for q in plan.questions:
            for oid in q.objective_ids:
                by_objective.setdefault(oid, []).append(q)

        n = 0
        used_questions: set = set()
        taught: set = set()  # cids taught by non-assessment slides (no duplication)
        assessed: set = set()  # cids locked into assessments (never re-practiced)
        # Planner's worked-example groups (authoritative grouping, honored below).
        grouped_cid: Dict[str, int] = {}
        work_groups: List[Dict] = ped.worked_examples if ped else []
        for gi, g in enumerate(work_groups):
            for cid in g.get("content_ids", []):
                grouped_cid.setdefault(cid, gi)
        emitted_groups: set = set()
        pending: list = []  # [(text, unit)] header kickers awaiting a slide

        def _attach_kicker(slide_ir: SlideIR) -> None:
            if pending:
                # Kicker is a short section label, never a sentence cut short:
                # if the pending wording cannot fit whole, name its section.
                ptext, pu = pending[-1]
                label = short_headline(ptext, 80)
                if "…" in label or "..." in label:
                    label = section_topic(pu.section_title or "") or ""
                slide_ir.kicker = label
                for _, pu in pending:
                    _claim(pu, slide_ir.id)
                pending.clear()

        def _next_id() -> str:
            nonlocal n
            n += 1
            return f"slide_{n:02d}"

        def _claim(u: ContentUnit, sid: str, teaches: bool = True) -> None:
            u.mark_covered(sid)
            if teaches:
                taught.add(u.id)
            for item in bp.inventory:
                if item.source_id == u.id:
                    item.slide_id = sid if not item.slide_id else item.slide_id + f"+{sid}"
                    item.preserved = True

        def _lock_and_emit(q: QuizQuestion, move: TeachingMove, state: str) -> None:
            """Lock one assessment and emit its prompt+reveal slides."""
            used_questions.add(q.id)
            unit = next((units[c] for c in q.source_content_ids if c in units), None)
            locked = lock_assessment(q, unit, self.answer_keys)
            bp.answer_keys.append(locked)
            first = True
            for slide_ir in self._assessment_slides(_next_id, plan, q, locked, state, move):
                bp.slides.append(slide_ir)
                if first:
                    _attach_kicker(slide_ir)
                    first = False
                for c in q.source_content_ids:
                    if c in units:
                        assessed.add(c)
                        _claim(units[c], slide_ir.id, teaches=False)

        sequence = ped.teaching_sequence if ped else []
        if not sequence:
            # No pedagogy: preserve content in source order (translation only).
            for u in units.values():
                task = classify_task(u)
                rep = select_representation(task, u)
                sid = _next_id()
                bp.slides.append(self._content_slide(sid, plan, u, task, rep, [], "EXPLANATION",
                                                    f"Preserve {u.id}"))
                _claim(u, sid)
            return bp

        for move in sequence:
            cids = [c for c in move.content_ids if c in units]
            state = move.state
            if state in _CHROME:
                rep, kind = _CHROME[state]
                sid = _next_id()
                bp.slides.append(self._chrome_slide(sid, plan, ped, move, rep, kind))
            elif state in ("EXPLANATION", "VISUAL_MODEL", "DEEPER_EXPLANATION"):
                for cid in cids:
                    if cid in taught:
                        continue
                    u = units[cid]
                    if u.content_type == ContentType.HEADING:
                        # Structure, not content: forwarded as kicker context
                        # (claimed on attach; trailing ones attach at sweep end).
                        pending.append((clean(u.normalized_content), u))
                        continue
                    if (_is_header_only(u.normalized_content)
                            and not _has_equation(u.normalized_content)):
                        # Section header, not a slide: forward as kicker subtitle.
                        pending.append((clean(u.normalized_content)[:160], u))
                        continue
                    if _is_calc_material(u):
                        # One calculation, one slide: merge the consecutive run
                        # (setup + steps) instead of fragmenting across slides.
                        run = [cid]
                        pos = self._order.index(cid) if cid in self._order else -1
                        for nid in self._order[pos + 1:]:
                            nu = units.get(nid)
                            if nu is None or nid in taught or not _is_calc_material(nu):
                                break
                            run.append(nid)
                        if len(run) > 1:
                            sid = _next_id()
                            run_units = [units[c] for c in run]
                            slide_ir = self._worked_slide(
                                sid, plan, run_units, TaskType.CALCULATION,
                                Representation.WORKED_CALCULATION, move.objective_ids,
                                state, move.purpose, move.teacher_move)
                            bp.slides.append(slide_ir)
                            _attach_kicker(slide_ir)
                            for ru in run_units:
                                _claim(ru, sid)
                            continue
                    if _is_legend(u.normalized_content) and bp.slides and (
                            bp.slides[-1].representation == "equation_focus"):
                        # Legend lines belong on the equation slide, not alone.
                        _merge_legend(bp.slides[-1], u.normalized_content)
                        _claim(u, bp.slides[-1].id)
                        continue
                    if u.content_type == ContentType.EXERCISE:
                        # Source questions are never prose slides: lock or practice them.
                        sid = _next_id()
                        q = next((qq for qq in plan.questions
                                  if cid in qq.source_content_ids), None)
                        if q is not None and (
                                re.search(r"^\s*[A-D]\)", u.normalized_content, re.MULTILINE)
                                or q.question_type in (QuestionType.MULTIPLE_CHOICE,
                                                       QuestionType.TRUE_FALSE)):
                            if q.id in used_questions or cid in assessed:
                                continue  # already locked elsewhere — never duplicate
                            _lock_and_emit(q, move, state)
                            taught.add(cid)
                        elif cid not in assessed and not _is_header_only(u.normalized_content):
                            task = classify_task(u, state)
                            slide_ir = self._practice_slide(
                                sid, plan, u, task, move.objective_ids, state,
                                move.purpose, move.teacher_move)
                            bp.slides.append(slide_ir)
                            _attach_kicker(slide_ir)
                            for cid2 in slide_ir.source_ids:
                                if cid2 in units:
                                    _claim(units[cid2], sid)
                        continue
                    if cid in grouped_cid and grouped_cid[cid] not in emitted_groups:
                        # Honor the planner's worked-example grouping (one calculation,
                        # one slide) instead of fragmenting steps across slides.
                        gi = grouped_cid[cid]
                        g = work_groups[gi]
                        g_units = [units[c] for c in g.get("content_ids", []) if c in units]
                        if g_units and any(x.content_type in (ContentType.EXAMPLE,
                                                              ContentType.WORKED_STEP,
                                                              ContentType.FORMULA)
                                           for x in g_units):
                            emitted_groups.add(gi)
                            sid = _next_id()
                            first = g_units[0]
                            task = classify_task(first, state)
                            if task != TaskType.CALCULATION:
                                task = TaskType.CALCULATION
                            slide_ir = self._worked_slide(
                                sid, plan, g_units, task,
                                Representation.WORKED_CALCULATION, move.objective_ids,
                                state, move.purpose, move.teacher_move)
                            bp.slides.append(slide_ir)
                            _attach_kicker(slide_ir)
                            for gu in g_units:
                                _claim(gu, sid)
                            continue
                    task = classify_task(u, state)
                    rep = select_representation(task, u, state)
                    sid = _next_id()
                    slide_ir = self._content_slide(
                        sid, plan, u, task, rep, move.objective_ids, state, move.purpose,
                        teacher_move=move.teacher_move)
                    bp.slides.append(slide_ir)
                    _attach_kicker(slide_ir)
                    for cid2 in slide_ir.source_ids:
                        if cid2 in units:
                            _claim(units[cid2], sid)
            elif state == "GUIDED_EXAMPLE":
                grouped = [units[c] for c in cids if c in units and c not in taught]
                if not grouped:
                    continue
                if not any(x.content_type == ContentType.WORKED_STEP for x in grouped) and not any(
                        _extract_stages(x.normalized_content) for x in grouped):
                    first_task = classify_task(grouped[0], state)
                    if first_task in (TaskType.PROCESS, TaskType.COMPARISON,
                                      TaskType.APPLICATION, TaskType.PROCEDURE):
                        # Source tasks for students (trace/contrast/apply), not worked
                        # examples: practice them task-typed, never force a template.
                        for x in grouped:
                            if x.id in assessed or _is_header_only(x.normalized_content):
                                continue
                            task = classify_task(x, state)
                            sid = _next_id()
                            slide_ir = self._practice_slide(
                                sid, plan, x, task, move.objective_ids, state, move.purpose,
                                move.teacher_move, faded=True)
                            bp.slides.append(slide_ir)
                            _attach_kicker(slide_ir)
                            _claim(x, sid)
                        continue
                first = grouped[0]
                task = classify_task(first, state)
                rep = select_representation(task, first, state)
                sid = _next_id()
                slide_ir = self._worked_slide(sid, plan, grouped, task, rep,
                                              move.objective_ids, state, move.purpose,
                                              move.teacher_move)
                bp.slides.append(slide_ir)
                _attach_kicker(slide_ir)
                for u in grouped:
                    _claim(u, sid)
            elif state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL", "ASSESSMENT"):
                qs = self._move_questions(move, by_objective, plan.questions, used_questions,
                                          state == "ASSESSMENT")
                qs = [q for q in qs if _is_askable(q)]
                if qs and state != "CUMULATIVE_RETRIEVAL":
                    for q in qs:
                        _lock_and_emit(q, move, state)
                else:
                    cids_named = [c for c in cids if c in units
                                  and not _is_header_only(units[c].normalized_content)]
                    # One probe, one target. The target is a TOPIC the source
                    # itself names — never a slice of source prose. "reconstruct
                    # Where:." and "reconstruct <half a sentence>…" are not
                    # prompts; a student can act on "about the chloroplast".
                    verb = "Revisit" if state == "CUMULATIVE_RETRIEVAL" else "Recall"
                    topic = self._recall_topic(cids_named, units, verb)
                    if topic is None:
                        topic = section_topic(plan.title) or "the key ideas"
                    ask = (f"Come back to {topic} now: state it again in your own words."
                           if verb == "Revisit" else
                           f"Without looking back: what do you remember about {topic}?")
                    sid = _next_id()
                    slide_ir = SlideIR(
                        id=sid, purpose=move.purpose,
                        concept_title=topic, task=TaskType.RETRIEVAL.value,
                        learning_goal=[f"recall {topic} from memory"],
                        representation=Representation.RETRIEVAL.value,
                        content_title=f"{verb}: {topic}",
                        body={"prompt": ask,
                              "origin": "model_generated"},
                        reveal_sequence=["prompt", "response"],
                        teacher_action=TeacherAction(type="prompt", prompt=move.teacher_move),
                        source_ids=list(cids), objective_ids=list(move.objective_ids),
                        instructional_state=state,
                        representation_reason="retrieval move with no unused question -> topic recall prompt",
                        pedagogical_ref=f"{plan.id}:{state}")
                    bp.slides.append(slide_ir)
                    _attach_kicker(slide_ir)
                    for c in cids:
                        _claim(units[c], sid, teaches=False)
            elif state == "MISCONCEPTION":
                for m in (ped.misconceptions if ped else [])[:2]:
                    srcs = [m["source_unit_id"]] if m.get("source_unit_id") else list(cids)
                    if srcs and all(c in taught for c in srcs if c in units):
                        continue  # already confronted with full assembly — never duplicate
                    sid = _next_id()
                    slide_ir = self._misconception_slide(sid, plan, m, move, units)
                    bp.slides.append(slide_ir)
                    _attach_kicker(slide_ir)
                    for cid2 in slide_ir.source_ids:
                        if cid2 in units:
                            _claim(units[cid2], sid)
            elif state in ("GUIDED_PRACTICE", "INDEPENDENT_PRACTICE"):
                for u in [units[c] for c in cids if c in units
                          and units[c].content_type == ContentType.EXERCISE]:
                    if u.id in assessed or u.id in taught or _is_header_only(u.normalized_content):
                        continue  # locked as assessment, taught, or header-only
                    task = classify_task(u, state)
                    sid = _next_id()
                    slide_ir = self._practice_slide(
                        sid, plan, u, task, move.objective_ids, state, move.purpose,
                        move.teacher_move, faded=state == "GUIDED_PRACTICE")
                    bp.slides.append(slide_ir)
                    _attach_kicker(slide_ir)
                    _claim(u, sid)
                if state == "INDEPENDENT_PRACTICE" and not any(
                        s.instructional_state == state for s in bp.slides):
                    # Source practice already placed elsewhere;
                    # do NOT invent replacements — reuse unassessed source items only.
                    src_ids = [u.id for u in units.values()
                               if u.content_type == ContentType.EXERCISE
                               and u.id not in assessed
                               and not _is_header_only(u.normalized_content)]
                    if src_ids:
                        sid = _next_id()
                        slide_ir = SlideIR(
                            id=sid, purpose=move.purpose, concept_title="Independent Practice",
                            task=TaskType.APPLICATION.value,
                            learning_goal=["apply the lesson independently"],
                            representation=Representation.PRACTICE_PROBLEM.value,
                            content_title="Independent Practice",
                            body={"items": [clean(units[c].normalized_content) for c in src_ids],
                                  "origin": "source"},
                            reveal_sequence=["problem", "attempt", "verify"],
                            teacher_action=TeacherAction(type="prompt", prompt=move.teacher_move),
                            source_ids=src_ids, objective_ids=list(move.objective_ids),
                            instructional_state=state,
                            representation_reason="unassessed source exercises -> practice set",
                            pedagogical_ref=f"{plan.id}:{state}")
                        bp.slides.append(slide_ir)
                        _attach_kicker(slide_ir)
        # Coverage sweep: every important unit needs a destination (traceability).
        for u in units.values():
            if any(it.source_id == u.id and it.preserved for it in bp.inventory):
                continue
            if _is_header_only(u.normalized_content):
                pending.append((clean(u.normalized_content)[:160], u))
                continue
            task = classify_task(u)
            rep = select_representation(task, u)
            sid = _next_id()
            slide_ir = self._content_slide(
                sid, plan, u, task, rep, [], "EXPLANATION",
                f"coverage sweep: preserve {u.id}")
            bp.slides.append(slide_ir)
            _attach_kicker(slide_ir)
            _claim(u, sid)
        if pending and bp.slides:
            # Headers with no following content: subtitle the last slide, keep destiny.
            last = bp.slides[-1]
            if not last.kicker:
                last.kicker = short_headline(pending[-1][0], 80)
            for _, pu in pending:
                _claim(pu, last.id)
            pending.clear()
        # Exit chrome.
        sid = _next_id()
        bp.slides.append(SlideIR(
            id=sid, purpose="Rapid formative exit check", concept_title="Exit Ticket",
            task=TaskType.RETRIEVAL.value, learning_goal=["surface one takeaway and one question"],
            representation=Representation.EXIT.value, content_title="Exit Ticket",
            body={"prompt_1": "Most important concept from today?",
                  "prompt_2": "One question you still have?"},
            reveal_sequence=["prompt"], source_ids=[], instructional_state="EXIT",
            representation_reason="chrome:exit",
            pedagogical_ref=f"{plan.id}:EXIT"))
        resolve_duplicate_titles(bp, plan, units)
        return bp

    # -- slide builders (translation) --------------------------------------
    def _teacher(self, move_text: str, concept: str, kind: str = "prompt") -> TeacherAction:
        prompt = f"{move_text} — {concept}".strip(" —") if move_text else concept
        return TeacherAction(type=kind, prompt=prompt[:300])

    def _chrome_slide(self, sid: str, plan: ChapterPlan, ped: PedagogicalPlan,
                      move: TeachingMove, rep: Representation, kind: str) -> SlideIR:
        body: Dict[str, Any] = {}
        chrome_title = plan.title
        if kind == "title":
            body = {"unit": plan.subject_domain.value.upper(), "topic": plan.title}
        elif kind == "prior_knowledge":
            body = {"prerequisites": list(plan.prior_knowledge)}
            chrome_title = "Prior Knowledge"
        elif kind == "objectives":
            body = {"objectives": [o.text for o in ped.learning_objectives]}
            chrome_title = "Learning Objectives"
        elif kind == "recap":
            raw = plan.core_concepts[:4] or [f"Mastery of {plan.title}"]
            body = {"takeaways": [clip_sentences(clean(t), 260) for t in raw]}
            chrome_title = "Key Takeaways"
        return SlideIR(id=sid, purpose=move.purpose, concept_title=plan.title,
                       task=TaskType.CONCEPT.value,
                       learning_goal=[o.text for o in ped.learning_objectives[:2]],
                       representation=rep.value, content_title=chrome_title, body=body,
                       reveal_sequence=["title", "detail"],
                       teacher_action=self._teacher(move.teacher_move, plan.title),
                       source_ids=[], objective_ids=list(move.objective_ids),
                       instructional_state=move.state,
                       representation_reason=f"chrome:{kind}",
                       pedagogical_ref=f"{plan.id}:{move.state}")

    def _content_slide(self, sid: str, plan: ChapterPlan, u: ContentUnit, task: TaskType,
                       rep: Representation, oids: List[str], state: str, purpose: str,
                       teacher_move: str = "") -> SlideIR:
        section = (u.section_title or "").strip()
        title = clean(section or plan.title)
        slide_extra_ids: List[str] = []
        # Payload cascade: if the chosen representation has no extractable
        # payload, reclassify to CONCEPT (translation correction, not pedagogy).
        if rep == Representation.EQUATION_FOCUS and not _has_equation(u.normalized_content):
            task, rep = TaskType.CONCEPT, Representation.CONCEPT_CARD
        if rep in (Representation.LABELED_DIAGRAM, Representation.ANATOMY_MAP):
            parts, _ = _extract_structure(u.normalized_content)
            if not parts:
                if task == TaskType.MECHANISM:
                    rep = Representation.CAUSE_EFFECT
                else:
                    task, rep = TaskType.CONCEPT, Representation.CONCEPT_CARD
        if rep in (Representation.PATHWAY, Representation.SEQUENCE, Representation.FLOW,
                   Representation.CYCLE) and not _extract_stages(u.normalized_content):
            task, rep = TaskType.CONCEPT, Representation.CONCEPT_CARD
        body: Dict[str, Any] = {}
        visual = VisualSpec()
        reveal = ["title", "body"]
        if rep == Representation.EQUATION_FOCUS:
            legend = [l for l in u.normalized_content.splitlines() if "represent" in l.lower()]
            eq = structure_equation(u.normalized_content, legend)
            visual = VisualSpec(subject=title, equation=eq)
            body = {"context": clip_sentences(clean(u.original_wording), 200)}
            reveal = ["equation", "terms", "meaning"]
            if title == plan.title and eq is not None:
                # The equation names itself: "6 CO₂ → C₆H₁₂O₆" beats any fallback.
                inline_title = short_headline(eq.inline(), 80)
                if inline_title and len(inline_title) > 4:
                    title = inline_title
        elif rep in (Representation.LABELED_DIAGRAM, Representation.ANATOMY_MAP):
            parts, labels = _extract_structure(u.normalized_content)
            visual = VisualSpec(subject=title, structure=parts, labels=labels)
            body = {"caption": clip_sentences(clean(u.normalized_content), 300)}
            reveal = parts + ["functions"] if parts else ["diagram", "labels"]
        elif rep in (Representation.PATHWAY, Representation.SEQUENCE, Representation.FLOW,
                     Representation.CYCLE):
            stages = _extract_stages(u.normalized_content)
            visual = VisualSpec(subject=title, structure=stages,
                                edges=[{"from": a, "to": b} for a, b in zip(stages, stages[1:])])
            body = {"narrative": clean(u.normalized_content)[:400]}
            reveal = stages or ["stages"]
        elif rep in (Representation.DATA_TABLE, Representation.COMPARISON_MATRIX):
            headers = [clean(h) for h in u.metadata.get("headers", [])]
            rows = [{h: clean(str(v)) for h, v in zip(headers, r)}
                    for r in u.metadata.get("rows", [])]
            if not headers:
                # Markdown table kept as text by ingestion: structure it here.
                headers, raw_rows = _parse_markdown_table(u.normalized_content)
                rows = [{h: clean(str(v)) for h, v in zip(headers, r)} for r in raw_rows]
            visual = VisualSpec(subject=title, columns=headers, rows=rows)
            body = {"title": clean(u.metadata.get("title", ""))}
            reveal = ["headers", "rows", "pattern"]
        elif rep == Representation.DEFINITION_FOCUS:
            term = extract_term(u.normalized_content) or extract_term(u.original_wording)
            full_def = clean(u.normalized_content)
            body = {"term": term or "",
                    "definition": first_sentences(full_def, 2, 260),
                    "detail": full_def}
            if term:
                title = term
        elif rep == Representation.WORKED_CALCULATION:
            problem, steps = _worked_from_unit(u.normalized_content)
            body = {"problem": problem, "givens": _extract_givens(problem),
                    "steps": steps,
                    "verify": "check units, boundary conditions, and result"}
            reveal = ["problem"] + [f"step_{i+1}" for i in range(len(steps))] + ["verify"]
        elif rep == Representation.CONTRAST and task == TaskType.MISCONCEPTION:
            combined, extra = self._assemble_context(u)
            wrong, why, correct = _parse_misconception_spans(combined)
            body = {"wrong_idea": wrong, "why_wrong": why,
                    "correct_idea": correct, "correct_reasoning": correct}
            reveal = ["tempting_error", "conflict", "correction", "check"]
            slide_extra_ids = extra
        else:
            body = {"points": _split_points(u.normalized_content)}
        display = _display_title(title, body, rep, section, plan.title)
        # Truthful instructional states (what the slide DOES, not which move made it).
        emit_state = state
        if task == TaskType.MISCONCEPTION:
            emit_state = "MISCONCEPTION"
        elif rep == Representation.WORKED_CALCULATION:
            emit_state = "GUIDED_EXAMPLE"
        return SlideIR(id=sid, purpose=purpose, concept_id=u.id, concept_title=title,
                       task=task.value,
                       learning_goal=[f"{task.value}: {title}"],
                       representation=rep.value, content_title=display, body=body,
                       visual=visual, reveal_sequence=reveal[:8],
                       teacher_action=self._teacher(teacher_move, title),
                       source_ids=[u.id] + slide_extra_ids, objective_ids=list(oids),
                       instructional_state=emit_state,
                       representation_reason=_rep_reason(task, rep, u),
                       pedagogical_ref=f"{plan.id}:{state}")

    def _worked_slide(self, sid: str, plan: ChapterPlan, grouped: List[ContentUnit],
                      task: TaskType, rep: Representation, oids: List[str],
                      state: str, purpose: str, teacher_move: str) -> SlideIR:
        first = grouped[0]
        steps = [clean(u.normalized_content)[:300] for u in grouped
                 if u.content_type == ContentType.WORKED_STEP]
        if steps:
            problem = clean(first.normalized_content)[:400]
        else:
            # Chunk the joined source honestly into problem + steps.
            joined = "\n".join(u.normalized_content for u in grouped)
            problem, steps = _worked_from_unit(joined)
            if not steps:
                steps = [problem]
        emit_state = "GUIDED_EXAMPLE" if task == TaskType.CALCULATION else state
        givens = _extract_givens(problem)
        if not givens:
            givens = _extract_givens(" ".join(steps[:2]))
        body: Dict[str, Any] = {"problem": problem, "steps": steps,
                                "verify": "check units, boundary conditions, and result",
                                "givens": givens}
        reveal = ["problem"] + [f"step_{i+1}" for i in range(len(steps))] + ["verify"]
        return SlideIR(id=sid, purpose=purpose, concept_id=first.id,
                       concept_title=clean(plan.title), task=task.value,
                       learning_goal=[f"{task.value}: {clean(plan.title)}"],
                       representation=rep.value, content_title="Worked Example",
                       body=body, reveal_sequence=reveal[:10],
                       teacher_action=self._teacher(teacher_move, "worked reasoning"),
                       source_ids=[u.id for u in grouped], objective_ids=list(oids),
                       instructional_state=emit_state,
                       representation_reason=_rep_reason(task, rep, first),
                       pedagogical_ref=f"{plan.id}:{emit_state}")

    def _practice_slide(self, sid: str, plan: ChapterPlan, u: ContentUnit, task: TaskType,
                        oids: List[str], state: str, purpose: str, teacher_move: str,
                        faded: bool = False) -> SlideIR:
        # Practice problems must stay complete: a cut problem is broken, not dense.
        text = clean(u.normalized_content)
        body: Dict[str, Any] = {"items": [text], "origin": "source", "faded": faded}
        if task == TaskType.COMPARISON:
            body["scaffold"] = {"columns": _comparison_parties(text),
                                "note": "Complete each cell from the lesson; no invented facts."}
        elif task == TaskType.PROCESS:
            body["scaffold"] = {"stages": [],
                                "note": "Number each transfer step; cite the source mechanism."}
        return SlideIR(id=sid, purpose=purpose, concept_id=u.id,
                       concept_title=clean(u.section_title or plan.title),
                       task=task.value, learning_goal=[f"{task.value}: apply the lesson"],
                       representation=Representation.PRACTICE_PROBLEM.value,
                       content_title=(leading_label(text)
                                      or section_topic(u.section_title or "")
                                      or "Independent Practice"),
                       body=body, reveal_sequence=["problem", "attempt", "verify"],
                       teacher_action=self._teacher(teacher_move, text[:120]),
                       source_ids=[u.id], objective_ids=list(oids),
                       instructional_state=state,
                       representation_reason=_rep_reason(task, Representation.PRACTICE_PROBLEM, u),
                       pedagogical_ref=f"{plan.id}:{state}")

    def _misconception_slide(self, sid: str, plan: ChapterPlan, m: Dict[str, str],
                             move: TeachingMove,
                             units: Optional[Dict[str, ContentUnit]] = None) -> SlideIR:
        wrong, why, correct = (clean(m.get("wrong_idea", "")), clean(m.get("why_wrong", "")),
                               clean(m.get("correct_reasoning", "") or m.get("correct_idea", "")))
        src_ids = [m["source_unit_id"]] if m.get("source_unit_id") else []
        if not (wrong and correct) and units:
            # Fragmented source (mistake / flaw / correction in sibling units):
            # assemble the full span — same decision, presentation structuring.
            src = units.get(m.get("source_unit_id", ""))
            if src is not None:
                combined, extra = self._assemble_context(src)
                wrong, why, correct = _parse_misconception_spans(combined)
                src_ids = [src.id] + extra
        core = ""
        m_wrong = re.search(r"(?:Common Mistake|Misconception)\s*:\s*(.+?)(?:\.|$)",
                            clean(m.get("wrong_idea", "")), re.IGNORECASE | re.DOTALL)
        if m_wrong:
            core = m_wrong.group(1).strip().split("\n")[0][:70]
        title = f"Misconception: {core}" if core else "Misconception → Correction"
        return SlideIR(
            id=sid, purpose=move.purpose, concept_title=clean(m.get("topic", plan.title)),
            task=TaskType.MISCONCEPTION.value,
            learning_goal=[f"distinguish {clean(m.get('topic', ''))} from the tempting error"],
            representation=Representation.CONTRAST.value,
            content_title=title,
            body={"wrong_idea": wrong,
                  "why_wrong": why,
                  "correct_idea": correct,
                  "correct_reasoning": correct},
            reveal_sequence=["tempting_error", "conflict", "correction", "check"],
            teacher_action=self._teacher(move.teacher_move, clean(m.get("wrong_idea", ""))[:120]),
            source_ids=list(src_ids),
            objective_ids=list(move.objective_ids), instructional_state=move.state,
            representation_reason="task=misconception + mistake/correction spans -> contrast",
            pedagogical_ref=f"{plan.id}:{move.state}")

    def _assessment_slides(self, next_id, plan: ChapterPlan, q: QuizQuestion,
                           locked: LockedAssessment, state: str, move: TeachingMove
                           ) -> List[SlideIR]:
        rep = {"mcq": Representation.MCQ, "true_false": Representation.TRUE_FALSE}.get(
            locked.type, Representation.RETRIEVAL)
        task = question_task(locked.stem)
        # The scene is titled for what it checks, not with a generic label
        # shared by every question in the lesson.
        all_units = getattr(self, "_units", {}) or {}
        src = next((all_units[c] for c in q.source_content_ids if c in all_units), None)
        sec = section_topic(src.section_title or "") if src is not None else ""
        check_title = f"Check: {sec}" if sec else "Check for Understanding"
        base_body = {"question_id": q.id, "prompt": locked.stem, "options": locked.options,
                     "origin": locked.origin}
        prompt_slide = SlideIR(
            id=next_id(), purpose=f"Assess: {locked.stem[:80]}",
            concept_title=check_title, task=task.value,
            learning_goal=[locked.stem[:150]],
            representation=rep.value, content_title=check_title,
            body=dict(base_body), reveal_sequence=["prompt", "think"],
            teacher_action=TeacherAction(type="prompt",
                                         prompt="Think time first; who can explain their reasoning?"),
            assessment=locked, source_ids=list(q.source_content_ids),
            objective_ids=list(q.objective_ids), instructional_state=state,
            representation_reason=f"locked {locked.type} assessment -> {rep.value}",
            pedagogical_ref=f"{plan.id}:{state}")
        reveal_slide = SlideIR(
            id=next_id(), purpose=f"Reveal locked answer for {q.id}",
            concept_title="Answer & Explanation", task=task.value,
            learning_goal=[locked.stem[:150]],
            representation=rep.value, content_title="Answer & Explanation",
            body={**base_body, "reveal": True},
            reveal_sequence=["answer", "explanation"],
            teacher_action=TeacherAction(type="explanation",
                                         focus="Explain why each distractor fails."),
            assessment=locked, source_ids=list(q.source_content_ids),
            objective_ids=list(q.objective_ids), instructional_state=state,
            representation_reason=f"locked {locked.type} answer reveal -> {rep.value}",
            pedagogical_ref=f"{plan.id}:{state}")
        return [prompt_slide, reveal_slide]

    def _assemble_context(self, u: ContentUnit) -> Tuple[str, List[str]]:
        """Append following sibling units carrying flaw/correction markers.

        The atomizer splits paragraphs; a misconception's 'why flawed' and
        'correct reasoning' often land in adjacent units. Assembling them is
        presentation structuring of one decision — not new pedagogy.
        """
        parts = [u.normalized_content]
        extra: List[str] = []
        order = getattr(self, "_order", [])
        units = getattr(self, "_units", {})
        try:
            pos = order.index(u.id)
        except ValueError:
            return parts[0], extra
        for nid in order[pos + 1:pos + 3]:
            nxt = units.get(nid)
            if nxt is None:
                continue
            if re.search(r"Why it is (?:flawed|wrong)|Correct Reasoning|Correction\s*:",
                         nxt.normalized_content, re.IGNORECASE):
                parts.append(nxt.normalized_content)
                extra.append(nid)
            else:
                break
        return "\n".join(parts), extra

    def _recall_topic(self, cids: List[str], units: Dict[str, ContentUnit],
                      verb: str) -> Optional[str]:
        """A section-derived topic no earlier recall scene already claimed.

        Candidates run strongest-first per unit: the section the source names
        itself, then that section with the unit's own label in front of it
        ("Correct Reasoning — The Dark Reactions…") when a sibling checkpoint
        took the plain section, then the label alone. Two checkpoints in the
        same section therefore stay distinguishable.
        """
        seen: set = getattr(self, "_recall_titles", None)
        if seen is None:
            seen = set()
            self._recall_titles = seen
        candidates: List[str] = []
        for c in cids:
            u = units.get(c)
            if u is None:
                continue
            sec = section_topic(u.section_title or "")
            lab = leading_label(u.normalized_content)
            if sec:
                candidates.append(sec)
                sec_lab = leading_label(sec)
                bare = sec
                if sec_lab:
                    bare = re.sub(rf"^{re.escape(sec_lab)}\s*:\s*", "", sec,
                                  flags=re.IGNORECASE).strip() or sec
                if lab and bare:
                    candidates.append(f"{lab} — {bare}")
                elif bare != sec:
                    candidates.append(bare)
            if lab:
                candidates.append(lab)
        for cand in candidates:
            title = f"{verb}: {cand}"
            if len(title) <= 90 and title not in seen:
                seen.add(title)
                return cand
        return candidates[0] if candidates else None

    def _move_questions(self, move: TeachingMove, by_objective: Dict[str, List[QuizQuestion]],
                        all_qs: List[QuizQuestion], used: set, take_all: bool
                        ) -> List[QuizQuestion]:
        if take_all:
            return [q for q in all_qs if q.id not in used]
        out = []
        for oid in move.objective_ids:
            for q in by_objective.get(oid, []):
                if q.id not in used and q.id not in [x.id for x in out]:
                    out.append(q)
                    break
        return out[:1]


# ---------------------------------------------------------------------------
# Content-derived visual payloads (extraction, never invention)
# ---------------------------------------------------------------------------

def _is_askable(q: QuizQuestion) -> bool:
    """A locked question must ask something: a real question mark, options to
    choose from, or a substantive non-heading prompt. Headings are never asked."""
    prompt = (q.prompt or "").strip()
    if not prompt or is_heading_block(prompt):
        return False
    if "?" in prompt or (q.options or []):
        return True
    return len(prompt) > 40


def _rep_reason(task: TaskType, rep: Representation, u: ContentUnit) -> str:
    """One-line record of why this representation was selected (debugging)."""
    text = u.normalized_content
    cue = ""
    if rep in (Representation.LABELED_DIAGRAM, Representation.ANATOMY_MAP):
        cue = "compartment bullets" if "**" in text else "legend lines"
    elif rep in (Representation.PATHWAY, Representation.SEQUENCE, Representation.FLOW,
                 Representation.CYCLE):
        cue = "numbered steps" if re.search(r"Step\s*\d+", text) else "directional markers"
    elif rep == Representation.EQUATION_FOCUS:
        cue = "stoichiometric equation"
    elif rep in (Representation.DATA_TABLE, Representation.COMPARISON_MATRIX):
        cue = "tabular source"
    elif rep == Representation.DEFINITION_FOCUS:
        cue = "definition wording"
    elif rep == Representation.WORKED_CALCULATION:
        cue = "worked steps"
    elif rep == Representation.CONTRAST:
        cue = "mistake/correction spans"
    parts = [f"task={task.value}", f"unit={u.content_type.value}"]
    if cue:
        parts.append(cue)
    parts.append(f"-> {rep.value}")
    return " + ".join(parts)


def _split_points(text: str, limit: int = 4) -> List[str]:
    t = clean(text)
    parts = [p.strip("- •* ") for p in re.split(r"\n+", t) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r";\s+", t) if p.strip()]
    # Drop bare section-numbering lines ("1. Introduction and Big Picture").
    parts = [p for p in parts
             if not re.match(r"^\d+\.\s+[A-Z][^.?!]{0,70}$", p.strip()) or len(parts) == 1]
    return [clip_sentences(p, 350) for p in parts[:limit]] or [clip_sentences(t, 350)]


def _extract_structure(text: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Compartment bullets '**Name**: description' → nodes + labeled leader lines."""
    parts: List[str] = []
    labels: List[Dict[str, str]] = []
    for m in re.finditer(r"\*\*(.+?)\*\*\s*:?\s*(.+?)(?=\n\s*[-•]?\s*\*\*|\Z)",
                         text, re.DOTALL):
        name = latex_to_unicode(m.group(1)).strip()
        desc = clean(m.group(2)).strip()
        # Split "Site of X, housing A, B" → function = first clause.
        func = re.split(r", housing|;|, containing", desc)[0].strip()
        parts.append(name)
        labels.append({"name": name, "target": name.lower().replace(" ", "_"),
                       "explanation": func[:160]})
    # Fallback: dash bullets naming compartments.
    if not parts:
        for line in text.splitlines():
            lm = re.match(r"[-•]\s*\*{0,2}(.+?)\*{0,2}\s*:\s*(.+)", line.strip())
            if lm:
                parts.append(latex_to_unicode(lm.group(1)).strip())
                labels.append({"name": parts[-1],
                               "target": parts[-1].lower().replace(" ", "_"),
                               "explanation": clean(lm.group(2))[:160]})
    # Fallback: legend bullets "X represents <function>".
    if not parts:
        for line in text.splitlines():
            lm = re.match(r"[-•]?\s*\$?(.+?)\$?\s+represents\s+(.+)", clean(line).strip(),
                          re.IGNORECASE)
            if lm and len(lm.group(1)) < 60:
                parts.append(lm.group(1).strip())
                labels.append({"name": parts[-1],
                               "target": parts[-1].lower().replace(" ", "_"),
                               "explanation": lm.group(2).strip()[:160]})
    return parts[:6], labels[:6]


def _extract_stages(text: str) -> List[str]:
    stages = re.findall(r"Step\s*\d+\s*:\s*(.+?)(?=Step\s*\d+\s*:|\Z)", clean(text),
                        re.IGNORECASE | re.DOTALL)
    if stages:
        return [s.strip()[:120] for s in stages[:8]]
    arrows = [s.strip()[:120] for s in re.split(r"→|->", clean(text)) if s.strip()]
    return arrows[:8] if 1 < len(arrows) <= 8 else []


def _extract_givens(problem: str) -> List[str]:
    givens = []
    for m in re.finditer(r"([A-Za-zλΔμ][\w\s²³°/%-]{0,40}?=\s*[\d.]+\s*[a-zA-Z°/%²³μ ]{0,12})",
                         problem):
        givens.append(m.group(1).strip())
    return givens[:5]


def _has_equation(text: str) -> bool:
    return bool(re.search(r"\$\$|\\longrightarrow|\\rightarrow|→", text))


def _legend_match(key: str, species: str) -> bool:
    """Species-key matching without substring false friends (O₂ vs CO₂)."""
    key, species = key.strip(), species.strip()
    if not key or not species:
        return False
    if key == species:
        return True
    head = key.split()[0]
    return head == species or head.startswith(species + "(") or head == species + "(s)"


def _merge_legend(slide_ir: SlideIR, legend_text: str) -> None:
    """Attach species legend notes to an equation slide (traceable merge)."""
    eq = slide_ir.visual.equation
    if eq is None:
        return
    for line in legend_text.splitlines():
        lm = re.match(r"[-•]?\s*(.+?)\s+represents\s+(.+)", clean(line).strip(), re.IGNORECASE)
        if not lm:
            continue
        key, note = lm.group(1).strip(), lm.group(2).strip()[:160]
        for term in eq.lhs + eq.rhs:
            if not term.note and _legend_match(key, term.species):
                term.note = note


def _worked_from_unit(text: str) -> Tuple[str, List[str]]:
    """Split a calculation unit into (problem, steps) without inventing content."""
    t = clean(text)
    parts = re.split(r"(Step\s*\d+\s*:)", t, flags=re.IGNORECASE)
    if len(parts) >= 3:
        problem = clip_sentences(parts[0].strip(), 400) or parts[1] + parts[2][:200]
        steps = []
        for i in range(1, len(parts) - 1, 2):
            steps.append(clip_sentences((parts[i] + " " + parts[i + 1]).strip(), 300))
        return problem, steps[:6]
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    if len(lines) > 1:
        return clip_sentences(lines[0], 400), [clip_sentences(l, 300) for l in lines[1:7]]
    return clip_sentences(t, 400), [clip_sentences(t, 300)]


def _parse_misconception_spans(text: str) -> Tuple[str, str, str]:
    """Structure wrong → why-flawed → correct spans from source wording."""
    t = clean(text)
    wrong = why = correct = ""
    m = re.search(r"(?:Common Mistake|Common Misconception|Misconception)\s*:\s*(.+?)(?=(?:Why it is flawed|Why it is wrong|Correction|Correct Reasoning)\s*:|\Z)",
                  t, re.IGNORECASE | re.DOTALL)
    if m:
        wrong = clip_sentences(m.group(1).strip(), 300)
    m = re.search(r"Why it is (?:flawed|wrong)\s*:\s*(.+?)(?=(?:Correction|Correct Reasoning)\s*:|\Z)",
                  t, re.IGNORECASE | re.DOTALL)
    if m:
        why = clip_sentences(m.group(1).strip(), 300)
    m = re.search(r"(?:Correct Reasoning|Correction)\s*:\s*(.+)", t,
                  re.IGNORECASE | re.DOTALL)
    if m:
        correct = clip_sentences(m.group(1).strip(), 400)
    if not wrong:
        wrong = clip_sentences(t, 300)
    return wrong, why, correct


def _has_structure(text: str) -> bool:
    """Compartment-style content: **Name**: description bullets or legend lines."""
    bold = re.findall(r"\*\*(.+?)\*\*\s*:?", text)
    if len(bold) >= 2:
        return True
    legend = [l for l in text.splitlines()
              if re.search(r"represents\s+", l, re.IGNORECASE)]
    return len(legend) >= 2


def _is_legend(text: str) -> bool:
    """Legend-only unit (species keys) that belongs on an equation slide."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 2 or re.search(r"\$\$|→|\\\\rightarrow", text):
        return False
    return sum(1 for l in lines if re.search(r"represents\s+", l, re.IGNORECASE)) >= 2


def _is_header_only(text: str) -> bool:
    """Section header masquerading as a practice unit (no task content)."""
    t = clean(text)
    if "?" in t:
        return False
    if re.search(r"\b(trace|contrast|compare|calculate|compute|determine|explain|solve|describe|predict|identify)\b",
                 t, re.IGNORECASE):
        return False
    return len(t) < 150


def _is_calc_material(u: ContentUnit) -> bool:
    """Unit belonging to a quantitative worked calculation (not an equation slide)."""
    if classify_task(u) == TaskType.CALCULATION:
        return True
    if _has_equation(u.normalized_content):
        return False
    if u.content_type in (ContentType.FORMULA, ContentType.EXPLANATION, ContentType.EXAMPLE):
        return bool(re.search(r"\bmol\b|photon|quantum|wavelength|λ|yield|efficiency|\bnm\b",
                              u.normalized_content, re.IGNORECASE))
    return False


def _display_title(fallback: str, body: Dict[str, Any], rep: Representation,
                   section: str = "", chapter: str = "") -> str:
    """Scene-specific title: term, first specific point, or section — never
    a bare chapter name unless nothing else exists (flagged downstream)."""
    if rep == Representation.DEFINITION_FOCUS and body.get("term"):
        return body["term"][:100]
    points = body.get("points") or []
    if points:
        first = re.sub(r"^\d+\.\s*", "", points[0]).strip()
        if (8 < len(first) <= 100 and first != chapter
                and first != short_headline(section or "", 100)):
            return first
    sec_head = short_headline(section, 80) if section else ""
    if sec_head and sec_head != chapter:
        return sec_head
    return fallback


def _parse_markdown_table(text: str) -> Tuple[List[str], List[List[str]]]:
    """Structure a Markdown pipe-table kept as text (no invented content)."""
    rows: List[List[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [latex_to_unicode(c).strip() for c in line.strip("|").split("|")]
            if cells and all(re.match(r"^:?-+:?$", c) for c in cells):
                continue  # alignment separator row
            rows.append(cells)
    if len(rows) < 2:
        return [], []
    width = len(rows[0])
    rows = [r for r in rows if len(r) == width]
    if len(rows) < 2:
        return [], []
    return rows[0], rows[1:6]


def _title_alternates(s, units: Dict[str, Any]) -> List[str]:
    """Titles derived from this scene's own payload, strongest first.

    Only ever consulted when the scene's first-choice title is already taken
    by an earlier scene — so the fallback still names THIS scene instead of
    repeating the last one.
    """
    out: List[str] = []

    def add(x: Any, cap: int = 80) -> None:
        if not x:
            return
        t = strip_markup_line(clean(str(x)))
        # A clipped headline is a fragment; fragments are never titles.
        if not t or len(t) > cap or "…" in t or "..." in t:
            return
        if t not in out:
            out.append(t)

    b = s.body or {}
    add(b.get("term"), 60)
    pts = b.get("points") or []
    if pts:
        add(short_headline(str(pts[0]), 70))
    for it in (b.get("items") or [])[:2]:
        add(leading_label(str(it)), 60)
    visual = getattr(s, "visual", None)
    parts = [clean(str(p)) for p in (getattr(visual, "structure", None) or [])]
    parts = [p for p in parts if p and "\\" not in p]
    if 1 < len(parts) <= 4:
        add(", ".join(parts[:3]), 60)
    add(b.get("problem"), 70)
    add(b.get("wrong_idea"), 70)
    u = next((units[c] for c in s.source_ids if c in units), None)
    if u is not None:
        sec = section_topic(u.section_title or "")
        if sec:
            lab = leading_label(u.normalized_content)
            if lab:
                add(f"{lab} — {sec}", 80)
            add(sec, 80)
    return out


def resolve_duplicate_titles(bp, plan, units: Dict[str, Any]) -> None:
    """Every scene headline must name THAT scene.

    Walks in slide order so the first scene keeps the section title; a later
    scene that would repeat it falls back to payload the earlier one did not
    use (its term, its first point, its structure parts, its own label).
    """
    used: set = set()
    for s in bp.slides:
        cands = [s.content_title] + _title_alternates(s, units)
        pick = next((c for c in cands if c and len(c) <= 90 and c not in used), None)
        if pick is None:
            # Every candidate taken: qualify with the scene's own task so the
            # headline still says what THIS scene does.
            task = (s.task or "").replace("_", " ").strip().title()
            base = cands[0] or plan.title
            for n in range(1, 100):
                cand = (f"{task}: {base}" if n == 1 else
                        f"{task}: {base} ({n})")[:90]
                if cand not in used:
                    pick = cand
                    break
            pick = pick or base
        s.content_title = pick
        used.add(pick)


def _comparison_parties(text: str) -> List[str]:
    found = []
    for cand in ("C3", "C4", "light reactions", "Calvin cycle", "PSII", "PSI"):
        if cand.lower() in text.lower():
            found.append(cand)
    if not found:
        m = re.search(r"[Cc]ontrast\s+(.+?)\s+with\s+(.+?)(?:\s+in|\s*$)", text)
        if m:
            found = [m.group(1).strip()[:40], m.group(2).strip()[:60]]
    return found[:2] or ["A", "B"]
