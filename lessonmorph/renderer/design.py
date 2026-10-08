"""Design system tokens and color semantics for classroom-ready presentations."""

from __future__ import annotations
from dataclasses import dataclass
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt


@dataclass(frozen=True)
class DesignSystem:
    # Canvas Dimensions (16:9 Widescreen)
    SLIDE_WIDTH = Inches(13.333)
    SLIDE_HEIGHT = Inches(7.5)

    # Margins and Safe Areas
    MARGIN_LEFT = Inches(0.8)
    MARGIN_TOP = Inches(0.6)
    MARGIN_RIGHT = Inches(0.8)
    MARGIN_BOTTOM = Inches(0.6)
    CONTENT_WIDTH = Inches(11.733)
    CONTENT_HEIGHT = Inches(6.3)

    # Typography
    FONT_TITLE = "Segoe UI"
    FONT_BODY = "Segoe UI"
    FONT_CODE = "Consolas"

    SIZE_HERO_TITLE = Pt(40)
    SIZE_SLIDE_TITLE = Pt(28)
    SIZE_SUBTITLE = Pt(14)
    SIZE_SECTION_BADGE = Pt(11)
    SIZE_HEADING = Pt(22)
    SIZE_BODY = Pt(17)
    SIZE_STEP_NUM = Pt(16)
    SIZE_NOTES = Pt(12)

    # Color Palette - High Contrast Classroom Theme
    COLOR_BG_PAGE = RGBColor(248, 250, 252)        # Slate 50
    COLOR_BG_CARD = RGBColor(255, 255, 255)        # Pure White
    COLOR_BG_HERO = RGBColor(15, 23, 42)           # Slate 900
    COLOR_BORDER_CARD = RGBColor(226, 232, 240)    # Slate 200

    # Text Colors
    COLOR_TEXT_PRIMARY = RGBColor(15, 23, 42)      # Slate 900
    COLOR_TEXT_SECONDARY = RGBColor(71, 85, 105)   # Slate 600
    COLOR_TEXT_MUTED = RGBColor(148, 163, 184)     # Slate 400
    COLOR_TEXT_ON_DARK = RGBColor(255, 255, 255)   # Pure White
    COLOR_TEXT_ON_DARK_MUTED = RGBColor(203, 213, 225) # Slate 300

    # Brand & Semantic Accents
    COLOR_ACCENT = RGBColor(2, 132, 199)           # Sky 600
    COLOR_ACCENT_BG = RGBColor(224, 242, 254)      # Sky 100
    COLOR_ACCENT_BORDER = RGBColor(125, 211, 252)  # Sky 300

    # Success / Verified
    COLOR_SUCCESS = RGBColor(16, 185, 129)         # Emerald 500
    COLOR_SUCCESS_BG = RGBColor(236, 253, 245)     # Emerald 50
    COLOR_SUCCESS_BORDER = RGBColor(110, 231, 183) # Emerald 300

    # Error / Misconception / Warning
    COLOR_DANGER = RGBColor(225, 29, 72)           # Rose 600
    COLOR_DANGER_BG = RGBColor(255, 241, 242)      # Rose 50
    COLOR_DANGER_BORDER = RGBColor(253, 164, 175)  # Rose 300

    # Warning / Note
    COLOR_WARNING = RGBColor(217, 119, 6)          # Amber 600
    COLOR_WARNING_BG = RGBColor(254, 243, 199)     # Amber 100
    COLOR_WARNING_BORDER = RGBColor(252, 211, 77)  # Amber 300
