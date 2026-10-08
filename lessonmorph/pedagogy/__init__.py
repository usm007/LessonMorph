"""Pedagogy package for LessonMorph."""
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.misconceptions import MisconceptionDetector, StructuredMisconception
from lessonmorph.pedagogy.pacing import LessonPacingEstimate, PacingCalculator
from lessonmorph.pedagogy.learner import infer_learner_profile
from lessonmorph.pedagogy.strategies import (
    profile_content, select_strategies, synthesize_objectives, build_dependency_chain,
)
from lessonmorph.pedagogy.sequencing import build_teaching_sequence
from lessonmorph.pedagogy.quality import safety_check, build_qa_report
from lessonmorph.pedagogy.planner import PedagogicalPlanner

__all__ = [
    "SubjectClassifier",
    "MisconceptionDetector",
    "StructuredMisconception",
    "PacingCalculator",
    "LessonPacingEstimate",
    "PedagogicalPlanner",
    "infer_learner_profile",
    "profile_content",
    "select_strategies",
    "synthesize_objectives",
    "build_dependency_chain",
    "build_teaching_sequence",
    "safety_check",
    "build_qa_report",
]
