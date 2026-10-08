/* Navigation: keyboard, mouse/tap, fullscreen. Runtime only — no pedagogy. */

interface Window {
  __lessonApp?: { lesson: Lesson; state: RuntimeState; stage: HTMLElement };
}

function toggleFullscreen(): void {
  try {
    if (document.fullscreenElement) { void document.exitFullscreen(); return; }
    const root = document.documentElement;
    if (root.requestFullscreen) { void root.requestFullscreen(); }
  } catch (e) { /* fullscreen unavailable */ }
}

function onSelectOption(key: string): void {
  const app = window.__lessonApp;
  if (!app) return;
  selectOption(app.state, key);
  renderScene(app.stage, app.lesson, app.state);
}

function initNav(app: { lesson: Lesson; state: RuntimeState; stage: HTMLElement }): void {
  window.__lessonApp = app;
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowRight" || ev.key === " ") {
      ev.preventDefault();
      stepForward(app);
    } else if (ev.key === "ArrowLeft") {
      ev.preventDefault();
      if (back(app.lesson, app.state)) paint(app, false);
    } else if (ev.key === "Home") {
      ev.preventDefault();
      if (goTo(app.lesson, app.state, 0)) paint(app, true);
    } else if (ev.key === "End") {
      ev.preventDefault();
      if (goTo(app.lesson, app.state, app.lesson.scenes.length - 1)) paint(app, true);
    }
    // Escape exits fullscreen natively; nothing to do here.
  });
  app.stage.addEventListener("click", () => stepForward(app));
}

function stepForward(app: { lesson: Lesson; state: RuntimeState; stage: HTMLElement }): void {
  const r = advance(app.lesson, app.state);
  if (r.moved) paint(app, true);
}

function paint(app: { lesson: Lesson; state: RuntimeState; stage: HTMLElement }, animate: boolean): void {
  renderScene(app.stage, app.lesson, app.state);
  playEntrance(app.stage, currentScene(app.lesson, app.state), app.state, animate);
}
