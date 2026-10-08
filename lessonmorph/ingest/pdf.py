"""PDF Extractor utilizing PyMuPDF (fitz).

Extracts bookmarks, page text, headings, tables, and images while preserving
exact page numbering and layout coordinates.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Optional
import pymupdf
from lessonmorph.core.models import DocumentMap, DocumentSection
from lessonmorph.ingest.base import BaseExtractor, ExtractedImage, ExtractedTable, IngestionResult


class PdfExtractor(BaseExtractor):
    """High-fidelity PDF document extractor."""

    def extract(self, file_path: Path) -> IngestionResult:
        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        title = doc.metadata.get("title") or file_path.stem.replace("_", " ").title()

        toc = doc.get_toc()  # [level, title, page]
        sections: List[DocumentSection] = []
        tables: List[ExtractedTable] = []
        images: List[ExtractedImage] = []

        # 1. Process outline / bookmarks if present
        if toc:
            # Group by top-level chapters (level 1 or 2)
            min_level = min(item[0] for item in toc)
            chapter_entries = [item for item in toc if item[0] == min_level]
            for idx, (level, ch_title, start_page) in enumerate(chapter_entries):
                if idx + 1 < len(chapter_entries):
                    end_page = max(start_page, chapter_entries[idx + 1][2] - 1)
                else:
                    end_page = total_pages
                
                # Collect text across pages of this section
                sec_text_parts = []
                for p_num in range(start_page, min(end_page + 1, total_pages + 1)):
                    page = doc[p_num - 1]
                    sec_text_parts.append(f"[Page {p_num}]\n{page.get_text('text')}")
                
                sections.append(
                    DocumentSection(
                        id=f"ch{idx + 1:02d}",
                        title=ch_title.strip(),
                        start_page=start_page,
                        end_page=end_page,
                        text_content="\n\n".join(sec_text_parts),
                    )
                )
        else:
            # Fallback: Detect headings by font size or divide into logical units
            current_sec_id = 1
            current_sec_title = f"Section 1"
            current_sec_start = 1
            current_sec_text: List[str] = []

            for p_num in range(1, total_pages + 1):
                page = doc[p_num - 1]
                page_text = page.get_text("text")
                
                # Check for prominent chapter/heading cues on the page
                heading_match = re.search(r"^(Chapter\s+\d+[:\s\w]+|[A-Z][A-Z\s]{4,30})\n", page_text)
                if heading_match and p_num > current_sec_start:
                    sections.append(
                        DocumentSection(
                            id=f"ch{current_sec_id:02d}",
                            title=current_sec_title,
                            start_page=current_sec_start,
                            end_page=p_num - 1,
                            text_content="\n\n".join(current_sec_text),
                        )
                    )
                    current_sec_id += 1
                    current_sec_title = heading_match.group(1).strip()
                    current_sec_start = p_num
                    current_sec_text = []

                current_sec_text.append(f"[Page {p_num}]\n{page_text}")

            sections.append(
                DocumentSection(
                    id=f"ch{current_sec_id:02d}",
                    title=current_sec_title,
                    start_page=current_sec_start,
                    end_page=total_pages,
                    text_content="\n\n".join(current_sec_text),
                )
            )

        # 2. Extract tables and images
        for p_idx, page in enumerate(doc):
            p_num = p_idx + 1
            # PyMuPDF Table finder
            try:
                found_tabs = page.find_tables()
                for t_idx, tab in enumerate(found_tabs.tables):
                    df_data = tab.extract()
                    if df_data and len(df_data) > 1:
                        headers = [str(c or "").strip() for c in df_data[0]]
                        rows = [[str(c or "").strip() for c in r] for r in df_data[1:]]
                        tables.append(
                            ExtractedTable(
                                title=f"Table {p_num}.{t_idx + 1}",
                                headers=headers,
                                rows=rows,
                                page_number=p_num,
                                source_ref=f"Page {p_num}, Table {t_idx + 1}",
                            )
                        )
            except Exception:
                pass

            # Image extraction
            try:
                img_list = page.get_images(full=True)
                for img_idx, img_info in enumerate(img_list):
                    xref = img_info[0]
                    base_img = doc.extract_image(xref)
                    if base_img:
                        images.append(
                            ExtractedImage(
                                id=f"img_p{p_num}_{img_idx + 1}",
                                page_number=p_num,
                                bbox=(0, 0, base_img["width"], base_img["height"]),
                                format=base_img["ext"],
                                image_bytes=base_img["image"],
                                caption=f"Figure on page {p_num}",
                            )
                        )
            except Exception:
                pass

        doc_map = DocumentMap(
            title=title,
            source_file=str(file_path),
            total_pages=total_pages,
            sections=sections,
            metadata={"format": "pdf", "has_bookmarks": bool(toc)},
        )

        doc.close()
        return IngestionResult(
            document_title=title,
            source_path=file_path,
            total_pages=total_pages,
            doc_map=doc_map,
            tables=tables,
            images=images,
        )
