"""PPTX EXPORTER — downstream of the Presentation IR, never upstream of design.

Position in architecture::

    PRESENTATION IR (Blueprint SlideIR, authoritative)
        -> SlideComposer (deterministic IR -> SlideSpec)
        -> PptxRenderer (executes representation literally)
        -> RenderQA + repair loop
        -> QualityGateValidator
        -> .pptx file (REGRESSION REFERENCE ONLY)

Rules:
- The exporter reads the SAME IR the browser pipeline reads. It never
  reinterprets pedagogy and never feeds anything back into the browser path.
- Nothing in lessonmorph/runtime or web/ imports this module.
- Kept functional for regression comparison; not a design target.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

from lessonmorph.blueprint.composer import SlideComposer
from lessonmorph.blueprint.render_qa import RenderQA
from lessonmorph.blueprint.repair import repair_blueprint
from lessonmorph.qa.validator import QualityGateValidator


def export_pptx(
    blueprints,
    chapter_plans,
    ledger,
    assets: Dict[str, Any],
    work_path: Path,
    out_path: Path,
    storyboard_engine=None,
) -> Dict[str, Any]:
    """IR -> editable .pptx. Returns slides, reports, and repair notes."""
    composer = SlideComposer()
    slides = []
    if len(chapter_plans) > 1 and storyboard_engine is not None:
        slides.append(storyboard_engine.build_contents_slide([p.title for p in chapter_plans]))
    for p, bp in zip(chapter_plans, blueprints):
        if len(chapter_plans) > 1 and storyboard_engine is not None:
            slides.append(storyboard_engine.build_chapter_divider(p))
        slides.extend(composer.compose_all(bp.slides, p.id))
        p.slides = slides

    for s in slides:
        img_id = (s.elements_data or {}).get("image_id")
        if img_id and img_id in (assets.get("mapping", {}) or {}):
            s.elements_data["image_path"] = assets["mapping"][img_id]

    storyboard_data = [
        {
            "slide_id": s.slide_id,
            "chapter_id": s.chapter_id,
            "title": s.title,
            "slide_type": s.slide_type.value,
            "visual_model": s.visual_model,
            "instructional_state": s.instructional_state,
            "instructional_purpose": s.instructional_purpose,
            "objective_ids": s.objective_ids,
            "animation_purposes": [getattr(a, "purpose", "") for a in (s.animation_steps or [])],
            "source_content_ids": s.source_content_ids,
            "estimated_time_minutes": s.estimated_time_minutes,
            "notes": s.speaker_notes.render_markdown(),
        }
        for s in slides
    ]
    (work_path / "storyboard.json").write_text(
        json.dumps(storyboard_data, ensure_ascii=False, indent=2), encoding="utf-8")

    from lessonmorph.renderer.engine import PptxRenderer
    renderer = PptxRenderer()
    renderer.render_presentation(slides, out_path)

    flat_bp = blueprints[0] if len(blueprints) == 1 else None
    render_report = RenderQA.inspect(out_path, flat_bp, work_dir=work_path)
    repair_notes: List[str] = []
    for _round in range(2):
        if not render_report.errors() or flat_bp is None:
            break
        repaired, notes = repair_blueprint(flat_bp, render_report)
        repair_notes.extend(notes)
        if not repaired:
            break
        (work_path / "blueprint_ch01.repaired.json").write_text(
            json.dumps(flat_bp.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        slides = composer.compose_all(flat_bp.slides, chapter_plans[0].id)
        chapter_plans[0].slides = slides
        renderer = PptxRenderer()
        renderer.render_presentation(slides, out_path)
        render_report = RenderQA.inspect(out_path, flat_bp, work_dir=work_path)

    return {
        "slides": slides,
        "storyboard_data": storyboard_data,
        "render_report": render_report,
        "repair_notes": repair_notes,
    }
