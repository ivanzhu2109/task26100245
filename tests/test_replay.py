"""replay 的行为测试。"""
import pytest

from survey_branch import (
    BranchError,
    Const,
    Edge,
    ErrorKind,
    Finished,
    MemberOf,
    NextQuestion,
    Question,
    QuestionType,
    Survey,
    replay,
)


@pytest.fixture()
def survey():
    questions = {
        "q1": Question("q1", QuestionType.YES_NO),
        "q2": Question("q2", QuestionType.RATING),
        "q3": Question("q3", QuestionType.SINGLE_CHOICE, ("A", "B")),
    }
    return Survey(
        questions=questions,
        edges={
            "q1": [
                Edge(MemberOf("q1", (True,)), "q2"),
                Edge(MemberOf("q1", (False,)), "q3"),
            ],
        },
        root_id="q1",
    )


def test_empty_prefix_waits_at_root(survey):
    assert replay(survey, []) == NextQuestion("q1")


def test_partial_prefix_returns_next_question(survey):
    assert replay(survey, [("q1", True)]) == NextQuestion("q2")
    assert replay(survey, [("q1", False)]) == NextQuestion("q3")


def test_full_path_finishes(survey):
    assert replay(survey, [("q1", True), ("q2", 10)]) == Finished()
    assert replay(survey, [("q1", False), ("q3", "A")]) == Finished()


def test_gap_and_conflict():
    q1 = Question("q1", QuestionType.YES_NO)
    q2 = Question("q2", QuestionType.RATING)
    gap_survey = Survey(
        questions={"q1": q1, "q2": q2},
        edges={"q1": [Edge(Const(False), "q2")]},
        root_id="q1",
    )
    assert replay(gap_survey, [("q1", True)]) == BranchError("q1", ErrorKind.GAP, 0)

    conflict_survey = Survey(
        questions={"q1": q1, "q2": q2},
        edges={"q1": [Edge(Const(True), "q2"), Edge(Const(True), "q2")]},
        root_id="q1",
    )
    assert replay(conflict_survey, [("q1", True)]) == BranchError(
        "q1", ErrorKind.CONFLICT, 2
    )


def test_stops_at_first_error():
    """错误发生后不能继续遍历：首个错误即返回。"""
    q1 = Question("q1", QuestionType.YES_NO)
    q2 = Question("q2", QuestionType.RATING)
    survey = Survey(
        questions={"q1": q1, "q2": q2},
        edges={"q1": [Edge(Const(False), "q2")]},
        root_id="q1",
    )
    result = replay(survey, [("q1", True), ("q2", 5)])
    assert result == BranchError("q1", ErrorKind.GAP, 0)


def test_rejects_mismatched_question_id(survey):
    with pytest.raises(ValueError, match="当前应作答题"):
        replay(survey, [("q2", 3)])


def test_rejects_illegal_answer_value(survey):
    with pytest.raises(ValueError, match="合法值"):
        replay(survey, [("q1", True), ("q2", 11)])


def test_rejects_answers_past_normal_end(survey):
    with pytest.raises(ValueError, match="正常结束后仍有剩余"):
        replay(survey, [("q1", True), ("q2", 5), ("q1", True)])
