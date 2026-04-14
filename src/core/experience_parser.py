"""经验字符串解析器

支持的格式:
  "3-5年"    → (3, 5)
  "1-3年"    → (1, 3)
  "经验不限"  → (0, 999)
  "5年以上"   → (5, 999)
  "应届生"    → (0, 0)
  "1年以下"   → (0, 1)
  "在校生"    → (0, 0)

不支持的格式 → 返回 None, 评分器跳过 experience_match 信号
"""

from __future__ import annotations

import re

# "3-5年", "1-3年"
_RANGE_PATTERN = re.compile(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*年\s*$")
# "5年以上", "10年以上"
_PLUS_PATTERN = re.compile(r"^\s*(\d+)\s*年\s*以\s*上")
# "1年以下"
_UNDER_PATTERN = re.compile(r"^\s*(\d+)\s*年\s*以\s*下")

_NO_LIMIT = {"经验不限", "不限", "经验不限/"}
_FRESH_GRAD = {"应届生", "在校生", "应届"}


def parse_experience(exp_desc: str | None) -> tuple[int, int] | None:
    """解析经验要求字符串。

    Returns:
        (min_years, max_years) 或 None（无法解析时）
    """
    if not exp_desc or not exp_desc.strip():
        return None

    stripped = exp_desc.strip()

    if stripped in _NO_LIMIT:
        return (0, 999)

    if stripped in _FRESH_GRAD:
        return (0, 0)

    # "X年以下"
    m = _UNDER_PATTERN.fullmatch(stripped)
    if m:
        return (0, int(m.group(1)))

    # "X年以上"
    m = _PLUS_PATTERN.fullmatch(stripped)
    if m:
        return (int(m.group(1)), 999)

    # "X-Y年"
    m = _RANGE_PATTERN.fullmatch(stripped)
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        if low > high:
            return None
        return (low, high)

    return None
