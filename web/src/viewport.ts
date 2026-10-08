/* 16:9 viewport scaler. Logical canvas 1280x720; the window letterboxes,
 * never distorts, never scrolls. */

const LOGICAL_W = 1280;
const LOGICAL_H = 720;

function fitStage(): void {
  const stage = document.getElementById("stage");
  const viewport = document.getElementById("viewport");
  if (!stage || !viewport) return;
  const scale = Math.min(window.innerWidth / LOGICAL_W, window.innerHeight / LOGICAL_H);
  stage.style.width = LOGICAL_W + "px";
  stage.style.height = LOGICAL_H + "px";
  stage.style.transform = "translate(-50%, -50%) scale(" + scale + ")";
  viewport.style.background = "#0b0e14";
}

function initViewport(): void {
  document.documentElement.style.height = "100%";
  document.body.style.height = "100%";
  document.body.style.margin = "0";
  document.body.style.overflow = "hidden";
  window.addEventListener("resize", fitStage);
  fitStage();
}
