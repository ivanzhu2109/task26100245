"""analyze 的场景测试。"""
import pytest

from survey_branch import (
    And,
    Const,
    Edge,
    ErrorKind,
    MemberOf,
    Not,
    Or,
    Question,
    QuestionType,
    Survey,
    analyze,
    replay,
    BranchError,
    Finished,
)


def make_question(qid, qtype, options=()):
    return Question(qid, qtype, options)


def test_healthy_survey_no_errors():
    """完全健康的问卷：无不可达题、无漏接、无冲突。"""
    questions = {
        "like": make_question("like", QuestionType.YES_NO),
        "score": make_question("score", QuestionType.RATING),
        "color": make_question("color", QuestionType.SINGLE_CHOICE, ("红", "蓝")),
    }
    survey = Survey(
        questions=questions,
        edges={
            "like": [
                Edge(MemberOf("like", (True,)), "score"),
                Edge(MemberOf("like", (False,)), "color"),
            ],
        },
        root_id="like",
    )
    result = analyze(survey)
    assert result.unreachable == []
    assert set(result.reports) == {"like", "score", "color"}
    for report in result.reports.values():
        assert not report.has_gap
        assert not report.has_conflict


def test_local_overlap_masked_by_ancestor_branch():
    """两条边条件局部重叠，但祖先分支已排除全部重叠答案。

    c 的边 e2 单独看可满足（r=False 合法），但到达 c 必须经过 r=True，
    因此不应误报冲突；e2 实际不可走，其目标 e 不可达。
    """
    questions = {
        "r": make_question("r", QuestionType.YES_NO),
        "b": make_question("b", QuestionType.RATING),
        "c": make_question("c", QuestionType.RATING),
        "d": make_question("d", QuestionType.YES_NO),
        "e": make_question("e", QuestionType.YES_NO),
    }
    survey = Survey(
        questions=questions,
        edges={
            "r": [
                Edge(MemberOf("r", (True,)), "c"),
                Edge(MemberOf("r", (False,)), "b"),
            ],
            "c": [
                # e1 与 e2 在 (r=False, c 任意) 上局部重叠
                Edge(MemberOf("c", tuple(range(1, 11))), "d"),
                Edge(MemberOf("r", (False,)), "e"),
            ],
        },
        root_id="r",
    )
    result = analyze(survey)

    assert result.unreachable == ["e"]
    report_c = result.reports["c"]
    assert not report_c.has_conflict, "祖先分支已排除重叠答案，不应误报冲突"
    assert not report_c.has_gap
    assert set(result.reports) == {"r", "b", "c", "d"}


def test_same_question_gap_and_conflict_on_different_prefixes():
    """同一题 m 在不同合法前缀下分别漏接与冲突。

    r=False 的前缀在 m 漏接；r=True 且 m∈1..5 的前缀在 m 冲突。
    冲突处虽有条件成立的出边，其子题 x、y 仍不可达。
    """
    questions = {
        "r": make_question("r", QuestionType.YES_NO),
        "m": make_question("m", QuestionType.RATING),
        "x": make_question("x", QuestionType.YES_NO),
        "y": make_question("y", QuestionType.YES_NO),
    }
    survey = Survey(
        questions=questions,
        edges={
            "r": [Edge(Const(True), "m")],
            "m": [
                Edge(
                    And((MemberOf("r", (True,)), MemberOf("m", (1, 2, 3, 4, 5)))),
                    "x",
                ),
                Edge(
                    And((MemberOf("r", (True,)), MemberOf("m", (1, 2, 3, 4, 5)))),
                    "y",
                ),
            ],
        },
        root_id="r",
    )
    result = analyze(survey)

    # 冲突处被阻断，x、y 不可达
    assert result.unreachable == ["x", "y"]

    report_m = result.reports["m"]
    assert report_m.has_gap
    assert report_m.has_conflict

    # 漏接与冲突见证都交给 replay 验证：首次错误的位置与类型必须一致
    for witness in report_m.gaps:
        assert witness.question_id == "m"
        outcome = replay(survey, witness.answers)
        assert outcome == BranchError("m", ErrorKind.GAP, 0)
    for witness in report_m.conflicts:
        assert witness.question_id == "m"
        outcome = replay(survey, witness.answers)
        assert outcome == BranchError("m", ErrorKind.CONFLICT, 2)

    # 两类错误确实出现在不同的合法前缀上
    gap_prefixes = {w.answers for w in report_m.gaps}
    conflict_prefixes = {w.answers for w in report_m.conflicts}
    assert gap_prefixes.isdisjoint(conflict_prefixes)
    assert any(dict(w.answers)["r"] is False for w in report_m.gaps)
    assert all(dict(w.answers)["r"] is True for w in report_m.conflicts)


def test_leaf_answer_is_normal_end_not_gap():
    """叶题作答后正常结束，不算漏接。"""
    questions = {"only": make_question("only", QuestionType.SINGLE_CHOICE, ("甲", "乙"))}
    survey = Survey(questions=questions, edges={}, root_id="only")
    result = analyze(survey)
    assert result.unreachable == []
    assert not result.reports["only"].has_gap
    assert not result.reports["only"].has_conflict


def test_gap_blocks_downstream_reachability():
    """漏接阻断的前缀不能作为后续题可达的证据。"""
    questions = {
        "a": make_question("a", QuestionType.YES_NO),
        "b": make_question("b", QuestionType.RATING),
    }
    survey = Survey(
        questions=questions,
        # a 的唯一出边恒假：b 结构上是子题，但任何会话都到不了
        edges={"a": [Edge(Const(False), "b")]},
        root_id="a",
    )
    result = analyze(survey)
    assert result.unreachable == ["b"]
    assert result.reports["a"].has_gap
    assert "b" not in result.reports


def test_complex_boolean_conditions():
    """与、或、非、常量组合的条件求值正确。"""
    questions = {
        "q1": make_question("q1", QuestionType.YES_NO),
        "q2": make_question("q2", QuestionType.RATING),
        "q3": make_question("q3", QuestionType.SINGLE_CHOICE, ("A", "B")),
    }
    survey = Survey(
        questions=questions,
        edges={
            "q1": [
                Edge(
                    Or((
                        MemberOf("q1", (True,)),
                        And((Not(MemberOf("q1", (True,))), Const(False))),
                    )),
                    "q2",
                ),
            ],
            "q2": [
                Edge(Not(MemberOf("q2", tuple(range(1, 11)))), "q3"),
            ],
        },
        root_id="q1",
    )
    result = analyze(survey)
    # q1=True 时进入 q2；q1=False 时漏接。q2 的出边恒假，全部答案漏接，q3 不可达。
    assert result.unreachable == ["q3"]
    assert result.reports["q1"].has_gap
    assert not result.reports["q1"].has_conflict
    assert len(result.reports["q2"].gaps) == 10
