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
