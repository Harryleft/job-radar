"""学历字符串解析 — 中文职位描述中的学历要求标准化

将 "本科"、"硕士" 等中文描述映射为数值等级，用于匹配评分。
"""

from __future__ import annotations

# 学历等级映射表
_EDU_LEVELS: dict[str, int] = {
    "博士": 6,
    "硕士": 5,
    "本科": 4,
    "大专": 3,
    "中专": 2,
    "高中": 2,
    "初中": 1,
}

# 无法解析时返回 None 的哨兵值
_SKIP_VALUES = {"学历不限", "不限", "无", ""}


def parse_education(edu_desc: str | None) -> int | None:
    """解析学历字符串为数值等级

    Args:
        edu_desc: 学历描述，如 "本科"、"硕士及以上"、"学历不限"

    Returns:
        数值等级 (1-6)，无法解析时返回 None

    Examples:
        >>> parse_education("硕士")
        5
        >>> parse_education("本科及以上")
        4
        >>> parse_education("学历不限")
        None
        >>> parse_education(None)
        None
    """
    if not edu_desc or not edu_desc.strip():
        return None

    text = edu_desc.strip()

    if text in _SKIP_VALUES:
        return None

    # 精确匹配
    if text in _EDU_LEVELS:
        return _EDU_LEVELS[text]

    # 模糊匹配: "硕士及以上" → 取 "硕士"
    for keyword, level in _EDU_LEVELS.items():
        if keyword in text:
            return level

    return None
