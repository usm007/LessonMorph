"use strict";
/* Lesson Runtime Model (mirrors lessonmorph/runtime/lesson_model.py).
 * Student-safe only: this file must never reference internal fields. */

"use strict";
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
        display: { size: 76, weight: 800, lineHeight: 1.05 },
        hero: { size: 56, weight: 800, lineHeight: 1.1 },
        title: { size: 44, weight: 700, lineHeight: 1.15 },
        subtitle: { size: 22, weight: 400, lineHeight: 1.4 },
        body: { size: 21, weight: 400, lineHeight: 1.55 },
        bodyLarge: { size: 24, weight: 400, lineHeight: 1.5 },
        label: { size: 13, weight: 700, lineHeight: 1.4 },
        caption: { size: 15, weight: 400, lineHeight: 1.5 },
        question: { size: 32, weight: 600, lineHeight: 1.35 },
        answer: { size: 22, weight: 400, lineHeight: 1.5 },
        equation: { size: 64, weight: 600, lineHeight: 1.2 },
        data: { size: 18, weight: 400, lineHeight: 1.45 },
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

"use strict";
/* Composition families — which component stages a scene.
 * The Python VisualDirector decides `visual.composition` once per scene
 * (semantic representation + deterministic variety). This module only
 * EXECUTES that decision; the fallback map below exists solely so older
 * bundles without visual.composition still stage correctly, and it must
 * match lessonmorph/runtime/visual_director.FAMILY_BY_REPRESENTATION. */
const FALLBACK_FAMILY = {
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
const FAMILY_COMPONENT = {
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
function familyOf(scene) {
    const v = scene.visual || {};
    if (v.composition && FAMILY_COMPONENT[v.composition])
        return v.composition;
    return FALLBACK_FAMILY[scene.representation] || "hero_concept";
}
function componentFor(family) {
    return FAMILY_COMPONENT[family] || "HeroConcept";
}
function sceneVariant(scene) {
    const v = scene.visual || {};
    return v.variant || "default";
}
function stageClass(scene) {
    return "fam-" + familyOf(scene) + " var-" + sceneVariant(scene);
}

"use strict";
/* Scientific visualization engines — pure string builders, no DOM, no imports.
 * Every builder consumes semantic scene data (labels, steps, terms, rows,
 * assets) and returns markup. No hardcoded lesson content anywhere here:
 * all words on screen come from the arguments. Concatenated into runtime.js
 * AFTER types/tokens/compositions (see build/bundle.cjs); keep names global
 * and collision-free (eng* prefix). Also evaluated standalone by
 * build/engines.test.cjs — so no document/window access at top level. */
function engEsc(s) {
    return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function engShort(s, n) {
    const t = String(s == null ? "" : s).trim();
    return t.length > n ? t.slice(0, n - 1) + "…" : t;
}
/* Accessible name for a figure: first element of an SVG is its <title>,
 * so screen readers announce what sighted students see. Text always comes
 * from scene data, never invented. */
function engSvgTitle(text) {
    const t = String(text == null ? "" : text).trim();
    return t ? "<title>" + engEsc(engShort(t, 90)) + "</title>" : "";
}
/* Chemical/math formatter: unicode sub/superscripts pass through; ASCII
 * trailing digits after letters become subscripts (CO2 → CO₂), ^x becomes
 * superscript, a/b (no spaces) becomes a stacked fraction. */
const ENG_SUB = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋",
};
const ENG_SUP = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "n": "ⁿ",
};
function engChem(s) {
    let t = String(s == null ? "" : s);
    t = t.replace(/\^([0-9+\-n]+)/g, (m, g) => g.split("").map((c) => ENG_SUP[c] || c).join(""));
    t = t.replace(/([A-Za-z)⟩])([0-9]{1,2}(?![0-9]))/g, (m, a, b) => a + b.split("").map((c) => ENG_SUB[c] || c).join(""));
    return engEsc(t);
}
function engFrac(term) {
    const m = String(term).match(/^([^/\s]+)\/([^/\s]+)$/);
    if (!m)
        return engChem(term);
    return "<span class=\"frac\"><span class=\"num\">" + engChem(m[1]) +
        "</span><span class=\"den\">" + engChem(m[2]) + "</span></span>";
}
/* ---------------- scientific diagram engine ----------------
 * Zones are real objects: membrane bands, disc stacks, fluid compartments.
 * Each label binds to a region id; leaders connect chip → anchor. */
