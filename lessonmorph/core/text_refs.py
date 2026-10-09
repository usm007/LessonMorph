"""Content-derived references: terms, headlines, and sentence-safe clips.

Neutral helpers shared by pedagogy (objectives) and the IR adapter (titles,
definition payloads). Everything is EXTRACTED from source wording — these
functions never invent terms, and return None/"" when nothing is derivable
so callers fall back honestly instead of fabricating.
"""

from __future__ import annotations
import re
from typing import List, Optional, Tuple


def strip_markup_line(text: str) -> str:
    """One line, markdown/numbering stripped, single-spaced."""
    t = re.sub(r"^#{1,6}\s+", "", text.strip())
    t = re.sub(r"^\d+\.\s+", "", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" -–—:\t")


def split_sentences(text: str) -> List[str]:
    """Split into sentences without breaking abbreviations or decimals."""
    t = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“$])", t)
    return [p.strip() for p in parts if p.strip()]


def first_sentences(text: str, max_sentences: int = 2, max_chars: int = 260) -> str:
    """First whole sentences only. A single over-long sentence falls back to
    a marked word-clip (detail state always holds the full wording)."""
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= max_chars:
        return t
    out: List[str] = []
    total = 0
    for sent in split_sentences(t):
        if out and (len(out) >= max_sentences or total + len(sent) > max_chars):
            break
        out.append(sent)
        total += len(sent)
    joined = " ".join(out)
    if joined and len(joined) <= max_chars:
        return joined
    return clip_words(t, max_chars)


def clip_words(text: str, max_chars: int) -> str:
    """Word-boundary clip (no mid-word cuts); ellipsis only when shortened."""
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars].rsplit(" ", 1)[0]
    return (cut or t[:max_chars]).rstrip(" ,;:") + "…"


def clip_sentences(text: str, max_chars: int) -> str:
    """Shorten to whole sentences within max_chars; word-clip only as fallback."""
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= max_chars:
        return t
    sents = split_sentences(t)
    out: List[str] = []
    total = 0
    for sent in sents:
        if out and total + len(sent) > max_chars:
            break
        out.append(sent)
        total += len(sent)
    if out and len(" ".join(out)) < len(t):
        joined = " ".join(out)
        return joined if len(joined) >= max_chars // 3 else clip_words(t, max_chars)
    return clip_words(t, max_chars)


def short_headline(text: str, max_chars: int = 80) -> str:
    """Scene-title/kicker candidate: first line, cleaned, word-clipped."""
    first = (text.strip().split("\n")[0] if text.strip() else "")
    return clip_words(strip_markup_line(first), max_chars)


_NON_HEADING_PREFIXES = (
    "common mistake", "misconception", "definition", "question",
    "practice problem", "exercise", "warning", "example",
    "why it is", "correct reasoning", "correction",
)
_TASK_VERBS = (
    "trace", "contrast", "compare", "calculate", "compute", "determine",
    "explain", "solve", "describe", "predict", "identify", "define",
    "list", "name",
)


