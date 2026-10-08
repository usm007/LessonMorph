"""Tests for the Content Completeness Ledger."""

from lessonmorph.core.models import ContentImportance, ContentType
from lessonmorph.ledger.ledger import ContentCompletenessLedger


def test_ledger_unit_creation_and_tracking():
    ledger = ContentCompletenessLedger(document_title="Test Physics Chapter")
    u1 = ledger.add_unit(
        source_location="Page 1, Paragraph 1",
        chapter_id="ch01",
        chapter_title="Newton's Laws",
        content_type=ContentType.DEFINITION,
        importance=ContentImportance.CORE,
        normalized_content="Inertia is the tendency of an object to resist changes in its state of motion.",
    )
    assert u1.id == "C001"
    assert not u1.covered
    assert ledger.coverage_summary()["uncovered_units"] == 1
    assert not ledger.coverage_summary()["is_complete"]

    # Mark covered
    ledger.mark_covered("C001", "Slide 4")
    assert u1.covered
    assert "Slide 4" in u1.covered_slides
    assert ledger.coverage_summary()["covered_units"] == 1
    assert ledger.coverage_summary()["uncovered_units"] == 0
    assert ledger.coverage_summary()["is_complete"]


def test_ledger_multiple_types_breakdown():
    ledger = ContentCompletenessLedger(document_title="Algebra")
    ledger.add_unit("p1", "ch01", "Linear Equations", ContentType.DEFINITION, ContentImportance.CORE, "Def")
    ledger.add_unit("p2", "ch01", "Linear Equations", ContentType.FORMULA, ContentImportance.CORE, "y = mx + b")
    ledger.add_unit("p3", "ch01", "Linear Equations", ContentType.EXAMPLE, ContentImportance.CORE, "Ex 1")

    summary = ledger.coverage_summary()
    assert summary["total_units"] == 3
    assert summary["type_breakdown"]["definition"]["total"] == 1
    assert summary["type_breakdown"]["formula"]["total"] == 1
    assert summary["type_breakdown"]["example"]["total"] == 1
