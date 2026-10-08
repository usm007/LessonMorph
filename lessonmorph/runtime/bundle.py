"""Lesson bundle writer — Lesson Runtime Model → self-contained browser lesson.

Output layout (<lesson_dir>/):
    index.html      shell; embeds lesson.json inline (file:// safe, no fetch)
    runtime.js      browser runtime (copied from web/dist, no external deps)
    styles.css      lesson styles (copied from web/dist)
    lesson.json     student-safe scenes (also embedded; file kept for QA/tools)
    teacher.json    teacher metadata: notes, intents, traceability (NOT loaded
                    by the student runtime; reserved for presenter mode)
    assets/         locally copied images referenced by scenes

Contracts enforced here:
- renderer never reinterprets pedagogy: scenes carry locked answers and
  fixed reveal states; the browser only advances/checks/displays.
- student bundle carries no internal fields (source/objective ids, intents,
  model labels, teacher guidance).
- zero network dependency: everything local, no fetch() at runtime.
"""

from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from lessonmorph.runtime.lesson_model import (
    Lesson, Scene, SceneInteraction, SceneLayer, SceneMotion, SceneState,
    TeacherScene,
)
from lessonmorph.runtime.motion_director import MotionDirector
from lessonmorph.runtime.visual_director import VisualDirector

WEB_DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"

# Internal fields that must never reach the student bundle.
_STRIPPED_SCENE_KEYS = {"purpose", "instructional_state", "concept_id",
                        "source_ids", "objective_ids", "learning_goal",
                        "teacher_action", "estimated_minutes"}


def _slug_concept(title: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in title)[:40].strip("-")


def build_scenes(blueprint: Dict[str, Any],
                 storyboard: List[Dict[str, Any]],
                 asset_map: Dict[str, str]) -> Tuple[List[Scene], List[TeacherScene]]:
    """Assemble runtime scenes from blueprint slides + storyboard notes.

    Prompt/reveal SlideIR pairs (same question_id, second marked reveal)
    merge into ONE scene with an extra "answered" state.
    """
    slides = blueprint.get("slides", [])
    notes_by_index = [s.get("notes", "") for s in storyboard]
    scenes: List[Scene] = []
    teachers: List[TeacherScene] = []
    recent: List[str] = []  # composition families, oldest first (variety tracker)
    i, n = 0, 1
    while i < len(slides):
        s = slides[i]
        body = s.get("body", {}) or {}
        nxt = slides[i + 1] if i + 1 < len(slides) else None
        pair = (nxt and (nxt.get("body", {}) or {}).get("reveal")
                and (nxt.get("body", {}) or {}).get("question_id")
                == body.get("question_id") and body.get("question_id"))
        group = [s, nxt] if pair else [s]
        scene_id = f"s{n:02d}"
        directed = VisualDirector.direct(s, recent)
        if pair:
            # Merged Q&A renders as its own reveal family with real geometry:
            # prompt, options, and verdict bands from the family template.
            from lessonmorph.runtime.visual_director import (
                family_regions as _regions, select_variant as _sv)
            directed["composition"] = "answer_reveal"
            directed["variant"] = _sv("answer_reveal", "standard", recent)
            directed["visual"]["composition"] = "answer_reveal"
            directed["visual"]["variant"] = directed["variant"]
            pair_regions = _regions("answer_reveal", directed["variant"],
                                    ["prompt", "options", "answer"])
            by_kind = {}
            for layer, region in zip(directed["layers"], pair_regions):
                layer["region"] = region
                by_kind[layer["kind"]] = layer
            directed["_pair_regions"] = pair_regions
        recent.append(directed.get("composition", ""))
        recent = recent[-6:]
        layers = [SceneLayer(**l) for l in directed["layers"]]
        states = [SceneState(**st) for st in directed["states"]]
        motion_in = MotionDirector.direct(
            s, (storyboard[i].get("animation_purposes", []) if i < len(storyboard) else []),
            layers=[{"id": l.id} for l in layers],
            states=[{"visible_layers": st.visible_layers} for st in states])
        motion = SceneMotion(enter_transition=motion_in["enter_transition"],
                             advance=motion_in["advance"],
                             paths=motion_in.get("paths", []))
        content = directed["content"]
        visual = {k: v for k, v in directed["visual"].items() if v}
        if visual.get("equation") and isinstance(visual["equation"], dict):
            visual["equation"].pop("raw_source", None)  # never ship source LaTeX
        content = _scrub_paths(content, asset_map)
        visual = _scrub_paths(visual, asset_map)
        assets = _resolve_assets(group, asset_map)
        interaction = SceneInteraction(**directed["interaction"])
        assessment = s.get("assessment") or {}
        if assessment and assessment.get("correct_option"):
            interaction.correct = str(assessment["correct_option"])
            interaction.explanation = str(assessment.get("explanation", ""))
            if not content.get("explanation"):
                content["explanation"] = str(assessment.get("explanation", ""))
        if pair:
            pair_regions = directed.pop("_pair_regions", None) or []
            answer_region = pair_regions[2] if len(pair_regions) > 2 else {
                "x": 96, "y": 470, "w": 1088, "h": 170}
            states.append(SceneState(id="answered", label="Answer",
                                     visible_layers=[l.id for l in layers]
                                     + ["answer"]))
            layers.append(SceneLayer(id="answer", kind="answer",
                                     region=answer_region,
                                     content_ref="answer", reveal_at=len(states) - 1,
                                     z=len(layers)))
            content["answer"] = {
                "correct": interaction.correct,
                "explanation": interaction.explanation,
                "prompt": content.get("prompt", ""),
            }
        scenes.append(Scene(
            scene_id=scene_id, representation=s.get("representation", ""),
            task=s.get("task", ""), states=states, layers=layers,
            content=content, visual=visual, assets=assets,
            interaction=interaction, motion=motion,
            estimated_minutes=float(s.get("estimated_minutes", 2.0) or 2.0)))
        notes = notes_by_index[i] if i < len(notes_by_index) else ""
        ta = s.get("teacher_action", {}) or {}
        teachers.append(TeacherScene(
            scene_id=scene_id, purpose=str(s.get("purpose", "")),
            instructional_state=str(s.get("instructional_state", "")),
            learning_goal=[str(g) for g in (s.get("learning_goal", []) or [])],
            teacher_notes=str(notes),
            teacher_prompt=str(ta.get("prompt", "") or ta.get("focus", "")),
            source_ids=[str(c) for c in (s.get("source_ids", []) or [])],
            objective_ids=[str(o) for o in (s.get("objective_ids", []) or [])],
            concept_id=str(s.get("concept_id", "")),
            estimated_minutes=float(s.get("estimated_minutes", 2.0) or 2.0)))
        i += len(group)
        n += 1
    return scenes, teachers


