"""Subject and presentation strategy classifier.

Classifies subject domains (Mathematics, Physics, Chemistry, Biology, History,
Geography, Literature, etc.) and determines subject-aware presentation strategies.
"""

from __future__ import annotations
import re
from typing import Dict, List, Set
from lessonmorph.core.models import SubjectDomain


DOMAIN_KEYWORDS: Dict[SubjectDomain, Set[str]] = {
    SubjectDomain.MATHEMATICS: {
        "equation", "algebra", "variable", "coefficient", "fraction", "polynomial",
        "factor", "integral", "derivative", "function", "graph", "coordinate",
        "triangle", "geometry", "theorem", "calculate", "simplify", "solve",
        "quadratic", "root", "roots", "linear", "matrix", "arithmetic", "formula"
    },
    SubjectDomain.PHYSICS: {
        "force", "velocity", "acceleration", "gravity", "mass", "friction", "kinetic",
        "potential", "momentum", "energy", "newton", "vector", "electric", "current",
        "circuit", "voltage", "wave", "frequency", "thermodynamics", "motion"
    },
    SubjectDomain.CHEMISTRY: {
        "molecule", "atom", "reaction", "bond", "acid", "base", "solution", "solvent",
        "element", "compound", "catalyst", "electron", "proton", "neutron", "periodic",
        "stoichiometry", "equilibrium", "molar", "concentration"
    },
    SubjectDomain.BIOLOGY: {
        "cell", "organism", "photosynthesis", "dna", "gene", "mitosis", "meiosis",
        "species", "ecosystem", "respiration", "enzyme", "protein", "membrane",
        "tissue", "organ", "evolution", "mutation", "chloroplast"
    },
    SubjectDomain.HISTORY: {
        "century", "revolution", "empire", "treaty", "monarchy", "war", "battle",
        "reign", "civilization", "dynasty", "colony", "constitution", "era", "chronology"
    },
    SubjectDomain.GEOGRAPHY: {
        "plateau", "glacier", "latitude", "longitude", "climate", "erosion", "topography",
        "tectonic", "volcano", "river", "delta", "basin", "precipitation", "biome"
    },
    SubjectDomain.LITERATURE: {
        "metaphor", "simile", "stanza", "poem", "protagonist", "theme", "narrator",
        "symbolism", "allegory", "irony", "rhyme", "meter", "soliloquy", "prose"
    },
    SubjectDomain.LANGUAGE: {
        "grammar", "tense", "syntax", "verb", "noun", "adjective", "clause",
        "preposition", "conjugation", "pronoun", "punctuation", "predicate"
    },
    SubjectDomain.COMPUTER_SCIENCE: {
        "algorithm", "binary", "data structure", "recursion", "array", "compiler",
        "complexity", "object", "class", "database", "network", "function", "pointer"
    },
}


class SubjectClassifier:
    """Classifies content text and suggests subject-aware visual structures."""

    @classmethod
    def classify_domain(cls, text: str) -> SubjectDomain:
        text_lower = text.lower()
        scores: Dict[SubjectDomain, int] = {domain: 0 for domain in SubjectDomain}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                matches = len(re.findall(r"\b" + re.escape(kw) + r"\b", text_lower))
                scores[domain] += matches

        best_domain, max_score = max(scores.items(), key=lambda item: item[1])
        if max_score >= 2:
            return best_domain
        return SubjectDomain.GENERAL

    @classmethod
    def select_visual_strategy(cls, domain: SubjectDomain, content_text: str) -> str:
        """Chooses the instructional visual model matching the subject and concept nature."""
        text_lower = content_text.lower()

        # Check for sequence / process cues
        if any(w in text_lower for w in ["step 1", "phase", "cycle", "procedure", "stages", "flow", "first, then"]):
            return "process_flow"

        # Check for comparison / versus cues
        if any(w in text_lower for w in ["versus", "vs", "compare", "difference between", "contrast", "advantage"]):
            return "2_column_compare"

        # Check for misconception cues
        if any(w in text_lower for w in ["mistake", "misconception", "incorrectly", "pitfall", "wrong", "watch out"]):
            return "common_misconception"

        # Check for formulas / mathematical derivations
        if domain in (SubjectDomain.MATHEMATICS, SubjectDomain.PHYSICS, SubjectDomain.CHEMISTRY):
            if any(sym in content_text for sym in ["=", "+", "×", "/", "^", "→", "λ", "θ", "π", "Δ"]):
                return "formula_breakdown"

        # Check for classification / categories
        if any(w in text_lower for w in ["classified into", "types of", "categories", "kinds of", "grouped into"]):
            return "classification_grid"

        # Domain default strategies
        if domain == SubjectDomain.HISTORY:
            return "timeline"
        elif domain in (SubjectDomain.BIOLOGY, SubjectDomain.GEOGRAPHY):
            return "diagram_explanation"
        elif domain in (SubjectDomain.MATHEMATICS, SubjectDomain.PHYSICS):
            return "stepped_cards"

        return "stepped_cards"
