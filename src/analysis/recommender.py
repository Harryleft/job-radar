"""推荐排序 — 多维度综合排序"""

from __future__ import annotations

from collections import Counter

from src.analysis.matcher import Matcher
from src.core.normalizer import normalize_skills
from src.data.models import Job, MatchResult, UserProfile


class Recommender:
    def __init__(self, matcher: Matcher | None = None):
        self.matcher = matcher or Matcher()

    def rank(
        self,
        jobs: list[Job],
        profile: UserProfile,
        top_n: int = 20,
        min_score: float = 0.0,
    ) -> list[tuple[Job, MatchResult]]:
        """评分并排序岗位

        Args:
            jobs: 岗位列表
            profile: 用户配置
            top_n: 返回前 N 条
            min_score: 最低分数过滤

        Returns:
            排序后的 (岗位, 评分) 列表
        """
        scored = self.matcher.match_all(jobs, profile)

        # 过滤低分
        filtered = [(j, r) for j, r in scored if r.total_score >= min_score]

        # 按总分降序
        filtered.sort(key=lambda x: x[1].total_score, reverse=True)

        return filtered[:top_n]

    def skill_gap_report(
        self,
        jobs: list[Job],
        profile: UserProfile,
        top_n: int = 10,
    ) -> dict:
        """生成技能差距报告

        Returns:
            {"have": [...], "need": [(skill, frequency)], "suggest": str}
        """
        profile_skills = set(normalize_skills(profile.skills))

        # 统计所有岗位中缺失技能的频率
        missing_counter: Counter[str] = Counter()
        total_jobs = 0

        ranked = self.rank(jobs, profile, top_n=top_n)
        for _job, result in ranked:
            total_jobs += 1
            for skill in result.missing_skills:
                missing_counter[skill] += 1

        # 按频率排序
        need = [
            (skill, round(freq / max(total_jobs, 1) * 100, 1))
            for skill, freq in missing_counter.most_common(10)
        ]

        # 建议优先学习的技能（频率最高）
        suggest = ""
        if need:
            top_skill, top_freq = need[0]
            suggest = f"{top_skill} — 出现频率 {top_freq}%，投入产出比最高"

        return {
            "have": sorted(profile_skills),
            "need": need,
            "suggest": suggest,
        }
