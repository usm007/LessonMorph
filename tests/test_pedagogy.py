"""Tests for pedagogy and teaching intelligence."""

from lessonmorph.core.models import SlideSpec, SlideType, SubjectDomain
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.misconceptions import MisconceptionDetector
from lessonmorph.pedagogy.pacing import PacingCalculator


def test_subject_classification():
    math_text = "Let us solve the quadratic equation x^2 - 5x + 6 = 0 by finding factors and roots."
    domain = SubjectClassifier.classify_domain(math_text)
    assert domain == SubjectDomain.MATHEMATICS

    physics_text = "The net force causes an acceleration according to Newton's second law with velocity and mass."
    domain_phys = SubjectClassifier.classify_domain(physics_text)
    assert domain_phys == SubjectDomain.PHYSICS


def test_misconception_detection():
    misconceptions = MisconceptionDetector.get_domain_misconceptions(
        SubjectDomain.PHYSICS, "free fall and gravity"
    )
    assert len(misconceptions) > 0
    assert "fall faster" in misconceptions[0].wrong_idea.lower()
    assert "9.8" in misconceptions[0].correct_idea


def test_pacing_calculator():
    slides = [
        SlideSpec("S1", "ch01", "Title", None, "intro", [], SlideType.TITLE, "hero_title"),
        SlideSpec("S2", "ch01", "Def", None, "teach", [], SlideType.CONCEPT_DEFINITION, "definition_card"),
        SlideSpec("S3", "ch01", "Worked", None, "practice", [], SlideType.WORKED_EXAMPLE, "stepped_cards"),
    ]
    pacing = PacingCalculator.estimate_chapter_pacing(slides)
    assert pacing.total_minutes >= 5
    assert "Introduction & Objectives" in pacing.breakdown_minutes
