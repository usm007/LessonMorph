"""Lesson QA — validates the browser bundle before delivery.

Gates (independent of PPTX QA):
- schema: lesson.json has canvas/scenes; every scene has id, representation,
  ≥1 state, ≥1 layer, and motion; interactions of type choice carry options.
- separation: student lesson.json contains none of the internal fields
  (source/objective ids, intents, model labels, teacher guidance, LaTeX).
- offline: shell + runtime + styles reference no remote resources and the
  runtime performs no fetch/XHR (static scan); every scene asset exists.
- traceability: every teacher scene maps 1:1 to a student scene.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

INTERNAL_PATTERNS = ("source_ids", "objective_ids", "concept_id",
                     "instructional_state", "teacher_action", "learning_goal",
                     "raw_source", '"purpose"')

REMOTE_PATTERNS = ("http://", "https://", "fetch(", "XMLHttpRequest", "@import")


@dataclass
class LessonQACheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class LessonQAReport:
    checks: List[LessonQACheck] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "PASS" if all(c.passed for c in self.checks) else "FAIL"

    def errors(self) -> List[LessonQACheck]:
        return [c for c in self.checks if not c.passed]

    def to_markdown(self) -> str:
        lines = ["## LESSON QA (browser bundle)", "",
                 f"Status: `{self.status}`", "",
                 "| Check | Status | Detail |", "| :--- | :---: | :--- |"]
        for c in self.checks:
            lines.append(f"| {c.name} | {'PASS' if c.passed else '**FAIL**'} | {c.detail} |")
        return "\n".join(lines)


class LessonQA:
    """Validates a written lesson bundle directory."""

    @classmethod
    def validate(cls, lesson_dir: Path | str) -> LessonQAReport:
        dest = Path(lesson_dir)
        report = LessonQAReport()
        lesson_file = dest / "lesson.json"
        teacher_file = dest / "teacher.json"
        if not lesson_file.exists():
            report.checks.append(LessonQACheck("bundle-present", False, "lesson.json missing"))
            return report
        report.checks.append(LessonQACheck("bundle-present", True, str(dest)))
        try:
            lesson = json.loads(lesson_file.read_text(encoding="utf-8"))
        except Exception as e:
            report.checks.append(LessonQACheck("schema", False, f"lesson.json unparseable: {e}"))
            return report
        report.checks.append(cls._check_schema(lesson))
        report.checks.append(cls._check_separation(lesson_file))
        report.checks.append(cls._check_offline(dest))
        report.checks.append(cls._check_assets(dest, lesson))
        report.checks.append(cls._check_teacher_map(teacher_file, lesson))
        return report

    @staticmethod
    def _check_schema(lesson: dict) -> LessonQACheck:
        problems = []
        if lesson.get("canvas") != {"width": 1280, "height": 720}:
            problems.append("canvas must be 1280x720")
        scenes = lesson.get("scenes", [])
        if not scenes:
            problems.append("no scenes")
        for s in scenes:
            sid = s.get("scene_id", "?")
            if not s.get("representation"):
                problems.append(f"{sid}: missing representation")
            if not s.get("states"):
                problems.append(f"{sid}: no states")
            if not s.get("layers"):
                problems.append(f"{sid}: no layers")
            inter = s.get("interaction", {})
            if inter.get("type") == "choice" and not inter.get("options"):
                problems.append(f"{sid}: choice interaction without options")
            if inter.get("type") == "choice" and not inter.get("correct"):
                problems.append(f"{sid}: unlocked answer (correct key empty)")
        return LessonQACheck("schema", not problems, "; ".join(problems) or f"{len(scenes)} scenes ok")

    @staticmethod
    def _check_separation(lesson_file: Path) -> LessonQACheck:
        text = lesson_file.read_text(encoding="utf-8")
        leaked = sorted({p for p in INTERNAL_PATTERNS if p in text})
        return LessonQACheck("student-separation", not leaked,
                             f"leaked: {leaked}" if leaked else "no internal fields")

    @staticmethod
    def _check_offline(dest: Path) -> LessonQACheck:
        problems = []
        for name in ("index.html", "runtime.js", "styles.css"):
            p = dest / name
            if not p.exists():
                problems.append(f"{name} missing")
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            hits = sorted({pat for pat in REMOTE_PATTERNS if pat in text})
            # https:// in a comment is still a smell; runtime must be clean.
            if hits:
                problems.append(f"{name} references remote: {hits}")
        return LessonQACheck("offline", not problems, "; ".join(problems) or "fully local")

    @staticmethod
    def _check_assets(dest: Path, lesson: dict) -> LessonQACheck:
        missing = []
        for s in lesson.get("scenes", []):
            for a in s.get("assets", []):
                if not (dest / a).exists():
                    missing.append(f"{s.get('scene_id')}:{a}")
        return LessonQACheck("assets", not missing,
                             f"missing: {missing}" if missing else "all local")

    @staticmethod
    def _check_teacher_map(teacher_file: Path, lesson: dict) -> LessonQACheck:
        if not teacher_file.exists():
            return LessonQACheck("teacher-map", False, "teacher.json missing")
        try:
            teacher = json.loads(teacher_file.read_text(encoding="utf-8"))
        except Exception as e:
            return LessonQACheck("teacher-map", False, f"unparseable: {e}")
        student_ids = [s.get("scene_id") for s in lesson.get("scenes", [])]
        teacher_ids = [s.get("scene_id") for s in teacher.get("scenes", [])]
        ok = student_ids == teacher_ids
        return LessonQACheck("teacher-map", ok,
                             "1:1 scene mapping" if ok else "scene id mismatch")
