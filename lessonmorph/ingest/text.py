"""Markdown and plain text document extractor."""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Optional
from lessonmorph.core.models import DocumentMap, DocumentSection
from lessonmorph.ingest.base import BaseExtractor, ExtractedImage, ExtractedTable, IngestionResult


class TextExtractor(BaseExtractor):
    """Extractor for Markdown (.md) and plain text (.txt) files."""

    def extract(self, file_path: Path) -> IngestionResult:
        content = file_path.read_text(encoding="utf-8")
        title = file_path.stem.replace("_", " ").title()

        # Parse markdown tables
        tables: List[ExtractedTable] = []
        table_matches = re.finditer(
            r"((?:\|[^\n]+\|\r?\n)(?:\|[-: |]+\|\r?\n)(?:\|[^\n]+\|\r?\n?)+)",
            content,
        )
        for t_idx, match in enumerate(table_matches):
            raw_table = match.group(0).strip().splitlines()
            if len(raw_table) >= 3:
                header_line = raw_table[0]
                headers = [c.strip() for c in header_line.split("|")[1:-1]]
                row_lines = raw_table[2:]
                rows = []
                for r in row_lines:
                    cols = [c.strip() for c in r.split("|")[1:-1]]
                    if cols:
                        rows.append(cols)
                tables.append(
                    ExtractedTable(
                        title=f"Table {t_idx + 1}",
                        headers=headers,
                        rows=rows,
                        page_number=1,
                        source_ref=f"Markdown Table {t_idx + 1}",
                    )
                )

        # Split sections by Heading 1 or Heading 2
        heading_matches = list(re.finditer(r"^(#{1,2})\s+(.+)$", content, re.MULTILINE))
        sections: List[DocumentSection] = []

        if heading_matches:
            # First check if H1 is the document title
            first_h1 = next((m for m in heading_matches if m.group(1) == "#"), None)
            if first_h1:
                title = first_h1.group(2).strip()

            # Chapter splits: use H1 or H2
            split_level = "#" if sum(1 for m in heading_matches if m.group(1) == "#") > 1 else "##"
            split_points = [m for m in heading_matches if m.group(1) == split_level]
            if not split_points:
                split_points = heading_matches

            for idx, m in enumerate(split_points):
                sec_title = m.group(2).strip()
                start_pos = m.end()
                end_pos = split_points[idx + 1].start() if idx + 1 < len(split_points) else len(content)
                sec_body = content[start_pos:end_pos].strip()
                sections.append(
                    DocumentSection(
                        id=f"ch{idx + 1:02d}",
                        title=sec_title,
                        start_page=idx + 1,
                        end_page=idx + 1,
                        text_content=sec_body,
                    )
                )
        else:
            # No headings, treat as single chapter
            sections.append(
                DocumentSection(
                    id="ch01",
                    title=title,
                    start_page=1,
                    end_page=1,
                    text_content=content.strip(),
                )
            )

        doc_map = DocumentMap(
            title=title,
            source_file=str(file_path),
            total_pages=len(sections),
            sections=sections,
            metadata={"format": "markdown"},
        )

        return IngestionResult(
            document_title=title,
            source_path=file_path,
            total_pages=len(sections),
            doc_map=doc_map,
            tables=tables,
            images=[],
        )
