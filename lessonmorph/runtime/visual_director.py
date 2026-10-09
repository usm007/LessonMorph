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

# Representation → composition family. The family owns spatial logic;
# the representation owns meaning. One family serves several representations
# so consecutive scenes can share a family only when semantics demand it.
FAMILY_BY_REPRESENTATION: Dict[str, str] = {
    "title": "cinematic_hook",
    "roadmap": "synthesis",
    "objectives": "hero_concept",
    "definition_focus": "hero_concept",
    "big_idea": "hero_concept",
    "concept_card": "hero_concept",
    "key_principle": "hero_concept",
    "contrast": "misconception",
    "labeled_diagram": "diagram_centered",
    "anatomy_map": "split_visual",
    "hierarchy": "concept_map",
    "cutaway": "full_visual",
    "spatial_relationship": "full_visual",
    "flow": "process_pathway",
    "sequence": "process_pathway",
    "pathway": "process_pathway",
    "cause_effect": "comparison",
    "before_after": "comparison",
    "comparison_matrix": "comparison",
    "cycle": "cycle",
    "equation_focus": "equation_focus",
    "worked_calculation": "equation_focus",
    "data_table": "data_visualization",
    "bar_chart": "data_visualization",
    "line_chart": "data_visualization",
    "mcq": "question_focus",
    "true_false": "question_focus",
    "prediction": "question_focus",
    "diagnostic_question": "question_focus",
    "retrieval": "question_focus",
    "practice_problem": "practice_workspace",
    "concept_map": "concept_map",
    "summary_matrix": "synthesis",
    "big_picture": "synthesis",
    "exit": "reflection",
}

COMPOSITION_FAMILIES: List[str] = [
    "cinematic_hook", "hero_concept", "full_visual", "split_visual",
    "diagram_centered", "process_pathway", "cycle", "comparison",
    "equation_focus", "data_visualization", "question_focus",
    "answer_reveal", "misconception", "practice_workspace",
    "concept_map", "synthesis", "reflection",
]

# Deterministic variants per family. Rotation (never random) guarantees
# consecutive scenes in one family never share arrangement + density.
FAMILY_VARIANTS: Dict[str, List[str]] = {
    "cinematic_hook": ["bottom-left", "center"],
    "hero_concept": ["left-anchored", "centered"],
    "full_visual": ["bleed", "inset"],
    "split_visual": ["media-left", "media-right"],
    "diagram_centered": ["hub", "columns"],
    "process_pathway": ["horizontal", "vertical"],
    "cycle": ["orbit", "grid"],
    "comparison": ["even", "emphasis-right", "emphasis-left"],
    "equation_focus": ["monument", "with-legend"],
    "data_visualization": ["wide", "with-caption"],
    "question_focus": ["centered", "left-rail"],
    "answer_reveal": ["banner", "inline"],
    "misconception": ["myth-left", "myth-right", "stacked"],
    "practice_workspace": ["open", "ruled"],
    "concept_map": ["radial", "lanes"],
    "synthesis": ["trio", "bands"],
    "reflection": ["duo", "stacked"],
}


def content_density(slide: Dict[str, Any]) -> str:
    """compact | standard | dense — from body text volume, never a guess."""
    body = slide.get("body", {}) or {}

    def _text(node: Any) -> str:
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return " ".join(_text(v) for v in node)
        if isinstance(node, dict):
            return " ".join(_text(v) for v in node.values())
        return ""

    volume = len(_text(body))
    if volume > 900:
        return "dense"
    if volume < 300:
        return "compact"
    return "standard"


def select_variant(family: str, density: str, recent: List[str]) -> str:
    """Deterministic variant rotation within a family.

    Counts how often the family already appears in recent history and steps
    through its variants; dense content offsets by one so heavy scenes land
    on airier arrangements. No randomness anywhere in this path.
    """
    variants = FAMILY_VARIANTS.get(family, ["default"])
    uses = sum(1 for f in recent if f == family)
    idx = uses % len(variants)
    if density == "dense":
        idx = (idx + 1) % len(variants)
    return variants[idx]


def _stack(x: float, y: float, w: float, h: float, n: int, gap: float = 16.0) -> List[Dict[str, float]]:
    if n <= 0:
        return []
    hh = (h - gap * (n - 1)) / n
    return [{"x": float(x), "y": float(y + i * (hh + gap)),
             "w": float(w), "h": float(hh)} for i in range(n)]


