"""Visual Director — IR representation → renderer-neutral scene composition.

Pure, deterministic translation. No pedagogy, no content extraction, no
meaning reinterpretation: it only decides WHERE things go on the 1280×720
canvas (regions, layers, z-order) and WHEN they appear (reveal states).

Safe area: 64px margins (≈5%); content width 1152px, centered.
"""

from __future__ import annotations
from typing import Any, Dict, List

from lessonmorph.blueprint.sanitize import clean
from lessonmorph.runtime.lesson_model import CANVAS_HEIGHT, CANVAS_WIDTH

MARGIN = 64
CONTENT_W = CANVAS_WIDTH - 2 * MARGIN  # 1152

TITLE_REGION = {"x": 96, "y": 44, "w": 1088, "h": 120}
BODY_REGION = {"x": 96, "y": 196, "w": 1088, "h": 460}
FULL_REGION = {"x": 96, "y": 44, "w": 1088, "h": 612}

# Representation → ordered layer kinds. The browser renderer owns the pixels;
# this table only fixes composition structure per representation family.
LAYOUTS: Dict[str, List[str]] = {
    "title": ["title", "subtitle"],
    "definition_focus": ["title", "text"],
    "big_idea": ["title", "text"],
    "concept_card": ["title", "list"],
    "key_principle": ["title", "list"],
    "contrast": ["title", "text", "text"],
    "labeled_diagram": ["title", "diagram", "note"],
    "anatomy_map": ["title", "diagram", "note"],
    "hierarchy": ["title", "list"],
    "cutaway": ["title", "diagram", "note"],
    "spatial_relationship": ["title", "diagram", "note"],
    "flow": ["title", "list"],
    "sequence": ["title", "list"],
    "cycle": ["title", "diagram"],
    "cause_effect": ["title", "list"],
    "before_after": ["title", "list", "list"],
    "pathway": ["title", "diagram"],
    "equation_focus": ["title", "equation", "list"],
    "worked_calculation": ["title", "text", "list"],
    "data_table": ["title", "table"],
    "bar_chart": ["title", "table"],
    "line_chart": ["title", "table"],
    "comparison_matrix": ["title", "table"],
    "mcq": ["prompt", "options"],
    "true_false": ["prompt", "options"],
    "prediction": ["prompt", "options"],
    "diagnostic_question": ["prompt", "options"],
    "retrieval": ["prompt"],
    "practice_problem": ["prompt", "note"],
    "concept_map": ["title", "list"],
    "summary_matrix": ["title", "table"],
    "big_picture": ["title", "list"],
    "roadmap": ["title", "list"],
    "objectives": ["title", "list"],
    "exit": ["title", "list"],
}


def _regions_for(kinds: List[str]) -> List[Dict[str, float]]:
    """Stack body layers vertically inside the body region."""
    regions = []
    n_body = max(1, len(kinds) - 1)
    body_h = BODY_REGION["h"] / n_body
    for i, kind in enumerate(kinds):
        if i == 0 and kind in ("title", "prompt"):
            regions.append(dict(TITLE_REGION if kind == "title" else
                                {"x": 96, "y": 80, "w": 1088, "h": 160}))
        else:
            y = BODY_REGION["y"] + (i - 1) * body_h if kinds[0] in ("title", "prompt") \
                else BODY_REGION["y"] + i * body_h
            regions.append({"x": float(BODY_REGION["x"]), "y": float(y),
                            "w": float(BODY_REGION["w"]),
                            "h": float(body_h - 16)})
    return regions