function engZoneKind(name) {
    const t = String(name || "").toLowerCase();
    if (/(membrane|envelope|wall|barrier|bilayer)/.test(t))
        return "membrane";
    if (/(lumen|matrix|stroma|fluid|interior|cytoplasm|nucleoplasm)/.test(t))
        return "fluid";
    if (/(thylakoid|grana|stack|disc|discs|cristae)/.test(t))
        return "stack";
    return "compartment";
}
function engLabelName(label) {
    return typeof label === "string" ? label : String((label && label.name) || "");
}
function engLabelNote(label) {
    return typeof label === "string" ? "" : String((label && label.explanation) || "");
}
function engDiagram(v, activeIndex) {
    const W = 1088, H = 440;
    const labels = v.labels && v.labels.length ? v.labels
        : (v.structure || []).map((s) => s);
    const n = Math.max(1, Math.min(6, labels.length));
    const top = 78, zh = H - top - 14, gap = 16;
    const zw = (W - 48 - gap * (n - 1)) / n;
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\">";
    svg += engSvgTitle(v.subject || engLabelName(labels[0] || ""));
    svg += "<rect x=\"8\" y=\"64\" width=\"" + (W - 16) + "\" height=\"" + (H - 72) + "\" rx=\"14\" class=\"dg-boundary\"/>";
    if (v.subject)
        svg += "<text x=\"28\" y=\"52\" class=\"dg-subject\">" + engEsc(engShort(v.subject, 48)) + "</text>";
    let legend = "";
    for (let i = 0; i < n; i++) {
        const name = engLabelName(labels[i] || "");
        const note = engLabelNote(labels[i] || "");
        const kind = engZoneKind(name);
        const x = 24 + i * (zw + gap);
        const cx = x + zw / 2;
        const state = i < activeIndex ? " lit" : (i === activeIndex ? " active" : " dimmed");
        let zone = "";
        if (kind === "membrane") {
            zone = "<line x1=\"" + x + "\" y1=\"" + (top + 40) + "\" x2=\"" + (x + zw) + "\" y2=\"" + (top + 40) + "\" class=\"dg-membrane\"/>"
                + "<line x1=\"" + x + "\" y1=\"" + (top + 52) + "\" x2=\"" + (x + zw) + "\" y2=\"" + (top + 52) + "\" class=\"dg-membrane\"/>";
        }
        else if (kind === "stack") {
            for (let d = 0; d < 4; d++) {
                const dy = top + 120 + d * 62;
                zone += "<ellipse cx=\"" + cx + "\" cy=\"" + dy + "\" rx=\"" + (zw / 2 - 14) + "\" ry=\"22\" class=\"dg-disc\"/>";
            }
        }
        else if (kind === "fluid") {
            zone = "<rect x=\"" + x + "\" y=\"" + top + "\" width=\"" + zw + "\" height=\"" + zh + "\" rx=\"10\" class=\"dg-fluid\"/>";
            for (let p = 0; p < 5; p++) {
                const px = x + 24 + ((p * 53) % Math.max(48, zw - 48));
                const py = top + 40 + ((p * 97) % Math.max(60, zh - 80));
                zone += "<circle cx=\"" + px + "\" cy=\"" + py + "\" r=\"5\" class=\"dg-particle\"/>";
            }
        }
        else {
            zone = "<rect x=\"" + x + "\" y=\"" + top + "\" width=\"" + zw + "\" height=\"" + zh + "\" rx=\"10\" class=\"dg-zone\"/>";
        }
        const anchorY = kind === "membrane" ? top + 46 : top + 30;
        svg += "<g id=\"region-" + i + "\" class=\"dg-region" + state + "\" data-region=\"" + i + "\">" + zone
            + "<circle cx=\"" + cx + "\" cy=\"" + anchorY + "\" r=\"11\" class=\"dg-marker\"/>"
            + "<text x=\"" + cx + "\" y=\"" + (anchorY + 4.5) + "\" class=\"dg-marker-n\">" + (i + 1) + "</text></g>";
        svg += "<g id=\"label-" + i + "\" class=\"dg-chip" + state + "\">"
            + "<line x1=\"" + cx + "\" y1=\"58\" x2=\"" + cx + "\" y2=\"" + anchorY + "\" class=\"dg-leader\"/>"
            + "<rect x=\"" + (cx - 118) + "\" y=\"14\" width=\"236\" height=\"44\" rx=\"8\" class=\"dg-chipbox\"/>"
            + "<text x=\"" + cx + "\" y=\"41\" class=\"dg-chiptext\">" + engEsc(engShort(name, 30)) + "</text></g>";
        legend += "<li><strong>" + (i + 1) + ". " + engEsc(engShort(name, 60)) + "</strong>"
            + (note ? ": " + engEsc(note) : "") + "</li>";
    }
    if (v.annotation)
        svg += "<text x=\"" + (W - 20) + "\" y=\"" + (H - 12) + "\" class=\"dg-annotation\" text-anchor=\"end\">" + engEsc(engShort(v.annotation, 70)) + "</text>";
    svg += "</svg>";
    return { svg: svg, legend: legend ? "<ol class=\"dg-legend\">" + legend + "</ol>" : "" };
}
/* ---------------- process / pathway engine ---------------- */
function engPathway(items, opts) {
    const list = (items || []).map((s) => String(s == null ? "" : s)).filter((s) => s.trim());
    if (!list.length)
        return "";
    const active = opts && opts.activeIndex != null ? opts.activeIndex : 999;
    let h = "<div class=\"pw-chain chain-n" + list.length + (opts && opts.loop ? " has-loop" : "") + "\">";
    list.forEach((item, i) => {
        const cls = i < active ? "pw-node lit" : (i === active ? "pw-node active" : "pw-node");
        h += (i > 0 ? "<div class=\"pw-arrow\" aria-hidden=\"true\">→</div>" : "")
            + "<div class=\"" + cls + "\"><span class=\"pw-step\">" + (i + 1) + "</span><span>" + engEsc(item) + "</span></div>";
    });
    if (opts && opts.loop)
        h += "<div class=\"pw-loopback\"><span>" + engEsc(opts.loopLabel || "feedback") + "</span></div>";
    return h + "</div>";
}
function engBranch(lanes, activeIndex) {
    const act = activeIndex != null ? activeIndex : 999;
    let flat = 0;
    let h = "<div class=\"pw-branch\">";
    lanes.forEach((lane) => {
        h += "<div class=\"pw-lane\">";
        lane.forEach((item) => {
            const cls = flat < act ? "pw-node lit" : (flat === act ? "pw-node active" : "pw-node");
            h += "<div class=\"" + cls + "\"><span>" + engEsc(item) + "</span></div>";
            flat++;
        });
        h += "</div>";
    });
    return h + "</div>";
}
function engCauseMechanismEffect(items) {
    const lanes = ["Cause", "Mechanism", "Effect"];
    let h = "<div class=\"pw-cme\">";
    items.slice(0, 3).forEach((item, i) => {
        h += (i > 0 ? "<div class=\"pw-arrow\" aria-hidden=\"true\">→</div>" : "")
            + "<div class=\"pw-lanebox\"><div class=\"pw-lanelabel\">" + lanes[i] + "</div>"
            + "<div class=\"pw-node\"><span>" + engEsc(item) + "</span></div></div>";
    });
    return h + "</div>";
}
/* ---------------- cycle engine ---------------- */
function engCycle(items, activeIndex) {
    const list = (items || []).map((s) => String(s == null ? "" : s)).filter((s) => s.trim()).slice(0, 8);
    if (!list.length)
        return "";
    const W = 1088, H = 400, cx = W / 2, cy = H / 2 + 10, R = 148;
    const act = activeIndex != null ? Math.min(activeIndex, list.length - 1) : -1;
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\">";
    svg += engSvgTitle("Cycle: " + list.slice(0, 3).join(", "));
    svg += "<defs><marker id=\"cy-arrow\" viewBox=\"0 0 10 10\" refX=\"8\" refY=\"5\" markerWidth=\"7\" markerHeight=\"7\" orient=\"auto-start-reverse\">"
        + "<path d=\"M 0 1 L 9 5 L 0 9\" fill=\"none\" stroke-width=\"1.6\" class=\"cy-arrowhead\"/></marker></defs>";
    const pts = list.map((_, i) => {
        const a = -Math.PI / 2 + (i / list.length) * Math.PI * 2;
        return { x: cx + R * Math.cos(a) * 2.1, y: cy + R * Math.sin(a) };
    });
    for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length];
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        const dx = b.x - a.x, dy = b.y - a.y, len = Math.max(1, Math.sqrt(dx * dx + dy * dy));
        const trim = 46 / len;
        svg += "<line x1=\"" + (a.x + dx * trim).toFixed(1) + "\" y1=\"" + (a.y + dy * trim).toFixed(1)
            + "\" x2=\"" + (mx).toFixed(1) + "\" y2=\"" + (my).toFixed(1) + "\" class=\"cy-edge\" marker-end=\"url(#cy-arrow)\"/>";
        svg += "<line x1=\"" + (mx).toFixed(1) + "\" y1=\"" + (my).toFixed(1)
            + "\" x2=\"" + (b.x - dx * trim).toFixed(1) + "\" y2=\"" + (b.y - dy * trim).toFixed(1) + "\" class=\"cy-edge\"/>";
    }
    pts.forEach((p, i) => {
        const cls = i < act ? "cy-node lit" : (i === act ? "cy-node active" : "cy-node");
        svg += "<g class=\"" + cls + "\"><circle cx=\"" + p.x.toFixed(1) + "\" cy=\"" + p.y.toFixed(1) + "\" r=\"42\"/>"
            + "<text x=\"" + p.x.toFixed(1) + "\" y=\"" + (p.y - 2).toFixed(1) + "\" class=\"cy-n\">" + (i + 1) + "</text>"
            + "<text x=\"" + p.x.toFixed(1) + "\" y=\"" + (p.y + 16).toFixed(1) + "\" class=\"cy-t\">" + engEsc(engShort(list[i], 16)) + "</text></g>";
    });
    svg += "</svg>";
    let legend = "<ol class=\"cy-legend\">";
    list.forEach((item, i) => {
        legend += "<li class=\"" + (i === act ? "active" : (i < act ? "lit" : "")) + "\"><strong>" + (i + 1) + ".</strong> " + engEsc(item) + "</li>";
    });
    return "<div class=\"cy-wrap\">" + svg + legend + "</ol></div>";
}
/* ---------------- comparison engine ---------------- */
function engIsNum(s) {
    const t = String(s == null ? "" : s).trim().toLowerCase();
    if (t === "" || t === "none" || t === "n/a" || t === "—" || t === "-")
        return false;
    return !isNaN(parseFloat(t)) && isFinite(parseFloat(t));
}
function engComparison(headers, rows) {
    const hs = (headers || []).map((h) => String(h == null ? "" : h));
    let h = "<table class=\"cmp-matrix\"><thead><tr>";
    hs.forEach((c, i) => { h += "<th scope=\"col\" class=\"" + (i === 0 ? "feat" : "opt-h") + "\">" + engEsc(c) + "</th>"; });
    h += "</tr></thead><tbody>";
    (rows || []).forEach((row) => {
        const cells = hs.map((_, i) => String((row || [])[i] == null ? "" : row[i]));
        const data = cells.slice(1);
        const shared = data.length > 1 && data.every((c) => c.toLowerCase() === data[0].toLowerCase());
        h += "<tr class=\"" + (shared ? "shared" : "") + "\">";
        cells.forEach((c, i) => {
            const diff = i > 0 && !shared && data.length > 1 ? " diff" : "";
            h += "<td class=\"" + (i === 0 ? "feat" : "val" + diff) + "\">" + engEsc(c) + "</td>";
        });
        h += "</tr>";
    });
    return h + "</tbody></table>";
}
function engSoloModel(kind, tag, claim, why) {
    /* One model fills its whole layer; the zone layout (side-by-side or
     * stacked rows) carries the wrong-vs-correct relationship. */
    return "<div class=\"wc-model wc-" + (kind === "wrong" ? "wrong" : "right") + "\">"
        + "<div class=\"wc-tag\">" + engEsc(tag) + "</div>"
        + "<p class=\"wc-claim\">" + engEsc(claim) + "</p>"
        + (why ? "<p class=\"wc-why\">" + engEsc(why) + "</p>" : "") + "</div>";
}
function engWrongCorrect(wrong, whyWrong, correct, whyRight) {
    return "<div class=\"wc-models\"><div class=\"wc-wrong\"><div class=\"wc-tag\">Common idea</div>"
        + "<p class=\"wc-claim\">" + engEsc(wrong) + "</p>"
        + (whyWrong ? "<p class=\"wc-why\">" + engEsc(whyWrong) + "</p>" : "") + "</div>"
        + "<div class=\"wc-right\"><div class=\"wc-tag\">Correct model</div>"
        + "<p class=\"wc-claim\">" + engEsc(correct) + "</p>"
        + (whyRight ? "<p class=\"wc-why\">" + engEsc(whyRight) + "</p>" : "") + "</div></div>";
}
/* ---------------- equation engine ---------------- */
function engTermHTML(coef, species, ref) {
    const c = String(coef == null ? "" : coef).trim();
    return (c ? "<span class=\"coef\">" + engEsc(c) + "</span>" : "")
        + "<span class=\"species\">" + engFrac(species) + "</span>"
        + (ref ? "<sup class=\"ref\">" + ref + "</sup>" : "");
}
function engEquation(eq) {
    const lhs = eq.lhs || [], rhs = eq.rhs || [];
    let ref = 0;
    const notes = [];
    const side = (terms) => terms.map((t) => {
        let r;
        if (t.note) {
            ref++;
            notes.push("<li><strong>" + engChem(t.species || "") + ":</strong> " + engEsc(t.note) + "</li>");
            r = ref;
        }
        return engTermHTML(t.coefficient || "", t.species || "", r);
    }).join("<span class=\"plus\">+</span>");
    let h = "<div class=\"eqn\"><div class=\"side\">" + side(lhs) + "</div>";
    if (eq.energy)
        h += "<div class=\"energy\">+ [" + engEsc(eq.energy) + "]</div>";
    h += "<div class=\"eq-arrow\">" + engEsc(eq.arrow || "→") + "</div>"
        + "<div class=\"side\">" + side(rhs) + "</div></div>";
    if (notes.length)
        h += "<ol class=\"eq-legend\">" + notes.join("") + "</ol>";
    return h;
}
/* ---------------- data engine ---------------- */
function engNumCols(columns, rows) {
    const idx = [];
    for (let i = 0; i < columns.length; i++) {
        let hits = 0, total = 0;
        for (const r of rows) {
            const v = Array.isArray(r) ? r[i] : r[columns[i]];
            if (v == null || String(v).trim() === "")
                continue;
            total++;
            if (engIsNum(String(v)))
                hits++;
        }
        if (total > 0 && hits === total)
            idx.push(i);
    }
    return idx;
}
function engRowVal(row, columns, i) {
    if (Array.isArray(row))
        return String(row[i] == null ? "" : row[i]);
    return String(row[columns[i]] == null ? "" : row[columns[i]]);
}
function engDataKind(columns, rows, rep) {
    const names = columns.join(" ").toLowerCase();
    const nums = engNumCols(columns, rows);
    if (/(nm\b|nanometer|wavelength|absorption|angstrom|å\b)/.test(names) && nums.length)
        return "spectrum";
    if (rep === "bar_chart" && nums.length)
        return "bars";
    if (rep === "line_chart" && nums.length >= 2)
        return "scatter";
    if (rep === "line_chart" && nums.length === 1)
        return "line";
    if (rep === "bar_chart" || (nums.length === 1 && rows.length <= 8)) {
        if (nums.length)
            return "bars";
    }
    return "table";
}
function engSpectrum(columns, rows) {
    const W = 1088, H = 300, L = 70, R = 1018, lo = 380, hi = 750;
    const x = (nm) => L + ((nm - lo) / (hi - lo)) * (R - L);
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\" class=\"sp-svg\">";
    svg += engSvgTitle("Absorption spectrum: " + engRowVal(rows[0] || {}, columns, 0));
    svg += "<defs><linearGradient id=\"sp-band\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\">"
        + "<stop offset=\"0\" stop-color=\"#7c3aed\"/><stop offset=\".25\" stop-color=\"#2f6fed\"/>"
        + "<stop offset=\".5\" stop-color=\"#22c55e\"/><stop offset=\".75\" stop-color=\"#eab308\"/>"
        + "<stop offset=\"1\" stop-color=\"#ef4444\"/></linearGradient></defs>";
    svg += "<rect x=\"" + L + "\" y=\"60\" width=\"" + (R - L) + "\" height=\"26\" fill=\"url(#sp-band)\" rx=\"4\" opacity=\".85\"/>";
    for (let t = 400; t <= 700; t += 100) {
        svg += "<line x1=\"" + x(t) + "\" y1=\"60\" x2=\"" + x(t) + "\" y2=\"92\" class=\"sp-tick\"/>"
            + "<text x=\"" + x(t) + "\" y=\"108\" class=\"sp-tickl\">" + t + "</text>";
    }
    const nmCols = columns.map((c, i) => ({ c: c, i: i }))
        .filter((o) => /(nm\b|wavelength|absorption)/i.test(o.c));
    const labelCol = columns.findIndex((c) => engNumCols(columns, rows).indexOf(columns.indexOf(c)) === -1);
    rows.forEach((row, r) => {
        const label = engShort(engRowVal(row, columns, labelCol < 0 ? 0 : labelCol), 26);
        nmCols.forEach((o, k) => {
            const raw = engRowVal(row, columns, o.i);
            if (!engIsNum(raw))
                return;
            const px = x(parseFloat(raw));
            const y = 150 + r * 44 + k * 8;
            svg += "<line x1=\"" + px + "\" y1=\"92\" x2=\"" + px + "\" y2=\"" + y + "\" class=\"sp-drop\"/>"
                + "<circle cx=\"" + px + "\" cy=\"" + y + "\" r=\"9\" class=\"sp-peak\"/>"
                + "<text x=\"" + (px + 14) + "\" y=\"" + (y + 5) + "\" class=\"sp-vallab\">" + engEsc(label) + " · " + engEsc(raw) + " nm</text>";
        });
    });
    return svg + "</svg>";
}
function engBars(columns, rows, numIdx, labelIdx) {
    const W = 1088, H = 320, L = 220, base = H - 40;
    let max = 0;
    const vals = rows.map((r) => engIsNum(engRowVal(r, columns, numIdx)) ? parseFloat(engRowVal(r, columns, numIdx)) : 0);
    vals.forEach((v) => { if (v > max)
        max = v; });
    max = max || 1;
    const rh = Math.min(44, (H - 80) / Math.max(1, rows.length));
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\" class=\"bar-svg\">";
    svg += engSvgTitle("Bar chart: " + engRowVal(rows[0] || {}, columns, labelIdx));
    rows.forEach((r, i) => {
        const y = 30 + i * (rh + 12);
        const w = Math.max(3, (vals[i] / max) * (W - L - 120));
        svg += "<text x=\"" + (L - 12) + "\" y=\"" + (y + rh / 2 + 5) + "\" class=\"bar-lab\" text-anchor=\"end\">" + engEsc(engShort(engRowVal(r, columns, labelIdx), 30)) + "</text>"
            + "<rect x=\"" + L + "\" y=\"" + y + "\" width=\"" + w.toFixed(1) + "\" height=\"" + rh + "\" rx=\"5\" class=\"bar-fill\"/>"
            + "<text x=\"" + (L + w + 10) + "\" y=\"" + (y + rh / 2 + 5) + "\" class=\"bar-val\">" + engEsc(engRowVal(r, columns, numIdx)) + "</text>";
    });
    return svg + "</svg>";
}
function engLine(columns, rows, numIdx) {
    const W = 1088, H = 320, L = 60, B = H - 44, T = 24;
    const vals = rows.map((r) => engIsNum(engRowVal(r, columns, numIdx)) ? parseFloat(engRowVal(r, columns, numIdx)) : NaN)
        .filter((v) => !isNaN(v));
    if (!vals.length)
        return "";
    let max = vals[0], min = vals[0];
    vals.forEach((v) => { if (v > max)
        max = v; if (v < min)
        min = v; });
    if (max === min)
        max = min + 1;
    const px = (i) => L + (i / Math.max(1, vals.length - 1)) * (W - L - 40);
    const py = (v) => B - ((v - min) / (max - min)) * (B - T);
    let d = "";
    vals.forEach((v, i) => { d += (i ? " L" : "M") + px(i).toFixed(1) + " " + py(v).toFixed(1); });
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\" class=\"line-svg\">"
        + engSvgTitle("Trend: " + columns[numIdx])
        + "<path d=\"" + d + "\" class=\"line-path\"/>";
    vals.forEach((v, i) => {
        svg += "<circle cx=\"" + px(i).toFixed(1) + "\" cy=\"" + py(v).toFixed(1) + "\" r=\"6\" class=\"line-dot\"/>";
    });
    return svg + "</svg>";
}
function engScatter(columns, rows, xi, yi) {
    const W = 1088, H = 320, L = 60, B = H - 44, T = 24;
    const pts = [];
    rows.forEach((r) => {
        const xs = engRowVal(r, columns, xi), ys = engRowVal(r, columns, yi);
        if (engIsNum(xs) && engIsNum(ys))
            pts.push({ x: parseFloat(xs), y: parseFloat(ys), lab: engShort(engRowVal(r, columns, 0), 20) });
    });
    if (!pts.length)
        return "";
    const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
    const x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    const y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    const px = (v) => L + ((v - x0) / Math.max(1e-9, x1 - x0)) * (W - L - 60);
    const py = (v) => B - ((v - y0) / Math.max(1e-9, y1 - y0)) * (B - T);
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\" class=\"sc-svg\">";
    svg += engSvgTitle("Scatter: " + columns[xi] + " vs " + columns[yi]);
    pts.forEach((p) => {
        svg += "<circle cx=\"" + px(p.x).toFixed(1) + "\" cy=\"" + py(p.y).toFixed(1) + "\" r=\"8\" class=\"sc-dot\"/>"
            + "<text x=\"" + (px(p.x) + 12).toFixed(1) + "\" y=\"" + (py(p.y) + 4).toFixed(1) + "\" class=\"sc-lab\">" + engEsc(p.lab) + "</text>";
    });
    return svg + "</svg>";
}
function engTable(columns, rows) {
    let h = "<table class=\"lyr-table t-data\"><thead><tr>";
    columns.forEach((c) => { h += "<th scope=\"col\">" + engEsc(c) + "</th>"; });
    h += "</tr></thead><tbody>";
    rows.forEach((r) => {
        h += "<tr>";
        columns.forEach((c, i) => { h += "<td>" + engEsc(engRowVal(r, columns, i)) + "</td>"; });
        h += "</tr>";
    });
    return h + "</tbody></table>";
}
/* Chooser: semantic intent from the IR representation + column meaning.
 * Rules: wavelength columns → spectrum; bar_chart → bars; line_chart →
 * scatter (x/y pair) or line (series); otherwise table. Figure first,
 * full data table preserved beneath (same values, nothing invented). */
