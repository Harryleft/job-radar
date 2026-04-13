"""岗位匹配 — 调用 scorer 对单岗位评分"""

from __future__ import annotations

from src.core.scorer import BaseScorer, RuleBasedScorer
from src.data.models import Job, MatchResult, UserProfile


class Matcher:
    def __init__(self, scorer: BaseScorer | None = None):
        self.scorer = scorer or RuleBasedScorer()

    def match(self, job: Job, profile: UserProfile) -> MatchResult:
        """对单个岗位评分"""
        return self.scorer.score(job, profile)

    def match_all(self, jobs: list[Job], profile: UserProfile) -> list[tuple[Job, MatchResult]]:
        """批量评分，返回 (岗位, 评分结果) 列表"""
        results = []
        for job in jobs:
            result = self.match(job, profile)
            results.append((job, result))
        return results
