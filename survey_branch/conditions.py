"""边条件表达式：成员判断、与、或、非、布尔常量。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


class Condition:
    """条件表达式基类。"""

    def evaluate(self, answers: Mapping[str, Any]) -> bool:
        """在已作答（题号 -> 答案）的映射上求值。"""
        raise NotImplementedError

    def referenced_questions(self) -> frozenset[str]:
        """表达式引用到的全部题号。"""
        raise NotImplementedError


@dataclass(frozen=True)
class MemberOf(Condition):
    """某题答案属于给定值集合。"""

    question_id: str
    values: Tuple[Any, ...]

    def evaluate(self, answers: Mapping[str, Any]) -> bool:
        return answers[self.question_id] in self.values

    def referenced_questions(self) -> frozenset[str]:
        return frozenset({self.question_id})


@dataclass(frozen=True)
class And(Condition):
    children: Tuple[Condition, ...]

    def evaluate(self, answers: Mapping[str, Any]) -> bool:
        return all(child.evaluate(answers) for child in self.children)

    def referenced_questions(self) -> frozenset[str]:
        return frozenset().union(*(c.referenced_questions() for c in self.children))


@dataclass(frozen=True)
class Or(Condition):
    children: Tuple[Condition, ...]

    def evaluate(self, answers: Mapping[str, Any]) -> bool:
        return any(child.evaluate(answers) for child in self.children)

    def referenced_questions(self) -> frozenset[str]:
        return frozenset().union(*(c.referenced_questions() for c in self.children))


@dataclass(frozen=True)
class Not(Condition):
    child: Condition

    def evaluate(self, answers: Mapping[str, Any]) -> bool:
        return not self.child.evaluate(answers)

    def referenced_questions(self) -> frozenset[str]:
        return self.child.referenced_questions()


@dataclass(frozen=True)
class Const(Condition):
    value: bool

    def evaluate(self, answers: Mapping[str, Any]) -> bool:
        return self.value

    def referenced_questions(self) -> frozenset[str]:
        return frozenset()
