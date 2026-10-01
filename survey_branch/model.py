"""数据模型：题目、边条件表达式、问卷。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ---------- 条件表达式 ----------

class Condition:
    """边条件表达式基类。env 为 {题号: 答案}。"""

    def evaluate(self, env: Dict[str, Any]) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class Const(Condition):
    value: bool

    def evaluate(self, env: Dict[str, Any]) -> bool:
        return self.value


@dataclass(frozen=True)
class MemberOf(Condition):
    """某题答案属于给定值集合。只能引用当前题或祖先题。"""

    question_id: str
    values: FrozenSet[Any]

    def evaluate(self, env: Dict[str, Any]) -> bool:
        return env.get(self.question_id) in self.values


@dataclass(frozen=True)
class And(Condition):
    parts: Tuple[Condition, ...]

    def evaluate(self, env: Dict[str, Any]) -> bool:
        return all(p.evaluate(env) for p in self.parts)


@dataclass(frozen=True)
class Or(Condition):
    parts: Tuple[Condition, ...]

    def evaluate(self, env: Dict[str, Any]) -> bool:
        return any(p.evaluate(env) for p in self.parts)


@dataclass(frozen=True)
class Not(Condition):
    part: Condition

    def evaluate(self, env: Dict[str, Any]) -> bool:
        return not self.part.evaluate(env)


# ---------- 题目 ----------

YESNO = "yesno"
RATING = "rating"
CHOICE = "choice"


@dataclass(frozen=True)
class Edge:
    condition: Condition
    target: str


@dataclass
class Question:
    id: str
    kind: str  # YESNO / RATING / CHOICE
    options: Tuple[Any, ...] = ()  # 仅 CHOICE 使用
    edges: List[Edge] = field(default_factory=list)

    def domain(self) -> List[Any]:
        """该题所有合法答案。"""
        if self.kind == YESNO:
            return [True, False]
        if self.kind == RATING:
            return list(range(1, 11))
        if self.kind == CHOICE:
            return list(self.options)
        raise ValueError(f"unknown question kind: {self.kind}")


@dataclass
class Survey:
    """有根树问卷。questions 的键为题号，root 为根题号。"""

    questions: Dict[str, Question]
    root: str

    def question(self, qid: str) -> Question:
        return self.questions[qid]