function engData(columns, rows, rep) {
    const cols = (columns || []).map((c) => String(c == null ? "" : c));
    const rs = rows || [];
    const kind = engDataKind(cols, rs, rep);
    const nums = engNumCols(cols, rs);
    const labelIdx = cols.findIndex((_, i) => nums.indexOf(i) === -1);
    const lab = labelIdx < 0 ? 0 : labelIdx;
    let fig = "";
    if (kind === "spectrum")
        fig = "<div class=\"fig-spectrum\">" + engSpectrum(cols, rs) + "</div>";
    else if (kind === "bars")
        fig = "<div class=\"fig-bars\">" + engBars(cols, rs, nums[0], lab) + "</div>";
    else if (kind === "line")
        fig = "<div class=\"fig-line\">" + engLine(cols, rs, nums[0]) + "</div>";
    else if (kind === "scatter") {
        const pair = nums.slice(0, 2);
        fig = "<div class=\"fig-scatter\">" + engScatter(cols, rs, pair[0], pair[1]) + "</div>";
    }
    const table = "<div class=\"table-wrap\">" + engTable(cols, rs) + "</div>";
    return { kind: kind, html: fig + table };
}
/* ---------------- concept-map engine ---------------- */
function engConceptMap(title, items, edgeKind, activeIndex) {
    const list = (items || []).map((s) => String(s == null ? "" : s)).filter((s) => s.trim()).slice(0, 6);
    if (!list.length)
        return "";
    const act = activeIndex != null ? activeIndex : 999;
    const W = 1088, H = 400, cx = W / 2, cy = H / 2;
    let svg = "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"xMidYMid meet\" role=\"img\">";
    svg += engSvgTitle("Concept map: " + title);
    const pos = list.map((_, i) => {
        const a = -Math.PI / 2 + (i / Math.max(1, list.length)) * Math.PI * 2;
        return { x: cx + Math.cos(a) * 400, y: cy + Math.sin(a) * 150 };
    });
    pos.forEach((p, i) => {
        const edgeCls = edgeKind === "sequence" ? "cm-edge seq" : (edgeKind === "causal" || edgeKind === "dependency" ? "cm-edge causal" : "cm-edge");
        svg += "<line x1=\"" + cx + "\" y1=\"" + cy + "\" x2=\"" + p.x.toFixed(1) + "\" y2=\"" + p.y.toFixed(1) + "\" class=\"" + edgeCls + "\"/>";
    });
    svg += "<rect x=\"" + (cx - 150) + "\" y=\"" + (cy - 34) + "\" width=\"300\" height=\"68\" rx=\"10\" class=\"cm-hub\"/>"
        + "<text x=\"" + cx + "\" y=\"" + (cy + 6) + "\" class=\"cm-hubtext\">" + engEsc(engShort(title, 30)) + "</text>";
    pos.forEach((p, i) => {
        const cls = i < act ? "cm-sat lit" : (i === act ? "cm-sat active" : "cm-sat");
        svg += "<g class=\"" + cls + "\"><rect x=\"" + (p.x - 130) + "\" y=\"" + (p.y - 30) + "\" width=\"260\" height=\"60\" rx=\"9\"/>"
            + "<text x=\"" + p.x.toFixed(1) + "\" y=\"" + (p.y + 5).toFixed(1) + "\" class=\"cm-sattext\">" + engEsc(engShort(list[i], 30)) + "</text></g>";
        if (edgeKind === "sequence") {
            svg += "<text x=\"" + ((cx + p.x) / 2).toFixed(1) + "\" y=\"" + ((cy + p.y) / 2).toFixed(1) + "\" class=\"cm-stepn\">" + (i + 1) + "</text>";
        }
    });
    svg += "</svg>";
    let legend = "<ol class=\"cm-legend\">";
    list.forEach((item, i) => {
        legend += "<li class=\"" + (i === act ? "active" : "") + "\"><strong>" + (i + 1) + ".</strong> " + engEsc(item) + "</li>";
    });
    return "<div class=\"cm-wrap\">" + svg + legend + "</ol></div>";
}
/* ---------------- image-composition engine ----------------
 * Layouts: hero | bleed | split | annotated | inset | overlay.
 * Purpose comes from caption/kicker text passed in — never assumed. */
