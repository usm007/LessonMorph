"""Pedagogical strategy selection: goal + content + learner -> strategy.

Decision principles (used when appropriate, never a checklist):
backward design, constructive alignment, cognitive load, multimedia/dual
coding, scaffolding, worked-example effect, retrieval, spacing, interleaving,
formative assessment, generative learning, misconception-based instruction,
gradual release, concrete-to-abstract, elaboration, prior-knowledge
activation, feedback, deliberate practice.

Central rule: NO universal lesson recipe. Strategy depends on subject, topic,
content type (conceptual/procedural/factual), learner level, objective,
complexity, and likely misconceptions.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from lessonmorph.core.models import (
    ContentType, ContentUnit, LearnerProfile, LearningObjective,
    OBSERVABLE_VERBS, SubjectDomain,
)
from lessonmorph.core.text_refs import (
    clip_words, extract_term, is_equation, is_step_fragment, short_headline,
    strip_markup_line, task_sentence,
)

PROCEDURAL_TYPES = (ContentType.WORKED_STEP, ContentType.EXERCISE, ContentType.FORMULA)
FACTUAL_TYPES = (ContentType.TERMINOLOGY, ContentType.TABLE, ContentType.FOOTNOTE)

_VERB_BY_TYPE = {
    "procedural": [("calculate", "application"), ("solve", "application"), ("apply", "application")],
    "factual": [("identify", "recall"), ("define", "recall"), ("classify", "understanding")],
    "conceptual": [("explain", "understanding"), ("compare", "analysis"), ("predict", "application")],
}


def classify_content_nature(unit: ContentUnit) -> str:
    """Conceptual / procedural / factual per unit (drives strategy choice)."""
    if unit.content_type in PROCEDURAL_TYPES:
        return "procedural"
    if unit.content_type in FACTUAL_TYPES:
        return "factual"
    text = unit.normalized_content.lower()
    if any(w in text for w in ("calculate", "solve", "step 1", "procedure", "substitute", "compute")):
        return "procedural"
    if any(w in text for w in ("born in", "in 19", "capital of", "list of", "refers to")):
        return "factual"
    return "conceptual"


def profile_content(units: List[ContentUnit]) -> Dict[str, str]:
    return {u.id: classify_content_nature(u) for u in units}


def synthesize_objectives(
    units: List[ContentUnit], chapter_title: str, content_profile: Dict[str, str],
) -> List[LearningObjective]:
    """Backward design: observable verbs bound to the content that teaches them.

    Every objective names real content extracted from the units (terms,
    formulas, misconception topics, tables). Generic filler such as
    "Explain conceptual content in …" is never emitted: if nothing specific
    is derivable, fewer objectives are returned instead.
    """
    # 1. Explicit objectives in source win.
    for u in units:
        if "objective" in u.normalized_content.lower() or "you will learn" in u.normalized_content.lower():
            lines = [l.strip("- *0123456789. ") for l in u.normalized_content.splitlines() if l.strip()]
            clean = [l for l in lines if len(l) > 12 and "objective" not in l.lower()][:5]
            if clean:
                return [LearningObjective(f"O{i+1:02d}", _with_verb(t), _guess_verb(t)[0],
                                          _guess_verb(t)[1], [u.id])
                        for i, t in enumerate(clean)]
    # 2. Derive one student-facing outcome per salient idea (cap 6, core first).
    #    Numbered steps of one worked example are parts of that example, never
    #    outcomes of their own; prose that merely contains inline math is not
    #    "a relationship". Ranks an explicitly stated task above worked-example
    #    bookkeeping so the example yields ONE outcome from its own task.
    ranked = sorted(units, key=lambda u: (0 if u.importance.value == "core" else 1,
                                          _objective_rank(u)))
    objectives: List[LearningObjective] = []
    seen_terms: set = set()
    oid = 1
    for u in ranked:
        if oid > 6:
            break
        if is_step_fragment(u.normalized_content):
            continue  # a step belongs to its worked example, not to the goals
        text = _objective_text(u)
        if text is None:
            continue
        key = text.lower()
        if key in seen_terms:
            continue
        seen_terms.add(key)
        verb, bloom = _guess_verb(text)
        objectives.append(LearningObjective(f"O{oid:02d}", text, verb, bloom, [u.id]))
        oid += 1
    return objectives


_TYPE_RANK = {
    "definition": 0, "misconception": 1, "formula": 2, "table": 3,
    "example": 5, "exercise": 5, "worked_step": 6,
}


def _objective_rank(u: ContentUnit) -> int:
    """Order candidates for the (capped) objective set.

    An explanation that states an explicit task ("Determine the theoretical
    moles of glucose…") is a real learning outcome and ranks above example
    bookkeeping, so a worked example contributes its own task rather than a
    pile of per-step fragments. Everything else falls to its content type.
    """
    if u.content_type == ContentType.EXPLANATION and task_sentence(u.normalized_content):
        return 4
    return _TYPE_RANK.get(u.content_type.value, 9)


def _objective_text(u: ContentUnit) -> Optional[str]:
    """One student-facing objective sentence, or None if not derivable."""
    ctype = u.content_type
    if ctype == ContentType.DEFINITION:
        term = extract_term(u.normalized_content) or extract_term(u.original_wording)
        if term:
            return f"Define {term} and explain what it means."
        head = short_headline(u.normalized_content, 60)
        if head and len(head) > 8:
            return f"Explain: {head}."
        return None
    if ctype == ContentType.FORMULA:
        from lessonmorph.blueprint.sanitize import clean
        if not is_equation(u.normalized_content):
            # Prose containing inline math is not a relationship. Use its own
            # stated task if it has one; otherwise emit nothing rather than
            # "Use the relationship <paragraph>…".
            return _task_objective(u)
        head = short_headline(clean(u.normalized_content), 70)
        if head and len(head) > 8:
            return f"Use the relationship {head} to calculate unknown quantities."
        return None
    if ctype == ContentType.MISCONCEPTION:
        topic = ""
        if u.section_title:
            topic = re.sub(r"^(?:common\s+)?(?:misconception|mistake|error)\s*:\s*", "",
                           u.section_title.strip(), flags=re.IGNORECASE).strip()
        if not topic:
            m = re.search(r"(?:Common Mistake|Misconception)\s*:\s*(.+?)(?:\.|;|$)",
                          u.normalized_content, re.IGNORECASE | re.DOTALL)
            topic = clip_words(m.group(1), 70) if m else short_headline(u.normalized_content, 70)
        if topic:
            return f"Correct the common misconception about {topic}."
        return None
    if ctype == ContentType.TABLE:
        title = (u.metadata or {}).get("title") or ""
        # "Table 1" carries no meaning — prefer the source section that names
        # what the data actually is.
        if not title or re.fullmatch(r"table\s*\d+", title.strip(), re.IGNORECASE):
            title = u.section_title or title
        if title:
            return f"Interpret the data in {strip_markup_line(title)}."
        return None
    if ctype in (ContentType.EXAMPLE, ContentType.WORKED_STEP, ContentType.EXERCISE):
        if is_step_fragment(u.normalized_content):
            return None  # a step is assessed through its worked example
        # Only an outcome we can also assess: the unit must show more than
        # the task it asks for, or there is no source wording to reveal.
        if not _demonstrates(u):
            return None
        return _task_objective(u) or _example_objective(u)
    if ctype == ContentType.EXPLANATION:
        # Only when the wording states an explicit task — never invent an
        # outcome from expository prose.
        return _task_objective(u)
    return None


_LABEL_RE = re.compile(
    r"^(?:\*\*)?(?:practice\s+problem|worked\s+(?:example|calculation)|example|question"
    r"|exercise|problem|task)\s*\d*\s*(?:\*\*)?\s*[:.]\s*", re.IGNORECASE)


def _demonstrates(u: ContentUnit) -> bool:
    """True when the unit carries content BEYOND its opening ask."""
    t = _LABEL_RE.sub("", u.normalized_content.strip())
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]
    rest = " ".join(sentences[1:]).strip() if len(sentences) > 1 else ""
    return len(strip_markup_line(rest)) >= 40


def _task_objective(u: ContentUnit) -> Optional[str]:
    """Objective taken verbatim from the unit's own stated task/question."""
    sent = task_sentence(u.normalized_content) or task_sentence(u.original_wording or "")
    if not sent:
        return None
    return clip_words(sent, 150).rstrip(".") + "."


def _example_objective(u: ContentUnit) -> Optional[str]:
    """Fallback outcome for example/practice wording with no stated task."""
    head = short_headline(re.sub(r"^(?:practice\s+problem|example)\s*\d*\s*[:.]\s*", "",
                                 u.normalized_content.strip(),
                                 flags=re.IGNORECASE), 80)
    if head and len(head) > 12:
        return f"Solve problems like: {head}."
    return None


def _guess_verb(text: str) -> Tuple[str, str]:
    low = text.lower()
    for v in OBSERVABLE_VERBS:
        if re.search(r"\b" + re.escape(v) + r"[a-z]*\b", low):
            bloom = {"identify": "recall", "define": "recall"}.get(v, "understanding")
            return v, bloom
    return "explain", "understanding"


def _with_verb(text: str) -> str:
    low = text.lower()
    if any(re.search(r"\b" + re.escape(v) + r"[a-z]*\b", low) for v in OBSERVABLE_VERBS):
        return text.rstrip(".") + "."
    return "Explain: " + text.rstrip(".") + "."


# Subject x content-nature -> strategies (adaptive, not a fixed recipe).
_STRATEGY_TABLE: Dict[Tuple[str, str], List[str]] = {
    ("mathematics", "procedural"): ["worked_example", "scaffolding", "gradual_release", "deliberate_practice"],
    ("mathematics", "conceptual"): ["concrete_to_abstract", "elaboration", "retrieval", "misconception_check"],
    ("physics", "procedural"): ["worked_example", "dual_coding", "gradual_release"],
    ("physics", "conceptual"): ["dual_coding", "misconception_check", "generative_predict"],
    ("chemistry", "procedural"): ["worked_example", "dual_coding", "scaffolding"],
    ("chemistry", "conceptual"): ["dual_coding", "concrete_to_abstract", "retrieval"],
    ("biology", "conceptual"): ["dual_coding", "sequencing", "generative_predict", "retrieval"],
    ("biology", "procedural"): ["sequencing", "worked_example", "retrieval"],
    ("history", "conceptual"): ["prior_activation", "chronology", "causation", "comparison", "elaboration"],
    ("history", "factual"): ["chronology", "spacing", "retrieval"],
    ("geography", "conceptual"): ["dual_coding", "comparison", "elaboration"],
    ("language", "procedural"): ["worked_example", "contrast", "guided_production", "gradual_release"],
    ("language", "conceptual"): ["contrast", "examples_first", "retrieval"],
    ("literature", "conceptual"): ["interpretation", "comparison", "elaboration", "generative_explain"],
}


def select_strategies(
    domain: SubjectDomain, content_profile: Dict[str, str], learner: LearnerProfile,
) -> List[str]:
    """Choose decision principles fitting subject + content + learner."""
    dom = domain.value
    natures = set(content_profile.values()) or {"conceptual"}
    picked: List[str] = []
    for nature in natures:
        picked += _STRATEGY_TABLE.get((dom, nature), [])
    if not picked:  # general fallback keeps backward design + alignment + load management
        picked = ["backward_design", "constructive_alignment", "cognitive_load",
                  "retrieval", "formative_assessment"]
    # Learner adjustments (level influences scaffolding depth, never the goal).
    if learner.level in ("primary", "middle_school"):
        for s in ("concrete_to_abstract", "scaffolding"):
            if s not in picked:
                picked.append(s)
    # De-duplicate, preserve order.
    seen, out = set(), []
    for s in picked:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def build_dependency_chain(prior: List[str], core_concepts: List[str]) -> List[List[str]]:
    """Prerequisite A -> B -> new concept -> application (hidden prereqs forbidden)."""
    if not core_concepts:
        return []
    chain = [*(p[:60] for p in prior[:2]), core_concepts[0][:60] + " (new)",
             (core_concepts[1][:60] if len(core_concepts) > 1 else "application") ]
    return [chain]


def complexity_of(unit: ContentUnit, nature: str) -> str:
    long_text = len(unit.normalized_content) > 400
    if unit.content_type in (ContentType.FORMULA, ContentType.WORKED_STEP) or (
            nature == "procedural" and long_text):
        return "high"
    if unit.content_type in (ContentType.DEFINITION, ContentType.TABLE) or long_text:
        return "medium"
    return "low"
