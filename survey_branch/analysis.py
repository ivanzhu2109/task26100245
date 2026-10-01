"""analyze：枚举全部合法会话，找出不可达题与漏接/冲突及见证。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .model import Survey

Witness = List[Tuple[str, Any]]  # 从根开始的 (题号, 答案) 序列


@dataclass
class QuestionReport:
    question_id: str
    reachable: bool
    has_gap: bool = False
    gap_witness: Optional[Witness] = None
    has_conflict: bool = False
    conflict_witness: Optional[Witness] = None


@dataclass
class AnalysisResult:
    reports: Dict[str, QuestionReport] = field(default_factory=dict)

    @property
    def unreachable(self) -> Set[str]:
        return {qid for qid, r in self.reports.items() if not r.reachable}

    def report(self, qid: str) -> QuestionReport:
        return self.reports[qid]


def analyze(survey: Survey) -> AnalysisResult:
    """枚举所有合法会话（每步恰好命中一条边的答案前缀）。

    只有被合法前缀到达的题才算可达；在可达题上，任一合法前缀导致
    零条出边成立记为漏接、多条成立记为冲突，并记录对应见证。
    """
    reports = {
        qid: QuestionReport(question_id=qid, reachable=False)
        for qid in survey.questions
    }

    def visit(qid: str, env: Dict[str, Any], path: Witness) -> None:
        report = reports[qid]
        report.reachable = True
        question = survey.question(qid)
        for answer in question.domain():
            env[qid] = answer
            step = path + [(qid, answer)]
            hits = [e.target for e in question.edges if e.condition.evaluate(env)]
            if len(hits) == 0:
                if question.edges and not report.has_gap:
                    report.has_gap = True
                    report.gap_witness = step
            elif len(hits) > 1:
                if not report.has_conflict:
                    report.has_conflict = True
                    report.conflict_witness = step
            else:
                visit(hits[0], env, step)
        del env[qid]

    visit(survey.root, {}, [])
    return AnalysisResult(reports)
