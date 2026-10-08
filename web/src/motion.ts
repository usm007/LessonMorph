/* Semantic motion executor — every animation answers "why should this move?".
 * Vocabulary mirrors lessonmorph/runtime/motion_director.py primitives; timings
 * mirror its TIMING_TOKENS. Scenes never invent timings. All playback is
 * deterministic (driven by scene.motion + state index) and inert under
 * prefers-reduced-motion: states still advance, meaning preserved. */

const MOTION_TOKENS = { fast: 180, normal: 250, slow: 400, process: 600 };
const MOTION_EASING = "ease-out";

/* Primitive → instructional reason (mirrors the director; audited by motion QA). */
const PRIMITIVE_WHY: { [k: string]: string } = {
  fade: "enter a supporting element without stealing focus",
  appear: "progressive disclosure of the next idea",
  wipe: "causal direction: this leads to that",
  slide: "transformation: the same object changes state",
  scale: "emphasize magnitude or importance once",
  highlight: "direct attention for comparison",
  pulse: "draw the eye to the active region, then stop",
  path_motion: "a marker travels a real visual path",
  progressive_reveal: "build a derivation or structure piece by piece",
  answer_reveal: "disclose the locked answer after thinking",
  diagram_reveal: "light up the next diagram component in sequence",
  state_transition: "move between scene states without rebuilding",
};

function reducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) { return false; }
}

function effectFor(scene: Scene, stepIndex: number): { effect: string; duration_ms: number } {
  const adv = scene.motion && scene.motion.advance ? scene.motion.advance : [];
  const found = adv.filter((a) => a.step === stepIndex + 1)[0];
  if (found) return { effect: found.effect, duration_ms: found.duration_ms };
  return { effect: "fade", duration_ms: MOTION_TOKENS.normal };
}

function playEntrance(stage: HTMLElement, scene: Scene, st: RuntimeState, firstPaint: boolean): void {
  if (reducedMotion()) return; // states advance; no movement. Meaning preserved.
  const fresh = newlyVisible(scene, st);
  if (firstPaint && scene.motion && scene.motion.enter_transition === "fade") {
    const anim = stage.animate([{ opacity: 0 }, { opacity: 1 }], { duration: MOTION_TOKENS.fast, easing: MOTION_EASING });
    if (anim && (anim as any).finished) (anim as any).finished.catch(function () { /* noop */ });
  }
  playFreshLayers(stage, fresh, scene, st);
  playRegionActivation(stage, scene, st);
  playSceneSequence(stage, scene, st);
  playPaths(stage, scene, st);
}

function playFreshLayers(stage: HTMLElement, fresh: string[], scene: Scene, st: RuntimeState): void {
  const kids = stage.querySelectorAll("[data-layer]");
  // Restrained: options enter as one staggered group, never N independent solos.
  let optDelay = 0;
  for (let i = 0; i < kids.length; i++) {
    const node = kids[i] as HTMLElement;
    const lid = node.dataset ? node.dataset.layer : "";
    if (!lid || fresh.indexOf(lid) === -1) continue;
    const fx = effectFor(scene, st.stateIndex);
    let delay = 0;
    if (node.classList && node.classList.contains("opt") && optDelay < 4) {
      delay = (optDelay++) * 60;
    }
    playEffect(node, fx.effect, fx.duration_ms, delay);
  }
}

/* Newly lit diagram region pulses once so the sequence reads as disclosure. */
function playRegionActivation(stage: HTMLElement, scene: Scene, st: RuntimeState): void {
  const regions = stage.querySelectorAll("[data-region].active");
  for (let i = 0; i < regions.length; i++) {
    const node = regions[i] as HTMLElement;
    playEffect(node, "highlight", MOTION_TOKENS.slow);
  }
}

/* Compositional sequences: misconception strike, answer evidence, think cue. */
function playSceneSequence(stage: HTMLElement, scene: Scene, st: RuntimeState): void {
  const v = scene.visual || {};
  const fam = (v.composition as string) || "";
  if (fam === "misconception" && st.stateIndex > 0) {
    stage.classList.add("played");
  }
  if (fam === "answer_reveal" || (scene.interaction && scene.interaction.type !== "none" && atFinalState(scene, st))) {
    const banner = stage.querySelector(".answer-banner, .lyr-answer");
    if (banner) playEffect(banner as HTMLElement, "emphasis", MOTION_TOKENS.slow);
  }
  if (fam === "question_focus" && st.stateIndex === 0 && !st.selected) {
    const cue = stage.querySelector(".think-cue");
    if (cue) playEffect(cue as HTMLElement, "highlight", MOTION_TOKENS.slow);
  }
}

