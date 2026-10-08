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
from typing import Dict, List, Tuple
from lessonmorph.core.models import (
    ContentType, ContentUnit, LearnerProfile, LearningObjective,
    OBSERVABLE_VERBS, SubjectDomain,
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
    """Backward design: observable verbs bound to the content that teaches them."""
    # 1. Explicit objectives in source win.
    for u in units:
        if "objective" in u.normalized_content.lower() or "you will learn" in u.normalized_content.lower():
            lines = [l.strip("- *0123456789. ") for l in u.normalized_content.splitlines() if l.strip()]
            clean = [l for l in lines if len(l) > 12 and "objective" not in l.lower()][:5]
            if clean:
                return [LearningObjective(f"O{i+1:02d}", _with_verb(t), _guess_verb(t)[0],
                                          _guess_verb(t)[1], [u.id])
                        for i, t in enumerate(clean)]
    # 2. Synthesize from content mix — verbs match the dominant content nature.
    counts = {"conceptual": 0, "procedural": 0, "factual": 0}
    by_nature: Dict[str, List[ContentUnit]] = {"conceptual": [], "procedural": [], "factual": []}
    for u in units:
        n = content_profile.get(u.id, "conceptual")
        counts[n] += 1
        by_nature[n].append(u)
    ranked = sorted(counts, key=lambda k: counts[k], reverse=True)
    objectives: List[LearningObjective] = []
    oid = 1
    for nature in ranked:
        group = by_nature[nature]
        if not group:
            continue
        for verb, bloom in _VERB_BY_TYPE[nature][:2]:
            if oid > 6:
                break
            ids = [u.id for u in group[:4]]
            objectives.append(LearningObjective(
                f"O{oid:02d}", f"{verb.capitalize()} {nature} content in {chapter_title}.",
                verb, bloom, ids))
            oid += 1
        if oid > 6:
            break
    return objectives or [LearningObjective("O01", f"Explain key ideas in {chapter_title}.",
                                            "explain", "understanding",
                                            [u.id for u in units[:4]])]


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
