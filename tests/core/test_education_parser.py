"""学历解析器测试"""

from src.core.education_parser import parse_education


class TestParseEducation:
    """parse_education 核心用例"""

    def test_master(self) -> None:
        assert parse_education("硕士") == 5

    def test_bachelor(self) -> None:
        assert parse_education("本科") == 4

    def test_college(self) -> None:
        assert parse_education("大专") == 3

    def test_phd(self) -> None:
        assert parse_education("博士") == 6

    def test_high_school(self) -> None:
        assert parse_education("高中") == 2

    def test_middle_school(self) -> None:
        assert parse_education("初中") == 1

    def test_vocational(self) -> None:
        assert parse_education("中专") == 2

    def test_bachelor_or_above(self) -> None:
        assert parse_education("本科及以上") == 4

    def test_master_or_above(self) -> None:
        assert parse_education("硕士及以上") == 5

    def test_no_limit(self) -> None:
        assert parse_education("学历不限") is None

    def test_empty_string(self) -> None:
        assert parse_education("") is None

    def test_none_input(self) -> None:
        assert parse_education(None) is None

    def test_whitespace(self) -> None:
        assert parse_education("  ") is None

    def test_unknown(self) -> None:
        assert parse_education(" unknown ") is None
