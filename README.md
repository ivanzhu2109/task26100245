# survey_branch

会话问卷分支校验库：在发布前枚举所有合法会话，找出会让受访者卡住（漏接）或产生歧义（冲突）的分支，并给出可用 `replay` 实际回放的答案见证。

## 数据模型

- `Question(id, kind, options, edges)`：题目。`kind` 为 `YESNO`（答案 `True/False`）、`RATING`（答案 `1..10`）或 `CHOICE`（答案取自 `options`）。
- `Edge(condition, target)`：出边。`Survey(questions, root)` 为一棵有根树。
- 条件表达式：`MemberOf(qid, values)`（某题答案属于值集合，只能引用当前题或祖先题）、`And` / `Or` / `Not` / `Const`。

## 构造示例

```python
from survey_branch import *

q_root = Question("root", YESNO, edges=[
    Edge(MemberOf("root", frozenset({True})), "rate"),
    Edge(MemberOf("root", frozenset({False})), "bye"),
])
q_rate = Question("rate", RATING, edges=[
    Edge(MemberOf("rate", frozenset({1, 2, 3})), "low"),
    Edge(Not(MemberOf("rate", frozenset({1, 2, 3}))), "high"),
])
q_bye  = Question("bye",  CHOICE, options=("a", "b"))           # 叶题
q_low  = Question("low",  YESNO)
q_high = Question("high", YESNO)
survey = Survey({q.id: q for q in (q_root, q_rate, q_bye, q_low, q_high)}, root="root")
```

## analyze(survey)

枚举所有合法会话（此前每步恰好命中一条边），返回 `AnalysisResult`：

- `result.unreachable`：不可达题号集合。被漏接/冲突阻断的前缀不作为可达证据；冲突中条件成立的出边也不能让其子题变为可达。
- `result.report(qid)`：`QuestionReport`，含 `reachable`、`has_gap` / `gap_witness`、`has_conflict` / `conflict_witness`。同一题可同时存在两类错误。
- 见证是从根开始的 `[(题号, 答案), ...]` 序列，在报告题上首次发生对应错误。

## replay(survey, answers)

按答案前缀从根执行，返回：

- `NextQuestion(qid)`：答案耗尽，等待作答的下一题；
- `Ended()`：叶题已作答，正常结束（叶题不算漏接）；
- `BranchError(kind, question_id, answers_used)`：首次分支错误，`kind` 为 `"gap"` 或 `"conflict"`，发生后不再继续。

答案取值非法或在结束后仍有剩余答案时抛出 `ValueError`。

```python
result = analyze(survey)
for report in result.reports.values():
    for kind, witness in (("gap", report.gap_witness), ("conflict", report.conflict_witness)):
        if witness:
            err = replay(survey, [a for _, a in witness])
            assert err.kind == kind and err.question_id == report.question_id
```

## 运行测试

```bash
python3 -m pytest tests/ -q
```
