# Pedagogical Intelligence Layer — Foundations & Constitution

The pedagogy layer sits **between content understanding and storyboard
generation**. Pipeline:

```text
SOURCE → UNDERSTAND → PEDAGOGICALLY PLAN → TEACH → ASSESS → VISUALIZE → ANIMATE → PRESENT
```

Primary question first: *"What instructional sequence gives these learners
the best chance of understanding, remembering, and applying this material?"*
Only then: *"How do I express that sequence in PowerPoint?"* Slide
aesthetics, slide count, and template convenience must never determine
instructional sequence.

## Machine-readable interfaces

```text
content model (ContentUnit / ledger)
        ↓
pedagogical model (PedagogicalPlan — plan of record, inspectable pre-render)
        ↓
storyboard model (SlideSpec + instructional_state/purpose + objective_ids)
        ↓
PPTX renderer
```

Inspect `work/<doc>/pedagogical_plan_<chapter>.json|.md` before rendering.
Acceptance: a reviewer can answer what students must learn, what they must
know first, why each concept/example/question is placed here, where retrieval
/ guided / independent practice happens, which misconception is addressed,
how support fades (I DO → WE DO → YOU DO), and how objectives are assessed.

## Decision principles (used when appropriate — never a checklist)

- **Backward design** (Wiggins & McTighe): objectives first, then
  instruction/practice/assessment. Objectives use observable verbs
  (identify, define, explain, compare, classify, calculate, interpret,
  predict, apply, analyse, evaluate, construct).
- **Constructive alignment** (Biggs): every objective is taught → practised →
  assessed. Never assess untaught content except labelled prior-knowledge
  recall / diagnostics.
- **Cognitive load** (Sweller): chunk intrinsic load, cut extraneous load,
  invest in germane effort. Goal is *manageable complexity*, not
  simplification at the expense of content. Dense sources split across
  slides; details move to speaker notes.
- **Multimedia / dual coding** (Mayer; Paivio): explanation + meaningful
  visual. No decorative or redundant visuals. Process → animated sequence;
  structure → labelled diagram; comparison → aligned comparison;
  quantity → chart; transformation → before/after.
- **Scaffolding + worked-example effect + gradual release** (I DO → WE DO →
  YOU DO TOGETHER → YOU DO): procedures get full examples before practice,
  then faded support. Never jump from explanation to hard independent work.
- **Retrieval, spacing, interleaving**: purposeful recall throughout (opening,
  after concepts, cumulative, exit) — recall/explain/apply, not recognition
  of visible text. Revisit important ideas; mix related problem types only
  when it helps.
- **Generative learning + formative assessment**: predict, explain, classify,
  justify, teach-back. Every check has a purpose (remember / understand /
  apply / misconception / pacing signal) — no arbitrary quizzes.
- **Misconception-based instruction + feedback**: plausible misconceptions
  only (intuitive idea → why it seems right → conflict → correct
  explanation → check). Feedback explains *why*, with per-distractor
  rationales.
- **Prior-knowledge activation + concrete→representational→abstract +
  elaboration + deliberate practice**: dependency chains with no hidden
  prerequisites; CRA where natural (never forced); pacing follows
  complexity (slow/small-chunked for hard concepts, faster for facts,
  extended for procedures).

## No universal recipe

Strategy = f(subject, topic, content type, learner, objective, complexity,
misconceptions, time). Procedural maths leans on worked examples + gradual
release; biology processes on visualisation + sequencing + prediction;
history on context + chronology + causation; language on contrast + guided
production. See `lessonmorph/pedagogy/strategies.py` (strategy table) and
`sequencing.py` (adaptive instructional states).

## Pedagogical Constitution (permanent rules)

1. Teach for understanding, not merely exposure.
2. Preserve important source content without unnecessary cognitive overload.
3. Start from learning outcomes and work backward.
4. Align instruction, practice and assessment.
5. Activate relevant prior knowledge.
6. Introduce complexity progressively.
7. Use worked examples for procedures and problem solving.
8. Gradually remove scaffolding.
9. Require learners to retrieve and generate knowledge.
10. Revisit important ideas.
11. Use meaningful formative assessment.
12. Explain mistakes rather than merely marking them wrong.
13. Address plausible misconceptions.
14. Use visuals and animation when they clarify meaning.
15. Never use visual effects merely to impress (every animation stores its
    instructional `purpose`: signalling, sequencing, transformation, causal
    explanation, comparison, highlighting, decomposition/reconstruction,
    error correction, answer reveal).
16. Choose pedagogy per learning task — never force a universal pattern.
17. Respect the role of the teacher.
18. The presentation is a teaching aid, not a replacement teacher.

## Evidence discipline

Do not attribute unsupported claims to research; do not invent learning
science terminology. Conceptual touchstones: Wiggins & McTighe (backward
design), Biggs (constructive alignment), Sweller (cognitive load), Mayer
(multimedia learning), Paivio (dual coding), Vygotsky / Wood et al.
(scaffolding), Rosenshine (explicit instruction / gradual release),
Roediger/Karpicke (retrieval), Cepeda (spacing), Rohrer/Taylor
(interleaving), Black & Wiliam (formative assessment), Chi/Wittrock
(generative learning), Vosniadou (misconceptions), Hattie & Timperley
(feedback), Ericsson (deliberate practice). The goal is sound software
foundations, not academic claims inside decks.
