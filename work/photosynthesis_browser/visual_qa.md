# VISUAL QUALITY GATE (browser, primary renderer)

Overall: `WARN`

## Regression benchmark

- opener: inspected s01
- definition: inspected s05
- equation: inspected s07
- chloroplast diagram: inspected s08
- worked calculation: inspected s10
- misconception: inspected s12
- question: inspected s06
- electron pathway: present
- c3/c4 comparison: present
- answer states: s06, s09, s11, s13, s23
- synthesis: s22

## VISUAL QA (static)

Status: `WARN`

| Scene | Code | Severity | Detail | Repair |
| :--- | :--- | :---: | :--- | :--- |
| s09 | title-treatment | WARNING | repeats 'Check for Understanding' from s06 | vary or drop the repeat |
| s11 | title-treatment | WARNING | repeats 'Check for Understanding' from s06 | vary or drop the repeat |
| s13 | title-treatment | WARNING | repeats 'Check for Understanding' from s06 | vary or drop the repeat |
| s16 | title-treatment | WARNING | repeats 'Recall & Reconstruct' from s14 | vary or drop the repeat |
| s18 | title-treatment | WARNING | repeats 'Practice Problem (source)' from s17 | vary or drop the repeat |
| s19 | title-treatment | WARNING | repeats 'Recall & Reconstruct' from s14 | vary or drop the repeat |
| s21 | title-treatment | WARNING | repeats 'Recall & Reconstruct' from s14 | vary or drop the repeat |
| s23 | title-treatment | WARNING | repeats 'Check for Understanding' from s06 | vary or drop the repeat |
| s01 | title-treatment | WARNING | 10 scenes share 'Chapter 4: Photosynthesis and the Transformation o' | give scenes distinct titles upstream (IR-level) |

## VISUAL QA (rendered)

Status: `WARN`
Shots: `72`

| Scene | State | Severity | Detail |
| :--- | :--- | :---: | :--- |
| s10 | s3 | WARNING | text auto-scaled to 78% — consider splitting the scene |
| s10 | s5 | WARNING | text auto-scaled to 78% — consider splitting the scene |
| s18 | s2 | WARNING | note auto-scaled to 78% — consider splitting the scene |
| s18 | s3 | WARNING | note auto-scaled to 78% — consider splitting the scene |