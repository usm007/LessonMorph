"""Tests for StoryboardEngine."""

from lessonmorph.core.models import (
    ChapterPlan,
    ContentImportance,
    ContentType,
    DocumentSection,
    SlideType,
    SubjectDomain,
)
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.planner import PedagogicalPlanner
from lessonmorph.storyboard.engine import StoryboardEngine


def test_storyboard_generation_and_full_coverage():
    ledger = ContentCompletenessLedger(document_title="Thermodynamics")
    u1 = ledger.add_unit(
        "p1", "ch01", "Thermodynamics", ContentType.DEFINITION, ContentImportance.CORE,
        "Heat is energy transferred between substances due to a temperature difference."
    )
    u2 = ledger.add_unit(
        "p2", "ch01", "Thermodynamics", ContentType.FORMULA, ContentImportance.CORE,
        "Q = m * c * ΔT"
    )

    sec = DocumentSection("ch01", "Thermodynamics", 1, 2, text_content=u1.normalized_content)
    planner = PedagogicalPlanner(ledger)
    plan = planner.plan_chapter(sec)

    sb = StoryboardEngine(ledger)
    slides = sb.generate_storyboard(plan)

    assert len(slides) >= 6
    # Check that both u1 and u2 are covered
    assert u1.covered
    assert u2.covered
    assert ledger.coverage_summary()["uncovered_units"] == 0

    # Verify slide types exist
    types = [s.slide_type for s in slides]
    assert SlideType.TITLE in types
    assert SlideType.ROADMAP in types
    assert SlideType.LEARNING_OBJECTIVES in types
    assert SlideType.SUMMARY_RECAP in types
