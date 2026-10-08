"""Main PowerPoint renderer engine for LessonMorph.

Compiles machine-readable slide specifications into an editable, classroom-ready
PowerPoint presentation (.pptx) with native shapes, 16:9 widescreen layout,
teacher speaker notes, and OpenXML animations.
"""

from __future__ import annotations
from pathlib import Path
from typing import List
import pptx
from lessonmorph.animation.engine import OoxmlAnimationEngine
from lessonmorph.core.models import SlideSpec
from lessonmorph.renderer.design import DesignSystem
from lessonmorph.renderer.diagrams import VisualModelRenderer


class PptxRenderer:
    """Renders SlideSpecs into a valid, native PowerPoint (.pptx) file."""

    def __init__(self):
        self.prs = pptx.Presentation()
        # Set 16:9 widescreen dimensions
        self.prs.slide_width = DesignSystem.SLIDE_WIDTH
        self.prs.slide_height = DesignSystem.SLIDE_HEIGHT
        self.blank_layout = self.prs.slide_layouts[6]  # Blank slide layout

    def render_presentation(self, slides: List[SlideSpec], output_path: Path | str) -> Path:
        """Renders all slide specifications into the output PPTX file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Asset directory: sibling work assets if provided via slide metadata
        for spec in slides:
            self._render_single_slide(spec)

        self.prs.save(str(out))
        # Post-save: patch animation timing that references real shape IDs
        # (animations are injected per-slide at render time; nothing further needed)
        return out

    def _render_single_slide(self, spec: SlideSpec) -> None:
        slide = self.prs.slides.add_slide(self.blank_layout)

        # 1. Dispatch to visual model renderer
        model = spec.visual_model
        animated_targets = []

        if model == "hero_title":
            animated_targets = VisualModelRenderer.render_hero_title(slide, spec)
        elif model == "roadmap_stepper":
            animated_targets = VisualModelRenderer.render_roadmap_stepper(slide, spec)
        elif model == "bullet_cards":
            animated_targets = VisualModelRenderer.render_learning_objectives(slide, spec)
        elif model == "prerequisite_grid":
            animated_targets = VisualModelRenderer.render_prior_knowledge(slide, spec)
        elif model == "definition_card":
            animated_targets = VisualModelRenderer.render_definition_card(slide, spec)
        elif model == "formula_breakdown":
            animated_targets = VisualModelRenderer.render_formula_breakdown(slide, spec)
        elif model == "stepped_cards":
            animated_targets = VisualModelRenderer.render_stepped_cards(slide, spec)
        elif model == "misconception_contrast":
            animated_targets = VisualModelRenderer.render_misconception_contrast(slide, spec)
        elif model == "quiz_prompt":
            animated_targets = VisualModelRenderer.render_quiz_prompt(slide, spec)
        elif model == "quiz_reveal":
            animated_targets = VisualModelRenderer.render_quiz_reveal(slide, spec)
        elif model == "table_display":
            animated_targets = VisualModelRenderer.render_table_display(slide, spec)
        elif model == "diagram_explanation":
            animated_targets = VisualModelRenderer.render_diagram_explanation(slide, spec)
        elif model in ("process_flow",):
            animated_targets = VisualModelRenderer.render_process_flow(slide, spec)
        elif model in ("2_column_compare", "comparison"):
            animated_targets = VisualModelRenderer.render_comparison(slide, spec)
        elif model in ("classification_grid",):
            animated_targets = VisualModelRenderer.render_classification_grid(slide, spec)
        elif model in ("timeline",):
            animated_targets = VisualModelRenderer.render_timeline(slide, spec)
        elif model in ("cause_effect",):
            animated_targets = VisualModelRenderer.render_cause_effect(slide, spec)
        elif model in ("chapter_divider",):
            animated_targets = VisualModelRenderer.render_chapter_divider(slide, spec)
        elif model in ("contents",):
            animated_targets = VisualModelRenderer.render_contents(slide, spec)
        elif model == "summary_cards":
            animated_targets = VisualModelRenderer.render_summary_cards(slide, spec)
        elif model == "practice_cards":
            animated_targets = VisualModelRenderer.render_practice_cards(slide, spec)
        elif model == "exit_ticket":
            animated_targets = VisualModelRenderer.render_exit_ticket(slide, spec)
        else:
            animated_targets = VisualModelRenderer.render_definition_card(slide, spec)

        # 2. Add teacher speaker notes + accessibility alt text
        if spec.speaker_notes:
            notes_slide = slide.notes_slide
            notes_tf = notes_slide.notes_text_frame
            notes_tf.text = spec.speaker_notes.render_markdown()

        self._apply_alt_text(slide, spec)

        # 3. Apply native OpenXML animation sequences if present.
        # Visual-model targets carry real shape IDs; storyboard animation_steps
        # use logical target names, so only visual targets are injected (avoids
        # invalid spids). Storyboard steps remain the teaching plan of record.
        if animated_targets:
            OoxmlAnimationEngine.apply_animations(slide, animated_targets)

    @staticmethod
    def _apply_alt_text(slide, spec: SlideSpec) -> None:
        """Sets meaningful alt text (cNvPr descr) for accessibility where supported."""
        alt = f"{spec.title}. {spec.purpose} ".strip()[:250]
        try:
            for shape in slide.shapes:
                try:
                    cNvPr = shape._element.find(
                        "{http://schemas.openxmlformats.org/presentationml/2006/main}nvPr"
                    )
                    # For pictures / shapes the cNvPr lives deeper; set name fallback
                    if shape.has_table:
                        continue
                    try:
                        shape.name = f"{spec.slide_id} {spec.visual_model}"[:60]
                    except Exception:
                        pass
                    # picture alt text via cNvPr descr
                    nvEl = shape._element.find(
                        ".//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr"
                    )
                    if nvEl is not None:
                        nvEl.set("descr", alt)
                except Exception:
                    continue
        except Exception:
            pass
