"""Semantic visual repair — fix the scene from its specification, never hide it.

Repairable codes (geometry/arrangement): overlap, off-canvas, tiny-zone,
same-arrangement-thrice, repetitive-composition, weak-focal, spill, overflow.
The repair picks the ROOMIEST variant of the SAME composition family
(largest minimum body-zone area — prose needs room, not a different idea)
and rewrites only regions + variant in lesson.json. Content, states, motion
and pedagogy are untouched. If no variant is roomier, it escalates to human
review instead of cycling.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

from lessonmorph.runtime.visual_director import FAMILY_VARIANTS, family_regions

REPAIRABLE = {"overlap", "off-canvas", "tiny-zone", "same-arrangement-thrice",
              "repetitive-composition", "weak-focal", "spill", "overflow"}

BODY_KINDS = {"text", "list", "table", "note", "options", "diagram", "equation"}


def roomiest_variant(family: str, kinds: List[str], current: str,
                     caption_len: int = 0, rep: str = "") -> str:
    """Variant giving cramped prose the most room: largest minimum body-zone
    width first (prose flows in width), then largest minimum area. Ties keep
    the current variant instead of churning."""
    def key(variant: str) -> tuple:
        regions = family_regions(family, variant, kinds, caption_len, rep)
        widths = [r["w"] for k, r in zip(kinds, regions) if k in BODY_KINDS]
        areas = [r["w"] * r["h"] for k, r in zip(kinds, regions) if k in BODY_KINDS]
        return (min(widths) if widths else 0.0, min(areas) if areas else 0.0)

    best, best_key = current, key(current)
    for variant in FAMILY_VARIANTS.get(family, ["default"]):
        variant_key = key(variant)
        if variant_key > best_key:
            best, best_key = variant, variant_key
    return best


def alternate_variant(family: str, current: str) -> str:
    variants = FAMILY_VARIANTS.get(family, ["default"])
    if current in variants:
        return variants[(variants.index(current) + 1) % len(variants)]
    return variants[0]


def repair_lesson(lesson: Dict[str, Any], scene_ids: List[str]) -> Dict[str, List[str]]:
    """Returns {scene_id: [notes]}; mutates the lesson dict in place."""
    log: Dict[str, List[str]] = {}
    by_id = {s.get("scene_id"): s for s in lesson.get("scenes", [])}
    for sid in scene_ids:
        s = by_id.get(sid)
        if not s:
            continue
        notes: List[str] = []
        visual = s.get("visual", {}) or {}
        family = visual.get("composition", "")
        if family not in FAMILY_VARIANTS:
            notes.append("no composition family — cannot repair geometrically; human review")
            log[sid] = notes
            continue
        kinds = [l.get("kind", "list") for l in s.get("layers", [])]
        content = s.get("content", {}) or {}
        caption_len = len(str(content.get("caption", "") or ""))
        target = roomiest_variant(family, kinds, visual.get("variant", ""), caption_len,
                                  s.get("representation", ""))
        if target == visual.get("variant", ""):
            notes.append(f"no roomier {family} variant — needs scene split upstream (IR-level human review)")
            log[sid] = notes
            continue
        regions = family_regions(family, target, kinds, caption_len, s.get("representation", ""))
        for layer, region in zip(s.get("layers", []), regions):
            layer["region"] = region
        visual["variant"] = target
        notes.append(f"variant {family}: {target} restaged for room (repair, content untouched)")
        log[sid] = notes
    return log


def scenes_for_codes(findings: List[Any], codes=REPAIRABLE) -> List[str]:
    out = []
    for f in findings:
        code = f.code if hasattr(f, "code") else f.get("code", "")
        sid = f.scene_id if hasattr(f, "scene_id") else f.get("scene", "")
        if code in codes and sid not in out:
            out.append(sid)
    return out
