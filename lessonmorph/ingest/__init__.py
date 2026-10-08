"""Ingestion package for LessonMorph."""
from lessonmorph.ingest.atomizer import ContentAtomizer
from lessonmorph.ingest.base import BaseExtractor, ExtractedImage, ExtractedTable, IngestionResult
from lessonmorph.ingest.detector import get_extractor_for_file, ingest_document
from lessonmorph.ingest.docx import DocxExtractor
from lessonmorph.ingest.pdf import PdfExtractor
from lessonmorph.ingest.text import TextExtractor

__all__ = [
    "BaseExtractor",
    "ExtractedImage",
    "ExtractedTable",
    "IngestionResult",
    "get_extractor_for_file",
    "ingest_document",
    "PdfExtractor",
    "DocxExtractor",
    "TextExtractor",
    "ContentAtomizer",
]