def _row(x: float, y: float, w: float, h: float, n: int, gap: float = 24.0) -> List[Dict[str, float]]:
    if n <= 0:
        return []
    ww = (w - gap * (n - 1)) / n
    return [{"x": float(x + i * (ww + gap)), "y": float(y),
             "w": float(ww), "h": float(h)} for i in range(n)]


def _caption_room(caption_len: int) -> tuple:
    """Foot height grows with caption + legend volume; the stage shrinks to fit."""
    foot_h = min(260.0, 48.0 + (caption_len // 50) * 20.0)
    foot_h = max(64.0, foot_h)
    foot_y = 656.0 - foot_h
    return foot_y, foot_h


def family_regions(family: str, variant: str, kinds: List[str],
                   caption_len: int = 0, rep: str = "") -> List[Dict[str, float]]:
    """Spatial logic per composition family — 17 genuinely different geometries.

    First kind is the head (title/prompt); the rest fill family zones.
    Coordinates are logical-canvas px (1280×720); the browser scales them.
    """
    n = len(kinds)
    head = kinds[0] if kinds else "title"
    body_kinds = kinds[1:]
    m = len(body_kinds)

    def head_zone(zone: Dict[str, float]) -> Dict[str, float]:
        return dict(zone)

    T_TOP = {"x": 96.0, "y": 44.0, "w": 1088.0, "h": 120.0}
    T_SMALL = {"x": 96.0, "y": 44.0, "w": 1088.0, "h": 56.0}
    T_PROMPT = {"x": 96.0, "y": 80.0, "w": 1088.0, "h": 160.0}
    BODY = {"x": 96.0, "y": 196.0, "w": 1088.0, "h": 460.0}

    is_prompt = head == "prompt"
    H = T_PROMPT if is_prompt else T_TOP
    HB = 196.0 if not is_prompt else 260.0
    BH = 720.0 - 64.0 - HB  # body height below head

    if family == "cinematic_hook":
        zones = ([{"x": 96.0, "y": 400.0, "w": 700.0, "h": 220.0}]
                 if variant == "bottom-left" else
                 [{"x": 190.0, "y": 300.0, "w": 900.0, "h": 220.0}])
        side = _stack(830.0 if variant == "bottom-left" else 190.0, 400.0,
                      354.0 if variant == "bottom-left" else 900.0, 220.0, m) if m else []
        if variant != "bottom-left":
            zones = [{"x": 190.0, "y": 180.0, "w": 900.0, "h": 200.0}]
            side = _stack(190.0, 400.0, 900.0, 220.0, m) if m else []
        return [head_zone(zones[0])] + side

    if family == "hero_concept":
        hz = dict(H)
        if m == 0:
            return [head_zone(hz)]
        if variant == "centered":
            focal = [{"x": 190.0, "y": HB + 10.0, "w": 900.0, "h": min(300.0, BH - 20.0)}]
            rest = _stack(190.0, HB + 320.0, 900.0, max(60.0, BH - 330.0), m - 1) if m > 1 else []
            return [head_zone(hz)] + focal + rest
        focal = [{"x": 96.0, "y": HB, "w": 640.0, "h": BH}]
        rail = _stack(760.0, HB, 424.0, BH, m - 1) if m > 1 else []
        return [head_zone(hz)] + focal + rail

    if family == "full_visual":
        hz = dict(T_SMALL)
        if variant == "bleed":
            full = [{"x": 64.0, "y": 116.0, "w": 1152.0, "h": 540.0}]
        else:
            full = [{"x": 190.0, "y": 130.0, "w": 900.0, "h": 470.0}]
        strip = _row(96.0, 620.0, 1088.0, 60.0, m - 1) if m > 1 else []
        return [head_zone(hz)] + full + strip

    if family == "split_visual":
        hz = dict(H)
        halves = _row(96.0, HB, 1088.0, BH, 2)
        if variant == "media-right":
            halves = halves[::-1]
        if m <= 2:
            return [head_zone(hz)] + (halves[:m] if m else [])
        extra = _stack(96.0, HB + BH + 8.0, 1088.0, 20.0, 1)
        return [head_zone(hz)] + halves[:2] + extra[: max(0, m - 2)][:1] + ([halves[0]] * max(0, m - 3))

    if family == "diagram_centered":
        hz = {"x": 96.0, "y": 44.0, "w": 1088.0, "h": 80.0}
        if variant == "hub":
            foot_y, foot_h = _caption_room(caption_len)
            center_h = foot_y - 12.0 - 150.0
            center = [{"x": 224.0, "y": 150.0, "w": 832.0, "h": center_h}]
            foot = _row(224.0, foot_y, 832.0, foot_h, m - 1) if m > 1 else []
            return [head_zone(hz)] + center + foot
        cols = _row(96.0, 150.0, 1088.0, 430.0, min(m, 3)) if m else []
        rest = _row(96.0, 592.0, 1088.0, 64.0, 1)[: max(0, m - 3)]
        return [head_zone(hz)] + cols + rest

    if family == "process_pathway":
        hz = dict(H)
        if variant == "horizontal":
            return [head_zone(hz)] + (_row(96.0, HB + 40.0, 1088.0, BH - 60.0, m) if m else [])
        return [head_zone(hz)] + (_stack(290.0, HB, 700.0, BH, m) if m else [])

    if family == "cycle":
        hz = dict(H)
        if variant == "orbit":
            hub = [{"x": 490.0, "y": HB + 90.0, "w": 300.0, "h": 220.0}]
            ring = _row(96.0, HB + 330.0, 1088.0, BH - 340.0, m - 1) if m > 1 else []
            return [head_zone(hz)] + hub + ring
        grid = []
        cols = 2
        rows = (m + cols - 1) // cols if m else 0
        cw, ch = 532.0, (BH - 16.0) / max(1, rows)
        for i in range(m):
            grid.append({"x": float(96.0 + (i % cols) * (cw + 24.0)),
                         "y": float(HB + (i // cols) * (ch + 16.0)),
                         "w": float(cw), "h": float(ch - 16.0)})
        return [head_zone(hz)] + grid

    if family == "comparison":
        hz = dict(H)
        if variant == "even":
            # Versus gutter down the middle (badge sits in it) — never plain halves.
            return [head_zone(hz)] + ([{"x": 96.0, "y": HB, "w": 506.0, "h": BH},
                                       {"x": 678.0, "y": HB, "w": 506.0, "h": BH}][:m] if m else [])
        wide = 640.0 if variant == "emphasis-right" else 424.0
        narrow = 1088.0 - wide - 24.0
        left_w = narrow if variant == "emphasis-right" else wide
        zones = [{"x": 96.0, "y": HB, "w": float(left_w), "h": BH},
                 {"x": float(96.0 + left_w + 24.0), "y": HB,
                  "w": float(1088.0 - left_w - 24.0), "h": BH}]
        return [head_zone(hz)] + zones[:m]

    if family == "equation_focus":
        hz = dict(T_SMALL)
        if rep == "worked_calculation":
            # The steps own the stage; problem + givens ride a compact strip.
            zones = [{"x": 96.0, "y": 120.0, "w": 1088.0, "h": 130.0},
                     {"x": 96.0, "y": 266.0, "w": 1088.0, "h": 378.0}]
            while len(zones) < m:
                zones.append({"x": 96.0, "y": 266.0, "w": 1088.0, "h": 378.0})
            return [head_zone(hz)] + zones[:m]
        if variant == "monument":
            stage = [{"x": 140.0, "y": 200.0, "w": 1000.0, "h": 300.0}]
            foot = _row(140.0, 520.0, 1000.0, 136.0, m - 1) if m > 1 else []
            return [head_zone(hz)] + stage + foot
        stage = [{"x": 96.0, "y": 140.0, "w": 700.0, "h": 320.0}]
        side = _stack(820.0, 140.0, 364.0, 320.0, m - 1) if m > 1 else []
        foot = _row(96.0, 480.0, 1088.0, 176.0, 1)[:0]
        return [head_zone(hz)] + stage + side + foot

    if family == "data_visualization":
        hz = {"x": 96.0, "y": 44.0, "w": 700.0, "h": 80.0}
        if variant == "wide":
            stage = [{"x": 96.0, "y": 150.0, "w": 1088.0, "h": 430.0}]
            foot = _row(96.0, 592.0, 1088.0, 64.0, m - 1) if m > 1 else []
            return [head_zone(hz)] + stage + foot
        stage = [{"x": 96.0, "y": 150.0, "w": 1088.0, "h": 360.0}]
        cap = _row(96.0, 524.0, 1088.0, 132.0, m - 1) if m > 1 else []
        return [head_zone(hz)] + stage + cap

    if family == "question_focus":
        if variant == "centered":
            prompt = [{"x": 140.0, "y": 140.0, "w": 1000.0, "h": 140.0}]
            opts = _stack(190.0, 300.0, 900.0, 330.0, m) if m else []
            return prompt + opts
        prompt = [{"x": 96.0, "y": 120.0, "w": 620.0, "h": 480.0}]
        opts = _stack(740.0, 120.0, 444.0, 480.0, m) if m else []
        return prompt + opts

    if family == "answer_reveal":
        # Merged Q&A geometry: prompt, options, and verdict each own a band.
        if kinds and kinds[0] == "prompt" and "options" not in kinds:
            # Short-answer reveal: the question IS the slide. Two bands, full
            # width — no dead strip where the choices would have been, and the
            # prompt keeps a real focal size instead of being squeezed into a
            # 88px caption bar.
            if variant == "banner":
                return ([{"x": 96.0, "y": 64.0, "w": 1088.0, "h": 204.0},
                         {"x": 96.0, "y": 304.0, "w": 1088.0, "h": 316.0}])[: n or 1]
            return ([{"x": 96.0, "y": 80.0, "w": 596.0, "h": 416.0},
                     {"x": 740.0, "y": 80.0, "w": 444.0, "h": 520.0}])[: n or 1]
        if variant == "banner":
            return ([{"x": 96.0, "y": 56.0, "w": 1088.0, "h": 88.0}]
                    + ([{"x": 96.0, "y": 156.0, "w": 1088.0, "h": 296.0}] if m >= 1 else [])
                    + ([{"x": 96.0, "y": 464.0, "w": 1088.0, "h": 192.0}] if m >= 2 else []))[: n or 1]
        zones = ([{"x": 96.0, "y": 60.0, "w": 640.0, "h": 180.0}]
                 + ([{"x": 96.0, "y": 260.0, "w": 640.0, "h": 384.0}] if m >= 1 else [])
                 + ([{"x": 760.0, "y": 60.0, "w": 424.0, "h": 584.0}] if m >= 2 else []))
        return zones[: n or 1]

    if family == "misconception":
        hz = dict(H)
        if variant == "stacked":
            # Full-width rows, correction-weighted: the error is shown small,
            # the verified model owns the room. Myth above, correction below.
            top_h = round((BH - 16.0) * 0.35)
            rows = [{"x": 96.0, "y": float(HB), "w": 1088.0, "h": float(top_h)},
                    {"x": 96.0, "y": float(HB + top_h + 16.0),
                     "w": 1088.0, "h": float(BH - top_h - 16.0)}][: max(0, min(m, 2))]
            extra = _row(96.0, HB + BH + 8.0, 1088.0, 20.0, 1)[: max(0, m - 2)]
            return [head_zone(hz)] + rows + extra
        # Myth gets less room than the correction — asymmetry is the point.
        if variant == "myth-left":
            zones = [{"x": 96.0, "y": HB, "w": 424.0, "h": BH},
                     {"x": 544.0, "y": HB, "w": 640.0, "h": BH}]
        else:
            zones = [{"x": 96.0, "y": HB, "w": 640.0, "h": BH},
                     {"x": 760.0, "y": HB, "w": 424.0, "h": BH}]
        extra = _row(96.0, HB + BH + 8.0, 1088.0, 20.0, 1)[: max(0, m - 2)]
        return [head_zone(hz)] + zones[: min(m, 2)] + extra

    if family == "practice_workspace":
        hz = dict(H)
        if variant == "open":
            return [head_zone(hz)] + (_stack(140.0, HB, 1000.0, BH, m) if m else [])
        return [head_zone(hz)] + (_row(140.0, HB, 1000.0, BH, m) if m else [])

    if family == "concept_map":
        hz = dict(H)
        if variant == "radial":
            hub = [{"x": 490.0, "y": HB + 60.0, "w": 300.0, "h": 200.0}]
            lanes = _row(96.0, HB + 280.0, 1088.0, BH - 290.0, m - 1) if m > 1 else []
            return [head_zone(hz)] + hub + lanes
        return [head_zone(hz)] + (_stack(290.0, HB, 700.0, BH, m) if m else [])

    if family == "synthesis":
        hz = dict(H)
        if variant == "trio":
            # Always three lanes (items take the first lanes) — never plain halves.
            lanes = _row(96.0, HB, 1088.0, BH, 3)
            return [head_zone(hz)] + lanes[: max(0, m)]
        return [head_zone(hz)] + (_stack(190.0, HB, 900.0, BH, m) if m else [])

    if family == "reflection":
        hz = dict(T_SMALL)
        if variant == "duo":
            return [head_zone(hz)] + (_row(140.0, 140.0, 1000.0, 480.0, min(m + 0, 2)) if m else [])
        return [head_zone(hz)] + (_stack(190.0, 140.0, 900.0, 480.0, m) if m else [])

    return [head_zone(dict(H))] + (_stack(96.0, HB, 1088.0, BH, m) if m else [])

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


def _asset_strategy(composition: str, slide: Dict[str, Any]) -> str:
    """Per-scene visual-asset decision (recorded, never decorated at random).

    Source figures win when present; scientific content gets native SVG;
    typographic scenes (questions, answers, practice, reflection) need none.
    """
    body = slide.get("body", {}) or {}
    visual = slide.get("visual", {}) or {}
    if body.get("image_id") or body.get("image_path"):
        return "USE_SOURCE_FIGURE"
    if any(visual.get(k) for k in ("labels", "structure", "edges", "equation",
                                   "columns", "rows")):
        return "NATIVE_SVG"
    if composition in ("diagram_centered", "split_visual", "full_visual",
                        "concept_map", "process_pathway", "cycle",
                        "equation_focus", "data_visualization", "comparison",
                        "cinematic_hook", "synthesis"):
        return "NATIVE_SVG"
    return "NO_EXTERNAL_ASSET_NEEDED"


class VisualDirector:
    """Composes scene layers + states from a SlideIR (dict form).

    Composition family owns spatial logic; the IR representation owns meaning.
    Variant rotation over recent history keeps consecutive scenes visually
    distinct without ever randomizing. Set ``recent`` to the composition
    families of previously built scenes (oldest first).
    """

    @classmethod
    def direct(cls, slide: Dict[str, Any],
               recent: List[str] | tuple = (),
               force: str | None = None) -> Dict[str, Any]:
        rep = slide.get("representation", "")
        composition = FAMILY_BY_REPRESENTATION.get(rep, "hero_concept")
        density = content_density(slide)
        variants = FAMILY_VARIANTS.get(composition, ["default"])
        variant = force if force in variants else select_variant(composition, density, list(recent))
        kinds = LAYOUTS.get(rep, ["title", "list"])
        body = slide.get("body", {}) or {}
        visual = slide.get("visual", {}) or {}
        legend_len = sum(len(str(l if isinstance(l, str) else l.get("name", "")))
                         for l in (visual.get("labels", []) or []))
        caption_len = len(str(body.get("caption", "") or "")) + legend_len
        regions = family_regions(composition, variant, kinds, caption_len, rep)
        # One body layer owns the whole body column: no stranded whitespace.
        if len(kinds) == 2 and len(regions) == 2:
            top, last = regions[0], regions[1]
            bottom = top["y"] + top["h"]
            if last["y"] >= bottom - 1 and last["y"] + last["h"] < 644.0:
                last = dict(last)
                last["h"] = 644.0 - last["y"]
                regions[1] = last
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
        visual["composition"] = composition
        visual["variant"] = variant
        visual["density"] = density
        visual["asset_strategy"] = _asset_strategy(composition, slide)
        interaction = cls._interaction(slide, rep)
        assets = cls._assets(slide)
        return {"layers": layers, "states": states, "content": content,
                "visual": visual, "interaction": interaction, "assets": assets,
                "representation": rep, "task": slide.get("task", ""),
                "composition": composition, "variant": variant}

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
                        "definition": clean(b.get("definition", "")),
                        "detail": clean(b.get("detail", ""))})
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
