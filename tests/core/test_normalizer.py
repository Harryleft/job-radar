"""技能归一化测试"""

from src.core.normalizer import normalize_skill, normalize_skills, reset_lookup


class TestNormalizeSkill:
    def setup_method(self):
        reset_lookup()

    def test_exact_match(self):
        assert normalize_skill("Python") == "python"

    def test_case_insensitive(self):
        assert normalize_skill("python") == "python"
        assert normalize_skill("PYTHON") == "python"

    def test_alias_python3(self):
        assert normalize_skill("python3") == "python"

    def test_alias_mysql(self):
        assert normalize_skill("mysql") == "sql"

    def test_alias_data_analysis(self):
        assert normalize_skill("data analysis") == "数据分析"

    def test_unknown_skill_passthrough(self):
        result = normalize_skill("Rust")
        assert result == "Rust"  # 原样返回（保留大小写）

    def test_whitespace_trim(self):
        assert normalize_skill("  Python  ") == "python"

    def test_empty_string(self):
        assert normalize_skill("") == ""

    def test_none_like(self):
        assert normalize_skill("  ") == "  "


class TestNormalizeSkills:
    def setup_method(self):
        reset_lookup()

    def test_batch_normalize(self):
        result = normalize_skills(["Python", "MySQL", "React"])
        assert result == ["python", "sql", "react"]

    def test_empty_list(self):
        assert normalize_skills([]) == []

    def test_mixed_known_unknown(self):
        result = normalize_skills(["Python", "Rust", "mysql"])
        assert result == ["python", "Rust", "sql"]
