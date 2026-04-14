"""可插拔评分器接口 + 规则引擎实现

5 维评分: skill, experience, salary, education, company quality
权重可配置（默认 30/25/20/10/15）。缺失信号时按比例重分配权重。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.education_parser import parse_education
from src.core.experience_parser import parse_experience
from src.core.normalizer import normalize_skills
from src.core.salary_parser import parse_salary
from src.data.models import Job, MatchResult, ScoringWeights, UserProfile


class BaseScorer(ABC):
    @abstractmethod
    def score(self, job: Job, profile: UserProfile) -> MatchResult: ...


class RuleBasedScorer(BaseScorer):
    """MVP 规则评分器

    5 个信号: skill_overlap, experience_match, salary_fit, education_match, company_quality
    缺失信号时按比例重分配权重到其他信号
    """

    def __init__(self, weights: ScoringWeights | None = None):
        self.weights = weights or ScoringWeights()

    def score(self, job: Job, profile: UserProfile) -> MatchResult:
        # --- Skill overlap ---
        normalized_job_skills = normalize_skills(job.skills)
        normalized_profile_skills = normalize_skills(profile.skills)

        job_skill_set = set(normalized_job_skills)
        profile_skill_set = set(normalized_profile_skills)

        matched = job_skill_set & profile_skill_set
        missing = job_skill_set - profile_skill_set

        # 岗位无技能标签 → 信号缺失而非 0 分
        skill_overlap: float | None = (
            len(matched) / len(job_skill_set) if job_skill_set else None
        )

        # --- Experience match ---
        exp_range = parse_experience(job.job_experience)
        if exp_range is not None:
            exp_min, exp_max = exp_range
            years = profile.experience.years
            if exp_min <= years <= exp_max:
                experience_match = 1.0
            elif years < exp_min:
                experience_match = max(0.0, 1.0 - (exp_min - years) / max(exp_min, 1))
            else:
                experience_match = max(0.0, 1.0 - (years - exp_max) / max(exp_max, 1))
        else:
            experience_match = None

        # --- Salary fit (区间重叠算法) ---
        job_salary = parse_salary(job.salary_desc)
        expected_min = profile.preferences.salary_min
        expected_max = profile.preferences.salary_max
        has_salary_pref = expected_min > 0 or expected_max > 0

        if job_salary is not None and has_salary_pref:
            lower = expected_min or 0
            upper = expected_max if expected_max > 0 else float("inf")
            job_lo = job_salary.min_monthly
            job_hi = job_salary.max_monthly
            overlap = max(0, min(upper, job_hi) - max(lower, job_lo))
            span = max(job_hi - job_lo, 1)
            # 定点薪资(如 20-20K)且落在期望区间内 → 完美匹配
            salary_fit = (
                1.0 if job_lo == job_hi and lower <= job_lo <= upper else overlap / span
            )
        else:
            salary_fit = None

        # --- Education match ---
        education_match = self._score_education(job, profile)

        # --- Company quality ---
        company_quality = self._score_company(job)

        # --- Weighted total with redistribution ---
        total = self._compute_total(
            skill_overlap, experience_match, salary_fit, education_match, company_quality
        )

        return MatchResult(
            total_score=round(total * 100, 1),
            skill_overlap=round(skill_overlap, 3) if skill_overlap is not None else None,
            experience_match=round(experience_match, 3) if experience_match is not None else None,
            salary_fit=round(salary_fit, 3) if salary_fit is not None else None,
            education_match=round(education_match, 3) if education_match is not None else None,
            company_quality=round(company_quality, 3) if company_quality is not None else None,
            matched_skills=sorted(matched),
            missing_skills=sorted(missing),
        )

    def _score_education(self, job: Job, profile: UserProfile) -> float | None:
        """学历匹配: 用户学历 vs 岗位要求"""
        job_edu = parse_education(job.job_degree)
        user_edu = parse_education(profile.education)

        if job_edu is None or user_edu is None:
            return None

        if user_edu >= job_edu:
            return 1.0
        # 学历不足但不直接归零（适当放宽）
        return 0.3

    def _score_company(self, job: Job) -> float | None:
        """公司质量: 基于规模 + 融资阶段"""
        scores: list[float] = []

        scale_score = self._parse_company_scale(job.company_scale)
        if scale_score is not None:
            scores.append(scale_score)

        stage_score = self._parse_company_stage(job.company_stage)
        if stage_score is not None:
            scores.append(stage_score)

        if not scores:
            return None

        return sum(scores) / len(scores)

    @staticmethod
    def _parse_company_scale(scale: str) -> float | None:
        """公司规模评分"""
        mapping: dict[str, float] = {
            "10000人以上": 1.0,
            "1000-9999人": 0.8,
            "500-999人": 0.6,
            "100-499人": 0.5,
            "20-99人": 0.35,
            "0-19人": 0.3,
            "0-99人": 0.3,
        }
        if not scale:
            return None
        if scale in mapping:
            return mapping[scale]
        # 模糊匹配: 按键长度降序，避免 "20-99人" 先命中 "0-99人"
        for key in sorted(mapping, key=len, reverse=True):
            if key in scale:
                return mapping[key]
        return None

    @staticmethod
    def _parse_company_stage(stage: str) -> float | None:
        """公司阶段评分"""
        mapping: dict[str, float] = {
            "已上市": 1.0,
            "D轮及以上": 0.9,
            "C轮": 0.8,
            "B轮": 0.7,
            "A轮": 0.6,
            "天使轮": 0.5,
            "未融资": 0.3,
            "不需要融资": 0.4,
        }
        if not stage:
            return None
        if stage in mapping:
            return mapping[stage]
        for key, val in mapping.items():
            if key in stage:
                return val
        return None

    def _compute_total(
        self,
        skill_overlap: float | None,
        experience_match: float | None,
        salary_fit: float | None,
        education_match: float | None = None,
        company_quality: float | None = None,
    ) -> float:
        """计算加权总分，缺失信号按比例重分配权重"""
        signals: list[tuple[float, float]] = []  # (weight, value)

        if skill_overlap is not None:
            signals.append((self.weights.skill, skill_overlap))
        if experience_match is not None:
            signals.append((self.weights.experience, experience_match))
        if salary_fit is not None:
            signals.append((self.weights.salary, salary_fit))
        if education_match is not None:
            signals.append((self.weights.education, education_match))
        if company_quality is not None:
            signals.append((self.weights.company, company_quality))

        total_weight = sum(w for w, _ in signals)
        if total_weight == 0:
            return 0.0

        # 归一化权重，使总和为 1.0
        return sum(w / total_weight * v for w, v in signals)
