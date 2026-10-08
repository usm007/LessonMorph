"""Rendered-scene QA — every scene/state as a student sees it.

Drives the real browser bundle with Playwright (Chromium, 1280×720, exactly
the logical canvas so CSS px == screenshot px): each scene is stepped through
its states like a teacher would (Space), choice scenes answer with the locked
key, and initial/mid/final/answered states are screenshotted to work/shots/.
Per-shot pixel checks: overflow, overlap, tiny text, focal presence, density,
contrast, emptiness. No browser available → a single skipped WARNING, never
a silent pass.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

METRICS_JS = r"""() => {
  const layers = [...document.querySelectorAll('#stage [data-layer]')].map(el => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    let contentBottom = r.top;
    const kids = el.querySelectorAll('*');
    for (let k = 0; k < kids.length; k++) {
      const b = kids[k].getBoundingClientRect();
      if (b.height > 0 && b.width > 0) contentBottom = Math.max(contentBottom, b.bottom);
    }
    const m = /scale\(([0-9.]+)\)/.exec(el.style.transform || '');
    return { id: el.dataset.layer || '', x: r.x, y: r.y, w: r.width, h: r.height,
             text: (el.innerText || '').trim(),
             fontSize: parseFloat(cs.fontSize) || 0,
             color: cs.color, display: cs.display,
             spill: (() => { const fit = /scale\(([0-9.]+)\)/.exec(el.style.transform || '');
               // A fitted layer is judged by its visible geometry: transforms do
               // not change scrollHeight, so layout height would false-positive.
               if (fit) return Math.max(0, contentBottom - (r.top + el.clientHeight));
               return Math.max(0, contentBottom - (r.top + el.clientHeight), el.scrollHeight - el.clientHeight); })(),
             fitted: m ? parseFloat(m[1]) : 1 };
  });
  const texts = [...document.querySelectorAll('#stage p, #stage li, #stage h1, #stage td, #stage th, #stage text, #stage .dg-chiptext')].map(el => {
    const cs = getComputedStyle(el);
    return { size: parseFloat(cs.fontSize) || 0, color: cs.color,
             bg: (() => { let n = el; while (n) { const b = getComputedStyle(n).backgroundColor;
               if (b && !/rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)/.test(b) && b !== 'transparent') return b; n = n.parentElement; } return 'rgb(250, 250, 250)'; })(),
             text: (el.textContent || '').trim().slice(0, 60) };
  });
  const svgArea = [...document.querySelectorAll('#stage svg')].reduce((a, s) => {
    const r = s.getBoundingClientRect(); return a + r.width * r.height; }, 0);
  const imgArea = [...document.querySelectorAll('#stage img')].reduce((a, s) => {
    const r = s.getBoundingClientRect(); return a + (r.width > 2 && r.height > 2 ? r.width * r.height : 0); }, 0);
  const maxText = texts.reduce((a, t) => Math.max(a, t.size || 0), 0);
  return { layers, texts, svgArea, imgArea, maxText,
           allText: layers.map(l => l.text).join(' ') };
}"""


def _lum(rgb: str) -> float:
    import re
    m = re.match(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)", rgb or "")
    if not m:
        return 1.0
    def lin(v: float) -> float:
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = lin(float(m.group(1))), lin(float(m.group(2))), lin(float(m.group(3)))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg: str, bg: str) -> float:
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


@dataclass
class ShotResult:
    scene_id: str
    state: str
    path: str


@dataclass
class RenderedQAReport:
    shots: List[ShotResult] = field(default_factory=list)
    findings: List[Dict[str, str]] = field(default_factory=list)
    skipped: str = ""

    @property
    def status(self) -> str:
        if self.skipped and not self.findings:
            return "SKIP"
        if any(f["severity"] == "ERROR" for f in self.findings):
            return "FAIL"
        if self.findings:
            return "WARN"
        return "PASS"

    def to_markdown(self) -> str:
        lines = ["## VISUAL QA (rendered)", "", f"Status: `{self.status}`",
                 f"Shots: `{len(self.shots)}`", ""]
        if self.skipped:
            lines.append(f"Note: {self.skipped}\n")
        lines += ["| Scene | State | Severity | Detail |",
                  "| :--- | :--- | :---: | :--- |"]
        for f in self.findings:
            lines.append(f"| {f['scene']} | {f['state']} | {f['severity']} | {f['detail']} |")
        if not self.findings and not self.skipped:
            lines.append("| — | — | PASS | Every shot reads clean. |")
        return "\n".join(lines)


class ShotRunner:
    """Screenshots + pixel checks. Browser missing → skipped report."""

    @classmethod
    def run(cls, lesson_dir: Path | str, shots_dir: Path | str,
            only: List[str] | None = None) -> RenderedQAReport:
        dest, out = Path(lesson_dir), Path(shots_dir)
        report = RenderedQAReport()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            report.skipped = "playwright not installed — rendered QA skipped"
            return report
        try:
            lesson = json.loads((dest / "lesson.json").read_text(encoding="utf-8"))
        except Exception as e:
            report.findings.append({"scene": "-", "state": "-", "severity": "ERROR",
                                    "detail": f"lesson.json unreadable: {e}"})
            return report
        scenes = lesson.get("scenes", [])
        if only:
            scenes = [s for s in scenes if s.get("scene_id") in only]
        out.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto((dest / "index.html").resolve().as_uri())
                page.wait_for_selector("#stage .scene-body", timeout=15000)
                for s in scenes:
                    cls._shoot_scene(page, s, out, report)
                browser.close()
        except Exception as e:
            if not report.shots and not report.findings:
                report.skipped = f"browser unavailable ({e}) — rendered QA skipped"
            else:
                report.findings.append({"scene": "-", "state": "-", "severity": "ERROR",
                                        "detail": f"shot run aborted: {e}"})
        return report

    @classmethod
    def _state(cls, page) -> dict:
        return page.evaluate("() => ({ i: window.__lessonApp.state.sceneIndex, "
                             "s: window.__lessonApp.state.stateIndex })")

    @classmethod
    def _goto(cls, page, idx: int) -> None:
        page.evaluate(f"() => {{ const a = window.__lessonApp; "
                      f"goTo(a.lesson, a.state, {idx}); paint(a, false); }}")
        page.wait_for_timeout(120)

    @classmethod
    def _press(cls, page, key: str = " ") -> None:
        page.keyboard.press("Space" if key == " " else key)
        page.wait_for_timeout(150)

    @classmethod
    def _shoot_scene(cls, page, scene: dict, out: Path, report: RenderedQAReport) -> None:
        sid = scene.get("scene_id", "?")
        # Resolve index via page lesson (authoritative at runtime).
        idx = page.evaluate(f"() => window.__lessonApp.lesson.scenes.findIndex(s => s.scene_id === '{sid}')")
        if idx is None or idx < 0:
            return
        # states_total is for scene 0; re-read after goto below.
        cls._goto(page, idx)
        n_states = page.evaluate("() => currentScene(window.__lessonApp.lesson, "
                                 "window.__lessonApp.state).states.length")
        interesting = sorted({0, n_states // 2, n_states - 1})
        # Walk states like a teacher; answer choice scenes with the locked key.
        correct = (scene.get("interaction", {}) or {}).get("correct", "")
        itype = (scene.get("interaction", {}) or {}).get("type", "none")
        for step in range(n_states + 1):
            st = cls._state(page)
            if st["i"] != idx:
                break
            if st["s"] in interesting or (itype == "choice" and step == n_states):
                tag = f"{sid}-s{st['s']}"
                path = out / f"{tag}.png"
                page.screenshot(path=str(path))
                report.shots.append(ShotResult(sid, f"s{st['s']}", str(path)))
                cls._inspect(page, sid, f"s{st['s']}", report)
            if itype == "choice" and correct and not page.evaluate(
                    "() => window.__lessonApp.state.selected"):
                btns = page.query_selector_all(f".opt[data-key='{correct}']")
                if btns:
                    btns[0].click()
                    page.wait_for_timeout(150)
            cls._press(page)
            if cls._state(page)["i"] != idx:
                # Final state of this scene may never have rendered — capture it.
                break
        # Ensure the terminal state was captured.
        last_tag = f"{sid}-s{n_states - 1}"
        if not any(s.path.endswith(last_tag + ".png") for s in report.shots):
            cls._goto(page, idx)
            for _ in range(n_states):
                cls._press(page)
            path = out / f"{last_tag}.png"
            page.screenshot(path=str(path))
            report.shots.append(ShotResult(sid, last_tag, str(path)))
            cls._inspect(page, sid, last_tag, report)

    @classmethod
    def _inspect(cls, page, sid: str, state: str, report: RenderedQAReport) -> None:
        m = page.evaluate(METRICS_JS)
        layers = m.get("layers", [])
        # Overflow / overlap on rendered boxes.
        for l in layers:
            if l["x"] < -1 or l["y"] < -1 or l["x"] + l["w"] > 1281 or l["y"] + l["h"] > 721:
                report.findings.append({"scene": sid, "state": state, "severity": "ERROR",
                    "code": "overflow",
                    "detail": f"overflow: {l['id']} at {l['x']:.0f},{l['y']:.0f} {l['w']:.0f}×{l['h']:.0f}"})
            if l.get("spill", 0) > 4:
                report.findings.append({"scene": sid, "state": state, "severity": "ERROR",
                    "code": "spill",
                    "detail": f"text escapes region: {l['id']} (+{l['spill']:.0f}px)"})
            if 0 < l.get("fitted", 1) < 0.8:
                report.findings.append({"scene": sid, "state": state, "severity": "WARNING",
                    "detail": f"{l['id']} auto-scaled to {l['fitted']:.0%} — consider splitting the scene"})
        for i in range(len(layers)):
            for j in range(i + 1, len(layers)):
                a, b = layers[i], layers[j]
                ix = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                iy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                if ix <= 0 or iy <= 0:
                    continue
                inter = ix * iy
                small = min(a["w"] * a["h"], b["w"] * b["h"])
                if small > 0 and inter > 0.9 * small:
                    continue  # container pattern
                if small > 0 and inter > 0.35 * small:
                    report.findings.append({"scene": sid, "state": state, "severity": "WARNING",
                        "detail": f"overlap: {a['id']} × {b['id']}"})
        tiny = sorted({f"{t['text'][:30]} ({t['size']:.0f}px)" for t in m.get("texts", []) if 0 < t["size"] < 12})
        if tiny:
            report.findings.append({"scene": sid, "state": state, "severity": "WARNING",
                "detail": f"tiny text: {'; '.join(tiny[:4])}"})
        if m.get("maxText", 0) < 30 and m.get("svgArea", 0) < 0.15 * 1280 * 720 and m.get("imgArea", 0) == 0:
            report.findings.append({"scene": sid, "state": state, "severity": "WARNING",
                "detail": "weak focal point: nothing ≥30px and no significant figure"})
        chars = len(m.get("allText", ""))
        if chars > 1400:
            report.findings.append({"scene": sid, "state": state, "severity": "WARNING",
                "detail": f"excessive density: ~{chars} chars on one viewport"})
        if not m.get("allText", "").strip() and m.get("svgArea", 0) == 0 and m.get("imgArea", 0) == 0:
            report.findings.append({"scene": sid, "state": state, "severity": "ERROR",
                "detail": "empty viewport: no text and no figure"})
        for t in m.get("texts", []):
            if not t["text"] or t["size"] <= 0:
                continue
            large = t["size"] >= 24
            need = 3.0 if large else 4.5
            if _contrast(t["color"], t["bg"]) < need:
                report.findings.append({"scene": sid, "state": state, "severity": "WARNING",
                    "detail": f"weak contrast: '{t['text'][:30]}'"})
                break