function engImage(assets, caption, layout, kicker) {
    if (!assets || !assets.length)
        return "";
    const src = engEsc(assets[0]);
    const cap = caption ? "<figcaption>" + engEsc(caption) + "</figcaption>" : "";
    const kick = kicker ? "<div class=\"img-kicker\">" + engEsc(kicker) + "</div>" : "";
    /* onerror degrades gracefully: layout holds, caption survives. */
    const img = "<img src=\"" + src + "\" alt=\"\" loading=\"lazy\" onerror=\"(function(i){var d=document.createElement('div');d.className='img-broken';d.textContent='Image unavailable \\u2014 see caption';i.replaceWith(d);})(this)\"/>";
    switch (layout) {
        case "bleed":
            return "<figure class=\"img-bleed\">" + img + cap + "</figure>";
        case "split":
            return "<figure class=\"img-split\">" + kick + "<div class=\"img-frame\">" + img + "</div>" + cap + "</figure>";
        case "annotated":
            return "<figure class=\"img-annotated\"><div class=\"img-frame\">" + img + "<span class=\"img-note\">" + engEsc(caption || "") + "</span></div></figure>";
        case "inset":
            return "<figure class=\"img-inset\"><div class=\"img-frame\">" + img + "</div>" + cap + "</figure>";
        case "overlay":
            return "<figure class=\"img-overlay\">" + img + "<div class=\"img-veil\">" + kick + cap + "</div></figure>";
        default:
            return "<figure class=\"img-hero\">" + kick + "<div class=\"img-frame\">" + img + "</div>" + cap + "</figure>";
    }
}

