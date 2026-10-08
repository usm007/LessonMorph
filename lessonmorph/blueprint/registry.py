"""Visual grammar registry — the single source of truth for representations.

The finite grammar lives in `ir.Representation`; legal task bindings in
`ir.TASK_FAMILIES`; conflated here with repair fallbacks so validators,
the adapter, and documentation all read the same table. The renderer
executes entries from this registry and nothing else.
"""

from __future__ import annotations
from typing import Dict, List
from lessonmorph.blueprint.ir import (
    REPAIR_FALLBACK,
    TASK_FAMILIES,
    Representation,
    TaskType,
)


def tasks_for(rep: Representation) -> List[TaskType]:
    """All cognitive tasks a representation may legally serve."""
    return [t for t, reps in TASK_FAMILIES.items() if rep in reps]


def representations_for(task: TaskType) -> List[Representation]:
    """All representations legal for a task (first = default)."""
    return list(TASK_FAMILIES[task])


def fallback_for(rep: Representation) -> Representation | None:
    """Simpler same-family representation for the repair loop (or None)."""
    return REPAIR_FALLBACK.get(rep)


REGISTRY: Dict[str, Dict[str, object]] = {
    rep.value: {"tasks": [t.value for t in tasks_for(rep)],
                "fallback": (REPAIR_FALLBACK[rep].value if rep in REPAIR_FALLBACK else None)}
    for rep in Representation
}
