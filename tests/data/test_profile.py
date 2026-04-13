"""用户配置加载测试"""

import pytest

from src.data.profile import _parse_salary_string, load_profile


class TestParseSalaryString:
    def test_15k(self):
        assert _parse_salary_string("15K") == 15000

    def test_15k_lowercase(self):
        assert _parse_salary_string("15k") == 15000

    def test_plain_number(self):
        assert _parse_salary_string("15000") == 15000

    def test_empty_string(self):
        assert _parse_salary_string("") == 0

    def test_none_like(self):
        assert _parse_salary_string("  ") == 0

    def test_with_space(self):
        assert _parse_salary_string("15 K") == 15000


class TestLoadProfile:
    def test_valid_profile(self, tmp_path):
        content = """\
skills:
  - Python
  - SQL
experience:
  years: 5
  level: mid-senior
preferences:
  cities: [上海, 北京]
  salary_min: 15K
  salary_max: 35K
target_roles:
  - 数据分析师
"""
        fp = tmp_path / "profile.yaml"
        fp.write_text(content, encoding="utf-8")

        profile = load_profile(str(fp))
        assert profile.skills == ["Python", "SQL"]
        assert profile.experience.years == 5
        assert profile.preferences.salary_min == 15000
        assert profile.preferences.salary_max == 35000
        assert profile.preferences.cities == ["上海", "北京"]
        assert profile.target_roles == ["数据分析师"]

    def test_minimal_profile(self, tmp_path):
        content = """\
skills:
  - Python
"""
        fp = tmp_path / "minimal.yaml"
        fp.write_text(content, encoding="utf-8")

        profile = load_profile(str(fp))
        assert profile.skills == ["Python"]
        assert profile.experience.years == 0
        assert profile.preferences.salary_min == 0

    def test_custom_scoring_weights(self, tmp_path):
        content = """\
skills:
  - Python
scoring:
  skill: 0.5
  experience: 0.3
  salary: 0.2
"""
        fp = tmp_path / "weights.yaml"
        fp.write_text(content, encoding="utf-8")

        profile = load_profile(str(fp))
        assert profile.scoring.skill == 0.5
        assert profile.scoring.experience == 0.3
        assert profile.scoring.salary == 0.2

    def test_missing_skills_fails(self, tmp_path):
        content = """\
experience:
  years: 3
"""
        fp = tmp_path / "no_skills.yaml"
        fp.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="skills"):
            load_profile(str(fp))

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="不存在"):
            load_profile("/nonexistent/profile.yaml")

    def test_boss_cookie_placeholder(self, tmp_path):
        content = """\
skills:
  - Python
boss_cookie: ""
"""
        fp = tmp_path / "cookie.yaml"
        fp.write_text(content, encoding="utf-8")

        profile = load_profile(str(fp))
        assert profile.boss_cookie == ""
