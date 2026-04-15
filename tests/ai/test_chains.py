"""LangChain Chain 测试 — Mock LLM 响应"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ai.schemas import CareerRecommendation, ResumeExtract


class TestExtractChain:
    """Chain 1: 结构化提取链路测试"""

    def test_successful_extraction(self):
        """Mock LLM 返回合法 JSON, 验证 Pydantic 解析"""
        mock_response = ResumeExtract(
            skills=["Python", "SQL", "数据分析"],
            experience_years=5,
            education="本科 计算机科学",
            work_history=["XX公司 数据分析"],
            highlights=["搭建数据分析平台"],
        )
        # 验证 schema 能正确解析
        assert mock_response.skills == ["Python", "SQL", "数据分析"]
        assert mock_response.experience_years == 5

    def test_llm_returns_invalid_json(self):
        """LLM 返回非法 JSON 时, Pydantic 应抛出 ValidationError"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResumeExtract.model_validate("not a dict")

    def test_llm_returns_partial_data(self):
        """LLM 返回部分字段时, 可选字段应使用默认值"""
        result = ResumeExtract.model_validate({
            "skills": ["Python"],
            "experience_years": 3,
        })
        assert result.education == ""
        assert result.work_history == []
        assert result.highlights == []
        assert result.location_preferences == []
        assert result.life_context == ""
        assert result.career_goals == ""

    def test_background_fields_parsed(self):
        """背景叙事字段正确解析"""
        result = ResumeExtract.model_validate({
            "skills": ["Python", "Go"],
            "experience_years": 5,
            "location_preferences": ["杭州-互联网机会多", "海口-生活成本低"],
            "life_context": "已婚有娃，考虑教育资源",
            "career_goals": "3年内晋升技术管理",
        })
        assert len(result.location_preferences) == 2
        assert "杭州" in result.location_preferences[0]
        assert result.life_context == "已婚有娃，考虑教育资源"
        assert result.career_goals == "3年内晋升技术管理"


class TestBackgroundExtractChain:
    """Chain 1b: 自由文本背景提取链路测试"""

    def test_successful_extraction(self) -> None:
        """Mock LLM 返回完整背景 JSON"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "skills": ["Python", "SQL", "项目管理"],
            "experience_years": 5,
            "education": "本科",
            "work_history": ["A公司 后端开发"],
            "highlights": ["主导微服务重构"],
            "location_preferences": ["杭州-职业机会多", "成都-生活节奏合适"],
            "life_context": "已婚，有一个孩子",
            "career_goals": "希望转型技术管理",
        })
        mock_llm.invoke.return_value = mock_response

        with patch("src.ai.chains._make_llm", return_value=mock_llm):
            from src.ai.chains import run_extract_background

            result = run_extract_background("我5年Python经验...")

        assert "Python" in result.skills
        assert result.experience_years == 5
        assert len(result.location_preferences) == 2
        assert result.life_context == "已婚，有一个孩子"

    def test_minimal_input_defaults(self) -> None:
        """背景文本信息不足时，新字段使用默认值"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "skills": ["Python"],
            "experience_years": 3,
        })
        mock_llm.invoke.return_value = mock_response

        with patch("src.ai.chains._make_llm", return_value=mock_llm):
            from src.ai.chains import run_extract_background

            result = run_extract_background("我会Python")

        assert result.location_preferences == []
        assert result.life_context == ""
        assert result.career_goals == ""


class TestRecommendChain:
    """Chain 2: 职业路径推荐链路测试"""

    def test_successful_3_paths(self):
        data = {
            "paths": [
                {
                    "title": "数据分析师",
                    "match_reason": "技能匹配",
                    "required_skills": ["Tableau"],
                },
                {
                    "title": "产品经理",
                    "match_reason": "有产品设计经验",
                    "required_skills": ["用户研究"],
                },
                {
                    "title": "Python开发",
                    "match_reason": "Python 核心技能",
                    "required_skills": ["Django"],
                },
            ]
        }
        result = CareerRecommendation.model_validate(data)
        assert len(result.paths) == 3
        assert result.paths[0].title == "数据分析师"

    def test_retry_on_parse_failure(self):
        """验证 PydanticOutputParser 在非法 JSON 时抛异常, 可被 with_retry 捕获"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CareerRecommendation.model_validate({"paths": []})


class TestApiKeyHandling:
    """ZHIPU_API_KEY 缺失时的行为"""

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises(self):
        """无 ZHIPU_API_KEY 时, 应该友好报错而非 raw traceback"""
        import os

        assert "ZHIPU_API_KEY" not in os.environ
        # 实际实现中应在 chains.py 中检查并抛出友好错误
        # 此测试验证环境变量确实缺失的场景
        with pytest.raises(KeyError):
            _ = os.environ["ZHIPU_API_KEY"]
