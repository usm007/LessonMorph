"""Central text sanitization: no Markdown / LaTeX may ever reach a slide.

All rendered text passes through `clean()`. Math passes through
`latex_to_unicode()` so equations typeset as clean readable notation.
"""

from __future__ import annotations
import re

_GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "lambda": "λ", "mu": "μ",
    "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ",
    "tau": "τ", "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Sigma": "Σ", "Omega": "Ω",
}

_SUB = str.maketrans("0123456789+-=aeohklmnpstx", "₀₁₂₃₄₅₆₇₈₉₊₋₌ₐₑₒₕₖₗₘₙₚₛₜₓ")
_SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")


def _replace_sub(m: re.Match) -> str:
    return m.group(1).translate(_SUB)


def _replace_sup(m: re.Match) -> str:
    return m.group(1).translate(_SUP)


def latex_to_unicode(text: str) -> str:
    """Convert common LaTeX math to readable Unicode. Never emits backslashes."""
    if not text:
        return ""
    t = text
    t = t.replace("$$", "").replace("\\[", "").replace("\\]", "").replace("\\(", "").replace("\\)", "")
    # Resolve nested \text{..} inside \frac args first: iterate to fixpoint.
    for _ in range(5):
        prev = t
        t = re.sub(r"\\d?frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", t)
        t = re.sub(r"\\(?:text|mathrm|mathbf|mathit|ce)\{([^{}]*)\}", r"\1", t)
        if t == prev:
            break
    for name, glyph in _GREEK.items():
        t = t.replace("\\" + name, glyph)
    t = t.replace("\\times", "×").replace("\\cdot", "·").replace("\\approx", "≈")
    t = t.replace("\\longrightarrow", "→").replace("\\rightarrow", "→")
    t = t.replace("\\leftarrow", "←").replace("\\neq", "≠").replace("\\pm", "±")
    # _{...} / ^{...} then single-char _x ^x
    t = re.sub(r"_\{([^{}]+)\}", _replace_sub, t)
    t = re.sub(r"\^\{([^{}]+)\}", _replace_sup, t)
    t = re.sub(r"_([0-9A-Za-z+\-=])", _replace_sub, t)
    t = re.sub(r"\^([0-9A-Za-z+\-=()n])", _replace_sup, t)
    t = t.replace("\\", "").replace("{", "").replace("}", "")
    t = t.replace("$", "")  # single-dollar math delimiters are never literal here
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def clean(text: str) -> str:
    """Strip Markdown + LaTeX residue for slide-safe plain text."""
    if not text:
        return ""
    t = latex_to_unicode(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)  # bold
    t = re.sub(r"__(.+?)__", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.MULTILINE)  # headings
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)  # links
    t = re.sub(r"^\s*[-*]\s+", "", t, flags=re.MULTILINE)  # bullets (composer re-adds structure)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def contains_markup(text: str) -> str:
    """Return the kind of leaked markup found, or '' if clean."""
    if not text:
        return ""
    if re.search(r"\\[a-zA-Z]+|\$\$", text):
        return "latex"
    if re.search(r"\*\*.+?\*\*|`[^`]+`|#{1,6}\s+\S|\[[^\]]+\]\(http", text):
        return "markdown"
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    pipes = [l for l in lines if l.startswith("|") and l.endswith("|")]
    if len(pipes) >= 2 or (pipes and re.search(r"\| *-+:?-+", text)):
        return "markdown"
    return ""
