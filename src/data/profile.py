"""用户配置文件加载（YAML）

加载 profile.yaml，salary 字段从 "15K" 字符串解析为 int（月薪元）。
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.data.models import ExperienceInfo, Preferences, ScoringWeights, UserProfile


def _parse_salary_string(s: str) -> int:
    """将 "15K" 或 "15000" 解析为月薪元数"""
    if not s or not s.strip():
        return 0

    stripped = s.strip().upper()

    # "15K" → 15000
    m = re.match(r"(\d+(?:\.\d+)?)\s*K", stripped)
    if m:
        return int(float(m.group(1)) * 1000)

    # "15000" → 15000
    m = re.match(r"(\d+)", stripped)
    if m:
        return int(m.group(1))

    return 0


def load_profile(profile_path: str) -> UserProfile:
    """从 YAML 文件加载用户配置

    Args:
        profile_path: YAML 文件路径

    Returns:
        UserProfile 实例

    Raises:
        FileNotFoundError: 文件不存在
        yaml.YAMLError: YAML 格式错误
        ValueError: 必填字段缺失
    """
    path = Path(profile_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {profile_path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or not isinstance(raw, dict):
        raise ValueError("配置文件为空或格式错误")

    return _build_profile(raw)


def _build_profile(raw: dict) -> UserProfile:
    """从原始 dict 构建 UserProfile，处理 salary 字符串转换"""
    # Skills
    skills = raw.get("skills", [])
    if not skills:
        raise ValueError("配置文件缺少 skills 字段（必填）")

    # Experience
    exp_raw = raw.get("experience", {})
    experience = ExperienceInfo(
        years=exp_raw.get("years", 0) if isinstance(exp_raw, dict) else 0,
        level=exp_raw.get("level", "mid") if isinstance(exp_raw, dict) else "mid",
    )

    # Preferences — salary 从字符串转 int
    pref_raw = raw.get("preferences", {})
    salary_min_str = pref_raw.get("salary_min", "")
    salary_max_str = pref_raw.get("salary_max", "")

    preferences = Preferences(
        cities=pref_raw.get("cities", []),
        salary_min=_parse_salary_string(str(salary_min_str)),
        salary_max=_parse_salary_string(str(salary_max_str)),
        industries=pref_raw.get("industries", []),
    )

    # Scoring weights
    scoring_raw = raw.get("scoring", {})
    scoring = ScoringWeights(
        skill=scoring_raw.get("skill", 0.4),
        experience=scoring_raw.get("experience", 0.3),
        salary=scoring_raw.get("salary", 0.3),
    ) if scoring_raw else ScoringWeights()

    # Target roles
    target_roles = raw.get("target_roles", [])

    # Boss cookie (预留)
    boss_cookie = raw.get("boss_cookie", "")

    return UserProfile(
        skills=skills,
        experience=experience,
        preferences=preferences,
        target_roles=target_roles,
        scoring=scoring,
        boss_cookie=boss_cookie,
    )
