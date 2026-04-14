"""评分器测试"""

import pytest

from src.core.normalizer import reset_lookup
from src.core.scorer import RuleBasedScorer
from src.data.models import (
    ExperienceInfo,
    Job,
    Preferences,
    ScoringWeights,
    UserProfile,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_lookup()
    yield
    reset_lookup()


class TestRuleBasedScorer:
    def _make_profile(
        self,
        skills=None,
        years=5,
        salary_min=15000,
        salary_max=35000,
        weights=None,
        education="本科",
    ):
        return UserProfile(
            skills=skills or ["Python", "SQL", "数据分析"],
            experience=ExperienceInfo(years=years),
            education=education,
            preferences=Preferences(salary_min=salary_min, salary_max=salary_max),
            scoring=weights or ScoringWeights(),
        )

    def _make_job(
        self,
        skills=None,
        salary_desc="20-30K",
        experience="3-5年",
        degree="本科",
        scale="",
        stage="",
    ):
        return Job(
            jobName="测试岗位",
            salaryDesc=salary_desc,
            cityName="上海",
            skills=skills or ["Python", "SQL"],
            jobExperience=experience,
            jobDegree=degree,
            brandName="测试公司",
            scaleName=scale,
            stageName=stage,
        )

    """3 信号完整评分"""

    def test_full_score_perfect_match(self):
        profile = self._make_profile(
            skills=["Python", "SQL"], years=4, salary_min=20000, salary_max=30000
        )
        job = self._make_job(
            skills=["Python", "SQL"], salary_desc="20-30K", experience="3-5年"
        )
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.skill_overlap == 1.0
        assert result.experience_match == 1.0
        assert result.salary_fit == 1.0
        assert result.total_score == 100.0
        assert result.matched_skills == ["python", "sql"]
        assert result.missing_skills == []

    def test_partial_match(self):
        profile = self._make_profile(skills=["Python", "SQL"], years=4)
        job = self._make_job(
            skills=["Python", "SQL", "R", "Java"],
            salary_desc="20-30K",
            experience="3-5年",
        )
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.skill_overlap == 0.5  # 2/4
        assert result.experience_match == 1.0
        assert len(result.matched_skills) == 2
        assert "R" in result.missing_skills

    """缺失信号权重重分配"""

    def test_salary_none_redistributes(self):
        profile = self._make_profile(
            skills=["Python", "SQL"], years=4, salary_min=20000, salary_max=30000
        )
        job = self._make_job(
            skills=["Python", "SQL"], salary_desc="面议", experience="3-5年"
        )
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.salary_fit is None
        assert result.skill_overlap == 1.0
        assert result.experience_match == 1.0
        # 权重重分配: skill(0.4) + exp(0.3) = 0.7, 归一化后 skill=4/7, exp=3/7
        # total = 4/7 * 1.0 + 3/7 * 1.0 = 1.0 → 100
        assert result.total_score == 100.0

    def test_experience_none_redistributes(self):
        profile = self._make_profile(skills=["Python", "SQL"], years=4)
        job = self._make_job(skills=["Python", "SQL"], salary_desc="20-30K", experience="未知格式")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.experience_match is None
        # 权重重分配: skill(0.4) + salary(0.3) = 0.7, 归一化后 1.0 → 100
        assert result.total_score == 100.0

    def test_both_none_only_skill(self):
        profile = self._make_profile(skills=["Python", "SQL"], years=4, salary_min=0, salary_max=0)
        job = self._make_job(skills=["Python", "SQL"], salary_desc="面议", experience="未知格式")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.salary_fit is None
        assert result.experience_match is None
        assert result.skill_overlap == 1.0
        assert result.total_score == 100.0

    """自定义权重"""

    def test_custom_weights(self):
        weights = ScoringWeights(
            skill=0.5, experience=0.3, salary=0.2, education=0.0, company=0.0
        )
        profile = self._make_profile(
            skills=["Python"], years=4, salary_min=20000, salary_max=30000, weights=weights
        )
        job = self._make_job(skills=["Python"], salary_desc="20-30K", experience="3-5年")
        scorer = RuleBasedScorer(weights)
        result = scorer.score(job, profile)

        assert result.total_score == 100.0

    """经验匹配边界"""

    def test_experience_below_range(self):
        profile = self._make_profile(skills=["Python"], years=1)
        job = self._make_job(skills=["Python"], salary_desc="20-30K", experience="3-5年")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.experience_match is not None
        assert result.experience_match < 1.0

    def test_experience_above_range(self):
        profile = self._make_profile(skills=["Python"], years=8)
        job = self._make_job(skills=["Python"], salary_desc="20-30K", experience="3-5年")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.experience_match is not None
        assert result.experience_match < 1.0

    def test_experience_no_limit(self):
        profile = self._make_profile(skills=["Python"], years=10)
        job = self._make_job(skills=["Python"], salary_desc="20-30K", experience="经验不限")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.experience_match == 1.0

    """学历匹配"""

    def test_education_meets_requirement(self):
        profile = self._make_profile(skills=["Python"], education="硕士")
        job = self._make_job(skills=["Python"], degree="本科")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.education_match == 1.0

    def test_education_below_requirement(self):
        profile = self._make_profile(skills=["Python"], education="大专")
        job = self._make_job(skills=["Python"], degree="本科")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.education_match == 0.3

    def test_education_no_limit(self):
        profile = self._make_profile(skills=["Python"], education="本科")
        job = self._make_job(skills=["Python"], degree="学历不限")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.education_match is None

    def test_education_empty_profile(self):
        profile = self._make_profile(skills=["Python"], education="")
        job = self._make_job(skills=["Python"], degree="本科")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.education_match is None

    """公司质量"""

    def test_company_large_listed(self):
        profile = self._make_profile(skills=["Python"])
        job = self._make_job(skills=["Python"], scale="10000人以上", stage="已上市")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.company_quality == 1.0

    def test_company_small_unfunded(self):
        profile = self._make_profile(skills=["Python"])
        job = self._make_job(skills=["Python"], scale="0-99人", stage="未融资")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.company_quality is not None
        assert result.company_quality < 0.5

    def test_company_no_info(self):
        profile = self._make_profile(skills=["Python"])
        job = self._make_job(skills=["Python"], scale="", stage="")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.company_quality is None

    def test_company_partial_info(self):
        profile = self._make_profile(skills=["Python"])
        job = self._make_job(skills=["Python"], scale="1000-9999人", stage="")
        scorer = RuleBasedScorer()
        result = scorer.score(job, profile)

        assert result.company_quality == 0.8
