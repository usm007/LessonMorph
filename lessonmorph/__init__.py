"""LessonMorph: Document-to-Teaching-Presentation Compiler.

Turns educational documents into detailed, classroom-ready PowerPoint presentations (.pptx)
with 100% source fidelity, teacher speaker notes, and native OpenXML animations.
"""

from lessonmorph.cli import compile_document
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.renderer.engine import PptxRenderer

__version__ = "1.0.0"
__all__ = ["compile_document", "ContentCompletenessLedger", "PptxRenderer"]
