"""数据模型定义 — 对齐 boss-cli JSON 导出结构"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Job(BaseModel):
    """单条岗位数据，字段 alias 对齐 boss-cli camelCase 导出"""

    model_config = ConfigDict(populate_by_name=True)

    job_name: str = Field(alias="jobName")
    salary_desc: str = Field(alias="salaryDesc", default="")
    city_name: str = Field(alias="cityName", default="")
    skills: list[str] = Field(default_factory=list)
    job_experience: str = Field(alias="jobExperience", default="")
    job_degree: str = Field(alias="jobDegree", default="")
    brand_name: str = Field(alias="brandName", default="")
    industry_name: str = Field(alias="industryName", default="")
    company_scale: str = Field(alias="scaleName", default="")
    company_stage: str = Field(alias="stageName", default="")
    job_description: str = Field(alias="postDescription", default="")


class SalaryRange(BaseModel):
    """解析后的薪资区间"""

    min_monthly: float  # 月薪下限（元）
    max_monthly: float  # 月薪上限（元）
    months: int = 12  # 年薪月数


class ExperienceInfo(BaseModel):
    years: int = 0
    level: str = "mid"  # junior / mid / mid-senior / senior


class Preferences(BaseModel):
    cities: list[str] = Field(default_factory=list)
    salary_min: int = 0  # 月薪下限（元），从 "15K" 解析为 15000
    salary_max: int = 0  # 月薪上限（元）
    industries: list[str] = Field(default_factory=list)


class ScoringWeights(BaseModel):
    skill: float = Field(0.3, ge=0)
    experience: float = Field(0.25, ge=0)
    salary: float = Field(0.2, ge=0)
    education: float = Field(0.1, ge=0)
    company: float = Field(0.15, ge=0)

    @model_validator(mode="after")
    def _validate_weights(self) -> ScoringWeights:
        total = self.skill + self.experience + self.salary + self.education + self.company
        if total <= 0:
            raise ValueError("ScoringWeights: 至少需要一个正权重")
        return self


class UserProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: ExperienceInfo = Field(default_factory=ExperienceInfo)
    education: str = ""  # 最高学历，如 "硕士"、"本科"
    preferences: Preferences = Field(default_factory=Preferences)
    target_roles: list[str] = Field(default_factory=list)
    scoring: ScoringWeights = Field(default_factory=ScoringWeights)

    # 预留配置
    boss_cookie: str = ""  # BOSS直聘 cookie，用户手动填入


class MatchResult(BaseModel):
    """单岗位评分结果"""

    total_score: float  # 0-100 综合分
    skill_overlap: float | None  # 0-1 或 None（岗位无技能标签时）
    experience_match: float | None  # 0-1 或 None（经验不限/无法解析时）
    salary_fit: float | None  # 0-1 或 None（面议/无法解析时）
    education_match: float | None  # 0-1 或 None（学历不限/无法解析时）
    company_quality: float | None  # 0-1 或 None（公司信息缺失时）
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
