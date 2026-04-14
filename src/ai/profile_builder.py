"""虚拟 Profile 生成 — CareerPath → UserProfile 转换"""

from __future__ import annotations

import logging

from src.ai.schemas import CareerPath, ResumeExtract
from src.core.normalizer import normalize_skills
from src.core.salary_parser import parse_salary
from src.data.models import ExperienceInfo, Preferences, ScoringWeights, UserProfile

logger = logging.getLogger(__name__)


def _infer_level(years: int) -> str:
    """根据工作年限推断职级"""
    years = max(0, years)
    if years >= 8:
        return "senior"
    if years >= 5:
        return "mid-senior"
    if years >= 3:
        return "mid"
    return "junior"


def career_path_to_profile(
    path: CareerPath, extracted: ResumeExtract
) -> UserProfile:
    """将职业路径 + 提取信息转换为 UserProfile

    技能经过 normalize_skills() 归一化、去重、空值过滤。
    薪资优先从 salary_parser 解析, 解析失败则为 0(不限制)。
    """
    # 归一化 + 去重 + 过滤空值
    normalized_skills = list(dict.fromkeys(
        s for s in normalize_skills(extracted.skills) if s and s.strip()
    ))

    salary_min, salary_max = 0, 0
    if path.salary_range:
        parsed = parse_salary(path.salary_range)
        if parsed:
            salary_min, salary_max = int(parsed.min_monthly), int(parsed.max_monthly)
        else:
            logger.warning("职业路径薪资无法解析: %s", path.salary_range)

    return UserProfile(
        skills=normalized_skills,
        experience=ExperienceInfo(
            years=max(0, extracted.experience_years),
            level=_infer_level(extracted.experience_years),
        ),
        education=extracted.education,
        preferences=Preferences(salary_min=salary_min, salary_max=salary_max),
        target_roles=[path.title],
        scoring=ScoringWeights(),
    )