"use strict";
/* Deterministic lesson state machine. Pure functions, no DOM. */
function initialState() {
    return { sceneIndex: 0, stateIndex: 0, selected: null, answeredScenes: {} };
}
function currentScene(lesson, st) {
    return lesson.scenes[st.sceneIndex];
}
function atFinalState(scene, st) {
    return st.stateIndex >= scene.states.length - 1;
}
function isLastScene(lesson, st) {
    return st.sceneIndex >= lesson.scenes.length - 1;
}
/** Advance: next state, or next scene. Returns {moved, wrapped}. */
function advance(lesson, st) {
    const scene = currentScene(lesson, st);
    if (!atFinalState(scene, st)) {
        st.stateIndex += 1;
        return { moved: true, wrapped: false };
    }
    // Leaving an interactive scene records completion.
    if (scene.interaction.type === "choice" && st.selected) {
        st.answeredScenes[scene.scene_id] = st.selected;
    }
    else if (scene.interaction.type !== "none") {
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
function back(lesson, st) {
    if (st.stateIndex > 0) {
        st.stateIndex -= 1;
        return true;
    }
    if (st.sceneIndex > 0) {
        st.sceneIndex -= 1;
        st.stateIndex = 0;
        st.selected = null;
        return true;
    }
    return false;
}
function goTo(lesson, st, sceneIndex) {
    if (sceneIndex < 0 || sceneIndex >= lesson.scenes.length)
        return false;
    st.sceneIndex = sceneIndex;
    st.stateIndex = 0;
    st.selected = null;
    return true;
}
function selectOption(st, key) {
    st.selected = (st.selected === key) ? null : key;
}
function visibleLayers(scene, st) {
    const vis = scene.states[Math.min(st.stateIndex, scene.states.length - 1)].visible_layers;
    return scene.layers.filter((l) => vis.indexOf(l.id) !== -1)
        .sort((a, b) => a.z - b.z);
}
/** Layers that became visible exactly at this state (for entrance motion). */
function newlyVisible(scene, st) {
    if (st.stateIndex === 0)
        return visibleLayers(scene, st).map((l) => l.id);
    const now = scene.states[st.stateIndex].visible_layers;
    const prev = scene.states[st.stateIndex - 1].visible_layers;
    return now.filter((id) => prev.indexOf(id) === -1);
}

"use strict";
/* 16:9 viewport scaler. Logical canvas 1280x720; the window letterboxes,
 * never distorts, never scrolls. */
const LOGICAL_W = 1280;
const LOGICAL_H = 720;
function fitStage() {
    const stage = document.getElementById("stage");
    const viewport = document.getElementById("viewport");
    if (!stage || !viewport)
        return;
    const scale = Math.min(window.innerWidth / LOGICAL_W, window.innerHeight / LOGICAL_H);
    stage.style.width = LOGICAL_W + "px";
    stage.style.height = LOGICAL_H + "px";
    stage.style.transform = "translate(-50%, -50%) scale(" + scale + ")";
    viewport.style.background = "#0b0e14";
}
function initViewport() {
    document.documentElement.style.height = "100%";
    document.body.style.height = "100%";
    document.body.style.margin = "0";
    document.body.style.overflow = "hidden";
    window.addEventListener("resize", fitStage);
    fitStage();
}

"use strict";
/* Scene renderer — executes family composition + semantic type scale.
 * Data-driven only: every string on screen comes from scene.content /
 * scene.visual / scene.assets. No hardcoded lesson content lives here.
 * Layer geometry arrives from the VisualDirector (logical 1280×720 regions);
 * family classes from compositions.ts drive emphasis, order, and treatment.
 * Cards are NOT the default: only answer banners, choice controls, and the
 * misconception correction panel use bordered surfaces (see styles.css). */
function esc(s) {
    return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function el(tag, cls, html) {
    const d = document.createElement(tag);
    if (cls)
        d.className = cls;
    d.innerHTML = html;
    return d;
}
function place(node, region) {
    node.style.left = region.x + "px";
    node.style.top = region.y + "px";
    node.style.width = region.w + "px";
    node.style.height = region.h + "px";
}
/* ---------- family components: 17 stagings, one focal point each ---------- */
function renderFamily(fam, scene, st, layers) {
    const placeAll = (extra) => layers.map((layer) => {
        const node = renderLayer(scene, layer, st, fam);
        if (node) {
            place(node, layer.region);
            node.dataset.layer = layer.id;
            if (extra)
                extra(node, layer);
        }
        return node;
    }).filter((n) => n);
    switch (fam) {
        case "cinematic_hook": { // HeroScene: giant topic, kicker whisper
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "title")
                    node.classList.add("focal-display");
                if (layer.kind === "subtitle")
                    node.classList.add("t-subtitle");
            });
            return [section("hook", nodes)];
        }
        case "hero_concept": { // HeroConcept: term as display type, definition large
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "text")
                    node.classList.add("focal-hero");
            });
            return [section("hero", nodes)];
        }
        case "full_visual":
        case "diagram_centered":
        case "split_visual": { // media-first: diagram/photo owns the eye
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "diagram" || layer.kind === "media")
                    node.classList.add("focal-media");
            });
            return [section("visual", nodes)];
        }
        case "process_pathway":
        case "cycle": { // ProcessScene: numbered flow, steps read as a path
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "list")
                    node.classList.add("steps-flow");
            });
            return [section("flow", nodes)];
        }
        case "comparison": { // ComparisonScene: A vs B with a quiet divider
            const nodes = placeAll();
            if (nodes.length >= 2) {
                const versus = el("div", "versus", "<span>vs</span>");
                const out = [nodes[0], versus].concat(nodes.slice(1));
                return [section("compare", out)];
            }
            return [section("compare", nodes)];
        }
        case "equation_focus": { // EquationScene: monument equation
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "equation")
                    node.classList.add("focal-equation");
            });
            return [section("equation", nodes)];
        }
        case "data_visualization": { // DataScene: table/chart at reading scale
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "table")
                    node.classList.add("focal-data");
            });
            return [section("data", nodes)];
        }
        case "question_focus": { // QuestionScene: the question IS the slide
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "prompt")
                    node.classList.add("focal-question");
                if (layer.kind === "options")
                    node.classList.add("choices-lg");
            });
            return [section("question", nodes)];
        }
        case "answer_reveal": { // AnswerScene: verdict banner, rest recedes
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "answer")
                    node.classList.add("answer-banner");
            });
            return [section("answer", nodes)];
        }
        case "misconception": { // MisconceptionScene: myth struck, correction lit
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "text")
                    node.classList.add("myth-correction");
            });
            return [section("myth", nodes)];
        }
        case "practice_workspace": { // PracticeScene: prompt + generous working room
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "note")
                    node.classList.add("workspace");
            });
            return [section("practice", nodes)];
        }
        case "concept_map": { // ConceptMapScene: hub + satellites
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "diagram")
                    node.classList.add("focal-media");
            });
            return [section("map", nodes)];
        }
        case "synthesis": { // SynthesisScene: takeaway band
            const nodes = placeAll((node, layer) => {
                if (layer.kind === "list" || layer.kind === "table")
                    node.classList.add("takeaways");
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
function section(kind, nodes) {
    const s = document.createElement("div");
    s.className = "scene-section sec-" + kind;
    for (const n of nodes)
        s.appendChild(n);
    return s;
}
function renderScene(stage, lesson, st) {
    const scene = currentScene(lesson, st);
    stage.innerHTML = "";
    const fam = familyOf(scene);
    const body = document.createElement("div");
    body.className = "scene-body " + stageClass(scene);
    body.dataset.composition = fam;
    body.dataset.component = componentFor(fam);
    const layers = visibleLayers(scene, st);
    for (const node of renderFamily(fam, scene, st, layers))
        body.appendChild(node);
    stage.appendChild(body);
    stage.appendChild(renderChrome(lesson, st));
    fitHeadlines(stage);
    fitBody(stage);
}
/* Deterministic auto-fit: long titles/prompts shrink within their region
 * (never below classroom minimums) instead of spilling over the scene. */
function fitHeadlines(stage) {
    const heads = stage.querySelectorAll(".lyr-title, .lyr-prompt");
    for (let i = 0; i < heads.length; i++) {
        const box = heads[i];
        const text = box.querySelector("h1, p");
        if (!text)
            continue;
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
function fitBody(stage) {
    const bodies = stage.querySelectorAll(".lyr-text, .lyr-list, .lyr-note, .lyr-options, .lyr-data, .lyr-equation, .lyr-diagram");
    for (let i = 0; i < bodies.length; i++) {
        const box = bodies[i];
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
function renderLayer(scene, layer, st, fam) {
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
            if (scene.representation === "contrast")
                return renderContrastModel(scene, layer);
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
            if (scene.representation === "practice_problem")
                return renderPracticeNote(scene);
            if (["labeled_diagram", "anatomy_map", "cutaway", "spatial_relationship"].indexOf(scene.representation) !== -1) {
                const legend = renderDiagramLegend(scene);
                const cap = scene.content.caption || noteText(scene);
                if (!legend && !cap)
                    return el("div", "lyr-note t-caption", "");
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
function renderContrastModel(scene, layer) {
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
function edgeKindForTask(task) {
    const t = String(task || "").toLowerCase();
    if (/sequence|order|steps|chronolog/.test(t))
        return "sequence";
    if (/mechanism|process|caus|drives|leads/.test(t))
        return "causal";
    if (/depend|prereq|require/.test(t))
        return "dependency";
    return "plain";
}
/* Content type determines visual form — never a default text box. */
function renderSemanticList(scene, layer, st) {
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
    const pts = c.points || c.takeaways || [];
    if (rep === "flow" || rep === "sequence" || rep === "pathway") {
        if (!pts.length)
            return null;
        wrap.innerHTML = engPathway(pts, { activeIndex: active });
        return wrap;
    }
    if (rep === "cause_effect") {
        if (!pts.length)
            return null;
        wrap.innerHTML = pts.length === 3 ? engCauseMechanismEffect(pts) : engPathway(pts, { activeIndex: active });
        return wrap;
    }
    if (rep === "concept_map" || rep === "hierarchy") {
        if (!pts.length)
            return null;
        wrap.innerHTML = engConceptMap(c.title || "", pts, edgeKindForTask(scene.task), active);
        wrap.classList.add("map-layer");
        return wrap;
    }
    if (rep === "before_after") {
        if (!pts.length)
            return null;
        const half = Math.ceil(pts.length / 2);
        const mine = (/1$/.test(layer.id) || layer.id === "list")
            ? pts.slice(0, half) : pts.slice(half);
        wrap.innerHTML = "<ul>" + mine.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
        return wrap;
    }
    wrap.innerHTML = renderListBody(scene);
    if (!wrap.textContent || !wrap.textContent.trim())
        return null;
    return wrap;
}
function renderTextBody(scene) {
    const c = scene.content;
    if (c.definition)
        return "<p class=\"term t-hero\">" + esc(c.term || "") + "</p><p class=\"t-body-large\">" + esc(c.definition) + "</p>";
    if (c.problem) {
        let h = "<p class=\"problem t-body-large\">" + esc(c.problem) + "</p>";
        if (c.givens && c.givens.length)
            h += "<p class=\"givens t-caption\">" + esc(c.givens.join(" · ")) + "</p>";
        return h;
    }
    if (c.caption)
        return "<p>" + esc(c.caption) + "</p>";
    if (c.items && c.items.length)
        return "<p>" + esc(c.items[0]) + "</p>";
    return "";
}
function renderListBody(scene) {
    const c = scene.content;
    const rep = scene.representation;
    if (rep === "worked_calculation" && c.steps) {
        return "<ol class=\"steps\">" + c.steps.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ol>"
            + (c.verify ? "<p class=\"verify\">" + esc(c.verify) + "</p>" : "");
    }
    if ((rep === "objectives" || rep === "roadmap") && c.objectives) {
        return "<ul>" + c.objectives.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
    }
    if (rep === "exit") {
        return "<p>" + esc(c.prompt_1 || "") + "</p><p>" + esc(c.prompt_2 || "") + "</p>";
    }
    const pts = c.points || c.takeaways || [];
    if (!pts.length)
        return "";
    return "<ul>" + pts.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
}
function renderOptions(scene, st) {
    const wrap = document.createElement("div");
    wrap.className = "lyr-options";
    const opts = scene.content.options || {};
    const keys = Object.keys(opts).sort();
    const answered = scene.scene_id in st.answeredScenes;
    if (keys.length >= 4)
        wrap.classList.add("opts-n4");
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
        if (st.selected === k)
            b.classList.add("selected");
        if (answered) {
            b.disabled = true;
            if (k === scene.interaction.correct)
                b.classList.add("correct");
            else if (k === st.answeredScenes[scene.scene_id])
                b.classList.add("incorrect");
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
function renderDataNode(scene) {
    const v = scene.visual || {};
    const cols = v.columns || [];
    if (!cols.length)
        return null;
    const wrap = document.createElement("div");
    wrap.className = "lyr-data data-kind-" + scene.representation;
    if (scene.representation === "comparison_matrix" || scene.representation === "summary_matrix") {
        const rows = (v.rows || []).map((r) => Array.isArray(r) ? r.map((c) => String(c == null ? "" : c)) : cols.map((c) => String(r[c] == null ? "" : r[c])));
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
function renderEquationNode(scene) {
    const eq = (scene.visual || {}).equation;
    if (!eq || (!eq.lhs && !eq.rhs))
        return null;
    const wrap = document.createElement("div");
    wrap.className = "lyr-equation";
    wrap.innerHTML = engEquation(eq)
        + (scene.content.context ? "<p class=\"context t-caption\">" + esc(scene.content.context) + "</p>" : "");
    return wrap;
}
function renderDiagramNode(scene, st) {
    const v = scene.visual || {};
    const rep = scene.representation;
    const pts = scene.content.points || [];
    if (rep === "cycle") {
        if (!pts.length)
            return null;
        const wrap = document.createElement("div");
        wrap.className = "lyr-diagram";
        wrap.innerHTML = engCycle(pts, st.stateIndex);
        return wrap;
    }
    if (rep === "pathway" || rep === "flow" || rep === "sequence") {
        if (!pts.length)
            return null;
        const wrap = document.createElement("div");
        wrap.className = "lyr-diagram";
        wrap.innerHTML = engPathway(pts, { activeIndex: st.stateIndex });
        return wrap;
    }
    const labels = v.labels || v.structure || [];
    if (!labels.length && !scene.assets.length)
        return null;
    const wrap = document.createElement("div");
    wrap.className = "lyr-diagram";
    const active = Math.min(st.stateIndex, Math.max(0, labels.length - 1));
    const d = engDiagram(v, labels.length ? active : 999);
    wrap.innerHTML = d.svg;
    wrap.dataset.legend = d.legend;
    return wrap;
}
function renderDiagramLegend(scene) {
    const v = scene.visual || {};
    const labels = v.labels || v.structure || [];
    if (!labels.length)
        return "";
    const d = engDiagram(v, 999);
    return d.legend;
}
function renderMediaNode(scene) {
    if (!scene.assets.length)
        return null;
    const v = scene.visual || {};
    const layouts = { full_visual: "bleed", split_visual: "split", cinematic_hook: "hero" };
    const layout = v.image_layout || layouts[v.composition] || "hero";
    const wrap = document.createElement("div");
    wrap.className = "lyr-mediawrap";
    wrap.innerHTML = engImage(scene.assets, scene.content.caption || "", layout, scene.content.kicker || "");
    if (!wrap.querySelector("img"))
        return null;
    return wrap;
}
function renderPracticeNote(scene) {
    const sc = scene.content.scaffold || {};
    const wrap = document.createElement("div");
    wrap.className = "lyr-note t-caption";
    if (sc.columns && sc.columns.length >= 2) {
        const heads = sc.columns.map((c) => String(c));
        let h = "<table class=\"cmp-matrix workspace\"><thead><tr>";
        heads.forEach((c) => { h += "<th>" + esc(c) + "</th>"; });
        h += "</tr></thead><tbody><tr>";
        heads.forEach(() => { h += "<td class=\"blank\"></td>"; });
        h += "</tr></tbody></table>";
        wrap.innerHTML = h + (sc.note ? "<p>" + esc(sc.note) + "</p>" : "");
        return wrap;
    }
    wrap.innerHTML = "<p>" + esc(noteText(scene)) + "</p>";
    return wrap;
}
function renderAnswer(scene, st) {
    const inter = scene.interaction;
    let verdict = "";
    if (inter.type === "choice") {
        const chosen = st.selected != null ? st.selected : st.answeredScenes[scene.scene_id];
        const ok = String(chosen) === String(inter.correct);
        verdict = "<p class=\"verdict " + (ok ? "ok" : "miss") + "\">" + (ok ? "Correct" : "Not quite") + "</p>";
    }
    return el("div", "lyr-answer t-answer", verdict + "<p>" + esc(inter.explanation || "") + "</p>");
}
function noteText(scene) {
    const c = scene.content;
    const sc = c.scaffold || {};
    if (sc.note)
        return sc.note;
    if (sc.columns)
        return "Complete the comparison from the lesson.";
    return c.caption || "";
}
function renderChrome(lesson, st) {
    const bar = document.createElement("div");
    bar.id = "progress";
    const pct = lesson.scenes.length <= 1 ? 100
        : Math.round((st.sceneIndex / (lesson.scenes.length - 1)) * 100);
    bar.innerHTML = "<div class=\"lesson-tag t-label\">" + esc(lesson.title || "") + "</div>"
        + "<div class=\"track\"><div class=\"fill\" style=\"width:" + pct + "%\"></div></div>"
        + "<div class=\"count t-label\">" + (st.sceneIndex + 1) + " / " + lesson.scenes.length + "</div>"
        + "<button id=\"fs-btn\" title=\"Fullscreen\">⛶</button>";
    const btn = bar.querySelector("#fs-btn");
    if (btn)
        btn.addEventListener("click", (ev) => { ev.stopPropagation(); toggleFullscreen(); });
    return bar;
}

"use strict";
/* Semantic motion executor — every animation answers "why should this move?".
 * Vocabulary mirrors lessonmorph/runtime/motion_director.py primitives; timings
 * mirror its TIMING_TOKENS. Scenes never invent timings. All playback is
 * deterministic (driven by scene.motion + state index) and inert under
 * prefers-reduced-motion: states still advance, meaning preserved. */
const MOTION_TOKENS = { fast: 180, normal: 250, slow: 400, process: 600 };
const MOTION_EASING = "ease-out";
/* Primitive → instructional reason (mirrors the director; audited by motion QA). */
const PRIMITIVE_WHY = {
    fade: "enter a supporting element without stealing focus",
    appear: "progressive disclosure of the next idea",
    wipe: "causal direction: this leads to that",
    slide: "transformation: the same object changes state",
    scale: "emphasize magnitude or importance once",
    highlight: "direct attention for comparison",
    pulse: "draw the eye to the active region, then stop",
    path_motion: "a marker travels a real visual path",
    progressive_reveal: "build a derivation or structure piece by piece",
    answer_reveal: "disclose the locked answer after thinking",
    diagram_reveal: "light up the next diagram component in sequence",
    state_transition: "move between scene states without rebuilding",
};
function reducedMotion() {
    try {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
    catch (e) {
        return false;
    }
}
function effectFor(scene, stepIndex) {
    const adv = scene.motion && scene.motion.advance ? scene.motion.advance : [];
    const found = adv.filter((a) => a.step === stepIndex + 1)[0];
    if (found)
        return { effect: found.effect, duration_ms: found.duration_ms };
    return { effect: "fade", duration_ms: MOTION_TOKENS.normal };
}
function playEntrance(stage, scene, st, firstPaint) {
    if (reducedMotion())
        return; // states advance; no movement. Meaning preserved.
    const fresh = newlyVisible(scene, st);
    if (firstPaint && scene.motion && scene.motion.enter_transition === "fade") {
        const anim = stage.animate([{ opacity: 0 }, { opacity: 1 }], { duration: MOTION_TOKENS.fast, easing: MOTION_EASING });
        if (anim && anim.finished)
            anim.finished.catch(function () { });
    }
    playFreshLayers(stage, fresh, scene, st);
    playRegionActivation(stage, scene, st);
    playSceneSequence(stage, scene, st);
    playPaths(stage, scene, st);
}
function playFreshLayers(stage, fresh, scene, st) {
    const kids = stage.querySelectorAll("[data-layer]");
    // Restrained: options enter as one staggered group, never N independent solos.
    let optDelay = 0;
    for (let i = 0; i < kids.length; i++) {
        const node = kids[i];
        const lid = node.dataset ? node.dataset.layer : "";
        if (!lid || fresh.indexOf(lid) === -1)
            continue;
        const fx = effectFor(scene, st.stateIndex);
        let delay = 0;
        if (node.classList && node.classList.contains("opt") && optDelay < 4) {
            delay = (optDelay++) * 60;
        }
        playEffect(node, fx.effect, fx.duration_ms, delay);
    }
}
/* Newly lit diagram region pulses once so the sequence reads as disclosure. */
function playRegionActivation(stage, scene, st) {
    const regions = stage.querySelectorAll("[data-region].active");
    for (let i = 0; i < regions.length; i++) {
        const node = regions[i];
        playEffect(node, "highlight", MOTION_TOKENS.slow);
    }
}
/* Compositional sequences: misconception strike, answer evidence, think cue. */
function playSceneSequence(stage, scene, st) {
    const v = scene.visual || {};
    const fam = v.composition || "";
    if (fam === "misconception" && st.stateIndex > 0) {
        stage.classList.add("played");
    }
    if (fam === "answer_reveal" || (scene.interaction && scene.interaction.type !== "none" && atFinalState(scene, st))) {
        const banner = stage.querySelector(".answer-banner, .lyr-answer");
        if (banner)
            playEffect(banner, "emphasis", MOTION_TOKENS.slow);
    }
    if (fam === "question_focus" && st.stateIndex === 0 && !st.selected) {
        const cue = stage.querySelector(".think-cue");
        if (cue)
            playEffect(cue, "highlight", MOTION_TOKENS.slow);
    }
}
/* Path motion: a marker travels real rendered geometry (region anchors or
 * pathway nodes), narrated by a live caption naming each leg. Waypoints come
 * from IR label names resolved to on-screen anchors — never invented. */
function resolveWaypoints(stage, via) {
    const out = [];
    const regions = stage.querySelectorAll("[data-region]");
    const byIndex = [];
    for (let i = 0; i < regions.length; i++)
        byIndex.push(regions[i]);
    const stageBox = stage.getBoundingClientRect();
    const anchor = (node) => {
        const b = node.getBoundingClientRect();
        return {
            x: (b.left + b.width / 2 - stageBox.left) / (stageBox.width || 1) * 1280,
            y: (b.top + b.height / 2 - stageBox.top) / (stageBox.height || 1) * 720,
            name: "",
        };
    };
    if (byIndex.length >= 2 && via.length >= 2) {
        const order = via.map((_, i) => Math.min(i, byIndex.length - 1));
        order.forEach((ri, k) => {
            const w = anchor(byIndex[ri]);
            w.name = via[k] || "";
            out.push(w);
        });
        return out;
    }
    const nodes = stage.querySelectorAll(".pw-node");
    for (let i = 0; i < nodes.length; i++) {
        const w = anchor(nodes[i]);
        w.name = via[i] || "";
        out.push(w);
    }
    return out;
}
function playPaths(stage, scene, st) {
    const paths = (scene.motion && scene.motion.paths) || [];
    if (!paths.length || st.stateIndex === 0)
        return;
    // One journey per scene, on the latest state only — never concurrent solos.
    const path = paths[0];
    const pts = resolveWaypoints(stage, path.via || []);
    if (pts.length < 2)
        return;
    const dur = Math.min(path.duration_ms || MOTION_TOKENS.process, 4000);
    const marker = document.createElement("div");
    marker.className = "path-marker kind-" + path.kind;
    const cap = document.createElement("div");
    cap.className = "path-caption";
    stage.appendChild(marker);
    stage.appendChild(cap);
    const legMs = dur / (pts.length - 1);
    let leg = 0;
    const place = (p) => {
        marker.style.left = p.x + "px";
        marker.style.top = p.y + "px";
    };
    place(pts[0]);
    const stepLeg = () => {
        if (leg >= pts.length - 1) {
            setTimeout(() => { if (marker.parentNode)
                marker.parentNode.removeChild(marker); }, 600);
            setTimeout(() => { if (cap.parentNode)
                cap.parentNode.removeChild(cap); }, 1800);
            return;
        }
        const a = pts[leg], b = pts[leg + 1];
        cap.textContent = (a.name ? a.name + " " : "") + "→ " + (b.name || "next");
        try {
            const anim = marker.animate([
                { left: a.x + "px", top: a.y + "px" },
                { left: b.x + "px", top: b.y + "px" },
            ], { duration: legMs, easing: "ease-in-out", fill: "forwards" });
            const done = () => { leg++; stepLeg(); };
            if (anim && anim.finished)
                anim.finished.then(done, done);
            else
                setTimeout(done, legMs);
        }
        catch (e) {
            place(b);
            leg++;
            stepLeg();
        }
    };
    setTimeout(stepLeg, 120);
}
function playEffect(node, effect, ms, delay) {
    const run = () => {
        let frames = [{ opacity: 0 }, { opacity: 1 }];
        if (effect === "slide")
            frames = [{ opacity: 0, transform: "translateX(28px)" }, { opacity: 1, transform: "none" }];
        else if (effect === "wipe")
            frames = [{ opacity: 0, clipPath: "inset(0 100% 0 0)" }, { opacity: 1, clipPath: "inset(0 0 0 0)" }];
        else if (effect === "highlight")
            frames = [{ opacity: 0 }, { opacity: 1 }, { opacity: 0.55 }, { opacity: 1 }];
        else if (effect === "emphasis")
            frames = [{ transform: "scale(1)" }, { transform: "scale(1.02)" }, { transform: "scale(1)" }];
        try {
            const anim = node.animate(frames, { duration: ms, easing: MOTION_EASING });
            if (anim && anim.finished)
                anim.finished.catch(function () { });
        }
        catch (e) { /* animation unsupported: content stays visible */ }
    };
    if (delay)
        setTimeout(run, delay);
    else
        run();
}

"use strict";
/* Navigation: keyboard, mouse/tap, fullscreen. Runtime only — no pedagogy. */
function toggleFullscreen() {
    try {
        if (document.fullscreenElement) {
            void document.exitFullscreen();
            return;
        }
        const root = document.documentElement;
        if (root.requestFullscreen) {
            void root.requestFullscreen();
        }
    }
    catch (e) { /* fullscreen unavailable */ }
}
function onSelectOption(key) {
    const app = window.__lessonApp;
    if (!app)
        return;
    selectOption(app.state, key);
    renderScene(app.stage, app.lesson, app.state);
}
function initNav(app) {
    window.__lessonApp = app;
    document.addEventListener("keydown", (ev) => {
        if (ev.key === "ArrowRight" || ev.key === " ") {
            ev.preventDefault();
            stepForward(app);
        }
        else if (ev.key === "ArrowLeft") {
            ev.preventDefault();
            if (back(app.lesson, app.state))
                paint(app, false);
        }
        else if (ev.key === "Home") {
            ev.preventDefault();
            if (goTo(app.lesson, app.state, 0))
                paint(app, true);
        }
        else if (ev.key === "End") {
            ev.preventDefault();
            if (goTo(app.lesson, app.state, app.lesson.scenes.length - 1))
                paint(app, true);
        }
        else if (ev.key === "Enter") {
            // Reveal/confirm: on a choice scene with a committed answer, Enter
            // discloses the locked answer; elsewhere it steps like Space.
            const scene = currentScene(app.lesson, app.state);
            if (scene.interaction && scene.interaction.type === "choice" && app.state.selected) {
                ev.preventDefault();
                stepForward(app);
            }
            else if (ev.target && ev.target.tagName !== "BUTTON") {
                ev.preventDefault();
                stepForward(app);
            }
            // Inside a focused button, Enter keeps its native activate behavior.
        }
        // Escape exits fullscreen natively and closes no overlays (there are
        // none — temporary UI like path captions dismiss themselves).
    });
    app.stage.addEventListener("click", () => stepForward(app));
}
function stepForward(app) {
    const r = advance(app.lesson, app.state);
    if (r.moved)
        paint(app, true);
}
function paint(app, animate) {
    renderScene(app.stage, app.lesson, app.state);
    playEntrance(app.stage, currentScene(app.lesson, app.state), app.state, animate);
}

"use strict";
/* Lesson runtime entry point. Reads the embedded lesson payload
 * (inlined at bundle time — no fetch, file:// safe) and boots the viewport,
 * store, renderer, and navigation. */
function boot() {
    const dataEl = document.getElementById("lesson-data");
    const stage = document.getElementById("stage");
    if (!dataEl || !stage)
        return;
    let lesson;
    try {
        lesson = JSON.parse(dataEl.textContent || "{}");
    }
    catch (e) {
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
}
else {
    boot();
}

