# Usage

## Install

```bash
pip install -r requirements.txt
```

## Compile a document

```bash
python -m lessonmorph.cli compile <document> [-o output.pptx] [-w work_dir]
```

Supported: `.pdf`, `.docx`/`.doc`, `.md`/`.markdown`/`.txt`.

## Teach from the output

1. Open the `.pptx` in Microsoft PowerPoint (reference runtime).
2. Teach front-to-back; click to reveal steps, misconception corrections, and quiz answers.
3. Read speaker notes for explanation, emphasis, oral questions, misconceptions, transitions, extensions.
4. Use Summary for recap, Practice for desk work/homework, Exit Ticket to close.

## Review quality

Open `work/<doc>/validation_report.md`:
- `PASS` = ready. `WARN` = ready with flagged slides to eyeball. `FAIL` = do not teach yet (uncovered units / corrupt package).
- Check `content_ledger.md` for the unit→slide map and `asset_warnings.md` if present.

## Classroom tips

- Give 30–45s thinking time on Question slides before advancing to the Answer slide.
- Pause after each revealed worked-example step; ask "what's next?" before clicking.
- The deck is long by design (fidelity > brevity); skip Optional Extension notes if time is short.
