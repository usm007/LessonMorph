"""Static visual QA — the bundle as data, before pixels.

Evaluates geometry (regions in-canvas, overlap, tiny zones), semantic fit
(structure→diagram, process→pathway, …), student readability (focal presence,
density, title discipline), motion discipline (every step has a why, timings
from tokens, no banned effects), repetition, and card policy. Findings carry
per-scene repair hints consumed by visual_repair.py.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from lessonmorph.runtime.motion_director import (
    EFFECT_DURATION_MS, PRIMITIVE_DURATION, PRIMITIVES, TIMING_TOKENS,
)
from lessonmorph.runtime.visual_director import FAMILY_VARIANTS

CANVAS_W, CANVAS_H = 1280, 720
BANNED_EFFECTS = {"bounce", "spin", "zoom", "flip", "rotate", "elastic"}
FOCAL_FAMILIES = {
    "cinematic_hook", "hero_concept", "full_visual", "split_visual",
    "diagram_centered", "process_pathway", "cycle", "comparison",
    "equation_focus", "data_visualization", "question_focus",
    "answer_reveal", "misconception",
}

# Representation → evidence that must exist in the scene to count as the
# thing it claims to be (never a text box wearing the label).
SEMANTIC_EVIDENCE: Dict[str, List[str]] = {
    "labeled_diagram": ["labels|structure"],
    "anatomy_map": ["labels|structure"],
    "cutaway": ["labels|structure"],
    "spatial_relationship": ["labels|structure"],
    "hierarchy": ["points|labels"],
    "flow": ["points|steps"],
    "sequence": ["points|steps"],
    "pathway": ["points|steps"],
    "cycle": ["points"],
    "cause_effect": ["points"],
    "before_after": ["points"],
    "equation_focus": ["equation.terms"],
    "worked_calculation": ["steps"],
    "data_table": ["columns+rows"],
    "bar_chart": ["columns+rows"],
    "line_chart": ["columns+rows"],
    "comparison_matrix": ["columns+rows"],
    "mcq": ["prompt+options"],
    "true_false": ["prompt+options"],
    "prediction": ["prompt"],
    "diagnostic_question": ["prompt"],
    "retrieval": ["prompt"],
    "practice_problem": ["items+scaffold"],
    "contrast": ["wrong+correct"],
    "definition_focus": ["term+definition"],
    "concept_map": ["points"],
}


@dataclass
class VisualFinding:
    scene_id: str
    code: str
    severity: str  # ERROR | WARNING
    detail: str
    repair: str = ""


@dataclass
class VisualQAReport:
    findings: List[VisualFinding] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(f.severity == "ERROR" for f in self.findings):
            return "FAIL"
        if self.findings:
            return "WARN"
        return "PASS"

    def errors(self) -> List[VisualFinding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    def to_markdown(self) -> str:
        lines = ["## VISUAL QA (static)", "", f"Status: `{self.status}`", "",
                 "| Scene | Code | Severity | Detail | Repair |",
                 "| :--- | :--- | :---: | :--- | :--- |"]
        for f in self.findings:
            lines.append(f"| {f.scene_id} | {f.code} | {f.severity} | {f.detail} | {f.repair} |")
        if not self.findings:
            lines.append("| — | — | PASS | No static visual defects. | — |")
        return "\n".join(lines)


def _text_of(content: Dict[str, Any]) -> str:
    parts = []
    for k, v in content.items():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts += [str(x) for x in v if isinstance(x, (str, int, float))]
        elif isinstance(v, dict):
            parts += [str(x) for x in v.values() if isinstance(x, (str, int, float))]
    return " ".join(parts)


class StaticVisualQA:
    """Analyzes lesson.json without a browser."""

    @classmethod
    def analyze(cls, lesson_dir: Path | str) -> VisualQAReport:
        dest = Path(lesson_dir)
        report = VisualQAReport()
        try:
            lesson = json.loads((dest / "lesson.json").read_text(encoding="utf-8"))
        except Exception as e:
            report.findings.append(VisualFinding("-", "bundle-unreadable", "ERROR", str(e), "rebuild bundle"))
            return report
        scenes = lesson.get("scenes", [])
        if not scenes:
            report.findings.append(VisualFinding("-", "no-scenes", "ERROR", "lesson has no scenes", "rebuild"))
            return report
        for s in scenes:
            cls._geometry(s, report)
            cls._semantic(s, report)
            cls._readability(s, report)
            cls._motion(s, report)
        cls._repetition(scenes, report)
        cls._titles(scenes, report, str(lesson.get("title", "")))
        return report

    @staticmethod
    def _geometry(s: Dict[str, Any], report: VisualQAReport) -> None:
        sid = s.get("scene_id", "?")
        boxes = [(l.get("id", "?"), l.get("region", {}) or {}) for l in s.get("layers", [])]
        for lid, r in boxes:
            try:
                x, y, w, h = float(r.get("x", 0)), float(r.get("y", 0)), float(r.get("w", 0)), float(r.get("h", 0))
            except (TypeError, ValueError):
                report.findings.append(VisualFinding(sid, "region-malformed", "ERROR", f"layer {lid}", "re-direct scene"))
                continue
            if x < 0 or y < 0 or x + w > CANVAS_W or y + h > CANVAS_H:
                report.findings.append(VisualFinding(sid, "off-canvas", "ERROR",
                    f"layer {lid} escapes 1280×720", "re-direct with tighter zones"))
            if (w < 60 or h < 24) and lid not in ("answer",):
                report.findings.append(VisualFinding(sid, "tiny-zone", "WARNING",
                    f"layer {lid} is {w:.0f}×{h:.0f}px", "merge into a sibling zone"))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i][1], boxes[j][1]
                try:
                    ax, ay, aw, ah = float(a.get("x", 0)), float(a.get("y", 0)), float(a.get("w", 0)), float(a.get("h", 0))
                    bx, by, bw, bh = float(b.get("x", 0)), float(b.get("y", 0)), float(b.get("w", 0)), float(b.get("h", 0))
                except (TypeError, ValueError):
                    continue
                ix = min(ax + aw, bx + bw) - max(ax, bx)
                iy = min(ay + ah, by + bh) - max(ay, by)
                if ix <= 0 or iy <= 0:
                    continue
                inter = ix * iy
                small = min(aw * ah, bw * bh)
                if small <= 0 or inter <= 0.9 * small and inter > 0.35 * small:
                    report.findings.append(VisualFinding(sid, "overlap", "WARNING",
                        f"{boxes[i][0]} × {boxes[j][0]}", "separate zones or stage as states"))

    @staticmethod
    def _evidence(s: Dict[str, Any], token: str) -> bool:
        content, visual = s.get("content", {}), s.get("visual", {})
        if token == "labels|structure":
            return bool(visual.get("labels") or visual.get("structure") or s.get("assets"))
        if token == "points|steps":
            return bool(content.get("points") or content.get("steps") or content.get("items"))
        if token == "points|labels":
            return bool(content.get("points") or visual.get("labels"))
        if token == "points":
            return bool(content.get("points"))
        if token == "steps":
            return bool(content.get("steps"))
        if token == "equation.terms":
            eq = visual.get("equation", {}) or {}
            return bool(eq.get("lhs") or eq.get("rhs"))
        if token == "columns+rows":
            return bool(visual.get("columns") and visual.get("rows"))
        if token == "prompt+options":
            return bool(content.get("prompt") and content.get("options"))
        if token == "prompt":
            return bool(content.get("prompt") or (content.get("items") or [""])[0])
        if token == "items+scaffold":
            return bool(content.get("items"))
        if token == "wrong+correct":
            return bool(content.get("wrong_idea") and content.get("correct_idea"))
        if token == "term+definition":
            return bool(content.get("term") and content.get("definition"))
        return True

    @classmethod
    def _semantic(cls, s: Dict[str, Any], report: VisualQAReport) -> None:
        sid, rep = s.get("scene_id", "?"), s.get("representation", "")
        for token in SEMANTIC_EVIDENCE.get(rep, []):
            if not cls._evidence(s, token):
                report.findings.append(VisualFinding(sid, "semantic-mismatch", "ERROR",
                    f"{rep} without {token} — a {rep} must be a {rep}, not prose",
                    "restore source payload or change representation"))

    @staticmethod
    def _readability(s: Dict[str, Any], report: VisualQAReport) -> None:
        sid = s.get("scene_id", "?")
        visual, content = s.get("visual", {}), s.get("content", {})
        fam = visual.get("composition", "")
        if fam and fam not in FOCAL_FAMILIES and fam not in (
                "practice_workspace", "concept_map", "synthesis", "reflection"):
            report.findings.append(VisualFinding(sid, "weak-focal", "WARNING",
                f"family {fam} has no focal treatment", "restage with a focal family"))
        body_chars = len(_text_of(content))
        body_area = sum(float((l.get("region", {}) or {}).get("w", 0)) * float((l.get("region", {}) or {}).get("h", 0))
                        for l in s.get("layers", []) if l.get("kind") in ("text", "list", "table"))
        if body_area > 0 and body_chars / body_area > 0.012:
            report.findings.append(VisualFinding(sid, "excessive-density", "WARNING",
                f"~{body_chars} chars in {body_area:.0f}px²", "split scene or move detail to notes"))
        if body_area > 0 and body_chars < 20 and fam not in ("cinematic_hook", "full_visual"):
            report.findings.append(VisualFinding(sid, "excessive-empty", "WARNING",
                "almost no content for the canvas", "enlarge the focal element"))

    @staticmethod
    def _motion(s: Dict[str, Any], report: VisualQAReport) -> None:
        sid = s.get("scene_id", "?")
        motion = s.get("motion", {}) or {}
        allowed_durations = set(TIMING_TOKENS.values()) | set(EFFECT_DURATION_MS.values()) | set(PRIMITIVE_DURATION.values())
        for step in motion.get("advance", []) or []:
            if not step.get("why"):
                report.findings.append(VisualFinding(sid, "motion-without-why", "ERROR",
                    f"step {step.get('step')}", "state the instructional reason"))
            if step.get("effect") in BANNED_EFFECTS or step.get("primitive") in BANNED_EFFECTS:
                report.findings.append(VisualFinding(sid, "banned-motion", "ERROR",
                    str(step.get("effect") or step.get("primitive")), "use a calm primitive"))
            if step.get("duration_ms") not in allowed_durations:
                report.findings.append(VisualFinding(sid, "rogue-timing", "ERROR",
                    f"{step.get('duration_ms')}ms off-token", "snap to a timing token"))
            if step.get("duration_ms", 0) > 4000:
                report.findings.append(VisualFinding(sid, "excessive-animation", "ERROR",
                    f"step runs {step.get('duration_ms')}ms", "shorten or split"))
        for path in motion.get("paths", []) or []:
            if not path.get("via") or len(path["via"]) < 2:
                report.findings.append(VisualFinding(sid, "path-without-waypoints", "ERROR",
                    "marker with nowhere to go", "drop the path or bind waypoints"))
            if not path.get("why"):
                report.findings.append(VisualFinding(sid, "motion-without-why", "ERROR",
                    "path", "state the instructional reason"))

    @staticmethod
    def _repetition(scenes: List[Dict[str, Any]], report: VisualQAReport) -> None:
        fams = [(s.get("scene_id", "?"), (s.get("visual", {}) or {}).get("composition", "")) for s in scenes]
        run, start = 1, fams[0][0] if fams else "-"
        for k in range(1, len(fams)):
            if fams[k][1] and fams[k][1] == fams[k - 1][1]:
                run += 1
            else:
                if run >= 5:
                    report.findings.append(VisualFinding(start, "repetitive-composition", "WARNING",
                        f"{fams[k-1][1]} ×{run}", "vary variant or restage one scene"))
                run, start = 1, fams[k][0]
        if run >= 5 and fams:
            report.findings.append(VisualFinding(start, "repetitive-composition", "WARNING",
                f"{fams[-1][1]} ×{run}", "vary variant or restage one scene"))
        variants = [(s.get("scene_id", "?"), (s.get("visual", {}) or {}).get("variant", "")) for s in scenes]
        for k in range(2, len(variants)):
            triple = variants[k - 2:k + 1]
            if triple[0][1] and all(v[1] == triple[0][1] for v in triple):
                fam = (scenes[k].get("visual", {}) or {}).get("composition", "")
                report.findings.append(VisualFinding(triple[0][0], "same-arrangement-thrice", "WARNING",
                    f"{fam}/{triple[0][1]} ×3", "force an alternate variant"))

    @staticmethod
    def _titles(scenes: List[Dict[str, Any]], report: VisualQAReport, lesson_title: str = "") -> None:
        from collections import Counter
        titles = [(s.get("scene_id", "?"), (s.get("content", {}) or {}).get("title", "")) for s in scenes]
        freq = Counter(t for _, t in titles if t)
        dominant = {t for t, c in freq.items() if c > max(3, len(titles) // 4)}
        seen: Dict[str, str] = {}
        for sid, title in titles:
            if not title:
                continue
            if len(title) > 90:
                report.findings.append(VisualFinding(sid, "title-treatment", "WARNING",
                    "title over 90 chars", "shorten; detail belongs in body"))
            if title in dominant or title == lesson_title:
                continue  # reported once below, not per scene
            if title in seen:
                report.findings.append(VisualFinding(sid, "title-treatment", "WARNING",
                    f"repeats '{title[:40]}' from {seen[title]}", "vary or drop the repeat"))
            else:
                seen[title] = sid
        for title in sorted(dominant):
            first = next(sid for sid, t in titles if t == title)
            report.findings.append(VisualFinding(first, "title-treatment", "WARNING",
                f"{freq[title]} scenes share '{title[:50]}'",
                "give scenes distinct titles upstream (IR-level)"))
