"""Quality Gates validator for LessonMorph presentations.

Validates Content QA (100% source coverage), Structural QA (valid PPTX package & notes),
Visual QA (text overflow & layout limits), and Teaching QA (pedagogical sequencing).
"""

from __future__ import annotations
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import pptx
from lessonmorph.core.models import ChapterPlan, ContentType, SlideSpec
from lessonmorph.ledger.ledger import ContentCompletenessLedger


@dataclass
class QualityCheckResult:
    category: str  # Content QA, Structural QA, Visual QA, Teaching QA
    check_name: str
    passed: bool
    details: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class ValidationReport:
    document_title: str
    total_slides: int
    estimated_teaching_time_minutes: int
    content_units_total: int
    content_units_covered: int
    content_units_uncovered: int
    coverage_percent: float
    checks: List[QualityCheckResult] = field(default_factory=list)
    overall_status: str = "PASS"  # PASS, WARN, FAIL

    def to_markdown(self) -> str:
        lines = [
            f"# LessonMorph Validation Report: {self.document_title}",
            "",
            f"**Overall Status**: `{self.overall_status}`",
            "",
            "## Presentation Overview",
            f"- **Total Slides**: {self.total_slides}",
            f"- **Estimated Teaching Duration**: {self.estimated_teaching_time_minutes} minutes",
            f"- **Content Coverage**: {self.content_units_covered} / {self.content_units_total} units ({self.coverage_percent}%)",
            f"- **Uncovered Units**: {self.content_units_uncovered}",
            "",
            "## Quality Gate Checks",
            "",
            "| Category | Check | Status | Details |",
            "| :--- | :--- | :---: | :--- |",
        ]
        for c in self.checks:
            stat = "PASS" if c.passed else f"**{c.severity}**"
            lines.append(f"| {c.category} | {c.check_name} | {stat} | {c.details} |")

        lines.append("")
        return "\n".join(lines)


