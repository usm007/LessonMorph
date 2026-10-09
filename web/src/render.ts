/* Scene renderer — executes family composition + semantic type scale.
 * Data-driven only: every string on screen comes from scene.content /
 * scene.visual / scene.assets. No hardcoded lesson content lives here.
 * Layer geometry arrives from the VisualDirector (logical 1280×720 regions);
 * family classes from compositions.ts drive emphasis, order, and treatment.
 * Cards are NOT the default: only answer banners, choice controls, and the
 * misconception correction panel use bordered surfaces (see styles.css). */

function esc(s: string): string {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function el(tag: string, cls: string, html: string): HTMLElement {
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  d.innerHTML = html;
  return d;
}

function place(node: HTMLElement, region: { x: number; y: number; w: number; h: number }): void {
  node.style.left = region.x + "px";
  node.style.top = region.y + "px";
  node.style.width = region.w + "px";
  node.style.height = region.h + "px";
}

/* ---------- family components: 17 stagings, one focal point each ---------- */

function renderFamily(fam: string, scene: Scene, st: RuntimeState, layers: SceneLayer[]): HTMLElement[] {
  const placeAll = (extra?: (node: HTMLElement, layer: SceneLayer) => void): HTMLElement[] =>
    layers.map((layer) => {
      const node = renderLayer(scene, layer, st, fam);
      if (node) {
        place(node, layer.region);
        node.dataset.layer = layer.id;
        if (extra) extra(node, layer);
      }
      return node;
    }).filter((n) => n) as HTMLElement[];

  switch (fam) {
    case "cinematic_hook": { // HeroScene: giant topic, kicker whisper
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "title") node.classList.add("focal-display");
        if (layer.kind === "subtitle") node.classList.add("t-subtitle");
      });
      return [section("hook", nodes)];
    }
    case "hero_concept": { // HeroConcept: term as display type, definition large
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "text") node.classList.add("focal-hero");
      });
      return [section("hero", nodes)];
    }
    case "full_visual":
    case "diagram_centered":
    case "split_visual": { // media-first: diagram/photo owns the eye
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "diagram" || layer.kind === "media") node.classList.add("focal-media");
      });
      return [section("visual", nodes)];
    }
    case "process_pathway":
    case "cycle": { // ProcessScene: numbered flow, steps read as a path
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "list") node.classList.add("steps-flow");
      });
      return [section("flow", nodes)];
    }
    case "comparison": { // ComparisonScene: A vs B with a quiet divider
      const nodes = placeAll();
      if (nodes.length >= 2) {
        const versus = el("div", "versus", "<span>vs</span>");
        const out: HTMLElement[] = [nodes[0], versus].concat(nodes.slice(1));
        return [section("compare", out)];
      }
      return [section("compare", nodes)];
    }
    case "equation_focus": { // EquationScene: monument equation
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "equation") node.classList.add("focal-equation");
      });
      return [section("equation", nodes)];
    }
    case "data_visualization": { // DataScene: table/chart at reading scale
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "table") node.classList.add("focal-data");
      });
      return [section("data", nodes)];
    }
    case "question_focus": { // QuestionScene: the question IS the slide
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "prompt") node.classList.add("focal-question");
        if (layer.kind === "options") node.classList.add("choices-lg");
      });
      return [section("question", nodes)];
    }
    case "answer_reveal": { // AnswerScene: verdict banner, rest recedes
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "answer") node.classList.add("answer-banner");
      });
      return [section("answer", nodes)];
    }
    case "misconception": { // MisconceptionScene: myth struck, correction lit
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "text") node.classList.add("myth-correction");
      });
      return [section("myth", nodes)];
    }
    case "practice_workspace": { // PracticeScene: prompt + generous working room
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "note") node.classList.add("workspace");
      });
      return [section("practice", nodes)];
    }
    case "concept_map": { // ConceptMapScene: hub + satellites
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "diagram") node.classList.add("focal-media");
      });
      return [section("map", nodes)];
    }
    case "synthesis": { // SynthesisScene: takeaway band
      const nodes = placeAll((node, layer) => {
        if (layer.kind === "list" || layer.kind === "table") node.classList.add("takeaways");
      });
      return [section("synth", nodes)];
    }
    case "reflection": { // ReflectionScene: two quiet prompts
      const nodes = placeAll((node, layer) => node.classList.add("reflect-card"));
      return [section("reflect", nodes)];
    }
    default:
      return [section("hero", placeAll())];
  }
}

