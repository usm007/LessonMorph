"""Repair loop: regenerate AFFECTED slides from their Blueprint.

Generate Blueprint → Blueprint QA → Generate PPTX → Render slides →
Visual QA → Identify failures → Repair Blueprint/slide representation →
Regenerate affected slide(s) → Render again → Final QA.

Only failing slides are re-composed; pedagogy is never regenerated.
Unfixable errors (e.g. incorrect locked answer rendering) escalate to the
final QA report for human review instead of being silently re-rendered.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Dict, List, Tuple
from lessonmorph.blueprint.ir import REPAIR_FALLBACK, Representation, SlideIR
from lessonmorph.blueprint.render_qa import RenderReport
from lessonmorph.blueprint.sanitize import clean

_SPLITTABLE = ("points", "steps", "stages", "takeaways", "nodes")


def repair_blueprint(bp, report: RenderReport) -> Tuple[List[str], List[str]]:
    """Patch failing SlideIRs in place. Returns (repaired_ids, notes)."""
    by_id: Dict[str, SlideIR] = {s.id: s for s in bp.slides}
    repaired: List[str] = []
    notes: List[str] = []
    errors = [f for f in report.errors() if f.slide_id and f.slide_id in by_id]
    if not errors:
        return repaired, notes

    for slide_id in sorted({f.slide_id for f in errors}):
        sir = by_id[slide_id]
        codes = {f.code for f in errors if f.slide_id == slide_id}
        if codes & {"incorrect_answer", "slide_count_mismatch"}:
            notes.append(f"{slide_id}: {sorted(codes)} escalated — locked-answer or "
                         "structural faults need human review, not re-rendering.")
            continue
        if codes & {"raw_latex", "raw_markdown", "broken_symbols"}:
            _resanitize(sir)
            repaired.append(slide_id)
            notes.append(f"{slide_id}: re-sanitized markup leak.")
            continue
        if codes & {"text_overflow", "overcrowding"} and _splittable_len(sir) > 3:
            _split_slide(bp, sir)
            repaired.append(slide_id)
            notes.append(f"{slide_id}: split dense payload across two slides.")
            continue
        # Representation fallback (same family, simpler visual).
        try:
            fallback = REPAIR_FALLBACK.get(Representation(sir.representation))
        except ValueError:
            fallback = None
        if fallback:
            notes.append(f"{slide_id}: {sir.representation} → {fallback.value} "
                         f"({sorted(codes)}).")
            sir.representation = fallback.value
            repaired.append(slide_id)
        else:
            notes.append(f"{slide_id}: {sorted(codes)} — no simpler representation; "
                         "kept as-is for human review.")
    return repaired, notes


def _resanitize(sir: SlideIR) -> None:
    for k, v in list(sir.body.items()):
        if isinstance(v, str):
            sir.body[k] = clean(v)
        elif isinstance(v, list):
            sir.body[k] = [clean(x) if isinstance(x, str) else x for x in v]


def _splittable_len(sir: SlideIR) -> int:
    for key in _SPLITTABLE:
        val = sir.body.get(key)
        if isinstance(val, list) and len(val) > 3:
            return len(val)
    stages = sir.visual.structure
    return len(stages) if len(stages) > 3 else 0


def _split_slide(bp, sir: SlideIR) -> None:
    key = next((k for k in _SPLITTABLE if isinstance(sir.body.get(k), list)
                and len(sir.body[k]) > 3), "")
    if key:
        items = sir.body[key]
        half = (len(items) + 1) // 2
        first, second = items[:half], items[half:]
    else:
        items = sir.visual.structure
        half = (len(items) + 1) // 2
        first, second = items[:half], items[half:]
        key = ""
    sir.body[key] = first if key else sir.body.get(key)
    if not key:
        sir.visual.structure = first
    sir.reveal_sequence = [r for r in sir.reveal_sequence][:half + 1] or ["part_1"]
    idx = bp.slides.index(sir)
    twin = deepcopy(sir)
    suffix = "b"
    existing = {s.id for s in bp.slides}
    while f"{sir.id}{suffix}" in existing:
        suffix += "b"
    twin.id = f"{sir.id}{suffix}"
    if key:
        twin.body[key] = second
    else:
        twin.visual.structure = second
    twin.reveal_sequence = ["part_2"]
    twin.purpose = f"{sir.purpose} (continued)"
    bp.slides.insert(idx + 1, twin)
    # Inventory: the twin preserves the same source elements (traceability kept).
    for item in bp.inventory:
        if item.slide_id == sir.id:
            item.slide_id = f"{sir.id}+{twin.id}"
