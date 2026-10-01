"""replay：按给定答案前缀执行会话。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, List, Tuple

from .model import Survey


class ErrorKind(Enum):
    GAP = "gap"  # 漏接：没有任何出边条件成立
    CONFLICT = "conflict"  # 冲突：多条出边条件同时成立


@dataclass(frozen=True)
class NextQuestion:
    """答案前缀已用完，等待作答的下一题。"""

    question_id: str


@dataclass(frozen=True)
class Finished:
    """叶题作答完毕，会话正常结束。"""


@dataclass(frozen=True)
class BranchError:
    """首次分支错误：作答 question_id 后命中 0 条（漏接）或多条（冲突）出边。"""

    question_id: str
    kind: ErrorKind
    matched_edges: int


ReplayResult = NextQuestion | Finished | BranchError


def replay(survey: Survey, answers: Iterable[Tuple[str, Any]]) -> ReplayResult:
    """按 (题号, 答案) 前缀从根开始执行，返回下一题、正常结束或首次分支错误。"""
    steps: List[Tuple[str, Any]] = list(answers)
    current = survey.root_id
    answered: dict[str, Any] = {}

    for index, (question_id, value) in enumerate(steps):
        if question_id != current:
            raise ValueError(
                f"第 {index + 1} 个答案对应题 {question_id!r}，"
                f"但当前应作答题为 {current!r}"
            )
        if value not in survey.question(current).domain():
            raise ValueError(f"答案 {value!r} 不是题 {current!r} 的合法值")
        answered[current] = value

        if survey.is_leaf(current):
            if index + 1 < len(steps):
                raise ValueError("答案序列在会话正常结束后仍有剩余")
            return Finished()

        matched = survey.matched_edges(current, answered)
        if len(matched) == 0:
            return BranchError(current, ErrorKind.GAP, 0)
        if len(matched) > 1:
            return BranchError(current, ErrorKind.CONFLICT, len(matched))
        current = matched[0].target_id

    return NextQuestion(current)
