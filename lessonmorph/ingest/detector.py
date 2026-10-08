"""Document format detector and unified ingestion loader."""

from __future__ import annotations
from pathlib import Path
from lessonmorph.ingest.base import BaseExtractor, IngestionResult
from lessonmorph.ingest.docx import DocxExtractor
from lessonmorph.ingest.pdf import PdfExtractor
from lessonmorph.ingest.text import TextExtractor


def get_extractor_for_file(file_path: Path | str) -> BaseExtractor:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PdfExtractor()
    elif suffix in (".docx", ".doc"):
        return DocxExtractor()
    elif suffix in (".md", ".markdown", ".txt"):
        return TextExtractor()
    else:
        # Default to text extractor if unknown text-bearing file
        return TextExtractor()


def ingest_document(file_path: Path | str) -> IngestionResult:
    """Detects format and extracts structured content from any supported document."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Source document not found: {p}")
    extractor = get_extractor_for_file(p)
    return extractor.extract(p)
