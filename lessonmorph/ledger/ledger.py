"""Content Completeness Ledger implementation.

Guarantees 100% meaningful coverage of source educational material.
Every content item extracted from the source document receives an immutable ID
and must be mapped to one or more presentation destinations (slides / notes).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from lessonmorph.core.models import ContentImportance, ContentType, ContentUnit


class ContentCompletenessLedger:
    """Manages atomic content units and verifies end-to-end presentation coverage."""

    def __init__(self, document_title: str = ""):
        self.document_title = document_title
        self._units: Dict[str, ContentUnit] = {}
        self._counter: int = 0

    def add_unit(
        self,
        source_location: str,
        chapter_id: str,
        chapter_title: str,
        content_type: ContentType,
        importance: ContentImportance,
        normalized_content: str,
        original_wording: str = "",
        section_title: Optional[str] = None,
        relationships: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContentUnit:
        """Register a new atomic content unit with an auto-incremented ID (e.g. C001)."""
        self._counter += 1
        unit_id = f"C{self._counter:03d}"
        unit = ContentUnit(
            id=unit_id,
            source_location=source_location,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            section_title=section_title,
            content_type=content_type,
            importance=importance,
            normalized_content=normalized_content.strip(),
            original_wording=(original_wording or normalized_content).strip(),
            relationships=relationships or [],
            metadata=metadata or {},
        )
        self._units[unit_id] = unit
        return unit

    def get_unit(self, unit_id: str) -> Optional[ContentUnit]:
        return self._units.get(unit_id)

    @property
    def units(self) -> List[ContentUnit]:
        return list(self._units.values())

    def mark_covered(self, unit_id: str, slide_ref: str) -> bool:
        """Mark a content unit as covered by a specific slide or note."""
        unit = self.get_unit(unit_id)
        if unit:
            unit.mark_covered(slide_ref)
            return True
        return False

    def mark_multiple_covered(self, unit_ids: List[str], slide_ref: str) -> None:
        for uid in unit_ids:
            self.mark_covered(uid, slide_ref)

    def get_covered_units(self) -> List[ContentUnit]:
        return [u for u in self._units.values() if u.covered]

    def get_uncovered_units(self) -> List[ContentUnit]:
        return [u for u in self._units.values() if not u.covered]

    def get_units_by_type(self, ctype: ContentType) -> List[ContentUnit]:
        return [u for u in self._units.values() if u.content_type == ctype]

    def get_units_by_chapter(self, chapter_id: str) -> List[ContentUnit]:
        return [u for u in self._units.values() if u.chapter_id == chapter_id]

    def coverage_summary(self) -> Dict[str, Any]:
        """Calculates detailed metrics across content units and types."""
        total = len(self._units)
        covered = len(self.get_covered_units())
        uncovered = len(self.get_uncovered_units())
        rate = (covered / total * 100.0) if total > 0 else 100.0

        type_breakdown: Dict[str, Dict[str, int]] = {}
        for ctype in ContentType:
            type_units = self.get_units_by_type(ctype)
            if type_units:
                type_total = len(type_units)
                type_covered = sum(1 for u in type_units if u.covered)
                type_breakdown[ctype.value] = {
                    "total": type_total,
                    "covered": type_covered,
                    "uncovered": type_total - type_covered,
                }

        return {
            "document_title": self.document_title,
            "total_units": total,
            "covered_units": covered,
            "uncovered_units": uncovered,
            "coverage_rate_percent": round(rate, 2),
            "is_complete": uncovered == 0 and total > 0,
            "type_breakdown": type_breakdown,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_title": self.document_title,
            "counter": self._counter,
            "summary": self.coverage_summary(),
            "units": [
                {
                    "id": u.id,
                    "source_location": u.source_location,
                    "chapter_id": u.chapter_id,
                    "chapter_title": u.chapter_title,
                    "section_title": u.section_title,
                    "content_type": u.content_type.value,
                    "importance": u.importance.value,
                    "normalized_content": u.normalized_content,
                    "original_wording": u.original_wording,
                    "relationships": u.relationships,
                    "intended_destination": u.intended_destination,
                    "covered": u.covered,
                    "covered_slides": u.covered_slides,
                    "metadata": u.metadata,
                }
                for u in self._units.values()
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_json(self, filepath: Path | str) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")

    def to_markdown(self) -> str:
        """Renders the Content Completeness Ledger as a readable Markdown document."""
        lines = [
            f"# Content Completeness Ledger: {self.document_title or 'Educational Source'}",
            "",
            "## Summary",
            "",
        ]
        s = self.coverage_summary()
        lines.append(f"- **Total Content Units**: {s['total_units']}")
        lines.append(f"- **Covered**: {s['covered_units']}")
        lines.append(f"- **Uncovered**: {s['uncovered_units']}")
        lines.append(f"- **Coverage Rate**: {s['coverage_rate_percent']}%")
        lines.append(f"- **Status**: {'COMPLETE (100% COVERAGE)' if s['is_complete'] else 'INCOMPLETE'}")
        lines.append("")

        lines.append("## Content Breakdown by Type")
        lines.append("")
        lines.append("| Type | Total | Covered | Uncovered |")
        lines.append("| :--- | :---: | :---: | :---: |")
        for ctype, info in s["type_breakdown"].items():
            lines.append(f"| {ctype} | {info['total']} | {info['covered']} | {info['uncovered']} |")
        lines.append("")

        lines.append("## Atomic Content Ledger")
        lines.append("")
        lines.append("| ID | Type | Location | Destination | Covered | Excerpt |")
        lines.append("| :--- | :--- | :--- | :--- | :---: | :--- |")
        for u in self._units.values():
            dest = ", ".join(u.covered_slides) if u.covered_slides else (u.intended_destination or "-")
            status = "Yes" if u.covered else "**NO**"
            excerpt = u.normalized_content.replace("\n", " ")
            if len(excerpt) > 75:
                excerpt = excerpt[:72] + "..."
            lines.append(
                f"| {u.id} | {u.content_type.value} | {u.source_location} | {dest} | {status} | {excerpt} |"
            )
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContentCompletenessLedger:
        ledger = cls(document_title=data.get("document_title", ""))
        ledger._counter = data.get("counter", 0)
        for u_dict in data.get("units", []):
            unit = ContentUnit(
                id=u_dict["id"],
                source_location=u_dict["source_location"],
                chapter_id=u_dict["chapter_id"],
                chapter_title=u_dict["chapter_title"],
                section_title=u_dict.get("section_title"),
                content_type=ContentType(u_dict["content_type"]),
                importance=ContentImportance(u_dict["importance"]),
                normalized_content=u_dict["normalized_content"],
                original_wording=u_dict.get("original_wording", ""),
                relationships=u_dict.get("relationships", []),
                intended_destination=u_dict.get("intended_destination"),
                covered=u_dict.get("covered", False),
                covered_slides=u_dict.get("covered_slides", []),
                metadata=u_dict.get("metadata", {}),
            )
            ledger._units[unit.id] = unit
        return ledger
