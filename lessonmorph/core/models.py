"""Core data models for LessonMorph.

Defines schemas for content atoms, document hierarchy, pedagogical structure,
storyboards, slides, quizzes, and validation reports.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContentType(str, Enum):
    DEFINITION = "definition"
    EXPLANATION = "explanation"
    EXAMPLE = "example"
    WORKED_STEP = "worked_step"
    EXCEPTION = "exception"
    DIAGRAM = "diagram"
    TABLE = "table"
    FORMULA = "formula"
    WARNING = "warning"
    EXERCISE = "exercise"
    HEADING = "heading"  # structural section header, not teachable content
    MISCONCEPTION = "misconception"
    CONTEXT = "context"
    TERMINOLOGY = "terminology"
    FOOTNOTE = "footnote"


class ContentImportance(str, Enum):
    CORE = "core"
    SUPPORTING = "supporting"
    EXTENSION = "extension"


@dataclass
class ContentUnit:
    """Atomic, traceable unit of content extracted from the source document."""
    id: str  # e.g. "C001"
    source_location: str  # e.g. "Page 4, Section 1.2"
    chapter_id: str  # e.g. "ch01"
    chapter_title: str
    section_title: Optional[str]
    content_type: ContentType
    importance: ContentImportance
    normalized_content: str
    original_wording: str = ""
    relationships: List[str] = field(default_factory=list)  # related unit IDs
    intended_destination: Optional[str] = None  # e.g. "Slide 4"
    covered: bool = False
    covered_slides: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_covered(self, slide_ref: str) -> None:
        self.covered = True
        if slide_ref not in self.covered_slides:
            self.covered_slides.append(slide_ref)
        if not self.intended_destination:
            self.intended_destination = slide_ref


class SubjectDomain(str, Enum):
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    SCIENCE_GENERAL = "science_general"
    HISTORY = "history"
    GEOGRAPHY = "geography"
    SOCIAL_SCIENCE = "social_science"
    LITERATURE = "literature"
    LANGUAGE = "language"
    COMPUTER_SCIENCE = "computer_science"
    GENERAL = "general"


class SlideType(str, Enum):
    TITLE = "title"
    ROADMAP = "roadmap"
    LEARNING_OBJECTIVES = "learning_objectives"
    PRIOR_KNOWLEDGE = "prior_knowledge"
    CONCEPT_DEFINITION = "concept_definition"
    PROCESS_FLOW = "process_flow"
    COMPARISON = "comparison"
    WORKED_EXAMPLE = "worked_example"
    COMMON_MISCONCEPTION = "common_misconception"
    FORMULA_BREAKDOWN = "formula_breakdown"
    CLASSIFICATION_GRID = "classification_grid"
    CAUSE_EFFECT = "cause_effect"
    TIMELINE = "timeline"
    TABLE_DISPLAY = "table_display"
    DIAGRAM_EXPLANATION = "diagram_explanation"
    QUIZ_QUESTION = "quiz_question"
    QUIZ_REVEAL = "quiz_reveal"
    SUMMARY_RECAP = "summary_recap"
    PRACTICE_SET = "practice_set"
    EXAM_STYLE = "exam_style"
    EXIT_TICKET = "exit_ticket"


class AnimationType(str, Enum):
    APPEAR = "appear"
    FADE = "fade"
    PROGRESSIVE_BUILD = "progressive_build"
    HIGHLIGHT = "highlight"
    CROSS_OUT = "cross_out"
    ANSWER_REVEAL = "answer_reveal"
    NONE = "none"


@dataclass
class AnimationStep:
    """Defines a discrete animation action on a slide."""
    step_number: int
    target_object_id: str
    action: AnimationType
    delay_ms: int = 0
    duration_ms: int = 500
    description: str = ""
    trigger: str = "on_click"  # "on_click" or "after_previous" or "with_previous"
    purpose: str = ""  # instructional purpose, e.g. "sequence causal steps"


@dataclass
class SpeakerNotes:
    """Comprehensive teacher speaker notes for classroom delivery."""
    teacher_explanation: str = ""
    emphasis: str = ""
    ask_students: str = ""
    likely_misconception: str = ""
    transition: str = ""
    optional_extension: str = ""

    def render_markdown(self) -> str:
        parts = []
        if self.teacher_explanation:
            parts.append(f"TEACHER EXPLANATION:\n{self.teacher_explanation}")
        if self.emphasis:
            parts.append(f"EMPHASIS / KEY POINT:\n{self.emphasis}")
        if self.ask_students:
            parts.append(f"ASK STUDENTS (ORAL CHECK):\n{self.ask_students}")
        if self.likely_misconception:
            parts.append(f"LIKELY MISCONCEPTION:\n{self.likely_misconception}")
        if self.transition:
            parts.append(f"TRANSITION:\n{self.transition}")
        if self.optional_extension:
            parts.append(f"OPTIONAL EXTENSION:\n{self.optional_extension}")
        return "\n\n".join(parts)


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"
    SEQUENCE_ORDER = "sequence_order"
    CLASSIFICATION = "classification"
    IDENTIFY_ERROR = "identify_error"
    CALCULATION = "calculation"
    ASSERTION_REASON = "assertion_reason"
    SHORT_ANSWER = "short_answer"
    EXAM_STYLE = "exam_style"


@dataclass
class QuizQuestion:
    """Quiz question linked to source content atoms."""
    id: str
    question_type: QuestionType
    source_content_ids: List[str]
    difficulty: str  # recall, understanding, application, analysis, evaluation
    prompt: str
    options: List[str] = field(default_factory=list)  # For MCQ / matching
    correct_answer: str = ""
    explanation: str = ""
    distractor_rationales: Dict[str, str] = field(default_factory=dict)
    slide_id: Optional[str] = None
    reveal_slide_id: Optional[str] = None
    objective_ids: List[str] = field(default_factory=list)  # O01... this item assesses
    misconception_target: str = ""  # which misconception this item probes, if any


@dataclass
class SlideSpec:
    """Complete specification for a single presentation slide."""
    slide_id: str  # e.g. "S001"
    chapter_id: str
    title: str
    subtitle: Optional[str]
    purpose: str
    source_content_ids: List[str]
    slide_type: SlideType
    visual_model: str  # e.g. "2_column_compare", "stepped_cards", "formula_card", etc.
    elements_data: Dict[str, Any] = field(default_factory=dict)
    animation_steps: List[AnimationStep] = field(default_factory=list)
    quiz: Optional[QuizQuestion] = None
    speaker_notes: SpeakerNotes = field(default_factory=SpeakerNotes)
    estimated_time_minutes: float = 1.5
    source_references: List[str] = field(default_factory=list)
    instructional_state: str = ""  # e.g. "EXPLANATION", "GUIDED_EXAMPLE", "RETRIEVAL"
    instructional_purpose: str = ""  # why this slide exists pedagogically
    objective_ids: List[str] = field(default_factory=list)  # O01... this slide serves


@dataclass
class ChapterPlan:
    """Curriculum and pedagogical plan for an extracted chapter."""
    id: str  # e.g. "ch01"
    title: str
    source_start_page: int
    source_end_page: int
    estimated_time_minutes: int
    subject_domain: SubjectDomain
    learning_objectives: List[str] = field(default_factory=list)
    prior_knowledge: List[str] = field(default_factory=list)
    core_concepts: List[str] = field(default_factory=list)
    misconceptions: List[Dict[str, str]] = field(default_factory=list)  # wrong vs right
    slides: List[SlideSpec] = field(default_factory=list)
    questions: List[QuizQuestion] = field(default_factory=list)
    pedagogical_plan: Optional["PedagogicalPlan"] = None  # machine-readable plan of record


# ---------------------------------------------------------------------------
# Pedagogical Intelligence Layer (machine-readable, testable, inspectable)
#
# Pipeline position: content model (ContentUnit/ledger) -> pedagogical model
# (below) -> storyboard model (SlideSpec) -> PPTX renderer.
# The storyboard engine must consume PedagogicalPlan.teaching_sequence;
# slide aesthetics must never determine instructional sequence.
# ---------------------------------------------------------------------------

class InstructionalState(str, Enum):
    HOOK = "HOOK"
    PRIOR_KNOWLEDGE = "PRIOR_KNOWLEDGE"
    OBJECTIVE = "OBJECTIVE"
    EXPLANATION = "EXPLANATION"
    VISUAL_MODEL = "VISUAL_MODEL"
    GUIDED_EXAMPLE = "GUIDED_EXAMPLE"
    RETRIEVAL = "RETRIEVAL"
    DEEPER_EXPLANATION = "DEEPER_EXPLANATION"
    MISCONCEPTION = "MISCONCEPTION"
    GUIDED_PRACTICE = "GUIDED_PRACTICE"
    INDEPENDENT_PRACTICE = "INDEPENDENT_PRACTICE"
    CUMULATIVE_RETRIEVAL = "CUMULATIVE_RETRIEVAL"
    RECAP = "RECAP"
    ASSESSMENT = "ASSESSMENT"


OBSERVABLE_VERBS = (
    "identify", "define", "explain", "compare", "classify", "calculate",
    "interpret", "predict", "apply", "analyse", "analyze", "evaluate", "construct",
    "describe", "distinguish", "solve", "derive", "justify",
)

ANIMATION_PURPOSES = (
    "signalling", "sequencing", "transformation", "causal_explanation",
    "comparison", "highlighting", "decomposition", "reconstruction",
    "error_correction", "answer_reveal",
)


@dataclass
class LearnerProfile:
    """Optional learner context; inferred cautiously when not provided."""
    grade: str = ""
    age_range: str = ""
    level: str = "general"  # e.g. middle_school, high_school, undergraduate, general
    prior_knowledge: str = ""
    curriculum: str = ""
    lesson_duration_minutes: int = 45
    language: str = "en"
    exam_orientation: str = ""
    inferred: bool = True  # True when defaulted rather than user-supplied

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grade": self.grade, "age_range": self.age_range, "level": self.level,
            "prior_knowledge": self.prior_knowledge, "curriculum": self.curriculum,
            "lesson_duration_minutes": self.lesson_duration_minutes,
            "language": self.language, "exam_orientation": self.exam_orientation,
            "inferred": self.inferred,
        }


@dataclass
class LearningObjective:
    """One observable learning outcome (backward design)."""
    id: str  # e.g. "O01"
    text: str
    verb: str = "explain"  # observable verb
    bloom_level: str = "understanding"  # recall/understanding/application/analysis/evaluation
    content_ids: List[str] = field(default_factory=list)  # C-ids that teach it

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "verb": self.verb,
                "bloom_level": self.bloom_level, "content_ids": self.content_ids}


@dataclass
class TeachingMove:
    """One instructional state in the teaching sequence (not a slide title)."""
    state: str  # InstructionalState value
    purpose: str  # why this move exists pedagogically
    content_ids: List[str] = field(default_factory=list)
    objective_ids: List[str] = field(default_factory=list)
    strategy: str = ""  # e.g. "worked_example", "dual_coding", "retrieval"
    teacher_move: str = ""  # lightweight teaching guide ("pause before revealing…")
    animation_purpose: str = ""  # one of ANIMATION_PURPOSES or ""
    complexity: str = "medium"  # low/medium/high -> drives pacing

    def to_dict(self) -> Dict[str, Any]:
        return {"state": self.state, "purpose": self.purpose,
                "content_ids": self.content_ids, "objective_ids": self.objective_ids,
                "strategy": self.strategy, "teacher_move": self.teacher_move,
                "animation_purpose": self.animation_purpose, "complexity": self.complexity}


@dataclass
class PedagogicalPlan:
    """Plan of record between content understanding and storyboard generation.

    Inspectable before PPTX rendering (exported as pedagogical_plan.json/md).
    Central rule: learning goal + content structure + learner needs -> strategy.
    Never a rigid per-chapter template.
    """
    chapter_id: str
    chapter_title: str
    subject_domain: str = "general"
    learner_profile: LearnerProfile = field(default_factory=LearnerProfile)
    learning_objectives: List[LearningObjective] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    concept_dependencies: List[List[str]] = field(default_factory=list)
    content_types: Dict[str, str] = field(default_factory=dict)  # C-id -> conceptual/procedural/factual
    pedagogical_strategies: List[str] = field(default_factory=list)
    teaching_sequence: List[TeachingMove] = field(default_factory=list)
    scaffolding_plan: List[str] = field(default_factory=list)  # I DO -> WE DO -> YOU DO…
    retrieval_plan: List[str] = field(default_factory=list)  # slide/state refs where retrieval happens
    assessment_map: Dict[str, List[str]] = field(default_factory=dict)  # O-id -> Q-ids
    misconceptions: List[Dict[str, str]] = field(default_factory=list)
    worked_examples: List[Dict[str, Any]] = field(default_factory=list)
    practice_plan: List[str] = field(default_factory=list)
    pacing_notes: str = ""
    safety_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_id": self.chapter_id, "chapter_title": self.chapter_title,
            "subject_domain": self.subject_domain,
            "learner_profile": self.learner_profile.to_dict(),
            "learning_objectives": [o.to_dict() for o in self.learning_objectives],
            "prerequisites": self.prerequisites,
            "concept_dependencies": self.concept_dependencies,
            "content_types": self.content_types,
            "pedagogical_strategies": self.pedagogical_strategies,
            "teaching_sequence": [m.to_dict() for m in self.teaching_sequence],
            "scaffolding_plan": self.scaffolding_plan,
            "retrieval_plan": self.retrieval_plan,
            "assessment_map": self.assessment_map,
            "misconceptions": self.misconceptions,
            "worked_examples": self.worked_examples,
            "practice_plan": self.practice_plan,
            "pacing_notes": self.pacing_notes,
            "safety_warnings": self.safety_warnings,
        }

    def to_markdown(self) -> str:
        lines = [f"# Pedagogical Plan: {self.chapter_title} (`{self.chapter_id}`)",
                 f"Domain: {self.subject_domain} | Strategies: {', '.join(self.pedagogical_strategies) or '—'}",
                 "",
                 "## Learning objectives (backward design)",
                 ""]
        for o in self.learning_objectives:
            lines.append(f"- **{o.id}** [{o.verb}/{o.bloom_level}] {o.text} (covers: {', '.join(o.content_ids) or '—'})")
        lines += ["", "## Prerequisites & dependencies", ""]
        for p in self.prerequisites:
            lines.append(f"- {p}")
        for chain in self.concept_dependencies:
            lines.append(f"- chain: {' → '.join(chain)}")
        lines += ["", "## Teaching sequence (instructional states)", ""]
        for i, m in enumerate(self.teaching_sequence, 1):
            lines.append(f"{i}. **{m.state}** — {m.purpose} [strategy: {m.strategy or '—'}]")
        lines += ["", "## Scaffolding (gradual release)", ""]
        for s in self.scaffolding_plan:
            lines.append(f"- {s}")
        lines += ["", "## Retrieval & spacing", ""]
        for r in self.retrieval_plan:
            lines.append(f"- {r}")
        lines += ["", "## Assessment alignment (O → Q)", ""]
        for oid, qids in self.assessment_map.items():
            lines.append(f"- {oid} → {', '.join(qids) or 'not yet assessed'}")
        lines += ["", "## Practice", ""]
        for p in self.practice_plan:
            lines.append(f"- {p}")
        if self.safety_warnings:
            lines += ["", "## Safety warnings", ""]
            for w in self.safety_warnings:
                lines.append(f"- ⚠ {w}")
        if self.pacing_notes:
            lines += ["", f"## Pacing", "", self.pacing_notes]
        return "\n".join(lines) + "\n"


@dataclass
class PedagogicalQAReport:
    """Pedagogical QA alongside PPTX validation (judgment, not rigid pass/fail)."""
    objectives_total: int = 0
    objectives_taught: int = 0
    objectives_practiced: int = 0
    objectives_assessed: int = 0
    prerequisites_identified: int = 0
    prerequisites_addressed: int = 0
    worked_examples: int = 0
    guided_practice_items: int = 0
    independent_practice_items: int = 0
    retrieval_opportunities: int = 0
    cumulative_retrieval: int = 0
    misconceptions_identified: int = 0
    misconceptions_addressed: int = 0
    formative_checks: int = 0
    assessment_coverage_percent: float = 0.0
    warnings: List[str] = field(default_factory=list)
    status: str = "PASS"  # PASS / WARN / FAIL

    def to_markdown(self) -> str:
        return "\n".join([
            "## PEDAGOGICAL QA", "",
            f"Learning objectives: {self.objectives_total}",
            f"Objectives taught: {self.objectives_taught}",
            f"Objectives practiced: {self.objectives_practiced}",
            f"Objectives assessed: {self.objectives_assessed}", "",
            f"Prerequisites identified: {self.prerequisites_identified}",
            f"Prerequisites addressed: {self.prerequisites_addressed}", "",
            f"Worked examples: {self.worked_examples}",
            f"Guided practice items: {self.guided_practice_items}",
            f"Independent practice items: {self.independent_practice_items}", "",
            f"Retrieval opportunities: {self.retrieval_opportunities}",
            f"Cumulative retrieval opportunities: {self.cumulative_retrieval}", "",
            f"Misconceptions identified: {self.misconceptions_identified}",
            f"Misconceptions addressed: {self.misconceptions_addressed}", "",
            f"Formative checks: {self.formative_checks}",
            f"Final assessment coverage: {self.assessment_coverage_percent}%", "",
            *((["Warnings:"] + [f"- {w}" for w in self.warnings]) if self.warnings else ["Warnings: none"]),
            "", f"Status: {self.status}",
        ])


@dataclass
class DocumentSection:
    """Section in the ingested document."""
    id: str
    title: str
    start_page: int
    end_page: int
    unit_title: Optional[str] = None
    text_content: str = ""


@dataclass
class DocumentMap:
    """Top-level map of the source document."""
    title: str
    source_file: str
    total_pages: int
    sections: List[DocumentSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
