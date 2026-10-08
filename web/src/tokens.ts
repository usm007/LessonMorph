/* LessonMorph student design tokens — the single source of truth.
 * Every value here mirrors a :root custom property in styles.css
 * (same names, same numbers). Change a token here AND in styles.css.
 * Nothing else in web/src may hardcode sizes, colors, spacing, or motion. */

const TOKENS = {
  canvas: { width: 1280, height: 720 },
  safe: { margin: 64, contentWidth: 1152 },
  grid: { unit: 8 },
  spacing: {
    xs: 8, sm: 16, md: 24, lg: 32, xl: 48, xxl: 64, xxxl: 96,
    gutter: 24, sectionGap: 48,
  },
  type: {
    display:  { size: 76, weight: 800, lineHeight: 1.05 },
    hero:     { size: 56, weight: 800, lineHeight: 1.1 },
    title:    { size: 44, weight: 700, lineHeight: 1.15 },
    subtitle: { size: 22, weight: 400, lineHeight: 1.4 },
    body:        { size: 21, weight: 400, lineHeight: 1.55 },
    bodyLarge:   { size: 24, weight: 400, lineHeight: 1.5 },
    label:    { size: 13, weight: 700, lineHeight: 1.4 },
    caption:  { size: 15, weight: 400, lineHeight: 1.5 },
    question: { size: 32, weight: 600, lineHeight: 1.35 },
    answer:   { size: 22, weight: 400, lineHeight: 1.5 },
    equation: { size: 64, weight: 600, lineHeight: 1.2 },
    data:     { size: 18, weight: 400, lineHeight: 1.45 },
  },
  color: {
    ink: "#1a2332",
    inkSoft: "#3c4a61",
    inkFaint: "#5b6b82",
    paper: "#fafafa",
    paperWarm: "#f4f1ea",
    paperDark: "#0b0e14",
    accent: "#2f6fed",
    accentInk: "#1d4fc4",
    success: "#1c7a4d",
    successWash: "#e9f6ef",
    danger: "#c0362c",
    dangerWash: "#fdeeee",
    warn: "#9a6a00",
    warnWash: "#fdf3dd",
    hairline: "#d7dee8",
    washBlue: "#eef4ff",
  },
  radius: { sm: 6, md: 10, lg: 12, pill: 999 },
  shadow: {
    // Restraint: one soft stage shadow only. No per-card drop shadows.
    stage: "0 0 60px rgba(0,0,0,.55)",
    lift: "0 2px 10px rgba(26,35,50,.10)",
  },
  motion: {
    fast: 180, normal: 250, slow: 400, process: 600,
    easing: "ease-out",
  },
  families: [
    "cinematic_hook", "hero_concept", "full_visual", "split_visual",
    "diagram_centered", "process_pathway", "cycle", "comparison",
    "equation_focus", "data_visualization", "question_focus",
    "answer_reveal", "misconception", "practice_workspace",
    "concept_map", "synthesis", "reflection",
  ],
};
