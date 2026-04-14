"""虚拟 Profile 生成测试"""

from __future__ import annotations

import pytest

from src.ai.profile_builder import _infer_level, career_path_to_profile
from src.ai.schemas import CareerPath, ResumeExtract
from src.core.normalizer import reset_lookup


@pytest.fixture(autouse=True)
def _reset_normalizer():
    reset_lookup()
    yield
    reset_lookup()


class TestInferLevel:
    """_infer_level 边界测试"""

    @pytest.mark.parametrize(
        ("years", "expected"),
        [
            (0, "junior"),
            (1, "junior"),
            (2, "junior"),
            (3, "mid"),
            (4, "mid"),
            (5, "mid-senior"),
            (7, "mid-senior"),
            (8, "senior"),
            (10, "senior"),
            (20, "senior"),
        ],
    )
    def test_level_mapping(self, years, expected):
        assert _infer_level(years) == expected


class TestCareerPathToProfile:
    """career_path_to_profile 测试"""

    def _make_extract(
        self,
        skills=None,
        years=5,
    ) -> ResumeExtract:
        return ResumeExtract(
            skills=skills or ["Python", "SQL", "数据分析"],
            experience_years=years,
        )

    def _make_path(
        self,
        title="数据分析师",
        salary_range=None,
        required_skills=None,
    ) -> CareerPath:
        return CareerPath(
            title=title,
            match_reason="匹配",
            required_skills=required_skills or [],
            salary_range=salary_range,
        )

    def test_basic_profile_generation(self):
        extract = self._make_extract()
        path = self._make_path(title="数据分析师")
        profile = career_path_to_profile(path, extract)

        assert profile.target_roles == ["数据分析师"]
        assert profile.experience.years == 5
        assert profile.experience.level == "mid-senior"
        assert len(profile.skills) == 3

    def test_skills_normalized(self):
        """LLM 输出的别名技能应该被归一化"""
        extract = ResumeExtract(
            skills=["python3", "mysql", "前端开发"],
            experience_years=3,
        )
        path = self._make_path()
        profile = career_path_to_profile(path, extract)

        # python3 → python, mysql → sql, 前端开发 → 前端
        assert "python" in profile.skills
        assert "sql" in profile.skills
        assert "前端" in profile.skills

    def test_salary_range_parsed(self):
        extract = self._make_extract()
        path = self._make_path(salary_range="20-30K")
        profile = career_path_to_profile(path, extract)

        assert profile.preferences.salary_min == 20000
        assert profile.preferences.salary_max == 30000

    def test_salary_range_none_defaults_to_zero(self):
        """salary_range 为 None 时, salary_min/max 为 0(不限制)"""
        extract = self._make_extract()
        path = self._make_path(salary_range=None)
        profile = career_path_to_profile(path, extract)

        assert profile.preferences.salary_min == 0
        assert profile.preferences.salary_max == 0

    def test_salary_range_unparseable_defaults_to_zero(self):
        """salary_range 无法解析时, 降级为 0"""
        extract = self._make_extract()
        path = self._make_path(salary_range="面议")
        profile = career_path_to_profile(path, extract)

        assert profile.preferences.salary_min == 0
        assert profile.preferences.salary_max == 0

    def test_default_scoring_weights(self):
        extract = self._make_extract()
        path = self._make_path()
        profile = career_path_to_profile(path, extract)

        assert profile.scoring.skill == 0.4
        assert profile.scoring.experience == 0.3
        assert profile.scoring.salary == 0.3

    def test_junior_level(self):
        extract = self._make_extract(years=1)
        path = self._make_path()
        profile = career_path_to_profile(path, extract)

        assert profile.experience.level == "junior"

    def test_senior_level(self):
        extract = self._make_extract(years=10)
        path = self._make_path()
        profile = career_path_to_profile(path, extract)

        assert profile.experience.level == "senior"