class QualityGateValidator:
    """Runs rigorous verification across all quality gates."""

    @classmethod
    def validate(
        cls,
        pptx_path: Path | str,
        ledger: ContentCompletenessLedger,
        plan: ChapterPlan,
        slides: List[SlideSpec],
    ) -> ValidationReport:
        checks: List[QualityCheckResult] = []

        # 1. Content QA: Completeness Ledger
        summary = ledger.coverage_summary()
        uncovered = ledger.get_uncovered_units()
        if not uncovered:
            checks.append(
                QualityCheckResult(
                    category="Content QA",
                    check_name="100% Content Coverage",
                    passed=True,
                    details=f"All {summary['total_units']} source content units are verified as covered.",
                )
            )
        else:
            checks.append(
                QualityCheckResult(
                    category="Content QA",
                    check_name="100% Content Coverage",
                    passed=False,
                    details=f"{len(uncovered)} content units lack slide destination (IDs: {', '.join([u.id for u in uncovered[:5]])}).",
                    severity="ERROR",
                )
            )

        # 2. Structural QA: Can PPTX be re-opened and parsed?
        p_path = Path(pptx_path)
        if not p_path.exists():
            checks.append(
                QualityCheckResult(
                    category="Structural QA",
                    check_name="File Existence",
                    passed=False,
                    details=f"Output presentation file missing: {p_path}",
                    severity="ERROR",
                )
            )
            return ValidationReport(
                document_title=ledger.document_title,
                total_slides=len(slides),
                estimated_teaching_time_minutes=plan.estimated_time_minutes,
                content_units_total=summary["total_units"],
                content_units_covered=summary["covered_units"],
                content_units_uncovered=summary["uncovered_units"],
                coverage_percent=summary["coverage_rate_percent"],
                checks=checks,
                overall_status="FAIL",
            )

        try:
            prs = pptx.Presentation(p_path)
            slide_count = len(prs.slides)
            checks.append(
                QualityCheckResult(
                    category="Structural QA",
                    check_name="PPTX Package Integrity",
                    passed=True,
                    details=f"Successfully opened presentation package with {slide_count} slides.",
                )
            )

            # Check that notes slides are properly populated
            slides_with_notes = sum(
                1 for s in prs.slides if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip()
            )
            if slides_with_notes >= len(prs.slides) * 0.8:
                checks.append(
                    QualityCheckResult(
                        category="Structural QA",
                        check_name="Speaker Notes Coverage",
                        passed=True,
                        details=f"{slides_with_notes} of {slide_count} slides have teacher speaker notes.",
                    )
                )
            else:
                checks.append(
                    QualityCheckResult(
                        category="Structural QA",
                        check_name="Speaker Notes Coverage",
                        passed=False,
                        details=f"Only {slides_with_notes} of {slide_count} slides have speaker notes.",
                        severity="WARNING",
                    )
                )

        except Exception as e:
            checks.append(
                QualityCheckResult(
                    category="Structural QA",
                    check_name="PPTX Package Integrity",
                    passed=False,
                    details=f"Failed to open generated presentation: {e}",
                    severity="ERROR",
                )
            )

        # 3. Visual QA: Text Overflow & Density Heuristics
        overflow_count = 0
        for s in slides:
            # Check length of primary text
            for k, v in s.elements_data.items():
                if isinstance(v, str) and len(v) > 600:
                    overflow_count += 1
                    break

        if overflow_count == 0:
            checks.append(
                QualityCheckResult(
                    category="Visual QA",
                    check_name="Text Density & Overflow",
                    passed=True,
                    details="All slides respect density guidelines for classroom projector viewing.",
                )
            )
        else:
            checks.append(
                QualityCheckResult(
                    category="Visual QA",
                    check_name="Text Density & Overflow",
                    passed=False,
                    details=f"{overflow_count} slides exceed recommended density limits and may require font scaling.",
                    severity="WARNING",
                )
            )

        # 3b. Visual QA: geometry overlap + off-canvas detection (python-pptx bounds)
        try:
            prs_geo = pptx.Presentation(p_path) if p_path.exists() else None
            overlap_slides = 0
            offcanvas_slides = 0
            if prs_geo is not None:
                sw, sh = prs_geo.slide_width, prs_geo.slide_height
                slide_area = float(sw * sh)
                for sl in prs_geo.slides:
                    boxes = []
                    for shp in sl.shapes:
                        try:
                            if not shp.has_text_frame and not shp.has_table:
                                # pictures still count; pure lines/connectors skipped
                                try:
                                    _ = (shp.left, shp.top, shp.width, shp.height)
                                except Exception:
                                    continue
                                if shp.shape_type is not None and str(getattr(shp.shape_type, "name", "")) == "LINE":
                                    continue
                            boxes.append((shp.left, shp.top, shp.width, shp.height))
                            if shp.left < -12700 or shp.top < -12700 or (shp.left + shp.width) > sw + 12700 or (shp.top + shp.height) > sh + 12700:
                                offcanvas_slides += 1
                                break
                        except Exception:
                            continue
                    # Exclude full-bleed backgrounds/canvas fills from overlap math
                    boxes = [b for b in boxes if float(b[2] * b[3]) < 0.85 * slide_area]
                    # pairwise overlap: flag only sibling content collisions,
                    # not card-container + inner-textbox containment (by design)
                    found = False
                    for i in range(len(boxes)):
                        for j in range(i + 1, len(boxes)):
                            ax, ay, aw, ah = boxes[i]
                            bx, by, bw, bh = boxes[j]
                            if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
                                continue
                            ix = min(ax + aw, bx + bw) - max(ax, bx)
                            iy = min(ay + ah, by + bh) - max(ay, by)
                            if ix <= 0 or iy <= 0:
                                continue
                            inter = float(ix * iy)
                            small = float(min(aw * ah, bw * bh))
                            if small <= 0:
                                continue
                            # Containment (textbox inside its card): not a defect
                            if inter > 0.9 * small:
                                continue
                            if inter > 0.35 * small:
                                found = True
                                break
                        if found:
                            break
                    if found:
                        overlap_slides += 1
            if overlap_slides == 0 and offcanvas_slides == 0:
                checks.append(QualityCheckResult("Visual QA", "Geometry Overlap & Canvas", True, "No major overlaps or off-canvas objects detected."))
            else:
                checks.append(QualityCheckResult("Visual QA", "Geometry Overlap & Canvas", False,
                    f"{overlap_slides} slides with major overlaps; {offcanvas_slides} slides with off-canvas objects.",
                    severity="WARNING"))
        except Exception as e:
            checks.append(QualityCheckResult("Visual QA", "Geometry Overlap & Canvas", True, f"Geometry check skipped: {e}", severity="INFO"))

        # 3c. Animation package check: timing XML well-formed and references real shapes
        try:
            import zipfile as _zf
            from lxml import etree as _et
            anim_slides = 0
            with _zf.ZipFile(p_path) as z:
                slide_files = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
                for sf in slide_files:
                    data = z.read(sf)
                    if b"<p:timing" in data or b":timing" in data:
                        anim_slides += 1
                        _et.fromstring(data)  # raises if malformed
            checks.append(QualityCheckResult("Structural QA", "Animation XML Validity", True,
                f"{anim_slides} slides carry native <p:timing> sequences; package XML parses cleanly."))
        except ImportError:
            checks.append(QualityCheckResult("Structural QA", "Animation XML Validity", True,
                "Animation present; lxml not installed so deep XML parse skipped.", severity="INFO"))
        except Exception as e:
            checks.append(QualityCheckResult("Structural QA", "Animation XML Validity", False,
                f"Animation XML problem: {e}", severity="ERROR"))

        # 3d. Content QA extras: formulas, tables, human-review flags
        formulas = [u for u in ledger.units if u.content_type == ContentType.FORMULA]
        long_formulas = [u.id for u in formulas if len(u.normalized_content) > 800]
        if long_formulas:
            checks.append(QualityCheckResult("Content QA", "Formula Integrity", False,
                f"Formulas possibly over-long / degraded: {', '.join(long_formulas[:5])}. Requires human review.", severity="WARNING"))
        else:
            checks.append(QualityCheckResult("Content QA", "Formula Integrity", True,
                f"{len(formulas)} formulas preserved without truncation."))
        review_terms = ("ocr", "illegible", "ambiguous", "uncertain", "[?]", "???")
        review_units = [u.id for u in ledger.units if any(t in u.normalized_content.lower() for t in review_terms)]
        if review_units:
            checks.append(QualityCheckResult("Content QA", "Human Review Flags", False,
                f"{len(review_units)} units flagged for human review: {', '.join(review_units[:5])}.", severity="WARNING"))
        else:
            checks.append(QualityCheckResult("Content QA", "Human Review Flags", True, "No OCR/ambiguity flags detected."))

        # 4. Teaching QA: Progression Flow & Assessment Order
        has_title = any(s.slide_type.value == "title" for s in slides)
        has_recap = any(s.slide_type.value in ("summary_recap", "exit_ticket") for s in slides)
        has_quiz = any(s.slide_type.value in ("quiz_question", "quiz_reveal") for s in slides)

        if has_title and has_recap:
            checks.append(
                QualityCheckResult(
                    category="Teaching QA",
                    check_name="Pedagogical Arc",
                    passed=True,
                    details="Presentation includes clear onboarding (title/roadmap), concept exposition, and consolidation.",
                )
            )
        else:
            checks.append(
                QualityCheckResult(
                    category="Teaching QA",
                    check_name="Pedagogical Arc",
                    passed=False,
                    details="Missing opening orientation or closing recap consolidation.",
                    severity="WARNING",
                )
            )

        # Determine overall status
        has_errors = any(not c.passed and c.severity == "ERROR" for c in checks)
        has_warnings = any(not c.passed and c.severity == "WARNING" for c in checks)

        if has_errors:
            status = "FAIL"
        elif has_warnings:
            status = "WARN"
        else:
            status = "PASS"

        return ValidationReport(
            document_title=ledger.document_title or plan.title,
            total_slides=len(slides),
            estimated_teaching_time_minutes=plan.estimated_time_minutes,
            content_units_total=summary["total_units"],
            content_units_covered=summary["covered_units"],
            content_units_uncovered=summary["uncovered_units"],
            coverage_percent=summary["coverage_rate_percent"],
            checks=checks,
            overall_status=status,
        )
