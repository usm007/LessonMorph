"""Command Line Interface (CLI) and Unified Compiler for LessonMorph.

Usage:
    python -m lessonmorph.cli compile <document_path> [--output <pptx_path>] [--work-dir <work_dir>]
        [--level high_school] [--grade "Grade 10"] [--duration-min 45] [--curriculum CBSE]

Pipeline:
    SOURCE DOCUMENT -> CONTENT UNDERSTANDING -> EXISTING PEDAGOGICAL MODEL
      -> PRESENTATION BLUEPRINT / IR -> (Blueprint QA) -> SLIDE COMPOSER
      -> VISUAL COMPOSER -> PPTX GENERATOR -> RENDERED SLIDES
      -> VISUAL + CONTENT QA -> REPAIR / REGENERATE -> FINAL PPTX

The pedagogical model is the brain, the Blueprint is the execution plan,
the renderer is the executor. The renderer never reinterprets pedagogy.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from lessonmorph.blueprint.adapter import BlueprintCompiler
from lessonmorph.blueprint.composer import SlideComposer
from lessonmorph.blueprint.render_qa import RenderQA
from lessonmorph.blueprint.repair import repair_blueprint
from lessonmorph.blueprint.validators import BlueprintValidator
from lessonmorph.ingest.detector import ingest_document
from lessonmorph.ingest.atomizer import ContentAtomizer
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.planner import PedagogicalPlanner
from lessonmorph.qa.validator import QualityGateValidator
from lessonmorph.renderer.engine import PptxRenderer
from lessonmorph.storyboard.engine import StoryboardEngine


def _export_assets(ingest_res, work_path: Path) -> dict:
    """Writes extracted source images to work/assets for embedding + audit trail.

    Returns mapping image_id -> saved file path. Never fails the build;
    records warnings for the validation report instead.
    """
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


def compile_document(
    input_file: Path | str,
    output_file: Path | str | None = None,
    work_dir: Path | str | None = None,
    learner_hint: dict | None = None,
) -> dict:
    """Executes the complete document-to-teaching-presentation compilation pipeline."""
    src_path = Path(input_file).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"Input file not found: {src_path}")

    doc_stem = src_path.stem
    work_path = Path(work_dir) if work_dir else Path("work") / doc_stem
    work_path.mkdir(parents=True, exist_ok=True)

    out_path = Path(output_file) if output_file else Path("output") / f"{doc_stem}.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[LessonMorph] Starting compilation for: {src_path.name}")
    print(f"[LessonMorph] Work directory: {work_path}")
    print(f"[LessonMorph] Target output: {out_path}")

    # 1. Ingestion (MAP)
    print("[1/7] Ingesting source document...")
    ingest_res = ingest_document(src_path)
    print(f"      Document Title: '{ingest_res.document_title}', Sections: {len(ingest_res.doc_map.sections)}, Pages: {ingest_res.total_pages}")
    (work_path / "document_map.json").write_text(
        json.dumps({
            "title": ingest_res.doc_map.title,
            "total_pages": ingest_res.total_pages,
            "sections": [{"id": s.id, "title": s.title, "start_page": s.start_page, "end_page": s.end_page} for s in ingest_res.doc_map.sections],
            "tables": len(ingest_res.tables),
            "images": len(ingest_res.images),
        }, indent=2), encoding="utf-8")

    # Asset pipeline (source visuals preserved, never silently dropped)
    assets = _export_assets(ingest_res, work_path)
    if assets["warnings"]:
        print(f"      Asset warnings: {len(assets['warnings'])} (see work/asset_warnings.md)")

    # 2. Content Atomization & Ledger Construction (PRESERVE)
    print("[2/7] Atomizing content and constructing Completeness Ledger...")
    ledger = ContentCompletenessLedger(document_title=ingest_res.document_title)
    atomizer = ContentAtomizer(ledger)
    atomizer.atomize(ingest_res)
    ledger_summary = ledger.coverage_summary()
    print(f"      Extracted {ledger_summary['total_units']} atomic content units.")

    ledger.save_json(work_path / "content_ledger.json")
    (work_path / "content_ledger.md").write_text(ledger.to_markdown(), encoding="utf-8")

    # 3. Pedagogical Planning (PEDAGOGICALLY PLAN) — every chapter, not just the first
    print("[3/7] Pedagogically planning (objectives -> strategy -> sequence)...")
    planner = PedagogicalPlanner(ledger, learner_hint=learner_hint)
    chapter_plans = [planner.plan_chapter(sec) for sec in ingest_res.doc_map.sections]
    domains = {p.subject_domain.value for p in chapter_plans}
    print(f"      Chapters: {len(chapter_plans)}, Domains: {sorted(domains)}")

    # Inspectable plan of record: content -> pedagogy -> storyboard.
    for p in chapter_plans:
        ped = p.pedagogical_plan
        if ped is None:
            continue
        (work_path / f"pedagogical_plan_{p.id}.json").write_text(
            json.dumps(ped.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        (work_path / f"pedagogical_plan_{p.id}.md").write_text(
            ped.to_markdown(), encoding="utf-8")
    print("      Pedagogical plan(s) written — inspect before rendering.")

    # 4. Presentation Blueprint + Blueprint QA (execution plan, validated pre-render)
    print("[4/7] Compiling pedagogical plan -> Presentation Blueprint...")
    answer_key = src_path.with_suffix(".answer_key.json")
    blueprints = []
    for p in chapter_plans:
        compiler = BlueprintCompiler(
            ledger, answer_key_path=answer_key if answer_key.exists() else None)
        bp = compiler.compile(p)
        blueprints.append(bp)
        (work_path / f"blueprint_{p.id}.json").write_text(
            json.dumps(bp.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    from lessonmorph.blueprint.validators import BlueprintReport as _BR
    bp_reports: list[_BR] = [BlueprintValidator.validate(bp) for bp in blueprints]
    for p, rep in zip(chapter_plans, bp_reports):
        print(f"      Blueprint {p.id}: {rep.status} "
              f"({len(rep.errors())} errors, {len(rep.findings)} findings)")
        (work_path / f"blueprint_qa_{p.id}.md").write_text(
            rep.to_markdown(), encoding="utf-8")
    fatal = [(p.id, f) for p, rep in zip(chapter_plans, bp_reports) for f in rep.errors()]
    if fatal:
        for pid, f in fatal[:10]:
            print(f"      [Blueprint QA ERROR] {pid} {f.slide_id} {f.code}: {f.detail}")
        raise RuntimeError(
            f"Blueprint QA FAILED with {len(fatal)} error(s); refusing to render. "
            f"See work/{work_path.name}/blueprint_qa_*.md.")

    # 5. Slide composer (deterministic Blueprint -> SlideSpec, no pedagogy)
    print("[5/7] Composing slides from Blueprint...")
    composer = SlideComposer()
    slides = []
    if len(chapter_plans) > 1:
        sb_chrome = StoryboardEngine(ledger)  # navigation chrome builders only
        slides.append(sb_chrome.build_contents_slide([p.title for p in chapter_plans]))
    for p, bp in zip(chapter_plans, blueprints):
        if len(chapter_plans) > 1:
            slides.append(sb_chrome.build_chapter_divider(p))
        slides.extend(composer.compose_all(bp.slides, p.id))
        p.slides = slides
    total_time = sum(p.estimated_time_minutes for p in chapter_plans)
    print(f"      Composed {len(slides)} slides from {sum(len(b.slides) for b in blueprints)} "
          f"blueprint slides (Estimated Time: {total_time} min).")

    # Attach embedded image paths to diagram slides
    for s in slides:
        img_id = (s.elements_data or {}).get("image_id")
        if img_id and img_id in assets["mapping"]:
            s.elements_data["image_path"] = assets["mapping"][img_id]

    storyboard_data = [
        {
            "slide_id": s.slide_id,
            "chapter_id": s.chapter_id,
            "title": s.title,
            "slide_type": s.slide_type.value,
            "visual_model": s.visual_model,
            "instructional_state": s.instructional_state,
            "instructional_purpose": s.instructional_purpose,
            "objective_ids": s.objective_ids,
            "animation_purposes": [getattr(a, "purpose", "") for a in (s.animation_steps or [])],
            "source_content_ids": s.source_content_ids,
            "estimated_time_minutes": s.estimated_time_minutes,
            "notes": s.speaker_notes.render_markdown(),
        }
        for s in slides
    ]
    (work_path / "storyboard.json").write_text(
        json.dumps(storyboard_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6. Render + Visual QA + targeted repair loop
    print("[6/7] Rendering PPTX + visual QA + repair...")
    renderer = PptxRenderer()
    renderer.render_presentation(slides, out_path)
    flat_bp = blueprints[0] if len(blueprints) == 1 else None
    render_report = RenderQA.inspect(out_path, flat_bp, work_dir=work_path)
    print(f"      Render QA: {render_report.status} via {render_report.method} "
          f"({len(render_report.errors())} errors)")
    repair_notes: list[str] = []
    for _round in range(2):
        if not render_report.errors() or flat_bp is None:
            break
        repaired, notes = repair_blueprint(flat_bp, render_report)
        repair_notes.extend(notes)
        if not repaired:
            break
        print(f"      Repair round: recomposing {len(repaired)} slide(s): {repaired}")
        (work_path / "blueprint_ch01.repaired.json").write_text(
            json.dumps(flat_bp.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        composer = SlideComposer()
        slides = composer.compose_all(flat_bp.slides, chapter_plans[0].id)
        chapter_plans[0].slides = slides
        renderer = PptxRenderer()
        renderer.render_presentation(slides, out_path)
        render_report = RenderQA.inspect(out_path, flat_bp, work_dir=work_path)
        print(f"      Re-inspection: {render_report.status} "
              f"({len(render_report.errors())} errors)")
    print(f"      Successfully saved presentation to: {out_path}")

    # 7. Quality Gates & Validation Report (VALIDATE)
    print("[7/7] Executing Quality Gates and generating validation report...")
    primary_plan = chapter_plans[0]
    # For multi-chapter decks, report total time across chapters
    primary_plan.estimated_time_minutes = total_time
    report = QualityGateValidator.validate(out_path, ledger, primary_plan, slides)
    extra_notes = []
    if assets["warnings"]:
        extra_notes.append(f"\n## Asset / Extraction Warnings\n")
        extra_notes.extend(f"- {w}\n" for w in assets["warnings"])
    if len(chapter_plans) > 1:
        extra_notes.append(f"\n## Chapters\n")
        for p in chapter_plans:
            extra_notes.append(f"- {p.id}: {p.title} (pages {p.source_start_page}-{p.source_end_page}, ~{p.estimated_time_minutes} min)\n")
    md = report.to_markdown() + ("".join(extra_notes) if extra_notes else "")
    md += "\n" + "\n\n".join(rep.to_markdown() for rep in bp_reports) + "\n"
    md += "\n" + render_report.to_markdown() + "\n"
    if repair_notes:
        md += "\n## Repair Log\n" + "\n".join(f"- {n}" for n in repair_notes) + "\n"
    (work_path / "validation_report.md").write_text(md, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"  VALIDATION STATUS: {report.overall_status}")
    print(f"  CONTENT UNITS: {report.content_units_total} | COVERED: {report.content_units_covered} | UNCOVERED: {report.content_units_uncovered}")
    print(f"  TOTAL SLIDES: {report.total_slides} | DURATION: ~{report.estimated_teaching_time_minutes} MIN")
    print("=" * 60 + "\n")

    return {
        "status": report.overall_status,
        "pptx_path": str(out_path),
        "slides_count": len(slides),
        "chapters_count": len(chapter_plans),
        "total_units": report.content_units_total,
        "covered_units": report.content_units_covered,
        "uncovered_units": report.content_units_uncovered,
        "validation_report": str(work_path / "validation_report.md"),
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="lessonmorph",
        description="LessonMorph: Document-to-teaching-presentation compiler.",
    )
    subparsers = parser.add_subparsers(dest="command")

    compile_parser = subparsers.add_parser("compile", help="Compile a document into a classroom PPTX.")
    compile_parser.add_argument("document", type=str, help="Path to educational document (PDF, DOCX, MD).")
    compile_parser.add_argument("-o", "--output", type=str, help="Output .pptx path.")
    compile_parser.add_argument("-w", "--work-dir", type=str, help="Working directory for artifacts.")
    compile_parser.add_argument("--level", type=str, default="",
                                help="Learner level (primary, middle_school, high_school, undergraduate, general).")
    compile_parser.add_argument("--grade", type=str, default="", help="Class/grade, e.g. 'Grade 10'.")
    compile_parser.add_argument("--duration-min", type=int, default=45, help="Lesson duration in minutes.")
    compile_parser.add_argument("--curriculum", type=str, default="", help="Curriculum/board, e.g. CBSE.")
    compile_parser.add_argument("--language", type=str, default="", help="Language of instruction.")

    args = parser.parse_args()

    if args.command == "compile":
        try:
            hint = {k: v for k, v in {
                "level": args.level, "grade": args.grade,
                "lesson_duration_minutes": args.duration_min,
                "curriculum": args.curriculum, "language": args.language,
            }.items() if v}
            compile_document(args.document, args.output, args.work_dir,
                             learner_hint=hint or None)
        except Exception as e:
            print(f"[LessonMorph Error] {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
