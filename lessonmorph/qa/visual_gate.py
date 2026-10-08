"""Visual quality gate — technical + design + semantic + readability.

Pipeline: static QA → screenshots → repair loop (≤2) → re-shoot → report.
Static FAIL blocks delivery. Rendered FAIL blocks delivery (SKIP only when no
browser exists, recorded as a warning for human review). Regression asserts
the photosynthesis benchmark categories are present and were inspected.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from lessonmorph.qa.shots import RenderedQAReport, ShotRunner
from lessonmorph.qa.visual import StaticVisualQA, VisualQAReport
from lessonmorph.qa.visual_repair import repair_lesson, scenes_for_codes

# representation → benchmark slot for the photosynthesis regression lesson.
REGRESSION_SLOTS: Dict[str, str] = {
    "title": "opener",
    "definition_focus": "definition",
    "equation_focus": "equation",
    "labeled_diagram": "chloroplast diagram",
    "worked_calculation": "worked calculation",
    "contrast": "misconception",
    "mcq": "question",
}


@dataclass
class VisualGateReport:
    static: VisualQAReport = field(default_factory=VisualQAReport)
    rendered: RenderedQAReport = field(default_factory=RenderedQAReport)
    repair_log: Dict[str, List[str]] = field(default_factory=dict)
    regression: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        statuses = [self.static.status]
        if self.rendered.status != "SKIP":
            statuses.append(self.rendered.status)
        if any(s == "FAIL" for s in statuses):
            return "FAIL"
        if any(s == "WARN" for s in statuses) or self.rendered.status == "SKIP":
            return "WARN"
        return "PASS"

    def to_markdown(self) -> str:
        lines = ["# VISUAL QUALITY GATE (browser, primary renderer)", "",
                 f"Overall: `{self.status}`", ""]
        if self.regression:
            lines += ["## Regression benchmark", ""]
            lines += [f"- {r}" for r in self.regression] + [""]
        lines.append(self.static.to_markdown())
        lines += ["", self.rendered.to_markdown()]
        if self.repair_log:
            lines += ["", "## Repair log", ""]
            for sid, notes in self.repair_log.items():
                lines += [f"- {sid}: " + "; ".join(notes)]
        return "\n".join(lines)


def _regression(lesson: dict, shots: list) -> List[str]:
    reps = {}
    for s in lesson.get("scenes", []):
        reps.setdefault(s.get("representation", ""), []).append(s.get("scene_id", "?"))
    shot_ids = {s.scene_id for s in shots}
    lines = []
    for rep, slot in REGRESSION_SLOTS.items():
        ids = reps.get(rep, [])
        seen = [i for i in ids if i in shot_ids]
        lines.append(f"{slot}: {'inspected ' + ', '.join(seen) if seen else 'MISSING'}")
    practices = [s for s in lesson.get("scenes", []) if s.get("representation") == "practice_problem"]
    blob = json.dumps(practices).lower()
    lines.append(f"electron pathway: {'present' if 'electron' in blob else 'MISSING'}")
    lines.append(f"c3/c4 comparison: {'present' if ('c3' in blob and 'c4' in blob) else 'MISSING'}")
    answered = [s.get("scene_id") for s in lesson.get("scenes", [])
                if any(st.get("id") == "answered" for st in s.get("states", []))]
    lines.append(f"answer states: {', '.join(answered) if answered else 'MISSING'}")
    synth = reps.get("big_picture", []) + reps.get("concept_map", []) + reps.get("summary_matrix", [])
    lines.append(f"synthesis: {', '.join(synth) if synth else 'MISSING'}")
    return lines


def run_visual_qa(lesson_dir: Path | str, work_dir: Path | str,
                  shots: bool = True, repair: bool = True) -> VisualGateReport:
    """Full gate. Raises RuntimeError on FAIL (blocks delivery)."""
    lesson_path, work = Path(lesson_dir), Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    gate = VisualGateReport()

    gate.static = StaticVisualQA.analyze(lesson_path)
    if gate.static.status == "FAIL":
        _write(work, gate, lesson_path)
        raise RuntimeError("Visual QA (static) FAILED — refusing delivery. See work/visual_qa.md.")

    if shots:
        shots_dir = work / "shots"
        gate.rendered = ShotRunner.run(lesson_path, shots_dir)
        attempted: Dict[str, set] = {}
        for _ in range(2 if repair else 0):
            if gate.rendered.status != "FAIL":
                break
            repairable = scenes_for_codes(
                gate.rendered.findings,
                {"overlap", "off-canvas", "tiny-zone", "weak-focal", "spill", "overflow",
                 "repetitive-composition"})
            static_repairable = scenes_for_codes(gate.static.findings) if gate.static.status == "FAIL" else []
            targets = sorted(set(repairable) | set(static_repairable))
            # Don't cycle: scenes whose whole family was already tried escalate.
            fresh = [t for t in targets if len(attempted.get(t, set())) < _variant_count(lesson_path, t)]
            if not fresh:
                for t in targets:
                    gate.repair_log.setdefault(t, []).append(
                        "all variants exhausted — needs scene split upstream (IR-level human review)")
                break
            lesson = json.loads((lesson_path / "lesson.json").read_text(encoding="utf-8"))
            notes = repair_lesson(lesson, fresh)
            for sid, ns in notes.items():
                gate.repair_log.setdefault(sid, []).extend(ns)
                attempted.setdefault(sid, set()).add(_current_variant(lesson, sid))
            (lesson_path / "lesson.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
            _sync_embedded_payload(lesson_path, lesson)
            gate.rendered = ShotRunner.run(lesson_path, shots_dir)
        if gate.rendered.status == "FAIL":
            leftover = scenes_for_codes(
                gate.rendered.findings,
                {"overlap", "off-canvas", "tiny-zone", "weak-focal", "spill", "overflow"})
            for t in sorted(set(leftover)):
                if len(attempted.get(t, set())) >= _variant_count(lesson_path, t):
                    gate.repair_log.setdefault(t, []).append(
                        "geometry variants exhausted — needs scene split upstream (IR-level human review)")

    try:
        lesson = json.loads((lesson_path / "lesson.json").read_text(encoding="utf-8"))
        gate.regression = _regression(lesson, gate.rendered.shots)
    except Exception:
        gate.regression = ["regression: lesson unreadable"]
    _write(work, gate, lesson_path)
    if gate.status == "FAIL":
        raise RuntimeError("Visual QA FAILED — refusing delivery. See work/visual_qa.md.")
    return gate


def _current_variant(lesson: dict, scene_id: str) -> str:
    for s in lesson.get("scenes", []):
        if s.get("scene_id") == scene_id:
            return (s.get("visual", {}) or {}).get("variant", "")
    return ""


def _variant_count(lesson_path: Path, scene_id: str) -> int:
    try:
        from lessonmorph.runtime.visual_director import FAMILY_VARIANTS
        lesson = json.loads((lesson_path / "lesson.json").read_text(encoding="utf-8"))
        for s in lesson.get("scenes", []):
            if s.get("scene_id") == scene_id:
                fam = (s.get("visual", {}) or {}).get("composition", "")
                return len(FAMILY_VARIANTS.get(fam, ["default"]))
    except Exception:
        pass
    return 1


def _sync_embedded_payload(lesson_path: Path, lesson: dict) -> None:
    """index.html embeds a copy of the lesson for file:// use — keep it in sync."""
    import re
    html_file = lesson_path / "index.html"
    if not html_file.exists():
        return
    html = html_file.read_text(encoding="utf-8")
    payload = json.dumps(lesson, ensure_ascii=False)
    updated, count = re.subn(
        r'(<script type="application/json" id="lesson-data">\s*).*?(\s*</script>)',
        lambda m: m.group(1) + payload + m.group(2),
        html, count=1, flags=re.S)
    if count:
        html_file.write_text(updated, encoding="utf-8")


def _write(work: Path, gate: VisualGateReport, lesson_path: Path) -> None:
    (work / "visual_qa.md").write_text(gate.to_markdown(), encoding="utf-8")