function section(kind: string, nodes: HTMLElement[]): HTMLElement {
  const s = document.createElement("div");
  s.className = "scene-section sec-" + kind;
  for (const n of nodes) s.appendChild(n);
  return s;
}

function renderScene(stage: HTMLElement, lesson: Lesson, st: RuntimeState): void {
  const scene = currentScene(lesson, st);
  stage.innerHTML = "";
  const fam = familyOf(scene);
  const body = document.createElement("div");
  body.className = "scene-body " + stageClass(scene);
  body.dataset.composition = fam;
  body.dataset.component = componentFor(fam);
  const layers = visibleLayers(scene, st);
  for (const node of renderFamily(fam, scene, st, layers)) body.appendChild(node);
  stage.appendChild(body);
  stage.appendChild(renderChrome(lesson, st));
  fitHeadlines(stage);
  fitBody(stage);
}

/* Deterministic auto-fit: long titles/prompts shrink within their region
 * (never below classroom minimums) instead of spilling over the scene. */
function fitHeadlines(stage: HTMLElement): void {
  const heads = stage.querySelectorAll(".lyr-title, .lyr-prompt");
  for (let i = 0; i < heads.length; i++) {
    const box = heads[i] as HTMLElement;
    const text = box.querySelector("h1, p") as HTMLElement;
    if (!text) continue;
    let fs = parseFloat(getComputedStyle(text).fontSize) || 44;
    const min = box.classList.contains("lyr-prompt") ? 24 : 28;
    let guard = 0;
    while (box.scrollHeight > box.clientHeight + 2 && fs > min && guard++ < 20) {
      fs -= 2;
      text.style.fontSize = fs + "px";
    }
  }
}

/* Body auto-fit: prose/tables/options shrink toward readability floors,
 * then scale as one piece (never below 62%) rather than spill. Anything
 * still spilling afterwards is a scene-split case upstream. */
function fitBody(stage: HTMLElement): void {
  const bodies = stage.querySelectorAll(".lyr-text, .lyr-list, .lyr-note, .lyr-options, .lyr-data, .lyr-equation, .lyr-diagram");
  for (let i = 0; i < bodies.length; i++) {
    const box = bodies[i] as HTMLElement;
    let fs = parseFloat(getComputedStyle(box).fontSize) || 20;
    const min = box.classList.contains("lyr-note") ? 14 : 16;
    let guard = 0;
    while (box.scrollHeight > box.clientHeight + 2 && fs > min && guard++ < 12) {
      fs -= 1;
      box.style.fontSize = fs + "px";
    }
    if (box.scrollHeight > box.clientHeight + 2) {
      const s = box.clientHeight / box.scrollHeight;
      if (s >= 0.62) {
        box.style.transform = "scale(" + s.toFixed(3) + ")";
        box.style.transformOrigin = box.classList.contains("lyr-equation")
          ? "top center" : "top left";
      }
    }
  }
}

function renderLayer(scene: Scene, layer: SceneLayer, st: RuntimeState, fam?: string): HTMLElement | null {
  const c = scene.content;
  switch (layer.kind) {
    case "title":
      return el("div", "lyr-title t-title", "<h1>" + esc(c.title || "") + "</h1>");
    case "kicker":
      return c.kicker ? el("div", "lyr-kicker t-label", esc(c.kicker)) : null;
    case "prompt": {
      const promptText = c.prompt || ((c.items && c.items[0]) || "");
      return el("div", "lyr-prompt t-question", "<p>" + esc(promptText) + "</p>");
    }
    case "text":
      if (scene.representation === "contrast") return renderContrastModel(scene, layer);
      return el("div", "lyr-text t-body", renderTextBody(scene));
    case "list":
      return renderSemanticList(scene, layer, st);
    case "options":
      return renderOptions(scene, st);
    case "table":
      return renderDataNode(scene);
    case "equation":
      return renderEquationNode(scene);
    case "diagram":
      return renderDiagramNode(scene, st);
    case "media":
      return renderMediaNode(scene);
    case "answer":
      return renderAnswer(scene, st);
    case "note":
      if (scene.representation === "practice_problem") return renderPracticeNote(scene);
      if (["labeled_diagram", "anatomy_map", "cutaway", "spatial_relationship"].indexOf(scene.representation) !== -1) {
        const legend = renderDiagramLegend(scene);
        const cap = scene.content.caption || noteText(scene);
        if (!legend && !cap) return el("div", "lyr-note t-caption", "");
        const wrap = document.createElement("div");
        wrap.className = "lyr-note t-caption";
        wrap.innerHTML = legend + (cap ? "<p>" + esc(cap) + "</p>" : "");
        return wrap;
      }
      return el("div", "lyr-note t-caption", "<p>" + esc(noteText(scene)) + "</p>");
    case "subtitle":
      return el("div", "lyr-subtitle t-subtitle", "<p>" + esc(c.topic || c.unit || "") + "</p>");
    default:
      return null;
  }
}

