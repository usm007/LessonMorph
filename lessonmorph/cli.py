"""Command Line Interface (CLI) and Unified Compiler for LessonMorph.

BROWSER-FIRST pipeline (primary)::

    SOURCE DOCUMENT -> CONTENT UNDERSTANDING -> EXISTING PEDAGOGICAL MODEL
      -> PRESENTATION BLUEPRINT / IR -> VISUAL DIRECTOR -> MOTION DIRECTOR
      -> LESSON RUNTIME MODEL -> BROWSER PRESENTATION -> DESIGN + VISUAL QA

PPTX EXPORT (retained, downstream only)::

    PRESENTATION IR -> PPTX EXPORTER -> .pptx (regression reference)

The exporter reads the same IR. It never influences browser design and
nothing in the browser path imports the PPTX renderer.

Usage:
    python -m lessonmorph.cli compile <document> [--lesson-dir DIR] [--pptx FILE] [--no-pptx]
        [--work-dir DIR] [--level ...] [--grade ...] [--duration-min N] ...
    python -m lessonmorph.cli export-pptx <document> [-o FILE] [-w DIR] ...
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from lessonmorph.blueprint.adapter import BlueprintCompiler
from lessonmorph.blueprint.validators import BlueprintValidator
from lessonmorph.ingest.detector import ingest_document
from lessonmorph.ingest.atomizer import ContentAtomizer
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.planner import PedagogicalPlanner
from lessonmorph.qa.validator import QualityGateValidator
from lessonmorph.renderer.pptx_exporter import export_pptx
from lessonmorph.runtime.lesson_qa import LessonQA
from lessonmorph.runtime.pipeline import compile_lesson_from_ir, write_and_validate_lesson
from lessonmorph.storyboard.engine import StoryboardEngine


def _export_assets(ingest_res, work_path: Path) -> dict:
    """Writes extracted source images to work/assets for embedding + audit trail."""
    assets_dir = work_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict = {}
    warnings: list = []
    for img in ingest_res.images:
        try:
            if not img.image_bytes:
                warnings.append(f"Figure {img.id} on page {img.page_number} has no bytes; preserved as labeled placeholder.")
                continue
            ext = (img.format or "png").lower().replace("jpeg", "jpg")
            if ext not in ("png", "jpg", "jpeg", "gif", "bmp", "tiff"):
                ext = "png"
            dest = assets_dir / f"{img.id}.{ext}"
            dest.write_bytes(img.image_bytes)
            mapping[img.id] = str(dest)
        except Exception as e:
            warnings.append(f"Figure {img.id} on page {img.page_number} could not be embedded: {e}. Preserved as labeled placeholder.")
    (work_path / "asset_manifest.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    if warnings:
        (work_path / "asset_warnings.md").write_text("\n".join(f"- {w}" for w in warnings), encoding="utf-8")
    return {"mapping": mapping, "warnings": warnings}


def _build_ir(input_file: Path | str, work_path: Path, learner_hint: dict | None = None) -> dict:
    """SOURCE -> CONTENT -> PEDAGOGY -> BLUEPRINT IR. Shared by both outputs."""
    src_path = Path(input_file).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"Input file not found: {src_path}")
    work_path.mkdir(parents=True, exist_ok=True)

    ingest_res = ingest_document(src_path)
    (work_path / "document_map.json").write_text(json.dumps({
        "title": ingest_res.doc_map.title,
        "total_pages": ingest_res.total_pages,
        "sections": [{"id": s.id, "title": s.title, "start_page": s.start_page, "end_page": s.end_page}
                      for s in ingest_res.doc_map.sections],
        "tables": len(ingest_res.tables),
        "images": len(ingest_res.images),
    }, indent=2), encoding="utf-8")

    assets = _export_assets(ingest_res, work_path)

    ledger = ContentCompletenessLedger(document_title=ingest_res.document_title)
    ContentAtomizer(ledger).atomize(ingest_res)
    ledger.save_json(work_path / "content_ledger.json")
    (work_path / "content_ledger.md").write_text(ledger.to_markdown(), encoding="utf-8")

    planner = PedagogicalPlanner(ledger, learner_hint=learner_hint)
    chapter_plans = [planner.plan_chapter(sec) for sec in ingest_res.doc_map.sections]
    for p in chapter_plans:
        ped = p.pedagogical_plan
        if ped is None:
            continue
        (work_path / f"pedagogical_plan_{p.id}.json").write_text(
            json.dumps(ped.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        (work_path / f"pedagogical_plan_{p.id}.md").write_text(ped.to_markdown(), encoding="utf-8")

    answer_key = src_path.with_suffix(".answer_key.json")
    blueprints = []
    for p in chapter_plans:
        compiler = BlueprintCompiler(ledger, answer_key_path=answer_key if answer_key.exists() else None)
        bp = compiler.compile(p)
        blueprints.append(bp)
        (work_path / f"blueprint_{p.id}.json").write_text(
            json.dumps(bp.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    from lessonmorph.blueprint.validators import BlueprintReport as _BR
    bp_reports: list[_BR] = [BlueprintValidator.validate(bp) for bp in blueprints]
    for p, rep in zip(chapter_plans, bp_reports):
        (work_path / f"blueprint_qa_{p.id}.md").write_text(rep.to_markdown(), encoding="utf-8")
    fatal = [(p.id, f) for p, rep in zip(chapter_plans, bp_reports) for f in rep.errors()]
    if fatal:
        raise RuntimeError(f"Blueprint QA FAILED with {len(fatal)} error(s); refusing to render.")

    # Debug record: every slide's source refs + pedagogical + representation refs.
    storyboard = []
    for p, bp in zip(chapter_plans, blueprints):
        for s in bp.slides:
            storyboard.append({
                "slide_id": s.id,
                "chapter_id": p.id,
                "title": s.content_title,
                "representation": s.representation,
                "task": s.task,
                "source_refs": list(s.source_ids),
                "objective_ids": list(s.objective_ids),
                "pedagogical_ref": s.pedagogical_ref,
                "representation_reason": s.representation_reason,
                "instructional_state": s.instructional_state,
            })
    (work_path / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "src_path": src_path,
        "ingest_res": ingest_res,
        "assets": assets,
        "ledger": ledger,
        "chapter_plans": chapter_plans,
        "blueprints": blueprints,
        "bp_reports": bp_reports,
    }


def compile_lesson(
    input_file: Path | str,
    lesson_dir: Path | str | None = None,
    work_dir: Path | str | None = None,
    learner_hint: dict | None = None,
) -> dict:
    """PRIMARY path: IR -> Visual/Motion directors -> Lesson Runtime -> browser bundle."""
    src_path = Path(input_file).resolve()
    doc_stem = src_path.stem
    work_path = Path(work_dir) if work_dir else Path("work") / doc_stem
    lesson_path = Path(lesson_dir) if lesson_dir else Path("output") / f"{doc_stem}_lesson"

    print(f"\n[LessonMorph] Browser-first compilation for: {src_path.name}")
    print("[1/4] Building Presentation IR...")
    ir = _build_ir(src_path, work_path, learner_hint)
    print(f"      Chapters: {len(ir['chapter_plans'])}, Blueprint slides: {sum(len(b.slides) for b in ir['blueprints'])}")

    print("[2/4] Directing scenes (Visual + Motion)...")
    bp_slide_dicts: list = []
    for bp in ir["blueprints"]:
        bp_slide_dicts.extend(bp.to_dict().get("slides", []))
    # Storyboard notes feed teacher metadata + animation purposes only.
    from lessonmorph.blueprint.composer import SlideComposer
    composer = SlideComposer()
    storyboard_notes: list = []
    for p, bp in zip(ir["chapter_plans"], ir["blueprints"]):
        for s in composer.compose_all(bp.slides, p.id):
            storyboard_notes.append({
                "notes": s.speaker_notes.render_markdown(),
                "animation_purposes": [getattr(a, "purpose", "") for a in (s.animation_steps or [])],
            })
    lesson, teachers = compile_lesson_from_ir(
        bp_slide_dicts, storyboard_notes, ir["assets"]["mapping"],
        lesson_id=doc_stem, title=ir["ingest_res"].document_title)

    print("[3/4] Writing offline browser bundle...")
    lang = (learner_hint or {}).get("language", "") or "en"
    manifest, lesson_report = write_and_validate_lesson(
        lesson_path, lesson, teachers, ir["assets"]["mapping"], lang=lang)
    print(f"      Scenes: {len(lesson.scenes)}, Bundle: {lesson_path}/index.html")

    print("[4/4] Lesson QA + static visual QA...")
    (work_path / "lesson_qa.md").write_text(lesson_report.to_markdown(), encoding="utf-8")
    print(f"      LESSON QA: {lesson_report.status}")
    from lessonmorph.qa.visual import StaticVisualQA
    visual_report = StaticVisualQA.analyze(lesson_path)
    (work_path / "visual_qa_static.md").write_text(visual_report.to_markdown(), encoding="utf-8")
    print(f"      STATIC VISUAL QA: {visual_report.status}")
    if visual_report.status == "FAIL":
        raise RuntimeError("Static visual QA FAILED — refusing delivery. See work/visual_qa_static.md.")
    print("\n" + "=" * 60)
    print(f"  LESSON STATUS: {lesson_report.status}")
    print(f"  SCENES: {len(lesson.scenes)} | BUNDLE: {lesson_path}")
    print("=" * 60 + "\n")
    return {
        "status": lesson_report.status,
        "lesson_dir": str(lesson_path),
        "index_html": str(Path(lesson_path) / "index.html"),
        "scenes_count": len(lesson.scenes),
        "chapters_count": len(ir["chapter_plans"]),
        "work_dir": str(work_path),
        "ir": ir,
    }


def compile_document(
    input_file: Path | str,
    output_file: Path | str | None = None,
    work_dir: Path | str | None = None,
    learner_hint: dict | None = None,
    lesson_dir: Path | str | None = None,
    build_pptx: bool = True,
    build_lesson: bool = True,
) -> dict:
    """Backward-compatible entry: browser bundle (primary) + PPTX exporter (regression).

    Existing callers (incl. tests) pass output_file/work_dir and still receive
    pptx_path/status. New callers should prefer compile_lesson().
    """
    src_path = Path(input_file).resolve()
    doc_stem = src_path.stem
    work_path = Path(work_dir) if work_dir else Path("work") / doc_stem
    out_path = Path(output_file) if output_file else Path("output") / f"{doc_stem}.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lesson_path = Path(lesson_dir) if lesson_dir else Path("output") / f"{doc_stem}_lesson"

    print(f"\n[LessonMorph] Starting compilation for: {src_path.name}")
    print(f"[LessonMorph] Work directory: {work_path}")
    print(f"[LessonMorph] Primary output (browser): {lesson_path}")
    print(f"[LessonMorph] Exporter output (PPTX regression): {out_path}")

    ir = _build_ir(src_path, work_path, learner_hint)
    ledger, chapter_plans, blueprints = ir["ledger"], ir["chapter_plans"], ir["blueprints"]
    print(f"      Chapters: {len(chapter_plans)}, Blueprint slides: {sum(len(b.slides) for b in blueprints)}")

    lesson_status, scenes_count = "SKIPPED", 0
    if build_lesson:
        from lessonmorph.blueprint.composer import SlideComposer
        composer = SlideComposer()
        bp_slide_dicts: list = []
        for bp in blueprints:
            bp_slide_dicts.extend(bp.to_dict().get("slides", []))
        storyboard_notes: list = []
        for p, bp in zip(chapter_plans, blueprints):
            for s in composer.compose_all(bp.slides, p.id):
                storyboard_notes.append({
                    "notes": s.speaker_notes.render_markdown(),
                    "animation_purposes": [getattr(a, "purpose", "") for a in (s.animation_steps or [])],
                })
        lesson, teachers = compile_lesson_from_ir(
            bp_slide_dicts, storyboard_notes, ir["assets"]["mapping"],
            lesson_id=doc_stem, title=ir["ingest_res"].document_title)
        manifest, lesson_report = write_and_validate_lesson(
            lesson_path, lesson, teachers, ir["assets"]["mapping"],
            lang=(learner_hint or {}).get("language", "") or "en")
        (work_path / "lesson_qa.md").write_text(lesson_report.to_markdown(), encoding="utf-8")
        from lessonmorph.qa.visual import StaticVisualQA
        visual_report = StaticVisualQA.analyze(lesson_path)
        (work_path / "visual_qa_static.md").write_text(visual_report.to_markdown(), encoding="utf-8")
        print(f"      Static visual QA: {visual_report.status}")
        if visual_report.status == "FAIL":
            raise RuntimeError("Static visual QA FAILED — refusing delivery.")
        lesson_status, scenes_count = lesson_report.status, len(lesson.scenes)
        print(f"      Browser bundle: {lesson_path}/index.html ({scenes_count} scenes, QA {lesson_status})")

    pptx_status, slides_count = "SKIPPED", 0
    render_report, repair_notes = None, []
    if build_pptx:
        sb_engine = StoryboardEngine(ledger)
        exp = export_pptx(blueprints, chapter_plans, ledger, ir["assets"], work_path, out_path, sb_engine)
        slides = exp["slides"]
        render_report, repair_notes = exp["render_report"], exp["repair_notes"]
        print(f"      PPTX exporter: {out_path} ({len(slides)} slides, RenderQA {render_report.status})")
        total_time = sum(p.estimated_time_minutes for p in chapter_plans)
        primary_plan = chapter_plans[0]
        primary_plan.estimated_time_minutes = total_time
        report = QualityGateValidator.validate(out_path, ledger, primary_plan, slides)
        pptx_status, slides_count = report.overall_status, len(slides)
        extra = []
        if ir["assets"]["warnings"]:
            extra.append("\n## Asset / Extraction Warnings\n")
            extra.extend(f"- {w}\n" for w in ir["assets"]["warnings"])
        md = report.to_markdown() + ("".join(extra) if extra else "")
        md += "\n" + "\n\n".join(rep.to_markdown() for rep in ir["bp_reports"]) + "\n"
        md += "\n" + render_report.to_markdown() + "\n"
        if repair_notes:
            md += "\n## Repair Log\n" + "\n".join(f"- {n}" for n in repair_notes) + "\n"
        md += "\n" + LessonQA.validate(lesson_path).to_markdown() + "\n" if build_lesson else ""
        (work_path / "validation_report.md").write_text(md, encoding="utf-8")
        print("\n" + "=" * 60)
        print(f"  LESSON STATUS: {lesson_status} | PPTX (exporter): {pptx_status}")
        print("=" * 60 + "\n")
        return {
            "status": pptx_status,
            "pptx_path": str(out_path),
            "slides_count": slides_count,
            "chapters_count": len(chapter_plans),
            "total_units": report.content_units_total,
            "covered_units": report.content_units_covered,
            "uncovered_units": report.content_units_uncovered,
            "validation_report": str(work_path / "validation_report.md"),
            "lesson_status": lesson_status,
            "lesson_dir": str(lesson_path),
            "scenes_count": scenes_count,
        }

    return {
        "status": lesson_status,
        "lesson_status": lesson_status,
        "lesson_dir": str(lesson_path),
        "scenes_count": scenes_count,
        "chapters_count": len(chapter_plans),
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="lessonmorph",
        description="LessonMorph: browser-first lesson compiler (PPTX exporter retained).",
    )
    subparsers = parser.add_subparsers(dest="command")

    c = subparsers.add_parser("compile", help="Compile a document into a browser lesson (+ PPTX exporter).")
    c.add_argument("document", type=str, help="Path to educational document (PDF, DOCX, MD).")
    c.add_argument("--lesson-dir", type=str, default=None, help="Browser bundle directory (primary output).")
    c.add_argument("-o", "--output", type=str, default=None, help="Exporter .pptx path (regression reference).")
    c.add_argument("--pptx", type=str, default=None, help="Alias for --output.")
    c.add_argument("--no-pptx", action="store_true", help="Skip the PPTX exporter; browser bundle only.")
    c.add_argument("-w", "--work-dir", type=str, default=None, help="Working directory for artifacts.")
    for name, default, help_text in [
        ("--level", "", "Learner level."),
        ("--grade", "", "Class/grade."),
        ("--curriculum", "", "Curriculum/board."),
        ("--language", "", "Language of instruction."),
    ]:
        c.add_argument(name, type=str, default=default, help=help_text)
    c.add_argument("--duration-min", type=int, default=45, help="Lesson duration in minutes.")
    c.add_argument("--shots", action="store_true",
                   help="Run rendered screenshot QA after the build (slower; required before release).")

    e = subparsers.add_parser("export-pptx", help="PPTX exporter only (IR -> .pptx, regression reference).")
    e.add_argument("document", type=str, help="Path to educational document (PDF, DOCX, MD).")
    e.add_argument("-o", "--output", type=str, default=None, help="Output .pptx path.")
    e.add_argument("-w", "--work-dir", type=str, default=None, help="Working directory for artifacts.")

    v = subparsers.add_parser("visual-qa", help="Visual quality gate on a browser lesson (static + screenshots + repair).")
    v.add_argument("lesson_dir", type=str, help="Browser bundle directory.")
    v.add_argument("-w", "--work-dir", type=str, default=None, help="Working directory for the report + shots.")
    v.add_argument("--no-shots", action="store_true", help="Static QA only.")
    v.add_argument("--no-repair", action="store_true", help="Report only; do not repair.")

    args = parser.parse_args()
    if args.command == "compile":
        try:
            hint = {k: v for k, v in {
                "level": getattr(args, "level", ""), "grade": getattr(args, "grade", ""),
                "lesson_duration_minutes": getattr(args, "duration_min", 45),
                "curriculum": getattr(args, "curriculum", ""), "language": getattr(args, "language", ""),
            }.items() if v}
            pptx_path = getattr(args, "pptx", None) or getattr(args, "output", None)
            res = compile_document(args.document, pptx_path, getattr(args, "work_dir", None),
                             learner_hint=hint or None, lesson_dir=getattr(args, "lesson_dir", None),
                             build_pptx=not getattr(args, "no_pptx", False))
            if getattr(args, "shots", False):
                from lessonmorph.qa.visual_gate import run_visual_qa
                work = getattr(args, "work_dir", None) or str(Path(res["lesson_dir"]).parent / "work")
                run_visual_qa(res["lesson_dir"], work)
        except Exception as ex:
            print(f"[LessonMorph Error] {ex}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "visual-qa":
        try:
            from lessonmorph.qa.visual_gate import run_visual_qa
            lesson_dir = args.lesson_dir
            work = getattr(args, "work_dir", None) or "work/visual_qa"
            gate = run_visual_qa(lesson_dir, work,
                                 shots=not getattr(args, "no_shots", False),
                                 repair=not getattr(args, "no_repair", False))
            print(f"[LessonMorph] Visual QA: {gate.status}")
        except Exception as ex:
            print(f"[LessonMorph Error] {ex}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "export-pptx":
        try:
            compile_document(args.document, getattr(args, "output", None),
                             getattr(args, "work_dir", None), build_lesson=False, build_pptx=True)
        except Exception as ex:
            print(f"[LessonMorph Error] {ex}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
