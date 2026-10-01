"""可直接运行的构造示例：python3 examples_demo.py"""
from survey_branch import (
    BranchError, Edge, ErrorKind, MemberOf, Question, QuestionType, Survey,
    analyze, replay,
)

questions = {
    "like": Question("like", QuestionType.YES_NO),
    "score": Question("score", QuestionType.RATING),
    "color": Question("color", QuestionType.SINGLE_CHOICE, ("红", "蓝")),
}
survey = Survey(
    questions=questions,
    edges={
        "like": [
            Edge(MemberOf("like", (True,)), "score"),
            Edge(MemberOf("like", (False,)), "color"),
        ],
        "score": [Edge(MemberOf("score", (6, 7, 8, 9, 10)), "color")],
    },
    root_id="like",
)

result = analyze(survey)
print("不可达题:", result.unreachable)
for qid, report in result.reports.items():
    if report.has_gap or report.has_conflict:
        print(f"题 {qid}: 漏接 {len(report.gaps)} 处, 冲突 {len(report.conflicts)} 处")

witness = result.reports["score"].gaps[0]
print("漏接见证:", witness.answers)
print("回放结果:", replay(survey, witness.answers))
