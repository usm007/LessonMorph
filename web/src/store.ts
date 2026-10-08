/* Deterministic lesson state machine. Pure functions, no DOM. */

interface RuntimeState {
  sceneIndex: number;
  stateIndex: number;
  selected: string | null;   // chosen option key for choice scenes
  answeredScenes: { [sceneId: string]: string | boolean }; // scene -> choice|"done"
}

function initialState(): RuntimeState {
  return { sceneIndex: 0, stateIndex: 0, selected: null, answeredScenes: {} };
}

function currentScene(lesson: Lesson, st: RuntimeState): Scene {
  return lesson.scenes[st.sceneIndex];
}

function atFinalState(scene: Scene, st: RuntimeState): boolean {
  return st.stateIndex >= scene.states.length - 1;
}

function isLastScene(lesson: Lesson, st: RuntimeState): boolean {
  return st.sceneIndex >= lesson.scenes.length - 1;
}

/** Advance: next state, or next scene. Returns {moved, wrapped}. */
function advance(lesson: Lesson, st: RuntimeState): { moved: boolean; wrapped: boolean } {
  const scene = currentScene(lesson, st);
  if (!atFinalState(scene, st)) {
    st.stateIndex += 1;
    return { moved: true, wrapped: false };
  }
  // Leaving an interactive scene records completion.
  if (scene.interaction.type === "choice" && st.selected) {
    st.answeredScenes[scene.scene_id] = st.selected;
  } else if (scene.interaction.type !== "none") {
    st.answeredScenes[scene.scene_id] = true;
  }
  if (!isLastScene(lesson, st)) {
    st.sceneIndex += 1;
    st.stateIndex = 0;
    st.selected = null;
    return { moved: true, wrapped: false };
  }
  return { moved: false, wrapped: true };
}

function back(lesson: Lesson, st: RuntimeState): boolean {
  if (st.stateIndex > 0) { st.stateIndex -= 1; return true; }
  if (st.sceneIndex > 0) {
    st.sceneIndex -= 1;
    st.stateIndex = 0;
    st.selected = null;
    return true;
  }
  return false;
}

function goTo(lesson: Lesson, st: RuntimeState, sceneIndex: number): boolean {
  if (sceneIndex < 0 || sceneIndex >= lesson.scenes.length) return false;
  st.sceneIndex = sceneIndex;
  st.stateIndex = 0;
  st.selected = null;
  return true;
}

function selectOption(st: RuntimeState, key: string): void {
  st.selected = (st.selected === key) ? null : key;
}

function visibleLayers(scene: Scene, st: RuntimeState): SceneLayer[] {
  const vis = scene.states[Math.min(st.stateIndex, scene.states.length - 1)].visible_layers;
  return scene.layers.filter((l) => vis.indexOf(l.id) !== -1)
    .sort((a, b) => a.z - b.z);
}

/** Layers that became visible exactly at this state (for entrance motion). */
function newlyVisible(scene: Scene, st: RuntimeState): string[] {
  if (st.stateIndex === 0) return visibleLayers(scene, st).map((l) => l.id);
  const now: string[] = scene.states[st.stateIndex].visible_layers;
  const prev: string[] = scene.states[st.stateIndex - 1].visible_layers;
  return now.filter((id) => prev.indexOf(id) === -1);
}
