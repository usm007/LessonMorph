"""Helper entry point: compile a document into a browser-first lesson.

Usage:
    python skill/scripts/compile.py <document> [--lesson-dir DIR] [--no-pptx] [--pptx FILE] [-w DIR]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lessonmorph.cli import compile_document


def main():
    ap = argparse.ArgumentParser(description="LessonMorph compile helper (browser-first)")
    ap.add_argument("document", help="PDF, DOCX, MD, or TXT source")
    ap.add_argument("--lesson-dir", default=None, help="Browser bundle directory (primary output)")
    ap.add_argument("--pptx", default=None, help="Exporter .pptx path (regression reference)")
    ap.add_argument("-o", "--output", default=None, help="Alias for --pptx")
    ap.add_argument("--no-pptx", action="store_true", help="Browser bundle only")
    ap.add_argument("-w", "--work-dir", default=None)
    args = ap.parse_args()
    res = compile_document(args.document, args.output or args.pptx, args.work_dir,
                           lesson_dir=args.lesson_dir, build_pptx=not args.no_pptx)
    print({k: v for k, v in res.items() if k != "ir"})


if __name__ == "__main__":
    main()