/* Wrong/correct models: the two text layers of a contrast scene each stage
 * ONE full-width model — the zone layout carries the relationship. */
function renderContrastModel(scene: Scene, layer: SceneLayer): HTMLElement {
  const c = scene.content;
  const first = /1$/.test(layer.id) || layer.id === "text";
  const html = first
    ? engSoloModel("wrong", "Common idea", c.wrong_idea || "", c.why_wrong || "")
    : engSoloModel("right", "Correct model", c.correct_idea || "", c.correct_reasoning || "");
  const d = document.createElement("div");
  d.className = "lyr-text t-body";
  d.innerHTML = html;
  return d;
}

function edgeKindForTask(task: string): string {
  const t = String(task || "").toLowerCase();
  if (/sequence|order|steps|chronolog/.test(t)) return "sequence";
  if (/mechanism|process|caus|drives|leads/.test(t)) return "causal";
  if (/depend|prereq|require/.test(t)) return "dependency";
  return "plain";
}

/* Content type determines visual form — never a default text box. */
function renderSemanticList(scene: Scene, layer: SceneLayer, st: RuntimeState): HTMLElement | null {
  const c = scene.content;
  const rep = scene.representation;
  const wrap = document.createElement("div");
  wrap.className = "lyr-list t-body";
  const active = st.stateIndex;
  if (rep === "worked_calculation" && c.steps) {
    wrap.innerHTML = engPathway(c.steps, { activeIndex: active })
      + (c.verify ? "<p class=\"verify\">" + esc(c.verify) + "</p>" : "");
    return wrap;
  }
  const pts: string[] = c.points || c.takeaways || [];
  if (rep === "flow" || rep === "sequence" || rep === "pathway") {
    if (!pts.length) return null;
    wrap.innerHTML = engPathway(pts, { activeIndex: active });
    return wrap;
  }
  if (rep === "cause_effect") {
    if (!pts.length) return null;
    wrap.innerHTML = pts.length === 3 ? engCauseMechanismEffect(pts) : engPathway(pts, { activeIndex: active });
    return wrap;
  }
  if (rep === "concept_map" || rep === "hierarchy") {
    if (!pts.length) return null;
    wrap.innerHTML = engConceptMap(c.title || "", pts, edgeKindForTask(scene.task), active);
    wrap.classList.add("map-layer");
    return wrap;
  }
  if (rep === "before_after") {
    if (!pts.length) return null;
    const half = Math.ceil(pts.length / 2);
    const mine = (/1$/.test(layer.id) || layer.id === "list")
      ? pts.slice(0, half) : pts.slice(half);
    wrap.innerHTML = "<ul>" + mine.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
    return wrap;
  }
  wrap.innerHTML = renderListBody(scene);
  if (!wrap.textContent || !wrap.textContent.trim()) return null;
  return wrap;
}

function renderTextBody(scene: Scene): string {
  const c = scene.content;
  if (c.definition) {
    let h = "<p class=\"term t-hero\">" + esc(c.term || "") + "</p><p class=\"t-body-large\">" + esc(c.definition) + "</p>";
    if (c.detail && c.detail !== c.definition) h += "<p class=\"source-wording t-caption\">Source wording: " + esc(c.detail) + "</p>";
    return h;
  }
  if (c.problem) {
    let h = "<p class=\"problem t-body-large\">" + esc(c.problem) + "</p>";
    if (c.givens && c.givens.length) h += "<p class=\"givens t-caption\">" + esc(c.givens.join(" · ")) + "</p>";
    return h;
  }
  if (c.caption) return "<p>" + esc(c.caption) + "</p>";
  if (c.items && c.items.length) return "<p>" + esc(c.items[0]) + "</p>";
  return "";
}

