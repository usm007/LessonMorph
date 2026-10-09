"""Base ingestion interface and data structures."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from lessonmorph.core.models import DocumentMap, DocumentSection


@dataclass
class ExtractedTable:
    title: Optional[str]
    headers: List[str]
    rows: List[List[str]]
    page_number: int
    source_ref: str
    section_context: str = ""  # nearest preceding heading (for scene titles)


@dataclass
class ExtractedImage:
    id: str
    page_number: int
    bbox: tuple[float, float, float, float]
    format: str
    image_bytes: Optional[bytes] = None
    caption: Optional[str] = None


@dataclass
class IngestionResult:
    document_title: str
    source_path: Path
    total_pages: int
    doc_map: DocumentMap
    tables: List[ExtractedTable] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseExtractor(ABC):
    """Abstract base class for document extractors."""

    @abstractmethod
    def extract(self, file_path: Path) -> IngestionResult:
        """Extract structured content from the source document."""
        pass
