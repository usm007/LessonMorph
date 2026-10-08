/* Lesson Runtime Model (mirrors lessonmorph/runtime/lesson_model.py).
 * Student-safe only: this file must never reference internal fields. */

interface Region { x: number; y: number; w: number; h: number; }

interface SceneLayer {
  id: string;
  kind: string; // title|kicker|text|list|diagram|table|equation|options|prompt|media|answer|note
  region: Region;
  content_ref: string;
  reveal_at: number;
  z: number;
}

interface SceneState { id: string; label: string; visible_layers: string[]; }

interface MotionStep { step: number; effect: string; duration_ms: number; }
interface SceneMotion { enter_transition: string; advance: MotionStep[]; }

interface SceneInteraction {
  type: string; // none|choice|self_check|open
  options: string[];
  correct: string; // locked key: the runtime CHECKS, never solves
  explanation: string;
}

interface SceneContent { [key: string]: any; }
interface SceneVisual { [key: string]: any; }

interface Scene {
  scene_id: string;
  representation: string;
  task: string;
  states: SceneState[];
  layers: SceneLayer[];
  content: SceneContent;
  visual: SceneVisual;
  assets: string[];
  interaction: SceneInteraction;
  motion: SceneMotion;
  estimated_minutes: number;
}

interface Lesson {
  lesson_id: string;
  title: string;
  canvas: { width: number; height: number };
  scenes: Scene[];
  version: number;
}
