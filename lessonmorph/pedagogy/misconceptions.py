"""Misconception detection and pedagogical correction handler.

Identifies tempting but wrong ideas from source text or subject domain knowledge,
deconstructs the root error, and structures a visual comparison:
[Tempting Error (Crossed Out)] vs [Correct Reasoning (Verified)].
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from lessonmorph.core.models import ContentUnit, SubjectDomain


@dataclass
class StructuredMisconception:
    topic: str
    wrong_idea: str
    why_wrong: str
    correct_idea: str
    correct_reasoning: str
    source_unit_id: Optional[str] = None


class MisconceptionDetector:
    """Detects and structures educational misconceptions."""

    @classmethod
    def extract_from_content(cls, units: List[ContentUnit]) -> List[StructuredMisconception]:
        results: List[StructuredMisconception] = []

        for u in units:
            text = u.normalized_content
            # Check if this content unit discusses a misconception
            patterns = [
                r"(?:Common Misconception|Common Mistake|Frequent Error|Pitfall):\s*(.+?)(?:Why it is wrong|Correction|Correct:|\n\n|$)",
                r"(?:Students often assume|It is tempting to think|Do not confuse)\s*(.+?)(?:\. However|\. In reality|\. Instead|\. But|$)",
            ]
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
                if m:
                    wrong_idea = m.group(1).strip()
                    # Look for correction part
                    corr_match = re.search(
                        r"(?:Correction|Correct reasoning|In reality|Instead|Actually|Remember that):\s*(.+?)(?:\n\n|$)",
                        text,
                        re.IGNORECASE | re.DOTALL,
                    )
                    correct_idea = corr_match.group(1).strip() if corr_match else "Follow fundamental principles."
                    results.append(
                        StructuredMisconception(
                            topic=u.section_title or u.chapter_title,
                            wrong_idea=wrong_idea,
                            why_wrong="It overlooks critical qualifications or mathematical laws.",
                            correct_idea=correct_idea,
                            correct_reasoning=correct_idea,
                            source_unit_id=u.id,
                        )
                    )
                    break

        return results

    @classmethod
    def get_domain_misconceptions(cls, domain: SubjectDomain, topic_keywords: str) -> List[StructuredMisconception]:
        """Provides subject-grounded common misconceptions if explicitly relevant."""
        kw_lower = topic_keywords.lower()
        items: List[StructuredMisconception] = []

        if domain == SubjectDomain.MATHEMATICS:
            if any(k in kw_lower for k in ["fraction", "division", "cancel"]):
                items.append(
                    StructuredMisconception(
                        topic="Cancelling terms in fractions",
                        wrong_idea="(x + 3) / x = 3 by 'cancelling' x",
                        why_wrong="You can only cancel common factors across numerator and denominator, never terms in a sum.",
                        correct_idea="(x + 3) / x = 1 + 3/x",
                        correct_reasoning="Division distributes over addition: (x + 3)/x = x/x + 3/x = 1 + 3/x.",
                    )
                )
            if any(k in kw_lower for k in ["square", "power", "exponent"]):
                items.append(
                    StructuredMisconception(
                        topic="Squaring a binomial",
                        wrong_idea="(a + b)² = a² + b²",
                        why_wrong="Misses the middle cross-terms resulting from full distribution (FOIL).",
                        correct_idea="(a + b)² = a² + 2ab + b²",
                        correct_reasoning="(a + b)(a + b) = a·a + a·b + b·a + b·b = a² + 2ab + b².",
                    )
                )

        elif domain == SubjectDomain.PHYSICS:
            if any(k in kw_lower for k in ["gravity", "free fall", "weight"]):
                items.append(
                    StructuredMisconception(
                        topic="Gravitational Acceleration",
                        wrong_idea="Heavier objects fall faster than lighter objects in a vacuum.",
                        why_wrong="Equating gravitational force (which is larger on heavier mass) with acceleration.",
                        correct_idea="All objects experience identical gravitational acceleration g = 9.8 m/s².",
                        correct_reasoning="Since a = F/m and F = G·M·m/r², mass m cancels out, leaving acceleration mass-independent.",
                    )
                )
            if any(k in kw_lower for k in ["newton", "force", "motion"]):
                items.append(
                    StructuredMisconception(
                        topic="Motion and Force",
                        wrong_idea="A constant velocity requires a constant forward net force.",
                        why_wrong="Confusing velocity with acceleration; ignoring friction.",
                        correct_idea="Zero net force means constant velocity (Newton's First Law).",
                        correct_reasoning="A net force causes acceleration (change in speed/direction). Constant velocity requires net force ΣF = 0.",
                    )
                )

        elif domain == SubjectDomain.CHEMISTRY:
            if any(k in kw_lower for k in ["bond", "energy", "breaking"]):
                items.append(
                    StructuredMisconception(
                        topic="Chemical Bond Energy",
                        wrong_idea="Breaking chemical bonds releases energy.",
                        why_wrong="Confusing bond breaking with overall exothermic reaction net energy.",
                        correct_idea="Breaking bonds ALWAYS requires energy input (endothermic).",
                        correct_reasoning="Energy is absorbed to overcome electrostatic attraction between atoms. Energy is only released when new bonds form.",
                    )
                )

        elif domain == SubjectDomain.BIOLOGY:
            if any(k in kw_lower for k in ["respiration", "photosynthesis", "plant"]):
                items.append(
                    StructuredMisconception(
                        topic="Plant Respiration",
                        wrong_idea="Plants only do photosynthesis, while animals do cellular respiration.",
                        why_wrong="Confusing autotrophic food generation with universal metabolic energy production.",
                        correct_idea="Plants undergo cellular respiration continuously (24/7).",
                        correct_reasoning="Plants synthesize glucose via photosynthesis, but their cells must break down that glucose via respiration to generate ATP for cellular work.",
                    )
                )

        return items