function renderListBody(scene: Scene): string {
  const c = scene.content;
  const rep = scene.representation;
  if (rep === "worked_calculation" && c.steps) {
    return "<ol class=\"steps\">" + c.steps.map((s: string) => "<li>" + esc(s) + "</li>").join("") + "</ol>"
      + (c.verify ? "<p class=\"verify\">" + esc(c.verify) + "</p>" : "");
  }
  if ((rep === "objectives" || rep === "roadmap") && c.objectives) {
    return "<ul>" + c.objectives.map((s: string) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
  }
  if (rep === "exit") {
    return "<p>" + esc(c.prompt_1 || "") + "</p><p>" + esc(c.prompt_2 || "") + "</p>";
  }
  const pts: string[] = c.points || c.takeaways || [];
  if (!pts.length) return "";
  return "<ul>" + pts.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
}

function renderOptions(scene: Scene, st: RuntimeState): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "lyr-options";
  const opts: { [k: string]: string } = scene.content.options || {};
  const keys = Object.keys(opts).sort();
  const answered = scene.scene_id in st.answeredScenes;
  if (keys.length >= 4) wrap.classList.add("opts-n4");
  if (!answered && !st.selected) {
    const think = document.createElement("p");
    think.className = "think-cue inline t-body";
    think.innerHTML = "<strong>Think first · 30 seconds.</strong> Commit, then continue.";
    wrap.appendChild(think);
  }
  for (const k of keys) {
    const b = document.createElement("button");
    b.className = "opt t-body";
    b.dataset.key = k;
    b.innerHTML = "<span class=\"opt-key\">" + esc(k) + "</span><span>" + esc(opts[k]) + "</span>";
    if (st.selected === k) b.classList.add("selected");
    if (answered) {
      b.disabled = true;
      if (k === scene.interaction.correct) b.classList.add("correct");
      else if (k === st.answeredScenes[scene.scene_id]) b.classList.add("incorrect");
    }
    b.addEventListener("click", (ev) => { ev.stopPropagation(); onSelectOption(k); });
    wrap.appendChild(b);
  }
  if (!keys.length) {
    const p = document.createElement("p");
    p.className = "think-cue t-body";
    p.textContent = scene.interaction.type === "open"
      ? "Work it through, then continue."
      : "Think, then continue to check.";
    wrap.appendChild(p);
  }
  return wrap;
}

function renderDataNode(scene: Scene): HTMLElement | null {
  const v = scene.visual || {};
  const cols: string[] = v.columns || [];
  if (!cols.length) return null;
  const wrap = document.createElement("div");
  wrap.className = "lyr-data data-kind-" + scene.representation;
  if (scene.representation === "comparison_matrix" || scene.representation === "summary_matrix") {
    const rows: string[][] = (v.rows || []).map((r: string[] | { [k: string]: string }) =>
      Array.isArray(r) ? r.map((c) => String(c == null ? "" : c)) : cols.map((c) => String(r[c] == null ? "" : r[c])));
    wrap.dataset.datakind = "comparison";
    wrap.innerHTML = engComparison(cols, rows);
    return wrap;
  }
  const d = engData(cols, v.rows || [], scene.representation);
  if (scene.content.table_title) {
    const cap = document.createElement("p");
    cap.className = "t-caption data-title";
    cap.textContent = scene.content.table_title;
    wrap.appendChild(cap);
  }
  const fig = document.createElement("div");
  fig.innerHTML = d.html;
  wrap.appendChild(fig);
  return wrap;
}

function renderEquationNode(scene: Scene): HTMLElement | null {
  const eq = (scene.visual || {}).equation;
  if (!eq || (!eq.lhs && !eq.rhs)) return null;
  const wrap = document.createElement("div");
  wrap.className = "lyr-equation";
  wrap.innerHTML = engEquation(eq)
    + (scene.content.context ? "<p class=\"context t-caption\">" + esc(scene.content.context) + "</p>" : "");
  return wrap;
}

