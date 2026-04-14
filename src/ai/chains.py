"""LangChain Chain 定义 — 结构化提取 + 职业路径推荐

GLM-4-flash 通过 langchain-openai ChatOpenAI 调用（OpenAI 兼容接口）。
直接 prompt + Pydantic 解析，兼容 zhipuai OpenAI-compatible API。
"""

from __future__ import annotations

import json
import os
import re

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.ai.prompts import EXTRACT_PROMPT, RECOMMEND_PROMPT
from src.ai.schemas import CareerRecommendation, ResumeExtract

# ─── LLM 实例 ───

_API_KEY_MISSING_MSG = (
    "缺少环境变量 ZHIPU_API_KEY。\n"
    "请运行: set ZHIPU_API_KEY=你的密钥\n"
    "获取密钥: https://open.bigmodel.cn/"
)

_MAX_RETRIES = 3


def _get_api_key() -> str:
    key = os.environ.get("ZHIPU_API_KEY", "").strip()
    if not key:
        raise OSError(_API_KEY_MISSING_MSG)
    return key


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="glm-4-flash",
        api_key=_get_api_key(),
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        temperature=0.3,
        request_timeout=30,
    )


def _extract_json_from_text(text: str) -> str:
    """从 LLM 回复中提取 JSON 块（兼容 markdown 代码块包裹）"""
    # 尝试匹配 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 尝试匹配 { ... } 最外层大括号
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0)
    return text.strip()


# ─── 便捷入口 ───


def run_extract(resume_markdown: str) -> ResumeExtract:
    """Chain 1: 从简历 Markdown 提取结构化信息（带重试）"""
    llm = _make_llm()
    messages = EXTRACT_PROMPT.format_messages(resume_markdown=resume_markdown)

    last_err = None
    for _ in range(_MAX_RETRIES):
        try:
            response = llm.invoke(messages)
            raw = _extract_json_from_text(response.content)
            return ResumeExtract.model_validate_json(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_err = exc
            continue

    raise last_err  # type: ignore[misc]


def run_recommend(extract: ResumeExtract, num_paths: int = 3) -> CareerRecommendation:
    """Chain 2: 根据提取结果推荐职业路径（带重试）"""
    llm = _make_llm()
    messages = RECOMMEND_PROMPT.format_messages(
        extract_json=extract.model_dump_json(indent=2, ensure_ascii=False),
        num_paths=str(num_paths),
    )

    last_err = None
    for _ in range(_MAX_RETRIES):
        try:
            response = llm.invoke(messages)
            raw = _extract_json_from_text(response.content)
            return CareerRecommendation.model_validate_json(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_err = exc
            continue

    raise last_err  # type: ignore[misc]
