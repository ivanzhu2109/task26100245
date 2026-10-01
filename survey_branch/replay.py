"""replay：按答案前缀执行会话。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence, Tuple, Union

from .model import Survey


@dataclass(frozen=True)
class NextQuestion:
    """答案已用完，等待回答的下一题。"""

    question_id: str


@dataclass(frozen=True)
class Ended:
    """叶题已回答，会话正常结束。"""


@dataclass(frozen=True)
class BranchError:
    """首次分支错误。kind 为 "gap"（漏接）或 "conflict"（冲突）。"""

    kind: str
    question_id: str
    answers_used: Tuple[Any, ...]  # 触发错误时已消费的答案（含本题）


ReplayResult = Union[NextQuestion, Ended, BranchError]


def replay(survey: Survey, answers: Sequence[Any]) -> ReplayResult:
    """从根题开始依次消费答案。

    每个答案对应当前题的一次作答：校验合法性后计算全部出边条件，
    恰好一条成立则前进，零条返回漏接，多条返回冲突；叶题作答后正常结束。
    答案耗尽时返回等待作答的下一题。
    """
    qid = survey.root
    env = {}
    used = []
    for answer in answers:
        question = survey.question(qid)
        if answer not in question.domain():
            raise ValueError(
                f"invalid answer {answer!r} for question {qid!r} ({question.kind})"
            )
        env[qid] = answer
        used.append(answer)
        hits = [edge.target for edge in question.edges if edge.condition.evaluate(env)]
        if len(hits) == 0:
            if not question.edges:
                if len(used) < len(answers):
                    raise ValueError("answers remain after the session has ended")
                return Ended()
            return BranchError("gap", qid, tuple(used))
        if len(hits) > 1:
            return BranchError("conflict", qid, tuple(used))
        qid = hits[0]
    return NextQuestion(qid)