def _resolve_assets(group: List[Dict[str, Any]],
                    asset_map: Dict[str, str]) -> List[str]:
    """Relative asset refs for the bundle (absolute work paths never ship)."""
    out = []
    for s in group:
        for key in ("image_id", "image_path"):
            v = (s.get("body", {}) or {}).get(key)
            src = asset_map.get(v, "") if v else ""
            if src:
                name = "assets/" + Path(src).name
                if name not in out:
                    out.append(name)
    return out


def _scrub_paths(node: Any, asset_map: Dict[str, str]) -> Any:
    """Replace absolute work-dir asset paths with bundle-relative refs."""
    rev = {v: "assets/" + Path(v).name for v in set(asset_map.values())}
    if isinstance(node, dict):
        return {k: _scrub_paths(v, asset_map) for k, v in node.items()}
    if isinstance(node, list):
        return [_scrub_paths(v, asset_map) for v in node]
    if isinstance(node, str) and node in rev:
        return rev[node]
    return node


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Lesson</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<div id="viewport"><div id="stage"></div></div>
<script type="application/json" id="lesson-data">
{lesson_json}
</script>
<script src="runtime.js"></script>
</body>
</html>
"""


def write_bundle(lesson_dir: Path | str, lesson: Lesson,
                 teachers: List[TeacherScene],
                 asset_sources: Dict[str, str]) -> Dict[str, Any]:
    """Write the self-contained lesson directory. Returns a manifest summary."""
    dest = Path(lesson_dir)
    (dest / "assets").mkdir(parents=True, exist_ok=True)
    lesson_dict = lesson.to_dict()
    (dest / "lesson.json").write_text(
        json.dumps(lesson_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    (dest / "teacher.json").write_text(
        json.dumps({"scenes": [t.__dict__ for t in teachers]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    copied = []
    for src in sorted(set(asset_sources.values())):
        p = Path(src)
        if p.exists() and p.is_file():
            shutil.copy2(p, dest / "assets" / p.name)
            copied.append(p.name)
    for name in ("runtime.js", "styles.css"):
        src = WEB_DIST / name
        if not src.exists():
            raise FileNotFoundError(
                f"Browser runtime artifact missing: {src}. Run 'npm run build' in web/.")
        shutil.copy2(src, dest / name)
    (dest / "index.html").write_text(
        INDEX_TEMPLATE.format(
            title=lesson.title,
            lesson_json=json.dumps(lesson_dict, ensure_ascii=False)),
        encoding="utf-8")
    return {"lesson_dir": str(dest), "scenes": len(lesson.scenes),
            "assets_copied": copied,
            "internal_fields_stripped": sorted(_STRIPPED_SCENE_KEYS)}
