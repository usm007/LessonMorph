"""Blueprint package: Presentation IR execution layer (pedagogy in, slides out)."""
from lessonmorph.blueprint.ir import (
    Blueprint,
    DEFAULT_REPRESENTATION,
    REPAIR_FALLBACK,
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

__all__ = [
    "Blueprint", "DEFAULT_REPRESENTATION", "REPAIR_FALLBACK", "TASK_FAMILIES",
    "EquationIR", "EquationTerm", "InventoryItem", "LockedAssessment",
    "Representation", "SlideIR", "TaskType", "TeacherAction", "VisualSpec",
]
