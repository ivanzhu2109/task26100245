"""analyze：发布前静态校验，找出不可达题、漏接与冲突，并给出答案见证。

核心思路：条件只能引用当前题或祖先题，因此一个会话在某个题目处的
行为完全由“该题子树中实际被引用到的祖先答案”决定。按此投影枚举
每个可达题的所有可能答案组合，恰好覆盖全部合法会话，且每个被传播
的状态都对应至少一条此前每步恰好命中一条边的合法前缀。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .model import Survey
from .replay import ErrorKind

# 投影后的答案赋值：按题号排序的 (题号, 答案) 元组，可哈希。
_Assignment = Tuple[Tuple[str, Any], ...]
# 从根开始的作答路径：(题号, 答案) 序列。
_Path = Tuple[Tuple[str, Any], ...]


@dataclass(frozen=True)
class Witness:
    """从根开始的（题目, 答案）序列，最后一项是首次发生错误的题。"""

    kind: ErrorKind
    answers: Tuple[Tuple[str, Any], ...]

    @property
    def question_id(self) -> str:
        """首次发生错误的题。"""
        return self.answers[-1][0]


@dataclass
class QuestionReport:
    question_id: str
    gaps: List[Witness] = field(default_factory=list)
    conflicts: List[Witness] = field(default_factory=list)

    @property
    def has_gap(self) -> bool:
        return bool(self.gaps)

    @property
    def has_conflict(self) -> bool:
        return bool(self.conflicts)


@dataclass
class AnalysisResult:
    unreachable: List[str]
    reports: Dict[str, QuestionReport]  # 仅含可达题


def _subtree_needed_refs(survey: Survey) -> Dict[str, frozenset[str]]:
    """每题子树内全部出边条件引用到的题号集合（后序遍历一次算出）。"""
    needed: Dict[str, frozenset[str]] = {}

    def visit(question_id: str) -> frozenset[str]:
        refs: set[str] = set()
        for edge in survey.outgoing(question_id):
            refs |= edge.condition.referenced_questions()
            refs |= visit(edge.target_id)
        needed[question_id] = frozenset(refs)
        return needed[question_id]

    visit(survey.root_id)
    return needed


def _project(answers: Dict[str, Any], keep: frozenset[str]) -> _Assignment:
    return tuple(sorted((k, v) for k, v in answers.items() if k in keep))


def analyze(survey: Survey) -> AnalysisResult:
    needed = _subtree_needed_refs(survey)

    # 每题：投影赋值 -> 首次到达该赋值时的作答路径（不含本题答案）。
    states: Dict[str, Dict[_Assignment, _Path]] = {survey.root_id: {(): ()}}
    reports: Dict[str, QuestionReport] = {}
    queue: List[Tuple[str, _Assignment, _Path]] = [(survey.root_id, (), ())]

    while queue:
        question_id, assignment, path = queue.pop()
        question = survey.question(question_id)
        base = dict(assignment)
        report = reports.setdefault(question_id, QuestionReport(question_id))

        for value in question.domain():
            full = {**base, question_id: value}
            step_path = path + ((question_id, value),)

            if survey.is_leaf(question_id):
                continue  # 叶题作答后正常结束，不算漏接

            matched = survey.matched_edges(question_id, full)
            if len(matched) == 0:
                report.gaps.append(Witness(ErrorKind.GAP, step_path))
            elif len(matched) > 1:
                report.conflicts.append(Witness(ErrorKind.CONFLICT, step_path))
            else:
                child = matched[0].target_id
                projected = _project(full, needed[child])
                child_states = states.setdefault(child, {})
                if projected not in child_states:
                    child_states[projected] = step_path
                    queue.append((child, projected, step_path))

    unreachable = sorted(set(survey.questions) - set(states))
    return AnalysisResult(unreachable=unreachable, reports=reports)
