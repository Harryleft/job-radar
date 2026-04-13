"""共享测试 fixtures"""

import pytest

from src.data.models import ExperienceInfo, Job, Preferences, ScoringWeights, UserProfile


@pytest.fixture
def sample_jobs() -> list[Job]:
    """18 条样本岗位数据（与 data/samples/sample_jobs.json 结构一致）"""
    return [
        Job(
            jobName="数据分析师",
            salaryDesc="20-30K·14薪",
            cityName="上海",
            skills=["Python", "SQL", "Tableau", "Excel"],
            jobExperience="3-5年",
            jobDegree="本科",
            brandName="字节跳动",
            industryName="互联网",
            company_scale="10000人以上",
            company_stage="已上市",
            job_description="负责业务数据分析",
        ),
        Job(
            jobName="Python开发工程师",
            salaryDesc="18-28K·13薪",
            cityName="上海",
            skills=["Python", "Django", "MySQL", "Redis", "Docker"],
            jobExperience="3-5年",
            jobDegree="本科",
            brandName="拼多多",
            industryName="电商",
            company_scale="10000人以上",
            company_stage="已上市",
            job_description="后端服务开发",
        ),
        Job(
            jobName="全栈工程师",
            salaryDesc="面议",
            cityName="深圳",
            skills=["React", "Python", "MySQL", "Docker", "TypeScript"],
            jobExperience="3-5年",
            jobDegree="本科",
            brandName="OPPO",
            industryName="硬件",
            company_scale="10000人以上",
            company_stage="已上市",
            job_description="内部工具全栈开发",
        ),
        Job(
            jobName="实习生-数据分析",
            salaryDesc="150-200元/天",
            cityName="上海",
            skills=["Python", "SQL", "Excel"],
            jobExperience="经验不限",
            jobDegree="本科",
            brandName="B站",
            industryName="互联网",
            company_scale="1000-9999人",
            company_stage="已上市",
            job_description="数据分析实习",
        ),
        Job(
            jobName="算法工程师",
            salaryDesc="40-60K·16薪",
            cityName="北京",
            skills=["Python", "机器学习", "TensorFlow", "SQL"],
            jobExperience="3-5年",
            jobDegree="硕士",
            brandName="百度",
            industryName="互联网",
            company_scale="10000人以上",
            company_stage="已上市",
            job_description="推荐算法优化",
        ),
    ]


@pytest.fixture
def sample_profile() -> UserProfile:
    """示例用户配置"""
    return UserProfile(
        skills=["Python", "SQL", "数据分析", "产品设计"],
        experience=ExperienceInfo(years=5, level="mid-senior"),
        preferences=Preferences(
            cities=["上海", "北京", "深圳"],
            salary_min=15000,
            salary_max=35000,
            industries=["互联网", "金融科技"],
        ),
        target_roles=["数据分析师", "产品经理", "数据产品经理"],
        scoring=ScoringWeights(skill=0.4, experience=0.3, salary=0.3),
    )
