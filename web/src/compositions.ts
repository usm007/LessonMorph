/* Composition families — which component stages a scene.
 * The Python VisualDirector decides `visual.composition` once per scene
 * (semantic representation + deterministic variety). This module only
 * EXECUTES that decision; the fallback map below exists solely so older
 * bundles without visual.composition still stage correctly, and it must
 * match lessonmorph/runtime/visual_director.FAMILY_BY_REPRESENTATION. */

const FALLBACK_FAMILY: { [rep: string]: string } = {
  title: "cinematic_hook",
  roadmap: "synthesis",
  objectives: "hero_concept",
  definition_focus: "hero_concept",
  big_idea: "hero_concept",
  concept_card: "hero_concept",
  key_principle: "hero_concept",
  contrast: "misconception",
  labeled_diagram: "diagram_centered",
  anatomy_map: "split_visual",
  hierarchy: "concept_map",
  cutaway: "full_visual",
  spatial_relationship: "full_visual",
  flow: "process_pathway",
  sequence: "process_pathway",
  pathway: "process_pathway",
  cause_effect: "comparison",
  before_after: "comparison",
  comparison_matrix: "comparison",
  cycle: "cycle",
  equation_focus: "equation_focus",
  worked_calculation: "equation_focus",
  data_table: "data_visualization",
  bar_chart: "data_visualization",
  line_chart: "data_visualization",
  mcq: "question_focus",
  true_false: "question_focus",
  prediction: "question_focus",
  diagnostic_question: "question_focus",
  retrieval: "question_focus",
  practice_problem: "practice_workspace",
  concept_map: "concept_map",
  summary_matrix: "synthesis",
  big_picture: "synthesis",
  exit: "reflection",
};

const FAMILY_COMPONENT: { [fam: string]: string } = {
  cinematic_hook: "HeroScene",
  hero_concept: "HeroConcept",
  full_visual: "FullVisualScene",
  split_visual: "SplitScene",
  diagram_centered: "DiagramScene",
  process_pathway: "ProcessScene",
  cycle: "CycleScene",
  comparison: "ComparisonScene",
  equation_focus: "EquationScene",
  data_visualization: "DataScene",
  question_focus: "QuestionScene",
  answer_reveal: "AnswerScene",
  misconception: "MisconceptionScene",
  practice_workspace: "PracticeScene",
  concept_map: "ConceptMapScene",
  synthesis: "SynthesisScene",
  reflection: "ReflectionScene",
};

function familyOf(scene: Scene): string {
  const v = scene.visual || {};
  if (v.composition && FAMILY_COMPONENT[v.composition]) return v.composition;
  return FALLBACK_FAMILY[scene.representation] || "hero_concept";
}

function componentFor(family: string): string {
  return FAMILY_COMPONENT[family] || "HeroConcept";
}

function sceneVariant(scene: Scene): string {
  const v = scene.visual || {};
  return v.variant || "default";
}

function stageClass(scene: Scene): string {
  return "fam-" + familyOf(scene) + " var-" + sceneVariant(scene);
}