def is_heading_block(block: str) -> bool:
    """A block that is only a section heading (no teachable content).

    - Markdown headings are structure, unless they carry a task after the
      colon ("Practice Problem 1: Trace…") or a question.
    - Label prefixes ("Common Mistake:", "Definition:", …) always signal
      content, never a bare heading.
    - Math/formula blocks are never headings.
    """
    lines = [l for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return True
    if len(lines) > 1:
        return False
    line = lines[0].strip()
    if re.search(r"\$\$|\\[a-zA-Z]+|→|\\longrightarrow", line):
        return False
    if re.match(r"^#{1,6}\s+\S", line):
        bare = strip_markup_line(line)
        if "?" in bare:
            return False
        low = bare.lower()
        if any(low.startswith(p) for p in _NON_HEADING_PREFIXES):
            return False
        if re.match(r"^step\s*\d+\b", low):
            return False
        if ":" in bare:
            after = bare.split(":", 1)[1]
            if re.match(r"^\s*(" + "|".join(_TASK_VERBS) + r")\b", after,
                        re.IGNORECASE):
                return False
        return True
    bare = strip_markup_line(line)
    if "?" in bare or ":" in bare or len(bare) >= 150:
        return False
    if re.search(r"\b(" + "|".join(_TASK_VERBS) + r")\b", bare, re.IGNORECASE):
        return False
    return bool(re.match(r"^\d*\.?\s*[A-Z]", bare)) or len(bare.split()) <= 10


def split_heading(block: str) -> Tuple[Optional[str], str]:
    """Split a leading markdown heading line off a block. Returns (heading, rest)."""
    lines = block.strip().splitlines()
    if lines and re.match(r"^#{1,6}\s+\S", lines[0].strip()):
        heading = strip_markup_line(lines[0])
        rest = "\n".join(lines[1:]).strip()
        if rest:
            return heading, rest
    return None, block


_LABEL_PREFIX = re.compile(
    r"^(?:\*\*)?(?:practice\s+problem|worked\s+(?:example|calculation)|example|question"
    r"|exercise|problem|task)\s*\d*\s*(?:\*\*)?\s*[:.]\s*", re.IGNORECASE)
_STEP_PREFIX = re.compile(r"^\**step\s*\d+\s*[:.)]\s*", re.IGNORECASE)


_LEADING_LABEL = re.compile(
    r"^(?:\*\*)?([A-Za-z][A-Za-z0-9 /'()&.,-]{1,44})\s*:\s*", re.UNICODE)
# Labels that are pure structure: they name nothing on their own.
_STRUCTURE_LABEL = re.compile(
    r"^(?:step\s*\d*|where|why|how|when|what|which|question|answer|solution)\s*$",
    re.IGNORECASE)


def leading_label(text: str) -> Optional[str]:
    """The semantic label the source puts on this block ("Common Mistake",
    "Correct Reasoning", "Practice Problem 1"), or None.

    Structural markers ("Step 3:", "Where:") are NOT labels — they name no
    content, so callers never build a title or topic from them.
    """
    m = _LEADING_LABEL.match(strip_markup_line(text or ""))
    if not m:
        return None
    lab = m.group(1).strip().strip(" -–—.")
    if not lab or _STRUCTURE_LABEL.match(lab):
        return None
    return lab


def section_topic(section: str) -> Optional[str]:
    """A short noun phrase naming what a section covers.

    Numbering is removed ("2. The Overall…" -> "The Overall…"); the section's
    own descriptive prefix ("Common Misconception:", "Worked Calculation:")
    is kept because it says what kind of content it is. Returns None when
    nothing is derivable so callers fall back honestly.
    """
    t = re.sub(r"\s+", " ", strip_markup_line(section or "")).strip()
    t = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", t).strip(" -–—:")
    if not t:
        return None
    return t if len(t) <= 70 else clip_words(t, 70)


def is_step_fragment(text: str) -> bool:
    """A numbered step of a worked example — never a learning outcome of its own."""
    return bool(_STEP_PREFIX.match(text.strip()))


def task_sentence(text: str) -> Optional[str]:
    """The genuine task stated in this wording, or None.

    Returns one whole sentence that either asks a question or directs the
    reader with an observable verb ("Determine the theoretical moles…",
    "Trace the path of an electron…"). Structural labels ("Example:",
    "Practice Problem 1:", "Step 2:") are stripped before matching. Never a
    meta-instruction, never a fragment — callers get None instead.
    """
    t = re.sub(r"\s+", " ", _LABEL_PREFIX.sub("", text.strip())).strip()
    t = _STEP_PREFIX.sub("", t).strip()
    if not t:
        return None
    for sent in split_sentences(t):
        s = sent.strip()
        if not s or len(s.split()) < 8:
            continue
        if "?" in s:
            return s
        if re.match(r"^(?:" + "|".join(_TASK_VERBS) + r")\b", s, re.IGNORECASE):
            return s
    return None


def is_equation(text: str) -> bool:
    """True only for a standalone relationship (display math or a compact
    identity). Prose that merely contains inline math is NOT an equation —
    callers must not build "Use the relationship …" objectives from it."""
    raw = re.sub(r"\s+", " ", text.strip())
    if raw.startswith(("$$", "\\[", "\\(")):
        return True
    if len(raw) > 90 or len(split_sentences(raw)) > 1:
        return False
    return bool(re.search(r"(=|→|≈|\\approx|\\longrightarrow|\\frac)", raw))


def extract_term(text: str) -> Optional[str]:
    """The defined term from definition wording, or None (never guessed)."""
    t = text.strip()
    m = re.search(r"\*\*Definition\*\*\s*:?\s*\**(.+?)\*\*\s*(?:is|refers to|means)", t,
                  re.IGNORECASE | re.DOTALL)
    if m:
        return strip_markup_line(m.group(1))[:60] or None
    # "**Definition**: Term is …" — term is the lead noun phrase before the verb.
    m = re.search(r"\*\*Definition\*\*\s*:?\s*([A-Z][\w\-]*(?:\s+[A-Za-z][\w\-]*){0,4}?)\s+"
                  r"(?:is|are|refers to|means)\b", t)
    if m:
        return strip_markup_line(m.group(1))[:60] or None
    m = re.search(r"(.+?)\s+is defined as\s+", t, re.IGNORECASE | re.DOTALL)
    if m and len(m.group(1).split()) <= 6:
        return strip_markup_line(m.group(1))[:60] or None
    m = re.search(r"^\**(.+?)\*\*\s*:\s*(?:is|refers to|means)\b", t,
                  re.IGNORECASE | re.DOTALL)
    if m and len(m.group(1).split()) <= 6:
        return strip_markup_line(m.group(1))[:60] or None
    m = re.search(r"^([A-Z][\w\- ]{1,40}?)\s+(?:is|refers to|means that)\b", t)
    if m:
        return strip_markup_line(m.group(1))[:60] or None
    return None
