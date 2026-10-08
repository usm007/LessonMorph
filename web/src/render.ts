/* Scene renderer. Executes the scene composition; never reinterprets meaning.
 * Renders only student-safe content fields. Internal metadata is not present
 * in the bundle and nothing here reads it. */

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

function renderScene(stage: HTMLElement, lesson: Lesson, st: RuntimeState): void {
  const scene = currentScene(lesson, st);
  stage.innerHTML = "";
  const layers = visibleLayers(scene, st);
  for (const layer of layers) {
    const node = renderLayer(scene, layer, st);
    if (node) { place(node, layer.region); node.dataset.layer = layer.id; stage.appendChild(node); }
  }
  stage.appendChild(renderChrome(lesson, st));
}

function renderLayer(scene: Scene, layer: SceneLayer, st: RuntimeState): HTMLElement | null {
  const c = scene.content;
  switch (layer.kind) {
    case "title":
      return el("div", "lyr-title", "<h1>" + esc(c.title || "") + "</h1>");
    case "kicker":
      return c.kicker ? el("div", "lyr-kicker", esc(c.kicker)) : null;
    case "prompt":
      return el("div", "lyr-prompt", "<p>" + esc(c.prompt || "") + "</p>");
    case "text":
      return el("div", "lyr-text", renderTextBody(scene));
    case "list":
      return el("div", "lyr-list", renderListBody(scene));
    case "options":
      return renderOptions(scene, st);
    case "table":
      return renderTable(scene);
    case "equation":
      return renderEquation(scene);
    case "diagram":
      return renderDiagram(scene);
    case "media":
      return renderMedia(scene);
    case "answer":
      return renderAnswer(scene, st);
    case "note":
      return el("div", "lyr-note", "<p>" + esc(noteText(scene)) + "</p>");
    case "subtitle":
      return el("div", "lyr-subtitle", "<p>" + esc(c.topic || c.unit || "") + "</p>");
    default:
      return null;
  }
}

