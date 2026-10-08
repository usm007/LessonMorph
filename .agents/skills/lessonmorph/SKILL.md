---
name: lessonmorph
description: Turn educational documents (PDF, DOCX, Markdown, Text) into detailed, classroom-ready PowerPoint presentations (.pptx) with 100% source fidelity, teacher speaker notes, native OpenXML animations, and quality validation.
---

# LessonMorph: Document-to-Teaching-Presentation Compiler

LessonMorph compiles educational documents into editable, classroom-ready Microsoft PowerPoint presentations (`.pptx`).

It behaves like a **best friend for a teacher**:
- **100% Source Content Coverage** via the atomic Content Completeness Ledger.
- **Pedagogical Flow**: Onboarding (Title, Roadmap, Objectives, Prerequisites) → Core Definitions & Formulas → Worked Examples (Stepped Builds) → Common Misconceptions (Tempting Error vs Correct Reasoning) → 2-Stage Classroom Checks → Key Takeaways Summary → Practice & Exit Ticket.
- **Native Editable PowerPoint**: Uses real shapes, rounded cards, formatted text boxes, tables, and typography (never flattened images).
- **Explanation-Driven Animation**: Native OpenXML `<p:timing>` animation sequences for progressive step-by-step builds, misconception cross-outs, and answer reveals.
- **Rich Teacher Speaker Notes**: Every slide contains structured teacher guidance (Explanation, Emphasis, Ask Students, Likely Misconception, Transition, Optional Extension).
- **Automated Quality Gates**: Validates package integrity, 100% coverage ledger, speaker notes presence, and visual density.

## Quick Start / CLI Usage

To compile an educational document into a presentation:

```bash
python -m lessonmorph.cli compile <path/to/document> [-o <path/to/output.pptx>] [-w <path/to/work_dir>]
```

Example:

```bash
python -m lessonmorph.cli compile source/examples/photosynthesis_and_cellular_energy.md -o output/photosynthesis.pptx
```
