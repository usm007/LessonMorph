# Quality Assurance & Validation Guide

## The 4 Quality Gates

Every generated presentation undergoes automatic validation before delivery:

### 1. Content QA
- Content Completeness Ledger audited for 100% coverage.
- Zero unmapped atomic units.
- Formulas, definitions, and tables preserved intact.

### 2. Structural QA
- Presentation package re-opened with OpenXML parser to confirm valid XML.
- Verifies that speaker notes exist across slides.
- Slide dimensions verified at 16:9 widescreen.

### 3. Visual QA
- Text length and density heuristics check that body paragraphs fit inside card dimensions.
- Slides exceeding character limits are flagged for human review.

### 4. Teaching QA
- Validates the pedagogical arc: onboarding, exposition, active checks, recap, and practice.
- Ensures checks occur after concepts have been taught, not before.

## Status Ratings

- **PASS**: All gates cleared without issues.
- **WARN**: Package valid and 100% coverage achieved, but minor warnings (e.g. dense text on 1 slide) flagged for human review.
- **FAIL**: Uncovered source content, corrupted presentation file, or missing pedagogical arc.
