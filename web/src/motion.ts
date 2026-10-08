/* Motion executor. Applies entrance motion to newly visible layers using
 * the Web Animations API (browser-native, no libraries). Effects mirror the
 * Motion Director vocabulary: fade | wipe | slide | highlight | emphasis | reveal.
 * Scene transitions: subtle fade on the stage. */

function effectFor(scene: Scene, stepIndex: number): { effect: string; duration_ms: number } {
  const adv = scene.motion && scene.motion.advance ? scene.motion.advance : [];
  const found = adv.filter((a) => a.step === stepIndex + 1)[0];
  if (found) return { effect: found.effect, duration_ms: found.duration_ms };
  return { effect: "fade", duration_ms: 250 };
}

function playEntrance(stage: HTMLElement, scene: Scene, st: RuntimeState, firstPaint: boolean): void {
  const fresh = newlyVisible(scene, st);
  if (firstPaint && scene.motion && scene.motion.enter_transition === "fade") {
    const anim = stage.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 220, easing: "ease-out" });
    if (anim && (anim as any).finished) (anim as any).finished.catch(function () { /* noop */ });
  }
  const kids = stage.children;
  for (let i = 0; i < kids.length; i++) {
    const node = kids[i] as HTMLElement;
    const lid = node.dataset ? node.dataset.layer : "";
    if (!lid || fresh.indexOf(lid) === -1 || node.id === "progress") continue;
    const fx = effectFor(scene, st.stateIndex);
    playEffect(node, fx.effect, fx.duration_ms);
  }
}

function playEffect(node: HTMLElement, effect: string, ms: number): void {
  let frames: Keyframe[] = [{ opacity: 0 }, { opacity: 1 }];
  if (effect === "slide") frames = [{ opacity: 0, transform: "translateX(28px)" }, { opacity: 1, transform: "none" }];
  else if (effect === "wipe") frames = [{ opacity: 0, clipPath: "inset(0 100% 0 0)" }, { opacity: 1, clipPath: "inset(0 0 0 0)" }];
  else if (effect === "highlight") frames = [{ opacity: 0 }, { opacity: 1 }, { opacity: 0.55 }, { opacity: 1 }];
  else if (effect === "emphasis") frames = [{ transform: "scale(1)" }, { transform: "scale(1.02)" }, { transform: "scale(1)" }];
  try {
    const anim = node.animate(frames, { duration: ms, easing: "ease-out" });
    if (anim && (anim as any).finished) (anim as any).finished.catch(function () { /* noop */ });
  } catch (e) { /* animation unsupported: content stays visible */ }
}
