/* Lesson runtime entry point. Reads the embedded lesson payload
 * (inlined at bundle time — no fetch, file:// safe) and boots the viewport,
 * store, renderer, and navigation. */

function boot(): void {
  const dataEl = document.getElementById("lesson-data");
  const stage = document.getElementById("stage");
  if (!dataEl || !stage) return;
  let lesson: Lesson;
  try {
    lesson = JSON.parse(dataEl.textContent || "{}") as Lesson;
  } catch (e) {
    stage.textContent = "Lesson data is invalid.";
    return;
  }
  if (!lesson.scenes || !lesson.scenes.length) {
    stage.textContent = "This lesson has no scenes.";
    return;
  }
  initViewport();
  const app = { lesson: lesson, state: initialState(), stage: stage };
  initNav(app);
  paint(app, false);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
