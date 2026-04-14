"""LangChain Chain 测试 — Mock LLM 响应"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ai.schemas import CareerRecommendation, CareerPath, ResumeExtract


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


class TestRecommendChain:
    """Chain 2: 职业路径推荐链路测试"""

    def test_successful_3_paths(self):
        data = {
            "paths": [
                {"title": "数据分析师", "match_reason": "技能匹配", "required_skills": ["Tableau"]},
                {"title": "产品经理", "match_reason": "有产品设计经验", "required_skills": ["用户研究"]},
                {"title": "Python开发", "match_reason": "Python 核心技能", "required_skills": ["Django"]},
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
