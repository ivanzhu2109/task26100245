# task26100245

会话问卷分支校验库 `survey_branch`：在发布前找出会让受访者卡住（漏接）
或产生歧义（冲突）的分支，并给出可用 `replay` 实际回放的答案见证。

## 数据模型

- `Question(question_id, qtype, options)`：题目。题型为
  `QuestionType.YES_NO`（答案 `True`/`False`）、`QuestionType.RATING`
  （答案整数 `1..10`）、`QuestionType.SINGLE_CHOICE`（答案为 `options` 之一）。
- `Edge(condition, target_id)`：出边。每题的出边放在 `Survey.edges` 中；
  没有出边的题是叶题，作答后正常结束。
- 条件表达式：`MemberOf(qid, values)`（某题答案属于给定值集合）、
  `And` / `Or` / `Not` / `Const(bool)`。条件只能引用当前题或祖先题。
- `Survey(questions, edges, root_id)`：一棵有根树。

## API

- `analyze(survey) -> AnalysisResult`
  - `unreachable`：不可达题号列表（只有此前每步恰好命中一条边才算可达；
    被漏接/冲突阻断的前缀不作为可达证据）。
  - `reports[qid]`：每个可达题的 `QuestionReport`，含 `gaps` / `conflicts`
    两个见证列表（`has_gap` / `has_conflict` 为是否存在对应错误）。
  - 见证 `Witness.answers` 是从根开始的 `(题号, 答案)` 序列，最后一项即
    首次发生错误的题。
- `replay(survey, answers)`：按 `(题号, 答案)` 前缀从根执行，返回
  `NextQuestion(qid)`（等待作答下一题）、`Finished()`（正常结束）或
  `BranchError(qid, kind, matched_edges)`（首次分支错误，
  `kind` 为 `ErrorKind.GAP` / `ErrorKind.CONFLICT`）。

## 构造与分析示例

```python
from survey_branch import (
    And, Edge, MemberOf, Not, Question, QuestionType, Survey,
    analyze, replay, BranchError, ErrorKind,
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
        # score 漏接：打 1..5 分时没有任何出边成立
        "score": [Edge(MemberOf("score", (6, 7, 8, 9, 10)), "color")],
    },
    root_id="like",
)

result = analyze(survey)
assert result.unreachable == []
report = result.reports["score"]
assert report.has_gap

witness = report.gaps[0]            # 例如 (("like", True), ("score", 1))
outcome = replay(survey, witness.answers)
assert outcome == BranchError("score", ErrorKind.GAP, 0)
```

## 运行测试

```bash
python3 -m pytest tests -q
```

纯标准库实现，无第三方依赖，不需要任何外部服务。
