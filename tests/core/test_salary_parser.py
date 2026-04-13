"""薪资解析器测试"""

from src.core.salary_parser import parse_salary
from src.data.models import SalaryRange


class TestParseSalary:
    """标准格式"""

    def test_standard_k(self):
        result = parse_salary("20-30K")
        assert result == SalaryRange(min_monthly=20000, max_monthly=30000, months=12)

    def test_standard_k_lowercase(self):
        result = parse_salary("20-30k")
        assert result == SalaryRange(min_monthly=20000, max_monthly=30000, months=12)

    def test_with_months(self):
        result = parse_salary("20-30K·14薪")
        assert result == SalaryRange(min_monthly=20000, max_monthly=30000, months=14)

    def test_with_16_months(self):
        result = parse_salary("15-25K·16薪")
        assert result == SalaryRange(min_monthly=15000, max_monthly=25000, months=16)

    def test_with_13_months(self):
        result = parse_salary("18-28K·13薪")
        assert result == SalaryRange(min_monthly=18000, max_monthly=28000, months=13)

    def test_low_range(self):
        result = parse_salary("10-15K")
        assert result == SalaryRange(min_monthly=10000, max_monthly=15000, months=12)

    def test_high_range(self):
        result = parse_salary("40-60K·16薪")
        assert result == SalaryRange(min_monthly=40000, max_monthly=60000, months=16)

    """不可解析格式 → None"""

    def test_negotiable(self):
        assert parse_salary("面议") is None

    def test_negotiable_full(self):
        assert parse_salary("薪资面议") is None

    def test_daily_pay(self):
        assert parse_salary("150-200元/天") is None

    def test_empty_string(self):
        assert parse_salary("") is None

    def test_none_input(self):
        assert parse_salary(None) is None

    def test_whitespace(self):
        assert parse_salary("   ") is None

    """边界情况"""

    def test_spaces_in_format(self):
        result = parse_salary("20 - 30 K · 14 薪")
        assert result is not None
        assert result.months == 14

    def test_same_min_max(self):
        result = parse_salary("20-20K")
        assert result is not None
        assert result.min_monthly == result.max_monthly

    def test_reversed_range(self):
        # min > max 应返回 None
        assert parse_salary("30-20K") is None
