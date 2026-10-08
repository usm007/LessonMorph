"""Presentation Blueprint IR — the executable execution plan.

Pipeline position (authoritative pedagogy in, deterministic slides out):

    PedagogicalPlan (brain — DO NOT reinterpret)
        ↓  BlueprintCompiler (adapter)
    Blueprint / Presentation IR (this module — execution plan, inspectable)
        ↓  SlideComposer
    SlideSpec (renderer input — pure execution, no pedagogy)
        ↓  PptxRenderer
    PPTX

Every slide carries WHAT (concept/content), WHY (learning_goal/purpose),
HOW-encountered (task + reveal_sequence), HOW-represented (representation +
visual spec), HOW-used (teacher_action), HOW-checked (assessment) — as
separate fields. A bare `slide_type`/`visual_model` label is not sufficient.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Representation(str, Enum):
    """Finite visual grammar. The ONLY legal slide representations.

    Conceptual
    """
    DEFINITION_FOCUS = "definition_focus"
    BIG_IDEA = "big_idea"
    CONCEPT_CARD = "concept_card"
    KEY_PRINCIPLE = "key_principle"
    CONTRAST = "contrast"
    # Structural
    LABELED_DIAGRAM = "labeled_diagram"
    ANATOMY_MAP = "anatomy_map"
    HIERARCHY = "hierarchy"
    CUTAWAY = "cutaway"
    SPATIAL_RELATIONSHIP = "spatial_relationship"
    # Process
    FLOW = "flow"
    SEQUENCE = "sequence"
    CYCLE = "cycle"
    CAUSE_EFFECT = "cause_effect"
    BEFORE_AFTER = "before_after"
    PATHWAY = "pathway"
    # Quantitative
    EQUATION_FOCUS = "equation_focus"
    WORKED_CALCULATION = "worked_calculation"
    DATA_TABLE = "data_table"
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    COMPARISON_MATRIX = "comparison_matrix"
    # Assessment
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    PREDICTION = "prediction"
    DIAGNOSTIC_QUESTION = "diagnostic_question"
    RETRIEVAL = "retrieval"
    PRACTICE_PROBLEM = "practice_problem"
    # Synthesis
    CONCEPT_MAP = "concept_map"
    SUMMARY_MATRIX = "summary_matrix"
    BIG_PICTURE = "big_picture"
    # Chrome (non-instructional navigation only)
    TITLE = "title"
    ROADMAP = "roadmap"
    OBJECTIVES = "objectives"
    EXIT = "exit"


class TaskType(str, Enum):
    """Cognitive task taxonomy — structure follows the task, never a template."""
    DEFINITION = "definition"
    FACT = "fact"
    CONCEPT = "concept"
    MECHANISM = "mechanism"
    PROCESS = "process"
    SEQUENCE = "sequence"
    COMPARISON = "comparison"
    CLASSIFICATION = "classification"
    CALCULATION = "calculation"
    DERIVATION = "derivation"
    ARGUMENT = "argument"
    CASE_STUDY = "case_study"
    DIAGRAM_INTERPRETATION = "diagram_interpretation"
    EXPERIMENTAL_DATA = "experimental_data"
    MISCONCEPTION = "misconception"
    PROCEDURE = "procedure"
    APPLICATION = "application"
    PREDICTION = "prediction"
    RETRIEVAL = "retrieval"


# Representation families: which tasks each representation may serve.
# The adapter may ONLY pick within the task's family (hard prohibition:
# calculation templates for conceptual tasks and vice versa).
TASK_FAMILIES: Dict[TaskType, List[Representation]] = {
    TaskType.DEFINITION: [Representation.DEFINITION_FOCUS, Representation.CONCEPT_CARD,
                          Representation.KEY_PRINCIPLE],
    TaskType.FACT: [Representation.CONCEPT_CARD, Representation.KEY_PRINCIPLE,
                    Representation.DATA_TABLE],
    TaskType.CONCEPT: [Representation.CONCEPT_CARD, Representation.BIG_IDEA,
                       Representation.KEY_PRINCIPLE, Representation.CONTRAST,
                       Representation.CONCEPT_MAP, Representation.SUMMARY_MATRIX,
                       Representation.BIG_PICTURE],
    TaskType.MECHANISM: [Representation.LABELED_DIAGRAM, Representation.FLOW,
                         Representation.CAUSE_EFFECT, Representation.PATHWAY],
    TaskType.PROCESS: [Representation.FLOW, Representation.SEQUENCE,
                       Representation.PATHWAY, Representation.CYCLE],
    TaskType.SEQUENCE: [Representation.SEQUENCE, Representation.FLOW,
                        Representation.PATHWAY],
    TaskType.COMPARISON: [Representation.COMPARISON_MATRIX, Representation.CONTRAST,
                          Representation.BEFORE_AFTER],
    TaskType.CLASSIFICATION: [Representation.HIERARCHY, Representation.COMPARISON_MATRIX,
                              Representation.CONCEPT_MAP],
    TaskType.CALCULATION: [Representation.WORKED_CALCULATION, Representation.EQUATION_FOCUS],
    TaskType.DERIVATION: [Representation.EQUATION_FOCUS, Representation.WORKED_CALCULATION,
                          Representation.SEQUENCE],
    TaskType.ARGUMENT: [Representation.CAUSE_EFFECT, Representation.CONCEPT_CARD],
    TaskType.CASE_STUDY: [Representation.CONCEPT_CARD, Representation.CAUSE_EFFECT],
    TaskType.DIAGRAM_INTERPRETATION: [Representation.LABELED_DIAGRAM,
                                      Representation.ANATOMY_MAP,
                                      Representation.SPATIAL_RELATIONSHIP,
                                      Representation.CUTAWAY],
    TaskType.EXPERIMENTAL_DATA: [Representation.DATA_TABLE, Representation.BAR_CHART,
                                 Representation.LINE_CHART],
    TaskType.MISCONCEPTION: [Representation.CONTRAST, Representation.CAUSE_EFFECT],
    TaskType.PROCEDURE: [Representation.SEQUENCE, Representation.FLOW,
                         Representation.WORKED_CALCULATION],
    TaskType.APPLICATION: [Representation.PRACTICE_PROBLEM, Representation.CONCEPT_CARD],
    TaskType.PREDICTION: [Representation.PREDICTION, Representation.DIAGNOSTIC_QUESTION],
    TaskType.RETRIEVAL: [Representation.RETRIEVAL, Representation.TRUE_FALSE,
                         Representation.MCQ],
}

# Default representation per task (first choice unless content demands otherwise).
DEFAULT_REPRESENTATION: Dict[TaskType, Representation] = {
    t: reps[0] for t, reps in TASK_FAMILIES.items()
}

# Fallback when a slide must be simplified during repair (same family, simpler).
REPAIR_FALLBACK: Dict[Representation, Representation] = {
    Representation.LABELED_DIAGRAM: Representation.ANATOMY_MAP,
    Representation.ANATOMY_MAP: Representation.CONCEPT_CARD,
    Representation.PATHWAY: Representation.SEQUENCE,
    Representation.SEQUENCE: Representation.FLOW,
    Representation.FLOW: Representation.CONCEPT_CARD,
    Representation.CYCLE: Representation.SEQUENCE,
    Representation.COMPARISON_MATRIX: Representation.CONTRAST,
    Representation.WORKED_CALCULATION: Representation.EQUATION_FOCUS,
    Representation.CONCEPT_MAP: Representation.SUMMARY_MATRIX,
}


@dataclass
class EquationTerm:
    coefficient: str = ""  # e.g. "6" ("" means 1 / absent)
    species: str = ""  # e.g. "CO₂" (Unicode, never LaTeX)
    note: str = ""  # e.g. "atmospheric carbon dioxide via stomata"


@dataclass
class EquationIR:
    """Structured equation — renderer typesets this, never raw LaTeX."""
    lhs: List[EquationTerm] = field(default_factory=list)
    energy: str = ""  # e.g. "light energy"
    arrow: str = "→"
    rhs: List[EquationTerm] = field(default_factory=list)
    raw_source: str = ""  # original source text for traceability (never rendered)

    def inline(self) -> str:
        def side(terms: List[EquationTerm]) -> str:
            return " + ".join(f"{t.coefficient} {t.species}".strip() for t in terms)
        eq = f"{side(self.lhs)} {self.arrow} {side(self.rhs)}"
        if self.energy:
            eq = f"{side(self.lhs)} + [{self.energy}] {self.arrow} {side(self.rhs)}"
        return eq


@dataclass
class LockedAssessment:
    """Assessment locked ONCE from source. Answer slides render FROM this object.

    SOURCE QUESTION → SOURCE ANSWER → LOCKED ANSWER KEY → ASSESSMENT IR
    → SLIDE → ANSWER VALIDATOR. Nothing downstream may re-solve the answer.
    """
    id: str  # e.g. "photosynthesis_ionophore_01"
    type: str  # "mcq" | "true_false" | "short_answer"
    stem: str = ""
    options: Dict[str, str] = field(default_factory=dict)  # {"A": ..., "B": ...}
    correct_option: str = ""  # key into options; "" = NOT LOCKED (QA error)
    explanation: str = ""
    source_anchor: str = ""  # source section supporting the answer
    origin: str = ""  # "source" | "model_generated" (never silently substituted)
    objective_ids: List[str] = field(default_factory=list)

    def is_locked(self) -> bool:
        return bool(self.correct_option) and self.correct_option in self.options


@dataclass
class TeacherAction:
    type: str = ""  # "prompt" | "prediction" | "explanation" | ""
    prompt: str = ""
    focus: str = ""


@dataclass
class VisualSpec:
    """Explicit visual specification — the renderer executes this literally."""
    subject: str = ""
    structure: List[str] = field(default_factory=list)  # nodes/stages/parts in order
    labels: List[Dict[str, str]] = field(default_factory=list)  # name/target/explanation
    edges: List[Dict[str, str]] = field(default_factory=list)  # from/to/label (flows, cycles)
    columns: List[str] = field(default_factory=list)  # comparison_matrix headers
    rows: List[Dict[str, Any]] = field(default_factory=list)  # matrix rows / table rows
    equation: Optional[EquationIR] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SlideIR:
    """One executable slide: WHAT / WHY / HOW-encounter / HOW-represent / HOW-use / HOW-check."""
    id: str  # e.g. "slide_09"
    purpose: str  # pedagogical purpose (from TeachingMove)
    concept_id: str = ""
    concept_title: str = ""
    task: str = ""  # TaskType value
    learning_goal: List[str] = field(default_factory=list)
    representation: str = ""  # Representation value — REQUIRED (hard prohibition otherwise)
    content_title: str = ""
    body: Dict[str, Any] = field(default_factory=dict)  # semantic payload per representation
    visual: VisualSpec = field(default_factory=VisualSpec)
    reveal_sequence: List[str] = field(default_factory=list)
    teacher_action: TeacherAction = field(default_factory=TeacherAction)
    assessment: Optional[LockedAssessment] = None
    source_ids: List[str] = field(default_factory=list)  # C-ids (traceability)
    objective_ids: List[str] = field(default_factory=list)
    instructional_state: str = ""
    estimated_minutes: float = 2.0
    kicker: str = ""  # section header forwarded onto this slide (traceable)


@dataclass
class InventoryItem:
    """Source → Blueprint → Slide traceability (nothing important disappears)."""
    source_id: str
    kind: str  # definition|principle|equation|quantity|example|table|process|
    # misconception|question|answer|practice_problem|terminology
    slide_id: str = ""
    preserved: bool = False


@dataclass
class Blueprint:
    """The full execution plan for one chapter. Validated BEFORE any PPTX work."""
    chapter_id: str
    chapter_title: str
    subject_domain: str = "general"
    slides: List[SlideIR] = field(default_factory=list)
    inventory: List[InventoryItem] = field(default_factory=list)
    answer_keys: List[LockedAssessment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"chapter_id": self.chapter_id, "chapter_title": self.chapter_title,
                "subject_domain": self.subject_domain,
                "slides": [asdict(s) for s in self.slides],
                "inventory": [asdict(i) for i in self.inventory],
                "answer_keys": [asdict(a) for a in self.answer_keys]}

    def slide(self, slide_id: str) -> Optional[SlideIR]:
        return next((s for s in self.slides if s.id == slide_id), None)
