"""市场分析 — 城市分布、薪资统计、技能频率"""

from __future__ import annotations

from collections import Counter

from src.core.normalizer import normalize_skills
from src.core.salary_parser import parse_salary
from src.data.models import Job


class MarketAnalysis:
    """对一组岗位数据做市场分析"""

    def __init__(self, jobs: list[Job]):
        self.jobs = jobs
        self._normalized_skills_cache: list[list[str]] | None = None

    def city_distribution(self) -> dict[str, float]:
        """城市分布（百分比）"""
        if not self.jobs:
            return {}
        counter = Counter(j.city_name for j in self.jobs if j.city_name)
        total = sum(counter.values())
        return {city: round(count / total * 100, 1) for city, count in counter.most_common()}

    def salary_stats(self) -> dict[str, float | None]:
        """薪资统计: min, max, median, avg（月薪元）"""
        salaries = []
        for j in self.jobs:
            sr = parse_salary(j.salary_desc)
            if sr:
                mid = (sr.min_monthly + sr.max_monthly) / 2
                salaries.append(mid)

        if not salaries:
            return {"min": None, "max": None, "median": None, "avg": None}

        salaries.sort()
        return {
            "min": round(salaries[0]),
            "max": round(salaries[-1]),
            "median": round(salaries[len(salaries) // 2]),
            "avg": round(sum(salaries) / len(salaries)),
        }

    def skill_frequency(self, top_n: int = 20) -> list[tuple[str, float]]:
        """技能出现频率（百分比），返回 top N"""
        if not self.jobs:
            return []

        all_skills: list[str] = []
        for j in self.jobs:
            all_skills.extend(normalize_skills(j.skills))

        counter = Counter(all_skills)
        total_jobs = len(self.jobs)

        return [
            (skill, round(count / total_jobs * 100, 1))
            for skill, count in counter.most_common(top_n)
        ]

    def industry_distribution(self) -> dict[str, float]:
        """行业分布（百分比）"""
        if not self.jobs:
            return {}
        counter = Counter(j.industry_name for j in self.jobs if j.industry_name)
        total = sum(counter.values())
        return {ind: round(count / total * 100, 1) for ind, count in counter.most_common(10)}

    def job_count(self) -> int:
        """岗位总数"""
        return len(self.jobs)

    def full_report(self) -> dict:
        """完整市场报告"""
        return {
            "total_jobs": self.job_count(),
            "cities": self.city_distribution(),
            "salary": self.salary_stats(),
            "top_skills": self.skill_frequency(),
            "industries": self.industry_distribution(),
        }
