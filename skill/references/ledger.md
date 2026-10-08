# Content Completeness Ledger Guide

## The 100% Coverage Invariant

In LessonMorph, presentation length is dictated by content fidelity, never by arbitrary slide caps. The Content Completeness Ledger ensures that no definitions, explanations, formulas, examples, exceptions, or tables are compressed away.

### Content Unit Schema

Each atomic unit receives a sequential identifier (`C001`, `C002`, ...) and tracks:
- `id`: Unique identifier
- `source_location`: Page number, section title, and paragraph block
- `chapter_id`: Section/chapter grouping
- `content_type`: `definition`, `formula`, `example`, `worked_step`, `misconception`, `table`, `diagram`, `exercise`, `explanation`
- `importance`: `core`, `supporting`, `extension`
- `normalized_content`: Extracted text and notation
- `intended_destination`: Target slide reference (e.g. `Slide 5`)
- `covered`: Boolean flag
- `covered_slides`: List of all slide IDs presenting this content

### Validation Gate

At validation time, the ledger must report:
```text
TOTAL UNITS: N
COVERED: N
UNCOVERED: 0
```
If any meaningful unit remains uncovered, the quality gate triggers a failure.
