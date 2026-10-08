"""Helper entry point: compile a document into a classroom PPTX.

Usage:
    python skill/scripts/compile.py <document> [-o output.pptx] [-w work_dir]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lessonmorph.cli import compile_document


def main():
    ap = argparse.ArgumentParser(description="LessonMorph compile helper")
    ap.add_argument("document", help="PDF, DOCX, MD, or TXT source")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("-w", "--work-dir", default=None)
    args = ap.parse_args()
    res = compile_document(args.document, args.output, args.work_dir)
    print(res)


if __name__ == "__main__":
    main()
