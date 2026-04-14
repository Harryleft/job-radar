"""Schema 校验测试"""

import pytest
from pydantic import ValidationError

from src.ai.schemas import CareerPath, CareerRecommendation, ResumeExtract


class TestResumeExtract:
    """ResumeExtract schema 测试"""

    def test_valid_full(self):
        data = {
            "skills": ["Python", "SQL"],
            "experience_years": 5,
            "education": "本科 计算机科学",
            "work_history": ["XX公司 Python开发"],
            "highlights": ["负责数据分析平台"],
        }
        result = ResumeExtract.model_validate(data)
        assert result.skills == ["Python", "SQL"]
        assert result.experience_years == 5

    def test_minimal_fields(self):
        result = ResumeExtract.model_validate({"skills": ["Python"], "experience_years": 3})
        assert result.education == ""
        assert result.work_history == []
        assert result.highlights == []

    def test_missing_skills_fails(self):
        with pytest.raises(ValidationError):
            ResumeExtract.model_validate({"experience_years": 3})

    def test_missing_experience_years_fails(self):
        with pytest.raises(ValidationError):
            ResumeExtract.model_validate({"skills": ["Python"]})

    def test_empty_skills_list_allowed(self):
        result = ResumeExtract.model_validate({"skills": [], "experience_years": 1})
        assert result.skills == []


class TestCareerPath:
    """CareerPath schema 测试"""

    def test_valid_full(self):
        data = {
            "title": "数据分析师",
            "match_reason": "Python + SQL 匹配",
            "required_skills": ["Tableau"],
            "salary_range": "15-30K",
        }
        result = CareerPath.model_validate(data)
        assert result.title == "数据分析师"
        assert result.salary_range == "15-30K"

    def test_salary_range_optional(self):
        result = CareerPath.model_validate({
            "title": "产品经理",
            "match_reason": "产品设计经验",
        })
        assert result.salary_range is None
        assert result.required_skills == []


class TestCareerRecommendation:
    """CareerRecommendation schema + paths 边界校验"""

    def _make_paths(self, n: int) -> list[dict]:
        return [
            {"title": f"路径{i+1}", "match_reason": f"理由{i+1}"}
            for i in range(n)
        ]

    def test_valid_3_paths(self):
        result = CareerRecommendation.model_validate({"paths": self._make_paths(3)})
        assert len(result.paths) == 3

    def test_valid_1_path_minimum(self):
        result = CareerRecommendation.model_validate({"paths": self._make_paths(1)})
        assert len(result.paths) == 1

    def test_valid_5_paths_maximum(self):
        result = CareerRecommendation.model_validate({"paths": self._make_paths(5)})
        assert len(result.paths) == 5

    def test_0_paths_fails(self):
        with pytest.raises(ValidationError, match="1-5"):
            CareerRecommendation.model_validate({"paths": []})

    def test_6_paths_fails(self):
        with pytest.raises(ValidationError, match="1-5"):
            CareerRecommendation.model_validate({"paths": self._make_paths(6)})

    def test_100_paths_fails(self):
        with pytest.raises(ValidationError, match="1-5"):
            CareerRecommendation.model_validate({"paths": self._make_paths(100)})
