"""Tests for QualityGateValidator and reporting."""

from pathlib import Path
from lessonmorph.core.models import ChapterPlan, ContentImportance, ContentType, SlideSpec, SlideType, SubjectDomain
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.qa.validator import QualityGateValidator
from lessonmorph.renderer.engine import PptxRenderer


def test_quality_gate_passes_complete_deck(tmp_path: Path):
    ledger = ContentCompletenessLedger("Biology")
    u = ledger.add_unit("p1", "ch01", "Cells", ContentType.DEFINITION, ContentImportance.CORE, "Cell theory")
    
    slides = [
        SlideSpec("S1", "ch01", "Title", None, "intro", [], SlideType.TITLE, "hero_title"),
        SlideSpec("S2", "ch01", "Def", None, "teach", ["C001"], SlideType.CONCEPT_DEFINITION, "definition_card"),
        SlideSpec("S3", "ch01", "Recap", None, "recap", [], SlideType.SUMMARY_RECAP, "summary_cards"),
    ]
    u.mark_covered("S2")

    plan = ChapterPlan("ch01", "Cells", 1, 1, 15, SubjectDomain.BIOLOGY)
    out_file = tmp_path / "bio.pptx"
    renderer = PptxRenderer()
    renderer.render_presentation(slides, out_file)

    report = QualityGateValidator.validate(out_file, ledger, plan, slides)
    assert report.overall_status in ("PASS", "WARN")
    assert report.content_units_uncovered == 0
    assert "## Quality Gate Checks" in report.to_markdown()
