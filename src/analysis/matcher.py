"""岗位匹配 — 调用 scorer 对单岗位评分"""

from __future__ import annotations

import logging

from src.core.scorer import BaseScorer, RuleBasedScorer
from src.data.models import Job, MatchResult, UserProfile

logger = logging.getLogger(__name__)


class Matcher:
    def __init__(self, scorer: BaseScorer | None = None):
        self.scorer = scorer or RuleBasedScorer()

    def match(self, job: Job, profile: UserProfile) -> MatchResult:
        """对单个岗位评分"""
        return self.scorer.score(job, profile)

    def match_all(self, jobs: list[Job], profile: UserProfile) -> list[tuple[Job, MatchResult]]:
        """批量评分，返回 (岗位, 评分结果) 列表，按总分降序排列"""
        results: list[tuple[Job, MatchResult]] = []
        for job in jobs:
            try:
                result = self.match(job, profile)
            except Exception:
                logger.warning("评分失败: %s (%s)", job.job_name, job.brand_name, exc_info=True)
                continue
            results.append((job, result))
        results.sort(key=lambda item: item[1].total_score, reverse=True)
        return results
