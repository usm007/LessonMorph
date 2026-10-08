"""Visual model renderers for PowerPoint slides.

Implements rich, native presentation layouts: hero titles, roadmap steppers,
definition cards, formula breakdowns, worked problem stepped cards, misconception
contrasts, 2-stage quiz cards, and styled editable data tables.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from lessonmorph.core.models import AnimationType, SlideSpec
from lessonmorph.renderer.design import DesignSystem
from lessonmorph.renderer.shapes import ShapeHelper


class VisualModelRenderer:
    """Renders specific pedagogical visual models onto PowerPoint slides."""

    @classmethod
    def render_hero_title(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders dark hero title slide."""
        ShapeHelper.set_slide_background(slide, DesignSystem.COLOR_BG_HERO)

        # Subject Badge
        unit_text = spec.elements_data.get("unit_title", "LESSON")
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(1.5),
            Inches(2.0),
            Inches(2.8),
            Inches(0.4),
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = RGBColor(30, 41, 59)
        badge.line.color.rgb = DesignSystem.COLOR_ACCENT
        badge.line.width = Pt(1.5)
        p = badge.text_frame.paragraphs[0]
        p.text = f"• {unit_text} •"
        p.font.name = DesignSystem.FONT_BODY
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = DesignSystem.COLOR_ACCENT
        p.alignment = PP_ALIGN.CENTER

        # Main Title
        title_box = slide.shapes.add_textbox(
            Inches(1.5),
            Inches(2.6),
            Inches(10.3),
            Inches(1.8),
        )
        tf = title_box.text_frame
        tf.word_wrap = True
        p_title = tf.paragraphs[0]
        p_title.text = spec.title
        p_title.font.name = DesignSystem.FONT_TITLE
        p_title.font.size = DesignSystem.SIZE_HERO_TITLE
        p_title.font.bold = True
        p_title.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK

        # Subtitle
        if spec.subtitle:
            p_sub = tf.add_paragraph()
            p_sub.text = spec.subtitle
            p_sub.font.name = DesignSystem.FONT_BODY
            p_sub.font.size = Pt(18)
            p_sub.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK_MUTED
            p_sub.space_before = Pt(10)

        # Bottom Bar: Classroom Ready badge
        bottom_bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(1.5),
            Inches(5.5),
            Inches(4.5),
            Inches(0.45),
        )
        bottom_bar.fill.solid()
        bottom_bar.fill.fore_color.rgb = RGBColor(30, 41, 59)
        bottom_bar.line.color.rgb = RGBColor(51, 65, 85)
        p_bot = bottom_bar.text_frame.paragraphs[0]
        p_bot.text = "CLASSROOM-READY TEACHING DECK"
        p_bot.font.name = DesignSystem.FONT_BODY
        p_bot.font.size = Pt(11)
        p_bot.font.bold = True
        p_bot.font.color.rgb = RGBColor(148, 163, 184)
        p_bot.alignment = PP_ALIGN.CENTER

        return []

    @classmethod
    def render_roadmap_stepper(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders 4 connected roadmap cards."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Overview")

        stages = spec.elements_data.get("stages", [])
        num_stages = max(1, len(stages))
        card_width = (DesignSystem.CONTENT_WIDTH - Inches(0.3 * (num_stages - 1))) / num_stages
        card_height = Inches(3.8)
        top_y = Inches(2.2)

        for idx, stage in enumerate(stages):
            left_x = DesignSystem.MARGIN_LEFT + idx * (card_width + Inches(0.3))
            card = ShapeHelper.add_card(slide, left_x, top_y, card_width, card_height)

            # Step Number Pill
            pill = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                left_x + Inches(0.25),
                top_y + Inches(0.25),
                Inches(0.65),
                Inches(0.65),
            )
            pill.fill.solid()
            pill.fill.fore_color.rgb = DesignSystem.COLOR_ACCENT_BG
            pill.line.color.rgb = DesignSystem.COLOR_ACCENT
            p_pill = pill.text_frame.paragraphs[0]
            p_pill.text = stage.get("step", f"0{idx+1}")
            p_pill.font.bold = True
            p_pill.font.size = Pt(13)
            p_pill.font.color.rgb = DesignSystem.COLOR_ACCENT
            p_pill.alignment = PP_ALIGN.CENTER

            # Stage Name and Desc
            tb = slide.shapes.add_textbox(
                left_x + Inches(0.25),
                top_y + Inches(1.1),
                card_width - Inches(0.5),
                Inches(2.4),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p_name = tf.paragraphs[0]
            p_name.text = stage.get("name", f"Phase {idx+1}")
            p_name.font.name = DesignSystem.FONT_TITLE
            p_name.font.size = Pt(18)
            p_name.font.bold = True
            p_name.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

            p_desc = tf.add_paragraph()
            p_desc.text = stage.get("desc", "")
            p_desc.font.name = DesignSystem.FONT_BODY
            p_desc.font.size = Pt(14)
            p_desc.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY
            p_desc.space_before = Pt(8)

        return []

    @classmethod
    def render_learning_objectives(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders learning objectives cards."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Goals")

        objs = spec.elements_data.get("objectives", [])
        top_y = Inches(2.0)
        card_h = Inches(1.0)
        gap = Inches(0.22)

        for idx, obj in enumerate(objs[:4]):
            y = top_y + idx * (card_h + gap)
            card = ShapeHelper.add_card(slide, DesignSystem.MARGIN_LEFT, y, DesignSystem.CONTENT_WIDTH, card_h)

            # Left number accent
            num_box = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                DesignSystem.MARGIN_LEFT,
                y,
                Inches(0.9),
                card_h,
            )
            num_box.fill.solid()
            num_box.fill.fore_color.rgb = DesignSystem.COLOR_ACCENT
            num_box.line.fill.background()
            p_num = num_box.text_frame.paragraphs[0]
            p_num.text = f"{idx+1}"
            p_num.font.bold = True
            p_num.font.size = Pt(18)
            p_num.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK
            p_num.alignment = PP_ALIGN.CENTER

            # Text
            tb = slide.shapes.add_textbox(
                DesignSystem.MARGIN_LEFT + Inches(1.1),
                y + Inches(0.15),
                DesignSystem.CONTENT_WIDTH - Inches(1.3),
                card_h - Inches(0.3),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p_txt = tf.paragraphs[0]
            p_txt.text = obj
            p_txt.font.name = DesignSystem.FONT_BODY
            p_txt.font.size = Pt(16)
            p_txt.font.bold = True
            p_txt.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        return []

    @classmethod
    def render_prior_knowledge(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders prior knowledge prerequisites."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Prerequisites")

        prereqs = spec.elements_data.get("prerequisites", [])
        card_w = (DesignSystem.CONTENT_WIDTH - Inches(0.4)) / 2
        card_h = Inches(1.8)

        for idx, pr in enumerate(prereqs[:4]):
            col = idx % 2
            row = idx // 2
            left_x = DesignSystem.MARGIN_LEFT + col * (card_w + Inches(0.4))
            top_y = Inches(2.2) + row * (card_h + Inches(0.35))

            card = ShapeHelper.add_card(slide, left_x, top_y, card_w, card_h)
            tb = slide.shapes.add_textbox(
                left_x + Inches(0.3),
                top_y + Inches(0.2),
                card_w - Inches(0.6),
                card_h - Inches(0.4),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p_head = tf.paragraphs[0]
            p_head.text = f"• Prerequisite {idx+1}"
            p_head.font.bold = True
            p_head.font.size = Pt(13)
            p_head.font.color.rgb = DesignSystem.COLOR_ACCENT

            p_body = tf.add_paragraph()
            p_body.text = pr
            p_body.font.size = Pt(16)
            p_body.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            p_body.space_before = Pt(6)

        return []

    @classmethod
    def render_definition_card(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders formal definition card with high visual emphasis."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Core Concept")

        def_text = spec.elements_data.get("definition_text") or spec.elements_data.get("content", "")
        expl_text = spec.elements_data.get("explanation_text", "")
        src_ref = spec.elements_data.get("source_ref", "")

        # Main Definition Card
        card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(2.0),
            DesignSystem.CONTENT_WIDTH,
            Inches(2.8),
            border_color=DesignSystem.COLOR_ACCENT,
            border_width=Pt(2.0),
        )

        # Definition Callout Text
        tb = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.5),
            Inches(2.3),
            DesignSystem.CONTENT_WIDTH - Inches(1.0),
            Inches(2.2),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p_def = tf.paragraphs[0]
        p_def.text = f'"{def_text}"'
        p_def.font.name = DesignSystem.FONT_TITLE
        p_def.font.size = Pt(21)
        p_def.font.bold = True
        p_def.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        # Secondary Explanation / Context Card
        if expl_text or src_ref:
            sub_card = ShapeHelper.add_card(
                slide,
                DesignSystem.MARGIN_LEFT,
                Inches(5.0),
                DesignSystem.CONTENT_WIDTH,
                Inches(1.6),
                bg_color=DesignSystem.COLOR_ACCENT_BG,
                border_color=DesignSystem.COLOR_ACCENT_BORDER,
            )
            tb_sub = slide.shapes.add_textbox(
                DesignSystem.MARGIN_LEFT + Inches(0.4),
                Inches(5.15),
                DesignSystem.CONTENT_WIDTH - Inches(0.8),
                Inches(1.3),
            )
            tf_sub = tb_sub.text_frame
            tf_sub.word_wrap = True
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = expl_text if expl_text else "Key pedagogical insight from source material."
            p_sub.font.name = DesignSystem.FONT_BODY
            p_sub.font.size = Pt(16)
            p_sub.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

            if src_ref:
                p_ref = tf_sub.add_paragraph()
                p_ref.text = f"Source Reference: {src_ref}"
                p_ref.font.size = Pt(11)
                p_ref.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY
                p_ref.space_before = Pt(4)

        return []

    @classmethod
    def render_formula_breakdown(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders mathematical equation card with breakdown."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Formula")

        formula = spec.elements_data.get("formula", "")
        context = spec.elements_data.get("context", "")

        # Main Formula Box (Top)
        box = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(2.0),
            DesignSystem.CONTENT_WIDTH,
            Inches(1.8),
            bg_color=RGBColor(241, 245, 249),
            border_color=DesignSystem.COLOR_ACCENT,
            border_width=Pt(2),
        )
        tb_form = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.5),
            Inches(2.2),
            DesignSystem.CONTENT_WIDTH - Inches(1.0),
            Inches(1.4),
        )
        tf_f = tb_form.text_frame
        tf_f.word_wrap = True
        p_f = tf_f.paragraphs[0]
        p_f.text = formula
        p_f.font.name = DesignSystem.FONT_CODE
        p_f.font.size = Pt(26)
        p_f.font.bold = True
        p_f.font.color.rgb = RGBColor(15, 23, 42)
        p_f.alignment = PP_ALIGN.CENTER

        # Context and variables card (Bottom)
        bot_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(4.1),
            DesignSystem.CONTENT_WIDTH,
            Inches(2.5),
        )
        tb_c = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.4),
            Inches(4.3),
            DesignSystem.CONTENT_WIDTH - Inches(0.8),
            Inches(2.1),
        )
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        p_head = tf_c.paragraphs[0]
        p_head.text = "Mathematical & Physical Interpretation:"
        p_head.font.bold = True
        p_head.font.size = Pt(17)
        p_head.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        p_body = tf_c.add_paragraph()
        p_body.text = context if context else "Verify all units and boundary conditions during application."
        p_body.font.size = Pt(16)
        p_body.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY
        p_body.space_before = Pt(8)

        return []

    @classmethod
    def render_stepped_cards(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders worked example with animated progressive step reveal."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Worked Example")

        problem = spec.elements_data.get("problem", "Problem Statement")
        steps = spec.elements_data.get("steps", [])

        # Problem Box (Left Column: width 4.5 in)
        prob_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(2.0),
            Inches(4.2),
            Inches(4.7),
            bg_color=RGBColor(241, 245, 249),
        )
        tb_p = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.3),
            Inches(2.2),
            Inches(3.6),
            Inches(4.3),
        )
        tf_p = tb_p.text_frame
        tf_p.word_wrap = True
        p_title = tf_p.paragraphs[0]
        p_title.text = "PROBLEM PROMPT"
        p_title.font.bold = True
        p_title.font.size = Pt(13)
        p_title.font.color.rgb = DesignSystem.COLOR_ACCENT

        p_prob = tf_p.add_paragraph()
        p_prob.text = problem
        p_prob.font.size = Pt(16)
        p_prob.font.bold = True
        p_prob.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        p_prob.space_before = Pt(10)

        # Step Cards (Right Column: width 7.1 in)
        right_x = DesignSystem.MARGIN_LEFT + Inches(4.6)
        right_w = DesignSystem.CONTENT_WIDTH - Inches(4.6)
        num_steps = max(1, len(steps))
        step_h = min(Inches(1.4), (Inches(4.7) - Inches(0.2 * (num_steps - 1))) / num_steps)

        animated_targets: List[Tuple[int, AnimationType]] = []

        for s_idx, step_text in enumerate(steps[:3]):
            y = Inches(2.0) + s_idx * (step_h + Inches(0.2))
            step_card = ShapeHelper.add_card(
                slide,
                right_x,
                y,
                right_w,
                step_h,
                border_color=DesignSystem.COLOR_ACCENT if s_idx == 0 else DesignSystem.COLOR_BORDER_CARD,
            )

            tb_s = slide.shapes.add_textbox(
                right_x + Inches(0.3),
                y + Inches(0.15),
                right_w - Inches(0.6),
                step_h - Inches(0.3),
            )
            tf_s = tb_s.text_frame
            tf_s.word_wrap = True
            p_shead = tf_s.paragraphs[0]
            p_shead.text = f"STEP {s_idx + 1}"
            p_shead.font.bold = True
            p_shead.font.size = Pt(12)
            p_shead.font.color.rgb = DesignSystem.COLOR_ACCENT

            p_sbody = tf_s.add_paragraph()
            p_sbody.text = step_text
            p_sbody.font.size = Pt(15)
            p_sbody.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            p_sbody.space_before = Pt(3)

            # Step 2 and beyond get animated reveal
            if s_idx > 0:
                animated_targets.append((step_card.shape_id, AnimationType.APPEAR))

        return animated_targets

    @classmethod
    def render_misconception_contrast(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders side-by-side: Common Mistake (Red/Crossed Out) vs Correct Reasoning (Green/Checkmark)."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Misconception & Trap")

        wrong_idea = spec.elements_data.get("wrong_idea", "")
        why_wrong = spec.elements_data.get("why_wrong", "")
        correct_idea = spec.elements_data.get("correct_idea", "")
        correct_reasoning = spec.elements_data.get("correct_reasoning", "")

        col_w = (DesignSystem.CONTENT_WIDTH - Inches(0.4)) / 2
        card_h = Inches(4.7)
        top_y = Inches(2.0)

        # 1. Left Card: Common Mistake (Rose theme)
        left_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            top_y,
            col_w,
            card_h,
            bg_color=DesignSystem.COLOR_DANGER_BG,
            border_color=DesignSystem.COLOR_DANGER,
            border_width=Pt(2),
        )
        tb_w = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.4),
            top_y + Inches(0.3),
            col_w - Inches(0.8),
            card_h - Inches(0.6),
        )
        tf_w = tb_w.text_frame
        tf_w.word_wrap = True
        p_wh = tf_w.paragraphs[0]
        p_wh.text = "✖  COMMON MISTAKE (TEMPTING ERROR)"
        p_wh.font.bold = True
        p_wh.font.size = Pt(13)
        p_wh.font.color.rgb = DesignSystem.COLOR_DANGER

        p_wi = tf_w.add_paragraph()
        p_wi.text = wrong_idea
        p_wi.font.name = DesignSystem.FONT_TITLE
        p_wi.font.size = Pt(19)
        p_wi.font.bold = True
        p_wi.font.color.rgb = DesignSystem.COLOR_DANGER
        p_wi.space_before = Pt(12)

        p_why = tf_w.add_paragraph()
        p_why.text = f"Why it is flawed:\n{why_wrong}"
        p_why.font.size = Pt(15)
        p_why.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        p_why.space_before = Pt(14)

        # 2. Right Card: Correct Reasoning (Emerald theme)
        right_x = DesignSystem.MARGIN_LEFT + col_w + Inches(0.4)
        right_card = ShapeHelper.add_card(
            slide,
            right_x,
            top_y,
            col_w,
            card_h,
            bg_color=DesignSystem.COLOR_SUCCESS_BG,
            border_color=DesignSystem.COLOR_SUCCESS,
            border_width=Pt(2),
        )
        tb_c = slide.shapes.add_textbox(
            right_x + Inches(0.4),
            top_y + Inches(0.3),
            col_w - Inches(0.8),
            card_h - Inches(0.6),
        )
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        p_ch = tf_c.paragraphs[0]
        p_ch.text = "✔  CORRECT REASONING & TRUTH"
        p_ch.font.bold = True
        p_ch.font.size = Pt(13)
        p_ch.font.color.rgb = DesignSystem.COLOR_SUCCESS

        p_ci = tf_c.add_paragraph()
        p_ci.text = correct_idea
        p_ci.font.name = DesignSystem.FONT_TITLE
        p_ci.font.size = Pt(19)
        p_ci.font.bold = True
        p_ci.font.color.rgb = DesignSystem.COLOR_SUCCESS
        p_ci.space_before = Pt(12)

        p_cr = tf_c.add_paragraph()
        p_cr.text = f"Why this is sound:\n{correct_reasoning}"
        p_cr.font.size = Pt(15)
        p_cr.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        p_cr.space_before = Pt(14)

        # Animate right card reveal
        return [(right_card.shape_id, AnimationType.APPEAR)]

    @classmethod
    def render_quiz_prompt(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders classroom check: question prompt and options without revealing answer."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Question")

        prompt = spec.elements_data.get("prompt", "")
        options = spec.elements_data.get("options", [])

        # Question Prompt Box
        q_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(2.0),
            DesignSystem.CONTENT_WIDTH,
            Inches(1.8),
            border_color=DesignSystem.COLOR_ACCENT,
            border_width=Pt(2),
        )
        tb_q = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.4),
            Inches(2.2),
            DesignSystem.CONTENT_WIDTH - Inches(0.8),
            Inches(1.4),
        )
        tf_q = tb_q.text_frame
        tf_q.word_wrap = True
        p_q = tf_q.paragraphs[0]
        p_q.text = prompt
        p_q.font.name = DesignSystem.FONT_TITLE
        p_q.font.size = Pt(20)
        p_q.font.bold = True
        p_q.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        # Options if available
        if options:
            top_y = Inches(4.0)
            opt_h = Inches(0.7)
            for idx, opt in enumerate(options[:4]):
                y = top_y + idx * (opt_h + Inches(0.15))
                card = ShapeHelper.add_card(
                    slide,
                    DesignSystem.MARGIN_LEFT,
                    y,
                    DesignSystem.CONTENT_WIDTH,
                    opt_h,
                )
                tb_o = slide.shapes.add_textbox(
                    DesignSystem.MARGIN_LEFT + Inches(0.3),
                    y + Inches(0.1),
                    DesignSystem.CONTENT_WIDTH - Inches(0.6),
                    opt_h - Inches(0.2),
                )
                tf_o = tb_o.text_frame
                tf_o.word_wrap = True
                p_o = tf_o.paragraphs[0]
                p_o.text = opt
                p_o.font.size = Pt(16)
                p_o.font.bold = True
                p_o.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        else:
            # Open question instruction card
            prompt_card = ShapeHelper.add_card(
                slide,
                DesignSystem.MARGIN_LEFT,
                Inches(4.2),
                DesignSystem.CONTENT_WIDTH,
                Inches(2.2),
                bg_color=DesignSystem.COLOR_ACCENT_BG,
                border_color=DesignSystem.COLOR_ACCENT_BORDER,
            )
            tb_inst = slide.shapes.add_textbox(
                DesignSystem.MARGIN_LEFT + Inches(0.4),
                Inches(4.5),
                DesignSystem.CONTENT_WIDTH - Inches(0.8),
                Inches(1.6),
            )
            tf_i = tb_inst.text_frame
            tf_i.word_wrap = True
            p_i = tf_i.paragraphs[0]
            p_i.text = "Quiet thinking time: 30 seconds."
            p_i.font.bold = True
            p_i.font.size = Pt(18)
            p_i.font.color.rgb = DesignSystem.COLOR_ACCENT

            p_i2 = tf_i.add_paragraph()
            p_i2.text = "Write your response in your notebook before we reveal the answer."
            p_i2.font.size = Pt(16)
            p_i2.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY
            p_i2.space_before = Pt(8)

        return []

    @classmethod
    def render_quiz_reveal(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders check for understanding answer reveal and full explanation."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Answer & Solution")

        prompt = spec.elements_data.get("prompt", "")
        correct_answer = spec.elements_data.get("correct_answer", "")
        explanation = spec.elements_data.get("explanation", "")

        # Top: Prompt reminder
        top_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(2.0),
            DesignSystem.CONTENT_WIDTH,
            Inches(1.1),
            bg_color=RGBColor(241, 245, 249),
        )
        tb_t = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.3),
            Inches(2.1),
            DesignSystem.CONTENT_WIDTH - Inches(0.6),
            Inches(0.9),
        )
        tf_t = tb_t.text_frame
        tf_t.word_wrap = True
        p_t = tf_t.paragraphs[0]
        p_t.text = f"Question: {prompt}"
        p_t.font.size = Pt(15)
        p_t.font.bold = True
        p_t.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY

        # Middle: Correct Answer Reveal Card (Emerald Theme)
        ans_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(3.3),
            DesignSystem.CONTENT_WIDTH,
            Inches(1.4),
            bg_color=DesignSystem.COLOR_SUCCESS_BG,
            border_color=DesignSystem.COLOR_SUCCESS,
            border_width=Pt(2),
        )
        tb_a = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.4),
            Inches(3.45),
            DesignSystem.CONTENT_WIDTH - Inches(0.8),
            Inches(1.1),
        )
        tf_a = tb_a.text_frame
        tf_a.word_wrap = True
        p_ah = tf_a.paragraphs[0]
        p_ah.text = "✔  CORRECT ANSWER:"
        p_ah.font.bold = True
        p_ah.font.size = Pt(13)
        p_ah.font.color.rgb = DesignSystem.COLOR_SUCCESS

        p_ab = tf_a.add_paragraph()
        p_ab.text = correct_answer
        p_ab.font.name = DesignSystem.FONT_TITLE
        p_ab.font.size = Pt(21)
        p_ab.font.bold = True
        p_ab.font.color.rgb = DesignSystem.COLOR_SUCCESS
        p_ab.space_before = Pt(4)

        # Bottom: Detailed Explanation Card
        exp_card = ShapeHelper.add_card(
            slide,
            DesignSystem.MARGIN_LEFT,
            Inches(4.9),
            DesignSystem.CONTENT_WIDTH,
            Inches(1.8),
        )
        tb_e = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.4),
            Inches(5.05),
            DesignSystem.CONTENT_WIDTH - Inches(0.8),
            Inches(1.5),
        )
        tf_e = tb_e.text_frame
        tf_e.word_wrap = True
        p_eh = tf_e.paragraphs[0]
        p_eh.text = "PEDAGOGICAL EXPLANATION & REASONING:"
        p_eh.font.bold = True
        p_eh.font.size = Pt(13)
        p_eh.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        p_eb = tf_e.add_paragraph()
        p_eb.text = explanation
        p_eb.font.size = Pt(15)
        p_eb.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY
        p_eb.space_before = Pt(6)

        return [(ans_card.shape_id, AnimationType.ANSWER_REVEAL)]

    @classmethod
    def render_table_display(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders clean styled native PowerPoint table."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Data Table")

        headers = spec.elements_data.get("headers", ["Column 1", "Column 2"])
        rows = spec.elements_data.get("rows", [["A", "B"]])

        num_rows = min(6, len(rows) + 1)
        num_cols = min(6, len(headers))
        table_shape = slide.shapes.add_table(
            num_rows,
            num_cols,
            DesignSystem.MARGIN_LEFT,
            Inches(2.1),
            DesignSystem.CONTENT_WIDTH,
            Inches(4.5),
        )
        table = table_shape.table

        # Format Header Row
        for col_idx in range(num_cols):
            cell = table.cell(0, col_idx)
            cell.text = headers[col_idx] if col_idx < len(headers) else ""
            cell.fill.solid()
            cell.fill.fore_color.rgb = DesignSystem.COLOR_ACCENT
            for p in cell.text_frame.paragraphs:
                p.font.name = DesignSystem.FONT_BODY
                p.font.size = Pt(15)
                p.font.bold = True
                p.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK
                p.alignment = PP_ALIGN.CENTER

        # Format Data Rows
        for r_idx in range(1, num_rows):
            data_row = rows[r_idx - 1] if r_idx - 1 < len(rows) else []
            for col_idx in range(num_cols):
                cell = table.cell(r_idx, col_idx)
                cell.text = str(data_row[col_idx]) if col_idx < len(data_row) else ""
                cell.fill.solid()
                # Zebra striping
                cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if r_idx % 2 == 1 else RGBColor(255, 255, 255)
                for p in cell.text_frame.paragraphs:
                    p.font.name = DesignSystem.FONT_BODY
                    p.font.size = Pt(14)
                    p.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        return []

    @classmethod
    def render_summary_cards(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders summary takeaways cards."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Takeaways")

        takeaways = spec.elements_data.get("takeaways", [])
        num_items = max(1, len(takeaways))
        card_w = (DesignSystem.CONTENT_WIDTH - Inches(0.3 * (num_items - 1))) / num_items
        card_h = Inches(4.2)
        top_y = Inches(2.1)

        for idx, t in enumerate(takeaways[:4]):
            x = DesignSystem.MARGIN_LEFT + idx * (card_w + Inches(0.3))
            card = ShapeHelper.add_card(
                slide,
                x,
                top_y,
                card_w,
                card_h,
                border_color=DesignSystem.COLOR_ACCENT if idx == 0 else DesignSystem.COLOR_BORDER_CARD,
            )
            # Card Top Badge
            badge = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                x,
                top_y,
                card_w,
                Inches(0.4),
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = DesignSystem.COLOR_ACCENT
            badge.line.fill.background()
            p_b = badge.text_frame.paragraphs[0]
            p_b.text = f"KEY TAKEAWAY #{idx+1}"
            p_b.font.bold = True
            p_b.font.size = Pt(11)
            p_b.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK
            p_b.alignment = PP_ALIGN.CENTER

            # Body text
            tb = slide.shapes.add_textbox(
                x + Inches(0.25),
                top_y + Inches(0.6),
                card_w - Inches(0.5),
                card_h - Inches(0.8),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p_t = tf.paragraphs[0]
            p_t.text = t
            p_t.font.name = DesignSystem.FONT_BODY
            p_t.font.size = Pt(16)
            p_t.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        return []

    @classmethod
    def render_practice_cards(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders practice problems list."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Practice")

        problems = spec.elements_data.get("problems", [])
        card_h = Inches(1.2)
        top_y = Inches(2.1)
        gap = Inches(0.25)

        for idx, prob in enumerate(problems[:3]):
            y = top_y + idx * (card_h + gap)
            card = ShapeHelper.add_card(slide, DesignSystem.MARGIN_LEFT, y, DesignSystem.CONTENT_WIDTH, card_h)
            tb = slide.shapes.add_textbox(
                DesignSystem.MARGIN_LEFT + Inches(0.4),
                y + Inches(0.15),
                DesignSystem.CONTENT_WIDTH - Inches(0.8),
                card_h - Inches(0.3),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = prob
            p.font.name = DesignSystem.FONT_BODY
            p.font.size = Pt(16)
            p.font.bold = True
            p.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        return []

    @classmethod
    def render_exit_ticket(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Renders end-of-class exit ticket cards."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Reflection")

        prompt1 = spec.elements_data.get("prompt_1", "What was the core takeaway today?")
        prompt2 = spec.elements_data.get("prompt_2", "What is one question you still have?")

        col_w = (DesignSystem.CONTENT_WIDTH - Inches(0.4)) / 2
        card_h = Inches(4.3)
        top_y = Inches(2.2)

        # Prompt 1
        ShapeHelper.add_card(slide, DesignSystem.MARGIN_LEFT, top_y, col_w, card_h)
        tb1 = slide.shapes.add_textbox(
            DesignSystem.MARGIN_LEFT + Inches(0.4),
            top_y + Inches(0.4),
            col_w - Inches(0.8),
            card_h - Inches(0.8),
        )
        tf1 = tb1.text_frame
        tf1.word_wrap = True
        p1 = tf1.paragraphs[0]
        p1.text = prompt1
        p1.font.name = DesignSystem.FONT_TITLE
        p1.font.size = Pt(18)
        p1.font.bold = True
        p1.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        # Prompt 2
        right_x = DesignSystem.MARGIN_LEFT + col_w + Inches(0.4)
        ShapeHelper.add_card(slide, right_x, top_y, col_w, card_h)
        tb2 = slide.shapes.add_textbox(
            right_x + Inches(0.4),
            top_y + Inches(0.4),
            col_w - Inches(0.8),
            card_h - Inches(0.8),
        )
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = prompt2
        p2.font.name = DesignSystem.FONT_TITLE
        p2.font.size = Pt(18)
        p2.font.bold = True
        p2.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY

        return []

    # ---- Papermorph-adapted generic visual models (subject-aware strategies) ----

    @classmethod
    def render_diagram_explanation(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Labeled structure / mechanism visual: caption + recreated label chips + optional embedded image."""
        from pathlib import Path as _Path
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Visual Model")
        caption = spec.elements_data.get("caption") or spec.elements_data.get("content", "")
        src_ref = spec.elements_data.get("source_ref", "")
        image_path = spec.elements_data.get("image_path")
        # Left: visual stage card
        stage = ShapeHelper.add_card(
            slide, DesignSystem.MARGIN_LEFT, Inches(2.0),
            Inches(7.0), Inches(4.7),
            bg_color=DesignSystem.COLOR_BG_CARD,
            border_color=DesignSystem.COLOR_ACCENT,
            border_width=Pt(2),
        )
        embedded = False
        if image_path:
            try:
                p = _Path(str(image_path))
                if p.exists():
                    slide.shapes.add_picture(
                        str(p),
                        DesignSystem.MARGIN_LEFT + Inches(0.3),
                        Inches(2.3),
                        width=Inches(6.4), height=Inches(3.2),
                    )
                    embedded = True
            except Exception:
                embedded = False
        if not embedded:
            tb_stage = slide.shapes.add_textbox(
                DesignSystem.MARGIN_LEFT + Inches(0.4), Inches(2.3),
                Inches(6.2), Inches(3.4),
            )
            tf = tb_stage.text_frame
            tf.word_wrap = True
            ph = tf.paragraphs[0]
            ph.text = "VISUAL MODEL — recreated from source"
            ph.font.bold = True
            ph.font.size = Pt(12)
            ph.font.color.rgb = DesignSystem.COLOR_ACCENT
            pb = tf.add_paragraph()
            pb.text = caption[:500] if caption else "See speaker notes for label-by-label walkthrough."
            pb.font.size = Pt(15)
            pb.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            pb.space_before = Pt(8)
        # Right: label / walkthrough card
        rx = DesignSystem.MARGIN_LEFT + Inches(7.4)
        ShapeHelper.add_card(slide, rx, Inches(2.0), DesignSystem.CONTENT_WIDTH - Inches(7.4), Inches(4.7))
        tb = slide.shapes.add_textbox(rx + Inches(0.3), Inches(2.2), DesignSystem.CONTENT_WIDTH - Inches(8.0), Inches(4.3))
        tf = tb.text_frame
        tf.word_wrap = True
        ph = tf.paragraphs[0]
        ph.text = "READ THE DIAGRAM"
        ph.font.bold = True
        ph.font.size = Pt(12)
        ph.font.color.rgb = DesignSystem.COLOR_ACCENT
        pb = tf.add_paragraph()
        pb.text = caption[:600]
        pb.font.size = Pt(15)
        pb.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        pb.space_before = Pt(8)
        if src_ref:
            pr = tf.add_paragraph()
            pr.text = f"Source: {src_ref}"
            pr.font.size = Pt(11)
            pr.font.color.rgb = DesignSystem.COLOR_TEXT_SECONDARY
            pr.space_before = Pt(6)
        try:
            stage.name = f"diagram_stage_{spec.slide_id}"
        except Exception:
            pass
        return []

    @classmethod
    def render_process_flow(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Sequential stages with connecting arrows; steps reveal progressively."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Process")
        content = spec.elements_data.get("content", "")
        import re as _re
        parts = [p.strip(" -•\t") for p in _re.split(r"\n+", content) if p.strip()]
        if len(parts) <= 1 and len(content) > 120:
            parts = [content[i:i + 160] for i in range(0, len(content), 160)][:4]
        steps = parts[:4] if parts else [content or "Process stages from source."]
        n = len(steps)
        card_w = (DesignSystem.CONTENT_WIDTH - Inches(0.5 * (n - 1))) / n
        animated: List[Tuple[int, AnimationType]] = []
        for idx, st in enumerate(steps):
            x = DesignSystem.MARGIN_LEFT + idx * (card_w + Inches(0.5))
            card = ShapeHelper.add_card(slide, x, Inches(2.4), card_w, Inches(3.6))
            tb = slide.shapes.add_textbox(x + Inches(0.25), Inches(2.6), card_w - Inches(0.5), Inches(3.2))
            tf = tb.text_frame
            tf.word_wrap = True
            ph = tf.paragraphs[0]
            ph.text = f"STAGE {idx + 1}"
            ph.font.bold = True
            ph.font.size = Pt(12)
            ph.font.color.rgb = DesignSystem.COLOR_ACCENT
            pb = tf.add_paragraph()
            pb.text = st[:380]
            pb.font.size = Pt(14)
            pb.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            pb.space_before = Pt(6)
            if idx > 0:
                animated.append((card.shape_id, AnimationType.APPEAR))
        return animated

    @classmethod
    def render_comparison(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Side-by-side comparison (2_column_compare alias)."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Comparison")
        content = spec.elements_data.get("content", "")
        import re as _re
        halves = _re.split(r"\b(?:vs\.?|versus|compared (?:to|with)|on the other hand)\b", content, flags=_re.IGNORECASE)
        left_t = halves[0].strip()[:500] if halves else content[:500]
        right_t = halves[1].strip()[:500] if len(halves) > 1 else "Contrast, difference, or trade-off from source notes."
        col_w = (DesignSystem.CONTENT_WIDTH - Inches(0.4)) / 2
        ShapeHelper.add_card(slide, DesignSystem.MARGIN_LEFT, Inches(2.0), col_w, Inches(4.7),
                             border_color=DesignSystem.COLOR_ACCENT, border_width=Pt(2))
        tb = slide.shapes.add_textbox(DesignSystem.MARGIN_LEFT + Inches(0.35), Inches(2.3), col_w - Inches(0.7), Inches(4.1))
        tf = tb.text_frame
        tf.word_wrap = True
        pa = tf.paragraphs[0]
        pa.text = "A"
        pa.font.bold = True
        pa.font.size = Pt(13)
        pa.font.color.rgb = DesignSystem.COLOR_ACCENT
        pb = tf.add_paragraph()
        pb.text = left_t
        pb.font.size = Pt(15)
        pb.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        pb.space_before = Pt(6)
        rx = DesignSystem.MARGIN_LEFT + col_w + Inches(0.4)
        ShapeHelper.add_card(slide, rx, Inches(2.0), col_w, Inches(4.7))
        tb2 = slide.shapes.add_textbox(rx + Inches(0.35), Inches(2.3), col_w - Inches(0.7), Inches(4.1))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        pa2 = tf2.paragraphs[0]
        pa2.text = "B"
        pa2.font.bold = True
        pa2.font.size = Pt(13)
        pa2.font.color.rgb = DesignSystem.COLOR_ACCENT
        pb2 = tf2.add_paragraph()
        pb2.text = right_t
        pb2.font.size = Pt(15)
        pb2.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
        pb2.space_before = Pt(6)
        return []

    @classmethod
    def render_classification_grid(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Grouping / categorization into up to 4 labeled buckets."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Classification")
        content = spec.elements_data.get("content", "")
        import re as _re
        items = [i.strip(" -•\t") for i in _re.split(r"\n+", content) if i.strip()][:4]
        if not items:
            items = [content[:300] if content else "Category from source."]
        card_w = (DesignSystem.CONTENT_WIDTH - Inches(0.4)) / 2
        for idx, item in enumerate(items[:4]):
            col, row = idx % 2, idx // 2
            x = DesignSystem.MARGIN_LEFT + col * (card_w + Inches(0.4))
            y = Inches(2.1) + row * Inches(2.4)
            ShapeHelper.add_card(slide, x, y, card_w, Inches(2.1))
            tb = slide.shapes.add_textbox(x + Inches(0.3), y + Inches(0.2), card_w - Inches(0.6), Inches(1.7))
            tf = tb.text_frame
            tf.word_wrap = True
            ph = tf.paragraphs[0]
            ph.text = f"GROUP {idx + 1}"
            ph.font.bold = True
            ph.font.size = Pt(12)
            ph.font.color.rgb = DesignSystem.COLOR_ACCENT
            pb = tf.add_paragraph()
            pb.text = item[:320]
            pb.font.size = Pt(14)
            pb.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            pb.space_before = Pt(6)
        return []

    @classmethod
    def render_timeline(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Chronological spine with up to 4 dated events."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Timeline")
        content = spec.elements_data.get("content", "")
        import re as _re
        items = [i.strip(" -•\t") for i in _re.split(r"\n+", content) if i.strip()][:4]
        if not items:
            items = [content[:300] if content else "Event from source."]
        spine = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, DesignSystem.MARGIN_LEFT, Inches(3.9),
            DesignSystem.CONTENT_WIDTH, Inches(0.08),
        )
        spine.fill.solid()
        spine.fill.fore_color.rgb = DesignSystem.COLOR_ACCENT
        spine.line.fill.background()
        n = len(items)
        card_w = (DesignSystem.CONTENT_WIDTH - Inches(0.3) * (n - 1)) / n if n else DesignSystem.CONTENT_WIDTH
        for idx, item in enumerate(items):
            x = DesignSystem.MARGIN_LEFT + idx * (card_w + Inches(0.3))
            ShapeHelper.add_card(slide, x, Inches(2.0), card_w, Inches(1.7))
            tb = slide.shapes.add_textbox(x + Inches(0.25), Inches(2.15), card_w - Inches(0.5), Inches(1.4))
            tf = tb.text_frame
            tf.word_wrap = True
            ph = tf.paragraphs[0]
            ph.text = f"EVENT {idx + 1}"
            ph.font.bold = True
            ph.font.size = Pt(12)
            ph.font.color.rgb = DesignSystem.COLOR_ACCENT
            pb = tf.add_paragraph()
            pb.text = item[:280]
            pb.font.size = Pt(13)
            pb.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            pb.space_before = Pt(4)
        return []

    @classmethod
    def render_cause_effect(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        """Cause arrow effect chain."""
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Cause & Effect")
        content = spec.elements_data.get("content", "")
        return cls.render_comparison(slide, SlideSpec(
            slide_id=spec.slide_id, chapter_id=spec.chapter_id, title=spec.title,
            subtitle=spec.subtitle, purpose=spec.purpose, source_content_ids=spec.source_content_ids,
            slide_type=spec.slide_type, visual_model="comparison",
            elements_data={"content": content}, speaker_notes=spec.speaker_notes,
        ))

    @classmethod
    def render_chapter_divider(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        ShapeHelper.set_slide_background(slide, DesignSystem.COLOR_BG_HERO)
        tb = slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.3), Inches(3.0))
        tf = tb.text_frame
        tf.word_wrap = True
        pk = tf.paragraphs[0]
        pk.text = (spec.subtitle or "CHAPTER").upper()
        pk.font.size = Pt(14)
        pk.font.bold = True
        pk.font.color.rgb = DesignSystem.COLOR_ACCENT
        pk.font.name = DesignSystem.FONT_BODY
        pt = tf.add_paragraph()
        pt.text = spec.title
        pt.font.size = Pt(36)
        pt.font.bold = True
        pt.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK
        pt.font.name = DesignSystem.FONT_TITLE
        pt.space_before = Pt(8)
        if spec.elements_data.get("detail"):
            pd = tf.add_paragraph()
            pd.text = str(spec.elements_data["detail"])[:300]
            pd.font.size = Pt(16)
            pd.font.color.rgb = DesignSystem.COLOR_TEXT_ON_DARK_MUTED
            pd.space_before = Pt(10)
        return []

    @classmethod
    def render_contents(cls, slide, spec: SlideSpec) -> List[Tuple[int, AnimationType]]:
        ShapeHelper.set_slide_background(slide)
        ShapeHelper.add_header(slide, spec.title, spec.subtitle, "Contents")
        entries = spec.elements_data.get("entries", [])
        top_y = Inches(2.1)
        for idx, entry in enumerate(entries[:8]):
            y = top_y + idx * Inches(0.62)
            tb = slide.shapes.add_textbox(DesignSystem.MARGIN_LEFT + Inches(0.3), y, DesignSystem.CONTENT_WIDTH - Inches(0.6), Inches(0.55))
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = f"{idx + 1}.  {entry}"
            p.font.size = Pt(16)
            p.font.color.rgb = DesignSystem.COLOR_TEXT_PRIMARY
            p.font.name = DesignSystem.FONT_BODY
        return []
