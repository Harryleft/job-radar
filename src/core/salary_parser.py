"""薪资字符串解析器

支持的格式:
  "20-30K"        → SalaryRange(min=20000, max=30000, months=12)
  "20-30K·14薪"   → SalaryRange(min=20000, max=30000, months=14)
  "15-25K·16薪"   → SalaryRange(min=15000, max=25000, months=16)
  "10-15k"        → SalaryRange(min=10000, max=15000, months=12)  (小写k)

不支持的格式 → 返回 None, 评分器跳过 salary_fit 信号:
  "面议", "薪资面议", "200-300元/天", "20-30W", None, ""
"""

from __future__ import annotations

import re

from src.data.models import SalaryRange

# 匹配: 数字-数字K/K，可选·数字薪
_PATTERN = re.compile(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*[Kk](?:\s*[·.]\s*(\d+)\s*薪)?\s*$")


def parse_salary(salary_desc: str | None) -> SalaryRange | None:
    """解析薪资描述字符串。

    Returns:
        SalaryRange 或 None（无法解析时）
    """
    if not salary_desc or not salary_desc.strip():
        return None

    # 快速跳过已知不可解析格式
    stripped = salary_desc.strip()
    if stripped in ("面议", "薪资面议"):
        return None

    match = _PATTERN.fullmatch(stripped)
    if not match:
        return None

    min_k = int(match.group(1))
    max_k = int(match.group(2))
    months = int(match.group(3)) if match.group(3) else 12

    if min_k <= 0 or max_k <= 0 or min_k > max_k or months <= 0:
        return None

    return SalaryRange(
        min_monthly=min_k * 1000,
        max_monthly=max_k * 1000,
        months=months,
    )
