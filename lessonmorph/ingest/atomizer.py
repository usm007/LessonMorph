"""Content Atomizer: converts raw ingested text, tables, and figures into atomic ContentUnits.

Guarantees 100% source fidelity by decomposing educational text into definitions,
explanations, formulas, worked examples, misconceptions, exercises, and tables.
"""

from __future__ import annotations
import re
from typing import List, Optional, Tuple
from lessonmorph.core.models import ContentImportance, ContentType, ContentUnit
from lessonmorph.core.text_refs import is_heading_block, split_heading, strip_markup_line
from lessonmorph.ingest.base import IngestionResult
from lessonmorph.ledger.ledger import ContentCompletenessLedger


class ContentAtomizer:
    """Decomposes structured ingestion results into atomic ContentUnits in a ContentCompletenessLedger."""

    def __init__(self, ledger: ContentCompletenessLedger):
        self.ledger = ledger

    def atomize(self, ingest_res: IngestionResult) -> ContentCompletenessLedger:
        """Process sections, tables, and images into content atoms."""
        self.ledger.document_title = ingest_res.document_title

        # 1. Process document sections
        for sec in ingest_res.doc_map.sections:
            self._atomize_section(sec.id, sec.title, sec.start_page, sec.text_content)

        # 2. Process extracted tables
        for tab in ingest_res.tables:
            table_content = f"Headers: {', '.join(tab.headers)}\nRows:\n" + "\n".join(
                [f" - {', '.join(r)}" for r in tab.rows]
            )
            self.ledger.add_unit(
                source_location=tab.source_ref,
                chapter_id="ch01" if not ingest_res.doc_map.sections else ingest_res.doc_map.sections[0].id,
                chapter_title=ingest_res.doc_map.sections[0].title if ingest_res.doc_map.sections else "General",
                section_title=tab.section_context or None,
                content_type=ContentType.TABLE,
                importance=ContentImportance.CORE,
                normalized_content=table_content,
                original_wording=table_content,
                metadata={"headers": tab.headers, "rows": tab.rows, "title": tab.title},
            )

        # 3. Process extracted images / figures
        for img in ingest_res.images:
            self.ledger.add_unit(
                source_location=f"Page {img.page_number}, Figure {img.id}",
                chapter_id="ch01" if not ingest_res.doc_map.sections else ingest_res.doc_map.sections[0].id,
                chapter_title=ingest_res.doc_map.sections[0].title if ingest_res.doc_map.sections else "General",
                content_type=ContentType.DIAGRAM,
                importance=ContentImportance.CORE,
                normalized_content=img.caption or f"Diagram on page {img.page_number}",
                metadata={"image_id": img.id, "format": img.format, "bbox": img.bbox},
            )

        return self.ledger

    def _atomize_section(self, ch_id: str, ch_title: str, start_page: int, text: str) -> None:
        """Decomposes section text into atomic content units."""
        if not text or not text.strip():
            return

        # Split text into paragraphs or thematic blocks
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        current_subsection: Optional[str] = None

        for b_idx, block in enumerate(blocks):
            loc_ref = f"Page {start_page}, Section {ch_title}, Block {b_idx + 1}"

            # Leading markdown heading belongs to structure: record it as a
            # HEADING unit (kicker/title material) and atomize the remainder.
            heading, rest = split_heading(block)
            if heading:
                current_subsection = heading
                self.ledger.add_unit(
                    source_location=f"{loc_ref}, Heading",
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=heading,
                    content_type=ContentType.HEADING,
                    importance=ContentImportance.SUPPORTING,
                    normalized_content=heading,
                    original_wording=heading,
                )
                if not rest.strip():
                    continue
                block = rest.strip()
                loc_ref = f"{loc_ref}, Body"
            elif is_heading_block(block):
                # Bare heading block: structure, never an exercise/question.
                heading_text = strip_markup_line(block)
                current_subsection = heading_text
                self.ledger.add_unit(
                    source_location=f"{loc_ref}, Heading",
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=heading_text,
                    content_type=ContentType.HEADING,
                    importance=ContentImportance.SUPPORTING,
                    normalized_content=heading_text,
                    original_wording=block,
                )
                continue

            section = current_subsection

            # Check if block contains explicit worked examples
            if re.search(r"\b(?:Example|Worked Example|Problem)\b[:\s]", block, re.IGNORECASE):
                self._atomize_worked_example(ch_id, ch_title, section, loc_ref, block)
                continue

            # Check for misconceptions / common mistakes
            if re.search(r"\b(?:Misconception|Common Mistake|Pitfall|Watch Out|Warning)\b[:\s]", block, re.IGNORECASE):
                self.ledger.add_unit(
                    source_location=loc_ref,
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=section,
                    content_type=ContentType.MISCONCEPTION,
                    importance=ContentImportance.CORE,
                    normalized_content=block,
                    original_wording=block,
                )
                continue

            # Check for exercises / practice questions
            if re.search(r"\b(?:Exercise|Question|Practice|Check for Understanding)\b[:\s]", block, re.IGNORECASE):
                self.ledger.add_unit(
                    source_location=loc_ref,
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=section,
                    content_type=ContentType.EXERCISE,
                    importance=ContentImportance.CORE,
                    normalized_content=block,
                    original_wording=block,
                )
                continue

            # Check for definitions
            if re.search(r"\b(?:Definition|is defined as|refers to|means that)\b", block, re.IGNORECASE) or (
                block.startswith("**") and "**:" in block[:50]
            ):
                self.ledger.add_unit(
                    source_location=loc_ref,
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=section,
                    content_type=ContentType.DEFINITION,
                    importance=ContentImportance.CORE,
                    normalized_content=block,
                    original_wording=block,
                )
                continue

            # Check for formulas / equations
            if re.search(r"(?:\$\$|\\\[|\\\(|[a-zA-Z]\s*=\s*[\w\d\+\-\*\/\^\(\)]+)", block):
                self.ledger.add_unit(
                    source_location=loc_ref,
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=section,
                    content_type=ContentType.FORMULA,
                    importance=ContentImportance.CORE,
                    normalized_content=block,
                    original_wording=block,
                )
                continue

            # Check for bulleted lists or sub-steps
            if block.startswith(("- ", "* ", "1. ", "2. ")):
                items = [item.strip() for item in block.splitlines() if item.strip()]
                # If short list, group or register individually
                for item_idx, item in enumerate(items):
                    clean_item = re.sub(r"^[-*\d\.]+\s*", "", item)
                    self.ledger.add_unit(
                        source_location=f"{loc_ref}, Item {item_idx + 1}",
                        chapter_id=ch_id,
                        chapter_title=ch_title,
                        section_title=section,
                        content_type=ContentType.EXPLANATION,
                        importance=ContentImportance.CORE,
                        normalized_content=clean_item,
                        original_wording=item,
                    )
                continue

            # Default: standard explanation or context
            self.ledger.add_unit(
                source_location=loc_ref,
                chapter_id=ch_id,
                chapter_title=ch_title,
                section_title=section,
                content_type=ContentType.EXPLANATION,
                importance=ContentImportance.CORE if len(block) > 40 else ContentImportance.SUPPORTING,
                normalized_content=block,
                original_wording=block,
            )

    def _atomize_worked_example(self, ch_id: str, ch_title: str, section: Optional[str],
                                loc_ref: str, block: str) -> None:
        """Splits worked example into problem prompt and individual calculation / logical steps."""
        step_pattern = re.compile(r"(Step\s+\d+[:\.]?|First,|Second,|Then,|Finally,)", re.IGNORECASE)
        parts = step_pattern.split(block)

        if len(parts) > 1:
            # First part is problem statement
            prompt = parts[0].strip()
            self.ledger.add_unit(
                source_location=f"{loc_ref}, Problem",
                chapter_id=ch_id,
                chapter_title=ch_title,
                section_title=section,
                content_type=ContentType.EXAMPLE,
                importance=ContentImportance.CORE,
                normalized_content=prompt,
                original_wording=prompt,
            )
            # Subsequent parts are steps
            for i in range(1, len(parts), 2):
                step_header = parts[i].strip()
                step_body = parts[i + 1].strip() if i + 1 < len(parts) else ""
                full_step = f"{step_header} {step_body}".strip()
                self.ledger.add_unit(
                    source_location=f"{loc_ref}, {step_header}",
                    chapter_id=ch_id,
                    chapter_title=ch_title,
                    section_title=section,
                    content_type=ContentType.WORKED_STEP,
                    importance=ContentImportance.CORE,
                    normalized_content=full_step,
                    original_wording=full_step,
                )
        else:
            self.ledger.add_unit(
                source_location=loc_ref,
                chapter_id=ch_id,
                chapter_title=ch_title,
                section_title=section,
                content_type=ContentType.EXAMPLE,
                importance=ContentImportance.CORE,
                normalized_content=block,
                original_wording=block,
            )
