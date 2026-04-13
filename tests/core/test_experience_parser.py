"""经验解析器测试"""

from src.core.experience_parser import parse_experience


class TestParseExperience:
    """标准格式"""

    def test_range_3_5(self):
        assert parse_experience("3-5年") == (3, 5)

    def test_range_1_3(self):
        assert parse_experience("1-3年") == (1, 3)

    def test_range_5_10(self):
        assert parse_experience("5-10年") == (5, 10)

    """特殊格式"""

    def test_no_limit(self):
        assert parse_experience("经验不限") == (0, 999)

    def test_plus_years(self):
        assert parse_experience("5年以上") == (5, 999)

    def test_plus_10_years(self):
        assert parse_experience("10年以上") == (10, 999)

    def test_fresh_grad(self):
        assert parse_experience("应届生") == (0, 0)

    def test_student(self):
        assert parse_experience("在校生") == (0, 0)

    def test_under_1_year(self):
        assert parse_experience("1年以下") == (0, 1)

    """不可解析 → None"""

    def test_none_input(self):
        assert parse_experience(None) is None

    def test_empty_string(self):
        assert parse_experience("") is None

    def test_whitespace(self):
        assert parse_experience("   ") is None

    def test_unknown_format(self):
        assert parse_experience("三年以上") is None  # 中文数字不支持

    def test_gibberish(self):
        assert parse_experience("abc") is None
