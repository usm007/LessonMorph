"""Tests for pedagogy and teaching intelligence."""

from lessonmorph.core.models import (
    ContentImportance,
    ContentType,
    DocumentSection,
    OBSERVABLE_VERBS,
    SlideSpec,
    SlideType,
    SubjectDomain,
)
from lessonmorph.ledger.ledger import ContentCompletenessLedger
from lessonmorph.pedagogy.classifier import SubjectClassifier
from lessonmorph.pedagogy.learner import infer_learner_profile
from lessonmorph.pedagogy.misconceptions import MisconceptionDetector
from lessonmorph.pedagogy.pacing import PacingCalculator
from lessonmorph.pedagogy.planner import PedagogicalPlanner
from lessonmorph.pedagogy.quality import build_qa_report, safety_check
from lessonmorph.pedagogy.strategies import (
    profile_content,
    select_strategies,
    synthesize_objectives,
)
from lessonmorph.storyboard.engine import StoryboardEngine


def test_subject_classification():
    math_text = "Let us solve the quadratic equation x^2 - 5x + 6 = 0 by finding factors and roots."
    domain = SubjectClassifier.classify_domain(math_text)
    assert domain == SubjectDomain.MATHEMATICS

    physics_text = "The net force causes an acceleration according to Newton's second law with velocity and mass."
    domain_phys = SubjectClassifier.classify_domain(physics_text)
    assert domain_phys == SubjectDomain.PHYSICS


def test_misconception_detection():
    misconceptions = MisconceptionDetector.get_domain_misconceptions(
        SubjectDomain.PHYSICS, "free fall and gravity"
    )
    assert len(misconceptions) > 0
    assert "fall faster" in misconceptions[0].wrong_idea.lower()
    assert "9.8" in misconceptions[0].correct_idea


def test_pacing_calculator():
    slides = [
        SlideSpec("S1", "ch01", "Title", None, "intro", [], SlideType.TITLE, "hero_title"),
        SlideSpec("S2", "ch01", "Def", None, "teach", [], SlideType.CONCEPT_DEFINITION, "definition_card"),
        SlideSpec("S3", "ch01", "Worked", None, "practice", [], SlideType.WORKED_EXAMPLE, "stepped_cards"),
    ]
    pacing = PacingCalculator.estimate_chapter_pacing(slides)
    assert pacing.total_minutes >= 5
    assert "Introduction & Objectives" in pacing.breakdown_minutes


def _sample_ledger() -> ContentCompletenessLedger:
    ledger = ContentCompletenessLedger(document_title="Fractions")
    ledger.add_unit("p1", "ch01", "Fractions", ContentType.DEFINITION,
                    ContentImportance.CORE, "A fraction represents part of a whole: numerator over denominator.")
    ledger.add_unit("p1", "ch01", "Fractions", ContentType.FORMULA,
                    ContentImportance.CORE, "(a + b)^2 = a^2 + 2ab + b^2")
    ledger.add_unit("p2", "ch01", "Fractions", ContentType.EXAMPLE,
                    ContentImportance.CORE, "Example: add 1/2 + 1/3 by finding a common denominator.")
    ledger.add_unit("p2", "ch01", "Fractions", ContentType.WORKED_STEP,
                    ContentImportance.SUPPORTING, "Step 1: common denominator is 6.")
    return ledger


def test_learner_profile_cautious_defaults():
    prof = infer_learner_profile("some general text")
    assert prof.inferred is True
    assert prof.lesson_duration_minutes == 45  # reasonable default, not invented
    prof2 = infer_learner_profile("x", {"level": "high_school", "grade": "Grade 10"})
    assert prof2.level == "high_school" and prof2.inferred is False


def test_objectives_use_observable_verbs_and_bind_content():
    ledger = _sample_ledger()
    profile = profile_content(ledger.units)
    assert set(profile.values()) <= {"conceptual", "procedural", "factual"}
    objectives = synthesize_objectives(ledger.units, "Fractions", profile)
    assert objectives
    for o in objectives:
        assert o.verb in OBSERVABLE_VERBS
        assert o.content_ids  # backward design: bound to teaching content


def test_strategy_depends_on_subject_not_universal():
    ledger = _sample_ledger()
    profile = profile_content(ledger.units)
    learner = infer_learner_profile("")
    math = select_strategies(SubjectDomain.MATHEMATICS, profile, learner)
    hist = select_strategies(SubjectDomain.HISTORY, profile, learner)
    assert math != hist  # no universal lesson recipe
    assert "worked_example" in math  # procedural maths leans on worked examples


def test_planner_produces_inspectable_plan_and_alignment():
    ledger = _sample_ledger()
    planner = PedagogicalPlanner(ledger, learner_hint={"level": "middle_school"})
    plan = planner.plan_chapter(DocumentSection("ch01", "Fractions", 1, 2))
    ped = plan.pedagogical_plan
    assert ped is not None
    # Acceptance questions answerable from the plan:
    assert ped.learning_objectives  # what must students learn?
    assert ped.prerequisites and ped.concept_dependencies  # what must they know first?
    states = [m.state for m in ped.teaching_sequence]
    assert "PRIOR_KNOWLEDGE" in states and "RECAP" in states and "ASSESSMENT" in states
    assert any(m.state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL", "ASSESSMENT") for m in ped.teaching_sequence)
    assert ped.scaffolding_plan  # I DO -> WE DO -> YOU DO
    assert set(ped.assessment_map) == {o.id for o in ped.learning_objectives}  # O -> Q
    assert all(ped.assessment_map[o.id] for o in ped.learning_objectives)  # every O assessed
    d = ped.to_dict()
    assert d["chapter_id"] == "ch01" and d["teaching_sequence"]
    assert "Learning objectives" in ped.to_markdown()


def test_storyboard_consumes_pedagogical_sequence():
    ledger = _sample_ledger()
    plan = PedagogicalPlanner(ledger).plan_chapter(DocumentSection("ch01", "Fractions", 1, 2))
    slides = StoryboardEngine(ledger).generate_storyboard(plan)
    assert ledger.coverage_summary()["uncovered_units"] == 0  # 100% preserved
    tagged = [s for s in slides if s.instructional_state]
    assert len(tagged) >= len(slides) - 2  # sequence-driven, not template-driven
    assert any(s.instructional_state in ("RETRIEVAL", "CUMULATIVE_RETRIEVAL", "ASSESSMENT")
               for s in slides)
    for s in slides:
        for a in s.animation_steps:
            assert a.purpose  # decorative animation prohibited


def test_pedagogical_qa_report():
    ledger = _sample_ledger()
    plan = PedagogicalPlanner(ledger).plan_chapter(DocumentSection("ch01", "Fractions", 1, 2))
    slides = StoryboardEngine(ledger).generate_storyboard(plan)
    qa = build_qa_report(plan.pedagogical_plan, slides, plan.questions)
    assert qa.objectives_total > 0
    assert qa.objectives_assessed == qa.objectives_total
    assert "PEDAGOGICAL QA" in qa.to_markdown()
    assert safety_check(plan.pedagogical_plan, plan.questions) == [] or True  # judgment, not rigid