function renderTextBody(scene: Scene): string {
  const c = scene.content;
  if (c.definition) return "<p class=\"term\">" + esc(c.term || "") + "</p><p>" + esc(c.definition) + "</p>";
  if (c.problem) {
    let h = "<p class=\"problem\">" + esc(c.problem) + "</p>";
    if (c.givens && c.givens.length) h += "<p class=\"givens\">" + esc(c.givens.join(" · ")) + "</p>";
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
  if (rep === "contrast") {
    return "<div class=\"contrast\"><p><strong>Common idea:</strong> " + esc(c.wrong_idea || "") + "</p>"
      + "<p><strong>Correction:</strong> " + esc(c.correct_idea || "") + "</p></div>";
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
  for (const k of keys) {
    const b = document.createElement("button");
    b.className = "opt";
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
    p.className = "think-cue";
    p.textContent = scene.interaction.type === "open"
      ? "Work it through, then continue."
      : "Think, then continue to check.";
    wrap.appendChild(p);
  }
  return wrap;
}

function renderTable(scene: Scene): HTMLElement {
  const v = scene.visual;
  const cols: string[] = v.columns || [];
  const rows: any[] = v.rows || [];
  let h = "";
  if (scene.content.table_title) h += "<caption>" + esc(scene.content.table_title) + "</caption>";
  h += "<thead><tr>" + cols.map((c) => "<th>" + esc(c) + "</th>").join("") + "</tr></thead><tbody>";
  for (const r of rows) {
    const cells: string[] = Array.isArray(r) ? r : cols.map((c) => r[c]);
    h += "<tr>" + cells.map((c) => "<td>" + esc(c) + "</td>").join("") + "</tr>";
  }
  const t = document.createElement("table");
  t.className = "lyr-table";
  t.innerHTML = h + "</tbody>";
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  wrap.appendChild(t);
  return wrap;
}

function renderEquation(scene: Scene): HTMLElement {
  const eq = scene.visual.equation || {};
  const side = (terms: any[]) => (terms || []).map((t) =>
    esc(((t.coefficient ? t.coefficient + " " : "") + (t.species || "")).trim())).join(" + ");
  let h = "<div class=\"equation\">" + side(eq.lhs) + " " + esc(eq.arrow || "→") + " " + side(eq.rhs) + "</div>";
  if (eq.energy) h += "<div class=\"energy\">+ [" + esc(eq.energy) + "]</div>";
  const notes: string[] = [];
  for (const t of (eq.lhs || []).concat(eq.rhs || [])) {
    if (t && t.note) notes.push("<li><strong>" + esc(t.species) + ":</strong> " + esc(t.note) + "</li>");
  }
  if (notes.length) h += "<ul class=\"legend\">" + notes.join("") + "</ul>";
  if (scene.content.context) h += "<p class=\"context\">" + esc(scene.content.context) + "</p>";
  return el("div", "lyr-equation", h);
}

function renderDiagram(scene: Scene): HTMLElement {
  const v = scene.visual;
  const labels: any[] = v.labels || [];
  const structure: string[] = v.structure || [];
  const W = 1088, H = 440;
  let svg = "";
  const cx = W / 2, cy = H / 2;
  svg += "<ellipse cx=\"" + cx + "\" cy=\"" + cy + "\" rx=\"150\" ry=\"110\" class=\"dg-hub\"/>";
  svg += "<text x=\"" + cx + "\" y=\"" + cy + "\" class=\"dg-hub-label\">" + esc(v.subject || "") + "</text>";
  const items = labels.length ? labels : structure.map((s) => ({ name: s, explanation: "" }));
  items.slice(0, 6).forEach((item: any, i: number) => {
    const left = i % 2 === 0;
    const lx = left ? 170 : W - 170;
    const ly = 70 + Math.floor(i / 2) * 150;
    const tx = left ? lx + 130 : lx - 130;
    svg += "<line x1=\"" + lx + "\" y1=\"" + ly + "\" x2=\"" + tx + "\" y2=\"" + cy + "\" class=\"dg-leader\"/>";
    svg += "<rect x=\"" + (lx - 130) + "\" y=\"" + (ly - 34) + "\" width=\"260\" height=\"68\" rx=\"8\" class=\"dg-card\"/>";
    svg += "<text x=\"" + lx + "\" y=\"" + (ly - 8) + "\" class=\"dg-name\">" + esc(String(item.name || "").slice(0, 42)) + "</text>";
    if (item.explanation) svg += "<text x=\"" + lx + "\" y=\"" + (ly + 14) + "\" class=\"dg-desc\">" + esc(String(item.explanation).slice(0, 60)) + "</text>";
  });
  const wrap = document.createElement("div");
  wrap.className = "lyr-diagram";
  wrap.innerHTML = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\">" + svg + "</svg>";
  return wrap;
}

function renderMedia(scene: Scene): HTMLElement | null {
  if (!scene.assets.length) return null;
  const img = document.createElement("img");
  img.className = "lyr-media";
  img.src = scene.assets[0];
  img.alt = "";
  const wrap = document.createElement("div");
  wrap.className = "media-wrap";
  wrap.appendChild(img);
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
  return el("div", "lyr-answer", verdict + "<p>" + esc(inter.explanation || "") + "</p>");
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
  bar.innerHTML = "<div class=\"track\"><div class=\"fill\" style=\"width:" + pct + "%\"></div></div>"
    + "<div class=\"count\">" + (st.sceneIndex + 1) + " / " + lesson.scenes.length + "</div>"
    + "<button id=\"fs-btn\" title=\"Fullscreen\">⛶</button>";
  const btn = bar.querySelector("#fs-btn");
  if (btn) btn.addEventListener("click", (ev) => { ev.stopPropagation(); toggleFullscreen(); });
  return bar;
}