function renderDiagramNode(scene: Scene, st: RuntimeState): HTMLElement | null {
  const v = scene.visual || {};
  const rep = scene.representation;
  const pts: string[] = scene.content.points || [];
  if (rep === "cycle") {
    if (!pts.length) return null;
    const wrap = document.createElement("div");
    wrap.className = "lyr-diagram";
    wrap.innerHTML = engCycle(pts, st.stateIndex);
    return wrap;
  }
  if (rep === "pathway" || rep === "flow" || rep === "sequence") {
    if (!pts.length) return null;
    const wrap = document.createElement("div");
    wrap.className = "lyr-diagram";
    wrap.innerHTML = engPathway(pts, { activeIndex: st.stateIndex });
    return wrap;
  }
  const labels = v.labels || v.structure || [];
  if (!labels.length && !scene.assets.length) return null;
  const wrap = document.createElement("div");
  wrap.className = "lyr-diagram";
  const active = Math.min(st.stateIndex, Math.max(0, labels.length - 1));
  const d = engDiagram(v, labels.length ? active : 999);
  wrap.innerHTML = d.svg;
  wrap.dataset.legend = d.legend;
  return wrap;
}

function renderDiagramLegend(scene: Scene): string {
  const v = scene.visual || {};
  const labels = v.labels || v.structure || [];
  if (!labels.length) return "";
  const d = engDiagram(v, 999);
  return d.legend;
}

function renderMediaNode(scene: Scene): HTMLElement | null {
  if (!scene.assets.length) return null;
  const v = scene.visual || {};
  const layouts = { full_visual: "bleed", split_visual: "split", cinematic_hook: "hero" } as { [k: string]: string };
  const layout = v.image_layout || layouts[v.composition] || "hero";
  const wrap = document.createElement("div");
  wrap.className = "lyr-mediawrap";
  wrap.innerHTML = engImage(scene.assets, scene.content.caption || "", layout, scene.content.kicker || "");
  if (!wrap.querySelector("img")) return null;
  return wrap;
}

function renderPracticeNote(scene: Scene): HTMLElement {
  const sc = scene.content.scaffold || {};
  const wrap = document.createElement("div");
  wrap.className = "lyr-note t-caption";
  if (sc.columns && sc.columns.length >= 2) {
    const heads = sc.columns.map((c: string) => String(c));
    let h = "<table class=\"cmp-matrix workspace\"><thead><tr>";
    heads.forEach((c: string) => { h += "<th>" + esc(c) + "</th>"; });
    h += "</tr></thead><tbody><tr>";
    heads.forEach(() => { h += "<td class=\"blank\"></td>"; });
    h += "</tr></tbody></table>";
    wrap.innerHTML = h + (sc.note ? "<p>" + esc(sc.note) + "</p>" : "");
    return wrap;
  }
  wrap.innerHTML = "<p>" + esc(noteText(scene)) + "</p>";
  return wrap;
}

function renderAnswer(scene: Scene, st: RuntimeState): HTMLElement {
  const inter = scene.interaction;
  let verdict = "";
  if (inter.type === "choice") {
    const chosen = st.selected != null ? st.selected : st.answeredScenes[scene.scene_id];
    const ok = String(chosen) === String(inter.correct);
    verdict = "<p class=\"verdict " + (ok ? "ok" : "miss") + "\">" + (ok ? "Correct" : "Not quite") + "</p>";
  }
  return el("div", "lyr-answer t-answer", verdict + "<p>" + esc(inter.explanation || "") + "</p>");
}

function noteText(scene: Scene): string {
  const c = scene.content;
  const sc = c.scaffold || {};
  if (sc.note) return sc.note;
  if (sc.columns) return "Complete the comparison from the lesson.";
  return c.caption || "";
}

function renderChrome(lesson: Lesson, st: RuntimeState): HTMLElement {
  const bar = document.createElement("div");
  bar.id = "progress";
  const pct = lesson.scenes.length <= 1 ? 100
    : Math.round((st.sceneIndex / (lesson.scenes.length - 1)) * 100);
  bar.innerHTML = "<div class=\"lesson-tag t-label\">" + esc(lesson.title || "") + "</div>"
    + "<div class=\"track\"><div class=\"fill\" style=\"width:" + pct + "%\"></div></div>"
    + "<div class=\"count t-label\">" + (st.sceneIndex + 1) + " / " + lesson.scenes.length + "</div>"
    + "<button id=\"fs-btn\" title=\"Fullscreen\">⛶</button>";
  const btn = bar.querySelector("#fs-btn");
  if (btn) btn.addEventListener("click", (ev) => { ev.stopPropagation(); toggleFullscreen(); });
  return bar;
}
