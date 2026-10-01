"""问卷数据模型：题目、出边、问卷。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Tuple

from .conditions import Condition


class QuestionType(Enum):
    YES_NO = "yes_no"
    RATING = "rating"  # 1 至 10 分
    SINGLE_CHOICE = "single_choice"


@dataclass(frozen=True)
class Question:
    question_id: str
    qtype: QuestionType
    options: Tuple[Any, ...] = ()  # 仅单选题使用

    def domain(self) -> Tuple[Any, ...]:
        """该题所有合法答案。"""
        if self.qtype is QuestionType.YES_NO:
            return (True, False)
        if self.qtype is QuestionType.RATING:
            return tuple(range(1, 11))
        if self.qtype is QuestionType.SINGLE_CHOICE:
            if not self.options:
                raise ValueError(f"单选题 {self.question_id!r} 缺少选项")
            return self.options
        raise ValueError(f"未知题型: {self.qtype!r}")


@dataclass(frozen=True)
class Edge:
    condition: Condition
    target_id: str


@dataclass
class Survey:
    questions: Dict[str, Question]
    edges: Dict[str, List[Edge]]
    root_id: str

    def question(self, question_id: str) -> Question:
        return self.questions[question_id]

    def outgoing(self, question_id: str) -> List[Edge]:
        return self.edges.get(question_id, [])

    def is_leaf(self, question_id: str) -> bool:
        return not self.outgoing(question_id)

    def matched_edges(
        self, question_id: str, answers: Mapping[str, Any]
    ) -> List[Edge]:
        """给定已作答映射，返回条件成立的出边。"""
        return [e for e in self.outgoing(question_id) if e.condition.evaluate(answers)]