class VisualDirector:
    """Composes scene layers + states from a SlideIR (dict form)."""

    @classmethod
    def direct(cls, slide: Dict[str, Any]) -> Dict[str, Any]:
        rep = slide.get("representation", "")
        kinds = LAYOUTS.get(rep, ["title", "list"])
        regions = _regions_for(kinds)
        reveal = [str(r) for r in slide.get("reveal_sequence", [])] or ["show"]
        states = [{"id": "base", "label": "", "visible_layers": []}]
        for i, name in enumerate(reveal):
            states.append({"id": f"s{i + 1}", "label": clean(name),
                           "visible_layers": []})
        layers = []
        for i, kind in enumerate(kinds):
            lid = kind if kinds.count(kind) == 1 else f"{kind}-{i}"
            reveal_at = min(i, len(states) - 1)
            layers.append({"id": lid, "kind": kind, "region": regions[i],
                           "content_ref": lid, "reveal_at": reveal_at, "z": i})
        for st_i, st in enumerate(states):
            st["visible_layers"] = [l["id"] for l in layers if l["reveal_at"] <= st_i]
        content = cls._content(slide, rep)
        visual = {k: slide.get("visual", {}).get(k)
                  for k in ("subject", "structure", "labels", "edges",
                            "columns", "rows", "equation")}
        interaction = cls._interaction(slide, rep)
        assets = cls._assets(slide)
        return {"layers": layers, "states": states, "content": content,
                "visual": visual, "interaction": interaction, "assets": assets,
                "representation": rep, "task": slide.get("task", "")}

    @staticmethod
    def _content(slide: Dict[str, Any], rep: str) -> Dict[str, Any]:
        b = slide.get("body", {}) or {}
        out: Dict[str, Any] = {
            "title": clean(slide.get("content_title", "")),
            "kicker": clean(slide.get("kicker", "")),
        }
        if rep == "title":
            out.update({"unit": clean(b.get("unit", "")),
                        "topic": clean(b.get("topic", slide.get("content_title", "")))})
        elif rep == "definition_focus":
            out.update({"term": clean(b.get("term", "")),
                        "definition": clean(b.get("definition", ""))})
        elif rep in ("mcq", "true_false", "prediction", "diagnostic_question",
                     "retrieval"):
            out.update({"prompt": clean(b.get("prompt", "")),
                        "options": {k: clean(v) for k, v in (b.get("options", {}) or {}).items()},
                        "explanation": clean(b.get("explanation", ""))})
        elif rep == "practice_problem":
            out.update({"items": [clean(i) for i in (b.get("items", []) or [])],
                        "scaffold": b.get("scaffold", {}) or {}})
        elif rep == "equation_focus":
            out.update({"context": clean(b.get("context", ""))})
        elif rep == "worked_calculation":
            out.update({"problem": clean(b.get("problem", "")),
                        "givens": [clean(g) for g in (b.get("givens", []) or [])],
                        "steps": [clean(s) for s in (b.get("steps", []) or [])],
                        "verify": clean(b.get("verify", ""))})
        elif rep in ("data_table", "comparison_matrix", "summary_matrix",
                     "bar_chart", "line_chart"):
            out.update({"table_title": clean(b.get("title", ""))})
        elif rep == "objectives":
            out.update({"objectives": [clean(o) for o in (b.get("objectives", []) or [])]})
        elif rep == "exit":
            out.update({"prompt_1": clean(b.get("prompt_1", "")),
                        "prompt_2": clean(b.get("prompt_2", ""))})
        elif rep == "contrast":
            out.update({k: clean(b.get(k, "")) for k in
                        ("wrong_idea", "why_wrong", "correct_idea", "correct_reasoning")})
        else:
            out.update({"points": [clean(p) for p in (b.get("points", []) or [])],
                        "caption": clean(b.get("caption", ""))})
            if b.get("takeaways"):
                out["points"] = [clean(t) for t in b["takeaways"]]
        return out

    @staticmethod
    def _interaction(slide: Dict[str, Any], rep: str) -> Dict[str, Any]:
        if rep in ("mcq", "true_false"):
            a = slide.get("assessment") or {}
            return {"type": "choice",
                    "options": sorted((a.get("options", {}) or {}).keys()),
                    "correct": "",  # filled from locked assessment by bundle builder
                    "explanation": ""}
        if rep in ("prediction", "diagnostic_question"):
            return {"type": "choice", "options": [], "correct": "", "explanation": ""}
        if rep == "practice_problem":
            return {"type": "open", "options": [], "correct": "", "explanation": ""}
        if rep == "retrieval":
            return {"type": "self_check", "options": [], "correct": "", "explanation": ""}
        return {"type": "none", "options": [], "correct": "", "explanation": ""}

    @staticmethod
    def _assets(slide: Dict[str, Any]) -> List[str]:
        out = []
        for key in ("image_id", "image_path"):
            v = (slide.get("body", {}) or {}).get(key)
            if v:
                out.append(str(v))
        return out
