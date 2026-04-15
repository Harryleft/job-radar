"""AI 层输出 schema — Pydantic 模型定义"""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class ResumeExtract(BaseModel):
    """Chain 1 输出: 简历 / 背景文本结构化提取"""

    skills: list[str]
    experience_years: int
    education: str = ""
    work_history: list[str] = []
    highlights: list[str] = []
    # 背景叙事维度（纯文本输入时填充，PDF 输入时默认为空）
    location_preferences: list[str] = []
    life_context: str = ""
    career_goals: str = ""


class CareerPath(BaseModel):
    """单条职业路径"""

    title: str
    match_reason: str
    required_skills: list[str] = []
    salary_range: str | None = None


class CareerRecommendation(BaseModel):
    """Chain 2 输出: N 条职业路径"""

    paths: list[CareerPath]

    @model_validator(mode="after")
    def validate_paths_count(self) -> CareerRecommendation:
        if len(self.paths) < 1 or len(self.paths) > 5:
            raise ValueError(f"paths count must be 1-5, got {len(self.paths)}")
        return self
