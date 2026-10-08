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
