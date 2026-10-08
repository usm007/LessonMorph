"""Pedagogy package for LessonMorph."""
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.misconceptions import MisconceptionDetector, StructuredMisconception
from lessonmorph.pedagogy.pacing import LessonPacingEstimate, PacingCalculator
from lessonmorph.pedagogy.planner import PedagogicalPlanner

__all__ = [
    "SubjectClassifier",
    "MisconceptionDetector",
    "StructuredMisconception",
    "PacingCalculator",
    "LessonPacingEstimate",
    "PedagogicalPlanner",
]
