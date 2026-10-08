"""Tests for QuizEngine."""

from lessonmorph.core.models import ContentImportance, ContentType, ContentUnit, QuestionType
from lessonmorph.quiz.engine import QuizEngine


def test_quiz_generation():
    unit = ContentUnit(
        id="C010",
        source_location="Page 5",
        chapter_id="ch01",
        chapter_title="Chemistry",
        section_title="Acids and Bases",
        content_type=ContentType.DEFINITION,
        importance=ContentImportance.CORE,
        normalized_content="An acid is a substance that donates protons in an aqueous solution.",
    )

    q_mcq = QuizEngine.generate_quiz_for_concept(unit, QuestionType.MULTIPLE_CHOICE)
    assert q_mcq.question_type == QuestionType.MULTIPLE_CHOICE
    assert len(q_mcq.options) >= 3
    assert q_mcq.correct_answer.startswith("A)")
    assert len(q_mcq.distractor_rationales) > 0

    q_tf = QuizEngine.generate_quiz_for_concept(unit, QuestionType.TRUE_FALSE)
    assert q_tf.question_type == QuestionType.TRUE_FALSE
    assert q_tf.correct_answer == "True"