interface Waypoint { x: number; y: number; name: string; }

/* Path motion: a marker travels real rendered geometry (region anchors or
 * pathway nodes), narrated by a live caption naming each leg. Waypoints come
 * from IR label names resolved to on-screen anchors — never invented. */
function resolveWaypoints(stage: HTMLElement, via: string[]): Waypoint[] {
  const out: Waypoint[] = [];
  const regions = stage.querySelectorAll("[data-region]");
  const byIndex: HTMLElement[] = [];
  for (let i = 0; i < regions.length; i++) byIndex.push(regions[i] as HTMLElement);
  const stageBox = stage.getBoundingClientRect();
  const anchor = (node: HTMLElement): Waypoint => {
    const b = node.getBoundingClientRect();
    return {
      x: (b.left + b.width / 2 - stageBox.left) / (stageBox.width || 1) * 1280,
      y: (b.top + b.height / 2 - stageBox.top) / (stageBox.height || 1) * 720,
      name: "",
    };
  };
  if (byIndex.length >= 2 && via.length >= 2) {
    const order = via.map((_, i) => Math.min(i, byIndex.length - 1));
    order.forEach((ri, k) => {
      const w = anchor(byIndex[ri]);
      w.name = via[k] || "";
      out.push(w);
    });
    return out;
  }
  const nodes = stage.querySelectorAll(".pw-node");
  for (let i = 0; i < nodes.length; i++) {
    const w = anchor(nodes[i] as HTMLElement);
    w.name = via[i] || "";
    out.push(w);
  }
  return out;
}

function playPaths(stage: HTMLElement, scene: Scene, st: RuntimeState): void {
  const paths = (scene.motion && scene.motion.paths) || [];
  if (!paths.length || st.stateIndex === 0) return;
  // One journey per scene, on the latest state only — never concurrent solos.
  const path = paths[0];
  const pts = resolveWaypoints(stage, path.via || []);
  if (pts.length < 2) return;
  const dur = Math.min(path.duration_ms || MOTION_TOKENS.process, 4000);
  const marker = document.createElement("div");
  marker.className = "path-marker kind-" + path.kind;
  const cap = document.createElement("div");
  cap.className = "path-caption";
  stage.appendChild(marker);
  stage.appendChild(cap);
  const legMs = dur / (pts.length - 1);
  let leg = 0;
  const place = (p: Waypoint): void => {
    marker.style.left = p.x + "px";
    marker.style.top = p.y + "px";
  };
  place(pts[0]);
  const stepLeg = (): void => {
    if (leg >= pts.length - 1) {
      setTimeout(() => { if (marker.parentNode) marker.parentNode.removeChild(marker); }, 600);
      setTimeout(() => { if (cap.parentNode) cap.parentNode.removeChild(cap); }, 1800);
      return;
    }
    const a = pts[leg], b = pts[leg + 1];
    cap.textContent = (a.name ? a.name + " " : "") + "→ " + (b.name || "next");
    try {
      const anim = marker.animate([
        { left: a.x + "px", top: a.y + "px" },
        { left: b.x + "px", top: b.y + "px" },
      ], { duration: legMs, easing: "ease-in-out", fill: "forwards" });
      const done = (): void => { leg++; stepLeg(); };
      if (anim && (anim as any).finished) (anim as any).finished.then(done, done);
      else setTimeout(done, legMs);
    } catch (e) { place(b); leg++; stepLeg(); }
  };
  setTimeout(stepLeg, 120);
}

function playEffect(node: HTMLElement, effect: string, ms: number, delay?: number): void {
  const run = (): void => {
    let frames: Keyframe[] = [{ opacity: 0 }, { opacity: 1 }];
    if (effect === "slide") frames = [{ opacity: 0, transform: "translateX(28px)" }, { opacity: 1, transform: "none" }];
    else if (effect === "wipe") frames = [{ opacity: 0, clipPath: "inset(0 100% 0 0)" }, { opacity: 1, clipPath: "inset(0 0 0 0)" }];
    else if (effect === "highlight") frames = [{ opacity: 0 }, { opacity: 1 }, { opacity: 0.55 }, { opacity: 1 }];
    else if (effect === "emphasis") frames = [{ transform: "scale(1)" }, { transform: "scale(1.02)" }, { transform: "scale(1)" }];
    try {
      const anim = node.animate(frames, { duration: ms, easing: MOTION_EASING });
      if (anim && (anim as any).finished) (anim as any).finished.catch(function () { /* noop */ });
    } catch (e) { /* animation unsupported: content stays visible */ }
  };
  if (delay) setTimeout(run, delay);
  else run();
}
