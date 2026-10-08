/* Engine unit harness — runs the PURE string builders from dist/engines.js
 * (emitted by `npm run build`, no DOM needed) and asserts semantic output.
 * Exit non-zero on the first failure. No lesson content in expectations
 * beyond synthetic fixtures defined below. */
const fs = require("fs");
const path = require("path");

const dist = path.join(__dirname, "..", "dist");
const src = fs.readFileSync(path.join(dist, "engines.js"), "utf8");
(0, eval)(src + "\n;globalThis.__eng = { engDiagram, engPathway, engBranch, engCauseMechanismEffect, engCycle, engComparison, engSoloModel, engWrongCorrect, engChem, engFrac, engEquation, engDataKind, engData, engConceptMap, engImage, engSpectrum, engBars, engLine, engScatter, engTable };");
const E = globalThis.__eng;

let n = 0;
function ok(cond, name) {
  n++;
  if (!cond) { console.error("FAIL: " + name); process.exit(1); }
  console.log("ok " + n + " - " + name);
}

/* diagram: labels bind to regions, leaders exist, reveal states */
{
  const d = E.engDiagram({ subject: "Chloroplast", labels: [
    { name: "Thylakoid Membrane System" }, { name: "Stroma" }, { name: "Thylakoid Lumen" }] }, 1);
  ok(d.svg.includes('id="region-0"') && d.svg.includes('id="region-2"'), "diagram regions per label");
  ok(d.svg.includes('id="label-0"') && d.svg.includes("dg-leader"), "diagram leaders label→region");
  ok(d.svg.includes("dg-membrane") && d.svg.includes("dg-disc") === false, "membrane band geometry");
  const d2 = E.engDiagram({ subject: "X", labels: ["Thylakoid stacks", "Stroma fluid"] }, 0);
  ok(d2.svg.includes("dg-disc") && d2.svg.includes("dg-fluid"), "stack + fluid motifs");
  ok(d.svg.includes("active") && d.svg.includes("dimmed"), "diagram reveal states");
  ok(d.legend.includes("Thylakoid Lumen"), "diagram legend preserves labels");
}

/* pathway: directional chain, loop, branch, cme */
{
  const p = E.engPathway(["A", "B", "C"], { activeIndex: 1 });
  ok(p.includes("pw-node") && p.includes("pw-arrow"), "pathway nodes + arrows");
  ok(!p.includes("<p>"), "pathway is structure, not paragraphs");
  const loop = E.engPathway(["A", "B"], { loop: true });
  ok(loop.includes("pw-loopback"), "feedback loop rail");
  const br = E.engBranch([["A1", "A2"], ["B1"]]);
  ok(br.includes("pw-lane") && br.includes("A2") && br.includes("B1"), "branched lanes");
  const cme = E.engCauseMechanismEffect(["sun", "capture", "sugar"]);
  ok(cme.includes("Cause") && cme.includes("Mechanism") && cme.includes("Effect"), "cause-mechanism-effect lanes");
}

/* cycle: ring nodes, arrows, active emphasis */
{
  const c = E.engCycle(["one", "two", "three"], 1);
  ok(c.includes("cy-node active") && c.includes("marker-end"), "cycle active node + directed arcs");
}

/* comparison: symmetry + computed differences */
{
  const t = E.engComparison(["Feature", "C3", "C4"],
    [["Habitats", "moist", "arid"], ["Shared", "same", "same"]]);
  ok(t.includes("cmp-matrix"), "comparison matrix");
  ok(t.includes("diff"), "differing cells highlighted");
  ok(t.includes("shared"), "shared rows marked");
  const wc = E.engWrongCorrect("myth", "why wrong", "truth", "why right");
  ok(wc.includes("wc-wrong") && wc.includes("wc-right") && wc.includes("why right"), "wrong/correct models");
  const solo = E.engSoloModel("wrong", "Common idea", "myth", "why wrong");
  ok(solo.includes("wc-model") && solo.includes("myth") && !solo.includes("wc-right"), "solo model fills its layer");
}

/* equation: structured, never raw latex */
{
  ok(E.engChem("CO2") === "CO₂" && E.engChem("H2O") === "H₂O", "chemical subscripts");
  ok(E.engFrac("F/m").includes("frac"), "fraction stacking");
  const e = E.engEquation({ lhs: [{ coefficient: "6", species: "CO2", note: "air" }],
    arrow: "→", rhs: [{ coefficient: "6", species: "O2", note: "" }], energy: "light" });
  ok(e.includes("coef") && e.includes("CO₂") && e.includes("eq-arrow"), "equation monument");
  ok(e.includes("eq-legend") && e.includes("air"), "annotation legend from notes");
  ok(!/\\[a-zA-Z]+\$\$/.test(e) && e.indexOf("$$") === -1, "no latex residue");
}

/* data: intent chooser + annotated figures */
{
  const cols = ["Pigment", "Blue (nm)", "Red (nm)", "Share (%)"];
  const rows = [{ "Pigment": "Chl a", "Blue (nm)": "430", "Red (nm)": "662", "Share (%)": "65" }];
  ok(E.engDataKind(cols, rows, "data_table") === "spectrum", "wavelength intent → spectrum");
  const spec = E.engData(cols, rows, "data_table");
  ok(spec.html.includes("sp-peak") && spec.html.includes("430"), "spectrum peaks annotated");
  ok(spec.html.includes("<table"), "source table preserved under figure");
  ok(E.engDataKind(["A", "V"], [{ A: "x", V: "1" }], "bar_chart") === "bars", "bar intent → bars");
  ok(E.engDataKind(["A", "V"], [{ A: "x", V: "1" }], "line_chart") === "line", "series intent → line");
  ok(E.engDataKind(["A", "X", "Y"], [{ A: "x", X: "1", Y: "2" }], "line_chart") === "scatter", "x/y pair → scatter");
}

/* concept map + image */
{
  const m = E.engConceptMap("Hub", ["a", "b", "c"], "causal", 0);
  ok(m.includes("cm-hub") && m.includes("cm-sat active"), "concept map hub + active satellite");
  const img = E.engImage(["assets/x.png"], "cap", "annotated", "kick");
  ok(img.includes("img-annotated") && img.includes("assets/x.png"), "annotated image layout");
  ok(E.engImage([], "cap", "hero") === "", "no assets → no figure");
}

console.log("engines: " + n + " assertions passed");
