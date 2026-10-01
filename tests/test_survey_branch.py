import pytest

from survey_branch import (
    And,
    BranchError,
    Const,
    Edge,
    Ended,
    MemberOf,
    NextQuestion,
    Not,
    Or,
    Question,
    Survey,
    analyze,
    replay,
    CHOICE,
    RATING,
    YESNO,
)


def member(qid, *values):
    return MemberOf(qid, frozenset(values))


def assert_witness(survey, witness, expected_kind, expected_qid):
    """见证必须能在报告题上首次触发对应错误。"""
    answers = [a for _, a in witness]
    # 去掉最后一步时不应发生任何错误
    prefix_result = replay(survey, answers[:-1])
    assert isinstance(prefix_result, NextQuestion)
    assert prefix_result.question_id == expected_qid
    # 完整见证在报告题上首次发生对应类型的错误
    result = replay(survey, answers)
    assert isinstance(result, BranchError)
    assert result.kind == expected_kind
    assert result.question_id == expected_qid
    assert list(result.answers_used) == answers


# ---------- 场景一：祖先分支排除了局部重叠 ----------

def build_ancestor_excludes_overlap():
    """root=True 才能到 q1。q1 的两条边局部可同时成立（q1=3 且 root=False），
    但合法前缀里 root 恒为 True，因此无冲突；t2 因条件永假而不可达。"""
    q_root = Question("root", YESNO, edges=[
        Edge(member("root", True), "q1"),
        Edge(member("root", False), "leaf_b"),
    ])
    q_q1 = Question("q1", RATING, edges=[
        Edge(member("q1", 1, 2, 3), "t1"),
        Edge(And((member("q1", 3, 4), member("root", False))), "t2"),
        Edge(member("q1", 4, 5, 6, 7, 8, 9, 10), "t3"),
    ])
    q_t1 = Question("t1", YESNO, edges=[])
    q_t2 = Question("t2", YESNO, edges=[])
    q_t3 = Question("t3", YESNO, edges=[])
    q_leaf_b = Question("leaf_b", YESNO, edges=[])
    questions = {q.id: q for q in (q_root, q_q1, q_t1, q_t2, q_t3, q_leaf_b)}
    return Survey(questions, root="root")


def test_no_false_conflict_when_ancestor_excludes_overlap():
    survey = build_ancestor_excludes_overlap()
    result = analyze(survey)
    q1 = result.report("q1")
    assert q1.reachable
    assert not q1.has_conflict
    assert not q1.has_gap


def test_unreachable_question_detected():
    survey = build_ancestor_excludes_overlap()
    result = analyze(survey)
    assert result.unreachable == {"t2"}
    assert not result.report("t2").reachable
    # 其余题均可达
    for qid in ("root", "q1", "t1", "t3", "leaf_b"):
        assert result.report(qid).reachable


# ---------- 场景二：同一题在不同前缀下分别漏接和冲突 ----------

def build_gap_and_conflict_same_question():
    """root 两个答案都通向 q1。
    root=True 且 q1=5 时两条边同时成立（冲突），t2 只在冲突中命中；
    root=False 时没有任何边成立（漏接）。"""
    q_root = Question("root", YESNO, edges=[
        Edge(member("root", True), "q1"),
        Edge(member("root", False), "q1"),
    ])
    q_q1 = Question("q1", RATING, edges=[
        Edge(member("root", True), "t1"),
        Edge(And((member("root", True), member("q1", 5))), "t2"),
    ])
    q_t1 = Question("t1", YESNO, edges=[])
    q_t2 = Question("t2", YESNO, edges=[Edge(Const(True), "grand")])
    q_grand = Question("grand", YESNO, edges=[])
    questions = {q.id: q for q in (q_root, q_q1, q_t1, q_t2, q_grand)}
    return Survey(questions, root="root")


def test_same_question_gap_and_conflict():
    survey = build_gap_and_conflict_same_question()
    result = analyze(survey)
    q1 = result.report("q1")
    assert q1.reachable
    assert q1.has_gap
    assert q1.has_conflict


def test_conflict_edge_target_and_child_not_reachable():
    survey = build_gap_and_conflict_same_question()
    result = analyze(survey)
    # t2 只在冲突中被命中，不能据此认为可达；其子题 grand 同样不可达
    assert result.unreachable == {"t2", "grand"}
    assert result.report("t1").reachable


def test_witnesses_replay_to_first_error():
    survey = build_gap_and_conflict_same_question()
    result = analyze(survey)
    q1 = result.report("q1")
    assert_witness(survey, q1.gap_witness, "gap", "q1")
    assert_witness(survey, q1.conflict_witness, "conflict", "q1")
    # 见证的具体内容符合预期
    assert q1.gap_witness == [("root", False), ("q1", 1)]
    assert q1.conflict_witness == [("root", True), ("q1", 5)]


def test_replay_reports_first_error_only():
    survey = build_gap_and_conflict_same_question()
    gap = replay(survey, [False, 7])
    assert gap == BranchError("gap", "q1", (False, 7))
    conflict = replay(survey, [True, 5])
    assert conflict == BranchError("conflict", "q1", (True, 5))
    # 冲突发生后不能继续遍历
    assert isinstance(replay(survey, [True, 5, True]), BranchError)


# ---------- 基础行为 ----------

def build_simple_survey():
    q_root = Question("root", YESNO, edges=[
        Edge(member("root", True), "rate"),
        Edge(member("root", False), "pick"),
    ])
    q_rate = Question("rate", RATING, edges=[
        Edge(Or((member("rate", 1, 2), member("rate", 3))), "low"),
        Edge(Not(Or((member("rate", 1, 2), member("rate", 3),))), "high"),
    ])
    q_pick = Question("pick", CHOICE, options=("a", "b"), edges=[])
    q_low = Question("low", YESNO, edges=[])
    q_high = Question("high", YESNO, edges=[])
    questions = {q.id: q for q in (q_root, q_rate, q_pick, q_low, q_high)}
    return Survey(questions, root="root")


def test_clean_survey_has_no_errors():
    result = analyze(build_simple_survey())
    assert result.unreachable == set()
    for report in result.reports.values():
        assert not report.has_gap
        assert not report.has_conflict


def test_replay_next_question_and_ended():
    survey = build_simple_survey()
    assert replay(survey, []) == NextQuestion("root")
    assert replay(survey, [True]) == NextQuestion("rate")
    assert replay(survey, [True, 2]) == NextQuestion("low")
    assert replay(survey, [True, 2, True]) == Ended()
    assert replay(survey, [False, "a"]) == Ended()  # 叶题作答后正常结束，不算漏接


def test_replay_rejects_invalid_answer():
    survey = build_simple_survey()
    with pytest.raises(ValueError):
        replay(survey, [True, 11])
    with pytest.raises(ValueError):
        replay(survey, [False, "zzz"])


def test_replay_rejects_answers_after_end():
    survey = build_simple_survey()
    with pytest.raises(ValueError):
        replay(survey, [False, "a", True])


def test_gap_witness_at_root():
    """root=False 时漏接；root=True 时正常前进，child 可达。"""
    q_root = Question("root", YESNO, edges=[
        Edge(member("root", True), "child"),
    ])
    q_child = Question("child", YESNO, edges=[])
    survey = Survey({"root": q_root, "child": q_child}, root="root")
    result = analyze(survey)
    root = result.report("root")
    assert root.has_gap
    assert not root.has_conflict
    assert result.unreachable == set()
    assert root.gap_witness == [("root", False)]
    assert_witness(survey, root.gap_witness, "gap", "root")
